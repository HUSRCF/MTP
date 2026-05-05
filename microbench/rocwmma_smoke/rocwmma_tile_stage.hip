#include <hip/hip_runtime.h>
#include <rocwmma/rocwmma.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int kM = 16;
constexpr int kN = 16;
constexpr int kK = 16;
constexpr int kTileElems = 256;

#define HIP_CHECK(expr)                                                     \
  do {                                                                      \
    hipError_t _err = (expr);                                                \
    if (_err != hipSuccess) {                                                \
      std::ostringstream _oss;                                               \
      _oss << "HIP error at " << __FILE__ << ":" << __LINE__ << ": "       \
           << hipGetErrorString(_err);                                       \
      throw std::runtime_error(_oss.str());                                  \
    }                                                                       \
  } while (0)

enum class Mode : int {
  kGlobalBaseline = 0,
  kLdsHit = 1,
  kLdsMissOverwrite = 2,
};

struct Options {
  int device = 0;
  int warmup = 20;
  int iters = 200;
  Mode mode = Mode::kGlobalBaseline;
};

int parse_int(const char* value, const char* name) {
  char* end = nullptr;
  long parsed = std::strtol(value, &end, 10);
  if (!end || *end != '\0') {
    throw std::runtime_error(std::string("invalid integer for ") + name + ": " + value);
  }
  return static_cast<int>(parsed);
}

Mode parse_mode(const std::string& value) {
  if (value == "global_baseline") return Mode::kGlobalBaseline;
  if (value == "lds_hit") return Mode::kLdsHit;
  if (value == "lds_miss_overwrite") return Mode::kLdsMissOverwrite;
  throw std::runtime_error("unknown mode: " + value);
}

const char* mode_name(Mode mode) {
  switch (mode) {
    case Mode::kGlobalBaseline:
      return "global_baseline";
    case Mode::kLdsHit:
      return "lds_hit";
    case Mode::kLdsMissOverwrite:
      return "lds_miss_overwrite";
  }
  return "unknown";
}

Options parse_args(int argc, char** argv) {
  Options opt;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto need_value = [&](const char* name) -> const char* {
      if (i + 1 >= argc) {
        throw std::runtime_error(std::string("missing value for ") + name);
      }
      return argv[++i];
    };
    if (arg == "--device") {
      opt.device = parse_int(need_value("--device"), "--device");
    } else if (arg == "--warmup") {
      opt.warmup = parse_int(need_value("--warmup"), "--warmup");
    } else if (arg == "--iters") {
      opt.iters = parse_int(need_value("--iters"), "--iters");
    } else if (arg == "--mode") {
      opt.mode = parse_mode(need_value("--mode"));
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: rocwmma_tile_stage [--device N] [--mode global_baseline|lds_hit|lds_miss_overwrite]"
                   " [--warmup N] [--iters N]\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  return opt;
}

__global__ void rocwmma_tile_stage_kernel(
    const rocwmma::float16_t* __restrict__ a,
    const rocwmma::float16_t* __restrict__ b_true,
    const rocwmma::float16_t* __restrict__ b_wrong,
    float* __restrict__ c,
    int mode) {
  using namespace rocwmma;
  using FragA = fragment<matrix_a, kM, kN, kK, float16_t, row_major>;
  using FragB = fragment<matrix_b, kM, kN, kK, float16_t, row_major>;
  using FragC = fragment<accumulator, kM, kN, kK, float>;

  __shared__ float16_t s_a[kTileElems];
  __shared__ float16_t s_b[kTileElems];

  FragA frag_a;
  FragB frag_b;
  FragC frag_c;
  FragC frag_d;

  if (mode == static_cast<int>(Mode::kGlobalBaseline)) {
    load_matrix_sync(frag_a, a, kK);
    load_matrix_sync(frag_b, b_true, kN);
  } else if (mode == static_cast<int>(Mode::kLdsHit)) {
    for (int idx = threadIdx.x; idx < kTileElems; idx += blockDim.x) {
      s_a[idx] = a[idx];
      s_b[idx] = b_true[idx];
    }
    __syncthreads();
    load_matrix_sync(frag_a, s_a, kK);
    load_matrix_sync(frag_b, s_b, kN);
  } else {
    for (int idx = threadIdx.x; idx < kTileElems; idx += blockDim.x) {
      s_a[idx] = a[idx];
      s_b[idx] = b_wrong[idx];
    }
    __syncthreads();
    // Miss path: prediction staged the wrong tile, then validation forces a
    // bounded overwrite of the LDS tile before rocWMMA consumes it.
    for (int idx = threadIdx.x; idx < kTileElems; idx += blockDim.x) {
      s_b[idx] = b_true[idx];
    }
    __syncthreads();
    load_matrix_sync(frag_a, s_a, kK);
    load_matrix_sync(frag_b, s_b, kN);
  }

  fill_fragment(frag_c, 0.0f);
  mma_sync(frag_d, frag_a, frag_b, frag_c);
  store_matrix_sync(c, frag_d, kN, mem_row_major);
}

double mean(const std::vector<float>& xs) {
  if (xs.empty()) return 0.0;
  return std::accumulate(xs.begin(), xs.end(), 0.0) / static_cast<double>(xs.size());
}

void fill_inputs(std::vector<rocwmma::float16_t>& a,
                 std::vector<rocwmma::float16_t>& b,
                 std::vector<rocwmma::float16_t>& b_wrong) {
  for (int m = 0; m < kM; ++m) {
    for (int k = 0; k < kK; ++k) {
      const float v = 0.01f * static_cast<float>((m * 3 + k * 5) % 11 - 5);
      a[m * kK + k] = static_cast<rocwmma::float16_t>(v);
    }
  }
  for (int k = 0; k < kK; ++k) {
    for (int n = 0; n < kN; ++n) {
      const float v = 0.01f * static_cast<float>((k * 7 + n * 2) % 13 - 6);
      const float wrong = 0.01f * static_cast<float>((k * 5 + n * 11) % 17 - 8);
      b[k * kN + n] = static_cast<rocwmma::float16_t>(v);
      b_wrong[k * kN + n] = static_cast<rocwmma::float16_t>(wrong);
    }
  }
}

std::vector<float> reference(const std::vector<rocwmma::float16_t>& a,
                             const std::vector<rocwmma::float16_t>& b) {
  std::vector<float> ref(kM * kN, 0.0f);
  for (int m = 0; m < kM; ++m) {
    for (int n = 0; n < kN; ++n) {
      float acc = 0.0f;
      for (int k = 0; k < kK; ++k) {
        acc += static_cast<float>(a[m * kK + k]) * static_cast<float>(b[k * kN + n]);
      }
      ref[m * kN + n] = acc;
    }
  }
  return ref;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = parse_args(argc, argv);
    if (opt.warmup < 0 || opt.iters <= 0) {
      throw std::runtime_error("invalid warmup/iters");
    }
    HIP_CHECK(hipSetDevice(opt.device));
    hipDeviceProp_t prop{};
    HIP_CHECK(hipGetDeviceProperties(&prop, opt.device));

    std::vector<rocwmma::float16_t> h_a(kTileElems);
    std::vector<rocwmma::float16_t> h_b(kTileElems);
    std::vector<rocwmma::float16_t> h_b_wrong(kTileElems);
    std::vector<float> h_c(kM * kN, 0.0f);
    fill_inputs(h_a, h_b, h_b_wrong);
    const std::vector<float> ref = reference(h_a, h_b);

    rocwmma::float16_t* d_a = nullptr;
    rocwmma::float16_t* d_b = nullptr;
    rocwmma::float16_t* d_b_wrong = nullptr;
    float* d_c = nullptr;
    HIP_CHECK(hipMalloc(&d_a, h_a.size() * sizeof(rocwmma::float16_t)));
    HIP_CHECK(hipMalloc(&d_b, h_b.size() * sizeof(rocwmma::float16_t)));
    HIP_CHECK(hipMalloc(&d_b_wrong, h_b_wrong.size() * sizeof(rocwmma::float16_t)));
    HIP_CHECK(hipMalloc(&d_c, h_c.size() * sizeof(float)));
    HIP_CHECK(hipMemcpy(d_a, h_a.data(), h_a.size() * sizeof(rocwmma::float16_t),
                        hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(d_b, h_b.data(), h_b.size() * sizeof(rocwmma::float16_t),
                        hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(d_b_wrong, h_b_wrong.data(), h_b_wrong.size() * sizeof(rocwmma::float16_t),
                        hipMemcpyHostToDevice));
    HIP_CHECK(hipMemset(d_c, 0, h_c.size() * sizeof(float)));

    const int mode_int = static_cast<int>(opt.mode);
    for (int i = 0; i < opt.warmup; ++i) {
      hipLaunchKernelGGL(
          rocwmma_tile_stage_kernel, dim3(1), dim3(64), 0, 0, d_a, d_b, d_b_wrong, d_c, mode_int);
      HIP_CHECK(hipGetLastError());
    }
    HIP_CHECK(hipDeviceSynchronize());

    std::vector<float> wall_ms;
    wall_ms.reserve(opt.iters);
    hipEvent_t start = nullptr;
    hipEvent_t stop = nullptr;
    HIP_CHECK(hipEventCreate(&start));
    HIP_CHECK(hipEventCreate(&stop));
    for (int i = 0; i < opt.iters; ++i) {
      HIP_CHECK(hipEventRecord(start));
      hipLaunchKernelGGL(
          rocwmma_tile_stage_kernel, dim3(1), dim3(64), 0, 0, d_a, d_b, d_b_wrong, d_c, mode_int);
      HIP_CHECK(hipGetLastError());
      HIP_CHECK(hipEventRecord(stop));
      HIP_CHECK(hipEventSynchronize(stop));
      float ms = 0.0f;
      HIP_CHECK(hipEventElapsedTime(&ms, start, stop));
      wall_ms.push_back(ms);
    }
    HIP_CHECK(hipEventDestroy(start));
    HIP_CHECK(hipEventDestroy(stop));

    HIP_CHECK(hipMemcpy(h_c.data(), d_c, h_c.size() * sizeof(float), hipMemcpyDeviceToHost));

    double max_abs_err = 0.0;
    double mean_abs_err = 0.0;
    for (size_t i = 0; i < h_c.size(); ++i) {
      const double err = std::abs(static_cast<double>(h_c[i]) - static_cast<double>(ref[i]));
      max_abs_err = std::max(max_abs_err, err);
      mean_abs_err += err;
    }
    mean_abs_err /= static_cast<double>(h_c.size());

    std::cout << std::fixed << std::setprecision(8);
    std::cout << "{\n";
    std::cout << "  \"ok\": " << (max_abs_err < 5.0e-3 ? "true" : "false") << ",\n";
    std::cout << "  \"device\": " << opt.device << ",\n";
    std::cout << "  \"device_name\": \"" << prop.name << "\",\n";
    std::cout << "  \"mode\": \"" << mode_name(opt.mode) << "\",\n";
    std::cout << "  \"matrix_m\": " << kM << ",\n";
    std::cout << "  \"matrix_n\": " << kN << ",\n";
    std::cout << "  \"matrix_k\": " << kK << ",\n";
    std::cout << "  \"block_threads\": 64,\n";
    std::cout << "  \"lds_bytes_per_block\": " << (2 * kTileElems * static_cast<int>(sizeof(rocwmma::float16_t))) << ",\n";
    std::cout << "  \"input_dtype\": \"rocwmma::float16_t\",\n";
    std::cout << "  \"accum_dtype\": \"float\",\n";
    std::cout << "  \"layout_a\": \"row_major\",\n";
    std::cout << "  \"layout_b\": \"row_major\",\n";
    std::cout << "  \"layout_c\": \"row_major\",\n";
    std::cout << "  \"max_abs_err\": " << max_abs_err << ",\n";
    std::cout << "  \"mean_abs_err\": " << mean_abs_err << ",\n";
    std::cout << "  \"wall_ms_mean\": " << mean(wall_ms) << "\n";
    std::cout << "}\n";

    HIP_CHECK(hipFree(d_a));
    HIP_CHECK(hipFree(d_b));
    HIP_CHECK(hipFree(d_b_wrong));
    HIP_CHECK(hipFree(d_c));
  } catch (const std::exception& ex) {
    std::cerr << "error: " << ex.what() << "\n";
    return 1;
  }
  return 0;
}
