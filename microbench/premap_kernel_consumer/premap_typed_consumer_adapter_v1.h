#pragma once

#include <cstdint>

#include "premap_typed_consumer_abi_v1.h"

// Future kernel-side consumer adapter for the readonly typed premap ABI.
//
// The adapter is intentionally not the current AWQ WNA16 fused-MoE kernel
// launch signature.  It is a native row-view contract that a future kernel can
// consume after its ABI is updated to accept the typed descriptor/address table.
struct PremapKernelSideTypedConsumerRowV1 {
  uint64_t descriptor_ptr;
  uint64_t packed_weight_descriptor;
  uint64_t scale_metadata_handle;
  uint64_t aux_metadata_handle;
  int32_t expert_id;
  uint64_t address_key_hash;
  uint32_t row_index;
};

constexpr const char* kPremapKernelSideTypedConsumerAdapterV1Name =
    "premap_kernel_side_typed_consumer_adapter_v1";
constexpr bool kPremapKernelSideTypedConsumerAdapterV1PayloadDerefAllowed = false;
constexpr bool kPremapKernelSideTypedConsumerAdapterV1KernelArgPassAllowed = false;
constexpr const char* kPremapKernelSideTypedConsumerPathV1Name =
    "premap_kernel_side_typed_consumer_path_v1";
constexpr const char* kPremapKernelSideCompatibleConsumerAbiV1Name =
    "premap_kernel_side_compatible_consumer_abi_v1";
constexpr const char* kPremapKernelSideCompatibleConsumerAbiV1Mode =
    "readonly_kernel_side_compatible_consumer_abi";
constexpr bool kPremapKernelSideCompatibleConsumerAbiV1PayloadDerefAllowed = false;
constexpr bool kPremapKernelSideCompatibleConsumerAbiV1KernelArgPassAllowed = false;
constexpr bool kPremapKernelSideCompatibleConsumerAbiV1CurrentWna16ArgCompatible =
    false;

// A closer-to-real future kernel argument envelope.  This is still explicitly
// not the current WNA16 kernel argument list; it models the typed object a
// future descriptor/address consumer kernel would receive once its ABI grows a
// readonly premap table slot.
constexpr const char* kPremapFutureKernelSideConsumerArgsV1Name =
    "premap_future_kernel_side_consumer_args_v1";
constexpr const char* kPremapFutureKernelSideConsumerArgsV1Mode =
    "readonly_future_kernel_consumer_args";
constexpr bool kPremapFutureKernelSideConsumerArgsV1PayloadDerefAllowed =
    false;
constexpr bool kPremapFutureKernelSideConsumerArgsV1KernelArgPassAllowed =
    false;
constexpr bool kPremapFutureKernelSideConsumerArgsV1CurrentWna16ArgCompatible =
    false;
constexpr const char* kPremapFutureKernelArgsCompatibleConsumerPathV1Name =
    "premap_future_kernel_args_compatible_consumer_path_v1";
constexpr const char* kPremapFutureKernelArgsCompatibleConsumerPathV1Mode =
    "readonly_future_kernel_args_to_compatible_consumer_path";
constexpr const char* kPremapFutureKernelArgsCompatibleConsumerPathV1Source =
    "premap_future_kernel_side_consumer_args_v1";
constexpr bool
    kPremapFutureKernelArgsCompatibleConsumerPathV1PayloadDerefAllowed = false;
constexpr bool kPremapFutureKernelArgsCompatibleConsumerPathV1KernelArgPassAllowed =
    false;
constexpr bool
    kPremapFutureKernelArgsCompatibleConsumerPathV1CurrentWna16ArgCompatible =
        false;

// A standalone, future-kernel-shaped native ABI.  Unlike the compatibility path
// above, this does not call through the current launch envelope representation;
// it exposes the descriptor/address columns as the fields a future consumer
// kernel would read directly.
constexpr const char* kPremapFutureKernelNativeConsumerAbiV1Name =
    "premap_future_kernel_native_consumer_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerAbiV1Mode =
    "readonly_future_kernel_native_consumer_abi";
constexpr const char* kPremapFutureKernelNativeConsumerAbiV1Source =
    "premap_typed_handle_table_soa_fields";
constexpr bool kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed =
    false;
constexpr bool kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed =
    false;
constexpr bool kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible =
    false;
constexpr const char* kPremapFutureKernelNativeConsumerLaunchAbiV1Name =
    "premap_future_kernel_native_consumer_launch_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerLaunchAbiV1Mode =
    "readonly_future_kernel_native_consumer_launch_abi";
constexpr const char* kPremapFutureKernelNativeConsumerLaunchAbiV1Source =
    "premap_future_kernel_native_consumer_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerLaunchAbiV1Version = 1;
constexpr bool kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed =
    false;
constexpr bool kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed =
    false;
constexpr bool
    kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char* kPremapFutureKernelNativeConsumerDispatchAbiV1Name =
    "premap_future_kernel_native_consumer_dispatch_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerDispatchAbiV1Mode =
    "readonly_future_kernel_native_consumer_dispatch_abi";
constexpr const char* kPremapFutureKernelNativeConsumerDispatchAbiV1Source =
    "premap_future_kernel_native_consumer_launch_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerDispatchAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char* kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Name =
    "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Mode =
    "readonly_future_kernel_native_consumer_dispatch_ptr_abi";
constexpr const char* kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Source =
    "premap_future_kernel_native_consumer_dispatch_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchPtrAbiV1PayloadDerefAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchPtrAbiV1KernelArgPassAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerDispatchPtrAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char* kPremapFutureKernelNativeConsumerArgSlotAbiV1Name =
    "premap_future_kernel_native_consumer_arg_slot_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerArgSlotAbiV1Mode =
    "readonly_future_kernel_native_consumer_arg_slot_abi";
constexpr const char* kPremapFutureKernelNativeConsumerArgSlotAbiV1Source =
    "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerArgSlotAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerArgSlotAbiV1PayloadDerefAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerArgSlotAbiV1KernelArgPassAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerArgSlotAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char* kPremapFutureKernelNativeConsumerViewAbiV1Name =
    "premap_future_kernel_native_consumer_view_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerViewAbiV1Mode =
    "readonly_future_kernel_native_consumer_view_abi";
constexpr const char* kPremapFutureKernelNativeConsumerViewAbiV1Source =
    "premap_future_kernel_native_consumer_arg_slot_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerViewAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerViewAbiV1PayloadDerefAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerViewAbiV1KernelArgPassAllowed = false;
constexpr bool
    kPremapFutureKernelNativeConsumerViewAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char* kPremapFutureKernelNativeConsumerProgramViewAbiV1Name =
    "premap_future_kernel_native_consumer_program_view_abi_v1";
constexpr const char* kPremapFutureKernelNativeConsumerProgramViewAbiV1Mode =
    "readonly_future_kernel_native_consumer_program_view_abi";
constexpr const char* kPremapFutureKernelNativeConsumerProgramViewAbiV1Source =
    "premap_future_kernel_native_consumer_view_abi_v1";
constexpr uint32_t kPremapFutureKernelNativeConsumerProgramViewAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerProgramViewAbiV1PayloadDerefAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerProgramViewAbiV1KernelArgPassAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerProgramViewAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char*
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Name =
        "premap_future_kernel_native_consumer_program_view_ptr_abi_v1";
constexpr const char*
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Mode =
        "readonly_future_kernel_native_consumer_program_view_ptr_abi";
constexpr const char*
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Source =
        "premap_future_kernel_native_consumer_program_view_abi_v1";
constexpr uint32_t
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1PayloadDerefAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1KernelArgPassAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char*
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Name =
        "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1";
constexpr const char*
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Mode =
        "readonly_future_kernel_native_consumer_kernel_arg_packet_abi";
constexpr const char*
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Source =
        "premap_future_kernel_native_consumer_program_view_ptr_abi_v1";
constexpr uint32_t
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1PayloadDerefAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1KernelArgPassAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char*
    kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Name =
        "premap_future_kernel_native_consumer_kernel_entry_summary_abi_v1";
constexpr uint32_t
    kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1PayloadDerefAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1KernelArgPassAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1CurrentWna16ArgCompatible =
        false;
constexpr const char*
    kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1Name =
        "premap_future_kernel_native_consumer_kernel_entry_args_abi_v1";
constexpr uint32_t
    kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1Version = 1;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1PayloadDerefAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1KernelArgPassAllowed =
        false;
constexpr bool
    kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1CurrentWna16ArgCompatible =
        false;

constexpr uint32_t kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag = 1u << 0;
constexpr uint32_t
    kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag = 1u << 1;
constexpr uint32_t
    kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag = 1u << 2;
constexpr uint32_t kPremapFutureKernelSideConsumerArgsV1RequiredFlags =
    kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag |
    kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag |
    kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag;

constexpr uint32_t kPremapFutureKernelSideConsumerFieldNone = 0;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldDescriptorPtr = 1;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor = 2;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldScaleMetadataHandle = 3;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldAuxMetadataHandle = 4;

constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr =
    1u << 0;
constexpr uint32_t
    kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor = 1u << 1;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle =
    1u << 2;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle =
    1u << 3;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskRequired =
    kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr |
    kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor |
    kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle;
constexpr uint32_t kPremapFutureKernelSideConsumerFieldMaskAll =
    kPremapFutureKernelSideConsumerFieldMaskRequired |
    kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle;

struct PremapKernelSideTypedConsumerLaunchEnvelopeV1 {
  PremapKernelSideTypedConsumerAbiV1 table;
  uint64_t expected_schema_hash_hi;
  uint64_t expected_schema_hash_lo;
  uint64_t expected_row_order_hash;
  uint64_t expected_ordered_row_hash;
  uint32_t expected_row_count;
  uint32_t expected_column_count;
  uint32_t payload_bytes;
  uint32_t flags;
};

struct PremapFutureKernelSideConsumerArgsV1 {
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope;
  uint32_t field_mask;
  uint32_t single_field_mirror_kind;
  uint32_t payload_bytes;
  uint32_t flags;
};

struct PremapFutureKernelNativeConsumerParamsV1 {
  const uint64_t* descriptor_ptr;
  const uint64_t* packed_weight_descriptor;
  const uint64_t* scale_metadata_handle;
  const uint64_t* aux_metadata_handle;
  const int32_t* expert_id;
  const uint64_t* address_key_hash;
  uint64_t typed_schema_hash_hi;
  uint64_t typed_schema_hash_lo;
  uint64_t row_order_hash;
  uint64_t ordered_row_hash;
  uint32_t row_count;
  uint32_t column_count;
  uint32_t lifetime_epoch;
  uint32_t field_mask;
  uint32_t single_field_mirror_kind;
  uint32_t payload_bytes;
  uint32_t flags;
};

// A launch-shaped wrapper around the standalone native consumer params. This
// mirrors the object a future kernel launch would receive after a real ABI slot
// exists, but remains independent from the current WNA16 argument list.
struct PremapFutureKernelNativeConsumerLaunchV1 {
  PremapFutureKernelNativeConsumerParamsV1 params;
  uint32_t abi_version;
  uint32_t params_struct_size;
  uint32_t result_struct_size;
  uint32_t row_stride;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Dispatch-shaped readonly wrapper.  This is the closest native stub to a
// future launch site: it carries the launch ABI plus row-window and launch-shape
// metadata a real kernel-side consumer would see, while still avoiding payload
// dereference and current WNA16 kernel-argument mutation.
struct PremapFutureKernelNativeConsumerDispatchV1 {
  PremapFutureKernelNativeConsumerLaunchV1 launch;
  uint32_t dispatch_version;
  uint32_t grid_x;
  uint32_t block_x;
  uint32_t shared_mem_bytes;
  uint32_t row_offset;
  uint32_t row_limit;
  uint32_t rows_per_program;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Pointer-backed future kernel argument packet.  A real kernel-side consumer is
// expected to receive a compact argument slot that points at launch/dispatch
// metadata rather than having host-side Python rebuild row tuples.  This still
// forbids payload dereference and current WNA16 argument mutation.
struct PremapFutureKernelNativeConsumerDispatchPtrV1 {
  const PremapFutureKernelNativeConsumerDispatchV1* dispatch;
  uint32_t abi_version;
  uint32_t dispatch_struct_size;
  uint32_t result_struct_size;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Future kernel argument slot.  This models the compact argument packet a
// future kernel would receive: the slot points at a dispatch pointer packet,
// which points at dispatch metadata, which points at the typed handle table.
// It is intentionally not the current WNA16 fused-MoE kernel argument list.
struct PremapFutureKernelNativeConsumerArgSlotV1 {
  const PremapFutureKernelNativeConsumerDispatchPtrV1* dispatch_ptr;
  uint32_t abi_version;
  uint32_t dispatch_ptr_struct_size;
  uint32_t result_struct_size;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Device-side row view produced after decoding the future arg slot.  A future
// kernel would typically unpack a compact launch argument into a view like this
// before iterating rows.  It remains readonly and is not the current WNA16
// fused-MoE kernel argument list.
struct PremapFutureKernelNativeConsumerViewV1 {
  PremapFutureKernelNativeConsumerParamsV1 params;
  uint32_t abi_version;
  uint32_t source_packet_chain_depth;
  uint32_t row_offset;
  uint32_t row_limit;
  uint32_t rows_per_program;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Program/lane-level readonly view a future kernel-side consumer would iterate.
// This is intentionally downstream from the decoded view and upstream of a real
// WNA16 replacement.  It proves the future ABI can express grid/program row
// assignment without passing or mutating current kernel arguments.
struct PremapFutureKernelNativeConsumerProgramViewV1 {
  PremapFutureKernelNativeConsumerViewV1 view;
  uint32_t abi_version;
  uint32_t program_count;
  uint32_t full_program_count;
  uint32_t last_program_active_rows;
  uint32_t inactive_lane_count;
  uint32_t first_program_row_offset;
  uint32_t last_program_row_offset;
  uint64_t program_iteration_hash;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Pointer-backed packet for the program/lane-level view.  This is closer to a
// real kernel argument than the by-value diagnostic view above: a future kernel
// would receive one compact pointer packet, then load the readonly program-view
// object before assigning rows to lanes.
struct PremapFutureKernelNativeConsumerProgramViewPtrV1 {
  const PremapFutureKernelNativeConsumerProgramViewV1* program_view;
  uint32_t abi_version;
  uint32_t program_view_struct_size;
  uint32_t result_struct_size;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Future kernel argument packet.  This is the closest readonly ABI shape in
// this stub: a future kernel would receive this compact packet, load the
// pointer-backed program-view packet, then iterate rows.  It is deliberately
// not passed to the current WNA16 fused-MoE kernel.
struct PremapFutureKernelNativeConsumerKernelArgPacketV1 {
  const PremapFutureKernelNativeConsumerProgramViewPtrV1* program_view_ptr;
  uint32_t abi_version;
  uint32_t program_view_ptr_struct_size;
  uint32_t result_struct_size;
  uint32_t payload_bytes;
  uint32_t flags;
};

// Compact readonly summary produced by a future-kernel-shaped entry stub.  The
// entry stub receives only the future kernel-arg packet plus this summary
// pointer, then walks the packet chain and typed rows internally.  It is still
// not the current WNA16 argument list and it does not move payload bytes.
struct PremapFutureKernelNativeConsumerKernelEntrySummaryV1 {
  uint32_t abi_version;
  uint32_t packet_valid;
  uint32_t row_count;
  uint32_t row_ok_count;
  uint32_t descriptor_ptr_read_ok_count;
  uint32_t packed_weight_descriptor_read_ok_count;
  uint32_t scale_metadata_handle_read_ok_count;
  uint32_t aux_metadata_handle_read_ok_count;
  uint32_t error_count;
  uint32_t field_mask;
  uint32_t payload_bytes;
  uint32_t passed_to_kernel;
  uint32_t changes_kernel_launch_args;
  uint32_t current_wna16_arg_compatible;
  uint32_t requires_wna16_arg_reinterpretation;
  uint32_t reserved;
  uint64_t row_hash_accumulator;
  uint64_t field_read_hash_accumulator;
};

// Single-argument future kernel entry envelope.  This models the ABI shape a
// future descriptor/address consumer kernel would receive at launch: one
// compact argument object that points to the readonly kernel-arg packet and a
// diagnostics/status summary.  It is still not the current WNA16 kernel
// argument list and does not authorize payload movement.
struct PremapFutureKernelNativeConsumerKernelEntryArgsV1 {
  const PremapFutureKernelNativeConsumerKernelArgPacketV1* kernel_arg_packet;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1* summary;
  uint32_t abi_version;
  uint32_t kernel_arg_packet_struct_size;
  uint32_t summary_struct_size;
  uint32_t payload_bytes;
  uint32_t flags;
};

constexpr const char* kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name =
    "premap_kernel_side_typed_consumer_launch_envelope_v1";
constexpr uint32_t kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag =
    1u << 0;
constexpr uint32_t
    kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag =
        1u << 1;

struct PremapKernelSideTypedConsumerPathResultV1 {
  uint32_t ok;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapKernelSideCompatibleConsumerResultV1 {
  uint32_t ok;
  uint32_t envelope_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelSideConsumerResultV1 {
  uint32_t ok;
  uint32_t args_valid;
  uint32_t envelope_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

struct PremapFutureKernelArgsCompatibleConsumerPathResultV1 {
  uint32_t ok;
  uint32_t args_valid;
  uint32_t compatible_consumer_ok;
  uint32_t envelope_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelNativeConsumerResultV1 {
  uint32_t ok;
  uint32_t params_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

struct PremapFutureKernelNativeConsumerLaunchResultV1 {
  uint32_t ok;
  uint32_t launch_valid;
  uint32_t native_consumer_ok;
  uint32_t params_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

struct PremapFutureKernelNativeConsumerDispatchResultV1 {
  uint32_t ok;
  uint32_t dispatch_valid;
  uint32_t launch_geometry_valid;
  uint32_t launch_consumer_ok;
  uint32_t launch_valid;
  uint32_t row_window_valid;
  uint32_t active_rows;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t single_field_mirror_checked;
  uint32_t single_field_mirror_ok;
  uint32_t single_field_mirror_kind;
  uint32_t field_count;
  uint64_t row_hash;
  uint64_t single_field_mirror_hash;
};

using PremapFutureKernelNativeConsumerArgSlotResultV1 =
    PremapFutureKernelNativeConsumerDispatchResultV1;

struct PremapFutureKernelNativeConsumerViewResultV1 {
  uint32_t ok;
  uint32_t view_valid;
  uint32_t launch_geometry_valid;
  uint32_t row_window_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t all_handle_fields_read;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelNativeConsumerProgramViewResultV1 {
  uint32_t ok;
  uint32_t program_view_valid;
  uint32_t view_valid;
  uint32_t launch_geometry_valid;
  uint32_t row_window_valid;
  uint32_t program_iteration_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t all_handle_fields_read;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelNativeConsumerProgramViewPtrResultV1 {
  uint32_t ok;
  uint32_t packet_valid;
  uint32_t program_view_valid;
  uint32_t view_valid;
  uint32_t launch_geometry_valid;
  uint32_t row_window_valid;
  uint32_t program_iteration_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t all_handle_fields_read;
  uint32_t field_count;
  uint64_t row_hash;
};

struct PremapFutureKernelNativeConsumerKernelArgPacketResultV1 {
  uint32_t ok;
  uint32_t packet_valid;
  uint32_t program_view_ptr_valid;
  uint32_t program_view_valid;
  uint32_t view_valid;
  uint32_t launch_geometry_valid;
  uint32_t row_window_valid;
  uint32_t program_iteration_valid;
  uint32_t row_valid;
  uint32_t required_handle_visible;
  uint32_t lifetime_valid;
  uint32_t all_handle_fields_read;
  uint32_t field_count;
  uint64_t row_hash;
};

__host__ __device__ static inline uint64_t
premap_typed_consumer_mix64_v1(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 33;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 33;
  return x;
}

__host__ __device__ static inline bool
premap_typed_consumer_schema_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return table.typed_schema_hash_hi == expected_schema_hash_hi &&
         table.typed_schema_hash_lo == expected_schema_hash_lo &&
         table.column_count == kPremapKernelSideTypedConsumerAbiV1HandleColumnCount &&
         table.row_count > 0 && table.descriptor_ptr != nullptr &&
         table.packed_weight_descriptor != nullptr &&
         table.scale_metadata_handle != nullptr && table.expert_id != nullptr &&
         table.address_key_hash != nullptr;
}

__host__ __device__ static inline bool
premap_typed_consumer_launch_envelope_matches_v1(
    const PremapKernelSideTypedConsumerLaunchEnvelopeV1& envelope) {
  return premap_typed_consumer_schema_matches_v1(
             envelope.table,
             envelope.expected_schema_hash_hi,
             envelope.expected_schema_hash_lo) &&
         envelope.table.row_count == envelope.expected_row_count &&
         envelope.table.column_count == envelope.expected_column_count &&
         envelope.table.row_order_hash == envelope.expected_row_order_hash &&
         envelope.table.ordered_row_hash == envelope.expected_ordered_row_hash &&
         envelope.payload_bytes == 0 &&
         (envelope.flags &
          kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag) != 0 &&
         (envelope.flags &
          kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag) !=
             0;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_kernel_args_match_v1(
    const PremapFutureKernelSideConsumerArgsV1& args) {
  return premap_typed_consumer_launch_envelope_matches_v1(args.envelope) &&
         args.payload_bytes == 0 &&
         (args.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (args.flags &
         kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (args.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         args.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         (args.field_mask & ~kPremapFutureKernelSideConsumerFieldMaskAll) == 0 &&
         (args.field_mask & kPremapFutureKernelSideConsumerFieldMaskRequired) ==
             kPremapFutureKernelSideConsumerFieldMaskRequired &&
         !kPremapFutureKernelSideConsumerArgsV1PayloadDerefAllowed &&
         !kPremapFutureKernelSideConsumerArgsV1KernelArgPassAllowed &&
         !kPremapFutureKernelSideConsumerArgsV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_params_match_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return params.typed_schema_hash_hi == expected_schema_hash_hi &&
         params.typed_schema_hash_lo == expected_schema_hash_lo &&
         params.column_count == kPremapKernelSideTypedConsumerAbiV1HandleColumnCount &&
         params.row_count > 0 && params.descriptor_ptr != nullptr &&
         params.packed_weight_descriptor != nullptr &&
         params.scale_metadata_handle != nullptr && params.expert_id != nullptr &&
         params.address_key_hash != nullptr && params.lifetime_epoch == 1 &&
         params.payload_bytes == 0 &&
         (params.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (params.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (params.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         params.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         (params.field_mask & ~kPremapFutureKernelSideConsumerFieldMaskAll) == 0 &&
         (params.field_mask & kPremapFutureKernelSideConsumerFieldMaskRequired) ==
             kPremapFutureKernelSideConsumerFieldMaskRequired &&
         !kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_launch_matches_v1(
    const PremapFutureKernelNativeConsumerLaunchV1& launch,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return premap_typed_consumer_future_native_params_match_v1(
             launch.params,
             expected_schema_hash_hi,
             expected_schema_hash_lo) &&
         launch.abi_version ==
             kPremapFutureKernelNativeConsumerLaunchAbiV1Version &&
         launch.params_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerParamsV1) &&
         launch.result_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerLaunchResultV1) &&
         launch.row_stride == 1 && launch.payload_bytes == 0 &&
         (launch.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (launch.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (launch.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         launch.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_dispatch_matches_v1(
    const PremapFutureKernelNativeConsumerDispatchV1& dispatch,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  const bool row_window_valid =
      dispatch.row_offset <= dispatch.launch.params.row_count &&
      dispatch.row_limit <= dispatch.launch.params.row_count &&
      dispatch.row_offset < dispatch.row_limit;
  const uint32_t active_rows =
      row_window_valid ? (dispatch.row_limit - dispatch.row_offset) : 0;
  const uint64_t launched_threads =
      static_cast<uint64_t>(dispatch.grid_x) *
      static_cast<uint64_t>(dispatch.block_x);
  const uint64_t previous_grid_threads =
      dispatch.grid_x > 0
          ? static_cast<uint64_t>(dispatch.grid_x - 1) *
                static_cast<uint64_t>(dispatch.block_x)
          : 0;
  return premap_typed_consumer_future_native_launch_matches_v1(
             dispatch.launch,
             expected_schema_hash_hi,
             expected_schema_hash_lo) &&
         dispatch.dispatch_version ==
             kPremapFutureKernelNativeConsumerDispatchAbiV1Version &&
         dispatch.grid_x > 0 && dispatch.block_x > 0 &&
         row_window_valid && active_rows > 0 &&
         launched_threads >= static_cast<uint64_t>(active_rows) &&
         previous_grid_threads < static_cast<uint64_t>(active_rows) &&
         dispatch.rows_per_program == dispatch.block_x &&
         dispatch.payload_bytes == 0 &&
         (dispatch.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (dispatch.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (dispatch.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         dispatch.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline bool
premap_typed_consumer_future_native_dispatch_ptr_packet_matches_v1(
    const PremapFutureKernelNativeConsumerDispatchPtrV1& dispatch_ptr) {
  return dispatch_ptr.dispatch != nullptr &&
         dispatch_ptr.abi_version ==
             kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Version &&
         dispatch_ptr.dispatch_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerDispatchV1) &&
         dispatch_ptr.result_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerDispatchResultV1) &&
         dispatch_ptr.payload_bytes == 0 &&
         (dispatch_ptr.flags &
          kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (dispatch_ptr.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (dispatch_ptr.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         dispatch_ptr.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline bool
premap_typed_consumer_future_native_arg_slot_packet_matches_v1(
    const PremapFutureKernelNativeConsumerArgSlotV1& arg_slot) {
  return arg_slot.dispatch_ptr != nullptr &&
         arg_slot.abi_version ==
             kPremapFutureKernelNativeConsumerArgSlotAbiV1Version &&
         arg_slot.dispatch_ptr_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerDispatchPtrV1) &&
         arg_slot.result_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerArgSlotResultV1) &&
         arg_slot.payload_bytes == 0 &&
         (arg_slot.flags &
          kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (arg_slot.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (arg_slot.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         arg_slot.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerArgSlotAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerArgSlotAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerArgSlotAbiV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_view_matches_v1(
    const PremapFutureKernelNativeConsumerViewV1& view,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  const bool row_window_valid =
      view.row_offset <= view.params.row_count &&
      view.row_limit <= view.params.row_count &&
      view.row_offset < view.row_limit;
  return premap_typed_consumer_future_native_params_match_v1(
             view.params, expected_schema_hash_hi, expected_schema_hash_lo) &&
         view.abi_version ==
             kPremapFutureKernelNativeConsumerViewAbiV1Version &&
         view.source_packet_chain_depth == 3 && row_window_valid &&
         view.rows_per_program > 0 && view.payload_bytes == 0 &&
         (view.flags & kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (view.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (view.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         view.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerViewAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerViewAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerViewAbiV1CurrentWna16ArgCompatible;
}

__host__ __device__ static inline uint64_t
premap_typed_consumer_program_iteration_hash_v1(
    uint32_t program_count,
    uint32_t rows_per_program,
    uint32_t row_offset,
    uint32_t row_limit,
    uint32_t last_program_active_rows,
    uint32_t inactive_lane_count) {
  return premap_typed_consumer_mix64_v1(
             static_cast<uint64_t>(program_count) + 0xd15c2001ULL) ^
         premap_typed_consumer_mix64_v1(
             static_cast<uint64_t>(rows_per_program) + 0xd15c2002ULL) ^
         premap_typed_consumer_mix64_v1(
             static_cast<uint64_t>(row_offset) + 0xd15c2003ULL) ^
         premap_typed_consumer_mix64_v1(
             static_cast<uint64_t>(row_limit) + 0xd15c2004ULL) ^
         premap_typed_consumer_mix64_v1(
             static_cast<uint64_t>(last_program_active_rows) + 0xd15c2005ULL) ^
         premap_typed_consumer_mix64_v1(
             static_cast<uint64_t>(inactive_lane_count) + 0xd15c2006ULL);
}

__host__ __device__ static inline bool
premap_typed_consumer_future_native_program_view_matches_v1(
    const PremapFutureKernelNativeConsumerProgramViewV1& program_view,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  const PremapFutureKernelNativeConsumerViewV1& view = program_view.view;
  const bool view_valid =
      premap_typed_consumer_future_native_view_matches_v1(
          view, expected_schema_hash_hi, expected_schema_hash_lo);
  const bool row_window_valid =
      view.row_offset <= view.params.row_count &&
      view.row_limit <= view.params.row_count &&
      view.row_offset < view.row_limit &&
      view.rows_per_program > 0;
  const uint32_t active_rows =
      row_window_valid ? view.row_limit - view.row_offset : 0;
  const uint64_t launched_lanes =
      static_cast<uint64_t>(program_view.program_count) *
      static_cast<uint64_t>(view.rows_per_program);
  const uint64_t previous_program_lanes =
      program_view.program_count > 0
          ? static_cast<uint64_t>(program_view.program_count - 1) *
                static_cast<uint64_t>(view.rows_per_program)
          : 0ULL;
  const uint32_t expected_full_program_count =
      row_window_valid
          ? static_cast<uint32_t>(
                static_cast<uint64_t>(active_rows) /
                static_cast<uint64_t>(view.rows_per_program))
          : 0;
  const uint32_t expected_last_program_active_rows =
      row_window_valid && active_rows > 0
          ? static_cast<uint32_t>(
                static_cast<uint64_t>(active_rows) - previous_program_lanes)
          : 0;
  const uint32_t expected_inactive_lane_count =
      launched_lanes >= static_cast<uint64_t>(active_rows)
          ? static_cast<uint32_t>(
                launched_lanes - static_cast<uint64_t>(active_rows))
          : 0;
  const uint32_t expected_first_program_row_offset = view.row_offset;
  const uint32_t expected_last_program_row_offset =
      static_cast<uint32_t>(
          static_cast<uint64_t>(view.row_offset) + previous_program_lanes);
  const uint64_t expected_program_iteration_hash =
      premap_typed_consumer_program_iteration_hash_v1(
          program_view.program_count,
          view.rows_per_program,
          view.row_offset,
          view.row_limit,
          expected_last_program_active_rows,
          expected_inactive_lane_count);
  return view_valid &&
         program_view.abi_version ==
             kPremapFutureKernelNativeConsumerProgramViewAbiV1Version &&
         row_window_valid && active_rows > 0 && program_view.program_count > 0 &&
         launched_lanes >= static_cast<uint64_t>(active_rows) &&
         previous_program_lanes < static_cast<uint64_t>(active_rows) &&
         program_view.full_program_count == expected_full_program_count &&
         program_view.last_program_active_rows ==
             expected_last_program_active_rows &&
         program_view.inactive_lane_count == expected_inactive_lane_count &&
         program_view.first_program_row_offset ==
             expected_first_program_row_offset &&
         program_view.last_program_row_offset ==
             expected_last_program_row_offset &&
         program_view.program_iteration_hash == expected_program_iteration_hash &&
         program_view.payload_bytes == 0 &&
         (program_view.flags &
          kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (program_view.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (program_view.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         program_view.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerProgramViewAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerProgramViewAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerProgramViewAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline bool
premap_typed_consumer_future_native_program_view_ptr_packet_matches_v1(
    const PremapFutureKernelNativeConsumerProgramViewPtrV1& program_view_ptr) {
  return program_view_ptr.program_view != nullptr &&
         program_view_ptr.abi_version ==
             kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Version &&
         program_view_ptr.program_view_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerProgramViewV1) &&
         program_view_ptr.result_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerProgramViewPtrResultV1) &&
         program_view_ptr.payload_bytes == 0 &&
         (program_view_ptr.flags &
          kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (program_view_ptr.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (program_view_ptr.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         program_view_ptr.flags ==
             kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline bool
premap_typed_consumer_future_native_kernel_arg_packet_matches_v1(
    const PremapFutureKernelNativeConsumerKernelArgPacketV1& kernel_arg_packet) {
  return kernel_arg_packet.program_view_ptr != nullptr &&
         kernel_arg_packet.abi_version ==
             kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Version &&
         kernel_arg_packet.program_view_ptr_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerProgramViewPtrV1) &&
         kernel_arg_packet.result_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerKernelArgPacketResultV1) &&
         kernel_arg_packet.payload_bytes == 0 &&
         (kernel_arg_packet.flags &
          kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (kernel_arg_packet.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (kernel_arg_packet.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         kernel_arg_packet.flags ==
             kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline bool
premap_typed_consumer_future_native_kernel_entry_args_matches_v1(
    const PremapFutureKernelNativeConsumerKernelEntryArgsV1& entry_args) {
  return entry_args.kernel_arg_packet != nullptr && entry_args.summary != nullptr &&
         entry_args.abi_version ==
             kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1Version &&
         entry_args.kernel_arg_packet_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1) &&
         entry_args.summary_struct_size ==
             sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1) &&
         entry_args.payload_bytes == 0 &&
         (entry_args.flags &
          kPremapFutureKernelSideConsumerArgsV1ReadonlyFlag) != 0 &&
         (entry_args.flags &
          kPremapFutureKernelSideConsumerArgsV1KernelArgPassDisabledFlag) != 0 &&
         (entry_args.flags &
          kPremapFutureKernelSideConsumerArgsV1PayloadDerefDisabledFlag) != 0 &&
         entry_args.flags == kPremapFutureKernelSideConsumerArgsV1RequiredFlags &&
         !kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1PayloadDerefAllowed &&
         !kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1KernelArgPassAllowed &&
         !kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1CurrentWna16ArgCompatible;
}

__device__ static inline bool
premap_typed_consumer_future_native_dispatch_ptr_matches_v1(
    const PremapFutureKernelNativeConsumerDispatchPtrV1& dispatch_ptr,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  return premap_typed_consumer_future_native_dispatch_ptr_packet_matches_v1(
             dispatch_ptr) &&
         premap_typed_consumer_future_native_dispatch_matches_v1(
             *dispatch_ptr.dispatch,
             expected_schema_hash_hi,
             expected_schema_hash_lo);
}

__device__ static inline PremapKernelSideTypedConsumerRowV1
premap_typed_consumer_load_row_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    uint32_t row_index) {
  PremapKernelSideTypedConsumerRowV1 row;
  row.descriptor_ptr = table.descriptor_ptr[row_index];
  row.packed_weight_descriptor = table.packed_weight_descriptor[row_index];
  row.scale_metadata_handle = table.scale_metadata_handle[row_index];
  row.aux_metadata_handle =
      table.aux_metadata_handle == nullptr ? 0ULL : table.aux_metadata_handle[row_index];
  row.expert_id = table.expert_id[row_index];
  row.address_key_hash = table.address_key_hash[row_index];
  row.row_index = row_index;
  return row;
}

__device__ static inline PremapKernelSideTypedConsumerRowV1
premap_typed_consumer_load_future_native_row_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint32_t row_index) {
  PremapKernelSideTypedConsumerRowV1 row;
  row.descriptor_ptr = params.descriptor_ptr[row_index];
  row.packed_weight_descriptor = params.packed_weight_descriptor[row_index];
  row.scale_metadata_handle = params.scale_metadata_handle[row_index];
  row.aux_metadata_handle =
      params.aux_metadata_handle == nullptr ? 0ULL : params.aux_metadata_handle[row_index];
  row.expert_id = params.expert_id[row_index];
  row.address_key_hash = params.address_key_hash[row_index];
  row.row_index = row_index;
  return row;
}

__device__ static inline uint32_t
premap_typed_consumer_required_handles_visible_v1(
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      row.descriptor_ptr != 0 && row.packed_weight_descriptor != 0 &&
      row.scale_metadata_handle != 0);
}

__device__ static inline uint32_t
premap_typed_consumer_descriptor_ptr_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.descriptor_ptr != nullptr && row.descriptor_ptr != 0 &&
      row.descriptor_ptr == table.descriptor_ptr[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_scale_metadata_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.scale_metadata_handle != nullptr && row.scale_metadata_handle != 0 &&
      row.scale_metadata_handle == table.scale_metadata_handle[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_packed_weight_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.packed_weight_descriptor != nullptr &&
      row.packed_weight_descriptor != 0 &&
      row.packed_weight_descriptor == table.packed_weight_descriptor[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_aux_metadata_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.aux_metadata_handle != nullptr && row.aux_metadata_handle != 0 &&
      row.aux_metadata_handle == table.aux_metadata_handle[row.row_index]);
}

__device__ static inline uint32_t
premap_typed_consumer_lifetime_valid_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      table.lifetime_epoch == 1 && row.address_key_hash != 0 && row.expert_id >= 0);
}

__device__ static inline PremapKernelSideTypedConsumerPathResultV1
premap_typed_consumer_kernel_side_consume_row_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    uint32_t row_index) {
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(table, row_index);
  PremapKernelSideTypedConsumerPathResultV1 result;
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid = premap_typed_consumer_lifetime_valid_v1(table, row);
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.ok = static_cast<uint32_t>(
      result.required_handle_visible != 0 && result.lifetime_valid != 0 &&
      row_index < table.row_count &&
      table.column_count == kPremapKernelSideTypedConsumerAbiV1HandleColumnCount);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr) ^
      premap_typed_consumer_mix64_v1(row.packed_weight_descriptor + 0x1000ULL) ^
      premap_typed_consumer_mix64_v1(row.scale_metadata_handle + 0x2000ULL) ^
      premap_typed_consumer_mix64_v1(row.aux_metadata_handle + 0x3000ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(static_cast<uint64_t>(row.row_index)) ^
      premap_typed_consumer_mix64_v1(table.row_order_hash) ^
      premap_typed_consumer_mix64_v1(table.ordered_row_hash);
  return result;
}

__device__ static inline PremapKernelSideCompatibleConsumerResultV1
premap_typed_consumer_kernel_side_compatible_consume_row_v1(
    const PremapKernelSideTypedConsumerLaunchEnvelopeV1& envelope,
    uint32_t row_index) {
  PremapKernelSideCompatibleConsumerResultV1 result;
  result.envelope_valid = static_cast<uint32_t>(
      premap_typed_consumer_launch_envelope_matches_v1(envelope));
  result.row_valid = static_cast<uint32_t>(row_index < envelope.table.row_count);
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  if (result.envelope_valid == 0 || result.row_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(envelope.table, row_index);
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid =
      premap_typed_consumer_lifetime_valid_v1(envelope.table, row);
  result.ok = static_cast<uint32_t>(
      result.envelope_valid != 0 && result.row_valid != 0 &&
      result.required_handle_visible != 0 && result.lifetime_valid != 0 &&
      !kPremapKernelSideCompatibleConsumerAbiV1PayloadDerefAllowed &&
      !kPremapKernelSideCompatibleConsumerAbiV1KernelArgPassAllowed &&
      !kPremapKernelSideCompatibleConsumerAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xd35c0001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0x9ac6ed01ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0x5ca1e001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xa11c0001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(static_cast<uint64_t>(row.row_index)) ^
      premap_typed_consumer_mix64_v1(envelope.expected_row_order_hash) ^
      premap_typed_consumer_mix64_v1(envelope.expected_ordered_row_hash);
  return result;
}

__device__ static inline uint32_t
premap_typed_consumer_future_kernel_single_field_mirror_matches_v1(
    const PremapKernelSideTypedConsumerAbiV1& table,
    const PremapKernelSideTypedConsumerRowV1& row,
    uint32_t mirror_kind) {
  switch (mirror_kind) {
    case kPremapFutureKernelSideConsumerFieldDescriptorPtr:
      return premap_typed_consumer_descriptor_ptr_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor:
      return premap_typed_consumer_packed_weight_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldScaleMetadataHandle:
      return premap_typed_consumer_scale_metadata_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldAuxMetadataHandle:
      return premap_typed_consumer_aux_metadata_mirror_matches_v1(table, row);
    case kPremapFutureKernelSideConsumerFieldNone:
    default:
      return 0;
  }
}

__device__ static inline uint64_t
premap_typed_consumer_future_kernel_single_field_mirror_hash_v1(
    const PremapKernelSideTypedConsumerRowV1& row,
    uint32_t mirror_kind) {
  switch (mirror_kind) {
    case kPremapFutureKernelSideConsumerFieldDescriptorPtr:
      return premap_typed_consumer_mix64_v1(
                 row.descriptor_ptr + 0xf17d000000000001ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor:
      return premap_typed_consumer_mix64_v1(
                 row.packed_weight_descriptor + 0xf17d000000000002ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldScaleMetadataHandle:
      return premap_typed_consumer_mix64_v1(
                 row.scale_metadata_handle + 0xf17d000000000003ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldAuxMetadataHandle:
      return premap_typed_consumer_mix64_v1(
                 row.aux_metadata_handle + 0xf17d000000000004ULL) ^
             premap_typed_consumer_mix64_v1(row.row_index);
    case kPremapFutureKernelSideConsumerFieldNone:
    default:
      return 0;
  }
}

__device__ static inline PremapFutureKernelSideConsumerResultV1
premap_typed_consumer_future_kernel_consume_row_v1(
    const PremapFutureKernelSideConsumerArgsV1& args,
    uint32_t row_index) {
  PremapFutureKernelSideConsumerResultV1 result;
  result.args_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_kernel_args_match_v1(args));
  result.envelope_valid = static_cast<uint32_t>(
      premap_typed_consumer_launch_envelope_matches_v1(args.envelope));
  result.row_valid = static_cast<uint32_t>(row_index < args.envelope.table.row_count);
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = static_cast<uint32_t>(
      args.single_field_mirror_kind != kPremapFutureKernelSideConsumerFieldNone);
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = args.single_field_mirror_kind;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  result.single_field_mirror_hash = 0;
  if (result.args_valid == 0 || result.envelope_valid == 0 ||
      result.row_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(args.envelope.table, row_index);
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid =
      premap_typed_consumer_lifetime_valid_v1(args.envelope.table, row);
  if (result.single_field_mirror_checked != 0) {
    result.single_field_mirror_ok =
        premap_typed_consumer_future_kernel_single_field_mirror_matches_v1(
            args.envelope.table, row, args.single_field_mirror_kind);
    result.single_field_mirror_hash =
        premap_typed_consumer_future_kernel_single_field_mirror_hash_v1(
            row, args.single_field_mirror_kind);
  }
  const uint32_t mirror_gate =
      result.single_field_mirror_checked == 0 || result.single_field_mirror_ok != 0;
  result.ok = static_cast<uint32_t>(
      result.args_valid != 0 && result.envelope_valid != 0 &&
      result.row_valid != 0 && result.required_handle_visible != 0 &&
      result.lifetime_valid != 0 && mirror_gate != 0);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xf00d0001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0xf00d0002ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0xf00d0003ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xf00d0004ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(row.row_index) ^
      premap_typed_consumer_mix64_v1(args.field_mask) ^
      premap_typed_consumer_mix64_v1(args.single_field_mirror_kind) ^
      premap_typed_consumer_mix64_v1(args.envelope.expected_row_order_hash) ^
      premap_typed_consumer_mix64_v1(args.envelope.expected_ordered_row_hash);
  return result;
}

__device__ static inline PremapFutureKernelArgsCompatibleConsumerPathResultV1
premap_typed_consumer_future_kernel_args_compatible_consume_row_v1(
    const PremapFutureKernelSideConsumerArgsV1& args,
    uint32_t row_index) {
  PremapFutureKernelArgsCompatibleConsumerPathResultV1 result;
  result.args_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_kernel_args_match_v1(args));
  const PremapKernelSideCompatibleConsumerResultV1 compatible =
      premap_typed_consumer_kernel_side_compatible_consume_row_v1(
          args.envelope, row_index);
  result.compatible_consumer_ok = compatible.ok;
  result.envelope_valid = compatible.envelope_valid;
  result.row_valid = compatible.row_valid;
  result.required_handle_visible = compatible.required_handle_visible;
  result.lifetime_valid = compatible.lifetime_valid;
  result.field_count = compatible.field_count;
  result.ok = static_cast<uint32_t>(
      result.args_valid != 0 && result.compatible_consumer_ok != 0 &&
      !kPremapFutureKernelArgsCompatibleConsumerPathV1PayloadDerefAllowed &&
      !kPremapFutureKernelArgsCompatibleConsumerPathV1KernelArgPassAllowed &&
      !kPremapFutureKernelArgsCompatibleConsumerPathV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(compatible.row_hash + 0xfc0a0001ULL) ^
      premap_typed_consumer_mix64_v1(args.field_mask + 0xfc0a0002ULL) ^
      premap_typed_consumer_mix64_v1(
          args.envelope.expected_row_order_hash + 0xfc0a0003ULL) ^
      premap_typed_consumer_mix64_v1(
          args.envelope.expected_ordered_row_hash + 0xfc0a0004ULL);
  return result;
}

__device__ static inline uint32_t
premap_typed_consumer_future_native_single_field_mirror_matches_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    const PremapKernelSideTypedConsumerRowV1& row,
    uint32_t mirror_kind) {
  switch (mirror_kind) {
    case kPremapFutureKernelSideConsumerFieldDescriptorPtr:
      return static_cast<uint32_t>(
          params.descriptor_ptr != nullptr && row.descriptor_ptr != 0 &&
          row.descriptor_ptr == params.descriptor_ptr[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor:
      return static_cast<uint32_t>(
          params.packed_weight_descriptor != nullptr &&
          row.packed_weight_descriptor != 0 &&
          row.packed_weight_descriptor ==
              params.packed_weight_descriptor[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldScaleMetadataHandle:
      return static_cast<uint32_t>(
          params.scale_metadata_handle != nullptr &&
          row.scale_metadata_handle != 0 &&
          row.scale_metadata_handle == params.scale_metadata_handle[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldAuxMetadataHandle:
      return static_cast<uint32_t>(
          params.aux_metadata_handle != nullptr && row.aux_metadata_handle != 0 &&
          row.aux_metadata_handle == params.aux_metadata_handle[row.row_index]);
    case kPremapFutureKernelSideConsumerFieldNone:
    default:
      return 0;
  }
}

__device__ static inline uint32_t
premap_typed_consumer_future_native_lifetime_valid_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    const PremapKernelSideTypedConsumerRowV1& row) {
  return static_cast<uint32_t>(
      params.lifetime_epoch == 1 && row.address_key_hash != 0 &&
      row.expert_id >= 0);
}

__device__ static inline PremapFutureKernelNativeConsumerResultV1
premap_typed_consumer_future_native_consume_row_v1(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint32_t row_index,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerResultV1 result;
  result.params_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_params_match_v1(
          params, expected_schema_hash_hi, expected_schema_hash_lo));
  result.row_valid = static_cast<uint32_t>(row_index < params.row_count);
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = static_cast<uint32_t>(
      params.single_field_mirror_kind != kPremapFutureKernelSideConsumerFieldNone);
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = params.single_field_mirror_kind;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  result.single_field_mirror_hash = 0;
  if (result.params_valid == 0 || result.row_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(params, row_index);
  result.required_handle_visible =
      premap_typed_consumer_required_handles_visible_v1(row);
  result.lifetime_valid =
      premap_typed_consumer_future_native_lifetime_valid_v1(params, row);
  if (result.single_field_mirror_checked != 0) {
    result.single_field_mirror_ok =
        premap_typed_consumer_future_native_single_field_mirror_matches_v1(
            params, row, params.single_field_mirror_kind);
    result.single_field_mirror_hash =
        premap_typed_consumer_future_kernel_single_field_mirror_hash_v1(
            row, params.single_field_mirror_kind);
  }
  const uint32_t mirror_gate =
      result.single_field_mirror_checked == 0 || result.single_field_mirror_ok != 0;
  result.ok = static_cast<uint32_t>(
      result.params_valid != 0 && result.row_valid != 0 &&
      result.required_handle_visible != 0 && result.lifetime_valid != 0 &&
      mirror_gate != 0 &&
      !kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xab100001ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0xab100002ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0xab100003ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xab100004ULL) ^
      premap_typed_consumer_mix64_v1(
          row.address_key_hash + static_cast<uint64_t>(row.expert_id)) ^
      premap_typed_consumer_mix64_v1(row.row_index) ^
      premap_typed_consumer_mix64_v1(params.field_mask) ^
      premap_typed_consumer_mix64_v1(params.single_field_mirror_kind) ^
      premap_typed_consumer_mix64_v1(params.row_order_hash) ^
      premap_typed_consumer_mix64_v1(params.ordered_row_hash);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerLaunchResultV1
premap_typed_consumer_future_native_launch_consume_row_v1(
    const PremapFutureKernelNativeConsumerLaunchV1& launch,
    uint32_t row_index,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerLaunchResultV1 result;
  result.launch_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_launch_matches_v1(
          launch, expected_schema_hash_hi, expected_schema_hash_lo));
  const PremapFutureKernelNativeConsumerResultV1 native =
      premap_typed_consumer_future_native_consume_row_v1(
          launch.params,
          row_index,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.native_consumer_ok = native.ok;
  result.params_valid = native.params_valid;
  result.row_valid = native.row_valid;
  result.required_handle_visible = native.required_handle_visible;
  result.lifetime_valid = native.lifetime_valid;
  result.single_field_mirror_checked = native.single_field_mirror_checked;
  result.single_field_mirror_ok = native.single_field_mirror_ok;
  result.single_field_mirror_kind = native.single_field_mirror_kind;
  result.field_count = native.field_count;
  result.single_field_mirror_hash = native.single_field_mirror_hash;
  result.ok = static_cast<uint32_t>(
      result.launch_valid != 0 && result.native_consumer_ok != 0 &&
      !kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(native.row_hash + 0x1a9c000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(launch.abi_version) + 0x1a9c0002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(launch.params_struct_size) + 0x1a9c0003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(launch.row_stride) + 0x1a9c0004ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerDispatchResultV1
premap_typed_consumer_future_native_dispatch_consume_row_v1(
    const PremapFutureKernelNativeConsumerDispatchV1& dispatch,
    uint32_t local_row_index,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerDispatchResultV1 result;
  result.dispatch_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_dispatch_matches_v1(
          dispatch, expected_schema_hash_hi, expected_schema_hash_lo));
  result.launch_geometry_valid = static_cast<uint32_t>(
      actual_grid_x == dispatch.grid_x && actual_block_x == dispatch.block_x);
  result.active_rows =
      dispatch.row_limit >= dispatch.row_offset
          ? dispatch.row_limit - dispatch.row_offset
          : 0;
  const bool row_index_add_valid =
      local_row_index <= (0xffffffffu - dispatch.row_offset);
  const uint32_t row_index =
      row_index_add_valid ? dispatch.row_offset + local_row_index : 0;
  result.row_window_valid = static_cast<uint32_t>(
      row_index_add_valid && local_row_index < result.active_rows &&
      row_index < dispatch.row_limit && row_index < dispatch.launch.params.row_count);
  result.launch_consumer_ok = 0;
  result.launch_valid = 0;
  result.row_valid = 0;
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = 0;
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = kPremapFutureKernelSideConsumerFieldNone;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.single_field_mirror_hash = 0;
  result.row_hash = 0;
  if (result.dispatch_valid == 0 || result.launch_geometry_valid == 0 ||
      result.row_window_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapFutureKernelNativeConsumerLaunchResultV1 launch_result =
      premap_typed_consumer_future_native_launch_consume_row_v1(
          dispatch.launch,
          row_index,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.launch_consumer_ok = launch_result.ok;
  result.launch_valid = launch_result.launch_valid;
  result.row_valid = launch_result.row_valid;
  result.required_handle_visible = launch_result.required_handle_visible;
  result.lifetime_valid = launch_result.lifetime_valid;
  result.single_field_mirror_checked =
      launch_result.single_field_mirror_checked;
  result.single_field_mirror_ok = launch_result.single_field_mirror_ok;
  result.single_field_mirror_kind = launch_result.single_field_mirror_kind;
  result.field_count = launch_result.field_count;
  result.single_field_mirror_hash = launch_result.single_field_mirror_hash;
  result.ok = static_cast<uint32_t>(
      result.dispatch_valid != 0 && result.launch_geometry_valid != 0 &&
      result.row_window_valid != 0 && result.launch_consumer_ok != 0 &&
      !kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(
          launch_result.row_hash + 0xd15c000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.dispatch_version) + 0xd15c0002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.grid_x) + 0xd15c0003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.block_x) + 0xd15c0004ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.row_offset) + 0xd15c0005ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch.row_limit) + 0xd15c0006ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerDispatchResultV1
premap_typed_consumer_future_native_dispatch_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerDispatchV1& dispatch,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  const bool program_lane_valid =
      program_id < actual_grid_x && lane_id < actual_block_x &&
      program_id < dispatch.grid_x && lane_id < dispatch.block_x &&
      lane_id < dispatch.rows_per_program;
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(dispatch.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  const bool local_row_index_valid = local_row_index_64 <= 0xffffffffULL;
  PremapFutureKernelNativeConsumerDispatchResultV1 result =
      premap_typed_consumer_future_native_dispatch_consume_row_v1(
          dispatch,
          local_row_index_valid ? static_cast<uint32_t>(local_row_index_64) : 0,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.ok = static_cast<uint32_t>(
      result.ok != 0 && program_lane_valid && local_row_index_valid);
  if (!program_lane_valid || !local_row_index_valid) {
    result.row_window_valid = 0;
    result.row_valid = 0;
    result.launch_consumer_ok = 0;
    result.required_handle_visible = 0;
    result.lifetime_valid = 0;
  }
  result.row_hash ^=
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_id) + 0xd15c100000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(lane_id) + 0xd15c100000000002ULL) ^
      premap_typed_consumer_mix64_v1(local_row_index_64 + 0xd15c100000000003ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerDispatchResultV1
premap_typed_consumer_future_native_dispatch_ptr_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerDispatchPtrV1& dispatch_ptr,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerDispatchResultV1 result;
  result.dispatch_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_dispatch_ptr_matches_v1(
          dispatch_ptr, expected_schema_hash_hi, expected_schema_hash_lo));
  result.launch_geometry_valid = 0;
  result.launch_consumer_ok = 0;
  result.launch_valid = 0;
  result.row_window_valid = 0;
  result.active_rows = 0;
  result.row_valid = 0;
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.single_field_mirror_checked = 0;
  result.single_field_mirror_ok = 0;
  result.single_field_mirror_kind = kPremapFutureKernelSideConsumerFieldNone;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.single_field_mirror_hash = 0;
  result.row_hash = 0;
  if (result.dispatch_valid == 0 ||
      !premap_typed_consumer_future_native_dispatch_ptr_packet_matches_v1(
          dispatch_ptr)) {
    result.ok = 0;
    return result;
  }
  result =
      premap_typed_consumer_future_native_dispatch_consume_program_lane_v1(
          *dispatch_ptr.dispatch,
          program_id,
          lane_id,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.ok = static_cast<uint32_t>(
      result.ok != 0 &&
      !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1CurrentWna16ArgCompatible);
  result.row_hash ^=
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_ptr.abi_version) +
          0xd15c300000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_ptr.dispatch_struct_size) +
          0xd15c300000000002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_ptr.result_struct_size) +
          0xd15c300000000003ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerArgSlotResultV1
premap_typed_consumer_future_native_arg_slot_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerArgSlotV1& arg_slot,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerArgSlotResultV1 result;
  if (!premap_typed_consumer_future_native_arg_slot_packet_matches_v1(
          arg_slot)) {
    result.dispatch_valid = 0;
    result.launch_geometry_valid = 0;
    result.launch_consumer_ok = 0;
    result.launch_valid = 0;
    result.row_window_valid = 0;
    result.active_rows = 0;
    result.row_valid = 0;
    result.required_handle_visible = 0;
    result.lifetime_valid = 0;
    result.single_field_mirror_checked = 0;
    result.single_field_mirror_ok = 0;
    result.single_field_mirror_kind = kPremapFutureKernelSideConsumerFieldNone;
    result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
    result.single_field_mirror_hash = 0;
    result.row_hash = 0;
    result.ok = 0;
    return result;
  }
  result =
      premap_typed_consumer_future_native_dispatch_ptr_consume_program_lane_v1(
          *arg_slot.dispatch_ptr,
          program_id,
          lane_id,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.ok = static_cast<uint32_t>(
      result.ok != 0 &&
      !kPremapFutureKernelNativeConsumerArgSlotAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerArgSlotAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerArgSlotAbiV1CurrentWna16ArgCompatible);
  result.row_hash ^=
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(arg_slot.abi_version) +
          0xa951000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(arg_slot.dispatch_ptr_struct_size) +
          0xa951000000000002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(arg_slot.result_struct_size) +
          0xa951000000000003ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerViewResultV1
premap_typed_consumer_future_native_view_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerViewV1& view,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerViewResultV1 result;
  result.view_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_view_matches_v1(
          view, expected_schema_hash_hi, expected_schema_hash_lo));
  result.launch_geometry_valid = static_cast<uint32_t>(
      program_id < actual_grid_x && lane_id < actual_block_x &&
      lane_id < view.rows_per_program);
  result.row_window_valid = 0;
  result.row_valid = 0;
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.all_handle_fields_read = 0;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(view.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  const bool local_row_index_valid = local_row_index_64 <= 0xffffffffULL;
  const uint32_t local_row_index =
      local_row_index_valid ? static_cast<uint32_t>(local_row_index_64) : 0;
  const uint32_t active_rows =
      view.row_limit >= view.row_offset ? view.row_limit - view.row_offset : 0;
  const bool row_index_add_valid =
      local_row_index <= (0xffffffffu - view.row_offset);
  const uint32_t row_index =
      row_index_add_valid ? view.row_offset + local_row_index : 0;
  result.row_window_valid = static_cast<uint32_t>(
      local_row_index_valid && row_index_add_valid &&
      local_row_index < active_rows && row_index < view.row_limit &&
      row_index < view.params.row_count);
  if (result.view_valid == 0 || result.launch_geometry_valid == 0 ||
      result.row_window_valid == 0) {
    result.ok = 0;
    return result;
  }
  const PremapFutureKernelNativeConsumerResultV1 native =
      premap_typed_consumer_future_native_consume_row_v1(
          view.params,
          row_index,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(view.params, row_index);
  result.row_valid = native.row_valid;
  result.required_handle_visible = native.required_handle_visible;
  result.lifetime_valid = native.lifetime_valid;
  result.all_handle_fields_read = static_cast<uint32_t>(
      row.descriptor_ptr != 0 && row.packed_weight_descriptor != 0 &&
      row.scale_metadata_handle != 0 &&
      ((view.params.field_mask &
        kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) == 0 ||
       row.aux_metadata_handle != 0));
  result.ok = static_cast<uint32_t>(
      native.ok != 0 && result.all_handle_fields_read != 0 &&
      !kPremapFutureKernelNativeConsumerViewAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerViewAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerViewAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(native.row_hash + 0xc051000000000001ULL) ^
      premap_typed_consumer_mix64_v1(row.descriptor_ptr + 0xc051000000000002ULL) ^
      premap_typed_consumer_mix64_v1(
          row.packed_weight_descriptor + 0xc051000000000003ULL) ^
      premap_typed_consumer_mix64_v1(
          row.scale_metadata_handle + 0xc051000000000004ULL) ^
      premap_typed_consumer_mix64_v1(
          row.aux_metadata_handle + 0xc051000000000005ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(view.source_packet_chain_depth) +
          0xc051000000000006ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(view.row_offset) + 0xc051000000000007ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(view.row_limit) + 0xc051000000000008ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerProgramViewResultV1
premap_typed_consumer_future_native_program_view_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerProgramViewV1& program_view,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerProgramViewResultV1 result;
  result.program_view_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_program_view_matches_v1(
          program_view, expected_schema_hash_hi, expected_schema_hash_lo));
  const PremapFutureKernelNativeConsumerViewResultV1 view_result =
      premap_typed_consumer_future_native_view_consume_program_lane_v1(
          program_view.view,
          program_id,
          lane_id,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.view_valid = view_result.view_valid;
  result.launch_geometry_valid = static_cast<uint32_t>(
      view_result.launch_geometry_valid != 0 &&
      actual_grid_x == program_view.program_count &&
      actual_block_x == program_view.view.rows_per_program &&
      program_id < program_view.program_count &&
      lane_id < program_view.view.rows_per_program);
  result.row_window_valid = view_result.row_window_valid;
  result.row_valid = view_result.row_valid;
  result.required_handle_visible = view_result.required_handle_visible;
  result.lifetime_valid = view_result.lifetime_valid;
  result.all_handle_fields_read = view_result.all_handle_fields_read;
  result.field_count = view_result.field_count;
  const uint64_t expected_program_iteration_hash =
      premap_typed_consumer_program_iteration_hash_v1(
          program_view.program_count,
          program_view.view.rows_per_program,
          program_view.view.row_offset,
          program_view.view.row_limit,
          program_view.last_program_active_rows,
          program_view.inactive_lane_count);
  result.program_iteration_valid = static_cast<uint32_t>(
      program_view.program_iteration_hash == expected_program_iteration_hash);
  result.ok = static_cast<uint32_t>(
      result.program_view_valid != 0 && view_result.ok != 0 &&
      result.launch_geometry_valid != 0 &&
      result.program_iteration_valid != 0 &&
      !kPremapFutureKernelNativeConsumerProgramViewAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerProgramViewAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerProgramViewAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(
          view_result.row_hash + 0xc052000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_view.program_count) +
          0xc052000000000002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_view.last_program_active_rows) +
          0xc052000000000003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_view.inactive_lane_count) +
          0xc052000000000004ULL) ^
      premap_typed_consumer_mix64_v1(
          program_view.program_iteration_hash + 0xc052000000000005ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerProgramViewPtrResultV1
premap_typed_consumer_future_native_program_view_ptr_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerProgramViewPtrV1& program_view_ptr,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerProgramViewPtrResultV1 result;
  result.packet_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_program_view_ptr_packet_matches_v1(
          program_view_ptr));
  result.program_view_valid = 0;
  result.view_valid = 0;
  result.launch_geometry_valid = 0;
  result.row_window_valid = 0;
  result.program_iteration_valid = 0;
  result.row_valid = 0;
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.all_handle_fields_read = 0;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  result.ok = 0;
  if (result.packet_valid == 0) {
    return result;
  }
  const PremapFutureKernelNativeConsumerProgramViewV1& program_view =
      *program_view_ptr.program_view;
  const PremapFutureKernelNativeConsumerProgramViewResultV1 inner =
      premap_typed_consumer_future_native_program_view_consume_program_lane_v1(
          program_view,
          program_id,
          lane_id,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.program_view_valid = inner.program_view_valid;
  result.view_valid = inner.view_valid;
  result.launch_geometry_valid = inner.launch_geometry_valid;
  result.row_window_valid = inner.row_window_valid;
  result.program_iteration_valid = inner.program_iteration_valid;
  result.row_valid = inner.row_valid;
  result.required_handle_visible = inner.required_handle_visible;
  result.lifetime_valid = inner.lifetime_valid;
  result.all_handle_fields_read = inner.all_handle_fields_read;
  result.field_count = inner.field_count;
  result.ok = static_cast<uint32_t>(
      inner.ok != 0 &&
      !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(inner.row_hash + 0xc053000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_view_ptr.abi_version) +
          0xc053000000000002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_view_ptr.program_view_struct_size) +
          0xc053000000000003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(program_view_ptr.result_struct_size) +
          0xc053000000000004ULL);
  return result;
}

__device__ static inline PremapFutureKernelNativeConsumerKernelArgPacketResultV1
premap_typed_consumer_future_native_kernel_arg_packet_consume_program_lane_v1(
    const PremapFutureKernelNativeConsumerKernelArgPacketV1& kernel_arg_packet,
    uint32_t program_id,
    uint32_t lane_id,
    uint32_t actual_grid_x,
    uint32_t actual_block_x,
    uint64_t expected_schema_hash_hi,
    uint64_t expected_schema_hash_lo) {
  PremapFutureKernelNativeConsumerKernelArgPacketResultV1 result;
  result.packet_valid = static_cast<uint32_t>(
      premap_typed_consumer_future_native_kernel_arg_packet_matches_v1(
          kernel_arg_packet));
  result.program_view_ptr_valid = 0;
  result.program_view_valid = 0;
  result.view_valid = 0;
  result.launch_geometry_valid = 0;
  result.row_window_valid = 0;
  result.program_iteration_valid = 0;
  result.row_valid = 0;
  result.required_handle_visible = 0;
  result.lifetime_valid = 0;
  result.all_handle_fields_read = 0;
  result.field_count = kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  result.row_hash = 0;
  result.ok = 0;
  if (result.packet_valid == 0) {
    return result;
  }
  const PremapFutureKernelNativeConsumerProgramViewPtrV1& program_view_ptr =
      *kernel_arg_packet.program_view_ptr;
  const PremapFutureKernelNativeConsumerProgramViewPtrResultV1 inner =
      premap_typed_consumer_future_native_program_view_ptr_consume_program_lane_v1(
          program_view_ptr,
          program_id,
          lane_id,
          actual_grid_x,
          actual_block_x,
          expected_schema_hash_hi,
          expected_schema_hash_lo);
  result.program_view_ptr_valid = inner.packet_valid;
  result.program_view_valid = inner.program_view_valid;
  result.view_valid = inner.view_valid;
  result.launch_geometry_valid = inner.launch_geometry_valid;
  result.row_window_valid = inner.row_window_valid;
  result.program_iteration_valid = inner.program_iteration_valid;
  result.row_valid = inner.row_valid;
  result.required_handle_visible = inner.required_handle_visible;
  result.lifetime_valid = inner.lifetime_valid;
  result.all_handle_fields_read = inner.all_handle_fields_read;
  result.field_count = inner.field_count;
  result.ok = static_cast<uint32_t>(
      inner.ok != 0 &&
      !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1PayloadDerefAllowed &&
      !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1KernelArgPassAllowed &&
      !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1CurrentWna16ArgCompatible);
  result.row_hash =
      premap_typed_consumer_mix64_v1(inner.row_hash + 0xc054000000000001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(kernel_arg_packet.abi_version) +
          0xc054000000000002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(kernel_arg_packet.program_view_ptr_struct_size) +
          0xc054000000000003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(kernel_arg_packet.result_struct_size) +
          0xc054000000000004ULL);
  return result;
}
