from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import torch


ThresholdType = Literal["manual_absolute", "calibrated_absolute", "percentile"]
AdmissionGoal = Literal["stall_reduction", "bandwidth_efficiency"]
AdmissionAction = Literal["skip", "premap", "metadata", "full_fetch"]
AdmissionReason = Literal[
    "admitted_score_gate",
    "skipped_not_novel",
    "skipped_rank_cap",
    "skipped_below_threshold",
    "skipped_invalid_score",
    "skipped_policy",
]


@dataclass(frozen=True)
class ScoreThresholdMetadata:
    threshold: float
    threshold_type: ThresholdType
    optimization_goal: AdmissionGoal
    target_budget: str
    metric: str
    calibration_split: str | None = None
    heldout_split: str | None = None
    notes: str | None = None
    schema_version: str = "score_threshold_metadata.v1"
    model_id: str | None = None
    trace_id: str | None = None
    sidecar_model_id: str | None = None
    router_trace_model_id: str | None = None
    prefc_fixed: bool | None = None
    num_samples: int | None = None
    num_tokens: int | None = None
    num_token_layer_examples: int | None = None
    num_layers: int | None = None
    num_experts: int | None = None
    top_m_tokens: int | None = None
    base_policy: str | None = None
    max_extra: int | None = None
    score_source: str | None = None
    calibration_report_path: str | None = None
    heldout_report_path: str | None = None
    created_at: str | None = None
    git_commit: str | None = None
    experiment_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AdmissionDecisionMasks:
    """Vectorized admission decisions for runtime shadow counters.

    All tensors have the same shape as the expert score tensor. The masks are
    disjoint over MTP top-k candidates, except that candidates outside MTP top-k
    are intentionally not represented by any reason mask.
    """

    admitted_full_fetch: torch.Tensor
    skipped_not_novel: torch.Tensor
    skipped_rank_cap: torch.Tensor
    skipped_below_threshold: torch.Tensor
    skipped_invalid_score: torch.Tensor
    skipped_policy: torch.Tensor

    @property
    def admitted_score_gate(self) -> torch.Tensor:
        return self.admitted_full_fetch

    def final_prefetch_mask(self, base_mask: torch.Tensor) -> torch.Tensor:
        return base_mask | self.admitted_full_fetch

    def reason_masks(self) -> dict[AdmissionReason, torch.Tensor]:
        return {
            "admitted_score_gate": self.admitted_full_fetch,
            "skipped_not_novel": self.skipped_not_novel,
            "skipped_rank_cap": self.skipped_rank_cap,
            "skipped_below_threshold": self.skipped_below_threshold,
            "skipped_invalid_score": self.skipped_invalid_score,
            "skipped_policy": self.skipped_policy,
        }


def select_topk_mask(scores: torch.Tensor, *, k: int) -> torch.Tensor:
    """Return a boolean mask for top-k scores along the expert dimension."""
    k = min(max(0, int(k)), int(scores.shape[-1]))
    mask = torch.zeros_like(scores, dtype=torch.bool)
    if k == 0:
        return mask
    topk = torch.topk(scores.float(), k=k, dim=-1).indices
    mask.scatter_(-1, topk, True)
    return mask


def novel_mtp_extra_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
) -> torch.Tensor:
    """Select up to `max_extra` MTP candidates outside a protected base pool."""
    max_extra = max(0, int(max_extra))
    if max_extra == 0:
        return torch.zeros_like(base_mask)
    mtp_topk = min(max(0, int(mtp_topk)), int(mtp_scores.shape[-1]))
    if mtp_topk == 0:
        return torch.zeros_like(base_mask)
    finite_scores = _finite_scores(mtp_scores)
    ranked = torch.topk(finite_scores, k=mtp_topk, dim=-1).indices
    novel = ~base_mask.gather(-1, ranked)
    selected_rank = novel & (novel.to(torch.int16).cumsum(dim=-1) <= max_extra)
    selected = torch.zeros_like(base_mask)
    selected.scatter_(-1, ranked, selected_rank)
    return selected & ~base_mask


def novel_mtp_extra_rank_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    rank: int,
) -> torch.Tensor:
    """Return exactly the one-based `rank`-th novel MTP candidate."""
    rank = int(rank)
    if rank <= 0:
        msg = f"rank must be one-based and positive, got {rank}."
        raise ValueError(msg)
    mtp_topk = min(max(0, int(mtp_topk)), int(mtp_scores.shape[-1]))
    output = torch.zeros_like(base_mask)
    if mtp_topk == 0:
        return output
    finite_scores = _finite_scores(mtp_scores)
    ranked = torch.topk(finite_scores, k=mtp_topk, dim=-1).indices
    novel = ~base_mask.gather(-1, ranked)
    selected_rank = novel & novel.to(torch.int16).cumsum(dim=-1).eq(rank)
    output.scatter_(-1, ranked, selected_rank)
    return output & ~base_mask


def score_threshold_mtp_extra_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
    score_threshold: float,
) -> torch.Tensor:
    """Keep novel MTP extras whose utility score passes a global threshold."""
    extra = novel_mtp_extra_mask(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    finite_scores = _finite_scores(mtp_scores)
    return extra & torch.isfinite(mtp_scores.float()) & finite_scores.ge(float(score_threshold))


def build_mtp_extra_utility_scores(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    rank_alpha: float = 1.0,
    layer_factors: torch.Tensor | None = None,
    ready_factors: torch.Tensor | None = None,
) -> torch.Tensor:
    """Build utility scores for novel MTP-extra admission.

    The score is `mtp_score * rank_decay * layer_factor * ready_factor` over
    the MTP top-k candidate universe. Non-MTP candidates receive `-inf`.
    Transition-base candidates are retained in the ranking universe so shadow
    counters can still report `skipped_not_novel`.
    """
    if base_mask.shape != mtp_scores.shape:
        msg = (
            "base_mask and mtp_scores must have the same shape, got "
            f"{tuple(base_mask.shape)} and {tuple(mtp_scores.shape)}."
        )
        raise ValueError(msg)
    mtp_topk = min(max(0, int(mtp_topk)), int(mtp_scores.shape[-1]))
    utility = torch.full_like(mtp_scores.float(), -float("inf"))
    if mtp_topk == 0:
        return utility

    finite_scores = _finite_scores(mtp_scores)
    ranked = torch.topk(finite_scores, k=mtp_topk, dim=-1).indices
    ranked_base = base_mask.gather(-1, ranked)
    ranked_novel = ~ranked_base
    ranked_novel_rank = ranked_novel.to(torch.int16).cumsum(dim=-1).to(torch.float32)
    alpha = max(0.0, float(rank_alpha))
    rank_factor = torch.where(
        ranked_novel,
        ranked_novel_rank.clamp_min(1.0).pow(-alpha),
        torch.ones_like(ranked_novel_rank),
    )
    layer_factor = _prepare_layer_factor(
        layer_factors,
        reference=mtp_scores,
    )
    ready_factor = _prepare_layer_factor(
        ready_factors,
        reference=mtp_scores,
    )
    ranked_scores = finite_scores.gather(-1, ranked).clamp_min(0.0)
    ranked_layer_factor = layer_factor.expand_as(mtp_scores).gather(-1, ranked)
    ranked_ready_factor = ready_factor.expand_as(mtp_scores).gather(-1, ranked)
    ranked_utility = ranked_scores * rank_factor * ranked_layer_factor * ranked_ready_factor
    utility.scatter_(-1, ranked, ranked_utility)
    return utility


def tail_swap_mtp_extra_mask(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    swap_count: int,
) -> torch.Tensor:
    """Replace the weakest transition-tail slots with novel MTP extras.

    This is a fixed-budget pressure policy: it protects the transition head
    (`transition_topk - swap_count`) and fills the freed tail slots with MTP
    candidates that are novel relative to the full protected transition top-k.
    """
    if transition_scores.shape != mtp_scores.shape:
        msg = (
            "transition_scores and mtp_scores must have the same shape, got "
            f"{tuple(transition_scores.shape)} and {tuple(mtp_scores.shape)}."
        )
        raise ValueError(msg)
    transition_topk = max(0, int(transition_topk))
    swap_count = min(max(0, int(swap_count)), transition_topk)
    if transition_topk == 0:
        return torch.zeros_like(transition_scores, dtype=torch.bool)
    protected_head_k = max(0, transition_topk - swap_count)
    protected_head = select_topk_mask(transition_scores, k=protected_head_k)
    if swap_count == 0:
        return protected_head
    full_transition = select_topk_mask(transition_scores, k=transition_topk)
    extra = novel_mtp_extra_mask(
        full_transition,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=swap_count,
    )
    return protected_head | extra


def score_threshold_mtp_extra_decision_masks(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
    score_threshold: float,
    policy_allowed_mask: torch.Tensor | None = None,
) -> AdmissionDecisionMasks:
    """Return score-gated MTP-extra admission masks with skip reasons.

    The hierarchy is:
    1. candidates already in `base_mask` are `skipped_not_novel`;
    2. novel candidates with invalid scores are `skipped_invalid_score`;
    3. valid novel candidates past `max_extra` are `skipped_rank_cap`;
    4. valid in-cap candidates below threshold are `skipped_below_threshold`;
    5. score-passing candidates blocked by runtime pressure are `skipped_policy`;
    6. remaining score-passing candidates are `admitted_full_fetch`.
    """
    if base_mask.shape != mtp_scores.shape:
        msg = (
            "base_mask and mtp_scores must have the same shape, got "
            f"{tuple(base_mask.shape)} and {tuple(mtp_scores.shape)}."
        )
        raise ValueError(msg)
    if policy_allowed_mask is not None and policy_allowed_mask.shape != base_mask.shape:
        msg = (
            "policy_allowed_mask must have the same shape as base_mask, got "
            f"{tuple(policy_allowed_mask.shape)} and {tuple(base_mask.shape)}."
        )
        raise ValueError(msg)

    max_extra = max(0, int(max_extra))
    mtp_topk = min(max(0, int(mtp_topk)), int(mtp_scores.shape[-1]))
    empty = torch.zeros_like(base_mask, dtype=torch.bool)
    if mtp_topk == 0:
        return AdmissionDecisionMasks(
            admitted_full_fetch=empty,
            skipped_not_novel=empty,
            skipped_rank_cap=empty,
            skipped_below_threshold=empty,
            skipped_invalid_score=empty,
            skipped_policy=empty,
        )

    finite = torch.isfinite(mtp_scores.float())
    finite_scores = _finite_scores(mtp_scores)
    ranked = torch.topk(finite_scores, k=mtp_topk, dim=-1).indices

    topk_mask = torch.zeros_like(base_mask, dtype=torch.bool)
    topk_mask.scatter_(-1, ranked, True)
    ranked_base = base_mask.gather(-1, ranked)
    ranked_finite = finite.gather(-1, ranked)
    ranked_novel = ~ranked_base
    ranked_novel_order = ranked_novel.to(torch.int16).cumsum(dim=-1)
    ranked_in_cap = ranked_novel & ranked_novel_order.le(max_extra)
    ranked_over_cap = ranked_novel & ranked_novel_order.gt(max_extra)

    skipped_not_novel = topk_mask & base_mask
    skipped_invalid_score = topk_mask & ~base_mask & ~finite

    skipped_rank_cap = torch.zeros_like(base_mask, dtype=torch.bool)
    skipped_rank_cap.scatter_(-1, ranked, ranked_over_cap & ranked_finite)

    in_cap = torch.zeros_like(base_mask, dtype=torch.bool)
    in_cap.scatter_(-1, ranked, ranked_in_cap & ranked_finite)

    score_pass = in_cap & finite_scores.ge(float(score_threshold))
    skipped_below_threshold = in_cap & ~score_pass

    if policy_allowed_mask is None:
        policy_allowed = torch.ones_like(base_mask, dtype=torch.bool)
    else:
        policy_allowed = policy_allowed_mask.to(dtype=torch.bool)
    skipped_policy = score_pass & ~policy_allowed
    admitted = score_pass & policy_allowed

    return AdmissionDecisionMasks(
        admitted_full_fetch=admitted,
        skipped_not_novel=skipped_not_novel,
        skipped_rank_cap=skipped_rank_cap,
        skipped_below_threshold=skipped_below_threshold,
        skipped_invalid_score=skipped_invalid_score,
        skipped_policy=skipped_policy,
    )


def _finite_scores(scores: torch.Tensor) -> torch.Tensor:
    finite = torch.isfinite(scores.float())
    return scores.float().masked_fill(~finite, -float("inf"))


def _prepare_layer_factor(
    factors: torch.Tensor | None,
    *,
    reference: torch.Tensor,
) -> torch.Tensor:
    if factors is None:
        return torch.ones(
            (1, 1, int(reference.shape[2]), 1),
            device=reference.device,
            dtype=torch.float32,
        )
    factors = factors.to(device=reference.device, dtype=torch.float32)
    if factors.ndim != 1 or int(factors.shape[0]) != int(reference.shape[2]):
        msg = (
            "layer/ready factors must be one-dimensional with length equal to "
            f"the layer dimension {int(reference.shape[2])}, got {tuple(factors.shape)}."
        )
        raise ValueError(msg)
    return factors.view(1, 1, -1, 1)
