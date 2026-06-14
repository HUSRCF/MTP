#pragma once

#include <cstdint>

// Future kernel-side typed consumer ABI for readonly descriptor/address prep.
// This is not the current AWQ WNA16 fused-MoE kernel argument list.  The table
// is a no-payload struct-of-arrays handle view that native canaries can consume
// before any real kernel-argument handoff exists.
struct PremapKernelSideTypedConsumerAbiV1 {
  uint64_t typed_schema_hash_hi;
  uint64_t typed_schema_hash_lo;
  const uint64_t* descriptor_ptr;
  const uint64_t* packed_weight_descriptor;
  const uint64_t* scale_metadata_handle;
  const uint64_t* aux_metadata_handle;
  const int32_t* expert_id;
  const uint64_t* address_key_hash;
  uint64_t row_order_hash;
  uint64_t ordered_row_hash;
  uint64_t lifetime_epoch;
  uint32_t row_count;
  uint32_t column_count;
};

constexpr const char* kPremapKernelSideTypedConsumerAbiV1Name =
    "premap_kernel_side_typed_consumer_abi_v1";
constexpr uint32_t kPremapKernelSideTypedConsumerAbiV1HandleColumnCount = 4;
constexpr bool kPremapKernelSideTypedConsumerAbiV1PayloadBytesAllowed = false;
constexpr bool kPremapKernelSideTypedConsumerAbiV1KernelArgPassAllowed = false;

// Producer-side transition state ABI for payload-cache issue logic.
//
// This packet is the future native/inside-graph state boundary for
// previous-token transition admission.  It is intentionally separate from the
// descriptor/address typed table and from the current WNA16 launch arguments.
// It carries only expert ids and schema/state hashes; it does not move payload
// and must not be passed to the current fused-MoE kernel as an argument.
// The Python semantic packet carries additional owner/source/lifecycle metadata;
// this native ABI is the minimal fixed-field subset a future producer adapter
// can keep inside a graph-compatible boundary.
struct PremapPayloadCacheProducerTransitionStateAbiV1 {
  uint64_t schema_hash_hi;
  uint64_t schema_hash_lo;
  const int32_t* previous_expert_id;
  const int32_t* current_expert_id;
  uint64_t state_hash;
  uint32_t previous_count;
  uint32_t current_count;
  uint32_t layer_id;
  uint32_t transition_topk_count;
};

constexpr const char* kPremapPayloadCacheProducerTransitionStateAbiV1Name =
    "premap_payload_cache_producer_transition_state_abi_v1";
constexpr uint32_t kPremapPayloadCacheProducerTransitionStateAbiV1FieldCount = 9;
constexpr bool kPremapPayloadCacheProducerTransitionStateAbiV1PayloadBytesAllowed =
    false;
constexpr bool kPremapPayloadCacheProducerTransitionStateAbiV1KernelArgPassAllowed =
    false;
constexpr bool
    kPremapPayloadCacheProducerTransitionStateAbiV1CurrentWna16ArgCompatible =
        false;
