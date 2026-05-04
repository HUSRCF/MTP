"""Training loops for future expert prediction."""
from mtp_expert_prefetch.training.alignment_merge import (
    MergeResult,
    merge_mtp_source_with_router_targets,
    merge_trace_manifests,
)
from mtp_expert_prefetch.training.baselines import (
    TokenFrequencyTable,
    apply_token_frequency_table,
    apply_transition_matrix,
    build_token_frequency_table,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.training.hidden_residual import (
    HiddenResidualExpertPredictor,
    PreviousTokenHiddenBatch,
    build_previous_token_hidden_batch,
    fit_prior_tables,
    stack_router_input_hidden,
)
from mtp_expert_prefetch.training.mtp_alignment import (
    MtpRouterAlignmentBatch,
    build_mtp_router_alignment,
    stack_backbone_router_topk,
    stack_backbone_router_scores,
    stack_backbone_router_weights,
)
from mtp_expert_prefetch.training.predictor import (
    MassCoverageAtM,
    MtpRouterOnlyPredictor,
    RecallAtM,
    Top1RiskAtM,
    mass_coverage_at_m,
    recall_at_m,
    router_topk_to_dense_feature,
    target_expert_ids_to_dense_weights,
    target_expert_ids_to_multihot,
    top1_risk_at_m,
)

__all__ = [
    "MergeResult",
    "MassCoverageAtM",
    "MtpRouterAlignmentBatch",
    "MtpRouterOnlyPredictor",
    "HiddenResidualExpertPredictor",
    "PreviousTokenHiddenBatch",
    "RecallAtM",
    "TokenFrequencyTable",
    "Top1RiskAtM",
    "apply_token_frequency_table",
    "apply_transition_matrix",
    "build_previous_token_hidden_batch",
    "build_mtp_router_alignment",
    "build_token_frequency_table",
    "fit_prior_tables",
    "merge_mtp_source_with_router_targets",
    "merge_trace_manifests",
    "mass_coverage_at_m",
    "recall_at_m",
    "router_topk_to_dense_feature",
    "stack_router_input_hidden",
    "stack_backbone_router_weights",
    "stack_backbone_router_scores",
    "stack_backbone_router_topk",
    "target_expert_ids_to_dense_weights",
    "target_expert_ids_to_multihot",
    "top1_risk_at_m",
    "train_frequency_scores",
    "train_transition_matrix",
]
