#include <hip/hip_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

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
  kGlobalLoad = 0,
  kLdsHeavy = 1,
};

struct Options {
  int device = 0;
  int warmup = 5;
  int iters = 20;
  int blocks = 256;
  int threads = 256;
  int elems = 1 << 22;
  int inner_iters = 64;
  Mode mode = Mode::kGlobalLoad;
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
  if (value == "global_load") return Mode::kGlobalLoad;
  if (value == "lds_heavy") return Mode::kLdsHeavy;
  throw std::runtime_error("unknown mode: " + value);
}

const char* mode_name(Mode mode) {
  switch (mode) {
    case Mode::kGlobalLoad:
      return "global_load";
    case Mode::kLdsHeavy:
      return "lds_heavy";
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
    } else if (arg == "--blocks") {
      opt.blocks = parse_int(need_value("--blocks"), "--blocks");
    } else if (arg == "--threads") {
      opt.threads = parse_int(need_value("--threads"), "--threads");
    } else if (arg == "--elems") {
      opt.elems = parse_int(need_value("--elems"), "--elems");
    } else if (arg == "--inner-iters") {
      opt.inner_iters = parse_int(need_value("--inner-iters"), "--inner-iters");
    } else if (arg == "--mode") {
      opt.mode = parse_mode(need_value("--mode"));
    } else if (arg == "--help" || arg == "-h") {
      std::cout << "Usage: rocprof_positive_controls [--mode global_load|lds_heavy]\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  return opt;
}

__global__ void global_load_heavy_kernel(const float* __restrict__ x,
                                         float* __restrict__ out,
                                         int elems,
                                         int inner_iters) {
  float acc = 0.0f;
  const int tid = blockIdx.x * blockDim.x + threadIdx.x;
  const int stride = gridDim.x * blockDim.x;
  for (int iter = 0; iter < inner_iters; ++iter) {
    for (int idx = tid + iter * 97; idx < elems; idx += stride) {
      acc += x[idx] * 1.0001f;
    }
  }
  if ((threadIdx.x & 31) == 0) {
    atomicAdd(out, acc);
  }
}

__global__ void lds_heavy_kernel(const float* __restrict__ x,
                                 float* __restrict__ out,
                                 int elems,
                                 int inner_iters) {
  extern __shared__ float s[];
  const int tid = blockIdx.x * blockDim.x + threadIdx.x;
  const int local = threadIdx.x;
  s[local] = x[tid % elems];
  __syncthreads();
  float acc = s[local];
  for (int iter = 0; iter < inner_iters; ++iter) {
    const int src = (local + iter * 17) & (blockDim.x - 1);
    acc += s[src] * 1.0003f;
    s[local] = acc;
    __syncthreads();
  }
  if ((threadIdx.x & 31) == 0) {
    atomicAdd(out, acc);
  }
}

double mean(const std::vector<float>& xs) {
  if (xs.empty()) return 0.0;
  return std::accumulate(xs.begin(), xs.end(), 0.0) / static_cast<double>(xs.size());
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = parse_args(argc, argv);
    if (opt.warmup < 0 || opt.iters <= 0 || opt.blocks <= 0 || opt.threads <= 0 ||
        opt.elems <= 0 || opt.inner_iters <= 0 || (opt.threads & (opt.threads - 1)) != 0) {
      throw std::runtime_error("invalid warmup/iters/blocks/threads/elems/inner_iters");
    }
    HIP_CHECK(hipSetDevice(opt.device));
    hipDeviceProp_t prop{};
    HIP_CHECK(hipGetDeviceProperties(&prop, opt.device));

    std::vector<float> h_x(opt.elems);
    for (int i = 0; i < opt.elems; ++i) {
      h_x[i] = static_cast<float>((i * 13) % 97) * 0.001f;
    }
    float* d_x = nullptr;
    float* d_out = nullptr;
    HIP_CHECK(hipMalloc(&d_x, h_x.size() * sizeof(float)));
    HIP_CHECK(hipMalloc(&d_out, sizeof(float)));
    HIP_CHECK(hipMemcpy(d_x, h_x.data(), h_x.size() * sizeof(float), hipMemcpyHostToDevice));
    HIP_CHECK(hipMemset(d_out, 0, sizeof(float)));

    auto launch = [&]() {
      if (opt.mode == Mode::kGlobalLoad) {
        hipLaunchKernelGGL(global_load_heavy_kernel,
                           dim3(opt.blocks),
                           dim3(opt.threads),
                           0,
                           0,
                           d_x,
                           d_out,
                           opt.elems,
                           opt.inner_iters);
      } else {
        hipLaunchKernelGGL(lds_heavy_kernel,
                           dim3(opt.blocks),
                           dim3(opt.threads),
                           static_cast<size_t>(opt.threads) * sizeof(float),
                           0,
                           d_x,
                           d_out,
                           opt.elems,
                           opt.inner_iters);
      }
      HIP_CHECK(hipGetLastError());
    };

    for (int i = 0; i < opt.warmup; ++i) {
      launch();
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
      launch();
      HIP_CHECK(hipEventRecord(stop));
      HIP_CHECK(hipEventSynchronize(stop));
      float ms = 0.0f;
      HIP_CHECK(hipEventElapsedTime(&ms, start, stop));
      wall_ms.push_back(ms);
    }
    HIP_CHECK(hipEventDestroy(start));
    HIP_CHECK(hipEventDestroy(stop));

    float h_out = 0.0f;
    HIP_CHECK(hipMemcpy(&h_out, d_out, sizeof(float), hipMemcpyDeviceToHost));

    std::cout << std::fixed << std::setprecision(8);
    std::cout << "{\n";
    std::cout << "  \"ok\": true,\n";
    std::cout << "  \"device\": " << opt.device << ",\n";
    std::cout << "  \"device_name\": \"" << prop.name << "\",\n";
    std::cout << "  \"mode\": \"" << mode_name(opt.mode) << "\",\n";
    std::cout << "  \"blocks\": " << opt.blocks << ",\n";
    std::cout << "  \"threads\": " << opt.threads << ",\n";
    std::cout << "  \"elems\": " << opt.elems << ",\n";
    std::cout << "  \"inner_iters\": " << opt.inner_iters << ",\n";
    std::cout << "  \"lds_bytes_per_block\": "
              << (opt.mode == Mode::kLdsHeavy ? opt.threads * static_cast<int>(sizeof(float)) : 0)
              << ",\n";
    std::cout << "  \"output_sink\": " << h_out << ",\n";
    std::cout << "  \"wall_ms_mean\": " << mean(wall_ms) << "\n";
    std::cout << "}\n";

    HIP_CHECK(hipFree(d_x));
    HIP_CHECK(hipFree(d_out));
  } catch (const std::exception& ex) {
    std::cerr << "error: " << ex.what() << "\n";
    return 1;
  }
  return 0;
}
