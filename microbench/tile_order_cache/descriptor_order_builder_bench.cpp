#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Args {
  std::string tile_ids_path;
  std::string window_ids_path;
  std::string layer_ids_path;
  std::string utility_scores_path;
  std::string prior_order_path;
  std::string mode = "bucket";
  int64_t count = -1;
  int num_tiles = 256;
  int num_layers = 40;
  int top_utility_override = 0;
  int warmup = 5;
  int iters = 50;
};

struct Scratch {
  std::vector<int> counts;
  std::vector<int> offsets;
  std::vector<int> cursors;
  std::vector<float> max_scores;
  std::vector<double> total_scores;
  std::vector<uint8_t> selected;
  std::vector<int> active;
  std::vector<int> ranked;
  std::vector<int> group_order;

  explicit Scratch(int num_tiles)
      : counts(num_tiles, 0),
        offsets(num_tiles, 0),
        cursors(num_tiles, 0),
        max_scores(num_tiles, -std::numeric_limits<float>::infinity()),
        total_scores(num_tiles, 0.0),
        selected(num_tiles, 0) {
    active.reserve(num_tiles);
    ranked.reserve(num_tiles);
    group_order.reserve(num_tiles);
  }
};

template <typename T>
std::vector<T> read_binary(const std::string& path, int64_t count) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("failed to open input: " + path);
  }
  input.seekg(0, std::ios::end);
  const auto bytes = input.tellg();
  input.seekg(0, std::ios::beg);
  if (bytes < 0 || static_cast<int64_t>(bytes) % static_cast<int64_t>(sizeof(T)) != 0) {
    throw std::runtime_error("invalid binary size: " + path);
  }
  const int64_t inferred_count = static_cast<int64_t>(bytes) / static_cast<int64_t>(sizeof(T));
  if (count >= 0 && inferred_count < count) {
    throw std::runtime_error("binary input shorter than requested count: " + path);
  }
  const int64_t n = count >= 0 ? count : inferred_count;
  std::vector<T> values(static_cast<size_t>(n));
  input.read(reinterpret_cast<char*>(values.data()), n * static_cast<int64_t>(sizeof(T)));
  if (!input) {
    throw std::runtime_error("failed to read input: " + path);
  }
  return values;
}

Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    const std::string key(argv[i]);
    auto require_value = [&](const char* name) -> std::string {
      if (i + 1 >= argc) {
        throw std::runtime_error(std::string("missing value for ") + name);
      }
      return std::string(argv[++i]);
    };
    if (key == "--tile-ids-bin") {
      args.tile_ids_path = require_value("--tile-ids-bin");
    } else if (key == "--window-ids-bin") {
      args.window_ids_path = require_value("--window-ids-bin");
    } else if (key == "--layer-ids-bin") {
      args.layer_ids_path = require_value("--layer-ids-bin");
    } else if (key == "--utility-scores-bin") {
      args.utility_scores_path = require_value("--utility-scores-bin");
    } else if (key == "--prior-order-bin") {
      args.prior_order_path = require_value("--prior-order-bin");
    } else if (key == "--mode") {
      args.mode = require_value("--mode");
    } else if (key == "--count") {
      args.count = std::stoll(require_value("--count"));
    } else if (key == "--num-tiles") {
      args.num_tiles = std::stoi(require_value("--num-tiles"));
    } else if (key == "--num-layers") {
      args.num_layers = std::stoi(require_value("--num-layers"));
    } else if (key == "--top-utility-override") {
      args.top_utility_override = std::stoi(require_value("--top-utility-override"));
    } else if (key == "--warmup") {
      args.warmup = std::stoi(require_value("--warmup"));
    } else if (key == "--iters") {
      args.iters = std::stoi(require_value("--iters"));
    } else {
      throw std::runtime_error("unknown argument: " + key);
    }
  }
  if (args.tile_ids_path.empty() || args.window_ids_path.empty() ||
      args.utility_scores_path.empty()) {
    throw std::runtime_error("tile/window/utility inputs are required");
  }
  if (args.num_tiles <= 0 || args.num_layers <= 0 || args.iters <= 0 || args.warmup < 0 ||
      args.top_utility_override < 0) {
    throw std::runtime_error("invalid num_tiles/warmup/iters");
  }
  return args;
}

int top_groups_from_mode(const std::string& mode) {
  if (mode == "linear") {
    return -2;
  }
  if (mode == "bucket") {
    return -1;
  }
  if (mode == "top16") {
    return 16;
  }
  if (mode == "top32") {
    return 32;
  }
  if (mode == "layer_prior_plan" || mode == "layer_prior_materialized") {
    return -3;
  }
  throw std::runtime_error("unknown mode: " + mode);
}

bool is_layer_prior_mode(const std::string& mode) {
  return mode == "layer_prior_plan" || mode == "layer_prior_materialized";
}

uint64_t build_order(const std::vector<int32_t>& tile_ids,
                     const std::vector<int32_t>& window_ids,
                     const std::vector<float>& utility_scores,
                     std::vector<int32_t>& output,
                     int num_tiles,
                     int top_groups,
                     Scratch& scratch) {
  const int64_t n = static_cast<int64_t>(tile_ids.size());
  if (top_groups == -2) {
    std::copy(tile_ids.begin(), tile_ids.end(), output.begin());
    return static_cast<uint64_t>(output.empty() ? 0 : output[n / 2]);
  }

  auto& counts = scratch.counts;
  auto& offsets = scratch.offsets;
  auto& cursors = scratch.cursors;
  auto& max_scores = scratch.max_scores;
  auto& total_scores = scratch.total_scores;
  auto& selected = scratch.selected;
  auto& active = scratch.active;
  auto& ranked = scratch.ranked;
  auto& group_order = scratch.group_order;

  int64_t begin = 0;
  uint64_t checksum = 0;
  while (begin < n) {
    int64_t end = begin + 1;
    while (end < n && window_ids[end] == window_ids[begin]) {
      ++end;
    }

    active.clear();
    for (int64_t i = begin; i < end; ++i) {
      const int tile = tile_ids[i];
      if (tile < 0 || tile >= num_tiles) {
        throw std::runtime_error("tile id out of range");
      }
      if (counts[tile] == 0) {
        active.push_back(tile);
        max_scores[tile] = -std::numeric_limits<float>::infinity();
        total_scores[tile] = 0.0;
      }
      counts[tile] += 1;
      const float score = utility_scores[i];
      if (score > max_scores[tile]) {
        max_scores[tile] = score;
      }
      total_scores[tile] += static_cast<double>(score);
    }

    ranked = active;
    std::sort(ranked.begin(), ranked.end(), [&](int lhs, int rhs) {
      if (max_scores[lhs] != max_scores[rhs]) {
        return max_scores[lhs] > max_scores[rhs];
      }
      if (total_scores[lhs] != total_scores[rhs]) {
        return total_scores[lhs] > total_scores[rhs];
      }
      if (counts[lhs] != counts[rhs]) {
        return counts[lhs] > counts[rhs];
      }
      return lhs < rhs;
    });

    group_order.clear();
    if (top_groups >= 0) {
      const int limit = std::min<int>(top_groups, static_cast<int>(ranked.size()));
      for (int tile : active) {
        selected[tile] = 0;
      }
      for (int i = 0; i < limit; ++i) {
        group_order.push_back(ranked[i]);
        selected[ranked[i]] = 1;
      }
      for (int tile = 0; tile < num_tiles; ++tile) {
        if (counts[tile] > 0 && !selected[tile]) {
          group_order.push_back(tile);
        }
      }
    } else {
      group_order = ranked;
    }

    int cursor = static_cast<int>(begin);
    for (int tile : group_order) {
      offsets[tile] = cursor;
      cursors[tile] = cursor;
      cursor += counts[tile];
    }
    for (int64_t i = begin; i < end; ++i) {
      const int tile = tile_ids[i];
      output[cursors[tile]++] = tile_ids[i];
    }
    if (begin < end) {
      checksum += static_cast<uint64_t>(output[begin]);
      checksum += static_cast<uint64_t>(output[end - 1]);
    }

    for (int tile : active) {
      counts[tile] = 0;
      offsets[tile] = 0;
      cursors[tile] = 0;
      max_scores[tile] = -std::numeric_limits<float>::infinity();
      total_scores[tile] = 0.0;
      selected[tile] = 0;
    }
    begin = end;
  }
  return checksum;
}

uint64_t build_layer_prior_plan(const std::vector<int32_t>& tile_ids,
                                const std::vector<int32_t>& window_ids,
                                const std::vector<int32_t>& layer_ids,
                                const std::vector<float>& utility_scores,
                                const std::vector<int32_t>& prior_order,
                                std::vector<int32_t>& output,
                                int num_tiles,
                                int num_layers,
                                int top_utility_override,
                                bool materialize,
                                Scratch& scratch) {
  const int64_t n = static_cast<int64_t>(tile_ids.size());
  auto& counts = scratch.counts;
  auto& offsets = scratch.offsets;
  auto& cursors = scratch.cursors;
  auto& max_scores = scratch.max_scores;
  auto& total_scores = scratch.total_scores;
  auto& selected = scratch.selected;
  auto& active = scratch.active;
  auto& ranked = scratch.ranked;
  auto& group_order = scratch.group_order;

  int64_t begin = 0;
  uint64_t checksum = 0;
  while (begin < n) {
    int64_t end = begin + 1;
    while (end < n && window_ids[end] == window_ids[begin]) {
      ++end;
    }

    const int layer = layer_ids[begin];
    if (layer < 0 || layer >= num_layers) {
      throw std::runtime_error("layer id out of range");
    }

    active.clear();
    for (int64_t i = begin; i < end; ++i) {
      const int tile = tile_ids[i];
      if (tile < 0 || tile >= num_tiles) {
        throw std::runtime_error("tile id out of range");
      }
      if (counts[tile] == 0) {
        active.push_back(tile);
        max_scores[tile] = -std::numeric_limits<float>::infinity();
        total_scores[tile] = 0.0;
      }
      counts[tile] += 1;
      const float score = utility_scores[i];
      if (score > max_scores[tile]) {
        max_scores[tile] = score;
      }
      total_scores[tile] += static_cast<double>(score);
    }

    group_order.clear();
    if (top_utility_override > 0) {
      ranked = active;
      std::sort(ranked.begin(), ranked.end(), [&](int lhs, int rhs) {
        if (max_scores[lhs] != max_scores[rhs]) {
          return max_scores[lhs] > max_scores[rhs];
        }
        if (total_scores[lhs] != total_scores[rhs]) {
          return total_scores[lhs] > total_scores[rhs];
        }
        if (counts[lhs] != counts[rhs]) {
          return counts[lhs] > counts[rhs];
        }
        return lhs < rhs;
      });
      const int limit = std::min<int>(top_utility_override, static_cast<int>(ranked.size()));
      for (int tile : active) {
        selected[tile] = 0;
      }
      for (int i = 0; i < limit; ++i) {
        group_order.push_back(ranked[i]);
        selected[ranked[i]] = 1;
      }
    }

    const int64_t prior_base = static_cast<int64_t>(layer) * static_cast<int64_t>(num_tiles);
    for (int i = 0; i < num_tiles; ++i) {
      const int tile = prior_order[prior_base + i];
      if (tile >= 0 && tile < num_tiles && counts[tile] > 0 && !selected[tile]) {
        group_order.push_back(tile);
        selected[tile] = 1;
      }
    }
    for (int tile = 0; tile < num_tiles; ++tile) {
      if (counts[tile] > 0 && !selected[tile]) {
        group_order.push_back(tile);
        selected[tile] = 1;
      }
    }

    int cursor = static_cast<int>(begin);
    for (int tile : group_order) {
      offsets[tile] = cursor;
      cursors[tile] = cursor;
      cursor += counts[tile];
      checksum += static_cast<uint64_t>((tile + 1) * (counts[tile] + 1));
    }

    if (materialize) {
      for (int64_t i = begin; i < end; ++i) {
        const int tile = tile_ids[i];
        output[cursors[tile]++] = tile_ids[i];
      }
      checksum += static_cast<uint64_t>(output[begin]);
      checksum += static_cast<uint64_t>(output[end - 1]);
    } else if (!group_order.empty()) {
      checksum += static_cast<uint64_t>(group_order.front());
      checksum += static_cast<uint64_t>(group_order.back());
      checksum += static_cast<uint64_t>(cursor - static_cast<int>(begin));
    }

    for (int tile : active) {
      counts[tile] = 0;
      offsets[tile] = 0;
      cursors[tile] = 0;
      max_scores[tile] = -std::numeric_limits<float>::infinity();
      total_scores[tile] = 0.0;
      selected[tile] = 0;
    }
    begin = end;
  }
  return checksum;
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

}  // namespace

int main(int argc, char** argv) {
  try {
    const Args args = parse_args(argc, argv);
    auto tile_ids = read_binary<int32_t>(args.tile_ids_path, args.count);
    auto window_ids = read_binary<int32_t>(args.window_ids_path, args.count);
    auto utility_scores = read_binary<float>(args.utility_scores_path, args.count);
    if (tile_ids.size() != window_ids.size() || tile_ids.size() != utility_scores.size()) {
      throw std::runtime_error("input lengths do not match");
    }
    std::vector<int32_t> layer_ids;
    std::vector<int32_t> prior_order;
    if (is_layer_prior_mode(args.mode)) {
      if (args.layer_ids_path.empty() || args.prior_order_path.empty()) {
        throw std::runtime_error("layer-prior mode requires layer ids and prior order inputs");
      }
      layer_ids = read_binary<int32_t>(args.layer_ids_path, args.count);
      prior_order = read_binary<int32_t>(
          args.prior_order_path,
          static_cast<int64_t>(args.num_layers) * static_cast<int64_t>(args.num_tiles));
      if (layer_ids.size() != tile_ids.size()) {
        throw std::runtime_error("layer id input length does not match tile ids");
      }
    }
    std::vector<int32_t> output(tile_ids.size(), 0);
    const int top_groups = top_groups_from_mode(args.mode);
    Scratch scratch(args.num_tiles);
    const bool layer_prior_mode = is_layer_prior_mode(args.mode);
    const bool materialize = args.mode == "layer_prior_materialized";

    uint64_t checksum = 0;
    for (int i = 0; i < args.warmup; ++i) {
      if (layer_prior_mode) {
        checksum += build_layer_prior_plan(tile_ids,
                                           window_ids,
                                           layer_ids,
                                           utility_scores,
                                           prior_order,
                                           output,
                                           args.num_tiles,
                                           args.num_layers,
                                           args.top_utility_override,
                                           materialize,
                                           scratch);
      } else {
        checksum += build_order(
            tile_ids, window_ids, utility_scores, output, args.num_tiles, top_groups, scratch);
      }
    }

    std::vector<double> times_us;
    times_us.reserve(static_cast<size_t>(args.iters));
    for (int i = 0; i < args.iters; ++i) {
      const auto start = std::chrono::high_resolution_clock::now();
      if (layer_prior_mode) {
        checksum += build_layer_prior_plan(tile_ids,
                                           window_ids,
                                           layer_ids,
                                           utility_scores,
                                           prior_order,
                                           output,
                                           args.num_tiles,
                                           args.num_layers,
                                           args.top_utility_override,
                                           materialize,
                                           scratch);
      } else {
        checksum += build_order(
            tile_ids, window_ids, utility_scores, output, args.num_tiles, top_groups, scratch);
      }
      const auto stop = std::chrono::high_resolution_clock::now();
      const double us = std::chrono::duration<double, std::micro>(stop - start).count();
      times_us.push_back(us);
    }
    const double sum = std::accumulate(times_us.begin(), times_us.end(), 0.0);
    const double mean = sum / static_cast<double>(times_us.size());
    const double median = percentile(times_us, 0.50);
    const double p10 = percentile(times_us, 0.10);
    const double p90 = percentile(times_us, 0.90);
    const auto [min_it, max_it] = std::minmax_element(times_us.begin(), times_us.end());

    std::cout << "{\n"
              << "  \"ok\": true,\n"
              << "  \"mode\": \"" << args.mode << "\",\n"
              << "  \"tile_count\": " << tile_ids.size() << ",\n"
              << "  \"num_tiles\": " << args.num_tiles << ",\n"
              << "  \"num_layers\": " << args.num_layers << ",\n"
              << "  \"top_utility_override\": " << args.top_utility_override << ",\n"
              << "  \"materialize\": " << (materialize ? "true" : "false") << ",\n"
              << "  \"warmup\": " << args.warmup << ",\n"
              << "  \"iters\": " << args.iters << ",\n"
              << "  \"checksum\": " << checksum << ",\n"
              << "  \"build_us_mean\": " << mean << ",\n"
              << "  \"build_us_median\": " << median << ",\n"
              << "  \"build_us_p10\": " << p10 << ",\n"
              << "  \"build_us_p90\": " << p90 << ",\n"
              << "  \"build_us_min\": " << *min_it << ",\n"
              << "  \"build_us_max\": " << *max_it << "\n"
              << "}\n";
    return 0;
  } catch (const std::exception& exc) {
    std::cerr << exc.what() << "\n";
    std::cout << "{\n  \"ok\": false,\n  \"error\": \"" << exc.what() << "\"\n}\n";
    return 1;
  }
}
