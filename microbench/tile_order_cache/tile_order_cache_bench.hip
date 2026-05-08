#include <hip/hip_runtime.h>

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Options {
  int device = 0;
  std::string tile_ids_bin;
  std::string group_tile_ids_bin;
  std::string group_counts_bin;
  std::string group_offsets_bin;
  int tile_count = 0;
  int tile_elems = 256;
  int tiles_per_cta = 32;
  int warmup = 10;
  int iters = 50;
  int cache_flush_elems = 0;
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

__global__ void consume_order_kernel(const float* __restrict__ b_tiles,
                                     const int* __restrict__ tile_ids,
                                     float* __restrict__ sink,
                                     int tile_count,
                                     int tile_elems,
                                     int tiles_per_cta) {
  const int tid = threadIdx.x;
  const int begin = blockIdx.x * tiles_per_cta;
  const int end = min(begin + tiles_per_cta, tile_count);
  float acc = 0.0f;
  for (int pos = begin; pos < end; ++pos) {
    const int tile_id = tile_ids[pos];
    const float* tile = b_tiles + static_cast<size_t>(tile_id) * tile_elems;
    for (int i = tid; i < tile_elems; i += blockDim.x) {
      acc = fmaf(tile[i], 0.0009765625f, acc);
    }
  }
  sink[blockIdx.x * blockDim.x + tid] = acc;
}

__global__ void consume_group_plan_kernel(const float* __restrict__ b_tiles,
                                          const int* __restrict__ group_tile_ids,
                                          const int* __restrict__ group_counts,
                                          float* __restrict__ sink,
                                          int group_count,
                                          int tile_elems,
                                          int groups_per_cta) {
  const int tid = threadIdx.x;
  float acc = 0.0f;
  const int begin = blockIdx.x * groups_per_cta;
  const int end = min(begin + groups_per_cta, group_count);
  for (int group_idx = begin; group_idx < end; ++group_idx) {
    const int tile_id = group_tile_ids[group_idx];
    const int repeat_count = group_counts[group_idx];
    const float* tile = b_tiles + static_cast<size_t>(tile_id) * tile_elems;
    for (int repeat = 0; repeat < repeat_count; ++repeat) {
      for (int i = tid; i < tile_elems; i += blockDim.x) {
        acc = fmaf(tile[i], 0.0009765625f, acc);
      }
    }
  }
  sink[blockIdx.x * blockDim.x + tid] = acc;
}

__global__ void flush_kernel(float* data, int elems) {
  const int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < elems) {
    data[idx] = data[idx] * 1.000001f + 0.125f;
  }
}

std::vector<int> load_ints(const std::string& path, int expected_count, const char* label) {
  std::ifstream file(path, std::ios::binary);
  if (!file) {
    throw std::runtime_error(std::string("failed to open ") + label + " file: " + path);
  }
  file.seekg(0, std::ios::end);
  const std::streamoff bytes = file.tellg();
  file.seekg(0, std::ios::beg);
  if (bytes % static_cast<std::streamoff>(sizeof(std::int32_t)) != 0) {
    throw std::runtime_error(std::string(label) + " file size is not int32-aligned");
  }
  const int count = static_cast<int>(bytes / static_cast<std::streamoff>(sizeof(std::int32_t)));
  if (expected_count > 0 && count != expected_count) {
    throw std::runtime_error(std::string(label) + " count mismatch");
  }
  std::vector<int> values(count);
  file.read(reinterpret_cast<char*>(values.data()), bytes);
  return values;
}

Options parse_args(int argc, char** argv) {
  Options opts;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto need_value = [&](const char* name) -> const char* {
      if (i + 1 >= argc) {
        throw std::runtime_error(std::string("missing value for ") + name);
      }
      return argv[++i];
    };
    if (arg == "--device") {
      opts.device = std::atoi(need_value("--device"));
    } else if (arg == "--tile-ids-bin") {
      opts.tile_ids_bin = need_value("--tile-ids-bin");
    } else if (arg == "--group-tile-ids-bin") {
      opts.group_tile_ids_bin = need_value("--group-tile-ids-bin");
    } else if (arg == "--group-counts-bin") {
      opts.group_counts_bin = need_value("--group-counts-bin");
    } else if (arg == "--group-offsets-bin") {
      opts.group_offsets_bin = need_value("--group-offsets-bin");
    } else if (arg == "--tile-count") {
      opts.tile_count = std::atoi(need_value("--tile-count"));
    } else if (arg == "--tile-elems") {
      opts.tile_elems = std::atoi(need_value("--tile-elems"));
    } else if (arg == "--tiles-per-cta") {
      opts.tiles_per_cta = std::atoi(need_value("--tiles-per-cta"));
    } else if (arg == "--warmup") {
      opts.warmup = std::atoi(need_value("--warmup"));
    } else if (arg == "--iters") {
      opts.iters = std::atoi(need_value("--iters"));
    } else if (arg == "--cache-flush-elems") {
      opts.cache_flush_elems = std::atoi(need_value("--cache-flush-elems"));
    } else {
      throw std::runtime_error("unknown argument: " + arg);
    }
  }
  const bool materialized_mode = !opts.tile_ids_bin.empty();
  const bool group_plan_mode = !opts.group_tile_ids_bin.empty() ||
                               !opts.group_counts_bin.empty() ||
                               !opts.group_offsets_bin.empty();
  if (materialized_mode == group_plan_mode) {
    throw std::runtime_error("provide either --tile-ids-bin or group-plan inputs");
  }
  if (group_plan_mode &&
      (opts.group_tile_ids_bin.empty() || opts.group_counts_bin.empty() ||
       opts.group_offsets_bin.empty())) {
    throw std::runtime_error("group-plan mode requires tile ids, counts, and offsets");
  }
  if (opts.tile_elems <= 0 || opts.tiles_per_cta <= 0 || opts.iters <= 0) {
    throw std::runtime_error("tile_elems, tiles_per_cta, and iters must be positive");
  }
  return opts;
}

double elapsed_ms(hipEvent_t start, hipEvent_t stop) {
  float ms = 0.0f;
  HIP_CHECK(hipEventElapsedTime(&ms, start, stop));
  return static_cast<double>(ms);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Options opts = parse_args(argc, argv);
    HIP_CHECK(hipSetDevice(opts.device));
    const bool group_plan_mode = !opts.group_tile_ids_bin.empty();
    const std::vector<int> host_ids = group_plan_mode
        ? std::vector<int>()
        : load_ints(opts.tile_ids_bin, opts.tile_count, "tile id");
    const std::vector<int> host_group_tile_ids = group_plan_mode
        ? load_ints(opts.group_tile_ids_bin, -1, "group tile id")
        : std::vector<int>();
    const std::vector<int> host_group_counts = group_plan_mode
        ? load_ints(opts.group_counts_bin, static_cast<int>(host_group_tile_ids.size()),
                    "group count")
        : std::vector<int>();
    const std::vector<int> host_group_offsets = group_plan_mode
        ? load_ints(opts.group_offsets_bin, -1, "group offset")
        : std::vector<int>();
    if (group_plan_mode && host_group_offsets.empty()) {
      throw std::runtime_error("group offsets must not be empty");
    }
    if (group_plan_mode && host_group_offsets.back() != static_cast<int>(host_group_tile_ids.size())) {
      throw std::runtime_error("group offsets do not end at group count");
    }
    const int tile_count = group_plan_mode
        ? std::accumulate(host_group_counts.begin(), host_group_counts.end(), 0)
        : static_cast<int>(host_ids.size());
    const int max_tile = group_plan_mode
        ? (host_group_tile_ids.empty() ? 0 : *std::max_element(host_group_tile_ids.begin(),
                                                               host_group_tile_ids.end()))
        : (host_ids.empty() ? 0 : *std::max_element(host_ids.begin(), host_ids.end()));
    const int b_pool_tiles = max_tile + 1;
    const int block_threads = 256;
    const int group_count = static_cast<int>(host_group_tile_ids.size());
    const int window_count = group_plan_mode ? static_cast<int>(host_group_offsets.size()) - 1 : 0;
    const int num_cta = group_plan_mode
        ? (group_count + opts.tiles_per_cta - 1) / opts.tiles_per_cta
        : (tile_count + opts.tiles_per_cta - 1) / opts.tiles_per_cta;

    std::vector<float> host_b(static_cast<size_t>(b_pool_tiles) * opts.tile_elems);
    for (size_t i = 0; i < host_b.size(); ++i) {
      host_b[i] = static_cast<float>((i * 17u + 13u) & 255u) * 0.00390625f;
    }

    int* dev_ids = nullptr;
    int* dev_group_tile_ids = nullptr;
    int* dev_group_counts = nullptr;
    float* dev_b = nullptr;
    float* dev_sink = nullptr;
    float* dev_flush = nullptr;
    if (group_plan_mode) {
      HIP_CHECK(hipMalloc(&dev_group_tile_ids, sizeof(int) * host_group_tile_ids.size()));
      HIP_CHECK(hipMalloc(&dev_group_counts, sizeof(int) * host_group_counts.size()));
      HIP_CHECK(hipMemcpy(dev_group_tile_ids, host_group_tile_ids.data(),
                          sizeof(int) * host_group_tile_ids.size(), hipMemcpyHostToDevice));
      HIP_CHECK(hipMemcpy(dev_group_counts, host_group_counts.data(),
                          sizeof(int) * host_group_counts.size(), hipMemcpyHostToDevice));
    } else {
      HIP_CHECK(hipMalloc(&dev_ids, sizeof(int) * host_ids.size()));
      HIP_CHECK(hipMemcpy(dev_ids, host_ids.data(), sizeof(int) * host_ids.size(),
                          hipMemcpyHostToDevice));
    }
    HIP_CHECK(hipMalloc(&dev_b, sizeof(float) * host_b.size()));
    HIP_CHECK(hipMalloc(&dev_sink, sizeof(float) * static_cast<size_t>(num_cta) * block_threads));
    HIP_CHECK(hipMemcpy(dev_b, host_b.data(), sizeof(float) * host_b.size(), hipMemcpyHostToDevice));
    if (opts.cache_flush_elems > 0) {
      HIP_CHECK(hipMalloc(&dev_flush, sizeof(float) * static_cast<size_t>(opts.cache_flush_elems)));
      HIP_CHECK(hipMemset(dev_flush, 0, sizeof(float) * static_cast<size_t>(opts.cache_flush_elems)));
    }

    auto run_once = [&]() {
      if (dev_flush != nullptr) {
        const int flush_blocks = (opts.cache_flush_elems + block_threads - 1) / block_threads;
        hipLaunchKernelGGL(flush_kernel, dim3(flush_blocks), dim3(block_threads), 0, 0,
                           dev_flush, opts.cache_flush_elems);
      }
      if (group_plan_mode) {
        hipLaunchKernelGGL(consume_group_plan_kernel, dim3(num_cta), dim3(block_threads), 0, 0,
                           dev_b, dev_group_tile_ids, dev_group_counts, dev_sink,
                           group_count, opts.tile_elems, opts.tiles_per_cta);
      } else {
        hipLaunchKernelGGL(consume_order_kernel, dim3(num_cta), dim3(block_threads), 0, 0,
                           dev_b, dev_ids, dev_sink, tile_count, opts.tile_elems,
                           opts.tiles_per_cta);
      }
    };

    for (int i = 0; i < opts.warmup; ++i) {
      run_once();
    }
    HIP_CHECK(hipDeviceSynchronize());

    hipEvent_t start;
    hipEvent_t stop;
    HIP_CHECK(hipEventCreate(&start));
    HIP_CHECK(hipEventCreate(&stop));
    HIP_CHECK(hipEventRecord(start, 0));
    for (int i = 0; i < opts.iters; ++i) {
      run_once();
    }
    HIP_CHECK(hipEventRecord(stop, 0));
    HIP_CHECK(hipEventSynchronize(stop));
    const double total_ms = elapsed_ms(start, stop);
    const double mean_ms = total_ms / static_cast<double>(opts.iters);
    const double us_per_tile = (mean_ms * 1000.0) / static_cast<double>(tile_count);

    double checksum = 0.0;
    std::vector<float> host_sink(static_cast<size_t>(num_cta) * block_threads);
    HIP_CHECK(hipMemcpy(host_sink.data(), dev_sink, sizeof(float) * host_sink.size(), hipMemcpyDeviceToHost));
    for (float value : host_sink) {
      checksum += static_cast<double>(value);
    }

    std::cout << std::fixed << std::setprecision(9)
              << "{"
              << "\"ok\":true,"
              << "\"mode\":\"" << (group_plan_mode ? "group_plan" : "materialized") << "\","
              << "\"device\":" << opts.device << ","
              << "\"tile_count\":" << tile_count << ","
              << "\"group_count\":" << group_count << ","
              << "\"window_count\":" << window_count << ","
              << "\"unique_tiles\":" << b_pool_tiles << ","
              << "\"tile_elems\":" << opts.tile_elems << ","
              << "\"tiles_per_cta\":" << opts.tiles_per_cta << ","
              << "\"num_cta\":" << num_cta << ","
              << "\"cache_flush_elems\":" << opts.cache_flush_elems << ","
              << "\"iters\":" << opts.iters << ","
              << "\"wall_ms_mean\":" << mean_ms << ","
              << "\"us_per_tile\":" << us_per_tile << ","
              << "\"checksum\":" << checksum
              << "}" << std::endl;

    HIP_CHECK(hipEventDestroy(start));
    HIP_CHECK(hipEventDestroy(stop));
    if (dev_ids != nullptr) {
      HIP_CHECK(hipFree(dev_ids));
    }
    if (dev_group_tile_ids != nullptr) {
      HIP_CHECK(hipFree(dev_group_tile_ids));
    }
    if (dev_group_counts != nullptr) {
      HIP_CHECK(hipFree(dev_group_counts));
    }
    HIP_CHECK(hipFree(dev_b));
    HIP_CHECK(hipFree(dev_sink));
    if (dev_flush != nullptr) {
      HIP_CHECK(hipFree(dev_flush));
    }
    return 0;
  } catch (const std::exception& exc) {
    std::cerr << exc.what() << std::endl;
    return 1;
  }
}
