#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

struct Args {
  std::string keys_path;
  std::string mode = "warm_lookup";
  int64_t count = -1;
  int warmup = 5;
  int iters = 100;
};

std::vector<uint64_t> read_keys(const std::string& path, int64_t count) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("failed to open keys: " + path);
  }
  input.seekg(0, std::ios::end);
  const auto bytes = input.tellg();
  input.seekg(0, std::ios::beg);
  if (bytes < 0 || static_cast<int64_t>(bytes) % static_cast<int64_t>(sizeof(uint64_t)) != 0) {
    throw std::runtime_error("invalid key binary size");
  }
  const int64_t inferred_count = static_cast<int64_t>(bytes) / static_cast<int64_t>(sizeof(uint64_t));
  if (count >= 0 && inferred_count < count) {
    throw std::runtime_error("key input shorter than requested count");
  }
  const int64_t n = count >= 0 ? count : inferred_count;
  std::vector<uint64_t> keys(static_cast<size_t>(n));
  input.read(reinterpret_cast<char*>(keys.data()), n * static_cast<int64_t>(sizeof(uint64_t)));
  if (!input) {
    throw std::runtime_error("failed to read keys");
  }
  return keys;
}

Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    const std::string key(argv[i]);
    auto value = [&](const char* name) -> std::string {
      if (i + 1 >= argc) {
        throw std::runtime_error(std::string("missing value for ") + name);
      }
      return std::string(argv[++i]);
    };
    if (key == "--keys-bin") {
      args.keys_path = value("--keys-bin");
    } else if (key == "--mode") {
      args.mode = value("--mode");
    } else if (key == "--count") {
      args.count = std::stoll(value("--count"));
    } else if (key == "--warmup") {
      args.warmup = std::stoi(value("--warmup"));
    } else if (key == "--iters") {
      args.iters = std::stoi(value("--iters"));
    } else {
      throw std::runtime_error("unknown argument: " + key);
    }
  }
  if (args.keys_path.empty() || args.warmup < 0 || args.iters <= 0) {
    throw std::runtime_error("invalid arguments");
  }
  return args;
}

double percentile(std::vector<double> values, double q) {
  if (values.empty()) {
    return 0.0;
  }
  std::sort(values.begin(), values.end());
  if (values.size() == 1) {
    return values.front();
  }
  const double position = (static_cast<double>(values.size()) - 1.0) * q;
  const auto lower = static_cast<size_t>(position);
  const auto upper = std::min(lower + 1, values.size() - 1);
  const double weight = position - static_cast<double>(lower);
  return values[lower] * (1.0 - weight) + values[upper] * weight;
}

uint64_t run_warm_lookup(const std::vector<uint64_t>& keys,
                         const std::vector<uint64_t>& unique_keys,
                         std::unordered_map<uint64_t, uint32_t>& cache) {
  cache.clear();
  cache.reserve(unique_keys.size() * 2 + 1);
  for (uint32_t i = 0; i < unique_keys.size(); ++i) {
    cache.emplace(unique_keys[i], i);
  }
  uint64_t checksum = 0;
  for (const auto key : keys) {
    auto it = cache.find(key);
    if (it != cache.end()) {
      checksum += it->second;
    }
  }
  return checksum;
}

uint64_t run_replay_insert(const std::vector<uint64_t>& keys,
                           std::unordered_map<uint64_t, uint32_t>& cache,
                           int& hits,
                           int& misses) {
  cache.clear();
  cache.reserve(keys.size() * 2 + 1);
  hits = 0;
  misses = 0;
  uint64_t checksum = 0;
  uint32_t next_value = 0;
  for (const auto key : keys) {
    auto it = cache.find(key);
    if (it != cache.end()) {
      hits += 1;
      checksum += it->second;
    } else {
      misses += 1;
      cache.emplace(key, next_value);
      checksum += next_value;
      next_value += 1;
    }
  }
  return checksum;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    const Args args = parse_args(argc, argv);
    const auto keys = read_keys(args.keys_path, args.count);
    std::unordered_set<uint64_t> unique_set(keys.begin(), keys.end());
    std::vector<uint64_t> unique_keys(unique_set.begin(), unique_set.end());
    std::sort(unique_keys.begin(), unique_keys.end());
    std::unordered_map<uint64_t, uint32_t> cache;

    uint64_t checksum = 0;
    int hits = 0;
    int misses = 0;
    for (int i = 0; i < args.warmup; ++i) {
      if (args.mode == "warm_lookup") {
        checksum += run_warm_lookup(keys, unique_keys, cache);
      } else if (args.mode == "replay_insert") {
        checksum += run_replay_insert(keys, cache, hits, misses);
      } else {
        throw std::runtime_error("unknown mode: " + args.mode);
      }
    }

    std::vector<double> times_us;
    times_us.reserve(static_cast<size_t>(args.iters));
    for (int i = 0; i < args.iters; ++i) {
      const auto start = std::chrono::high_resolution_clock::now();
      if (args.mode == "warm_lookup") {
        checksum += run_warm_lookup(keys, unique_keys, cache);
        hits = static_cast<int>(keys.size());
        misses = 0;
      } else {
        checksum += run_replay_insert(keys, cache, hits, misses);
      }
      const auto stop = std::chrono::high_resolution_clock::now();
      times_us.push_back(std::chrono::duration<double, std::micro>(stop - start).count());
    }
    const double sum = std::accumulate(times_us.begin(), times_us.end(), 0.0);
    const double mean = sum / static_cast<double>(times_us.size());
    const double median = percentile(times_us, 0.50);
    const double p10 = percentile(times_us, 0.10);
    const double p90 = percentile(times_us, 0.90);
    const auto [min_it, max_it] = std::minmax_element(times_us.begin(), times_us.end());
    const double ns_per_key = (median * 1000.0) / static_cast<double>(std::max<size_t>(1, keys.size()));

    std::cout << "{\n"
              << "  \"ok\": true,\n"
              << "  \"mode\": \"" << args.mode << "\",\n"
              << "  \"key_count\": " << keys.size() << ",\n"
              << "  \"unique_key_count\": " << unique_keys.size() << ",\n"
              << "  \"warmup\": " << args.warmup << ",\n"
              << "  \"iters\": " << args.iters << ",\n"
              << "  \"hits_last_iter\": " << hits << ",\n"
              << "  \"misses_last_iter\": " << misses << ",\n"
              << "  \"checksum\": " << checksum << ",\n"
              << "  \"lookup_us_mean\": " << mean << ",\n"
              << "  \"lookup_us_median\": " << median << ",\n"
              << "  \"lookup_us_p10\": " << p10 << ",\n"
              << "  \"lookup_us_p90\": " << p90 << ",\n"
              << "  \"lookup_us_min\": " << *min_it << ",\n"
              << "  \"lookup_us_max\": " << *max_it << ",\n"
              << "  \"ns_per_key_median\": " << ns_per_key << "\n"
              << "}\n";
    return 0;
  } catch (const std::exception& exc) {
    std::cerr << exc.what() << "\n";
    std::cout << "{\n  \"ok\": false,\n  \"error\": \"" << exc.what() << "\"\n}\n";
    return 1;
  }
}
