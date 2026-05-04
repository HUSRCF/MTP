"""Prediction metrics and cache simulation."""
from mtp_expert_prefetch.evaluation.prefill_working_set import (
    PrefillWorkingSetReport,
    analyze_prefill_working_set,
    write_prefill_working_set_report,
)
from mtp_expert_prefetch.evaluation.prefetch_shadow import (
    PrefetchShadowReport,
    simulate_prefetch_shadow,
    write_prefetch_shadow_report,
)
from mtp_expert_prefetch.evaluation.router_hidden_oracle import (
    RouterHiddenOracleReport,
    analyze_router_hidden_oracle,
    write_router_hidden_oracle_report,
)
from mtp_expert_prefetch.evaluation.router_trace_sanity import (
    RouterTraceSanityReport,
    analyze_router_trace_sanity,
    write_router_trace_sanity_report,
)

__all__ = [
    "PrefillWorkingSetReport",
    "PrefetchShadowReport",
    "RouterHiddenOracleReport",
    "RouterTraceSanityReport",
    "analyze_router_hidden_oracle",
    "analyze_router_trace_sanity",
    "analyze_prefill_working_set",
    "simulate_prefetch_shadow",
    "write_router_hidden_oracle_report",
    "write_router_trace_sanity_report",
    "write_prefill_working_set_report",
    "write_prefetch_shadow_report",
]
