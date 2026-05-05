#include <hip/hip_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

enum Mode : int {
  kReactive = 0,
  kOracle = 1,
  kSpecHit = 2,
  kSpecMiss = 3,
  kMixed = 4,
  kDummyLdsStore = 5,
  kWrongNoConsume = 6,
  kGlobalNoLds = 7,
};

struct Options {
  Mode mode = kMixed;
  int device = 0;
  int requests = 4096;
  int experts = 256;
  int tile_elems = 1024;
  int block_threads = 256;
  int warmup = 10;
  int iters = 100;
  int validate_iters = 256;
  int metadata_tokens = 0;
  int compute_iters = 1;
  int interference_iters = 0;
  int interference_elems = 1 << 20;
  double miss_rate = 0.25;
  unsigned int seed = 17;
};

struct MetricsDevice {
  unsigned long long first_fma_cycles;
  unsigned long long stage_cycles;
  unsigned long long validate_cycles;
  unsigned long long metadata_wait_cycles;
  unsigned long long overwrite_cycles;
  unsigned int miss;
};

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

__device__ __forceinline__ unsigned int spin_wait(int iters, unsigned int v) {
  for (int i = 0; i < iters; ++i) {
    v = v * 1664525u + static_cast<unsigned int>(1013904223u + i);
  }
  return v;
}

__device__ __forceinline__ unsigned long long read_timer() {
  return clock64();
}

__device__ __forceinline__ unsigned long long timer_delta(unsigned long long end,
                                                          unsigned long long begin) {
  return end >= begin ? (end - begin) : 0ull;
}

__device__ __forceinline__ int align_up_int(int value, int alignment) {
  return ((value + alignment - 1) / alignment) * alignment;
}

__global__ void lds_tile_staging_kernel(
    const float* __restrict__ expert_tiles,
    const int* __restrict__ true_ids,
    const int* __restrict__ pred_ids,
    float* __restrict__ sink,
    MetricsDevice* __restrict__ metrics,
    int requests,
    int experts,
    int tile_elems,
    int mode,
    int validate_iters,
    int metadata_tokens,
    int compute_iters) {
  extern __shared__ unsigned char shared_raw[];
  float* lds = reinterpret_cast<float*>(shared_raw);
  const int tile_bytes = tile_elems * static_cast<int>(sizeof(float));
  const int counts_offset = align_up_int(tile_bytes, 16);
  int* expert_counts = reinterpret_cast<int*>(shared_raw + counts_offset);
  int* expert_offsets = expert_counts + experts;

  const int request = blockIdx.x;
  if (request >= requests) {
    return;
  }

  const int tid = threadIdx.x;
  const int true_expert = true_ids[request];
  const int pred_expert = pred_ids[request];
  unsigned int scratch = static_cast<unsigned int>(request * 131u + tid);

  const unsigned long long t0 = read_timer();
  unsigned long long t_stage = t0;
  unsigned long long t_validate = t0;
  unsigned long long t_overwrite = t0;
  float stage_register_acc = 0.0f;

  const bool reactive = (mode == kReactive);
  const bool oracle = (mode == kOracle);
  const bool dummy_lds_store = (mode == kDummyLdsStore);
  const bool wrong_no_consume = (mode == kWrongNoConsume);
  const bool global_no_lds = (mode == kGlobalNoLds);

  if (!reactive) {
    const int staged_expert = oracle ? true_expert : pred_expert;
    const float* src = expert_tiles + static_cast<size_t>(staged_expert) * tile_elems;
    if (dummy_lds_store) {
      for (int i = tid; i < tile_elems; i += blockDim.x) {
        lds[i] = static_cast<float>((i + request) & 255) * 0.00390625f;
      }
    } else if (global_no_lds) {
      for (int i = tid; i < tile_elems; i += blockDim.x) {
        stage_register_acc = fmaf(src[i], 0.0009765625f, stage_register_acc);
      }
    } else {
      for (int i = tid; i < tile_elems; i += blockDim.x) {
        lds[i] = src[i];
      }
    }
    __syncthreads();
    t_stage = read_timer();
  }

  if (metadata_tokens > 0) {
    for (int i = tid; i < experts; i += blockDim.x) {
      expert_counts[i] = 0;
      expert_offsets[i] = 0;
    }
    __syncthreads();

    for (int token = tid; token < metadata_tokens; token += blockDim.x) {
      const int expert = (true_expert + token * 17 + request * 13) & (experts - 1);
      atomicAdd(expert_counts + expert, 1);
    }
    __syncthreads();

    if (tid == 0) {
      int prefix = 0;
      for (int expert = 0; expert < experts; ++expert) {
        const int count = expert_counts[expert];
        expert_offsets[expert] = prefix;
        prefix += count;
      }
      scratch ^= static_cast<unsigned int>(prefix + expert_offsets[true_expert]);
    }
  }
  scratch = spin_wait(validate_iters, scratch);
  __syncthreads();
  t_validate = read_timer();

  const bool miss =
      dummy_lds_store || (!reactive && !oracle && pred_expert != true_expert);

  if (reactive || (miss && !wrong_no_consume && !global_no_lds)) {
    const float* src = expert_tiles + static_cast<size_t>(true_expert) * tile_elems;
    for (int i = tid; i < tile_elems; i += blockDim.x) {
      lds[i] = src[i];
    }
    __syncthreads();
    t_overwrite = read_timer();
  } else {
    t_overwrite = t_validate;
  }

  const unsigned long long t_first_fma = read_timer();

  float acc = 0.0f;
  const float* true_src = expert_tiles + static_cast<size_t>(true_expert) * tile_elems;
  const bool consume_global = wrong_no_consume || global_no_lds;
  for (int iter = 0; iter < compute_iters; ++iter) {
    const float scale = 1.0009765625f + static_cast<float>(iter & 7) * 0.0001220703125f;
    for (int i = tid; i < tile_elems; i += blockDim.x) {
      const float x = consume_global ? true_src[i] : lds[i];
      acc = fmaf(x, scale, acc);
    }
  }

  for (int offset = warpSize / 2; offset > 0; offset >>= 1) {
    acc += __shfl_down(acc, offset);
  }

  if ((tid & (warpSize - 1)) == 0) {
    atomicAdd(sink + request,
              acc + stage_register_acc + static_cast<float>(scratch & 7u) * 1.0e-7f);
  }

  if (tid == 0) {
    metrics[request].first_fma_cycles = timer_delta(t_first_fma, t0);
    metrics[request].stage_cycles = reactive ? 0ull : timer_delta(t_stage, t0);
    metrics[request].validate_cycles = timer_delta(t_validate, t0);
    metrics[request].metadata_wait_cycles =
        timer_delta(t_validate, reactive ? t0 : t_stage);
    metrics[request].overwrite_cycles =
        (reactive || miss) ? timer_delta(t_overwrite, t_validate) : 0ull;
    metrics[request].miss = miss ? 1u : 0u;
  }
}

__global__ void router_interference_kernel(
    const float* __restrict__ input,
    float* __restrict__ output,
    int elems,
    int iters) {
  const int tid = blockIdx.x * blockDim.x + threadIdx.x;
  const int stride = blockDim.x * gridDim.x;
  float acc = 0.0f;
  for (int iter = 0; iter < iters; ++iter) {
    for (int i = tid; i < elems; i += stride) {
      const int j = (i * 17 + iter * 131) & (elems - 1);
      acc = fmaf(input[j], 1.000244140625f, acc);
    }
  }
  if (tid < 1024) {
    output[tid] = acc;
  }
}

Mode parse_mode(const std::string& value) {
  if (value == "reactive") return kReactive;
  if (value == "oracle") return kOracle;
  if (value == "spec_hit") return kSpecHit;
  if (value == "spec_miss") return kSpecMiss;
  if (value == "mixed") return kMixed;
  if (value == "dummy_lds_store") return kDummyLdsStore;
  if (value == "wrong_no_consume") return kWrongNoConsume;
  if (value == "global_no_lds") return kGlobalNoLds;
  throw std::runtime_error("unknown mode: " + value);
}

const char* mode_name(Mode mode) {
  switch (mode) {
    case kReactive: return "reactive";
    case kOracle: return "oracle";
    case kSpecHit: return "spec_hit";
    case kSpecMiss: return "spec_miss";
    case kMixed: return "mixed";
    case kDummyLdsStore: return "dummy_lds_store";
    case kWrongNoConsume: return "wrong_no_consume";
    case kGlobalNoLds: return "global_no_lds";
  }
  return "unknown";
}

int parse_int(const char* value, const char* name) {
  char* end = nullptr;
  long parsed = std::strtol(value, &end, 10);
  if (!end || *end != '\0') {
    throw std::runtime_error(std::string("invalid integer for ") + name + ": " + value);
  }
  return static_cast<int>(parsed);
}

double parse_double(const char* value, const char* name) {
  char* end = nullptr;
  double parsed = std::strtod(value, &end);
  if (!end || *end != '\0') {
    throw std::runtime_error(std::string("invalid float for ") + name + ": " + value);
  }
  return parsed;
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
    if (arg == "--mode") {
      opt.mode = parse_mode(need_value("--mode"));
    } else if (arg == "--device") {
      opt.device = parse_int(need_value("--device"), "--device");
    } else if (arg == "--requests") {
      opt.requests = parse_int(need_value("--requests"), "--requests");
    } else if (arg == "--experts") {
      opt.experts = parse_int(need_value("--experts"), "--experts");
    } else if (arg == "--tile-elems") {
      opt.tile_elems = parse_int(need_value("--tile-elems"), "--tile-elems");
    } else if (arg == "--block-threads") {
      opt.block_threads = parse_int(need_value("--block-threads"), "--block-threads");
    } else if (arg == "--warmup") {
      opt.warmup = parse_int(need_value("--warmup"), "--warmup");
    } else if (arg == "--iters") {
      opt.iters = parse_int(need_value("--iters"), "--iters");
    } else if (arg == "--validate-iters") {
      opt.validate_iters = parse_int(need_value("--validate-iters"), "--validate-iters");
    } else if (arg == "--metadata-tokens") {
      opt.metadata_tokens = parse_int(need_value("--metadata-tokens"), "--metadata-tokens");
    } else if (arg == "--compute-iters") {
      opt.compute_iters = parse_int(need_value("--compute-iters"), "--compute-iters");
    } else if (arg == "--interference-iters") {
      opt.interference_iters = parse_int(
          need_value("--interference-iters"), "--interference-iters");
    } else if (arg == "--interference-elems") {
      opt.interference_elems = parse_int(
          need_value("--interference-elems"), "--interference-elems");
    } else if (arg == "--miss-rate") {
      opt.miss_rate = parse_double(need_value("--miss-rate"), "--miss-rate");
    } else if (arg == "--seed") {
      opt.seed = static_cast<unsigned int>(parse_int(need_value("--seed"), "--seed"));
    } else if (arg == "--help" || arg == "-h") {
      std::cout
          << "Usage: lds_tile_staging_bench [options]\n"
          << "  --mode reactive|oracle|spec_hit|spec_miss|mixed|dummy_lds_store|wrong_no_consume|global_no_lds\n"
          << "  --device N\n"
          << "  --requests N\n"
          << "  --experts N\n"
          << "  --tile-elems N\n"
          << "  --block-threads N\n"
          << "  --warmup N\n"
          << "  --iters N\n"
          << "  --validate-iters N\n"
          << "  --metadata-tokens N\n"
          << "  --compute-iters N\n"
          << "  --interference-iters N\n"
          << "  --interference-elems N\n"
          << "  --miss-rate F\n";
      std::exit(0);
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  return opt;
}

double mean(const std::vector<double>& xs) {
  if (xs.empty()) return 0.0;
  return std::accumulate(xs.begin(), xs.end(), 0.0) / static_cast<double>(xs.size());
}

double percentile(std::vector<double> xs, double q) {
  if (xs.empty()) return 0.0;
  std::sort(xs.begin(), xs.end());
  const double pos = q * static_cast<double>(xs.size() - 1);
  const size_t lo = static_cast<size_t>(std::floor(pos));
  const size_t hi = static_cast<size_t>(std::ceil(pos));
  const double frac = pos - static_cast<double>(lo);
  return xs[lo] * (1.0 - frac) + xs[hi] * frac;
}

void fill_inputs(const Options& opt, std::vector<float>& tiles, std::vector<int>& true_ids,
                 std::vector<int>& pred_ids) {
  tiles.resize(static_cast<size_t>(opt.experts) * opt.tile_elems);
  true_ids.resize(opt.requests);
  pred_ids.resize(opt.requests);

  for (int expert = 0; expert < opt.experts; ++expert) {
    for (int i = 0; i < opt.tile_elems; ++i) {
      const int v = (expert * 17 + i * 13) & 1023;
      tiles[static_cast<size_t>(expert) * opt.tile_elems + i] =
          static_cast<float>(v) * 0.0009765625f;
    }
  }

  unsigned int state = opt.seed;
  for (int i = 0; i < opt.requests; ++i) {
    state = state * 1664525u + 1013904223u;
    const int truth = static_cast<int>((state >> 8) % static_cast<unsigned int>(opt.experts));
    true_ids[i] = truth;

    bool miss = false;
    if (opt.mode == kSpecMiss || opt.mode == kWrongNoConsume || opt.mode == kDummyLdsStore) {
      miss = true;
    } else if (opt.mode == kMixed || opt.mode == kGlobalNoLds) {
      const double u = static_cast<double>((state >> 1) & 0x00ffffffu) /
                       static_cast<double>(0x01000000u);
      miss = u < opt.miss_rate;
    }
    pred_ids[i] = miss ? ((truth + 1 + (i % (opt.experts - 1))) % opt.experts) : truth;
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opt = parse_args(argc, argv);
    if (opt.requests <= 0 || opt.experts <= 1 || opt.tile_elems <= 0 ||
        opt.block_threads <= 0 || opt.iters <= 0 || opt.warmup < 0 ||
        opt.interference_iters < 0 || opt.interference_elems <= 0 ||
        opt.metadata_tokens < 0 || opt.compute_iters <= 0) {
      throw std::runtime_error("invalid non-positive benchmark parameter");
    }
    if ((opt.interference_elems & (opt.interference_elems - 1)) != 0) {
      throw std::runtime_error("--interference-elems must be a power of two");
    }

    HIP_CHECK(hipSetDevice(opt.device));

    hipDeviceProp_t prop{};
    HIP_CHECK(hipGetDeviceProperties(&prop, opt.device));

    const int tile_bytes = opt.tile_elems * static_cast<int>(sizeof(float));
    const int counts_offset = ((tile_bytes + 15) / 16) * 16;
    const size_t shared_bytes =
        static_cast<size_t>(counts_offset) + static_cast<size_t>(2 * opt.experts) * sizeof(int);
    if (shared_bytes > static_cast<size_t>(prop.sharedMemPerBlock)) {
      std::ostringstream oss;
      oss << "tile uses " << shared_bytes << " bytes of LDS, but device limit is "
          << prop.sharedMemPerBlock;
      throw std::runtime_error(oss.str());
    }

    std::vector<float> h_tiles;
    std::vector<int> h_true_ids;
    std::vector<int> h_pred_ids;
    fill_inputs(opt, h_tiles, h_true_ids, h_pred_ids);

    float* d_tiles = nullptr;
    int* d_true_ids = nullptr;
    int* d_pred_ids = nullptr;
    float* d_sink = nullptr;
    MetricsDevice* d_metrics = nullptr;
    float* d_interference = nullptr;
    float* d_interference_out = nullptr;

    HIP_CHECK(hipMalloc(&d_tiles, h_tiles.size() * sizeof(float)));
    HIP_CHECK(hipMalloc(&d_true_ids, h_true_ids.size() * sizeof(int)));
    HIP_CHECK(hipMalloc(&d_pred_ids, h_pred_ids.size() * sizeof(int)));
    HIP_CHECK(hipMalloc(&d_sink, static_cast<size_t>(opt.requests) * sizeof(float)));
    HIP_CHECK(hipMalloc(&d_metrics, static_cast<size_t>(opt.requests) * sizeof(MetricsDevice)));
    if (opt.interference_iters > 0) {
      HIP_CHECK(hipMalloc(&d_interference,
                          static_cast<size_t>(opt.interference_elems) * sizeof(float)));
      HIP_CHECK(hipMalloc(&d_interference_out, static_cast<size_t>(1024) * sizeof(float)));
    }

    HIP_CHECK(hipMemcpy(d_tiles, h_tiles.data(), h_tiles.size() * sizeof(float), hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(d_true_ids, h_true_ids.data(), h_true_ids.size() * sizeof(int), hipMemcpyHostToDevice));
    HIP_CHECK(hipMemcpy(d_pred_ids, h_pred_ids.data(), h_pred_ids.size() * sizeof(int), hipMemcpyHostToDevice));
    HIP_CHECK(hipMemset(d_sink, 0, static_cast<size_t>(opt.requests) * sizeof(float)));
    HIP_CHECK(hipMemset(d_metrics, 0, static_cast<size_t>(opt.requests) * sizeof(MetricsDevice)));
    if (opt.interference_iters > 0) {
      HIP_CHECK(hipMemcpy(d_interference, h_tiles.data(),
                          std::min(h_tiles.size(), static_cast<size_t>(opt.interference_elems)) *
                              sizeof(float),
                          hipMemcpyHostToDevice));
      if (static_cast<size_t>(opt.interference_elems) > h_tiles.size()) {
        HIP_CHECK(hipMemset(d_interference + h_tiles.size(), 0,
                            (static_cast<size_t>(opt.interference_elems) - h_tiles.size()) *
                                sizeof(float)));
      }
      HIP_CHECK(hipMemset(d_interference_out, 0, static_cast<size_t>(1024) * sizeof(float)));
    }

    const dim3 grid(opt.requests);
    const dim3 block(opt.block_threads);
    hipStream_t bench_stream = nullptr;
    hipStream_t interference_stream = nullptr;
    HIP_CHECK(hipStreamCreate(&bench_stream));
    HIP_CHECK(hipStreamCreate(&interference_stream));

    auto launch_interference = [&]() {
      if (opt.interference_iters <= 0) {
        return;
      }
      const int interference_blocks = std::min(1024, std::max(1, opt.requests));
      hipLaunchKernelGGL(router_interference_kernel, dim3(interference_blocks), dim3(256), 0,
                         interference_stream, d_interference, d_interference_out,
                         opt.interference_elems, opt.interference_iters);
      HIP_CHECK(hipGetLastError());
    };

    auto launch = [&]() {
      hipLaunchKernelGGL(lds_tile_staging_kernel, grid, block, shared_bytes, bench_stream, d_tiles,
                         d_true_ids, d_pred_ids, d_sink, d_metrics, opt.requests,
                         opt.experts, opt.tile_elems, static_cast<int>(opt.mode),
                         opt.validate_iters, opt.metadata_tokens, opt.compute_iters);
      HIP_CHECK(hipGetLastError());
    };

    for (int i = 0; i < opt.warmup; ++i) {
      launch_interference();
      launch();
    }
    HIP_CHECK(hipStreamSynchronize(bench_stream));
    HIP_CHECK(hipStreamSynchronize(interference_stream));

    std::vector<float> wall_ms;
    wall_ms.reserve(opt.iters);
    hipEvent_t start = nullptr;
    hipEvent_t stop = nullptr;
    HIP_CHECK(hipEventCreate(&start));
    HIP_CHECK(hipEventCreate(&stop));
    for (int i = 0; i < opt.iters; ++i) {
      launch_interference();
      HIP_CHECK(hipEventRecord(start, bench_stream));
      launch();
      HIP_CHECK(hipEventRecord(stop, bench_stream));
      HIP_CHECK(hipEventSynchronize(stop));
      float ms = 0.0f;
      HIP_CHECK(hipEventElapsedTime(&ms, start, stop));
      wall_ms.push_back(ms);
      HIP_CHECK(hipStreamSynchronize(interference_stream));
    }
    HIP_CHECK(hipEventDestroy(start));
    HIP_CHECK(hipEventDestroy(stop));

    std::vector<MetricsDevice> h_metrics(opt.requests);
    std::vector<float> h_sink(opt.requests);
    HIP_CHECK(hipMemcpy(h_metrics.data(), d_metrics,
                        static_cast<size_t>(opt.requests) * sizeof(MetricsDevice),
                        hipMemcpyDeviceToHost));
    HIP_CHECK(hipMemcpy(h_sink.data(), d_sink, static_cast<size_t>(opt.requests) * sizeof(float),
                        hipMemcpyDeviceToHost));

    std::vector<double> first_cycles;
    std::vector<double> stage_cycles;
    std::vector<double> validate_cycles;
    std::vector<double> metadata_wait_cycles;
    std::vector<double> overwrite_cycles_all;
    std::vector<double> overwrite_cycles_miss;
    first_cycles.reserve(opt.requests);
    stage_cycles.reserve(opt.requests);
    validate_cycles.reserve(opt.requests);
    metadata_wait_cycles.reserve(opt.requests);
    overwrite_cycles_all.reserve(opt.requests);

    int miss_count = 0;
    for (const auto& m : h_metrics) {
      first_cycles.push_back(static_cast<double>(m.first_fma_cycles));
      stage_cycles.push_back(static_cast<double>(m.stage_cycles));
      validate_cycles.push_back(static_cast<double>(m.validate_cycles));
      metadata_wait_cycles.push_back(static_cast<double>(m.metadata_wait_cycles));
      overwrite_cycles_all.push_back(static_cast<double>(m.overwrite_cycles));
      if (m.miss) {
        miss_count += 1;
        overwrite_cycles_miss.push_back(static_cast<double>(m.overwrite_cycles));
      }
    }
    const double sink_checksum = std::accumulate(h_sink.begin(), h_sink.end(), 0.0);
    const double clock_khz = static_cast<double>(prop.clockRate);
    auto cycles_to_us = [&](double cycles) {
      return clock_khz > 0.0 ? cycles * 1000.0 / clock_khz : 0.0;
    };

    std::cout << std::fixed << std::setprecision(6);
    std::cout << "{\n";
    std::cout << "  \"mode\": \"" << mode_name(opt.mode) << "\",\n";
    std::cout << "  \"device\": " << opt.device << ",\n";
    std::cout << "  \"device_name\": \"" << prop.name << "\",\n";
    std::cout << "  \"clock_rate_khz\": " << prop.clockRate << ",\n";
    std::cout << "  \"requests\": " << opt.requests << ",\n";
    std::cout << "  \"experts\": " << opt.experts << ",\n";
    std::cout << "  \"tile_elems\": " << opt.tile_elems << ",\n";
    std::cout << "  \"tile_bytes\": " << (opt.tile_elems * static_cast<int>(sizeof(float))) << ",\n";
    std::cout << "  \"block_threads\": " << opt.block_threads << ",\n";
    std::cout << "  \"validate_iters\": " << opt.validate_iters << ",\n";
    std::cout << "  \"metadata_tokens\": " << opt.metadata_tokens << ",\n";
    std::cout << "  \"compute_iters\": " << opt.compute_iters << ",\n";
    std::cout << "  \"interference_iters\": " << opt.interference_iters << ",\n";
    std::cout << "  \"interference_elems\": " << opt.interference_elems << ",\n";
    std::cout << "  \"configured_miss_rate\": " << opt.miss_rate << ",\n";
    std::cout << "  \"observed_miss_fraction\": "
              << (static_cast<double>(miss_count) / static_cast<double>(opt.requests)) << ",\n";
    std::cout << "  \"wall_ms_mean\": " << mean(std::vector<double>(wall_ms.begin(), wall_ms.end())) << ",\n";
    std::cout << "  \"wall_ms_p50\": " << percentile(std::vector<double>(wall_ms.begin(), wall_ms.end()), 0.50) << ",\n";
    std::cout << "  \"wall_ms_p95\": " << percentile(std::vector<double>(wall_ms.begin(), wall_ms.end()), 0.95) << ",\n";
    std::cout << "  \"first_fma_cycles_mean\": " << mean(first_cycles) << ",\n";
    std::cout << "  \"first_fma_cycles_p50\": " << percentile(first_cycles, 0.50) << ",\n";
    std::cout << "  \"first_fma_cycles_p95\": " << percentile(first_cycles, 0.95) << ",\n";
    std::cout << "  \"first_fma_us_mean_est\": " << cycles_to_us(mean(first_cycles)) << ",\n";
    std::cout << "  \"stage_cycles_mean\": " << mean(stage_cycles) << ",\n";
    std::cout << "  \"stage_cycles_p50\": " << percentile(stage_cycles, 0.50) << ",\n";
    std::cout << "  \"stage_cycles_p95\": " << percentile(stage_cycles, 0.95) << ",\n";
    std::cout << "  \"stage_us_mean_est\": " << cycles_to_us(mean(stage_cycles)) << ",\n";
    std::cout << "  \"validate_cycles_mean\": " << mean(validate_cycles) << ",\n";
    std::cout << "  \"validate_cycles_p50\": " << percentile(validate_cycles, 0.50) << ",\n";
    std::cout << "  \"validate_cycles_p95\": " << percentile(validate_cycles, 0.95) << ",\n";
    std::cout << "  \"validate_us_mean_est\": " << cycles_to_us(mean(validate_cycles)) << ",\n";
    std::cout << "  \"metadata_wait_cycles_mean\": " << mean(metadata_wait_cycles) << ",\n";
    std::cout << "  \"metadata_wait_cycles_p50\": " << percentile(metadata_wait_cycles, 0.50) << ",\n";
    std::cout << "  \"metadata_wait_cycles_p95\": " << percentile(metadata_wait_cycles, 0.95) << ",\n";
    std::cout << "  \"metadata_wait_us_mean_est\": " << cycles_to_us(mean(metadata_wait_cycles)) << ",\n";
    std::cout << "  \"overwrite_cycles_mean_all\": " << mean(overwrite_cycles_all) << ",\n";
    std::cout << "  \"overwrite_cycles_p50_all\": " << percentile(overwrite_cycles_all, 0.50) << ",\n";
    std::cout << "  \"overwrite_cycles_p95_all\": " << percentile(overwrite_cycles_all, 0.95) << ",\n";
    std::cout << "  \"overwrite_cycles_mean_miss\": " << mean(overwrite_cycles_miss) << ",\n";
    std::cout << "  \"overwrite_cycles_p50_miss\": " << percentile(overwrite_cycles_miss, 0.50) << ",\n";
    std::cout << "  \"overwrite_cycles_p95_miss\": " << percentile(overwrite_cycles_miss, 0.95) << ",\n";
    std::cout << "  \"overwrite_us_mean_miss_est\": " << cycles_to_us(mean(overwrite_cycles_miss)) << ",\n";
    std::cout << "  \"sink_checksum\": " << sink_checksum << "\n";
    std::cout << "}\n";

    HIP_CHECK(hipFree(d_tiles));
    HIP_CHECK(hipFree(d_true_ids));
    HIP_CHECK(hipFree(d_pred_ids));
    HIP_CHECK(hipFree(d_sink));
    HIP_CHECK(hipFree(d_metrics));
    if (d_interference != nullptr) HIP_CHECK(hipFree(d_interference));
    if (d_interference_out != nullptr) HIP_CHECK(hipFree(d_interference_out));
    HIP_CHECK(hipStreamDestroy(bench_stream));
    HIP_CHECK(hipStreamDestroy(interference_stream));
    return 0;
  } catch (const std::exception& ex) {
    std::cerr << "error: " << ex.what() << "\n";
    return 1;
  }
}
