#include <hip/hip_runtime.h>

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "premap_typed_consumer_adapter_v1.h"
#include "premap_typed_consumer_abi_v1.h"

#ifndef MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1
#error "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1 must be defined for this stub"
#endif

#ifndef MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI
#error "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI must be injected by the runner"
#endif

#ifndef MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO
#error "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO must be injected by the runner"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF)
#error "payload dereference is forbidden in the readonly native stub"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS)
#error "kernel-arg passing is forbidden in the readonly native stub"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
#error "future-args compatible consumer path requires future kernel consumer args"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
#error "future native consumer launch ABI requires future native consumer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
#error "future native consumer dispatch ABI requires future native consumer launch ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
#error "future native consumer dispatch pointer ABI requires future native consumer dispatch ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI)
#error "future native consumer arg-slot ABI requires future native consumer dispatch pointer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI)
#error "future native consumer view ABI requires future native consumer arg-slot ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI)
#error "future native consumer program-view ABI requires future native consumer view ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI)
#error "future native consumer program-view pointer ABI requires future native consumer program-view ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI)
#error "future native consumer kernel-arg packet ABI requires future native consumer program-view pointer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI)
#error "future native consumer kernel entry-args ABI requires future native consumer kernel-arg packet ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI)
#error "future native consumer kernel entry-args pointer ABI requires future native consumer kernel entry-args ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI)
#error "future native consumer launch-envelope args ABI requires future native consumer kernel entry-args pointer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI)
#error "future native consumer launch-envelope args pointer ABI requires future native consumer launch-envelope args ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI)
#error "future native consumer kernel launch descriptor ABI requires future native consumer launch-envelope args pointer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI)
#error "future native consumer kernel launch context ABI requires future native consumer kernel launch descriptor ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI)
#error "future native consumer invocation ABI requires future native consumer kernel launch context ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI)
#error "future native consumer invocation entry ABI requires future native consumer invocation ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI)
#error "future native consumer endpoint ABI requires future native consumer invocation entry ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI)
#error "future native consumer endpoint pointer ABI requires future native consumer endpoint ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI)
#error "future native consumer WNA16-adjacent typed slot ABI requires future native consumer endpoint pointer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI)
#error "future native consumer request pointer ABI requires future native consumer kernel-arg packet ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI)
#error "future native consumer request launch ABI requires future native consumer request pointer ABI"
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI) && \
    !defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI)
#error "future native consumer request launch pointer ABI requires future native consumer request launch ABI"
#endif

#if (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)) || \
    (defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD) && \
     defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD))
#error "enable only one single-field mirror canary per stub build"
#endif

static_assert(!kPremapKernelSideTypedConsumerAbiV1PayloadBytesAllowed,
              "readonly typed consumer ABI must not allow payload bytes");
static_assert(!kPremapKernelSideTypedConsumerAbiV1KernelArgPassAllowed,
              "readonly typed consumer ABI must not allow kernel-arg pass");
static_assert(kPremapKernelSideTypedConsumerAbiV1HandleColumnCount == 4,
              "typed consumer ABI v1 must expose four handle columns");
static_assert(!kPremapKernelSideTypedConsumerAdapterV1PayloadDerefAllowed,
              "readonly typed consumer adapter must not allow payload dereference");
static_assert(!kPremapKernelSideTypedConsumerAdapterV1KernelArgPassAllowed,
              "readonly typed consumer adapter must not allow kernel-arg pass");
static_assert(!kPremapKernelSideCompatibleConsumerAbiV1PayloadDerefAllowed,
              "kernel-side compatible consumer ABI must not allow payload dereference");
static_assert(!kPremapKernelSideCompatibleConsumerAbiV1KernelArgPassAllowed,
              "kernel-side compatible consumer ABI must not allow kernel-arg pass");
static_assert(!kPremapKernelSideCompatibleConsumerAbiV1CurrentWna16ArgCompatible,
              "kernel-side compatible consumer ABI must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelSideConsumerArgsV1PayloadDerefAllowed,
              "future kernel consumer args must not allow payload dereference");
static_assert(!kPremapFutureKernelSideConsumerArgsV1KernelArgPassAllowed,
              "future kernel consumer args must not allow kernel-arg pass");
static_assert(!kPremapFutureKernelSideConsumerArgsV1CurrentWna16ArgCompatible,
              "future kernel consumer args must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelArgsCompatibleConsumerPathV1PayloadDerefAllowed,
    "future args compatible consumer path must not allow payload dereference");
static_assert(
    !kPremapFutureKernelArgsCompatibleConsumerPathV1KernelArgPassAllowed,
    "future args compatible consumer path must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelArgsCompatibleConsumerPathV1CurrentWna16ArgCompatible,
    "future args compatible consumer path must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelNativeConsumerAbiV1PayloadDerefAllowed,
              "future native consumer ABI must not allow payload dereference");
static_assert(!kPremapFutureKernelNativeConsumerAbiV1KernelArgPassAllowed,
              "future native consumer ABI must not allow kernel-arg pass");
static_assert(!kPremapFutureKernelNativeConsumerAbiV1CurrentWna16ArgCompatible,
              "future native consumer ABI must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelNativeConsumerLaunchAbiV1PayloadDerefAllowed,
              "future native consumer launch ABI must not allow payload dereference");
static_assert(!kPremapFutureKernelNativeConsumerLaunchAbiV1KernelArgPassAllowed,
              "future native consumer launch ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchAbiV1CurrentWna16ArgCompatible,
    "future native consumer launch ABI must not be the current WNA16 arg list");
static_assert(!kPremapFutureKernelNativeConsumerDispatchAbiV1PayloadDerefAllowed,
              "future native consumer dispatch ABI must not allow payload dereference");
static_assert(!kPremapFutureKernelNativeConsumerDispatchAbiV1KernelArgPassAllowed,
              "future native consumer dispatch ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerDispatchAbiV1CurrentWna16ArgCompatible,
    "future native consumer dispatch ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1PayloadDerefAllowed,
    "future native consumer dispatch pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1KernelArgPassAllowed,
    "future native consumer dispatch pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerDispatchPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer dispatch pointer ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerArgSlotAbiV1PayloadDerefAllowed,
    "future native consumer arg slot ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerArgSlotAbiV1KernelArgPassAllowed,
    "future native consumer arg slot ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerArgSlotAbiV1CurrentWna16ArgCompatible,
    "future native consumer arg slot ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerViewAbiV1PayloadDerefAllowed,
    "future native consumer view ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerViewAbiV1KernelArgPassAllowed,
    "future native consumer view ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerViewAbiV1CurrentWna16ArgCompatible,
    "future native consumer view ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerProgramViewAbiV1PayloadDerefAllowed,
    "future native consumer program-view ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerProgramViewAbiV1KernelArgPassAllowed,
    "future native consumer program-view ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerProgramViewAbiV1CurrentWna16ArgCompatible,
    "future native consumer program-view ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1PayloadDerefAllowed,
    "future native consumer program-view pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1KernelArgPassAllowed,
    "future native consumer program-view pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer program-view pointer ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1PayloadDerefAllowed,
    "future native consumer kernel-arg packet ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1KernelArgPassAllowed,
    "future native consumer kernel-arg packet ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1CurrentWna16ArgCompatible,
    "future native consumer kernel-arg packet ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1PayloadDerefAllowed,
    "future native consumer kernel entry-args ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1KernelArgPassAllowed,
    "future native consumer kernel entry-args ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1CurrentWna16ArgCompatible,
    "future native consumer kernel entry-args ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1PayloadDerefAllowed,
    "future native consumer kernel entry-args pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1KernelArgPassAllowed,
    "future native consumer kernel entry-args pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer kernel entry-args pointer ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1PayloadDerefAllowed,
    "future native consumer launch-envelope args ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1KernelArgPassAllowed,
    "future native consumer launch-envelope args ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1CurrentWna16ArgCompatible,
    "future native consumer launch-envelope args ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1PayloadDerefAllowed,
    "future native consumer launch-envelope args pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1KernelArgPassAllowed,
    "future native consumer launch-envelope args pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer launch-envelope args pointer ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1PayloadDerefAllowed,
    "future native consumer kernel launch descriptor ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1KernelArgPassAllowed,
    "future native consumer kernel launch descriptor ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1CurrentWna16ArgCompatible,
    "future native consumer kernel launch descriptor ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1PayloadDerefAllowed,
    "future native consumer kernel launch context ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1KernelArgPassAllowed,
    "future native consumer kernel launch context ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1CurrentWna16ArgCompatible,
    "future native consumer kernel launch context ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerInvocationAbiV1PayloadDerefAllowed,
    "future native consumer invocation ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerInvocationAbiV1KernelArgPassAllowed,
    "future native consumer invocation ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerInvocationAbiV1CurrentWna16ArgCompatible,
    "future native consumer invocation ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerEndpointAbiV1PayloadDerefAllowed,
    "future native consumer endpoint ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerEndpointAbiV1KernelArgPassAllowed,
    "future native consumer endpoint ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerEndpointAbiV1CurrentWna16ArgCompatible,
    "future native consumer endpoint ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerEndpointPtrAbiV1PayloadDerefAllowed,
    "future native consumer endpoint pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerEndpointPtrAbiV1KernelArgPassAllowed,
    "future native consumer endpoint pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerEndpointPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer endpoint pointer ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1PayloadDerefAllowed,
    "future native consumer WNA16-adjacent typed slot ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1KernelArgPassAllowed,
    "future native consumer WNA16-adjacent typed slot ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1CurrentWna16ArgCompatible,
    "future native consumer WNA16-adjacent typed slot ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1RequiresWna16ArgReinterpretation,
    "future native consumer WNA16-adjacent typed slot ABI must not require WNA16 arg reinterpretation");
static_assert(
    !kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1ReusesCurrentWna16ArgSlot,
    "future native consumer WNA16-adjacent typed slot ABI must not reuse current WNA16 arg slot");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestPtrAbiV1PayloadDerefAllowed,
    "future native consumer request pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestPtrAbiV1KernelArgPassAllowed,
    "future native consumer request pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer request pointer ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestLaunchAbiV1PayloadDerefAllowed,
    "future native consumer request launch ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestLaunchAbiV1KernelArgPassAllowed,
    "future native consumer request launch ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestLaunchAbiV1CurrentWna16ArgCompatible,
    "future native consumer request launch ABI must not be the current WNA16 arg list");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1PayloadDerefAllowed,
    "future native consumer request launch pointer ABI must not allow payload dereference");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1KernelArgPassAllowed,
    "future native consumer request launch pointer ABI must not allow kernel-arg pass");
static_assert(
    !kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1CurrentWna16ArgCompatible,
    "future native consumer request launch pointer ABI must not be the current WNA16 arg list");

constexpr uint64_t kTypedSchemaHashHi = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_HI;
constexpr uint64_t kTypedSchemaHashLo = MTP_PREMAP_TYPED_CONSUMER_SCHEMA_HASH_LO;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_descriptor_ptr_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "descriptor_ptr";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldDescriptorPtr;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_scale_metadata_handle_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "scale_metadata_handle";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldScaleMetadataHandle;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_packed_weight_descriptor_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "packed_weight_descriptor";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldPackedWeightDescriptor;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
constexpr const char* kSingleFieldMirrorMode =
    "readonly_aux_metadata_handle_abi_row_mirror";
constexpr const char* kSingleFieldMirrorFieldName = "aux_metadata_handle";
constexpr const char* kSingleFieldMirrorSource =
    "typed_consumer_abi_row_adapter_v1";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldAuxMetadataHandle;
#else
constexpr const char* kSingleFieldMirrorMode = "none";
constexpr const char* kSingleFieldMirrorFieldName = "none";
constexpr const char* kSingleFieldMirrorSource = "none";
constexpr uint32_t kSingleFieldMirrorKind =
    kPremapFutureKernelSideConsumerFieldNone;
#endif

static inline void hip_check(hipError_t err, const char* what) {
  if (err != hipSuccess) {
    std::cerr << what << ": " << hipGetErrorString(err) << "\n";
    std::exit(2);
  }
}

__host__ __device__ static inline uint64_t mix64(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 33;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 33;
  return x;
}

__device__ static inline uint64_t handle_projection_hash(
    const PremapFutureKernelNativeConsumerParamsV1& params,
    uint32_t row_index) {
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(params, row_index);
  return mix64(row.descriptor_ptr + 0x481d000000000001ULL) ^
         mix64(row.packed_weight_descriptor + 0x481d000000000002ULL) ^
         mix64(row.scale_metadata_handle + 0x481d000000000003ULL) ^
         mix64(row.aux_metadata_handle + 0x481d000000000004ULL) ^
         mix64(row.address_key_hash + 0x481d000000000005ULL) ^
         mix64(static_cast<uint64_t>(row.expert_id) + 0x481d000000000006ULL) ^
         mix64(static_cast<uint64_t>(row.row_index) + 0x481d000000000007ULL);
}

__global__ void typed_consumer_kernel(
    PremapKernelSideTypedConsumerAbiV1 table,
    uint32_t* row_ok,
    uint64_t* row_hash,
    uint32_t* single_field_mirror_ok,
    uint64_t* single_field_mirror_hash,
    uint32_t* kernel_side_consumer_path_ok,
    uint64_t* kernel_side_consumer_path_hash,
    uint32_t* kernel_side_compatible_consumer_ok,
    uint64_t* kernel_side_compatible_consumer_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= table.row_count) {
    return;
  }
  uint32_t ok = 1;
  uint64_t h = 0x9e3779b97f4a7c15ULL ^ static_cast<uint64_t>(idx);

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA)
  ok &= static_cast<uint32_t>(
      premap_typed_consumer_schema_matches_v1(
          table, kTypedSchemaHashHi, kTypedSchemaHashLo));
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION)
  ok &= static_cast<uint32_t>(idx < table.row_count);
#endif

  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(table, idx);
  uint32_t mirror_ok = 0;
  uint64_t mirror_hash = 0;
  uint32_t kernel_path_ok = 0;
  uint64_t kernel_path_hash = 0;
  uint32_t compatible_consumer_ok = 0;
  uint64_t compatible_consumer_hash = 0;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY)
  ok &= premap_typed_consumer_required_handles_visible_v1(row);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR)
  ok &= static_cast<uint32_t>(row.descriptor_ptr != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR)
  ok &= static_cast<uint32_t>(row.packed_weight_descriptor != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE)
  ok &= static_cast<uint32_t>(row.scale_metadata_handle != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_descriptor_ptr_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.descriptor_ptr + 0xde5c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_scale_metadata_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.scale_metadata_handle + 0x5ca1e00000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_packed_weight_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.packed_weight_descriptor + 0x9ac6ed0000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_aux_metadata_mirror_matches_v1(table, row);
  mirror_hash = mix64(row.aux_metadata_handle + 0xa11c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE)
  ok &= static_cast<uint32_t>(table.aux_metadata_handle != nullptr);
  ok &= static_cast<uint32_t>(row.aux_metadata_handle != 0);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME)
  ok &= premap_typed_consumer_lifetime_valid_v1(table, row);
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
  const PremapKernelSideTypedConsumerPathResultV1 kernel_path_result =
      premap_typed_consumer_kernel_side_consume_row_v1(table, idx);
  kernel_path_ok = kernel_path_result.ok;
  kernel_path_hash = kernel_path_result.row_hash;
  ok &= kernel_path_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 compatible_envelope;
  compatible_envelope.table = table;
  compatible_envelope.expected_schema_hash_hi = kTypedSchemaHashHi;
  compatible_envelope.expected_schema_hash_lo = kTypedSchemaHashLo;
  compatible_envelope.expected_row_order_hash = table.row_order_hash;
  compatible_envelope.expected_ordered_row_hash = table.ordered_row_hash;
  compatible_envelope.expected_row_count = table.row_count;
  compatible_envelope.expected_column_count = table.column_count;
  compatible_envelope.payload_bytes = 0;
  compatible_envelope.flags =
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag |
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag;
  const PremapKernelSideCompatibleConsumerResultV1 compatible_result =
      premap_typed_consumer_kernel_side_compatible_consume_row_v1(
          compatible_envelope, idx);
  compatible_consumer_ok = compatible_result.ok;
  compatible_consumer_hash = compatible_result.row_hash;
  ok &= compatible_consumer_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR)
  h ^= mix64(row.descriptor_ptr);
  h ^= mix64(row.packed_weight_descriptor + 0x1000ULL);
  h ^= mix64(row.scale_metadata_handle + 0x2000ULL);
  h ^= mix64(row.aux_metadata_handle + 0x3000ULL);
  h ^= mix64(row.address_key_hash + static_cast<uint64_t>(row.expert_id));
  h ^= mix64(table.row_order_hash);
  h ^= mix64(table.ordered_row_hash);
#else
  h ^= row.descriptor_ptr ^ row.packed_weight_descriptor ^
       row.scale_metadata_handle ^ row.aux_metadata_handle ^
       row.address_key_hash ^ static_cast<uint64_t>(row.expert_id);
#endif

  row_ok[idx] = ok;
  row_hash[idx] = h;
  single_field_mirror_ok[idx] = mirror_ok;
  single_field_mirror_hash[idx] = mirror_hash;
  kernel_side_consumer_path_ok[idx] = kernel_path_ok;
  kernel_side_consumer_path_hash[idx] = kernel_path_hash;
  kernel_side_compatible_consumer_ok[idx] = compatible_consumer_ok;
  kernel_side_compatible_consumer_hash[idx] = compatible_consumer_hash;
}

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
__global__ void typed_consumer_envelope_kernel(
    PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope,
    uint32_t* row_ok,
    uint64_t* row_hash,
    uint32_t* single_field_mirror_ok,
    uint64_t* single_field_mirror_hash,
    uint32_t* kernel_side_consumer_path_ok,
    uint64_t* kernel_side_consumer_path_hash,
    uint32_t* kernel_side_compatible_consumer_ok,
    uint64_t* kernel_side_compatible_consumer_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= envelope.table.row_count) {
    return;
  }
  uint32_t ok = static_cast<uint32_t>(
      premap_typed_consumer_launch_envelope_matches_v1(envelope));
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_row_v1(envelope.table, idx);
  ok &= premap_typed_consumer_required_handles_visible_v1(row);
  ok &= premap_typed_consumer_lifetime_valid_v1(envelope.table, row);
  uint32_t mirror_ok = 0;
  uint64_t mirror_hash = 0;
  uint32_t kernel_path_ok = 0;
  uint64_t kernel_path_hash = 0;
  uint32_t compatible_consumer_ok = 0;
  uint64_t compatible_consumer_hash = 0;

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_descriptor_ptr_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.descriptor_ptr + 0xde5c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_scale_metadata_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.scale_metadata_handle + 0x5ca1e00000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_packed_weight_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.packed_weight_descriptor + 0x9ac6ed0000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#elif defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
  mirror_ok = premap_typed_consumer_aux_metadata_mirror_matches_v1(
      envelope.table, row);
  mirror_hash = mix64(row.aux_metadata_handle + 0xa11c000000000000ULL) ^
                mix64(static_cast<uint64_t>(idx));
  ok &= mirror_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
  const PremapKernelSideTypedConsumerPathResultV1 kernel_path_result =
      premap_typed_consumer_kernel_side_consume_row_v1(envelope.table, idx);
  kernel_path_ok = kernel_path_result.ok;
  kernel_path_hash = kernel_path_result.row_hash;
  ok &= kernel_path_ok;
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
  const PremapKernelSideCompatibleConsumerResultV1 compatible_result =
      premap_typed_consumer_kernel_side_compatible_consume_row_v1(envelope, idx);
  compatible_consumer_ok = compatible_result.ok;
  compatible_consumer_hash = compatible_result.row_hash;
  ok &= compatible_consumer_ok;
#endif

  uint64_t h = 0x517cc1b727220a95ULL ^ static_cast<uint64_t>(idx);
  h ^= mix64(row.descriptor_ptr);
  h ^= mix64(row.packed_weight_descriptor + 0x1000ULL);
  h ^= mix64(row.scale_metadata_handle + 0x2000ULL);
  h ^= mix64(row.aux_metadata_handle + 0x3000ULL);
  h ^= mix64(row.address_key_hash + static_cast<uint64_t>(row.expert_id));
  h ^= mix64(envelope.expected_row_order_hash);
  h ^= mix64(envelope.expected_ordered_row_hash);
  row_ok[idx] = ok;
  row_hash[idx] = h;
  single_field_mirror_ok[idx] = mirror_ok;
  single_field_mirror_hash[idx] = mirror_hash;
  kernel_side_consumer_path_ok[idx] = kernel_path_ok;
  kernel_side_consumer_path_hash[idx] = kernel_path_hash;
  kernel_side_compatible_consumer_ok[idx] = compatible_consumer_ok;
  kernel_side_compatible_consumer_hash[idx] = compatible_consumer_hash;
}
#endif

__global__ void typed_consumer_future_kernel_args_kernel(
    PremapFutureKernelSideConsumerArgsV1 args,
    uint32_t* future_kernel_consumer_ok,
    uint64_t* future_kernel_consumer_hash,
    uint32_t* future_kernel_single_field_mirror_ok,
    uint64_t* future_kernel_single_field_mirror_hash,
    uint32_t* future_kernel_compatible_path_ok,
    uint64_t* future_kernel_compatible_path_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= args.envelope.table.row_count) {
    return;
  }
  const PremapFutureKernelSideConsumerResultV1 result =
      premap_typed_consumer_future_kernel_consume_row_v1(args, idx);
  uint32_t compatible_path_ok = 0;
  uint64_t compatible_path_hash = 0;
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH)
  const PremapFutureKernelArgsCompatibleConsumerPathResultV1 compatible_path =
      premap_typed_consumer_future_kernel_args_compatible_consume_row_v1(
          args, idx);
  compatible_path_ok = compatible_path.ok;
  compatible_path_hash = compatible_path.row_hash;
#endif
  future_kernel_consumer_ok[idx] = result.ok;
  future_kernel_consumer_hash[idx] = result.row_hash;
  future_kernel_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_kernel_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
  future_kernel_compatible_path_ok[idx] = compatible_path_ok;
  future_kernel_compatible_path_hash[idx] = compatible_path_hash;
}

__global__ void typed_consumer_future_native_kernel(
    PremapFutureKernelNativeConsumerParamsV1 params,
    uint32_t* future_native_consumer_ok,
    uint64_t* future_native_consumer_hash,
    uint32_t* future_native_single_field_mirror_ok,
    uint64_t* future_native_single_field_mirror_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= params.row_count) {
    return;
  }
  const PremapFutureKernelNativeConsumerResultV1 result =
      premap_typed_consumer_future_native_consume_row_v1(
          params, idx, kTypedSchemaHashHi, kTypedSchemaHashLo);
  future_native_consumer_ok[idx] = result.ok;
  future_native_consumer_hash[idx] = result.row_hash;
  future_native_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_launch_kernel(
    PremapFutureKernelNativeConsumerLaunchV1 launch,
    uint32_t* future_native_launch_consumer_ok,
    uint64_t* future_native_launch_consumer_hash,
    uint32_t* future_native_launch_single_field_mirror_ok,
    uint64_t* future_native_launch_single_field_mirror_hash) {
  const uint32_t idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= launch.params.row_count) {
    return;
  }
  const PremapFutureKernelNativeConsumerLaunchResultV1 result =
      premap_typed_consumer_future_native_launch_consume_row_v1(
          launch, idx, kTypedSchemaHashHi, kTypedSchemaHashLo);
  future_native_launch_consumer_ok[idx] = result.ok;
  future_native_launch_consumer_hash[idx] = result.row_hash;
  future_native_launch_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_launch_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_dispatch_kernel(
    PremapFutureKernelNativeConsumerDispatchV1 dispatch,
    uint32_t* future_native_dispatch_consumer_ok,
    uint64_t* future_native_dispatch_consumer_hash,
    uint64_t* future_native_dispatch_handle_projection_hash,
    uint32_t* future_native_dispatch_single_field_mirror_ok,
    uint64_t* future_native_dispatch_single_field_mirror_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  const bool row_window_valid =
      dispatch.row_limit >= dispatch.row_offset &&
      dispatch.row_limit <= dispatch.launch.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? dispatch.row_limit - dispatch.row_offset : 0;
  if (!row_window_valid) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(dispatch.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const uint32_t row_index = dispatch.row_offset + idx;
  const PremapFutureKernelNativeConsumerDispatchResultV1 result =
      premap_typed_consumer_future_native_dispatch_consume_program_lane_v1(
          dispatch,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_dispatch_consumer_ok[idx] = result.ok;
  future_native_dispatch_consumer_hash[idx] = result.row_hash;
  future_native_dispatch_handle_projection_hash[idx] =
      handle_projection_hash(dispatch.launch.params, row_index);
  future_native_dispatch_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_dispatch_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_dispatch_ptr_kernel(
    PremapFutureKernelNativeConsumerDispatchPtrV1 dispatch_ptr,
    uint32_t* future_native_dispatch_ptr_consumer_ok,
    uint64_t* future_native_dispatch_ptr_consumer_hash,
    uint64_t* future_native_dispatch_ptr_handle_projection_hash,
    uint32_t* future_native_dispatch_ptr_single_field_mirror_ok,
    uint64_t* future_native_dispatch_ptr_single_field_mirror_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  if (!premap_typed_consumer_future_native_dispatch_ptr_packet_matches_v1(
          dispatch_ptr)) {
    return;
  }
  const PremapFutureKernelNativeConsumerDispatchV1 dispatch =
      *dispatch_ptr.dispatch;
  const bool row_window_valid =
      dispatch.row_limit >= dispatch.row_offset &&
      dispatch.row_limit <= dispatch.launch.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? dispatch.row_limit - dispatch.row_offset : 0;
  if (!row_window_valid || dispatch.rows_per_program == 0) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(dispatch.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const uint32_t row_index = dispatch.row_offset + idx;
  const PremapFutureKernelNativeConsumerDispatchResultV1 result =
      premap_typed_consumer_future_native_dispatch_ptr_consume_program_lane_v1(
          dispatch_ptr,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_dispatch_ptr_consumer_ok[idx] = result.ok;
  future_native_dispatch_ptr_consumer_hash[idx] = result.row_hash;
  future_native_dispatch_ptr_handle_projection_hash[idx] =
      handle_projection_hash(dispatch.launch.params, row_index);
  future_native_dispatch_ptr_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_dispatch_ptr_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_arg_slot_kernel(
    PremapFutureKernelNativeConsumerArgSlotV1 arg_slot,
    uint32_t* future_native_arg_slot_consumer_ok,
    uint64_t* future_native_arg_slot_consumer_hash,
    uint64_t* future_native_arg_slot_handle_projection_hash,
    uint32_t* future_native_arg_slot_descriptor_ptr_read_ok,
    uint64_t* future_native_arg_slot_descriptor_ptr_read_hash,
    uint32_t* future_native_arg_slot_packed_weight_descriptor_read_ok,
    uint64_t* future_native_arg_slot_packed_weight_descriptor_read_hash,
    uint32_t* future_native_arg_slot_scale_metadata_handle_read_ok,
    uint64_t* future_native_arg_slot_scale_metadata_handle_read_hash,
    uint32_t* future_native_arg_slot_aux_metadata_handle_read_ok,
    uint64_t* future_native_arg_slot_aux_metadata_handle_read_hash,
    uint32_t* future_native_arg_slot_single_field_mirror_ok,
    uint64_t* future_native_arg_slot_single_field_mirror_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  if (!premap_typed_consumer_future_native_arg_slot_packet_matches_v1(
          arg_slot)) {
    return;
  }
  const PremapFutureKernelNativeConsumerDispatchPtrV1 dispatch_ptr =
      *arg_slot.dispatch_ptr;
  if (!premap_typed_consumer_future_native_dispatch_ptr_packet_matches_v1(
          dispatch_ptr)) {
    return;
  }
  const PremapFutureKernelNativeConsumerDispatchV1 dispatch =
      *dispatch_ptr.dispatch;
  const bool row_window_valid =
      dispatch.row_limit >= dispatch.row_offset &&
      dispatch.row_limit <= dispatch.launch.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? dispatch.row_limit - dispatch.row_offset : 0;
  if (!row_window_valid || dispatch.rows_per_program == 0) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(dispatch.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const uint32_t row_index = dispatch.row_offset + idx;
  const PremapFutureKernelNativeConsumerArgSlotResultV1 result =
      premap_typed_consumer_future_native_arg_slot_consume_program_lane_v1(
          arg_slot,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_arg_slot_consumer_ok[idx] = result.ok;
  future_native_arg_slot_consumer_hash[idx] = result.row_hash;
  future_native_arg_slot_handle_projection_hash[idx] =
      handle_projection_hash(dispatch.launch.params, row_index);
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(
          dispatch.launch.params, row_index);
  const uint32_t field_mask = dispatch.launch.params.field_mask;
  const uint32_t descriptor_ptr_visible =
      static_cast<uint32_t>(
          (field_mask & kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr) !=
              0 &&
          row.descriptor_ptr != 0);
  const uint32_t packed_weight_descriptor_visible =
      static_cast<uint32_t>(
          (field_mask &
           kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor) != 0 &&
          row.packed_weight_descriptor != 0);
  const uint32_t scale_metadata_handle_visible =
      static_cast<uint32_t>(
          (field_mask &
           kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle) != 0 &&
          row.scale_metadata_handle != 0);
  const uint32_t aux_metadata_handle_visible =
      static_cast<uint32_t>(
          (field_mask & kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) !=
              0 &&
          row.aux_metadata_handle != 0);
  future_native_arg_slot_descriptor_ptr_read_ok[idx] =
      descriptor_ptr_visible;
  future_native_arg_slot_descriptor_ptr_read_hash[idx] =
      descriptor_ptr_visible
          ? (mix64(row.descriptor_ptr + 0xd35c000000000001ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_arg_slot_packed_weight_descriptor_read_ok[idx] =
      packed_weight_descriptor_visible;
  future_native_arg_slot_packed_weight_descriptor_read_hash[idx] =
      packed_weight_descriptor_visible
          ? (mix64(row.packed_weight_descriptor + 0xd35c000000000002ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_arg_slot_scale_metadata_handle_read_ok[idx] =
      scale_metadata_handle_visible;
  future_native_arg_slot_scale_metadata_handle_read_hash[idx] =
      scale_metadata_handle_visible
          ? (mix64(row.scale_metadata_handle + 0xd35c000000000003ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_arg_slot_aux_metadata_handle_read_ok[idx] =
      aux_metadata_handle_visible;
  future_native_arg_slot_aux_metadata_handle_read_hash[idx] =
      aux_metadata_handle_visible
          ? (mix64(row.aux_metadata_handle + 0xd35c000000000004ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_arg_slot_single_field_mirror_ok[idx] =
      result.single_field_mirror_checked != 0 ? result.single_field_mirror_ok : 0;
  future_native_arg_slot_single_field_mirror_hash[idx] =
      result.single_field_mirror_hash;
}

__global__ void typed_consumer_future_native_consumer_view_kernel(
    PremapFutureKernelNativeConsumerViewV1 view,
    uint32_t* future_native_consumer_view_ok,
    uint64_t* future_native_consumer_view_hash,
    uint64_t* future_native_consumer_view_handle_projection_hash,
    uint32_t* future_native_consumer_view_descriptor_ptr_read_ok,
    uint64_t* future_native_consumer_view_descriptor_ptr_read_hash,
    uint32_t* future_native_consumer_view_packed_weight_descriptor_read_ok,
    uint64_t* future_native_consumer_view_packed_weight_descriptor_read_hash,
    uint32_t* future_native_consumer_view_scale_metadata_handle_read_ok,
    uint64_t* future_native_consumer_view_scale_metadata_handle_read_hash,
    uint32_t* future_native_consumer_view_aux_metadata_handle_read_ok,
    uint64_t* future_native_consumer_view_aux_metadata_handle_read_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  const bool row_window_valid =
      view.row_limit >= view.row_offset &&
      view.row_limit <= view.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? view.row_limit - view.row_offset : 0;
  if (!row_window_valid || view.rows_per_program == 0) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(view.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const uint32_t row_index = view.row_offset + idx;
  const PremapFutureKernelNativeConsumerViewResultV1 result =
      premap_typed_consumer_future_native_view_consume_program_lane_v1(
          view,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_consumer_view_ok[idx] = result.ok;
  future_native_consumer_view_hash[idx] = result.row_hash;
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(view.params, row_index);
  future_native_consumer_view_handle_projection_hash[idx] =
      handle_projection_hash(view.params, row_index);
  const uint32_t field_mask = view.params.field_mask;
  const uint32_t descriptor_ptr_visible =
      static_cast<uint32_t>(
          (field_mask & kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr) !=
              0 &&
          row.descriptor_ptr != 0);
  const uint32_t packed_weight_descriptor_visible =
      static_cast<uint32_t>(
          (field_mask &
           kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor) != 0 &&
          row.packed_weight_descriptor != 0);
  const uint32_t scale_metadata_handle_visible =
      static_cast<uint32_t>(
          (field_mask &
           kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle) != 0 &&
          row.scale_metadata_handle != 0);
  const uint32_t aux_metadata_handle_visible =
      static_cast<uint32_t>(
          (field_mask & kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) !=
              0 &&
          row.aux_metadata_handle != 0);
  future_native_consumer_view_descriptor_ptr_read_ok[idx] =
      descriptor_ptr_visible;
  future_native_consumer_view_descriptor_ptr_read_hash[idx] =
      descriptor_ptr_visible
          ? (mix64(row.descriptor_ptr + 0xc051000000000101ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_consumer_view_packed_weight_descriptor_read_ok[idx] =
      packed_weight_descriptor_visible;
  future_native_consumer_view_packed_weight_descriptor_read_hash[idx] =
      packed_weight_descriptor_visible
          ? (mix64(row.packed_weight_descriptor + 0xc051000000000102ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_consumer_view_scale_metadata_handle_read_ok[idx] =
      scale_metadata_handle_visible;
  future_native_consumer_view_scale_metadata_handle_read_hash[idx] =
      scale_metadata_handle_visible
          ? (mix64(row.scale_metadata_handle + 0xc051000000000103ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_consumer_view_aux_metadata_handle_read_ok[idx] =
      aux_metadata_handle_visible;
  future_native_consumer_view_aux_metadata_handle_read_hash[idx] =
      aux_metadata_handle_visible
          ? (mix64(row.aux_metadata_handle + 0xc051000000000104ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
}

__global__ void typed_consumer_future_native_consumer_program_view_kernel(
    PremapFutureKernelNativeConsumerProgramViewV1 program_view,
    uint32_t* future_native_consumer_program_view_ok,
    uint64_t* future_native_consumer_program_view_hash,
    uint64_t* future_native_consumer_program_view_handle_projection_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  const bool row_window_valid =
      program_view.view.row_limit >= program_view.view.row_offset &&
      program_view.view.row_limit <= program_view.view.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? program_view.view.row_limit - program_view.view.row_offset
                       : 0;
  if (!row_window_valid || program_view.view.rows_per_program == 0) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(program_view.view.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const uint32_t row_index = program_view.view.row_offset + idx;
  const PremapFutureKernelNativeConsumerProgramViewResultV1 result =
      premap_typed_consumer_future_native_program_view_consume_program_lane_v1(
          program_view,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_consumer_program_view_ok[idx] = result.ok;
  future_native_consumer_program_view_hash[idx] = result.row_hash;
  future_native_consumer_program_view_handle_projection_hash[idx] =
      handle_projection_hash(program_view.view.params, row_index);
}

__global__ void typed_consumer_future_native_consumer_program_view_ptr_kernel(
    PremapFutureKernelNativeConsumerProgramViewPtrV1 program_view_ptr,
    uint32_t* future_native_consumer_program_view_ptr_ok,
    uint64_t* future_native_consumer_program_view_ptr_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  if (program_view_ptr.program_view == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerProgramViewV1& program_view =
      *program_view_ptr.program_view;
  const bool row_window_valid =
      program_view.view.row_limit >= program_view.view.row_offset &&
      program_view.view.row_limit <= program_view.view.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? program_view.view.row_limit - program_view.view.row_offset
                       : 0;
  if (!row_window_valid || program_view.view.rows_per_program == 0) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(program_view.view.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const PremapFutureKernelNativeConsumerProgramViewPtrResultV1 result =
      premap_typed_consumer_future_native_program_view_ptr_consume_program_lane_v1(
          program_view_ptr,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_consumer_program_view_ptr_ok[idx] = result.ok;
  future_native_consumer_program_view_ptr_hash[idx] = result.row_hash;
}

__global__ void typed_consumer_future_native_consumer_kernel_arg_packet_kernel(
    PremapFutureKernelNativeConsumerKernelArgPacketV1 kernel_arg_packet,
    uint32_t* future_native_consumer_kernel_arg_packet_ok,
    uint64_t* future_native_consumer_kernel_arg_packet_hash,
    uint32_t* future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok,
    uint64_t* future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash,
    uint32_t*
        future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok,
    uint64_t*
        future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash,
    uint32_t*
        future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok,
    uint64_t*
        future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash,
    uint32_t*
        future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok,
    uint64_t*
        future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash) {
  const uint32_t program_id = static_cast<uint32_t>(blockIdx.x);
  const uint32_t lane_id = static_cast<uint32_t>(threadIdx.x);
  if (kernel_arg_packet.program_view_ptr == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerProgramViewPtrV1& program_view_ptr =
      *kernel_arg_packet.program_view_ptr;
  if (program_view_ptr.program_view == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerProgramViewV1& program_view =
      *program_view_ptr.program_view;
  const bool row_window_valid =
      program_view.view.row_limit >= program_view.view.row_offset &&
      program_view.view.row_limit <= program_view.view.params.row_count;
  const uint32_t active_rows =
      row_window_valid ? program_view.view.row_limit - program_view.view.row_offset
                       : 0;
  if (!row_window_valid || program_view.view.rows_per_program == 0) {
    return;
  }
  const uint64_t local_row_index_64 =
      static_cast<uint64_t>(program_id) *
          static_cast<uint64_t>(program_view.view.rows_per_program) +
      static_cast<uint64_t>(lane_id);
  if (local_row_index_64 >= static_cast<uint64_t>(active_rows)) {
    return;
  }
  const uint32_t idx = static_cast<uint32_t>(local_row_index_64);
  const PremapFutureKernelNativeConsumerKernelArgPacketResultV1 result =
      premap_typed_consumer_future_native_kernel_arg_packet_consume_program_lane_v1(
          kernel_arg_packet,
          program_id,
          lane_id,
          static_cast<uint32_t>(gridDim.x),
          static_cast<uint32_t>(blockDim.x),
          kTypedSchemaHashHi,
          kTypedSchemaHashLo);
  future_native_consumer_kernel_arg_packet_ok[idx] = result.ok;
  future_native_consumer_kernel_arg_packet_hash[idx] = result.row_hash;
  const uint32_t row_index =
      program_view.view.row_offset + static_cast<uint32_t>(local_row_index_64);
  const PremapKernelSideTypedConsumerRowV1 row =
      premap_typed_consumer_load_future_native_row_v1(
          program_view.view.params, row_index);
  const uint32_t field_mask = program_view.view.params.field_mask;
  const uint32_t descriptor_ptr_visible =
      static_cast<uint32_t>(
          (field_mask & kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr) !=
              0 &&
          row.descriptor_ptr != 0);
  const uint32_t packed_weight_descriptor_visible =
      static_cast<uint32_t>(
          (field_mask &
           kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor) != 0 &&
          row.packed_weight_descriptor != 0);
  const uint32_t scale_metadata_handle_visible =
      static_cast<uint32_t>(
          (field_mask &
           kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle) != 0 &&
          row.scale_metadata_handle != 0);
  const uint32_t aux_metadata_handle_visible =
      static_cast<uint32_t>(
          (field_mask & kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) !=
              0 &&
          row.aux_metadata_handle != 0);
  future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok[idx] =
      descriptor_ptr_visible;
  future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash[idx] =
      descriptor_ptr_visible
          ? (mix64(row.descriptor_ptr + 0xc054000000000101ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok[idx] =
      packed_weight_descriptor_visible;
  future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash[idx] =
      packed_weight_descriptor_visible
          ? (mix64(row.packed_weight_descriptor + 0xc054000000000102ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok[idx] =
      scale_metadata_handle_visible;
  future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash[idx] =
      scale_metadata_handle_visible
          ? (mix64(row.scale_metadata_handle + 0xc054000000000103ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
  future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok[idx] =
      aux_metadata_handle_visible;
  future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash[idx] =
      aux_metadata_handle_visible
          ? (mix64(row.aux_metadata_handle + 0xc054000000000104ULL) ^
             mix64(row.address_key_hash + static_cast<uint64_t>(row_index)))
          : 0ULL;
}

__device__ static inline PremapFutureKernelNativeConsumerKernelEntrySummaryV1
premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
    const PremapFutureKernelNativeConsumerKernelArgPacketV1& kernel_arg_packet) {
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
  out.abi_version =
      kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
  out.payload_bytes = 0;
  out.passed_to_kernel = 0;
  out.changes_kernel_launch_args = 0;
  out.current_wna16_arg_compatible = 0;
  out.requires_wna16_arg_reinterpretation = 0;

  const bool packet_valid =
      premap_typed_consumer_future_native_kernel_arg_packet_matches_v1(
          kernel_arg_packet);
  out.packet_valid = static_cast<uint32_t>(packet_valid);
  if (!packet_valid || kernel_arg_packet.program_view_ptr == nullptr) {
    out.error_count = 1;
    return out;
  }

  const PremapFutureKernelNativeConsumerProgramViewPtrV1& program_view_ptr =
      *kernel_arg_packet.program_view_ptr;
  if (program_view_ptr.program_view == nullptr) {
    out.error_count = 1;
    return out;
  }

  const PremapFutureKernelNativeConsumerProgramViewV1& program_view =
      *program_view_ptr.program_view;
  const PremapFutureKernelNativeConsumerViewV1& view = program_view.view;
  const bool row_window_valid =
      view.row_limit >= view.row_offset && view.row_limit <= view.params.row_count &&
      view.rows_per_program > 0 && program_view.program_count > 0;
  if (!row_window_valid) {
    out.error_count = 1;
    out.field_mask = view.params.field_mask;
    return out;
  }

  const uint32_t active_rows = view.row_limit - view.row_offset;
  out.row_count = active_rows;
  out.field_mask = view.params.field_mask;
  for (uint32_t local_row_index = 0; local_row_index < active_rows;
       ++local_row_index) {
    const uint32_t program_id = local_row_index / view.rows_per_program;
    const uint32_t lane_id = local_row_index % view.rows_per_program;
    const PremapFutureKernelNativeConsumerKernelArgPacketResultV1 result =
        premap_typed_consumer_future_native_kernel_arg_packet_consume_program_lane_v1(
            kernel_arg_packet,
            program_id,
            lane_id,
            program_view.program_count,
            view.rows_per_program,
            kTypedSchemaHashHi,
            kTypedSchemaHashLo);
    out.row_ok_count += result.ok == 1 ? 1 : 0;
    out.row_hash_accumulator ^=
        mix64(result.row_hash + static_cast<uint64_t>(local_row_index));

    const uint32_t row_index = view.row_offset + local_row_index;
    const PremapKernelSideTypedConsumerRowV1 row =
        premap_typed_consumer_load_future_native_row_v1(view.params, row_index);
    const uint32_t descriptor_ptr_visible =
        static_cast<uint32_t>(
            (view.params.field_mask &
             kPremapFutureKernelSideConsumerFieldMaskDescriptorPtr) != 0 &&
            row.descriptor_ptr != 0);
    const uint32_t packed_weight_descriptor_visible =
        static_cast<uint32_t>(
            (view.params.field_mask &
             kPremapFutureKernelSideConsumerFieldMaskPackedWeightDescriptor) !=
                0 &&
            row.packed_weight_descriptor != 0);
    const uint32_t scale_metadata_handle_visible =
        static_cast<uint32_t>(
            (view.params.field_mask &
             kPremapFutureKernelSideConsumerFieldMaskScaleMetadataHandle) != 0 &&
            row.scale_metadata_handle != 0);
    const uint32_t aux_metadata_handle_visible =
        static_cast<uint32_t>(
            (view.params.field_mask &
             kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) != 0 &&
            row.aux_metadata_handle != 0);
    const uint32_t expert_id_visible =
        static_cast<uint32_t>(row.expert_id >= 0);
    const uint32_t address_key_hash_visible =
        static_cast<uint32_t>(row.address_key_hash != 0);
    const uint32_t row_metadata_visible =
        static_cast<uint32_t>(expert_id_visible != 0 &&
                              address_key_hash_visible != 0 &&
                              row.row_index == row_index);

    out.descriptor_ptr_read_ok_count += descriptor_ptr_visible;
    out.packed_weight_descriptor_read_ok_count +=
        packed_weight_descriptor_visible;
    out.scale_metadata_handle_read_ok_count += scale_metadata_handle_visible;
    out.aux_metadata_handle_read_ok_count += aux_metadata_handle_visible;
    out.expert_id_read_ok_count += expert_id_visible;
    out.address_key_hash_read_ok_count += address_key_hash_visible;
    out.row_metadata_read_ok_count += row_metadata_visible;
    out.field_read_hash_accumulator ^=
        mix64(row.descriptor_ptr + 0xce17000000000101ULL) ^
        mix64(row.packed_weight_descriptor + 0xce17000000000102ULL) ^
        mix64(row.scale_metadata_handle + 0xce17000000000103ULL) ^
        mix64(row.aux_metadata_handle + 0xce17000000000104ULL) ^
        mix64(row.address_key_hash + static_cast<uint64_t>(row_index));
    out.row_metadata_hash_accumulator ^=
        mix64(static_cast<uint64_t>(row.row_index) + 0xce17000000000201ULL) ^
        mix64(static_cast<uint64_t>(row.expert_id) + 0xce17000000000202ULL) ^
        mix64(row.address_key_hash + 0xce17000000000203ULL);
  }

  const uint32_t expected_aux_rows =
      (view.params.field_mask &
       kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) != 0
          ? active_rows
          : 0;
  out.error_count =
      (out.packet_valid == 1 ? 0 : 1) + (active_rows - out.row_ok_count) +
      (active_rows - out.descriptor_ptr_read_ok_count) +
      (active_rows - out.packed_weight_descriptor_read_ok_count) +
      (active_rows - out.scale_metadata_handle_read_ok_count) +
      (expected_aux_rows - out.aux_metadata_handle_read_ok_count) +
      (active_rows - out.expert_id_read_ok_count) +
      (active_rows - out.address_key_hash_read_ok_count) +
      (active_rows - out.row_metadata_read_ok_count);
  return out;
}

__global__ void
typed_consumer_future_native_consumer_kernel_entry_summary_kernel(
    PremapFutureKernelNativeConsumerKernelArgPacketV1 kernel_arg_packet,
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1* summary) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || summary == nullptr) {
    return;
  }
  *summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          kernel_arg_packet);
}

__global__ void
typed_consumer_future_native_consumer_kernel_entry_args_kernel(
    PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || entry_args.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_kernel_entry_args_matches_v1(
          entry_args)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *entry_args.summary = out;
    return;
  }
  *entry_args.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void
typed_consumer_future_native_consumer_kernel_entry_args_ptr_kernel(
    const PremapFutureKernelNativeConsumerKernelEntryArgsV1* entry_args) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || entry_args == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 local = *entry_args;
  if (local.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_kernel_entry_args_matches_v1(local)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *local.kernel_arg_packet);
}

__device__ static inline void
premap_typed_consumer_future_native_consumer_launch_envelope_args_write_summary_v1(
    PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args) {
  if (launch_args.entry_args == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 local =
      *launch_args.entry_args;
  if (local.summary == nullptr) {
    return;
  }

  bool row_window_matches_program_view = false;
  if (local.kernel_arg_packet != nullptr) {
    const PremapFutureKernelNativeConsumerKernelArgPacketV1 kernel_arg_packet =
        *local.kernel_arg_packet;
    if (kernel_arg_packet.program_view_ptr != nullptr) {
      const PremapFutureKernelNativeConsumerProgramViewPtrV1 program_view_ptr =
          *kernel_arg_packet.program_view_ptr;
      if (program_view_ptr.program_view != nullptr) {
        const PremapFutureKernelNativeConsumerProgramViewV1 program_view =
            *program_view_ptr.program_view;
        row_window_matches_program_view =
            program_view.program_count == launch_args.grid_x &&
            program_view.view.rows_per_program == launch_args.rows_per_program &&
            program_view.view.row_offset == launch_args.row_offset &&
            program_view.view.row_limit == launch_args.row_limit;
      }
    }
  }

  if (!premap_typed_consumer_future_native_launch_envelope_args_matches_v1(
          launch_args) ||
      !premap_typed_consumer_future_native_kernel_entry_args_matches_v1(local) ||
      !row_window_matches_program_view) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *local.kernel_arg_packet);
}

__global__ void
typed_consumer_future_native_consumer_launch_envelope_args_kernel(
    PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }
  premap_typed_consumer_future_native_consumer_launch_envelope_args_write_summary_v1(
      launch_args);
}

__global__ void
typed_consumer_future_native_consumer_launch_envelope_args_ptr_kernel(
    const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1*
        launch_args_ptr) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || launch_args_ptr == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 local =
      *launch_args_ptr;
  if (!premap_typed_consumer_future_native_launch_envelope_args_ptr_matches_v1(
          local) ||
      local.launch_args == nullptr) {
    if (local.launch_args != nullptr) {
      const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
          *local.launch_args;
      if (launch_args.entry_args != nullptr) {
        const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
            *launch_args.entry_args;
        if (entry_args.summary != nullptr) {
          PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
          out.abi_version =
              kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
          out.payload_bytes = 0;
          out.passed_to_kernel = 0;
          out.changes_kernel_launch_args = 0;
          out.current_wna16_arg_compatible = 0;
          out.requires_wna16_arg_reinterpretation = 0;
          out.error_count = 1;
          *entry_args.summary = out;
        }
      }
    }
    return;
  }
  premap_typed_consumer_future_native_consumer_launch_envelope_args_write_summary_v1(
      *local.launch_args);
}

__global__ void
typed_consumer_future_native_consumer_kernel_launch_descriptor_kernel(
    const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1*
        launch_descriptor) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || launch_descriptor == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 local =
      *launch_descriptor;
  if (local.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_kernel_launch_descriptor_matches_v1(
          local)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *local.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void
typed_consumer_future_native_consumer_kernel_launch_context_kernel(
    const PremapFutureKernelNativeConsumerKernelLaunchContextV1* context) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || context == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerKernelLaunchContextV1 local = *context;
  if (local.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_kernel_launch_context_matches_v1(
          local)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 descriptor =
      *local.launch_descriptor;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *descriptor.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_invocation_kernel(
    const PremapFutureKernelNativeConsumerInvocationV1* invocation) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || invocation == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerInvocationV1 local = *invocation;
  if (local.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_invocation_matches_v1(local)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerKernelLaunchContextV1 context =
      *local.context;
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 descriptor =
      *context.launch_descriptor;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *descriptor.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_invocation_entry_kernel(
    PremapFutureKernelNativeConsumerInvocationV1 invocation) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }
  if (invocation.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_invocation_matches_v1(invocation)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *invocation.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerKernelLaunchContextV1 context =
      *invocation.context;
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 descriptor =
      *context.launch_descriptor;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *descriptor.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *invocation.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_endpoint_kernel(
    PremapFutureKernelNativeConsumerEndpointV1 endpoint) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }
  if (endpoint.invocation.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_endpoint_matches_v1(endpoint)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *endpoint.invocation.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerKernelLaunchContextV1 context =
      *endpoint.invocation.context;
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 descriptor =
      *context.launch_descriptor;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *descriptor.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *endpoint.invocation.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_endpoint_ptr_kernel(
    PremapFutureKernelNativeConsumerEndpointPtrV1 endpoint_ptr) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }
  if (endpoint_ptr.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_endpoint_ptr_matches_v1(
          endpoint_ptr)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *endpoint_ptr.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerEndpointV1 endpoint =
      *endpoint_ptr.endpoint;
  const PremapFutureKernelNativeConsumerKernelLaunchContextV1 context =
      *endpoint.invocation.context;
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 descriptor =
      *context.launch_descriptor;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *descriptor.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *endpoint_ptr.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void
typed_consumer_future_native_consumer_wna16_adjacent_typed_slot_kernel(
    PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1 slot) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }
  if (slot.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_wna16_adjacent_typed_slot_matches_v1(
          slot)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *slot.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerEndpointPtrV1 endpoint_ptr =
      slot.endpoint_ptr;
  const PremapFutureKernelNativeConsumerEndpointV1 endpoint =
      *endpoint_ptr.endpoint;
  const PremapFutureKernelNativeConsumerKernelLaunchContextV1 context =
      *endpoint.invocation.context;
  const PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1 descriptor =
      *context.launch_descriptor;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1 launch_args_ptr =
      *descriptor.launch_args_ptr;
  const PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1 launch_args =
      *launch_args_ptr.launch_args;
  const PremapFutureKernelNativeConsumerKernelEntryArgsV1 entry_args =
      *launch_args.entry_args;
  *slot.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *entry_args.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_request_ptr_kernel(
    const PremapFutureKernelNativeConsumerRequestPtrV1* request) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || request == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerRequestPtrV1 local = *request;
  if (local.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_request_ptr_matches_v1(local)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *local.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_request_launch_kernel(
    const PremapFutureKernelNativeConsumerRequestLaunchV1* launch) {
  if (blockIdx.x != 0 || threadIdx.x != 0 || launch == nullptr) {
    return;
  }
  const PremapFutureKernelNativeConsumerRequestLaunchV1 local = *launch;
  if (local.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_request_launch_matches_v1(local)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *local.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerRequestPtrV1 request =
      *local.request_ptr;
  *local.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *request.kernel_arg_packet);
}

__global__ void typed_consumer_future_native_consumer_request_launch_ptr_kernel(
    PremapFutureKernelNativeConsumerRequestLaunchPtrV1 launch_ptr) {
  if (blockIdx.x != 0 || threadIdx.x != 0) {
    return;
  }
  if (launch_ptr.summary == nullptr) {
    return;
  }
  if (!premap_typed_consumer_future_native_request_launch_ptr_matches_v1(
          launch_ptr)) {
    PremapFutureKernelNativeConsumerKernelEntrySummaryV1 out{};
    out.abi_version =
        kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
    out.payload_bytes = 0;
    out.passed_to_kernel = 0;
    out.changes_kernel_launch_args = 0;
    out.current_wna16_arg_compatible = 0;
    out.requires_wna16_arg_reinterpretation = 0;
    out.error_count = 1;
    *launch_ptr.summary = out;
    return;
  }
  const PremapFutureKernelNativeConsumerRequestLaunchV1 launch =
      *launch_ptr.request_launch;
  const PremapFutureKernelNativeConsumerRequestPtrV1 request =
      *launch.request_ptr;
  *launch_ptr.summary =
      premap_typed_consumer_build_future_native_kernel_entry_summary_v1(
          *request.kernel_arg_packet);
}

struct Args {
  int device = 0;
  int rows = 1024;
  int block_threads = 256;
  int dispatch_row_offset = 0;
  int dispatch_row_limit = -1;
  std::string input_prefix;
  bool omit_aux_pointer = false;
  bool fault_kernel_launch_descriptor_schema_hash = false;
  bool fault_invocation_device_ordinal = false;
  bool fault_invocation_stream_domain = false;
};

static Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    std::string key(argv[i]);
    auto require_value = [&](const char* name) -> const char* {
      if (i + 1 >= argc) {
        std::cerr << "missing value for " << name << "\n";
        std::exit(2);
      }
      return argv[++i];
    };
    if (key == "--device") {
      args.device = std::atoi(require_value("--device"));
    } else if (key == "--rows") {
      args.rows = std::atoi(require_value("--rows"));
    } else if (key == "--block-threads") {
      args.block_threads = std::atoi(require_value("--block-threads"));
    } else if (key == "--dispatch-row-offset") {
      args.dispatch_row_offset = std::atoi(require_value("--dispatch-row-offset"));
    } else if (key == "--dispatch-row-limit") {
      args.dispatch_row_limit = std::atoi(require_value("--dispatch-row-limit"));
    } else if (key == "--input-prefix") {
      args.input_prefix = require_value("--input-prefix");
    } else if (key == "--omit-aux-pointer") {
      args.omit_aux_pointer = true;
    } else if (key == "--fault-kernel-launch-descriptor-schema-hash") {
      args.fault_kernel_launch_descriptor_schema_hash = true;
    } else if (key == "--fault-invocation-device-ordinal") {
      args.fault_invocation_device_ordinal = true;
    } else if (key == "--fault-invocation-stream-domain") {
      args.fault_invocation_stream_domain = true;
    } else {
      std::cerr << "unknown argument: " << key << "\n";
      std::exit(2);
    }
  }
  if (args.rows <= 0 || args.block_threads <= 0) {
    std::cerr << "rows and block-threads must be positive\n";
    std::exit(2);
  }
  const int effective_dispatch_limit =
      args.dispatch_row_limit < 0 ? args.rows : args.dispatch_row_limit;
  if (args.dispatch_row_offset < 0 || effective_dispatch_limit <= args.dispatch_row_offset ||
      effective_dispatch_limit > args.rows) {
    std::cerr << "dispatch row window must satisfy 0 <= offset < limit <= rows\n";
    std::exit(2);
  }
  args.dispatch_row_limit = effective_dispatch_limit;
  return args;
}

template <typename T>
static void read_binary_array(const std::string& path, std::vector<T>& values) {
  std::ifstream stream(path, std::ios::binary);
  if (!stream) {
    std::cerr << "failed to open input array: " << path << "\n";
    std::exit(2);
  }
  stream.read(
      reinterpret_cast<char*>(values.data()),
      static_cast<std::streamsize>(values.size() * sizeof(T)));
  if (!stream) {
    std::cerr << "failed to read complete input array: " << path << "\n";
    std::exit(2);
  }
}

static std::string macro_json() {
  std::ostringstream os;
  os << "{";
  os << "\"MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI)
     << "true";
#else
     << "false";
#endif
  os << ",\"MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI)
     << "true";
#else
     << "false";
#endif
  os << "}";
  return os.str();
}

int main(int argc, char** argv) {
  const Args args = parse_args(argc, argv);
  const uint32_t requested_device_ordinal =
      static_cast<uint32_t>(args.device);
  const uint32_t invocation_device_ordinal =
      args.fault_invocation_device_ordinal
          ? (requested_device_ordinal ^ uint32_t{1})
          : requested_device_ordinal;
  const uint32_t invocation_stream_domain =
      args.fault_invocation_stream_domain ? uint32_t{1} : uint32_t{0};
  hip_check(hipSetDevice(args.device), "hipSetDevice");

  const int rows = args.rows;
  std::vector<uint64_t> descriptor(rows);
  std::vector<uint64_t> packed(rows);
  std::vector<uint64_t> scale(rows);
  std::vector<uint64_t> aux(rows);
  std::vector<int32_t> expert(rows);
  std::vector<uint64_t> address_key(rows);
  if (!args.input_prefix.empty()) {
    read_binary_array(args.input_prefix + ".descriptor_ptr.u64", descriptor);
    read_binary_array(args.input_prefix + ".packed_weight_descriptor.u64", packed);
    read_binary_array(args.input_prefix + ".scale_metadata_handle.u64", scale);
    read_binary_array(args.input_prefix + ".aux_metadata_handle.u64", aux);
    read_binary_array(args.input_prefix + ".expert_id.i32", expert);
    read_binary_array(args.input_prefix + ".address_key_hash.u64", address_key);
  } else {
    for (int i = 0; i < rows; ++i) {
      descriptor[i] = 0x100000000ULL + static_cast<uint64_t>(i) * 4096ULL;
      packed[i] = 0x200000000ULL + static_cast<uint64_t>(i) * 2048ULL;
      scale[i] = 0x300000000ULL + static_cast<uint64_t>(i) * 1024ULL;
      aux[i] = 0x400000000ULL + static_cast<uint64_t>(i) * 512ULL;
      expert[i] = static_cast<int32_t>(i % 256);
      address_key[i] = mix64(
          1ULL + static_cast<uint64_t>(expert[i]) + (static_cast<uint64_t>(i) << 16));
    }
  }

  uint64_t *d_descriptor = nullptr, *d_packed = nullptr, *d_scale = nullptr,
           *d_aux = nullptr, *d_address_key = nullptr, *d_hash = nullptr,
           *d_single_field_mirror_hash = nullptr,
           *d_kernel_side_consumer_path_hash = nullptr,
           *d_kernel_side_compatible_consumer_hash = nullptr,
           *d_future_kernel_consumer_hash = nullptr,
           *d_future_kernel_single_field_mirror_hash = nullptr,
           *d_future_kernel_compatible_path_hash = nullptr,
           *d_future_native_consumer_hash = nullptr,
           *d_future_native_single_field_mirror_hash = nullptr,
           *d_future_native_launch_consumer_hash = nullptr,
           *d_future_native_launch_single_field_mirror_hash = nullptr,
           *d_future_native_dispatch_consumer_hash = nullptr,
           *d_future_native_dispatch_handle_projection_hash = nullptr,
           *d_future_native_dispatch_single_field_mirror_hash = nullptr,
           *d_future_native_dispatch_ptr_consumer_hash = nullptr,
           *d_future_native_dispatch_ptr_handle_projection_hash = nullptr,
           *d_future_native_dispatch_ptr_single_field_mirror_hash = nullptr,
           *d_future_native_arg_slot_consumer_hash = nullptr,
           *d_future_native_arg_slot_handle_projection_hash = nullptr,
           *d_future_native_arg_slot_descriptor_ptr_read_hash = nullptr,
           *d_future_native_arg_slot_packed_weight_descriptor_read_hash = nullptr,
           *d_future_native_arg_slot_scale_metadata_handle_read_hash = nullptr,
           *d_future_native_arg_slot_aux_metadata_handle_read_hash = nullptr,
           *d_future_native_arg_slot_single_field_mirror_hash = nullptr,
           *d_future_native_consumer_view_hash = nullptr,
           *d_future_native_consumer_view_handle_projection_hash = nullptr,
           *d_future_native_consumer_view_descriptor_ptr_read_hash = nullptr,
           *d_future_native_consumer_view_packed_weight_descriptor_read_hash = nullptr,
           *d_future_native_consumer_view_scale_metadata_handle_read_hash = nullptr,
           *d_future_native_consumer_view_aux_metadata_handle_read_hash = nullptr,
           *d_future_native_consumer_program_view_hash = nullptr,
           *d_future_native_consumer_program_view_handle_projection_hash = nullptr,
           *d_future_native_consumer_program_view_ptr_hash = nullptr,
           *d_future_native_consumer_kernel_arg_packet_hash = nullptr,
           *d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash =
               nullptr,
           *d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash =
               nullptr,
           *d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash =
               nullptr,
           *d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash =
               nullptr;
  PremapFutureKernelNativeConsumerDispatchV1* d_future_native_dispatch_packet =
      nullptr;
  PremapFutureKernelNativeConsumerDispatchPtrV1*
      d_future_native_dispatch_ptr_packet = nullptr;
  PremapFutureKernelNativeConsumerProgramViewV1*
      d_future_native_consumer_program_view_packet = nullptr;
  PremapFutureKernelNativeConsumerProgramViewPtrV1*
      d_future_native_consumer_program_view_ptr_packet = nullptr;
  PremapFutureKernelNativeConsumerKernelArgPacketV1*
      d_future_native_consumer_kernel_arg_packet = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_kernel_entry_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_kernel_entry_args_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_kernel_entry_args_ptr_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_launch_envelope_args_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_launch_envelope_args_ptr_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_kernel_launch_descriptor_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntryArgsV1*
      d_future_native_consumer_kernel_entry_args = nullptr;
  PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1*
      d_future_native_consumer_launch_envelope_args_packet = nullptr;
  PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1*
      d_future_native_consumer_launch_envelope_args_ptr_packet = nullptr;
  PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1*
      d_future_native_consumer_kernel_launch_descriptor_packet = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_kernel_launch_context_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelLaunchContextV1*
      d_future_native_consumer_kernel_launch_context_packet = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_invocation_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_invocation_entry_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_endpoint_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_endpoint_ptr_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_wna16_adjacent_typed_slot_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_request_ptr_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_request_launch_summary = nullptr;
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1*
      d_future_native_consumer_request_launch_ptr_summary = nullptr;
  PremapFutureKernelNativeConsumerInvocationV1*
      d_future_native_consumer_invocation_packet = nullptr;
  PremapFutureKernelNativeConsumerEndpointV1*
      d_future_native_consumer_endpoint_packet = nullptr;
  PremapFutureKernelNativeConsumerRequestPtrV1*
      d_future_native_consumer_request_ptr_packet = nullptr;
  PremapFutureKernelNativeConsumerRequestLaunchV1*
      d_future_native_consumer_request_launch_packet = nullptr;
  int32_t* d_expert = nullptr;
  uint32_t *d_ok = nullptr, *d_single_field_mirror_ok = nullptr,
           *d_kernel_side_consumer_path_ok = nullptr,
           *d_kernel_side_compatible_consumer_ok = nullptr,
           *d_future_kernel_consumer_ok = nullptr,
           *d_future_kernel_single_field_mirror_ok = nullptr,
           *d_future_kernel_compatible_path_ok = nullptr,
           *d_future_native_consumer_ok = nullptr,
           *d_future_native_single_field_mirror_ok = nullptr,
           *d_future_native_launch_consumer_ok = nullptr,
           *d_future_native_launch_single_field_mirror_ok = nullptr,
           *d_future_native_dispatch_consumer_ok = nullptr,
           *d_future_native_dispatch_single_field_mirror_ok = nullptr,
           *d_future_native_dispatch_ptr_consumer_ok = nullptr,
           *d_future_native_dispatch_ptr_single_field_mirror_ok = nullptr,
           *d_future_native_arg_slot_consumer_ok = nullptr,
           *d_future_native_arg_slot_descriptor_ptr_read_ok = nullptr,
           *d_future_native_arg_slot_packed_weight_descriptor_read_ok = nullptr,
           *d_future_native_arg_slot_scale_metadata_handle_read_ok = nullptr,
           *d_future_native_arg_slot_aux_metadata_handle_read_ok = nullptr,
           *d_future_native_arg_slot_single_field_mirror_ok = nullptr,
           *d_future_native_consumer_view_ok = nullptr,
           *d_future_native_consumer_view_descriptor_ptr_read_ok = nullptr,
           *d_future_native_consumer_view_packed_weight_descriptor_read_ok = nullptr,
           *d_future_native_consumer_view_scale_metadata_handle_read_ok = nullptr,
           *d_future_native_consumer_view_aux_metadata_handle_read_ok = nullptr,
           *d_future_native_consumer_program_view_ok = nullptr,
           *d_future_native_consumer_program_view_ptr_ok = nullptr,
           *d_future_native_consumer_kernel_arg_packet_ok = nullptr,
           *d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok =
               nullptr,
           *d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok =
               nullptr,
           *d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok =
               nullptr,
           *d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok =
               nullptr;
  const size_t u64_bytes = static_cast<size_t>(rows) * sizeof(uint64_t);
  const size_t i32_bytes = static_cast<size_t>(rows) * sizeof(int32_t);
  const size_t u32_bytes = static_cast<size_t>(rows) * sizeof(uint32_t);
  hip_check(hipMalloc(&d_descriptor, u64_bytes), "hipMalloc descriptor");
  hip_check(hipMalloc(&d_packed, u64_bytes), "hipMalloc packed");
  hip_check(hipMalloc(&d_scale, u64_bytes), "hipMalloc scale");
  if (!args.omit_aux_pointer) {
    hip_check(hipMalloc(&d_aux, u64_bytes), "hipMalloc aux");
  }
  hip_check(hipMalloc(&d_address_key, u64_bytes), "hipMalloc address_key");
  hip_check(hipMalloc(&d_expert, i32_bytes), "hipMalloc expert");
  hip_check(hipMalloc(&d_ok, u32_bytes), "hipMalloc ok");
  hip_check(hipMalloc(&d_hash, u64_bytes), "hipMalloc hash");
  hip_check(
      hipMalloc(&d_single_field_mirror_ok, u32_bytes),
      "hipMalloc single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_single_field_mirror_hash, u64_bytes),
      "hipMalloc single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_kernel_side_consumer_path_ok, u32_bytes),
      "hipMalloc kernel_side_consumer_path_ok");
  hip_check(
      hipMalloc(&d_kernel_side_consumer_path_hash, u64_bytes),
      "hipMalloc kernel_side_consumer_path_hash");
  hip_check(
      hipMalloc(&d_kernel_side_compatible_consumer_ok, u32_bytes),
      "hipMalloc kernel_side_compatible_consumer_ok");
  hip_check(
      hipMalloc(&d_kernel_side_compatible_consumer_hash, u64_bytes),
      "hipMalloc kernel_side_compatible_consumer_hash");
  hip_check(
      hipMalloc(&d_future_kernel_consumer_ok, u32_bytes),
      "hipMalloc future_kernel_consumer_ok");
  hip_check(
      hipMalloc(&d_future_kernel_consumer_hash, u64_bytes),
      "hipMalloc future_kernel_consumer_hash");
  hip_check(
      hipMalloc(&d_future_kernel_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_kernel_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_kernel_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_kernel_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_kernel_compatible_path_ok, u32_bytes),
      "hipMalloc future_kernel_compatible_path_ok");
  hip_check(
      hipMalloc(&d_future_kernel_compatible_path_hash, u64_bytes),
      "hipMalloc future_kernel_compatible_path_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_ok, u32_bytes),
      "hipMalloc future_native_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_hash, u64_bytes),
      "hipMalloc future_native_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_launch_consumer_ok, u32_bytes),
      "hipMalloc future_native_launch_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_launch_consumer_hash, u64_bytes),
      "hipMalloc future_native_launch_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_launch_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_launch_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_launch_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_launch_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_consumer_ok, u32_bytes),
      "hipMalloc future_native_dispatch_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_dispatch_consumer_hash, u64_bytes),
      "hipMalloc future_native_dispatch_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_handle_projection_hash, u64_bytes),
      "hipMalloc future_native_dispatch_handle_projection_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_dispatch_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_dispatch_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_ptr_consumer_ok, u32_bytes),
      "hipMalloc future_native_dispatch_ptr_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_dispatch_ptr_consumer_hash, u64_bytes),
      "hipMalloc future_native_dispatch_ptr_consumer_hash");
  hip_check(
      hipMalloc(
          &d_future_native_dispatch_ptr_handle_projection_hash,
          u64_bytes),
      "hipMalloc future_native_dispatch_ptr_handle_projection_hash");
  hip_check(
      hipMalloc(&d_future_native_dispatch_ptr_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_dispatch_ptr_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_dispatch_ptr_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_dispatch_ptr_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_consumer_ok, u32_bytes),
      "hipMalloc future_native_arg_slot_consumer_ok");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_consumer_hash, u64_bytes),
      "hipMalloc future_native_arg_slot_consumer_hash");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_handle_projection_hash, u64_bytes),
      "hipMalloc future_native_arg_slot_handle_projection_hash");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_descriptor_ptr_read_ok, u32_bytes),
      "hipMalloc future_native_arg_slot_descriptor_ptr_read_ok");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_descriptor_ptr_read_hash, u64_bytes),
      "hipMalloc future_native_arg_slot_descriptor_ptr_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_arg_slot_packed_weight_descriptor_read_ok,
          u32_bytes),
      "hipMalloc future_native_arg_slot_packed_weight_descriptor_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_arg_slot_packed_weight_descriptor_read_hash,
          u64_bytes),
      "hipMalloc future_native_arg_slot_packed_weight_descriptor_read_hash");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_scale_metadata_handle_read_ok, u32_bytes),
      "hipMalloc future_native_arg_slot_scale_metadata_handle_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_arg_slot_scale_metadata_handle_read_hash,
          u64_bytes),
      "hipMalloc future_native_arg_slot_scale_metadata_handle_read_hash");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_aux_metadata_handle_read_ok, u32_bytes),
      "hipMalloc future_native_arg_slot_aux_metadata_handle_read_ok");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_aux_metadata_handle_read_hash, u64_bytes),
      "hipMalloc future_native_arg_slot_aux_metadata_handle_read_hash");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_single_field_mirror_ok, u32_bytes),
      "hipMalloc future_native_arg_slot_single_field_mirror_ok");
  hip_check(
      hipMalloc(&d_future_native_arg_slot_single_field_mirror_hash, u64_bytes),
      "hipMalloc future_native_arg_slot_single_field_mirror_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_view_ok, u32_bytes),
      "hipMalloc future_native_consumer_view_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_view_hash, u64_bytes),
      "hipMalloc future_native_consumer_view_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_view_handle_projection_hash, u64_bytes),
      "hipMalloc future_native_consumer_view_handle_projection_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_view_descriptor_ptr_read_ok, u32_bytes),
      "hipMalloc future_native_consumer_view_descriptor_ptr_read_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_view_descriptor_ptr_read_hash, u64_bytes),
      "hipMalloc future_native_consumer_view_descriptor_ptr_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_view_packed_weight_descriptor_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_view_packed_weight_descriptor_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_view_packed_weight_descriptor_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_view_packed_weight_descriptor_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_view_scale_metadata_handle_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_view_scale_metadata_handle_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_view_scale_metadata_handle_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_view_scale_metadata_handle_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_view_aux_metadata_handle_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_view_aux_metadata_handle_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_view_aux_metadata_handle_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_view_aux_metadata_handle_read_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_program_view_ok, u32_bytes),
      "hipMalloc future_native_consumer_program_view_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_program_view_hash, u64_bytes),
      "hipMalloc future_native_consumer_program_view_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_program_view_handle_projection_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_program_view_handle_projection_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_program_view_ptr_ok, u32_bytes),
      "hipMalloc future_native_consumer_program_view_ptr_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_program_view_ptr_hash, u64_bytes),
      "hipMalloc future_native_consumer_program_view_ptr_hash");
  hip_check(
      hipMalloc(&d_future_native_consumer_kernel_arg_packet_ok, u32_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_ok");
  hip_check(
      hipMalloc(&d_future_native_consumer_kernel_arg_packet_hash, u64_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok,
          u32_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash,
          u64_bytes),
      "hipMalloc future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_entry_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_kernel_entry_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_arg_packet,
          sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1)),
      "hipMalloc future_native_consumer_kernel_arg_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_entry_args_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_kernel_entry_args_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_entry_args_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_kernel_entry_args_ptr_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_launch_envelope_args_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_launch_envelope_args_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_launch_envelope_args_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_launch_envelope_args_ptr_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_launch_descriptor_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_kernel_launch_descriptor_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_entry_args,
          sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1)),
      "hipMalloc future_native_consumer_kernel_entry_args");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_launch_envelope_args_packet,
          sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1)),
      "hipMalloc future_native_consumer_launch_envelope_args_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_launch_envelope_args_ptr_packet,
          sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1)),
      "hipMalloc future_native_consumer_launch_envelope_args_ptr_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_launch_descriptor_packet,
          sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1)),
      "hipMalloc future_native_consumer_kernel_launch_descriptor_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_launch_context_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_kernel_launch_context_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_kernel_launch_context_packet,
          sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1)),
      "hipMalloc future_native_consumer_kernel_launch_context_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_invocation_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_invocation_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_invocation_entry_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_invocation_entry_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_endpoint_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_endpoint_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_endpoint_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_endpoint_ptr_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_wna16_adjacent_typed_slot_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_wna16_adjacent_typed_slot_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_request_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_request_ptr_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_request_launch_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_request_launch_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_request_launch_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "hipMalloc future_native_consumer_request_launch_ptr_summary");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_invocation_packet,
          sizeof(PremapFutureKernelNativeConsumerInvocationV1)),
      "hipMalloc future_native_consumer_invocation_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_endpoint_packet,
          sizeof(PremapFutureKernelNativeConsumerEndpointV1)),
      "hipMalloc future_native_consumer_endpoint_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_request_ptr_packet,
          sizeof(PremapFutureKernelNativeConsumerRequestPtrV1)),
      "hipMalloc future_native_consumer_request_ptr_packet");
  hip_check(
      hipMalloc(
          &d_future_native_consumer_request_launch_packet,
          sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1)),
      "hipMalloc future_native_consumer_request_launch_packet");
  hip_check(hipMemcpy(d_descriptor, descriptor.data(), u64_bytes, hipMemcpyHostToDevice), "copy descriptor");
  hip_check(hipMemcpy(d_packed, packed.data(), u64_bytes, hipMemcpyHostToDevice), "copy packed");
  hip_check(hipMemcpy(d_scale, scale.data(), u64_bytes, hipMemcpyHostToDevice), "copy scale");
  if (!args.omit_aux_pointer) {
    hip_check(hipMemcpy(d_aux, aux.data(), u64_bytes, hipMemcpyHostToDevice), "copy aux");
  }
  hip_check(hipMemcpy(d_address_key, address_key.data(), u64_bytes, hipMemcpyHostToDevice), "copy address_key");
  hip_check(hipMemcpy(d_expert, expert.data(), i32_bytes, hipMemcpyHostToDevice), "copy expert");
  hip_check(hipMemset(d_future_kernel_consumer_ok, 0, u32_bytes), "memset future_kernel_consumer_ok");
  hip_check(hipMemset(d_future_kernel_consumer_hash, 0, u64_bytes), "memset future_kernel_consumer_hash");
  hip_check(hipMemset(d_future_kernel_single_field_mirror_ok, 0, u32_bytes), "memset future_kernel_single_field_mirror_ok");
  hip_check(hipMemset(d_future_kernel_single_field_mirror_hash, 0, u64_bytes), "memset future_kernel_single_field_mirror_hash");
  hip_check(hipMemset(d_future_kernel_compatible_path_ok, 0, u32_bytes), "memset future_kernel_compatible_path_ok");
  hip_check(hipMemset(d_future_kernel_compatible_path_hash, 0, u64_bytes), "memset future_kernel_compatible_path_hash");
  hip_check(hipMemset(d_future_native_consumer_ok, 0, u32_bytes), "memset future_native_consumer_ok");
  hip_check(hipMemset(d_future_native_consumer_hash, 0, u64_bytes), "memset future_native_consumer_hash");
  hip_check(hipMemset(d_future_native_single_field_mirror_ok, 0, u32_bytes), "memset future_native_single_field_mirror_ok");
  hip_check(hipMemset(d_future_native_single_field_mirror_hash, 0, u64_bytes), "memset future_native_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_launch_consumer_ok, 0, u32_bytes),
      "memset future_native_launch_consumer_ok");
  hip_check(
      hipMemset(d_future_native_launch_consumer_hash, 0, u64_bytes),
      "memset future_native_launch_consumer_hash");
  hip_check(
      hipMemset(d_future_native_launch_single_field_mirror_ok, 0, u32_bytes),
      "memset future_native_launch_single_field_mirror_ok");
  hip_check(
      hipMemset(d_future_native_launch_single_field_mirror_hash, 0, u64_bytes),
      "memset future_native_launch_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_consumer_ok, 0, u32_bytes),
      "memset future_native_dispatch_consumer_ok");
  hip_check(
      hipMemset(d_future_native_dispatch_consumer_hash, 0, u64_bytes),
      "memset future_native_dispatch_consumer_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_handle_projection_hash, 0, u64_bytes),
      "memset future_native_dispatch_handle_projection_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_single_field_mirror_ok, 0, u32_bytes),
      "memset future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipMemset(d_future_native_dispatch_single_field_mirror_hash, 0, u64_bytes),
      "memset future_native_dispatch_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_ptr_consumer_ok, 0, u32_bytes),
      "memset future_native_dispatch_ptr_consumer_ok");
  hip_check(
      hipMemset(d_future_native_dispatch_ptr_consumer_hash, 0, u64_bytes),
      "memset future_native_dispatch_ptr_consumer_hash");
  hip_check(
      hipMemset(
          d_future_native_dispatch_ptr_handle_projection_hash,
          0,
          u64_bytes),
      "memset future_native_dispatch_ptr_handle_projection_hash");
  hip_check(
      hipMemset(d_future_native_dispatch_ptr_single_field_mirror_ok, 0, u32_bytes),
      "memset future_native_dispatch_ptr_single_field_mirror_ok");
  hip_check(
      hipMemset(d_future_native_dispatch_ptr_single_field_mirror_hash, 0, u64_bytes),
      "memset future_native_dispatch_ptr_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_arg_slot_consumer_ok, 0, u32_bytes),
      "memset future_native_arg_slot_consumer_ok");
  hip_check(
      hipMemset(d_future_native_arg_slot_consumer_hash, 0, u64_bytes),
      "memset future_native_arg_slot_consumer_hash");
  hip_check(
      hipMemset(d_future_native_arg_slot_handle_projection_hash, 0, u64_bytes),
      "memset future_native_arg_slot_handle_projection_hash");
  hip_check(
      hipMemset(d_future_native_arg_slot_descriptor_ptr_read_ok, 0, u32_bytes),
      "memset future_native_arg_slot_descriptor_ptr_read_ok");
  hip_check(
      hipMemset(d_future_native_arg_slot_descriptor_ptr_read_hash, 0, u64_bytes),
      "memset future_native_arg_slot_descriptor_ptr_read_hash");
  hip_check(
      hipMemset(
          d_future_native_arg_slot_packed_weight_descriptor_read_ok,
          0,
          u32_bytes),
      "memset future_native_arg_slot_packed_weight_descriptor_read_ok");
  hip_check(
      hipMemset(
          d_future_native_arg_slot_packed_weight_descriptor_read_hash,
          0,
          u64_bytes),
      "memset future_native_arg_slot_packed_weight_descriptor_read_hash");
  hip_check(
      hipMemset(
          d_future_native_arg_slot_scale_metadata_handle_read_ok,
          0,
          u32_bytes),
      "memset future_native_arg_slot_scale_metadata_handle_read_ok");
  hip_check(
      hipMemset(
          d_future_native_arg_slot_scale_metadata_handle_read_hash,
          0,
          u64_bytes),
      "memset future_native_arg_slot_scale_metadata_handle_read_hash");
  hip_check(
      hipMemset(
          d_future_native_arg_slot_aux_metadata_handle_read_ok,
          0,
          u32_bytes),
      "memset future_native_arg_slot_aux_metadata_handle_read_ok");
  hip_check(
      hipMemset(
          d_future_native_arg_slot_aux_metadata_handle_read_hash,
          0,
          u64_bytes),
      "memset future_native_arg_slot_aux_metadata_handle_read_hash");
  hip_check(
      hipMemset(d_future_native_arg_slot_single_field_mirror_ok, 0, u32_bytes),
      "memset future_native_arg_slot_single_field_mirror_ok");
  hip_check(
      hipMemset(d_future_native_arg_slot_single_field_mirror_hash, 0, u64_bytes),
      "memset future_native_arg_slot_single_field_mirror_hash");
  hip_check(
      hipMemset(d_future_native_consumer_view_ok, 0, u32_bytes),
      "memset future_native_consumer_view_ok");
  hip_check(
      hipMemset(d_future_native_consumer_view_hash, 0, u64_bytes),
      "memset future_native_consumer_view_hash");
  hip_check(
      hipMemset(d_future_native_consumer_view_handle_projection_hash, 0, u64_bytes),
      "memset future_native_consumer_view_handle_projection_hash");
  hip_check(
      hipMemset(d_future_native_consumer_view_descriptor_ptr_read_ok, 0, u32_bytes),
      "memset future_native_consumer_view_descriptor_ptr_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_descriptor_ptr_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_view_descriptor_ptr_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_packed_weight_descriptor_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_view_packed_weight_descriptor_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_packed_weight_descriptor_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_view_packed_weight_descriptor_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_scale_metadata_handle_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_view_scale_metadata_handle_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_scale_metadata_handle_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_view_scale_metadata_handle_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_aux_metadata_handle_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_view_aux_metadata_handle_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_view_aux_metadata_handle_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_view_aux_metadata_handle_read_hash");
  hip_check(
      hipMemset(d_future_native_consumer_program_view_ok, 0, u32_bytes),
      "memset future_native_consumer_program_view_ok");
  hip_check(
      hipMemset(d_future_native_consumer_program_view_hash, 0, u64_bytes),
      "memset future_native_consumer_program_view_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_program_view_handle_projection_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_program_view_handle_projection_hash");
  hip_check(
      hipMemset(d_future_native_consumer_program_view_ptr_ok, 0, u32_bytes),
      "memset future_native_consumer_program_view_ptr_ok");
  hip_check(
      hipMemset(d_future_native_consumer_program_view_ptr_hash, 0, u64_bytes),
      "memset future_native_consumer_program_view_ptr_hash");
  hip_check(
      hipMemset(d_future_native_consumer_kernel_arg_packet_ok, 0, u32_bytes),
      "memset future_native_consumer_kernel_arg_packet_ok");
  hip_check(
      hipMemset(d_future_native_consumer_kernel_arg_packet_hash, 0, u64_bytes),
      "memset future_native_consumer_kernel_arg_packet_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok,
          0,
          u32_bytes),
      "memset future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash,
          0,
          u64_bytes),
      "memset future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_entry_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_kernel_entry_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_entry_args_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_kernel_entry_args_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_entry_args_ptr_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_kernel_entry_args_ptr_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_launch_envelope_args_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_launch_envelope_args_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_launch_envelope_args_ptr_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_launch_envelope_args_ptr_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_launch_descriptor_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_kernel_launch_descriptor_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_entry_args,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1)),
      "memset future_native_consumer_kernel_entry_args");
  hip_check(
      hipMemset(
          d_future_native_consumer_launch_envelope_args_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1)),
      "memset future_native_consumer_launch_envelope_args_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_launch_envelope_args_ptr_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1)),
      "memset future_native_consumer_launch_envelope_args_ptr_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_launch_descriptor_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1)),
      "memset future_native_consumer_kernel_launch_descriptor_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_launch_context_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_kernel_launch_context_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_kernel_launch_context_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1)),
      "memset future_native_consumer_kernel_launch_context_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_invocation_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_invocation_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_invocation_entry_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_invocation_entry_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_endpoint_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_endpoint_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_endpoint_ptr_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_endpoint_ptr_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_wna16_adjacent_typed_slot_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_wna16_adjacent_typed_slot_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_request_ptr_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_request_ptr_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_request_launch_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_request_launch_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_request_launch_ptr_summary,
          0,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1)),
      "memset future_native_consumer_request_launch_ptr_summary");
  hip_check(
      hipMemset(
          d_future_native_consumer_invocation_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerInvocationV1)),
      "memset future_native_consumer_invocation_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_endpoint_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerEndpointV1)),
      "memset future_native_consumer_endpoint_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_request_ptr_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerRequestPtrV1)),
      "memset future_native_consumer_request_ptr_packet");
  hip_check(
      hipMemset(
          d_future_native_consumer_request_launch_packet,
          0,
          sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1)),
      "memset future_native_consumer_request_launch_packet");

  PremapKernelSideTypedConsumerAbiV1 table;
  table.typed_schema_hash_hi = kTypedSchemaHashHi;
  table.typed_schema_hash_lo = kTypedSchemaHashLo;
  table.descriptor_ptr = d_descriptor;
  table.packed_weight_descriptor = d_packed;
  table.scale_metadata_handle = d_scale;
  table.aux_metadata_handle = d_aux;
  table.expert_id = d_expert;
  table.address_key_hash = d_address_key;
  table.row_order_hash = 0xa02928d41970cdf1ULL;
  table.ordered_row_hash = 0xc1384d55958c9aa7ULL;
  table.lifetime_epoch = 1;
  table.row_count = static_cast<uint32_t>(rows);
  table.column_count = 4;
  const uint32_t future_kernel_consumer_args_field_mask =
      args.omit_aux_pointer ? kPremapFutureKernelSideConsumerFieldMaskRequired
                            : kPremapFutureKernelSideConsumerFieldMaskAll;

  const uint32_t threads = static_cast<uint32_t>(args.block_threads);
  const uint64_t blocks_u64 =
      (static_cast<uint64_t>(rows) + static_cast<uint64_t>(threads) - 1ULL) /
      static_cast<uint64_t>(threads);
  if (blocks_u64 == 0 || blocks_u64 > 0xffffffffULL) {
    std::cerr << "computed block count is outside uint32 range\n";
    std::exit(2);
  }
  const uint32_t blocks = static_cast<uint32_t>(blocks_u64);
  const uint64_t launch_threads =
      static_cast<uint64_t>(blocks) * static_cast<uint64_t>(threads);
  const uint32_t dispatch_row_offset =
      static_cast<uint32_t>(args.dispatch_row_offset);
  const uint32_t dispatch_row_limit =
      static_cast<uint32_t>(args.dispatch_row_limit);
  const uint32_t dispatch_active_rows =
      dispatch_row_limit >= dispatch_row_offset
          ? dispatch_row_limit - dispatch_row_offset
          : 0;
  const uint64_t dispatch_blocks_u64 =
      (static_cast<uint64_t>(dispatch_active_rows) +
       static_cast<uint64_t>(threads) - 1ULL) /
      static_cast<uint64_t>(threads);
  if (dispatch_blocks_u64 == 0 || dispatch_blocks_u64 > 0xffffffffULL) {
    std::cerr << "computed dispatch block count is outside uint32 range\n";
    std::exit(2);
  }
  const uint32_t dispatch_blocks = static_cast<uint32_t>(dispatch_blocks_u64);
  const uint64_t dispatch_launch_threads =
      static_cast<uint64_t>(dispatch_blocks) * static_cast<uint64_t>(threads);
  const bool dispatch_launch_covers_active_rows =
      dispatch_launch_threads >= static_cast<uint64_t>(dispatch_active_rows);
  const bool dispatch_launch_minimal_cover =
      dispatch_blocks == 1 ||
      ((static_cast<uint64_t>(dispatch_blocks - 1) *
        static_cast<uint64_t>(threads)) <
       static_cast<uint64_t>(dispatch_active_rows));
  const uint64_t dispatch_previous_program_threads =
      dispatch_blocks > 0
          ? static_cast<uint64_t>(dispatch_blocks - 1) *
                static_cast<uint64_t>(threads)
          : 0ULL;
  const uint32_t dispatch_full_program_count =
      static_cast<uint32_t>(
          static_cast<uint64_t>(dispatch_active_rows) /
          static_cast<uint64_t>(threads));
  const uint32_t dispatch_last_program_active_rows =
      dispatch_active_rows > 0
          ? static_cast<uint32_t>(
                static_cast<uint64_t>(dispatch_active_rows) -
                dispatch_previous_program_threads)
          : 0;
  const uint32_t dispatch_inactive_lane_count =
      dispatch_launch_threads >= static_cast<uint64_t>(dispatch_active_rows)
          ? static_cast<uint32_t>(
                dispatch_launch_threads -
                static_cast<uint64_t>(dispatch_active_rows))
          : 0;
  const uint32_t dispatch_first_program_row_offset = dispatch_row_offset;
  const uint32_t dispatch_last_program_row_offset =
      static_cast<uint32_t>(
          static_cast<uint64_t>(dispatch_row_offset) +
          dispatch_previous_program_threads);
  const uint64_t dispatch_program_iteration_hash =
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_blocks) + 0xd15c2001ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(threads) + 0xd15c2002ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_row_offset) + 0xd15c2003ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_row_limit) + 0xd15c2004ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_last_program_active_rows) +
          0xd15c2005ULL) ^
      premap_typed_consumer_mix64_v1(
          static_cast<uint64_t>(dispatch_inactive_lane_count) + 0xd15c2006ULL);
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 envelope;
  envelope.table = table;
  envelope.expected_schema_hash_hi = kTypedSchemaHashHi;
  envelope.expected_schema_hash_lo = kTypedSchemaHashLo;
  envelope.expected_row_order_hash = table.row_order_hash;
  envelope.expected_ordered_row_hash = table.ordered_row_hash;
  envelope.expected_row_count = table.row_count;
  envelope.expected_column_count = table.column_count;
  envelope.payload_bytes = 0;
  envelope.flags =
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag |
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag;
  hipLaunchKernelGGL(
      typed_consumer_envelope_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      envelope,
      d_ok,
      d_hash,
      d_single_field_mirror_ok,
      d_single_field_mirror_hash,
      d_kernel_side_consumer_path_ok,
      d_kernel_side_consumer_path_hash,
      d_kernel_side_compatible_consumer_ok,
      d_kernel_side_compatible_consumer_hash);
#else
  hipLaunchKernelGGL(
      typed_consumer_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      table,
      d_ok,
      d_hash,
      d_single_field_mirror_ok,
      d_single_field_mirror_hash,
      d_kernel_side_consumer_path_ok,
      d_kernel_side_consumer_path_hash,
      d_kernel_side_compatible_consumer_ok,
      d_kernel_side_compatible_consumer_hash);
#endif
  hip_check(hipGetLastError(), "kernel launch");
  hip_check(hipDeviceSynchronize(), "kernel sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
  PremapKernelSideTypedConsumerLaunchEnvelopeV1 future_envelope;
  future_envelope.table = table;
  future_envelope.expected_schema_hash_hi = kTypedSchemaHashHi;
  future_envelope.expected_schema_hash_lo = kTypedSchemaHashLo;
  future_envelope.expected_row_order_hash = table.row_order_hash;
  future_envelope.expected_ordered_row_hash = table.ordered_row_hash;
  future_envelope.expected_row_count = table.row_count;
  future_envelope.expected_column_count = table.column_count;
  future_envelope.payload_bytes = 0;
  future_envelope.flags =
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1ReadonlyFlag |
      kPremapKernelSideTypedConsumerLaunchEnvelopeV1KernelArgPassDisabledFlag;
  PremapFutureKernelSideConsumerArgsV1 future_args;
  future_args.envelope = future_envelope;
  future_args.field_mask = future_kernel_consumer_args_field_mask;
  future_args.single_field_mirror_kind = kSingleFieldMirrorKind;
  future_args.payload_bytes = 0;
  future_args.flags = kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_kernel_args_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      future_args,
      d_future_kernel_consumer_ok,
      d_future_kernel_consumer_hash,
      d_future_kernel_single_field_mirror_ok,
      d_future_kernel_single_field_mirror_hash,
      d_future_kernel_compatible_path_ok,
      d_future_kernel_compatible_path_hash);
  hip_check(hipGetLastError(), "future kernel consumer args launch");
  hip_check(hipDeviceSynchronize(), "future kernel consumer args sync");
#endif

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
  PremapFutureKernelNativeConsumerParamsV1 future_native_params;
  future_native_params.descriptor_ptr = table.descriptor_ptr;
  future_native_params.packed_weight_descriptor = table.packed_weight_descriptor;
  future_native_params.scale_metadata_handle = table.scale_metadata_handle;
  future_native_params.aux_metadata_handle = table.aux_metadata_handle;
  future_native_params.expert_id = table.expert_id;
  future_native_params.address_key_hash = table.address_key_hash;
  future_native_params.typed_schema_hash_hi = table.typed_schema_hash_hi;
  future_native_params.typed_schema_hash_lo = table.typed_schema_hash_lo;
  future_native_params.row_order_hash = table.row_order_hash;
  future_native_params.ordered_row_hash = table.ordered_row_hash;
  future_native_params.row_count = table.row_count;
  future_native_params.column_count = table.column_count;
  future_native_params.lifetime_epoch = table.lifetime_epoch;
  future_native_params.field_mask = future_kernel_consumer_args_field_mask;
  future_native_params.single_field_mirror_kind = kSingleFieldMirrorKind;
  future_native_params.payload_bytes = 0;
  future_native_params.flags = kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      future_native_params,
      d_future_native_consumer_ok,
      d_future_native_consumer_hash,
      d_future_native_single_field_mirror_ok,
      d_future_native_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native consumer launch");
  hip_check(hipDeviceSynchronize(), "future native consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
  PremapFutureKernelNativeConsumerLaunchV1 future_native_launch;
  future_native_launch.params = future_native_params;
  future_native_launch.abi_version =
      kPremapFutureKernelNativeConsumerLaunchAbiV1Version;
  future_native_launch.params_struct_size =
      sizeof(PremapFutureKernelNativeConsumerParamsV1);
  future_native_launch.result_struct_size =
      sizeof(PremapFutureKernelNativeConsumerLaunchResultV1);
  future_native_launch.row_stride = 1;
  future_native_launch.payload_bytes = 0;
  future_native_launch.flags = kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_launch_kernel,
      dim3(blocks),
      dim3(threads),
      0,
      0,
      future_native_launch,
      d_future_native_launch_consumer_ok,
      d_future_native_launch_consumer_hash,
      d_future_native_launch_single_field_mirror_ok,
      d_future_native_launch_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native launch consumer launch");
  hip_check(hipDeviceSynchronize(), "future native launch consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
  PremapFutureKernelNativeConsumerDispatchV1 future_native_dispatch;
  future_native_dispatch.launch = future_native_launch;
  future_native_dispatch.dispatch_version =
      kPremapFutureKernelNativeConsumerDispatchAbiV1Version;
  future_native_dispatch.grid_x = static_cast<uint32_t>(dispatch_blocks);
  future_native_dispatch.block_x = static_cast<uint32_t>(threads);
  future_native_dispatch.shared_mem_bytes = 0;
  future_native_dispatch.row_offset = dispatch_row_offset;
  future_native_dispatch.row_limit = dispatch_row_limit;
  future_native_dispatch.rows_per_program = static_cast<uint32_t>(threads);
  future_native_dispatch.payload_bytes = 0;
  future_native_dispatch.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_dispatch_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_dispatch,
      d_future_native_dispatch_consumer_ok,
      d_future_native_dispatch_consumer_hash,
      d_future_native_dispatch_handle_projection_hash,
      d_future_native_dispatch_single_field_mirror_ok,
      d_future_native_dispatch_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native dispatch consumer launch");
  hip_check(hipDeviceSynchronize(), "future native dispatch consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI)
  hip_check(
      hipMalloc(
          &d_future_native_dispatch_packet,
          sizeof(PremapFutureKernelNativeConsumerDispatchV1)),
      "hipMalloc future native dispatch packet");
  hip_check(
      hipMemcpy(
          d_future_native_dispatch_packet,
          &future_native_dispatch,
          sizeof(PremapFutureKernelNativeConsumerDispatchV1),
          hipMemcpyHostToDevice),
      "copy future native dispatch packet");
  PremapFutureKernelNativeConsumerDispatchPtrV1 future_native_dispatch_ptr;
  future_native_dispatch_ptr.dispatch = d_future_native_dispatch_packet;
  future_native_dispatch_ptr.abi_version =
      kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Version;
  future_native_dispatch_ptr.dispatch_struct_size =
      sizeof(PremapFutureKernelNativeConsumerDispatchV1);
  future_native_dispatch_ptr.result_struct_size =
      sizeof(PremapFutureKernelNativeConsumerDispatchResultV1);
  future_native_dispatch_ptr.payload_bytes = 0;
  future_native_dispatch_ptr.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_dispatch_ptr_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_dispatch_ptr,
      d_future_native_dispatch_ptr_consumer_ok,
      d_future_native_dispatch_ptr_consumer_hash,
      d_future_native_dispatch_ptr_handle_projection_hash,
      d_future_native_dispatch_ptr_single_field_mirror_ok,
      d_future_native_dispatch_ptr_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native dispatch pointer consumer launch");
  hip_check(hipDeviceSynchronize(), "future native dispatch pointer consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI)
  hip_check(
      hipMalloc(
          &d_future_native_dispatch_ptr_packet,
          sizeof(PremapFutureKernelNativeConsumerDispatchPtrV1)),
      "hipMalloc future native dispatch pointer packet");
  hip_check(
      hipMemcpy(
          d_future_native_dispatch_ptr_packet,
          &future_native_dispatch_ptr,
          sizeof(PremapFutureKernelNativeConsumerDispatchPtrV1),
          hipMemcpyHostToDevice),
      "copy future native dispatch pointer packet");
  PremapFutureKernelNativeConsumerArgSlotV1 future_native_arg_slot;
  future_native_arg_slot.dispatch_ptr = d_future_native_dispatch_ptr_packet;
  future_native_arg_slot.abi_version =
      kPremapFutureKernelNativeConsumerArgSlotAbiV1Version;
  future_native_arg_slot.dispatch_ptr_struct_size =
      sizeof(PremapFutureKernelNativeConsumerDispatchPtrV1);
  future_native_arg_slot.result_struct_size =
      sizeof(PremapFutureKernelNativeConsumerArgSlotResultV1);
  future_native_arg_slot.payload_bytes = 0;
  future_native_arg_slot.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_arg_slot_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_arg_slot,
      d_future_native_arg_slot_consumer_ok,
      d_future_native_arg_slot_consumer_hash,
      d_future_native_arg_slot_handle_projection_hash,
      d_future_native_arg_slot_descriptor_ptr_read_ok,
      d_future_native_arg_slot_descriptor_ptr_read_hash,
      d_future_native_arg_slot_packed_weight_descriptor_read_ok,
      d_future_native_arg_slot_packed_weight_descriptor_read_hash,
      d_future_native_arg_slot_scale_metadata_handle_read_ok,
      d_future_native_arg_slot_scale_metadata_handle_read_hash,
      d_future_native_arg_slot_aux_metadata_handle_read_ok,
      d_future_native_arg_slot_aux_metadata_handle_read_hash,
      d_future_native_arg_slot_single_field_mirror_ok,
      d_future_native_arg_slot_single_field_mirror_hash);
  hip_check(hipGetLastError(), "future native arg-slot consumer launch");
  hip_check(hipDeviceSynchronize(), "future native arg-slot consumer sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI)
  PremapFutureKernelNativeConsumerViewV1 future_native_consumer_view;
  future_native_consumer_view.params = future_native_params;
  future_native_consumer_view.abi_version =
      kPremapFutureKernelNativeConsumerViewAbiV1Version;
  future_native_consumer_view.source_packet_chain_depth = 3;
  future_native_consumer_view.row_offset = dispatch_row_offset;
  future_native_consumer_view.row_limit = dispatch_row_limit;
  future_native_consumer_view.rows_per_program = static_cast<uint32_t>(threads);
  future_native_consumer_view.payload_bytes = 0;
  future_native_consumer_view.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_view_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_consumer_view,
      d_future_native_consumer_view_ok,
      d_future_native_consumer_view_hash,
      d_future_native_consumer_view_handle_projection_hash,
      d_future_native_consumer_view_descriptor_ptr_read_ok,
      d_future_native_consumer_view_descriptor_ptr_read_hash,
      d_future_native_consumer_view_packed_weight_descriptor_read_ok,
      d_future_native_consumer_view_packed_weight_descriptor_read_hash,
      d_future_native_consumer_view_scale_metadata_handle_read_ok,
      d_future_native_consumer_view_scale_metadata_handle_read_hash,
      d_future_native_consumer_view_aux_metadata_handle_read_ok,
      d_future_native_consumer_view_aux_metadata_handle_read_hash);
  hip_check(hipGetLastError(), "future native consumer view launch");
  hip_check(hipDeviceSynchronize(), "future native consumer view sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI)
  PremapFutureKernelNativeConsumerProgramViewV1
      future_native_consumer_program_view;
  future_native_consumer_program_view.view = future_native_consumer_view;
  future_native_consumer_program_view.abi_version =
      kPremapFutureKernelNativeConsumerProgramViewAbiV1Version;
  future_native_consumer_program_view.program_count =
      static_cast<uint32_t>(dispatch_blocks);
  future_native_consumer_program_view.full_program_count =
      dispatch_full_program_count;
  future_native_consumer_program_view.last_program_active_rows =
      dispatch_last_program_active_rows;
  future_native_consumer_program_view.inactive_lane_count =
      dispatch_inactive_lane_count;
  future_native_consumer_program_view.first_program_row_offset =
      dispatch_first_program_row_offset;
  future_native_consumer_program_view.last_program_row_offset =
      dispatch_last_program_row_offset;
  future_native_consumer_program_view.program_iteration_hash =
      dispatch_program_iteration_hash;
  future_native_consumer_program_view.payload_bytes = 0;
  future_native_consumer_program_view.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_program_view_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_consumer_program_view,
      d_future_native_consumer_program_view_ok,
      d_future_native_consumer_program_view_hash,
      d_future_native_consumer_program_view_handle_projection_hash);
  hip_check(hipGetLastError(), "future native consumer program-view launch");
  hip_check(hipDeviceSynchronize(), "future native consumer program-view sync");

#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI)
  hip_check(
      hipMalloc(
          &d_future_native_consumer_program_view_packet,
          sizeof(PremapFutureKernelNativeConsumerProgramViewV1)),
      "hipMalloc future native consumer program-view packet");
  hip_check(
      hipMemcpy(
          d_future_native_consumer_program_view_packet,
          &future_native_consumer_program_view,
          sizeof(PremapFutureKernelNativeConsumerProgramViewV1),
          hipMemcpyHostToDevice),
      "copy future native consumer program-view packet");
  PremapFutureKernelNativeConsumerProgramViewPtrV1
      future_native_consumer_program_view_ptr;
  future_native_consumer_program_view_ptr.program_view =
      d_future_native_consumer_program_view_packet;
  future_native_consumer_program_view_ptr.abi_version =
      kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Version;
  future_native_consumer_program_view_ptr.program_view_struct_size =
      sizeof(PremapFutureKernelNativeConsumerProgramViewV1);
  future_native_consumer_program_view_ptr.result_struct_size =
      sizeof(PremapFutureKernelNativeConsumerProgramViewPtrResultV1);
  future_native_consumer_program_view_ptr.payload_bytes = 0;
  future_native_consumer_program_view_ptr.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_program_view_ptr_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_consumer_program_view_ptr,
      d_future_native_consumer_program_view_ptr_ok,
      d_future_native_consumer_program_view_ptr_hash);
  hip_check(hipGetLastError(), "future native consumer program-view pointer launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer program-view pointer sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI)
  hip_check(
      hipMalloc(
          &d_future_native_consumer_program_view_ptr_packet,
          sizeof(PremapFutureKernelNativeConsumerProgramViewPtrV1)),
      "hipMalloc future native consumer program-view pointer packet");
  hip_check(
      hipMemcpy(
          d_future_native_consumer_program_view_ptr_packet,
          &future_native_consumer_program_view_ptr,
          sizeof(PremapFutureKernelNativeConsumerProgramViewPtrV1),
          hipMemcpyHostToDevice),
      "copy future native consumer program-view pointer packet");
  PremapFutureKernelNativeConsumerKernelArgPacketV1
      future_native_consumer_kernel_arg_packet;
  future_native_consumer_kernel_arg_packet.program_view_ptr =
      d_future_native_consumer_program_view_ptr_packet;
  future_native_consumer_kernel_arg_packet.abi_version =
      kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Version;
  future_native_consumer_kernel_arg_packet.program_view_ptr_struct_size =
      sizeof(PremapFutureKernelNativeConsumerProgramViewPtrV1);
  future_native_consumer_kernel_arg_packet.result_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelArgPacketResultV1);
  future_native_consumer_kernel_arg_packet.payload_bytes = 0;
  future_native_consumer_kernel_arg_packet.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_kernel_arg_packet,
          &future_native_consumer_kernel_arg_packet,
          sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_kernel_arg_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_kernel_arg_packet_kernel,
      dim3(dispatch_blocks),
      dim3(threads),
      0,
      0,
      future_native_consumer_kernel_arg_packet,
      d_future_native_consumer_kernel_arg_packet_ok,
      d_future_native_consumer_kernel_arg_packet_hash,
      d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok,
      d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash,
      d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok,
      d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash,
      d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok,
      d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash,
      d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok,
      d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash);
  hip_check(
      hipGetLastError(),
      "future native consumer kernel-arg packet launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer kernel-arg packet sync");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_kernel_entry_summary_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_kernel_arg_packet,
      d_future_native_consumer_kernel_entry_summary);
  hip_check(
      hipGetLastError(),
      "future native consumer kernel entry summary launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer kernel entry summary sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI)
  PremapFutureKernelNativeConsumerRequestPtrV1
      future_native_consumer_request_ptr;
  future_native_consumer_request_ptr.kernel_arg_packet =
      d_future_native_consumer_kernel_arg_packet;
  future_native_consumer_request_ptr.summary =
      d_future_native_consumer_request_ptr_summary;
  future_native_consumer_request_ptr.expected_schema_hash_hi =
      table.typed_schema_hash_hi;
  future_native_consumer_request_ptr.expected_schema_hash_lo =
      table.typed_schema_hash_lo;
  future_native_consumer_request_ptr.expected_row_order_hash =
      table.row_order_hash;
  future_native_consumer_request_ptr.expected_ordered_row_hash =
      table.ordered_row_hash;
  future_native_consumer_request_ptr.abi_version =
      kPremapFutureKernelNativeConsumerRequestPtrAbiV1Version;
  future_native_consumer_request_ptr.kernel_arg_packet_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1);
  future_native_consumer_request_ptr.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_request_ptr.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1*);
  future_native_consumer_request_ptr.row_count = table.row_count;
  future_native_consumer_request_ptr.field_mask =
      future_kernel_consumer_args_field_mask;
  future_native_consumer_request_ptr.request_id = 1;
  future_native_consumer_request_ptr.payload_bytes = 0;
  future_native_consumer_request_ptr.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_request_ptr_packet,
          &future_native_consumer_request_ptr,
          sizeof(PremapFutureKernelNativeConsumerRequestPtrV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_request_ptr_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_request_ptr_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_request_ptr_packet);
  hip_check(
      hipGetLastError(),
      "future native consumer request pointer launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer request pointer sync");
#endif
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI)
  PremapFutureKernelNativeConsumerRequestLaunchV1
      future_native_consumer_request_launch;
  future_native_consumer_request_launch.request_ptr =
      d_future_native_consumer_request_ptr_packet;
  future_native_consumer_request_launch.summary =
      d_future_native_consumer_request_launch_summary;
  future_native_consumer_request_launch.expected_schema_hash_hi =
      table.typed_schema_hash_hi;
  future_native_consumer_request_launch.expected_schema_hash_lo =
      table.typed_schema_hash_lo;
  future_native_consumer_request_launch.expected_row_order_hash =
      table.row_order_hash;
  future_native_consumer_request_launch.expected_ordered_row_hash =
      table.ordered_row_hash;
  future_native_consumer_request_launch.abi_version =
      kPremapFutureKernelNativeConsumerRequestLaunchAbiV1Version;
  future_native_consumer_request_launch.request_ptr_struct_size =
      sizeof(PremapFutureKernelNativeConsumerRequestPtrV1);
  future_native_consumer_request_launch.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_request_launch.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerRequestPtrV1*);
  future_native_consumer_request_launch.grid_x =
      static_cast<uint32_t>((table.row_count + args.block_threads - 1) /
                            args.block_threads);
  future_native_consumer_request_launch.block_x =
      static_cast<uint32_t>(args.block_threads);
  future_native_consumer_request_launch.row_offset = 0;
  future_native_consumer_request_launch.row_limit = table.row_count;
  future_native_consumer_request_launch.rows_per_program =
      static_cast<uint32_t>(args.block_threads);
  future_native_consumer_request_launch.row_count = table.row_count;
  future_native_consumer_request_launch.field_mask =
      future_kernel_consumer_args_field_mask;
  future_native_consumer_request_launch.request_id = 1;
  future_native_consumer_request_launch.device_ordinal =
      static_cast<uint32_t>(args.device);
  future_native_consumer_request_launch.stream_domain = 0;
  future_native_consumer_request_launch.payload_bytes = 0;
  future_native_consumer_request_launch.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_request_launch_packet,
          &future_native_consumer_request_launch,
          sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_request_launch_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_request_launch_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_request_launch_packet);
  hip_check(
      hipGetLastError(),
      "future native consumer request launch launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer request launch sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI)
  PremapFutureKernelNativeConsumerRequestLaunchPtrV1
      future_native_consumer_request_launch_ptr;
  future_native_consumer_request_launch_ptr.request_launch =
      d_future_native_consumer_request_launch_packet;
  future_native_consumer_request_launch_ptr.summary =
      d_future_native_consumer_request_launch_ptr_summary;
  future_native_consumer_request_launch_ptr.abi_version =
      kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1Version;
  future_native_consumer_request_launch_ptr.request_launch_struct_size =
      sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1);
  future_native_consumer_request_launch_ptr.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_request_launch_ptr.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1*);
  future_native_consumer_request_launch_ptr.request_id = 1;
  future_native_consumer_request_launch_ptr.payload_bytes = 0;
  future_native_consumer_request_launch_ptr.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_request_launch_ptr_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_request_launch_ptr);
  hip_check(
      hipGetLastError(),
      "future native consumer request launch pointer launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer request launch pointer sync");
#endif
#endif
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI)
  PremapFutureKernelNativeConsumerKernelEntryArgsV1
      future_native_consumer_kernel_entry_args;
  future_native_consumer_kernel_entry_args.kernel_arg_packet =
      d_future_native_consumer_kernel_arg_packet;
  future_native_consumer_kernel_entry_args.summary =
      d_future_native_consumer_kernel_entry_args_summary;
  future_native_consumer_kernel_entry_args.abi_version =
      kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1Version;
  future_native_consumer_kernel_entry_args.kernel_arg_packet_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1);
  future_native_consumer_kernel_entry_args.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_kernel_entry_args.payload_bytes = 0;
  future_native_consumer_kernel_entry_args.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_kernel_entry_args_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_kernel_entry_args);
  hip_check(
      hipGetLastError(),
      "future native consumer kernel entry-args launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer kernel entry-args sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI)
  future_native_consumer_kernel_entry_args.summary =
      d_future_native_consumer_kernel_entry_args_ptr_summary;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_kernel_entry_args,
          &future_native_consumer_kernel_entry_args,
          sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_kernel_entry_args");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_kernel_entry_args_ptr_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_kernel_entry_args);
  hip_check(
      hipGetLastError(),
      "future native consumer kernel entry-args pointer launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer kernel entry-args pointer sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI)
  future_native_consumer_kernel_entry_args.summary =
      d_future_native_consumer_launch_envelope_args_summary;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_kernel_entry_args,
          &future_native_consumer_kernel_entry_args,
          sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_kernel_entry_args for launch envelope");
  PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1
      future_native_consumer_launch_envelope_args;
  future_native_consumer_launch_envelope_args.entry_args =
      d_future_native_consumer_kernel_entry_args;
  future_native_consumer_launch_envelope_args.abi_version =
      kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1Version;
  future_native_consumer_launch_envelope_args.entry_args_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1);
  future_native_consumer_launch_envelope_args.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1*);
  future_native_consumer_launch_envelope_args.grid_x = dispatch_blocks;
  future_native_consumer_launch_envelope_args.block_x = threads;
  future_native_consumer_launch_envelope_args.row_offset = dispatch_row_offset;
  future_native_consumer_launch_envelope_args.row_limit = dispatch_row_limit;
  future_native_consumer_launch_envelope_args.rows_per_program = threads;
  future_native_consumer_launch_envelope_args.payload_bytes = 0;
  future_native_consumer_launch_envelope_args.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_launch_envelope_args_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_launch_envelope_args);
  hip_check(
      hipGetLastError(),
      "future native consumer launch-envelope args launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer launch-envelope args sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI)
  future_native_consumer_kernel_entry_args.summary =
      d_future_native_consumer_launch_envelope_args_ptr_summary;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_kernel_entry_args,
          &future_native_consumer_kernel_entry_args,
          sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_kernel_entry_args for launch envelope ptr");
  hip_check(
      hipMemcpy(
          d_future_native_consumer_launch_envelope_args_packet,
          &future_native_consumer_launch_envelope_args,
          sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_launch_envelope_args_packet");
  PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1
      future_native_consumer_launch_envelope_args_ptr;
  future_native_consumer_launch_envelope_args_ptr.launch_args =
      d_future_native_consumer_launch_envelope_args_packet;
  future_native_consumer_launch_envelope_args_ptr.abi_version =
      kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1Version;
  future_native_consumer_launch_envelope_args_ptr.launch_args_struct_size =
      sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1);
  future_native_consumer_launch_envelope_args_ptr.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1*);
  future_native_consumer_launch_envelope_args_ptr.payload_bytes = 0;
  future_native_consumer_launch_envelope_args_ptr.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_launch_envelope_args_ptr_packet,
          &future_native_consumer_launch_envelope_args_ptr,
          sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_launch_envelope_args_ptr_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_launch_envelope_args_ptr_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_launch_envelope_args_ptr_packet);
  hip_check(
      hipGetLastError(),
      "future native consumer launch-envelope args pointer launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer launch-envelope args pointer sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI)
  PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1
      future_native_consumer_kernel_launch_descriptor;
  future_native_consumer_kernel_launch_descriptor.launch_args_ptr =
      d_future_native_consumer_launch_envelope_args_ptr_packet;
  future_native_consumer_kernel_launch_descriptor.summary =
      d_future_native_consumer_kernel_launch_descriptor_summary;
  future_native_consumer_kernel_launch_descriptor.expected_schema_hash_hi =
      args.fault_kernel_launch_descriptor_schema_hash
          ? (kTypedSchemaHashHi ^ 0x1ULL)
          : kTypedSchemaHashHi;
  future_native_consumer_kernel_launch_descriptor.expected_schema_hash_lo =
      kTypedSchemaHashLo;
  future_native_consumer_kernel_launch_descriptor.abi_version =
      kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1Version;
  future_native_consumer_kernel_launch_descriptor.launch_args_ptr_struct_size =
      sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1);
  future_native_consumer_kernel_launch_descriptor.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_kernel_launch_descriptor.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1*);
  future_native_consumer_kernel_launch_descriptor.grid_x = dispatch_blocks;
  future_native_consumer_kernel_launch_descriptor.block_x = threads;
  future_native_consumer_kernel_launch_descriptor.row_offset =
      dispatch_row_offset;
  future_native_consumer_kernel_launch_descriptor.row_limit =
      dispatch_row_limit;
  future_native_consumer_kernel_launch_descriptor.rows_per_program = threads;
  future_native_consumer_kernel_launch_descriptor.payload_bytes = 0;
  future_native_consumer_kernel_launch_descriptor.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_kernel_launch_descriptor_packet,
          &future_native_consumer_kernel_launch_descriptor,
          sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_kernel_launch_descriptor_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_kernel_launch_descriptor_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_kernel_launch_descriptor_packet);
  hip_check(
      hipGetLastError(),
      "future native consumer kernel launch descriptor launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer kernel launch descriptor sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI)
  PremapFutureKernelNativeConsumerKernelLaunchContextV1
      future_native_consumer_kernel_launch_context;
  future_native_consumer_kernel_launch_context.launch_descriptor =
      d_future_native_consumer_kernel_launch_descriptor_packet;
  future_native_consumer_kernel_launch_context.summary =
      d_future_native_consumer_kernel_launch_context_summary;
  future_native_consumer_kernel_launch_context.expected_schema_hash_hi =
      kTypedSchemaHashHi;
  future_native_consumer_kernel_launch_context.expected_schema_hash_lo =
      kTypedSchemaHashLo;
  future_native_consumer_kernel_launch_context.abi_version =
      kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1Version;
  future_native_consumer_kernel_launch_context.launch_descriptor_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1);
  future_native_consumer_kernel_launch_context.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_kernel_launch_context.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1*);
  future_native_consumer_kernel_launch_context.device_ordinal =
      static_cast<uint32_t>(args.device);
  future_native_consumer_kernel_launch_context.stream_domain = 0;
  future_native_consumer_kernel_launch_context.payload_bytes = 0;
  future_native_consumer_kernel_launch_context.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_kernel_launch_context_packet,
          &future_native_consumer_kernel_launch_context,
          sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_kernel_launch_context_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_kernel_launch_context_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_kernel_launch_context_packet);
  hip_check(
      hipGetLastError(),
      "future native consumer kernel launch context launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer kernel launch context sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI)
  PremapFutureKernelNativeConsumerInvocationV1
      future_native_consumer_invocation;
  future_native_consumer_invocation.context =
      d_future_native_consumer_kernel_launch_context_packet;
  future_native_consumer_invocation.summary =
      d_future_native_consumer_invocation_summary;
  future_native_consumer_invocation.expected_schema_hash_hi = kTypedSchemaHashHi;
  future_native_consumer_invocation.expected_schema_hash_lo = kTypedSchemaHashLo;
  future_native_consumer_invocation.abi_version =
      kPremapFutureKernelNativeConsumerInvocationAbiV1Version;
  future_native_consumer_invocation.context_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1);
  future_native_consumer_invocation.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_invocation.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1*);
  future_native_consumer_invocation.invocation_id = 1;
  future_native_consumer_invocation.device_ordinal = invocation_device_ordinal;
  future_native_consumer_invocation.stream_domain = invocation_stream_domain;
  future_native_consumer_invocation.payload_bytes = 0;
  future_native_consumer_invocation.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hip_check(
      hipMemcpy(
          d_future_native_consumer_invocation_packet,
          &future_native_consumer_invocation,
          sizeof(PremapFutureKernelNativeConsumerInvocationV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_invocation_packet");
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_invocation_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      d_future_native_consumer_invocation_packet);
  hip_check(hipGetLastError(), "future native consumer invocation launch");
  hip_check(hipDeviceSynchronize(), "future native consumer invocation sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI)
  future_native_consumer_invocation.summary =
      d_future_native_consumer_invocation_entry_summary;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_invocation_entry_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_invocation);
  hip_check(
      hipGetLastError(),
      "future native consumer invocation entry launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer invocation entry sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI)
  future_native_consumer_invocation.summary =
      d_future_native_consumer_endpoint_summary;
  PremapFutureKernelNativeConsumerEndpointV1 future_native_consumer_endpoint;
  future_native_consumer_endpoint.invocation = future_native_consumer_invocation;
  future_native_consumer_endpoint.abi_version =
      kPremapFutureKernelNativeConsumerEndpointAbiV1Version;
  future_native_consumer_endpoint.invocation_struct_size =
      sizeof(PremapFutureKernelNativeConsumerInvocationV1);
  future_native_consumer_endpoint.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_endpoint.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1*);
  future_native_consumer_endpoint.endpoint_id = 1;
  future_native_consumer_endpoint.payload_bytes = 0;
  future_native_consumer_endpoint.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_endpoint_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_endpoint);
  hip_check(
      hipGetLastError(),
      "future native consumer endpoint launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer endpoint sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI)
  hip_check(
      hipMemcpy(
          d_future_native_consumer_endpoint_packet,
          &future_native_consumer_endpoint,
          sizeof(PremapFutureKernelNativeConsumerEndpointV1),
          hipMemcpyHostToDevice),
      "copy future_native_consumer_endpoint_packet");
  PremapFutureKernelNativeConsumerEndpointPtrV1 future_native_consumer_endpoint_ptr;
  future_native_consumer_endpoint_ptr.endpoint =
      d_future_native_consumer_endpoint_packet;
  future_native_consumer_endpoint_ptr.summary =
      d_future_native_consumer_endpoint_ptr_summary;
  future_native_consumer_endpoint_ptr.abi_version =
      kPremapFutureKernelNativeConsumerEndpointPtrAbiV1Version;
  future_native_consumer_endpoint_ptr.endpoint_struct_size =
      sizeof(PremapFutureKernelNativeConsumerEndpointV1);
  future_native_consumer_endpoint_ptr.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_endpoint_ptr.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerEndpointV1*);
  future_native_consumer_endpoint_ptr.endpoint_id = 1;
  future_native_consumer_endpoint_ptr.payload_bytes = 0;
  future_native_consumer_endpoint_ptr.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_endpoint_ptr_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_endpoint_ptr);
  hip_check(
      hipGetLastError(),
      "future native consumer endpoint pointer launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer endpoint pointer sync");
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI)
  PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1
      future_native_consumer_wna16_adjacent_typed_slot;
  future_native_consumer_endpoint_ptr.summary =
      d_future_native_consumer_wna16_adjacent_typed_slot_summary;
  future_native_consumer_wna16_adjacent_typed_slot.endpoint_ptr =
      future_native_consumer_endpoint_ptr;
  future_native_consumer_wna16_adjacent_typed_slot.summary =
      d_future_native_consumer_wna16_adjacent_typed_slot_summary;
  future_native_consumer_wna16_adjacent_typed_slot.abi_version =
      kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1Version;
  future_native_consumer_wna16_adjacent_typed_slot.endpoint_ptr_struct_size =
      sizeof(PremapFutureKernelNativeConsumerEndpointPtrV1);
  future_native_consumer_wna16_adjacent_typed_slot.summary_struct_size =
      sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  future_native_consumer_wna16_adjacent_typed_slot.pointer_size =
      sizeof(PremapFutureKernelNativeConsumerEndpointPtrV1*);
  future_native_consumer_wna16_adjacent_typed_slot.slot_id = 1;
  future_native_consumer_wna16_adjacent_typed_slot.packet_chain_depth = 14;
  future_native_consumer_wna16_adjacent_typed_slot.payload_bytes = 0;
  future_native_consumer_wna16_adjacent_typed_slot.flags =
      kPremapFutureKernelSideConsumerArgsV1RequiredFlags;
  future_native_consumer_wna16_adjacent_typed_slot.current_wna16_arg_compatible =
      0;
  future_native_consumer_wna16_adjacent_typed_slot
      .requires_wna16_arg_reinterpretation = 0;
  future_native_consumer_wna16_adjacent_typed_slot.explicit_typed_abi_slot = 1;
  future_native_consumer_wna16_adjacent_typed_slot.reuses_current_wna16_arg_slot =
      0;
  hipLaunchKernelGGL(
      typed_consumer_future_native_consumer_wna16_adjacent_typed_slot_kernel,
      dim3(1),
      dim3(1),
      0,
      0,
      future_native_consumer_wna16_adjacent_typed_slot);
  hip_check(
      hipGetLastError(),
      "future native consumer WNA16-adjacent typed slot launch");
  hip_check(
      hipDeviceSynchronize(),
      "future native consumer WNA16-adjacent typed slot sync");
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif
#endif

  std::vector<uint32_t> ok(rows);
  std::vector<uint64_t> hashes(rows);
  std::vector<uint32_t> single_field_mirror_ok(rows);
  std::vector<uint64_t> single_field_mirror_hashes(rows);
  std::vector<uint32_t> kernel_side_consumer_path_ok(rows);
  std::vector<uint64_t> kernel_side_consumer_path_hashes(rows);
  std::vector<uint32_t> kernel_side_compatible_consumer_ok(rows);
  std::vector<uint64_t> kernel_side_compatible_consumer_hashes(rows);
  std::vector<uint32_t> future_kernel_consumer_ok(rows);
  std::vector<uint64_t> future_kernel_consumer_hashes(rows);
  std::vector<uint32_t> future_kernel_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_kernel_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_kernel_compatible_path_ok(rows);
  std::vector<uint64_t> future_kernel_compatible_path_hashes(rows);
  std::vector<uint32_t> future_native_consumer_ok(rows);
  std::vector<uint64_t> future_native_consumer_hashes(rows);
  std::vector<uint32_t> future_native_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_launch_consumer_ok(rows);
  std::vector<uint64_t> future_native_launch_consumer_hashes(rows);
  std::vector<uint32_t> future_native_launch_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_launch_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_dispatch_consumer_ok(rows);
  std::vector<uint64_t> future_native_dispatch_consumer_hashes(rows);
  std::vector<uint64_t> future_native_dispatch_handle_projection_hashes(rows);
  std::vector<uint32_t> future_native_dispatch_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_dispatch_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_dispatch_ptr_consumer_ok(rows);
  std::vector<uint64_t> future_native_dispatch_ptr_consumer_hashes(rows);
  std::vector<uint64_t> future_native_dispatch_ptr_handle_projection_hashes(rows);
  std::vector<uint32_t> future_native_dispatch_ptr_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_dispatch_ptr_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_arg_slot_consumer_ok(rows);
  std::vector<uint64_t> future_native_arg_slot_consumer_hashes(rows);
  std::vector<uint64_t> future_native_arg_slot_handle_projection_hashes(rows);
  std::vector<uint32_t> future_native_arg_slot_descriptor_ptr_read_ok(rows);
  std::vector<uint64_t> future_native_arg_slot_descriptor_ptr_read_hashes(rows);
  std::vector<uint32_t>
      future_native_arg_slot_packed_weight_descriptor_read_ok(rows);
  std::vector<uint64_t>
      future_native_arg_slot_packed_weight_descriptor_read_hashes(rows);
  std::vector<uint32_t>
      future_native_arg_slot_scale_metadata_handle_read_ok(rows);
  std::vector<uint64_t>
      future_native_arg_slot_scale_metadata_handle_read_hashes(rows);
  std::vector<uint32_t> future_native_arg_slot_aux_metadata_handle_read_ok(rows);
  std::vector<uint64_t> future_native_arg_slot_aux_metadata_handle_read_hashes(rows);
  std::vector<uint32_t> future_native_arg_slot_single_field_mirror_ok(rows);
  std::vector<uint64_t> future_native_arg_slot_single_field_mirror_hashes(rows);
  std::vector<uint32_t> future_native_consumer_view_ok(rows);
  std::vector<uint64_t> future_native_consumer_view_hashes(rows);
  std::vector<uint64_t> future_native_consumer_view_handle_projection_hashes(rows);
  std::vector<uint32_t> future_native_consumer_view_descriptor_ptr_read_ok(rows);
  std::vector<uint64_t> future_native_consumer_view_descriptor_ptr_read_hashes(rows);
  std::vector<uint32_t>
      future_native_consumer_view_packed_weight_descriptor_read_ok(rows);
  std::vector<uint64_t>
      future_native_consumer_view_packed_weight_descriptor_read_hashes(rows);
  std::vector<uint32_t>
      future_native_consumer_view_scale_metadata_handle_read_ok(rows);
  std::vector<uint64_t>
      future_native_consumer_view_scale_metadata_handle_read_hashes(rows);
  std::vector<uint32_t> future_native_consumer_view_aux_metadata_handle_read_ok(rows);
  std::vector<uint64_t> future_native_consumer_view_aux_metadata_handle_read_hashes(rows);
  std::vector<uint32_t> future_native_consumer_program_view_ok(rows);
  std::vector<uint64_t> future_native_consumer_program_view_hashes(rows);
  std::vector<uint64_t>
      future_native_consumer_program_view_handle_projection_hashes(rows);
  std::vector<uint32_t> future_native_consumer_program_view_ptr_ok(rows);
  std::vector<uint64_t> future_native_consumer_program_view_ptr_hashes(rows);
  std::vector<uint32_t> future_native_consumer_kernel_arg_packet_ok(rows);
  std::vector<uint64_t>
      future_native_consumer_kernel_arg_packet_hashes(rows);
  std::vector<uint32_t>
      future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok(rows);
  std::vector<uint64_t>
      future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hashes(rows);
  std::vector<uint32_t>
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok(
          rows);
  std::vector<uint64_t>
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hashes(
          rows);
  std::vector<uint32_t>
      future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok(rows);
  std::vector<uint64_t>
      future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hashes(
          rows);
  std::vector<uint32_t>
      future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok(rows);
  std::vector<uint64_t>
      future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hashes(
          rows);
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_kernel_entry_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_kernel_entry_args_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_kernel_entry_args_ptr_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_launch_envelope_args_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_launch_envelope_args_ptr_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_kernel_launch_descriptor_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_kernel_launch_context_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_invocation_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_invocation_entry_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_endpoint_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_endpoint_ptr_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_wna16_adjacent_typed_slot_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_request_ptr_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_request_launch_summary{};
  PremapFutureKernelNativeConsumerKernelEntrySummaryV1
      future_native_consumer_request_launch_ptr_summary{};
  hip_check(hipMemcpy(ok.data(), d_ok, u32_bytes, hipMemcpyDeviceToHost), "copy ok");
  hip_check(hipMemcpy(hashes.data(), d_hash, u64_bytes, hipMemcpyDeviceToHost), "copy hash");
  hip_check(
      hipMemcpy(
          single_field_mirror_ok.data(),
          d_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          single_field_mirror_hashes.data(),
          d_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          kernel_side_consumer_path_ok.data(),
          d_kernel_side_consumer_path_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_consumer_path_ok");
  hip_check(
      hipMemcpy(
          kernel_side_consumer_path_hashes.data(),
          d_kernel_side_consumer_path_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_consumer_path_hash");
  hip_check(
      hipMemcpy(
          kernel_side_compatible_consumer_ok.data(),
          d_kernel_side_compatible_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_compatible_consumer_ok");
  hip_check(
      hipMemcpy(
          kernel_side_compatible_consumer_hashes.data(),
          d_kernel_side_compatible_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy kernel_side_compatible_consumer_hash");
  hip_check(
      hipMemcpy(
          future_kernel_consumer_ok.data(),
          d_future_kernel_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_consumer_ok");
  hip_check(
      hipMemcpy(
          future_kernel_consumer_hashes.data(),
          d_future_kernel_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_consumer_hash");
  hip_check(
      hipMemcpy(
          future_kernel_single_field_mirror_ok.data(),
          d_future_kernel_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_kernel_single_field_mirror_hashes.data(),
          d_future_kernel_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_kernel_compatible_path_ok.data(),
          d_future_kernel_compatible_path_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_compatible_path_ok");
  hip_check(
      hipMemcpy(
          future_kernel_compatible_path_hashes.data(),
          d_future_kernel_compatible_path_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_kernel_compatible_path_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_ok.data(),
          d_future_native_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_hashes.data(),
          d_future_native_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_single_field_mirror_ok.data(),
          d_future_native_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_single_field_mirror_hashes.data(),
          d_future_native_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_launch_consumer_ok.data(),
          d_future_native_launch_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_launch_consumer_hashes.data(),
          d_future_native_launch_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_launch_single_field_mirror_ok.data(),
          d_future_native_launch_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_launch_single_field_mirror_hashes.data(),
          d_future_native_launch_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_launch_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_consumer_ok.data(),
          d_future_native_dispatch_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_dispatch_consumer_hashes.data(),
          d_future_native_dispatch_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_handle_projection_hashes.data(),
          d_future_native_dispatch_handle_projection_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_handle_projection_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_single_field_mirror_ok.data(),
          d_future_native_dispatch_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_dispatch_single_field_mirror_hashes.data(),
          d_future_native_dispatch_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_ptr_consumer_ok.data(),
          d_future_native_dispatch_ptr_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_ptr_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_dispatch_ptr_consumer_hashes.data(),
          d_future_native_dispatch_ptr_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_ptr_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_ptr_handle_projection_hashes.data(),
          d_future_native_dispatch_ptr_handle_projection_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_ptr_handle_projection_hash");
  hip_check(
      hipMemcpy(
          future_native_dispatch_ptr_single_field_mirror_ok.data(),
          d_future_native_dispatch_ptr_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_ptr_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_dispatch_ptr_single_field_mirror_hashes.data(),
          d_future_native_dispatch_ptr_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_dispatch_ptr_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_consumer_ok.data(),
          d_future_native_arg_slot_consumer_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_consumer_ok");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_consumer_hashes.data(),
          d_future_native_arg_slot_consumer_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_consumer_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_handle_projection_hashes.data(),
          d_future_native_arg_slot_handle_projection_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_handle_projection_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_descriptor_ptr_read_ok.data(),
          d_future_native_arg_slot_descriptor_ptr_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_descriptor_ptr_read_ok");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_descriptor_ptr_read_hashes.data(),
          d_future_native_arg_slot_descriptor_ptr_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_descriptor_ptr_read_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_packed_weight_descriptor_read_ok.data(),
          d_future_native_arg_slot_packed_weight_descriptor_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_packed_weight_descriptor_read_ok");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_packed_weight_descriptor_read_hashes.data(),
          d_future_native_arg_slot_packed_weight_descriptor_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_packed_weight_descriptor_read_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_scale_metadata_handle_read_ok.data(),
          d_future_native_arg_slot_scale_metadata_handle_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_scale_metadata_handle_read_ok");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_scale_metadata_handle_read_hashes.data(),
          d_future_native_arg_slot_scale_metadata_handle_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_scale_metadata_handle_read_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_aux_metadata_handle_read_ok.data(),
          d_future_native_arg_slot_aux_metadata_handle_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_aux_metadata_handle_read_ok");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_aux_metadata_handle_read_hashes.data(),
          d_future_native_arg_slot_aux_metadata_handle_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_aux_metadata_handle_read_hash");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_single_field_mirror_ok.data(),
          d_future_native_arg_slot_single_field_mirror_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_single_field_mirror_ok");
  hip_check(
      hipMemcpy(
          future_native_arg_slot_single_field_mirror_hashes.data(),
          d_future_native_arg_slot_single_field_mirror_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_arg_slot_single_field_mirror_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_ok.data(),
          d_future_native_consumer_view_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_hashes.data(),
          d_future_native_consumer_view_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_handle_projection_hashes.data(),
          d_future_native_consumer_view_handle_projection_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_handle_projection_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_descriptor_ptr_read_ok.data(),
          d_future_native_consumer_view_descriptor_ptr_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_descriptor_ptr_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_descriptor_ptr_read_hashes.data(),
          d_future_native_consumer_view_descriptor_ptr_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_descriptor_ptr_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_packed_weight_descriptor_read_ok.data(),
          d_future_native_consumer_view_packed_weight_descriptor_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_packed_weight_descriptor_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_packed_weight_descriptor_read_hashes.data(),
          d_future_native_consumer_view_packed_weight_descriptor_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_packed_weight_descriptor_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_scale_metadata_handle_read_ok.data(),
          d_future_native_consumer_view_scale_metadata_handle_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_scale_metadata_handle_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_scale_metadata_handle_read_hashes.data(),
          d_future_native_consumer_view_scale_metadata_handle_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_scale_metadata_handle_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_aux_metadata_handle_read_ok.data(),
          d_future_native_consumer_view_aux_metadata_handle_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_aux_metadata_handle_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_view_aux_metadata_handle_read_hashes.data(),
          d_future_native_consumer_view_aux_metadata_handle_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_view_aux_metadata_handle_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_program_view_ok.data(),
          d_future_native_consumer_program_view_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_program_view_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_program_view_hashes.data(),
          d_future_native_consumer_program_view_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_program_view_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_program_view_handle_projection_hashes.data(),
          d_future_native_consumer_program_view_handle_projection_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_program_view_handle_projection_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_program_view_ptr_ok.data(),
          d_future_native_consumer_program_view_ptr_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_program_view_ptr_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_program_view_ptr_hashes.data(),
          d_future_native_consumer_program_view_ptr_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_program_view_ptr_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_ok.data(),
          d_future_native_consumer_kernel_arg_packet_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_hashes.data(),
          d_future_native_consumer_kernel_arg_packet_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok.data(),
          d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hashes.data(),
          d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok
              .data(),
          d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hashes
              .data(),
          d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok.data(),
          d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hashes
              .data(),
          d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok.data(),
          d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok,
          u32_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok");
  hip_check(
      hipMemcpy(
          future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hashes.data(),
          d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash,
          u64_bytes,
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash");
  hip_check(
      hipMemcpy(
          &future_native_consumer_kernel_entry_summary,
          d_future_native_consumer_kernel_entry_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_entry_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_kernel_entry_args_summary,
          d_future_native_consumer_kernel_entry_args_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_entry_args_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_kernel_entry_args_ptr_summary,
          d_future_native_consumer_kernel_entry_args_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_entry_args_ptr_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_launch_envelope_args_summary,
          d_future_native_consumer_launch_envelope_args_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_launch_envelope_args_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_launch_envelope_args_ptr_summary,
          d_future_native_consumer_launch_envelope_args_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_launch_envelope_args_ptr_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_kernel_launch_descriptor_summary,
          d_future_native_consumer_kernel_launch_descriptor_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_launch_descriptor_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_kernel_launch_context_summary,
          d_future_native_consumer_kernel_launch_context_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_kernel_launch_context_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_invocation_summary,
          d_future_native_consumer_invocation_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_invocation_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_invocation_entry_summary,
          d_future_native_consumer_invocation_entry_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_invocation_entry_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_endpoint_summary,
          d_future_native_consumer_endpoint_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_endpoint_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_endpoint_ptr_summary,
          d_future_native_consumer_endpoint_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_endpoint_ptr_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_wna16_adjacent_typed_slot_summary,
          d_future_native_consumer_wna16_adjacent_typed_slot_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_wna16_adjacent_typed_slot_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_request_ptr_summary,
          d_future_native_consumer_request_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_request_ptr_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_request_launch_summary,
          d_future_native_consumer_request_launch_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_request_launch_summary");
  hip_check(
      hipMemcpy(
          &future_native_consumer_request_launch_ptr_summary,
          d_future_native_consumer_request_launch_ptr_summary,
          sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1),
          hipMemcpyDeviceToHost),
      "copy future_native_consumer_request_launch_ptr_summary");

  uint64_t hash_acc = 0;
  uint64_t single_field_mirror_hash_acc = 0;
  uint64_t kernel_side_consumer_path_hash_acc = 0;
  uint64_t kernel_side_compatible_consumer_hash_acc = 0;
  uint64_t future_kernel_consumer_hash_acc = 0;
  uint64_t future_kernel_single_field_mirror_hash_acc = 0;
  uint64_t future_kernel_compatible_path_hash_acc = 0;
  uint64_t future_native_consumer_hash_acc = 0;
  uint64_t future_native_single_field_mirror_hash_acc = 0;
  uint64_t future_native_launch_consumer_hash_acc = 0;
  uint64_t future_native_launch_single_field_mirror_hash_acc = 0;
  uint64_t future_native_dispatch_consumer_hash_acc = 0;
  uint64_t future_native_dispatch_handle_projection_hash_acc = 0;
  uint64_t future_native_dispatch_single_field_mirror_hash_acc = 0;
  uint64_t future_native_dispatch_ptr_consumer_hash_acc = 0;
  uint64_t future_native_dispatch_ptr_handle_projection_hash_acc = 0;
  uint64_t future_native_dispatch_ptr_single_field_mirror_hash_acc = 0;
  uint64_t future_native_arg_slot_consumer_hash_acc = 0;
  uint64_t future_native_arg_slot_handle_projection_hash_acc = 0;
  uint64_t future_native_arg_slot_descriptor_ptr_read_hash_acc = 0;
  uint64_t future_native_arg_slot_packed_weight_descriptor_read_hash_acc = 0;
  uint64_t future_native_arg_slot_scale_metadata_handle_read_hash_acc = 0;
  uint64_t future_native_arg_slot_aux_metadata_handle_read_hash_acc = 0;
  uint64_t future_native_arg_slot_single_field_mirror_hash_acc = 0;
  uint64_t future_native_consumer_view_hash_acc = 0;
  uint64_t future_native_consumer_view_handle_projection_hash_acc = 0;
  uint64_t future_native_consumer_view_descriptor_ptr_read_hash_acc = 0;
  uint64_t future_native_consumer_view_packed_weight_descriptor_read_hash_acc = 0;
  uint64_t future_native_consumer_view_scale_metadata_handle_read_hash_acc = 0;
  uint64_t future_native_consumer_view_aux_metadata_handle_read_hash_acc = 0;
  uint64_t future_native_consumer_program_view_hash_acc = 0;
  uint64_t future_native_consumer_program_view_handle_projection_hash_acc = 0;
  uint64_t future_native_consumer_program_view_ptr_hash_acc = 0;
  uint64_t future_native_consumer_kernel_arg_packet_hash_acc = 0;
  uint64_t
      future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash_acc = 0;
  uint64_t
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash_acc =
          0;
  uint64_t
      future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash_acc =
          0;
  uint64_t
      future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash_acc =
          0;
  int ok_count = 0;
  int single_field_mirror_ok_count = 0;
  int kernel_side_consumer_path_ok_count = 0;
  int kernel_side_compatible_consumer_ok_count = 0;
  int future_kernel_consumer_ok_count = 0;
  int future_kernel_single_field_mirror_ok_count = 0;
  int future_kernel_compatible_path_ok_count = 0;
  int future_native_consumer_ok_count = 0;
  int future_native_single_field_mirror_ok_count = 0;
  int future_native_launch_consumer_ok_count = 0;
  int future_native_launch_single_field_mirror_ok_count = 0;
  int future_native_dispatch_consumer_ok_count = 0;
  int future_native_dispatch_single_field_mirror_ok_count = 0;
  int future_native_dispatch_ptr_consumer_ok_count = 0;
  int future_native_dispatch_ptr_single_field_mirror_ok_count = 0;
  int future_native_arg_slot_consumer_ok_count = 0;
  int future_native_arg_slot_descriptor_ptr_read_ok_count = 0;
  int future_native_arg_slot_packed_weight_descriptor_read_ok_count = 0;
  int future_native_arg_slot_scale_metadata_handle_read_ok_count = 0;
  int future_native_arg_slot_aux_metadata_handle_read_ok_count = 0;
  int future_native_arg_slot_single_field_mirror_ok_count = 0;
  int future_native_consumer_view_ok_count = 0;
  int future_native_consumer_view_descriptor_ptr_read_ok_count = 0;
  int future_native_consumer_view_packed_weight_descriptor_read_ok_count = 0;
  int future_native_consumer_view_scale_metadata_handle_read_ok_count = 0;
  int future_native_consumer_view_aux_metadata_handle_read_ok_count = 0;
  int future_native_consumer_program_view_ok_count = 0;
  int future_native_consumer_program_view_ptr_ok_count = 0;
  int future_native_consumer_kernel_arg_packet_ok_count = 0;
  int future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok_count = 0;
  int
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok_count =
          0;
  int future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok_count =
      0;
  int future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok_count =
      0;
  for (int i = 0; i < rows; ++i) {
    ok_count += ok[i] == 1 ? 1 : 0;
    hash_acc ^= mix64(hashes[i] + static_cast<uint64_t>(i));
    single_field_mirror_ok_count += single_field_mirror_ok[i] == 1 ? 1 : 0;
    single_field_mirror_hash_acc ^=
        mix64(single_field_mirror_hashes[i] + static_cast<uint64_t>(i));
    kernel_side_consumer_path_ok_count +=
        kernel_side_consumer_path_ok[i] == 1 ? 1 : 0;
    kernel_side_consumer_path_hash_acc ^=
        mix64(kernel_side_consumer_path_hashes[i] + static_cast<uint64_t>(i));
    kernel_side_compatible_consumer_ok_count +=
        kernel_side_compatible_consumer_ok[i] == 1 ? 1 : 0;
    kernel_side_compatible_consumer_hash_acc ^=
        mix64(kernel_side_compatible_consumer_hashes[i] + static_cast<uint64_t>(i));
    future_kernel_consumer_ok_count +=
        future_kernel_consumer_ok[i] == 1 ? 1 : 0;
    future_kernel_consumer_hash_acc ^=
        mix64(future_kernel_consumer_hashes[i] + static_cast<uint64_t>(i));
    future_kernel_single_field_mirror_ok_count +=
        future_kernel_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_kernel_single_field_mirror_hash_acc ^=
        mix64(
            future_kernel_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_kernel_compatible_path_ok_count +=
        future_kernel_compatible_path_ok[i] == 1 ? 1 : 0;
    future_kernel_compatible_path_hash_acc ^=
        mix64(
            future_kernel_compatible_path_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_ok_count +=
        future_native_consumer_ok[i] == 1 ? 1 : 0;
    future_native_consumer_hash_acc ^=
        mix64(future_native_consumer_hashes[i] + static_cast<uint64_t>(i));
    future_native_single_field_mirror_ok_count +=
        future_native_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_single_field_mirror_hash_acc ^=
        mix64(
            future_native_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_launch_consumer_ok_count +=
        future_native_launch_consumer_ok[i] == 1 ? 1 : 0;
    future_native_launch_consumer_hash_acc ^=
        mix64(
            future_native_launch_consumer_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_launch_single_field_mirror_ok_count +=
        future_native_launch_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_launch_single_field_mirror_hash_acc ^=
        mix64(
            future_native_launch_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_consumer_ok_count +=
        future_native_dispatch_consumer_ok[i] == 1 ? 1 : 0;
    future_native_dispatch_consumer_hash_acc ^=
        mix64(
            future_native_dispatch_consumer_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_handle_projection_hash_acc ^=
        mix64(
            future_native_dispatch_handle_projection_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_single_field_mirror_ok_count +=
        future_native_dispatch_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_dispatch_single_field_mirror_hash_acc ^=
        mix64(
            future_native_dispatch_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_ptr_consumer_ok_count +=
        future_native_dispatch_ptr_consumer_ok[i] == 1 ? 1 : 0;
    future_native_dispatch_ptr_consumer_hash_acc ^=
        mix64(
            future_native_dispatch_ptr_consumer_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_ptr_handle_projection_hash_acc ^=
        mix64(
            future_native_dispatch_ptr_handle_projection_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_dispatch_ptr_single_field_mirror_ok_count +=
        future_native_dispatch_ptr_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_dispatch_ptr_single_field_mirror_hash_acc ^=
        mix64(
            future_native_dispatch_ptr_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_consumer_ok_count +=
        future_native_arg_slot_consumer_ok[i] == 1 ? 1 : 0;
    future_native_arg_slot_consumer_hash_acc ^=
        mix64(
            future_native_arg_slot_consumer_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_handle_projection_hash_acc ^=
        mix64(
            future_native_arg_slot_handle_projection_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_descriptor_ptr_read_ok_count +=
        future_native_arg_slot_descriptor_ptr_read_ok[i] == 1 ? 1 : 0;
    future_native_arg_slot_descriptor_ptr_read_hash_acc ^=
        mix64(
            future_native_arg_slot_descriptor_ptr_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_packed_weight_descriptor_read_ok_count +=
        future_native_arg_slot_packed_weight_descriptor_read_ok[i] == 1 ? 1 : 0;
    future_native_arg_slot_packed_weight_descriptor_read_hash_acc ^=
        mix64(
            future_native_arg_slot_packed_weight_descriptor_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_scale_metadata_handle_read_ok_count +=
        future_native_arg_slot_scale_metadata_handle_read_ok[i] == 1 ? 1 : 0;
    future_native_arg_slot_scale_metadata_handle_read_hash_acc ^=
        mix64(
            future_native_arg_slot_scale_metadata_handle_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_aux_metadata_handle_read_ok_count +=
        future_native_arg_slot_aux_metadata_handle_read_ok[i] == 1 ? 1 : 0;
    future_native_arg_slot_aux_metadata_handle_read_hash_acc ^=
        mix64(
            future_native_arg_slot_aux_metadata_handle_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_arg_slot_single_field_mirror_ok_count +=
        future_native_arg_slot_single_field_mirror_ok[i] == 1 ? 1 : 0;
    future_native_arg_slot_single_field_mirror_hash_acc ^=
        mix64(
            future_native_arg_slot_single_field_mirror_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_view_ok_count +=
        future_native_consumer_view_ok[i] == 1 ? 1 : 0;
    future_native_consumer_view_hash_acc ^=
        mix64(future_native_consumer_view_hashes[i] + static_cast<uint64_t>(i));
    future_native_consumer_view_handle_projection_hash_acc ^=
        mix64(
            future_native_consumer_view_handle_projection_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_view_descriptor_ptr_read_ok_count +=
        future_native_consumer_view_descriptor_ptr_read_ok[i] == 1 ? 1 : 0;
    future_native_consumer_view_descriptor_ptr_read_hash_acc ^=
        mix64(
            future_native_consumer_view_descriptor_ptr_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_view_packed_weight_descriptor_read_ok_count +=
        future_native_consumer_view_packed_weight_descriptor_read_ok[i] == 1 ? 1 : 0;
    future_native_consumer_view_packed_weight_descriptor_read_hash_acc ^=
        mix64(
            future_native_consumer_view_packed_weight_descriptor_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_view_scale_metadata_handle_read_ok_count +=
        future_native_consumer_view_scale_metadata_handle_read_ok[i] == 1 ? 1 : 0;
    future_native_consumer_view_scale_metadata_handle_read_hash_acc ^=
        mix64(
            future_native_consumer_view_scale_metadata_handle_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_view_aux_metadata_handle_read_ok_count +=
        future_native_consumer_view_aux_metadata_handle_read_ok[i] == 1 ? 1 : 0;
    future_native_consumer_view_aux_metadata_handle_read_hash_acc ^=
        mix64(
            future_native_consumer_view_aux_metadata_handle_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_program_view_ok_count +=
        future_native_consumer_program_view_ok[i] == 1 ? 1 : 0;
    future_native_consumer_program_view_hash_acc ^=
        mix64(
            future_native_consumer_program_view_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_program_view_handle_projection_hash_acc ^=
        mix64(
            future_native_consumer_program_view_handle_projection_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_program_view_ptr_ok_count +=
        future_native_consumer_program_view_ptr_ok[i] == 1 ? 1 : 0;
    future_native_consumer_program_view_ptr_hash_acc ^=
        mix64(
            future_native_consumer_program_view_ptr_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_kernel_arg_packet_ok_count +=
        future_native_consumer_kernel_arg_packet_ok[i] == 1 ? 1 : 0;
    future_native_consumer_kernel_arg_packet_hash_acc ^=
        mix64(
            future_native_consumer_kernel_arg_packet_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok_count +=
        future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok[i] == 1
            ? 1
            : 0;
    future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash_acc ^=
        mix64(
            future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hashes[i] +
            static_cast<uint64_t>(i));
    future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok_count +=
        future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok[i] ==
                1
            ? 1
            : 0;
    future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash_acc ^=
        mix64(
            future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hashes
                [i] +
            static_cast<uint64_t>(i));
    future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok_count +=
        future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok[i] ==
                1
            ? 1
            : 0;
    future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash_acc ^=
        mix64(
            future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hashes
                [i] +
            static_cast<uint64_t>(i));
    future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok_count +=
        future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok[i] == 1
            ? 1
            : 0;
    future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash_acc ^=
        mix64(
            future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hashes[i] +
            static_cast<uint64_t>(i));
  }
  const int error_count = rows - ok_count;
  const bool single_field_mirror_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD) || \
    defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD)
      true;
#else
      false;
#endif
  const int single_field_mirror_row_count =
      single_field_mirror_checked ? rows : 0;
  const int single_field_mirror_error_count =
      single_field_mirror_checked ? rows - single_field_mirror_ok_count : 0;
  const bool kernel_side_consumer_path_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH)
      true;
#else
      false;
#endif
  const int kernel_side_consumer_path_row_count =
      kernel_side_consumer_path_checked ? rows : 0;
  const int kernel_side_consumer_path_error_count =
      kernel_side_consumer_path_checked ? rows - kernel_side_consumer_path_ok_count : 0;
  const bool kernel_side_compatible_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI)
      true;
#else
      false;
#endif
  const int kernel_side_compatible_consumer_row_count =
      kernel_side_compatible_consumer_checked ? rows : 0;
  const int kernel_side_compatible_consumer_error_count =
      kernel_side_compatible_consumer_checked
          ? rows - kernel_side_compatible_consumer_ok_count
          : 0;
  const bool future_kernel_consumer_args_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS)
      true;
#else
      false;
#endif
  const int future_kernel_consumer_args_row_count =
      future_kernel_consumer_args_checked ? rows : 0;
  const int future_kernel_consumer_args_error_count =
      future_kernel_consumer_args_checked ? rows - future_kernel_consumer_ok_count
                                          : 0;
  const bool future_kernel_single_field_mirror_checked =
      future_kernel_consumer_args_checked && single_field_mirror_checked;
  const int future_kernel_single_field_mirror_row_count =
      future_kernel_single_field_mirror_checked ? rows : 0;
  const int future_kernel_single_field_mirror_error_count =
      future_kernel_single_field_mirror_checked
          ? rows - future_kernel_single_field_mirror_ok_count
          : 0;
  const bool future_kernel_compatible_path_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH)
      true;
#else
      false;
#endif
  const int future_kernel_compatible_path_row_count =
      future_kernel_compatible_path_checked ? rows : 0;
  const int future_kernel_compatible_path_error_count =
      future_kernel_compatible_path_checked
          ? rows - future_kernel_compatible_path_ok_count
          : 0;
  const bool future_native_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_row_count =
      future_native_consumer_checked ? rows : 0;
  const int future_native_consumer_error_count =
      future_native_consumer_checked
          ? rows - future_native_consumer_ok_count
          : 0;
  const bool future_native_single_field_mirror_checked =
      future_native_consumer_checked && single_field_mirror_checked;
  const int future_native_single_field_mirror_row_count =
      future_native_single_field_mirror_checked ? rows : 0;
  const int future_native_single_field_mirror_error_count =
      future_native_single_field_mirror_checked
          ? rows - future_native_single_field_mirror_ok_count
          : 0;
  const bool future_native_launch_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI)
      true;
#else
      false;
#endif
  const int future_native_launch_consumer_row_count =
      future_native_launch_consumer_checked ? rows : 0;
  const int future_native_launch_consumer_error_count =
      future_native_launch_consumer_checked
          ? rows - future_native_launch_consumer_ok_count
          : 0;
  const bool future_native_launch_single_field_mirror_checked =
      future_native_launch_consumer_checked && single_field_mirror_checked;
  const int future_native_launch_single_field_mirror_row_count =
      future_native_launch_single_field_mirror_checked ? rows : 0;
  const int future_native_launch_single_field_mirror_error_count =
      future_native_launch_single_field_mirror_checked
          ? rows - future_native_launch_single_field_mirror_ok_count
          : 0;
  const bool future_native_dispatch_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI)
      true;
#else
      false;
#endif
  const int future_native_dispatch_active_rows =
      future_native_dispatch_consumer_checked
          ? static_cast<int>(dispatch_active_rows)
          : 0;
  const bool future_native_dispatch_launch_covers_active_rows =
      future_native_dispatch_consumer_checked
          ? dispatch_launch_covers_active_rows
          : false;
  const bool future_native_dispatch_launch_minimal_cover =
      future_native_dispatch_consumer_checked ? dispatch_launch_minimal_cover : false;
  const int future_native_dispatch_consumer_row_count =
      future_native_dispatch_consumer_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_dispatch_consumer_error_count =
      future_native_dispatch_consumer_checked
          ? future_native_dispatch_active_rows -
                future_native_dispatch_consumer_ok_count
          : 0;
  const bool future_native_dispatch_single_field_mirror_checked =
      future_native_dispatch_consumer_checked && single_field_mirror_checked;
  const int future_native_dispatch_single_field_mirror_row_count =
      future_native_dispatch_single_field_mirror_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_dispatch_single_field_mirror_error_count =
      future_native_dispatch_single_field_mirror_checked
          ? future_native_dispatch_active_rows -
                future_native_dispatch_single_field_mirror_ok_count
          : 0;
  const bool future_native_dispatch_ptr_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_dispatch_ptr_consumer_row_count =
      future_native_dispatch_ptr_consumer_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_dispatch_ptr_consumer_error_count =
      future_native_dispatch_ptr_consumer_checked
          ? future_native_dispatch_active_rows -
                future_native_dispatch_ptr_consumer_ok_count
          : 0;
  const bool future_native_dispatch_ptr_single_field_mirror_checked =
      future_native_dispatch_ptr_consumer_checked && single_field_mirror_checked;
  const int future_native_dispatch_ptr_single_field_mirror_row_count =
      future_native_dispatch_ptr_single_field_mirror_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_dispatch_ptr_single_field_mirror_error_count =
      future_native_dispatch_ptr_single_field_mirror_checked
          ? future_native_dispatch_active_rows -
                future_native_dispatch_ptr_single_field_mirror_ok_count
          : 0;
  const bool future_native_arg_slot_consumer_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI)
      true;
#else
      false;
#endif
  const int future_native_arg_slot_consumer_row_count =
      future_native_arg_slot_consumer_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_arg_slot_consumer_error_count =
      future_native_arg_slot_consumer_checked
          ? future_native_dispatch_active_rows -
                future_native_arg_slot_consumer_ok_count
          : 0;
  const int future_native_arg_slot_descriptor_ptr_read_row_count =
      future_native_arg_slot_consumer_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_arg_slot_packed_weight_descriptor_read_row_count =
      future_native_arg_slot_consumer_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_arg_slot_scale_metadata_handle_read_row_count =
      future_native_arg_slot_consumer_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_arg_slot_aux_metadata_handle_read_row_count =
      future_native_arg_slot_consumer_checked &&
              (future_kernel_consumer_args_field_mask &
               kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) != 0
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_arg_slot_descriptor_ptr_read_error_count =
      future_native_arg_slot_consumer_checked
          ? future_native_arg_slot_descriptor_ptr_read_row_count -
                future_native_arg_slot_descriptor_ptr_read_ok_count
          : 0;
  const int future_native_arg_slot_packed_weight_descriptor_read_error_count =
      future_native_arg_slot_consumer_checked
          ? future_native_arg_slot_packed_weight_descriptor_read_row_count -
                future_native_arg_slot_packed_weight_descriptor_read_ok_count
          : 0;
  const int future_native_arg_slot_scale_metadata_handle_read_error_count =
      future_native_arg_slot_consumer_checked
          ? future_native_arg_slot_scale_metadata_handle_read_row_count -
                future_native_arg_slot_scale_metadata_handle_read_ok_count
          : 0;
  const int future_native_arg_slot_aux_metadata_handle_read_error_count =
      future_native_arg_slot_consumer_checked
          ? future_native_arg_slot_aux_metadata_handle_read_row_count -
                future_native_arg_slot_aux_metadata_handle_read_ok_count
          : 0;
  const bool future_native_arg_slot_single_field_mirror_checked =
      future_native_arg_slot_consumer_checked && single_field_mirror_checked;
  const int future_native_arg_slot_single_field_mirror_row_count =
      future_native_arg_slot_single_field_mirror_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_arg_slot_single_field_mirror_error_count =
      future_native_arg_slot_single_field_mirror_checked
          ? future_native_dispatch_active_rows -
                future_native_arg_slot_single_field_mirror_ok_count
          : 0;
  const bool future_native_consumer_view_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_view_row_count =
      future_native_consumer_view_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_consumer_view_error_count =
      future_native_consumer_view_checked
          ? future_native_dispatch_active_rows -
                future_native_consumer_view_ok_count
          : 0;
  const int future_native_consumer_view_descriptor_ptr_read_row_count =
      future_native_consumer_view_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_consumer_view_packed_weight_descriptor_read_row_count =
      future_native_consumer_view_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_consumer_view_scale_metadata_handle_read_row_count =
      future_native_consumer_view_checked ? future_native_dispatch_active_rows : 0;
  const int future_native_consumer_view_aux_metadata_handle_read_row_count =
      future_native_consumer_view_checked &&
              (future_kernel_consumer_args_field_mask &
               kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) != 0
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_consumer_view_descriptor_ptr_read_error_count =
      future_native_consumer_view_checked
          ? future_native_consumer_view_descriptor_ptr_read_row_count -
                future_native_consumer_view_descriptor_ptr_read_ok_count
          : 0;
  const int future_native_consumer_view_packed_weight_descriptor_read_error_count =
      future_native_consumer_view_checked
          ? future_native_consumer_view_packed_weight_descriptor_read_row_count -
                future_native_consumer_view_packed_weight_descriptor_read_ok_count
          : 0;
  const int future_native_consumer_view_scale_metadata_handle_read_error_count =
      future_native_consumer_view_checked
          ? future_native_consumer_view_scale_metadata_handle_read_row_count -
                future_native_consumer_view_scale_metadata_handle_read_ok_count
          : 0;
  const int future_native_consumer_view_aux_metadata_handle_read_error_count =
      future_native_consumer_view_checked
          ? future_native_consumer_view_aux_metadata_handle_read_row_count -
                future_native_consumer_view_aux_metadata_handle_read_ok_count
          : 0;
  const bool future_native_consumer_program_view_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_program_view_row_count =
      future_native_consumer_program_view_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_consumer_program_view_error_count =
      future_native_consumer_program_view_checked
          ? future_native_dispatch_active_rows -
                future_native_consumer_program_view_ok_count
          : 0;
  const bool future_native_consumer_program_view_ptr_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_program_view_ptr_row_count =
      future_native_consumer_program_view_ptr_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_consumer_program_view_ptr_error_count =
      future_native_consumer_program_view_ptr_checked
          ? future_native_dispatch_active_rows -
                future_native_consumer_program_view_ptr_ok_count
          : 0;
  const bool future_native_consumer_kernel_arg_packet_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_kernel_arg_packet_row_count =
      future_native_consumer_kernel_arg_packet_checked
          ? future_native_dispatch_active_rows
          : 0;
  const int future_native_consumer_kernel_arg_packet_error_count =
      future_native_consumer_kernel_arg_packet_checked
          ? future_native_dispatch_active_rows -
                future_native_consumer_kernel_arg_packet_ok_count
          : 0;
  const int
      future_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_dispatch_active_rows
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_dispatch_active_rows
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_dispatch_active_rows
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_count =
          future_native_consumer_kernel_arg_packet_checked &&
                  (future_kernel_consumer_args_field_mask &
                   kPremapFutureKernelSideConsumerFieldMaskAuxMetadataHandle) != 0
              ? future_native_dispatch_active_rows
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_descriptor_ptr_read_error_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_count -
                    future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok_count
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_error_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_count -
                    future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok_count
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_error_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_count -
                    future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok_count
              : 0;
  const int
      future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_error_count =
          future_native_consumer_kernel_arg_packet_checked
              ? future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_count -
                    future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok_count
              : 0;
  const bool future_native_consumer_kernel_entry_summary_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_kernel_entry_summary_error_count =
      future_native_consumer_kernel_entry_summary_checked
          ? static_cast<int>(
                future_native_consumer_kernel_entry_summary.error_count)
          : 0;
  const bool future_native_consumer_kernel_entry_args_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_kernel_entry_args_error_count =
      future_native_consumer_kernel_entry_args_checked
          ? static_cast<int>(
                future_native_consumer_kernel_entry_args_summary.error_count)
          : 0;
  const bool future_native_consumer_kernel_entry_args_ptr_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_kernel_entry_args_ptr_error_count =
      future_native_consumer_kernel_entry_args_ptr_checked
          ? static_cast<int>(
                future_native_consumer_kernel_entry_args_ptr_summary.error_count)
          : 0;
  const bool future_native_consumer_launch_envelope_args_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_launch_envelope_args_error_count =
      future_native_consumer_launch_envelope_args_checked
          ? static_cast<int>(
                future_native_consumer_launch_envelope_args_summary.error_count)
          : 0;
  const bool future_native_consumer_launch_envelope_args_ptr_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_launch_envelope_args_ptr_error_count =
      future_native_consumer_launch_envelope_args_ptr_checked
          ? static_cast<int>(
                future_native_consumer_launch_envelope_args_ptr_summary
                    .error_count)
          : 0;
  const bool future_native_consumer_kernel_launch_descriptor_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_kernel_launch_descriptor_error_count =
      future_native_consumer_kernel_launch_descriptor_checked
          ? static_cast<int>(
                future_native_consumer_kernel_launch_descriptor_summary
                    .error_count)
          : 0;
  const bool future_native_consumer_kernel_launch_context_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_kernel_launch_context_error_count =
      future_native_consumer_kernel_launch_context_checked
          ? static_cast<int>(
                future_native_consumer_kernel_launch_context_summary
                    .error_count)
          : 0;
  const bool future_native_consumer_invocation_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_invocation_error_count =
      future_native_consumer_invocation_checked
          ? static_cast<int>(future_native_consumer_invocation_summary.error_count)
          : 0;
  const bool future_native_consumer_invocation_entry_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_invocation_entry_error_count =
      future_native_consumer_invocation_entry_checked
          ? static_cast<int>(
                future_native_consumer_invocation_entry_summary.error_count)
          : 0;
  const bool future_native_consumer_endpoint_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_endpoint_error_count =
      future_native_consumer_endpoint_checked
          ? static_cast<int>(
                future_native_consumer_endpoint_summary.error_count)
          : 0;
  const bool future_native_consumer_endpoint_ptr_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_endpoint_ptr_error_count =
      future_native_consumer_endpoint_ptr_checked
          ? static_cast<int>(
                future_native_consumer_endpoint_ptr_summary.error_count)
          : 0;
  const bool future_native_consumer_wna16_adjacent_typed_slot_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_wna16_adjacent_typed_slot_error_count =
      future_native_consumer_wna16_adjacent_typed_slot_checked
          ? static_cast<int>(
                future_native_consumer_wna16_adjacent_typed_slot_summary
                    .error_count)
          : 0;
  const bool future_native_consumer_request_ptr_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_request_ptr_error_count =
      future_native_consumer_request_ptr_checked
          ? static_cast<int>(
                future_native_consumer_request_ptr_summary.error_count)
          : 0;
  const bool future_native_consumer_request_launch_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_request_launch_error_count =
      future_native_consumer_request_launch_checked
          ? static_cast<int>(
                future_native_consumer_request_launch_summary.error_count)
          : 0;
  const bool future_native_consumer_request_launch_ptr_checked =
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI)
      true;
#else
      false;
#endif
  const int future_native_consumer_request_launch_ptr_error_count =
      future_native_consumer_request_launch_ptr_checked
          ? static_cast<int>(
                future_native_consumer_request_launch_ptr_summary.error_count)
          : 0;
  const bool all_ok =
      error_count == 0 && future_kernel_consumer_args_error_count == 0 &&
      future_kernel_single_field_mirror_error_count == 0 &&
      future_kernel_compatible_path_error_count == 0 &&
      future_native_consumer_error_count == 0 &&
      future_native_single_field_mirror_error_count == 0 &&
      future_native_launch_consumer_error_count == 0 &&
      future_native_launch_single_field_mirror_error_count == 0 &&
      future_native_dispatch_consumer_error_count == 0 &&
      future_native_dispatch_single_field_mirror_error_count == 0 &&
      future_native_dispatch_ptr_consumer_error_count == 0 &&
      future_native_dispatch_ptr_single_field_mirror_error_count == 0 &&
      future_native_arg_slot_consumer_error_count == 0 &&
      future_native_arg_slot_descriptor_ptr_read_error_count == 0 &&
      future_native_arg_slot_packed_weight_descriptor_read_error_count == 0 &&
      future_native_arg_slot_scale_metadata_handle_read_error_count == 0 &&
      future_native_arg_slot_aux_metadata_handle_read_error_count == 0 &&
      future_native_arg_slot_single_field_mirror_error_count == 0 &&
      future_native_consumer_view_error_count == 0 &&
      future_native_consumer_view_descriptor_ptr_read_error_count == 0 &&
      future_native_consumer_view_packed_weight_descriptor_read_error_count == 0 &&
      future_native_consumer_view_scale_metadata_handle_read_error_count == 0 &&
      future_native_consumer_view_aux_metadata_handle_read_error_count == 0 &&
      future_native_consumer_program_view_error_count == 0 &&
      future_native_consumer_program_view_ptr_error_count == 0 &&
      future_native_consumer_kernel_arg_packet_error_count == 0 &&
      future_native_consumer_kernel_arg_packet_descriptor_ptr_read_error_count == 0 &&
      future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_error_count == 0 &&
      future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_error_count == 0 &&
      future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_error_count == 0 &&
      future_native_consumer_kernel_entry_summary_error_count == 0 &&
      future_native_consumer_kernel_entry_args_error_count == 0 &&
      future_native_consumer_kernel_entry_args_ptr_error_count == 0 &&
      future_native_consumer_launch_envelope_args_error_count == 0 &&
      future_native_consumer_launch_envelope_args_ptr_error_count == 0 &&
      future_native_consumer_kernel_launch_descriptor_error_count == 0 &&
      future_native_consumer_kernel_launch_context_error_count == 0 &&
      future_native_consumer_invocation_error_count == 0 &&
      future_native_consumer_invocation_entry_error_count == 0 &&
      future_native_consumer_endpoint_error_count == 0 &&
      future_native_consumer_endpoint_ptr_error_count == 0 &&
      future_native_consumer_wna16_adjacent_typed_slot_error_count == 0 &&
      future_native_consumer_request_ptr_error_count == 0 &&
      future_native_consumer_request_launch_error_count == 0 &&
      future_native_consumer_request_launch_ptr_error_count == 0;

  hip_check(hipFree(d_descriptor), "hipFree descriptor");
  hip_check(hipFree(d_packed), "hipFree packed");
  hip_check(hipFree(d_scale), "hipFree scale");
  if (d_aux != nullptr) {
    hip_check(hipFree(d_aux), "hipFree aux");
  }
  hip_check(hipFree(d_address_key), "hipFree address_key");
  hip_check(hipFree(d_expert), "hipFree expert");
  hip_check(hipFree(d_ok), "hipFree ok");
  hip_check(hipFree(d_hash), "hipFree hash");
  hip_check(hipFree(d_single_field_mirror_ok), "hipFree single_field_mirror_ok");
  hip_check(
      hipFree(d_single_field_mirror_hash),
      "hipFree single_field_mirror_hash");
  hip_check(
      hipFree(d_kernel_side_consumer_path_ok),
      "hipFree kernel_side_consumer_path_ok");
  hip_check(
      hipFree(d_kernel_side_consumer_path_hash),
      "hipFree kernel_side_consumer_path_hash");
  hip_check(
      hipFree(d_kernel_side_compatible_consumer_ok),
      "hipFree kernel_side_compatible_consumer_ok");
  hip_check(
      hipFree(d_kernel_side_compatible_consumer_hash),
      "hipFree kernel_side_compatible_consumer_hash");
  hip_check(
      hipFree(d_future_kernel_consumer_ok),
      "hipFree future_kernel_consumer_ok");
  hip_check(
      hipFree(d_future_kernel_consumer_hash),
      "hipFree future_kernel_consumer_hash");
  hip_check(
      hipFree(d_future_kernel_single_field_mirror_ok),
      "hipFree future_kernel_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_kernel_single_field_mirror_hash),
      "hipFree future_kernel_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_kernel_compatible_path_ok),
      "hipFree future_kernel_compatible_path_ok");
  hip_check(
      hipFree(d_future_kernel_compatible_path_hash),
      "hipFree future_kernel_compatible_path_hash");
  hip_check(
      hipFree(d_future_native_consumer_ok),
      "hipFree future_native_consumer_ok");
  hip_check(
      hipFree(d_future_native_consumer_hash),
      "hipFree future_native_consumer_hash");
  hip_check(
      hipFree(d_future_native_single_field_mirror_ok),
      "hipFree future_native_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_single_field_mirror_hash),
      "hipFree future_native_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_launch_consumer_ok),
      "hipFree future_native_launch_consumer_ok");
  hip_check(
      hipFree(d_future_native_launch_consumer_hash),
      "hipFree future_native_launch_consumer_hash");
  hip_check(
      hipFree(d_future_native_launch_single_field_mirror_ok),
      "hipFree future_native_launch_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_launch_single_field_mirror_hash),
      "hipFree future_native_launch_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_dispatch_consumer_ok),
      "hipFree future_native_dispatch_consumer_ok");
  hip_check(
      hipFree(d_future_native_dispatch_consumer_hash),
      "hipFree future_native_dispatch_consumer_hash");
  hip_check(
      hipFree(d_future_native_dispatch_handle_projection_hash),
      "hipFree future_native_dispatch_handle_projection_hash");
  hip_check(
      hipFree(d_future_native_dispatch_single_field_mirror_ok),
      "hipFree future_native_dispatch_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_dispatch_single_field_mirror_hash),
      "hipFree future_native_dispatch_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_dispatch_ptr_consumer_ok),
      "hipFree future_native_dispatch_ptr_consumer_ok");
  hip_check(
      hipFree(d_future_native_dispatch_ptr_consumer_hash),
      "hipFree future_native_dispatch_ptr_consumer_hash");
  hip_check(
      hipFree(d_future_native_dispatch_ptr_handle_projection_hash),
      "hipFree future_native_dispatch_ptr_handle_projection_hash");
  hip_check(
      hipFree(d_future_native_dispatch_ptr_single_field_mirror_ok),
      "hipFree future_native_dispatch_ptr_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_dispatch_ptr_single_field_mirror_hash),
      "hipFree future_native_dispatch_ptr_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_consumer_ok),
      "hipFree future_native_arg_slot_consumer_ok");
  hip_check(
      hipFree(d_future_native_arg_slot_consumer_hash),
      "hipFree future_native_arg_slot_consumer_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_handle_projection_hash),
      "hipFree future_native_arg_slot_handle_projection_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_descriptor_ptr_read_ok),
      "hipFree future_native_arg_slot_descriptor_ptr_read_ok");
  hip_check(
      hipFree(d_future_native_arg_slot_descriptor_ptr_read_hash),
      "hipFree future_native_arg_slot_descriptor_ptr_read_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_packed_weight_descriptor_read_ok),
      "hipFree future_native_arg_slot_packed_weight_descriptor_read_ok");
  hip_check(
      hipFree(d_future_native_arg_slot_packed_weight_descriptor_read_hash),
      "hipFree future_native_arg_slot_packed_weight_descriptor_read_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_scale_metadata_handle_read_ok),
      "hipFree future_native_arg_slot_scale_metadata_handle_read_ok");
  hip_check(
      hipFree(d_future_native_arg_slot_scale_metadata_handle_read_hash),
      "hipFree future_native_arg_slot_scale_metadata_handle_read_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_aux_metadata_handle_read_ok),
      "hipFree future_native_arg_slot_aux_metadata_handle_read_ok");
  hip_check(
      hipFree(d_future_native_arg_slot_aux_metadata_handle_read_hash),
      "hipFree future_native_arg_slot_aux_metadata_handle_read_hash");
  hip_check(
      hipFree(d_future_native_arg_slot_single_field_mirror_ok),
      "hipFree future_native_arg_slot_single_field_mirror_ok");
  hip_check(
      hipFree(d_future_native_arg_slot_single_field_mirror_hash),
      "hipFree future_native_arg_slot_single_field_mirror_hash");
  hip_check(
      hipFree(d_future_native_consumer_view_ok),
      "hipFree future_native_consumer_view_ok");
  hip_check(
      hipFree(d_future_native_consumer_view_hash),
      "hipFree future_native_consumer_view_hash");
  hip_check(
      hipFree(d_future_native_consumer_view_handle_projection_hash),
      "hipFree future_native_consumer_view_handle_projection_hash");
  hip_check(
      hipFree(d_future_native_consumer_view_descriptor_ptr_read_ok),
      "hipFree future_native_consumer_view_descriptor_ptr_read_ok");
  hip_check(
      hipFree(d_future_native_consumer_view_descriptor_ptr_read_hash),
      "hipFree future_native_consumer_view_descriptor_ptr_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_view_packed_weight_descriptor_read_ok),
      "hipFree future_native_consumer_view_packed_weight_descriptor_read_ok");
  hip_check(
      hipFree(d_future_native_consumer_view_packed_weight_descriptor_read_hash),
      "hipFree future_native_consumer_view_packed_weight_descriptor_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_view_scale_metadata_handle_read_ok),
      "hipFree future_native_consumer_view_scale_metadata_handle_read_ok");
  hip_check(
      hipFree(d_future_native_consumer_view_scale_metadata_handle_read_hash),
      "hipFree future_native_consumer_view_scale_metadata_handle_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_view_aux_metadata_handle_read_ok),
      "hipFree future_native_consumer_view_aux_metadata_handle_read_ok");
  hip_check(
      hipFree(d_future_native_consumer_view_aux_metadata_handle_read_hash),
      "hipFree future_native_consumer_view_aux_metadata_handle_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_program_view_ok),
      "hipFree future_native_consumer_program_view_ok");
  hip_check(
      hipFree(d_future_native_consumer_program_view_hash),
      "hipFree future_native_consumer_program_view_hash");
  hip_check(
      hipFree(d_future_native_consumer_program_view_handle_projection_hash),
      "hipFree future_native_consumer_program_view_handle_projection_hash");
  hip_check(
      hipFree(d_future_native_consumer_program_view_ptr_ok),
      "hipFree future_native_consumer_program_view_ptr_ok");
  hip_check(
      hipFree(d_future_native_consumer_program_view_ptr_hash),
      "hipFree future_native_consumer_program_view_ptr_hash");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_ok),
      "hipFree future_native_consumer_kernel_arg_packet_ok");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_hash),
      "hipFree future_native_consumer_kernel_arg_packet_hash");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok),
      "hipFree future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash),
      "hipFree future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash");
  hip_check(
      hipFree(
          d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok),
      "hipFree future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok");
  hip_check(
      hipFree(
          d_future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash),
      "hipFree future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok),
      "hipFree future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok");
  hip_check(
      hipFree(
          d_future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash),
      "hipFree future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok),
      "hipFree future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash),
      "hipFree future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash");
  hip_check(
      hipFree(d_future_native_consumer_kernel_entry_summary),
      "hipFree future_native_consumer_kernel_entry_summary");
  hip_check(
      hipFree(d_future_native_consumer_kernel_arg_packet),
      "hipFree future_native_consumer_kernel_arg_packet");
  hip_check(
      hipFree(d_future_native_consumer_kernel_entry_args_summary),
      "hipFree future_native_consumer_kernel_entry_args_summary");
  hip_check(
      hipFree(d_future_native_consumer_kernel_entry_args_ptr_summary),
      "hipFree future_native_consumer_kernel_entry_args_ptr_summary");
  hip_check(
      hipFree(d_future_native_consumer_launch_envelope_args_summary),
      "hipFree future_native_consumer_launch_envelope_args_summary");
  hip_check(
      hipFree(d_future_native_consumer_launch_envelope_args_ptr_summary),
      "hipFree future_native_consumer_launch_envelope_args_ptr_summary");
  hip_check(
      hipFree(d_future_native_consumer_kernel_launch_descriptor_summary),
      "hipFree future_native_consumer_kernel_launch_descriptor_summary");
  hip_check(
      hipFree(d_future_native_consumer_kernel_launch_context_summary),
      "hipFree future_native_consumer_kernel_launch_context_summary");
  hip_check(
      hipFree(d_future_native_consumer_invocation_summary),
      "hipFree future_native_consumer_invocation_summary");
  hip_check(
      hipFree(d_future_native_consumer_invocation_entry_summary),
      "hipFree future_native_consumer_invocation_entry_summary");
  hip_check(
      hipFree(d_future_native_consumer_endpoint_summary),
      "hipFree future_native_consumer_endpoint_summary");
  hip_check(
      hipFree(d_future_native_consumer_endpoint_ptr_summary),
      "hipFree future_native_consumer_endpoint_ptr_summary");
  hip_check(
      hipFree(d_future_native_consumer_wna16_adjacent_typed_slot_summary),
      "hipFree future_native_consumer_wna16_adjacent_typed_slot_summary");
  hip_check(
      hipFree(d_future_native_consumer_request_ptr_summary),
      "hipFree future_native_consumer_request_ptr_summary");
  hip_check(
      hipFree(d_future_native_consumer_request_launch_summary),
      "hipFree future_native_consumer_request_launch_summary");
  hip_check(
      hipFree(d_future_native_consumer_request_launch_ptr_summary),
      "hipFree future_native_consumer_request_launch_ptr_summary");
  hip_check(
      hipFree(d_future_native_consumer_kernel_entry_args),
      "hipFree future_native_consumer_kernel_entry_args");
  hip_check(
      hipFree(d_future_native_consumer_launch_envelope_args_packet),
      "hipFree future_native_consumer_launch_envelope_args_packet");
  hip_check(
      hipFree(d_future_native_consumer_launch_envelope_args_ptr_packet),
      "hipFree future_native_consumer_launch_envelope_args_ptr_packet");
  hip_check(
      hipFree(d_future_native_consumer_kernel_launch_descriptor_packet),
      "hipFree future_native_consumer_kernel_launch_descriptor_packet");
  hip_check(
      hipFree(d_future_native_consumer_kernel_launch_context_packet),
      "hipFree future_native_consumer_kernel_launch_context_packet");
  hip_check(
      hipFree(d_future_native_consumer_invocation_packet),
      "hipFree future_native_consumer_invocation_packet");
  hip_check(
      hipFree(d_future_native_consumer_endpoint_packet),
      "hipFree future_native_consumer_endpoint_packet");
  hip_check(
      hipFree(d_future_native_consumer_request_ptr_packet),
      "hipFree future_native_consumer_request_ptr_packet");
  hip_check(
      hipFree(d_future_native_consumer_request_launch_packet),
      "hipFree future_native_consumer_request_launch_packet");
  if (d_future_native_dispatch_packet != nullptr) {
    hip_check(
        hipFree(d_future_native_dispatch_packet),
        "hipFree future_native_dispatch_packet");
  }
  if (d_future_native_dispatch_ptr_packet != nullptr) {
    hip_check(
        hipFree(d_future_native_dispatch_ptr_packet),
        "hipFree future_native_dispatch_ptr_packet");
  }
  if (d_future_native_consumer_program_view_packet != nullptr) {
    hip_check(
        hipFree(d_future_native_consumer_program_view_packet),
        "hipFree future_native_consumer_program_view_packet");
  }
  if (d_future_native_consumer_program_view_ptr_packet != nullptr) {
    hip_check(
        hipFree(d_future_native_consumer_program_view_ptr_packet),
        "hipFree future_native_consumer_program_view_ptr_packet");
  }

  std::cout << "{";
  std::cout << "\"ok\":" << (all_ok ? "true" : "false");
  std::cout << ",\"device\":" << args.device;
  std::cout << ",\"row_count\":" << rows;
  std::cout << ",\"column_count\":4";
  std::cout << ",\"abi_name\":\"" << kPremapKernelSideTypedConsumerAbiV1Name << "\"";
  std::cout << ",\"abi_handle_column_count\":"
            << kPremapKernelSideTypedConsumerAbiV1HandleColumnCount;
  std::cout << ",\"abi_payload_bytes_allowed\":false";
  std::cout << ",\"abi_kernel_arg_pass_allowed\":false";
  std::cout << ",\"adapter_name\":\"" << kPremapKernelSideTypedConsumerAdapterV1Name
            << "\"";
  std::cout << ",\"adapter_payload_deref_allowed\":false";
  std::cout << ",\"adapter_kernel_arg_pass_allowed\":false";
  std::cout << ",\"kernel_consumer_envelope_name\":\""
            << kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name << "\"";
  std::cout << ",\"kernel_consumer_envelope_checked\":"
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE)
            << "true";
#else
            << "false";
#endif
  std::cout << ",\"kernel_consumer_envelope_payload_bytes\":0";
  std::cout << ",\"kernel_consumer_envelope_passed_to_kernel\":false";
  std::cout << ",\"single_field_mirror_checked\":"
            << (single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"single_field_mirror_mode\":\"" << kSingleFieldMirrorMode
            << "\"";
  std::cout << ",\"single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"single_field_mirror_source\":\"" << kSingleFieldMirrorSource
            << "\"";
  std::cout << ",\"single_field_mirror_row_count\":"
            << single_field_mirror_row_count;
  std::cout << ",\"single_field_mirror_row_ok_count\":"
            << (single_field_mirror_checked ? single_field_mirror_ok_count : 0);
  std::cout << ",\"single_field_mirror_error_count\":"
            << single_field_mirror_error_count;
  std::cout << ",\"single_field_mirror_hash_accumulator\":\"" << std::hex
            << single_field_mirror_hash_acc << std::dec << "\"";
  std::cout << ",\"single_field_mirror_payload_bytes\":0";
  std::cout << ",\"single_field_mirror_passed_to_kernel\":false";
  std::cout << ",\"single_field_mirror_changes_kernel_launch_args\":false";
  std::cout << ",\"single_field_mirror_kernel_side_typed_consumer_compatible\":"
            << (single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"single_field_mirror_current_wna16_arg_compatible\":false";
  std::cout << ",\"kernel_side_consumer_path_name\":\""
            << kPremapKernelSideTypedConsumerPathV1Name << "\"";
  std::cout << ",\"kernel_side_consumer_path_checked\":"
            << (kernel_side_consumer_path_checked ? "true" : "false");
  std::cout << ",\"kernel_side_consumer_path_mode\":\"readonly_typed_row_consumer_path\"";
  std::cout << ",\"kernel_side_consumer_path_source\":\""
            << kPremapKernelSideTypedConsumerAdapterV1Name << "\"";
  std::cout << ",\"kernel_side_consumer_path_row_count\":"
            << kernel_side_consumer_path_row_count;
  std::cout << ",\"kernel_side_consumer_path_row_ok_count\":"
            << (kernel_side_consumer_path_checked
                    ? kernel_side_consumer_path_ok_count
                    : 0);
  std::cout << ",\"kernel_side_consumer_path_error_count\":"
            << kernel_side_consumer_path_error_count;
  std::cout << ",\"kernel_side_consumer_path_hash_accumulator\":\"" << std::hex
            << kernel_side_consumer_path_hash_acc << std::dec << "\"";
  std::cout << ",\"kernel_side_consumer_path_payload_bytes\":0";
  std::cout << ",\"kernel_side_consumer_path_passed_to_kernel\":false";
  std::cout << ",\"kernel_side_consumer_path_changes_kernel_launch_args\":false";
  std::cout << ",\"kernel_side_consumer_path_current_wna16_arg_compatible\":false";
  std::cout << ",\"kernel_side_compatible_consumer_name\":\""
            << kPremapKernelSideCompatibleConsumerAbiV1Name << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_checked\":"
            << (kernel_side_compatible_consumer_checked ? "true" : "false");
  std::cout << ",\"kernel_side_compatible_consumer_mode\":\""
            << kPremapKernelSideCompatibleConsumerAbiV1Mode << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_source\":\""
            << kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_row_count\":"
            << kernel_side_compatible_consumer_row_count;
  std::cout << ",\"kernel_side_compatible_consumer_row_ok_count\":"
            << (kernel_side_compatible_consumer_checked
                    ? kernel_side_compatible_consumer_ok_count
                    : 0);
  std::cout << ",\"kernel_side_compatible_consumer_error_count\":"
            << kernel_side_compatible_consumer_error_count;
  std::cout << ",\"kernel_side_compatible_consumer_hash_accumulator\":\"" << std::hex
            << kernel_side_compatible_consumer_hash_acc << std::dec << "\"";
  std::cout << ",\"kernel_side_compatible_consumer_payload_bytes\":0";
  std::cout << ",\"kernel_side_compatible_consumer_payload_deref_allowed\":false";
  std::cout << ",\"kernel_side_compatible_consumer_passed_to_kernel\":false";
  std::cout << ",\"kernel_side_compatible_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"kernel_side_compatible_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"kernel_side_compatible_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"kernel_side_compatible_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_consumer_args_name\":\""
            << kPremapFutureKernelSideConsumerArgsV1Name << "\"";
  std::cout << ",\"future_kernel_consumer_args_checked\":"
            << (future_kernel_consumer_args_checked ? "true" : "false");
  std::cout << ",\"future_kernel_consumer_args_mode\":\""
            << kPremapFutureKernelSideConsumerArgsV1Mode << "\"";
  std::cout << ",\"future_kernel_consumer_args_source\":\""
            << kPremapKernelSideTypedConsumerLaunchEnvelopeV1Name << "\"";
  std::cout << ",\"future_kernel_consumer_args_struct_size\":"
            << sizeof(PremapFutureKernelSideConsumerArgsV1);
  std::cout << ",\"future_kernel_consumer_args_struct_align\":"
            << alignof(PremapFutureKernelSideConsumerArgsV1);
  std::cout << ",\"future_kernel_consumer_args_result_struct_size\":"
            << sizeof(PremapFutureKernelSideConsumerResultV1);
  std::cout << ",\"future_kernel_consumer_args_result_struct_align\":"
            << alignof(PremapFutureKernelSideConsumerResultV1);
  std::cout << ",\"future_kernel_consumer_args_offset_envelope\":"
            << offsetof(PremapFutureKernelSideConsumerArgsV1, envelope);
  std::cout << ",\"future_kernel_consumer_args_offset_field_mask\":"
            << offsetof(PremapFutureKernelSideConsumerArgsV1, field_mask);
  std::cout << ",\"future_kernel_consumer_args_offset_single_field_mirror_kind\":"
            << offsetof(PremapFutureKernelSideConsumerArgsV1, single_field_mirror_kind);
  std::cout << ",\"future_kernel_consumer_args_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelSideConsumerArgsV1, payload_bytes);
  std::cout << ",\"future_kernel_consumer_args_offset_flags\":"
            << offsetof(PremapFutureKernelSideConsumerArgsV1, flags);
  std::cout << ",\"future_kernel_consumer_args_row_count\":"
            << future_kernel_consumer_args_row_count;
  std::cout << ",\"future_kernel_consumer_args_row_ok_count\":"
            << (future_kernel_consumer_args_checked
                    ? future_kernel_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_consumer_args_error_count\":"
            << future_kernel_consumer_args_error_count;
  std::cout << ",\"future_kernel_consumer_args_hash_accumulator\":\""
            << std::hex << future_kernel_consumer_hash_acc << std::dec << "\"";
  std::cout << ",\"future_kernel_consumer_args_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_consumer_args_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_checked\":"
            << (future_kernel_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_row_count\":"
            << future_kernel_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_row_ok_count\":"
            << (future_kernel_single_field_mirror_checked
                    ? future_kernel_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_error_count\":"
            << future_kernel_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_consumer_args_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_kernel_single_field_mirror_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_consumer_args_payload_bytes\":0";
  std::cout << ",\"future_kernel_consumer_args_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_consumer_args_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_consumer_args_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_consumer_args_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_consumer_args_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_consumer_args_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_name\":\""
            << kPremapFutureKernelArgsCompatibleConsumerPathV1Name << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_checked\":"
            << (future_kernel_compatible_path_checked ? "true" : "false");
  std::cout << ",\"future_kernel_args_compatible_consumer_path_mode\":\""
            << kPremapFutureKernelArgsCompatibleConsumerPathV1Mode << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_source\":\""
            << kPremapFutureKernelArgsCompatibleConsumerPathV1Source << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_row_count\":"
            << future_kernel_compatible_path_row_count;
  std::cout << ",\"future_kernel_args_compatible_consumer_path_row_ok_count\":"
            << (future_kernel_compatible_path_checked
                    ? future_kernel_compatible_path_ok_count
                    : 0);
  std::cout << ",\"future_kernel_args_compatible_consumer_path_error_count\":"
            << future_kernel_compatible_path_error_count;
  std::cout << ",\"future_kernel_args_compatible_consumer_path_hash_accumulator\":\""
            << std::hex << future_kernel_compatible_path_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_payload_bytes\":0";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_checked\":"
            << (future_native_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_params_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_consumer_params_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerResultV1);
  std::cout << ",\"future_kernel_native_consumer_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerResultV1);
  std::cout << ",\"future_kernel_native_consumer_params_offset_descriptor_ptr\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, descriptor_ptr);
  std::cout << ",\"future_kernel_native_consumer_params_offset_packed_weight_descriptor\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, packed_weight_descriptor);
  std::cout << ",\"future_kernel_native_consumer_params_offset_scale_metadata_handle\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, scale_metadata_handle);
  std::cout << ",\"future_kernel_native_consumer_params_offset_aux_metadata_handle\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, aux_metadata_handle);
  std::cout << ",\"future_kernel_native_consumer_params_offset_expert_id\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, expert_id);
  std::cout << ",\"future_kernel_native_consumer_params_offset_address_key_hash\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, address_key_hash);
  std::cout << ",\"future_kernel_native_consumer_params_offset_row_count\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, row_count);
  std::cout << ",\"future_kernel_native_consumer_params_offset_field_mask\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, field_mask);
  std::cout << ",\"future_kernel_native_consumer_params_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_params_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerParamsV1, flags);
  std::cout << ",\"future_kernel_native_consumer_row_count\":"
            << future_native_consumer_row_count;
  std::cout << ",\"future_kernel_native_consumer_row_ok_count\":"
            << (future_native_consumer_checked
                    ? future_native_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_error_count\":"
            << future_native_consumer_error_count;
  std::cout << ",\"future_kernel_native_consumer_hash_accumulator\":\""
            << std::hex << future_native_consumer_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_checked\":"
            << (future_native_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_row_count\":"
            << future_native_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_single_field_mirror_checked
                    ? future_native_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_error_count\":"
            << future_native_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_single_field_mirror_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_checked\":"
            << (future_native_launch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_launch_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_version\":"
            << kPremapFutureKernelNativeConsumerLaunchAbiV1Version;
  std::cout << ",\"future_kernel_native_launch_consumer_launch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchV1);
  std::cout << ",\"future_kernel_native_launch_consumer_launch_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerLaunchV1);
  std::cout << ",\"future_kernel_native_launch_consumer_params_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_launch_consumer_params_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_launch_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchResultV1);
  std::cout << ",\"future_kernel_native_launch_consumer_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerLaunchResultV1);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_params\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, params);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, abi_version);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_params_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, params_struct_size);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_result_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, result_struct_size);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_row_stride\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, row_stride);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, payload_bytes);
  std::cout << ",\"future_kernel_native_launch_consumer_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerLaunchV1, flags);
  std::cout << ",\"future_kernel_native_launch_consumer_row_stride\":1";
  std::cout << ",\"future_kernel_native_launch_consumer_row_count\":"
            << future_native_launch_consumer_row_count;
  std::cout << ",\"future_kernel_native_launch_consumer_row_ok_count\":"
            << (future_native_launch_consumer_checked
                    ? future_native_launch_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_launch_consumer_error_count\":"
            << future_native_launch_consumer_error_count;
  std::cout << ",\"future_kernel_native_launch_consumer_hash_accumulator\":\""
            << std::hex << future_native_launch_consumer_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_launch_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_checked\":"
            << (future_native_launch_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_row_count\":"
            << future_native_launch_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_launch_single_field_mirror_checked
                    ? future_native_launch_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_error_count\":"
            << future_native_launch_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_launch_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_launch_single_field_mirror_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_launch_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_launch_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_checked\":"
            << (future_native_dispatch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_version\":"
            << kPremapFutureKernelNativeConsumerDispatchAbiV1Version;
  std::cout << ",\"future_kernel_native_dispatch_consumer_dispatch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_dispatch_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerDispatchV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchResultV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerDispatchResultV1);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_launch\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, launch);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_dispatch_version\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, dispatch_version);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_grid_x\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, grid_x);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_block_x\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, block_x);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_shared_mem_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, shared_mem_bytes);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_row_offset\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, row_offset);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_row_limit\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, row_limit);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_rows_per_program\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, rows_per_program);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, payload_bytes);
  std::cout << ",\"future_kernel_native_dispatch_consumer_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchV1, flags);
  std::cout << ",\"future_kernel_native_dispatch_consumer_grid_x\":"
            << dispatch_blocks;
  std::cout << ",\"future_kernel_native_dispatch_consumer_block_x\":"
            << threads;
  std::cout << ",\"future_kernel_native_dispatch_consumer_shared_mem_bytes\":0";
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_offset\":"
            << dispatch_row_offset;
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_limit\":"
            << dispatch_row_limit;
  std::cout << ",\"future_kernel_native_dispatch_consumer_rows_per_program\":"
            << threads;
  std::cout << ",\"future_kernel_native_dispatch_consumer_active_rows\":"
            << future_native_dispatch_active_rows;
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_threads\":"
            << dispatch_launch_threads;
  std::cout << ",\"future_kernel_native_dispatch_consumer_program_iteration_checked\":"
            << (future_native_dispatch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_assignment_formula\":\""
            << "row_offset + program_id * rows_per_program + lane_id\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_program_count\":"
            << dispatch_blocks;
  std::cout << ",\"future_kernel_native_dispatch_consumer_full_program_count\":"
            << dispatch_full_program_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_last_program_active_rows\":"
            << dispatch_last_program_active_rows;
  std::cout << ",\"future_kernel_native_dispatch_consumer_inactive_lane_count\":"
            << dispatch_inactive_lane_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_first_program_row_offset\":"
            << dispatch_first_program_row_offset;
  std::cout << ",\"future_kernel_native_dispatch_consumer_last_program_row_offset\":"
            << dispatch_last_program_row_offset;
  std::cout << ",\"future_kernel_native_dispatch_consumer_program_iteration_hash\":\""
            << std::hex << dispatch_program_iteration_hash << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_geometry_checked\":"
            << (future_native_dispatch_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_covers_active_rows\":"
            << (future_native_dispatch_launch_covers_active_rows ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_launch_minimal_cover\":"
            << (future_native_dispatch_launch_minimal_cover ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_count\":"
            << future_native_dispatch_consumer_row_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_row_ok_count\":"
            << (future_native_dispatch_consumer_checked
                    ? future_native_dispatch_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_dispatch_consumer_error_count\":"
            << future_native_dispatch_consumer_error_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_hash_accumulator\":\""
            << std::hex << future_native_dispatch_consumer_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator\":\""
            << std::hex << future_native_dispatch_handle_projection_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_dispatch_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_checked\":"
            << (future_native_dispatch_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_row_count\":"
            << future_native_dispatch_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_dispatch_single_field_mirror_checked
                    ? future_native_dispatch_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_error_count\":"
            << future_native_dispatch_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_dispatch_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_dispatch_single_field_mirror_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_dispatch_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_checked\":"
            << (future_native_dispatch_ptr_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_version\":"
            << kPremapFutureKernelNativeConsumerDispatchPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_packet_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchPtrV1);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_packet_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerDispatchPtrV1);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_dispatch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchV1);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchResultV1);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_offset_dispatch\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchPtrV1, dispatch);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchPtrV1, abi_version);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_offset_dispatch_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchPtrV1, dispatch_struct_size);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_offset_result_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchPtrV1, result_struct_size);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchPtrV1, payload_bytes);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerDispatchPtrV1, flags);
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI)
  const bool future_native_dispatch_ptr_packet_visible =
      future_native_dispatch_ptr.dispatch != nullptr;
  const int future_native_dispatch_ptr_packet_chain_depth = 2;
#else
  const bool future_native_dispatch_ptr_packet_visible = false;
  const int future_native_dispatch_ptr_packet_chain_depth = 0;
#endif
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_packet_visible\":"
            << (future_native_dispatch_ptr_packet_visible ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible\":"
            << (d_future_native_dispatch_packet != nullptr ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_packet_chain_depth\":"
            << future_native_dispatch_ptr_packet_chain_depth;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_row_count\":"
            << future_native_dispatch_ptr_consumer_row_count;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_row_ok_count\":"
            << (future_native_dispatch_ptr_consumer_checked
                    ? future_native_dispatch_ptr_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_error_count\":"
            << future_native_dispatch_ptr_consumer_error_count;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_hash_accumulator\":\""
            << std::hex << future_native_dispatch_ptr_consumer_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator\":\""
            << std::hex
            << future_native_dispatch_ptr_handle_projection_hash_acc << std::dec
            << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_checked\":"
            << (future_native_dispatch_ptr_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count\":"
            << future_native_dispatch_ptr_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_dispatch_ptr_single_field_mirror_checked
                    ? future_native_dispatch_ptr_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count\":"
            << future_native_dispatch_ptr_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_dispatch_ptr_single_field_mirror_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_abi_name\":\""
            << kPremapFutureKernelNativeConsumerArgSlotAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_checked\":"
            << (future_native_arg_slot_consumer_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_arg_slot_consumer_mode\":\""
            << kPremapFutureKernelNativeConsumerArgSlotAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_source\":\""
            << kPremapFutureKernelNativeConsumerArgSlotAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_version\":"
            << kPremapFutureKernelNativeConsumerArgSlotAbiV1Version;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_slot_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerArgSlotV1);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_slot_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerArgSlotV1);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_dispatch_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerDispatchPtrV1);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerArgSlotResultV1);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_offset_dispatch_ptr\":"
            << offsetof(PremapFutureKernelNativeConsumerArgSlotV1, dispatch_ptr);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerArgSlotV1, abi_version);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_offset_dispatch_ptr_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerArgSlotV1, dispatch_ptr_struct_size);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_offset_result_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerArgSlotV1, result_struct_size);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerArgSlotV1, payload_bytes);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerArgSlotV1, flags);
#if defined(MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI)
  const bool future_native_arg_slot_slot_visible =
      future_native_arg_slot.dispatch_ptr != nullptr;
  const int future_native_arg_slot_packet_chain_depth = 3;
#else
  const bool future_native_arg_slot_slot_visible = false;
  const int future_native_arg_slot_packet_chain_depth = 0;
#endif
  std::cout << ",\"future_kernel_native_arg_slot_consumer_slot_visible\":"
            << (future_native_arg_slot_slot_visible ? "true" : "false");
  std::cout << ",\"future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible\":"
            << (d_future_native_dispatch_ptr_packet != nullptr ? "true" : "false");
  std::cout << ",\"future_kernel_native_arg_slot_consumer_dispatch_packet_visible\":"
            << (d_future_native_dispatch_packet != nullptr ? "true" : "false");
  std::cout << ",\"future_kernel_native_arg_slot_consumer_packet_chain_depth\":"
            << future_native_arg_slot_packet_chain_depth;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_row_count\":"
            << future_native_arg_slot_consumer_row_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_row_ok_count\":"
            << (future_native_arg_slot_consumer_checked
                    ? future_native_arg_slot_consumer_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_error_count\":"
            << future_native_arg_slot_consumer_error_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_hash_accumulator\":\""
            << std::hex << future_native_arg_slot_consumer_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator\":\""
            << std::hex << future_native_arg_slot_handle_projection_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count\":"
            << future_native_arg_slot_descriptor_ptr_read_row_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count\":"
            << (future_native_arg_slot_consumer_checked
                    ? future_native_arg_slot_descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count\":"
            << future_native_arg_slot_descriptor_ptr_read_error_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator\":\""
            << std::hex << future_native_arg_slot_descriptor_ptr_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count\":"
            << future_native_arg_slot_packed_weight_descriptor_read_row_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_arg_slot_consumer_checked
                    ? future_native_arg_slot_packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count\":"
            << future_native_arg_slot_packed_weight_descriptor_read_error_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator\":\""
            << std::hex
            << future_native_arg_slot_packed_weight_descriptor_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count\":"
            << future_native_arg_slot_scale_metadata_handle_read_row_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_arg_slot_consumer_checked
                    ? future_native_arg_slot_scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count\":"
            << future_native_arg_slot_scale_metadata_handle_read_error_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator\":\""
            << std::hex
            << future_native_arg_slot_scale_metadata_handle_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count\":"
            << future_native_arg_slot_aux_metadata_handle_read_row_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_arg_slot_consumer_checked
                    ? future_native_arg_slot_aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count\":"
            << future_native_arg_slot_aux_metadata_handle_read_error_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator\":\""
            << std::hex << future_native_arg_slot_aux_metadata_handle_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_kind\":"
            << kSingleFieldMirrorKind;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_checked\":"
            << (future_native_arg_slot_single_field_mirror_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_field_name\":\""
            << kSingleFieldMirrorFieldName << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_row_count\":"
            << future_native_arg_slot_single_field_mirror_row_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count\":"
            << (future_native_arg_slot_single_field_mirror_checked
                    ? future_native_arg_slot_single_field_mirror_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_error_count\":"
            << future_native_arg_slot_single_field_mirror_error_count;
  std::cout << ",\"future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator\":\""
            << std::hex << future_native_arg_slot_single_field_mirror_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_view_abi_name\":\""
            << kPremapFutureKernelNativeConsumerViewAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_checked\":"
            << (future_native_consumer_view_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_view_mode\":\""
            << kPremapFutureKernelNativeConsumerViewAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_source\":\""
            << kPremapFutureKernelNativeConsumerViewAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_version\":"
            << kPremapFutureKernelNativeConsumerViewAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_view_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerViewV1);
  std::cout << ",\"future_kernel_native_consumer_view_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerViewV1);
  std::cout << ",\"future_kernel_native_consumer_view_params_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_consumer_view_params_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerParamsV1);
  std::cout << ",\"future_kernel_native_consumer_view_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerViewResultV1);
  std::cout << ",\"future_kernel_native_consumer_view_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerViewResultV1);
  std::cout << ",\"future_kernel_native_consumer_view_row_struct_size\":"
            << sizeof(PremapKernelSideTypedConsumerRowV1);
  std::cout << ",\"future_kernel_native_consumer_view_row_struct_align\":"
            << alignof(PremapKernelSideTypedConsumerRowV1);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_descriptor_ptr\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, descriptor_ptr);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_packed_weight_descriptor\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, packed_weight_descriptor);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_scale_metadata_handle\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, scale_metadata_handle);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_aux_metadata_handle\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, aux_metadata_handle);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_expert_id\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, expert_id);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_address_key_hash\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, address_key_hash);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset_row_index\":"
            << offsetof(PremapKernelSideTypedConsumerRowV1, row_index);
  std::cout << ",\"future_kernel_native_consumer_view_offset_params\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, params);
  std::cout << ",\"future_kernel_native_consumer_view_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, abi_version);
  std::cout << ",\"future_kernel_native_consumer_view_offset_source_packet_chain_depth\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, source_packet_chain_depth);
  std::cout << ",\"future_kernel_native_consumer_view_offset_row_offset\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, row_offset);
  std::cout << ",\"future_kernel_native_consumer_view_offset_row_limit\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, row_limit);
  std::cout << ",\"future_kernel_native_consumer_view_offset_rows_per_program\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, rows_per_program);
  std::cout << ",\"future_kernel_native_consumer_view_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_view_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerViewV1, flags);
  std::cout << ",\"future_kernel_native_consumer_view_source_packet_chain_depth\":"
            << (future_native_consumer_view_checked ? 3 : 0);
  std::cout << ",\"future_kernel_native_consumer_view_row_offset\":"
            << (future_native_consumer_view_checked ? dispatch_row_offset : 0);
  std::cout << ",\"future_kernel_native_consumer_view_row_limit\":"
            << (future_native_consumer_view_checked ? dispatch_row_limit : 0);
  std::cout << ",\"future_kernel_native_consumer_view_rows_per_program\":"
            << (future_native_consumer_view_checked ? threads : 0);
  std::cout << ",\"future_kernel_native_consumer_view_row_count\":"
            << future_native_consumer_view_row_count;
  std::cout << ",\"future_kernel_native_consumer_view_row_ok_count\":"
            << (future_native_consumer_view_checked
                    ? future_native_consumer_view_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_view_error_count\":"
            << future_native_consumer_view_error_count;
  std::cout << ",\"future_kernel_native_consumer_view_hash_accumulator\":\""
            << std::hex << future_native_consumer_view_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_handle_projection_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_view_handle_projection_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_descriptor_ptr_read_row_count\":"
            << future_native_consumer_view_descriptor_ptr_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_view_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_view_checked
                    ? future_native_consumer_view_descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_view_descriptor_ptr_read_error_count\":"
            << future_native_consumer_view_descriptor_ptr_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_view_descriptor_ptr_read_hash_accumulator\":\""
            << std::hex << future_native_consumer_view_descriptor_ptr_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_packed_weight_descriptor_read_row_count\":"
            << future_native_consumer_view_packed_weight_descriptor_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_view_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_view_checked
                    ? future_native_consumer_view_packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_view_packed_weight_descriptor_read_error_count\":"
            << future_native_consumer_view_packed_weight_descriptor_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_view_packed_weight_descriptor_read_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_view_packed_weight_descriptor_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_scale_metadata_handle_read_row_count\":"
            << future_native_consumer_view_scale_metadata_handle_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_view_checked
                    ? future_native_consumer_view_scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_view_scale_metadata_handle_read_error_count\":"
            << future_native_consumer_view_scale_metadata_handle_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_view_scale_metadata_handle_read_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_view_scale_metadata_handle_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_aux_metadata_handle_read_row_count\":"
            << future_native_consumer_view_aux_metadata_handle_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_view_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_view_checked
                    ? future_native_consumer_view_aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_view_aux_metadata_handle_read_error_count\":"
            << future_native_consumer_view_aux_metadata_handle_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_view_aux_metadata_handle_read_hash_accumulator\":\""
            << std::hex << future_native_consumer_view_aux_metadata_handle_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_view_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_consumer_view_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_consumer_view_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_view_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_view_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_view_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_view_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_view_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_abi_name\":\""
            << kPremapFutureKernelNativeConsumerProgramViewAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_checked\":"
            << (future_native_consumer_program_view_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_program_view_mode\":\""
            << kPremapFutureKernelNativeConsumerProgramViewAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_source\":\""
            << kPremapFutureKernelNativeConsumerProgramViewAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_version\":"
            << kPremapFutureKernelNativeConsumerProgramViewAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_program_view_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerProgramViewV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerProgramViewV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerProgramViewResultV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_result_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerProgramViewResultV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_view\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, view);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, abi_version);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_program_count\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, program_count);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_full_program_count\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, full_program_count);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_last_program_active_rows\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, last_program_active_rows);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_inactive_lane_count\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, inactive_lane_count);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_first_program_row_offset\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, first_program_row_offset);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_last_program_row_offset\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, last_program_row_offset);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_program_iteration_hash\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, program_iteration_hash);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_program_view_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewV1, flags);
  std::cout << ",\"future_kernel_native_consumer_program_view_row_assignment_formula\":\"program_id * rows_per_program + lane_id + row_offset\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_row_count\":"
            << future_native_consumer_program_view_row_count;
  std::cout << ",\"future_kernel_native_consumer_program_view_row_ok_count\":"
            << (future_native_consumer_program_view_checked
                    ? future_native_consumer_program_view_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_error_count\":"
            << future_native_consumer_program_view_error_count;
  std::cout << ",\"future_kernel_native_consumer_program_view_hash_accumulator\":\""
            << std::hex << future_native_consumer_program_view_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_handle_projection_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_program_view_handle_projection_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_consumer_program_view_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_consumer_program_view_program_count\":"
            << (future_native_consumer_program_view_checked
                    ? dispatch_blocks
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_full_program_count\":"
            << (future_native_consumer_program_view_checked
                    ? dispatch_full_program_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_last_program_active_rows\":"
            << (future_native_consumer_program_view_checked
                    ? dispatch_last_program_active_rows
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_inactive_lane_count\":"
            << (future_native_consumer_program_view_checked
                    ? dispatch_inactive_lane_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_first_program_row_offset\":"
            << (future_native_consumer_program_view_checked
                    ? dispatch_first_program_row_offset
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_last_program_row_offset\":"
            << (future_native_consumer_program_view_checked
                    ? dispatch_last_program_row_offset
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_program_iteration_hash\":\""
            << std::hex
            << (future_native_consumer_program_view_checked
                    ? dispatch_program_iteration_hash
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_program_view_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_abi_name\":\""
            << kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_checked\":"
            << (future_native_consumer_program_view_ptr_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_mode\":\""
            << kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_source\":\""
            << kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_version\":"
            << kPremapFutureKernelNativeConsumerProgramViewPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_packet_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerProgramViewPtrV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_packet_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerProgramViewPtrV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_program_view_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerProgramViewV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerProgramViewPtrResultV1);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_offset_program_view\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewPtrV1, program_view);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewPtrV1, abi_version);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_offset_program_view_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewPtrV1, program_view_struct_size);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_offset_result_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewPtrV1, result_struct_size);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewPtrV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerProgramViewPtrV1, flags);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_row_count\":"
            << future_native_consumer_program_view_ptr_row_count;
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_row_ok_count\":"
            << (future_native_consumer_program_view_ptr_checked
                    ? future_native_consumer_program_view_ptr_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_error_count\":"
            << future_native_consumer_program_view_ptr_error_count;
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_hash_accumulator\":\""
            << std::hex << future_native_consumer_program_view_ptr_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_abi_name\":\""
            << kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_checked\":"
            << (future_native_consumer_kernel_arg_packet_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_mode\":\""
            << kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_source\":\""
            << kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_version\":"
            << kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerKernelArgPacketV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_program_view_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerProgramViewPtrV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_result_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelArgPacketResultV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_offset_program_view_ptr\":"
            << offsetof(PremapFutureKernelNativeConsumerKernelArgPacketV1, program_view_ptr);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerKernelArgPacketV1, abi_version);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_offset_program_view_ptr_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerKernelArgPacketV1, program_view_ptr_struct_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_offset_result_struct_size\":"
            << offsetof(PremapFutureKernelNativeConsumerKernelArgPacketV1, result_struct_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerKernelArgPacketV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerKernelArgPacketV1, flags);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_row_count\":"
            << future_native_consumer_kernel_arg_packet_row_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_row_ok_count\":"
            << (future_native_consumer_kernel_arg_packet_checked
                    ? future_native_consumer_kernel_arg_packet_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_error_count\":"
            << future_native_consumer_kernel_arg_packet_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_hash_accumulator\":\""
            << std::hex << future_native_consumer_kernel_arg_packet_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_count\":"
            << future_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_kernel_arg_packet_checked
                    ? future_native_consumer_kernel_arg_packet_descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_error_count\":"
            << future_native_consumer_kernel_arg_packet_descriptor_ptr_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_count\":"
            << future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_kernel_arg_packet_checked
                    ? future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_error_count\":"
            << future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_count\":"
            << future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_arg_packet_checked
                    ? future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_error_count\":"
            << future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_count\":"
            << future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_arg_packet_checked
                    ? future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_error_count\":"
            << future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash_accumulator\":\""
            << std::hex
            << future_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash_acc
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_field_mask\":"
            << future_kernel_consumer_args_field_mask;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_required_field_mask\":"
            << kPremapFutureKernelSideConsumerFieldMaskRequired;
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_abi_name\":\""
            << kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_mode\":\"readonly_future_kernel_native_consumer_kernel_entry_summary_abi\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_source\":\""
            << kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_field_read_path\":\"kernel_entry_summary_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_packet_chain_depth\":4";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_checked\":"
            << (future_native_consumer_kernel_entry_summary_checked ? "true"
                                                                    : "false");
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_version\":"
            << kPremapFutureKernelNativeConsumerKernelEntrySummaryAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_packet_valid\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   packet_valid);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_row_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   row_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_row_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   row_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_descriptor_ptr_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   descriptor_ptr_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_packed_weight_descriptor_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   packed_weight_descriptor_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_scale_metadata_handle_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   scale_metadata_handle_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_aux_metadata_handle_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   aux_metadata_handle_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_expert_id_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   expert_id_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_address_key_hash_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   address_key_hash_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_row_metadata_read_ok_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   row_metadata_read_ok_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_error_count\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   error_count);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_field_mask\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   field_mask);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_payload_bytes\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_passed_to_kernel\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   passed_to_kernel);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_changes_kernel_launch_args\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   changes_kernel_launch_args);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_current_wna16_arg_compatible\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   current_wna16_arg_compatible);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_requires_wna16_arg_reinterpretation\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   requires_wna16_arg_reinterpretation);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_reserved\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   reserved);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_row_hash_accumulator\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   row_hash_accumulator);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_field_read_hash_accumulator\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   field_read_hash_accumulator);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_offset_row_metadata_hash_accumulator\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntrySummaryV1,
                   row_metadata_hash_accumulator);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_packet_valid\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_row_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_error_count\":"
            << future_native_consumer_kernel_entry_summary_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_field_mask\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_payload_bytes\":"
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary.payload_bytes
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_summary_checked
                    ? future_native_consumer_kernel_entry_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_abi_name\":\""
            << kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_mode\":\"readonly_future_kernel_native_consumer_kernel_entry_args_abi\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_source\":\""
            << kPremapFutureKernelNativeConsumerKernelArgPacketAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_field_read_path\":\"kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_packet_chain_depth\":5";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_checked\":"
            << (future_native_consumer_kernel_entry_args_checked ? "true"
                                                                 : "false");
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_version\":"
            << kPremapFutureKernelNativeConsumerKernelEntryArgsAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerKernelEntryArgsV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   kernel_arg_packet);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_summary\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   summary);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   kernel_arg_packet_struct_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_summary_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   summary_struct_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_payload_bytes\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_offset_flags\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelEntryArgsV1,
                   flags);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_kernel_arg_packet_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_packet_valid\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_row_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_error_count\":"
            << future_native_consumer_kernel_entry_args_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_field_mask\":"
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_args_checked
                    ? future_native_consumer_kernel_entry_args_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_abi_name\":\""
            << kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_mode\":\""
            << kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_source\":\""
            << kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_field_read_path\":\"kernel_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_packet_chain_depth\":6";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_checked\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked ? "true"
                                                                     : "false");
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_version\":"
            << kPremapFutureKernelNativeConsumerKernelEntryArgsPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1*);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_entry_args_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_packet_valid\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_row_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_error_count\":"
            << future_native_consumer_kernel_entry_args_ptr_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_field_mask\":"
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_entry_args_ptr_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_entry_args_ptr_checked
                    ? future_native_consumer_kernel_entry_args_ptr_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_abi_name\":\""
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_mode\":\""
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_source\":\""
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_field_read_path\":\"launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_packet_chain_depth\":7";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_checked\":"
            << (future_native_consumer_launch_envelope_args_checked ? "true"
                                                                    : "false");
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_version\":"
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_entry_args\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   entry_args);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_grid_x\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   grid_x);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_block_x\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   block_x);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_row_offset\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   row_offset);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_row_limit\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   row_limit);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_offset_rows_per_program\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1,
                   rows_per_program);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_entry_args_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntryArgsV1*);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_grid_x\":"
            << dispatch_blocks;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_block_x\":"
            << threads;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_row_offset\":"
            << dispatch_row_offset;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_row_limit\":"
            << dispatch_row_limit;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_rows_per_program\":"
            << threads;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_packet_valid\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_row_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_error_count\":"
            << future_native_consumer_launch_envelope_args_error_count;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_field_mask\":"
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_launch_envelope_args_checked
                    ? future_native_consumer_launch_envelope_args_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_abi_name\":\""
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_mode\":\""
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_source\":\""
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_field_read_path\":\"launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_packet_chain_depth\":8";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_checked\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked ? "true"
                                                                        : "false");
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_version\":"
            << kPremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_offset_launch_args\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1,
                   launch_args);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_offset_launch_args_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1,
                   launch_args_struct_size);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_offset_pointer_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1,
                   pointer_size);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_offset_payload_bytes\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1,
                   payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_offset_flags\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1,
                   flags);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_launch_args_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsV1*);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_packet_valid\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_row_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_error_count\":"
            << future_native_consumer_launch_envelope_args_ptr_error_count;
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_field_mask\":"
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_launch_envelope_args_ptr_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_launch_envelope_args_ptr_checked
                    ? future_native_consumer_launch_envelope_args_ptr_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_abi_name\":\""
            << kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_mode\":\""
            << kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_source\":\""
            << kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_field_read_path\":\"kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_packet_chain_depth\":9";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_checked\":"
            << (future_native_consumer_kernel_launch_descriptor_checked ? "true"
                                                                        : "false");
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_version\":"
            << kPremapFutureKernelNativeConsumerKernelLaunchDescriptorAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_launch_args_ptr\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   launch_args_ptr);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_summary\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   summary);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_expected_schema_hash_hi\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   expected_schema_hash_hi);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_expected_schema_hash_lo\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   expected_schema_hash_lo);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_grid_x\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   grid_x);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_block_x\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   block_x);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_row_offset\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   row_offset);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_row_limit\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   row_limit);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_rows_per_program\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   rows_per_program);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_payload_bytes\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_offset_flags\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1,
                   flags);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_launch_args_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerLaunchEnvelopeArgsPtrV1*);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_grid_x\":"
            << dispatch_blocks;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_block_x\":"
            << threads;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_row_offset\":"
            << dispatch_row_offset;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_row_limit\":"
            << dispatch_row_limit;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_rows_per_program\":"
            << threads;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_packet_valid\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_row_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_error_count\":"
            << future_native_consumer_kernel_launch_descriptor_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_field_mask\":"
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_descriptor_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_launch_descriptor_checked
                    ? future_native_consumer_kernel_launch_descriptor_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_abi_name\":\""
            << kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_mode\":\""
            << kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_source\":\""
            << kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_field_read_path\":\"kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_packet_chain_depth\":10";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_checked\":"
            << (future_native_consumer_kernel_launch_context_checked ? "true"
                                                                     : "false");
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_version\":"
            << kPremapFutureKernelNativeConsumerKernelLaunchContextAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerKernelLaunchContextV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_launch_descriptor\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   launch_descriptor);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_summary\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   summary);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_expected_schema_hash_hi\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   expected_schema_hash_hi);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_expected_schema_hash_lo\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   expected_schema_hash_lo);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_launch_descriptor_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   launch_descriptor_struct_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_summary_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   summary_struct_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_pointer_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   pointer_size);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_device_ordinal\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   device_ordinal);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_stream_domain\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   stream_domain);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_payload_bytes\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_offset_flags\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerKernelLaunchContextV1,
                   flags);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_launch_descriptor_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchDescriptorV1*);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_device_ordinal\":"
            << args.device;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_stream_domain\":0";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_packet_valid\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_row_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_error_count\":"
            << future_native_consumer_kernel_launch_context_error_count;
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_field_mask\":"
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_kernel_launch_context_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_kernel_launch_context_checked
                    ? future_native_consumer_kernel_launch_context_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_abi_name\":\""
            << kPremapFutureKernelNativeConsumerInvocationAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_mode\":\""
            << kPremapFutureKernelNativeConsumerInvocationAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_source\":\""
            << kPremapFutureKernelNativeConsumerInvocationAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_field_read_path\":\"invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_packet_chain_depth\":11";
  std::cout << ",\"future_kernel_native_consumer_invocation_checked\":"
            << (future_native_consumer_invocation_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_invocation_version\":"
            << kPremapFutureKernelNativeConsumerInvocationAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_invocation_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerInvocationV1);
  std::cout << ",\"future_kernel_native_consumer_invocation_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerInvocationV1);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_context\":"
            << offsetof(PremapFutureKernelNativeConsumerInvocationV1, context);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_summary\":"
            << offsetof(PremapFutureKernelNativeConsumerInvocationV1, summary);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_expected_schema_hash_hi\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   expected_schema_hash_hi);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_expected_schema_hash_lo\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   expected_schema_hash_lo);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_abi_version\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   abi_version);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_context_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   context_struct_size);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_summary_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   summary_struct_size);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_pointer_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   pointer_size);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_invocation_id\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   invocation_id);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_device_ordinal\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   device_ordinal);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_stream_domain\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   stream_domain);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_payload_bytes\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerInvocationV1,
                   payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_invocation_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerInvocationV1, flags);
  std::cout << ",\"future_kernel_native_consumer_invocation_context_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_invocation_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1*);
  std::cout << ",\"future_kernel_native_consumer_invocation_id\":1";
  std::cout << ",\"future_kernel_native_consumer_invocation_device_ordinal\":"
            << invocation_device_ordinal;
  std::cout << ",\"future_kernel_native_consumer_invocation_stream_domain\":"
            << invocation_stream_domain;
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_packet_valid\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_row_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_error_count\":"
            << future_native_consumer_invocation_error_count;
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_field_mask\":"
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_invocation_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_invocation_checked
                    ? future_native_consumer_invocation_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_abi_name\":\"premap_future_kernel_native_consumer_invocation_entry_abi_v1\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_mode\":\"readonly_future_kernel_native_consumer_invocation_entry_abi\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_source\":\"premap_future_kernel_native_consumer_invocation_abi_v1_by_value\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_field_read_path\":\"by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_packet_chain_depth\":11";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_checked\":"
            << (future_native_consumer_invocation_entry_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_packet_valid\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_row_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_error_count\":"
            << future_native_consumer_invocation_entry_error_count;
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_field_mask\":"
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_invocation_entry_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_invocation_entry_checked
                    ? future_native_consumer_invocation_entry_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_abi_name\":\""
            << kPremapFutureKernelNativeConsumerEndpointAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_mode\":\""
            << kPremapFutureKernelNativeConsumerEndpointAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_source\":\""
            << kPremapFutureKernelNativeConsumerEndpointAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_field_read_path\":\"endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_packet_chain_depth\":12";
  std::cout << ",\"future_kernel_native_consumer_endpoint_checked\":"
            << (future_native_consumer_endpoint_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_endpoint_version\":"
            << kPremapFutureKernelNativeConsumerEndpointAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_endpoint_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerEndpointV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerEndpointV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_invocation\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointV1, invocation);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_abi_version\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointV1, abi_version);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_invocation_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerEndpointV1,
                   invocation_struct_size);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_summary_struct_size\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerEndpointV1,
                   summary_struct_size);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_pointer_size\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointV1, pointer_size);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_endpoint_id\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointV1, endpoint_id);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_payload_bytes\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointV1, payload_bytes);
  std::cout << ",\"future_kernel_native_consumer_endpoint_offset_flags\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointV1, flags);
  std::cout << ",\"future_kernel_native_consumer_endpoint_invocation_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerInvocationV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelLaunchContextV1*);
  std::cout << ",\"future_kernel_native_consumer_endpoint_id\":1";
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_packet_valid\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_row_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_error_count\":"
            << future_native_consumer_endpoint_error_count;
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_field_mask\":"
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_endpoint_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_endpoint_checked
                    ? future_native_consumer_endpoint_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_abi_name\":\""
            << kPremapFutureKernelNativeConsumerEndpointPtrAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_mode\":\""
            << kPremapFutureKernelNativeConsumerEndpointPtrAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_source\":\""
            << kPremapFutureKernelNativeConsumerEndpointPtrAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_field_read_path\":\"endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_packet_chain_depth\":13";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_checked\":"
            << (future_native_consumer_endpoint_ptr_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_version\":"
            << kPremapFutureKernelNativeConsumerEndpointPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerEndpointPtrV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerEndpointPtrV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_offset_endpoint\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointPtrV1, endpoint);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_offset_summary\":"
            << offsetof(PremapFutureKernelNativeConsumerEndpointPtrV1, summary);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_endpoint_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerEndpointV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerEndpointV1*);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_id\":1";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_packet_valid\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_row_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_error_count\":"
            << future_native_consumer_endpoint_ptr_error_count;
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_field_mask\":"
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_payload_deref_allowed\":"
            << (kPremapFutureKernelNativeConsumerEndpointPtrAbiV1PayloadDerefAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_kernel_arg_pass_allowed\":"
            << (kPremapFutureKernelNativeConsumerEndpointPtrAbiV1KernelArgPassAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_current_wna16_arg_compatible\":"
            << (kPremapFutureKernelNativeConsumerEndpointPtrAbiV1CurrentWna16ArgCompatible
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_endpoint_ptr_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_endpoint_ptr_checked
                    ? future_native_consumer_endpoint_ptr_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_abi_name\":\""
            << kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_mode\":\""
            << kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_source\":\""
            << kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_field_read_path\":\"wna16_adjacent_typed_slot_to_endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_packet_chain_depth\":14";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_checked\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_version\":"
            << kPremapFutureKernelNativeConsumerWna16AdjacentTypedSlotAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_offset_endpoint_ptr\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1,
                   endpoint_ptr);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_offset_summary\":"
            << offsetof(
                   PremapFutureKernelNativeConsumerWna16AdjacentTypedSlotV1,
                   summary);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_endpoint_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerEndpointPtrV1);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerEndpointPtrV1*);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_id\":1";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_packet_valid\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_error_count\":"
            << future_native_consumer_wna16_adjacent_typed_slot_error_count;
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_field_mask\":"
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_payload_deref_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_kernel_arg_pass_allowed\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_current_wna16_arg_compatible\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_explicit_typed_abi_slot\":true";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot\":false";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_wna16_adjacent_typed_slot_checked
                    ? future_native_consumer_wna16_adjacent_typed_slot_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_abi_name\":\""
            << kPremapFutureKernelNativeConsumerRequestPtrAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_mode\":\""
            << kPremapFutureKernelNativeConsumerRequestPtrAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_source\":\""
            << kPremapFutureKernelNativeConsumerRequestPtrAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_field_read_path\":\"request_ptr_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_packet_chain_depth\":4";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_checked\":"
            << (future_native_consumer_request_ptr_checked ? "true" : "false");
  std::cout << ",\"future_kernel_native_consumer_request_ptr_version\":"
            << kPremapFutureKernelNativeConsumerRequestPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_request_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestPtrV1);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerRequestPtrV1);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_offset_kernel_arg_packet\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestPtrV1,
                        kernel_arg_packet);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_offset_summary\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestPtrV1, summary);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_kernel_arg_packet_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelArgPacketV1*);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_request_id\":1";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_packet_valid\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_row_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_error_count\":"
            << future_native_consumer_request_ptr_error_count;
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_field_mask\":"
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_ptr_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_payload_deref_allowed\":"
            << (kPremapFutureKernelNativeConsumerRequestPtrAbiV1PayloadDerefAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_ptr_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed\":"
            << (kPremapFutureKernelNativeConsumerRequestPtrAbiV1KernelArgPassAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_ptr_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible\":"
            << (kPremapFutureKernelNativeConsumerRequestPtrAbiV1CurrentWna16ArgCompatible
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_ptr_checked
                    ? future_native_consumer_request_ptr_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_abi_name\":\""
            << kPremapFutureKernelNativeConsumerRequestLaunchAbiV1Name << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_mode\":\""
            << kPremapFutureKernelNativeConsumerRequestLaunchAbiV1Mode << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_source\":\""
            << kPremapFutureKernelNativeConsumerRequestLaunchAbiV1Source << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_field_read_path\":\"request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_packet_chain_depth\":5";
  std::cout << ",\"future_kernel_native_consumer_request_launch_checked\":"
            << (future_native_consumer_request_launch_checked ? "true"
                                                              : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_version\":"
            << kPremapFutureKernelNativeConsumerRequestLaunchAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_request_launch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerRequestLaunchV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_offset_request_ptr\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestLaunchV1,
                        request_ptr);
  std::cout << ",\"future_kernel_native_consumer_request_launch_offset_summary\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestLaunchV1,
                        summary);
  std::cout << ",\"future_kernel_native_consumer_request_launch_offset_grid_x\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestLaunchV1,
                        grid_x);
  std::cout << ",\"future_kernel_native_consumer_request_launch_offset_row_offset\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestLaunchV1,
                        row_offset);
  std::cout << ",\"future_kernel_native_consumer_request_launch_request_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestPtrV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestPtrV1*);
  std::cout << ",\"future_kernel_native_consumer_request_launch_request_id\":1";
  std::cout << ",\"future_kernel_native_consumer_request_launch_device_ordinal\":"
            << args.device;
  std::cout << ",\"future_kernel_native_consumer_request_launch_stream_domain\":0";
  std::cout << ",\"future_kernel_native_consumer_request_launch_grid_x\":"
            << ((table.row_count + args.block_threads - 1) /
                args.block_threads);
  std::cout << ",\"future_kernel_native_consumer_request_launch_block_x\":"
            << args.block_threads;
  std::cout << ",\"future_kernel_native_consumer_request_launch_row_offset\":0";
  std::cout << ",\"future_kernel_native_consumer_request_launch_row_limit\":"
            << table.row_count;
  std::cout << ",\"future_kernel_native_consumer_request_launch_rows_per_program\":"
            << args.block_threads;
  std::cout << ",\"future_kernel_native_consumer_request_launch_row_count\":"
            << table.row_count;
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_packet_valid\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_row_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary.row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_error_count\":"
            << future_native_consumer_request_launch_error_count;
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_field_mask\":"
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_request_launch_payload_deref_allowed\":"
            << (kPremapFutureKernelNativeConsumerRequestLaunchAbiV1PayloadDerefAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed\":"
            << (kPremapFutureKernelNativeConsumerRequestLaunchAbiV1KernelArgPassAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_request_launch_current_wna16_arg_compatible\":"
            << (kPremapFutureKernelNativeConsumerRequestLaunchAbiV1CurrentWna16ArgCompatible
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_launch_checked
                    ? future_native_consumer_request_launch_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_abi_name\":\""
            << kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1Name
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_mode\":\""
            << kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1Mode
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_source\":\""
            << kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1Source
            << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_field_read_path\":\"request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_packet_chain_depth\":6";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_checked\":"
            << (future_native_consumer_request_launch_ptr_checked ? "true"
                                                                  : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_version\":"
            << kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1Version;
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestLaunchPtrV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_struct_align\":"
            << alignof(PremapFutureKernelNativeConsumerRequestLaunchPtrV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_offset_request_launch\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestLaunchPtrV1,
                        request_launch);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_offset_summary\":"
            << offsetof(PremapFutureKernelNativeConsumerRequestLaunchPtrV1,
                        summary);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_request_launch_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_struct_size\":"
            << sizeof(PremapFutureKernelNativeConsumerKernelEntrySummaryV1);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_pointer_size\":"
            << sizeof(PremapFutureKernelNativeConsumerRequestLaunchV1*);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_request_id\":1";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_packet_valid\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary.packet_valid
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_row_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary.row_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .row_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_descriptor_ptr_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .descriptor_ptr_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .packed_weight_descriptor_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .scale_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .aux_metadata_handle_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_expert_id_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .expert_id_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_address_key_hash_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .address_key_hash_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .row_metadata_read_ok_count
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_error_count\":"
            << future_native_consumer_request_launch_ptr_error_count;
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_field_mask\":"
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary.field_mask
                    : 0);
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_payload_bytes\":0";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_payload_deref_allowed\":"
            << (kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1PayloadDerefAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_passed_to_kernel\":false";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed\":"
            << (kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1KernelArgPassAllowed
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args\":false";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible\":"
            << (kPremapFutureKernelNativeConsumerRequestLaunchPtrAbiV1CurrentWna16ArgCompatible
                    ? "true"
                    : "false");
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation\":false";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_row_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .row_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_field_read_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .field_read_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator\":\""
            << std::hex
            << (future_native_consumer_request_launch_ptr_checked
                    ? future_native_consumer_request_launch_ptr_summary
                          .row_metadata_hash_accumulator
                    : 0ULL)
            << std::dec << "\"";
  std::cout << ",\"typed_schema_hash_hi\":\"" << std::hex << kTypedSchemaHashHi << std::dec << "\"";
  std::cout << ",\"typed_schema_hash_lo\":\"" << std::hex << kTypedSchemaHashLo << std::dec << "\"";
  std::cout << ",\"aux_pointer_present\":" << (args.omit_aux_pointer ? "false" : "true");
  std::cout << ",\"fault_invocation_device_ordinal\":"
            << (args.fault_invocation_device_ordinal ? "true" : "false");
  std::cout << ",\"fault_invocation_stream_domain\":"
            << (args.fault_invocation_stream_domain ? "true" : "false");
  std::cout << ",\"row_ok_count\":" << ok_count;
  std::cout << ",\"error_count\":" << error_count;
  std::cout << ",\"input_source\":\"" << (args.input_prefix.empty() ? "synthetic" : "binary_prefix") << "\"";
  std::cout << ",\"hash_accumulator\":\"" << std::hex << hash_acc << std::dec << "\"";
  std::cout << ",\"payload_bytes\":0";
  std::cout << ",\"passed_to_kernel\":false";
  std::cout << ",\"changes_kernel_launch_args\":false";
  std::cout << ",\"compiled_macros\":" << macro_json();
  std::cout << "}\n";
  return all_ok ? 0 : 1;
}
