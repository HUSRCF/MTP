from __future__ import annotations

import torch

from mtp_expert_prefetch.training import (
    HiddenResidualExpertPredictor,
    MtpRouterOnlyPredictor,
    apply_token_frequency_table,
    apply_transition_matrix,
    build_previous_token_hidden_batch,
    build_token_frequency_table,
    fit_prior_tables,
    mass_coverage_at_m,
    recall_at_m,
    router_topk_to_dense_feature,
    target_expert_ids_to_dense_weights,
    target_expert_ids_to_multihot,
    top1_risk_at_m,
    train_transition_matrix,
)


def test_target_expert_ids_to_multihot_deduplicates_topk_experts():
    ids = torch.tensor([[[[1, 3, 3], [2, 4, 5]]]])

    labels = target_expert_ids_to_multihot(ids, num_experts=8)

    assert labels.shape == (1, 1, 2, 8)
    assert torch.equal(labels[0, 0, 0], torch.tensor([0, 1, 0, 1, 0, 0, 0, 0.0]))
    assert torch.equal(labels[0, 0, 1], torch.tensor([0, 0, 1, 0, 1, 1, 0, 0.0]))


def test_router_topk_to_dense_feature_scatter_adds_weights():
    ids = torch.tensor([[1, 3, 3]])
    weights = torch.tensor([[0.25, 0.5, 0.25]])

    features = router_topk_to_dense_feature(ids, weights, num_experts=5)

    assert torch.allclose(features, torch.tensor([[0.0, 0.25, 0.0, 0.75, 0.0]]))


def test_target_expert_ids_to_dense_weights_scatter_adds_gate_mass():
    ids = torch.tensor([[[[1, 3, 3], [2, 4, 5]]]])
    weights = torch.tensor([[[[0.2, 0.5, 0.3], [0.1, 0.6, 0.3]]]])

    dense = target_expert_ids_to_dense_weights(ids, weights, num_experts=8)

    assert dense.shape == (1, 1, 2, 8)
    assert torch.allclose(dense[0, 0, 0], torch.tensor([0.0, 0.2, 0.0, 0.8, 0, 0, 0, 0]))
    assert torch.allclose(dense[0, 0, 1], torch.tensor([0.0, 0.0, 0.1, 0, 0.6, 0.3, 0, 0]))


def test_recall_at_m_counts_true_expert_hits():
    labels = target_expert_ids_to_multihot(torch.tensor([[[[1, 2, 3]]]]), num_experts=6)
    logits = torch.tensor([[[[0.0, 5.0, 4.0, -1.0, 3.0, 2.0]]]])

    recall = recall_at_m(logits, labels, m=2)

    assert recall.numerator == 2.0
    assert recall.denominator == 3.0
    assert abs(recall.recall - (2.0 / 3.0)) < 1e-6


def test_mass_coverage_at_m_weights_true_expert_hits_by_gate_mass():
    target_mass = target_expert_ids_to_dense_weights(
        torch.tensor([[[[1, 2, 3]]]]),
        torch.tensor([[[[0.7, 0.2, 0.1]]]]),
        num_experts=6,
    )
    logits = torch.tensor([[[[0.0, 5.0, -1.0, 4.0, 3.0, 2.0]]]])

    coverage = mass_coverage_at_m(logits, target_mass, m=2)

    assert abs(coverage.numerator - 0.8) < 1e-6
    assert abs(coverage.coverage - 0.8) < 1e-6


def test_top1_risk_at_m_reports_hit_and_weighted_miss():
    target_mass = target_expert_ids_to_dense_weights(
        torch.tensor([[[[1, 2, 3], [4, 5, 0]]]]),
        torch.tensor([[[[0.7, 0.2, 0.1], [0.6, 0.3, 0.1]]]]),
        num_experts=6,
    )
    logits = torch.tensor(
        [[[[0.0, 5.0, 4.0, 3.0, 2.0, 1.0], [5.0, 4.0, 3.0, 2.0, 1.0, 0.0]]]]
    )

    risk = top1_risk_at_m(logits, target_mass, m=1)

    assert risk.hit_count == 1.0
    assert risk.total_count == 2.0
    assert abs(risk.top1_hit_rate - 0.5) < 1e-6
    assert abs(risk.weighted_miss_numerator - 0.6) < 1e-6
    assert abs(risk.weighted_top1_miss - 0.3) < 1e-6


def test_transition_baseline_learns_same_layer_expert_transitions():
    current = torch.tensor(
        [
            [[1.0, 0.0, 0.0]],
            [[0.0, 1.0, 0.0]],
            [[1.0, 0.0, 0.0]],
        ]
    )
    target = torch.zeros(3, 1, 1, 3)
    target[0, 0, 0, 2] = 1.0
    target[1, 0, 0, 0] = 1.0
    target[2, 0, 0, 2] = 1.0

    transition = train_transition_matrix(current, target)
    scores = apply_transition_matrix(current, transition)

    assert transition.shape == (1, 1, 3, 3)
    assert torch.argmax(scores[0, 0, 0]).item() == 2
    assert torch.argmax(scores[1, 0, 0]).item() == 0


def test_token_frequency_baseline_uses_fallback_for_unseen_tokens():
    target = torch.zeros(3, 1, 1, 4)
    target[0, 0, 0, 1] = 1.0
    target[1, 0, 0, 2] = 1.0
    target[2, 0, 0, 2] = 1.0
    token_ids = torch.tensor([10, 11, 11])

    table = build_token_frequency_table(token_ids, target)
    scores = apply_token_frequency_table(table, torch.tensor([11, 99]))

    assert torch.argmax(scores[0, 0, 0]).item() == 2
    assert torch.allclose(scores[1], table.fallback[0])


def test_mtp_router_only_predictor_shape():
    model = MtpRouterOnlyPredictor(num_experts=8, num_layers=3, future_window=2, width=16)
    features = torch.randn(5, 8)
    layer_ids = torch.tensor([0, 1, 2])

    logits = model(features, target_layer_ids=layer_ids)

    assert logits.shape == (5, 2, 3, 8)


def test_build_previous_token_hidden_batch_uses_prior_and_flattens_layer_examples():
    module0 = "model.language_model.layers.0.mlp.gate"
    module1 = "model.language_model.layers.1.mlp.gate"
    payload = {
        "router_topk": {
            module0: [torch.tensor([[0, 1], [1, 2], [2, 3], [3, 4]])],
            module1: [torch.tensor([[4, 5], [5, 6], [6, 7], [7, 0]])],
        },
        "router_weights": {
            module0: [torch.full((4, 2), 0.5)],
            module1: [torch.full((4, 2), 0.5)],
        },
        "router_input_hidden": {
            module0: [torch.randn(4, 6)],
            module1: [torch.randn(4, 6)],
        },
    }
    frequency, transition = fit_prior_tables([payload], future_window=1, num_experts=8)

    batch = build_previous_token_hidden_batch(
        payload,
        frequency_scores=frequency,
        transition_matrix=transition,
        future_window=1,
        num_experts=8,
    )

    assert batch.hidden.shape == (6, 6)
    assert batch.labels.shape == (6, 1, 8)
    assert batch.prior_logits.shape == (6, 1, 8)
    assert torch.equal(batch.layer_ids, torch.tensor([0, 1, 0, 1, 0, 1]))


def test_hidden_residual_expert_predictor_shape():
    model = HiddenResidualExpertPredictor(
        hidden_size=6,
        num_experts=8,
        num_layers=2,
        future_window=3,
        width=12,
    )
    hidden = torch.randn(5, 6)
    layer_ids = torch.tensor([0, 1, 0, 1, 0])

    logits = model(hidden, layer_ids=layer_ids)

    assert logits.shape == (5, 3, 8)


def test_hidden_residual_expert_predictor_zero_init_starts_from_zero_residual():
    model = HiddenResidualExpertPredictor(
        hidden_size=6,
        num_experts=8,
        num_layers=2,
        future_window=3,
        width=12,
        zero_init_output=True,
    )
    hidden = torch.randn(5, 6)
    layer_ids = torch.tensor([0, 1, 0, 1, 0])

    logits = model(hidden, layer_ids=layer_ids)

    assert torch.count_nonzero(logits) == 0
