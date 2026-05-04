#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))

from mtp_expert_prefetch.utils.config import (  # noqa: E402
    find_project_root,
    load_yaml,
    resolve_path,
)

DEFAULT_CONFIG = Path("configs/train/hidden_residual_predictor_64sample_sweep.yaml")


def _as_list(value: Any, *, default: list[Any]) -> list[Any]:
    if value is None:
        return default
    if isinstance(value, list):
        return value
    return [value]


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _metric(metrics: dict[str, Any], split: str, key: str, m: int) -> float:
    return float(metrics[split][key][str(m)])


def _run_summary(metrics_path: Path, *, budgets: list[int]) -> dict[str, Any]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    val = metrics["val"]
    per_layer = val.get("per_layer_delta_vs_transition", {})
    layer_summary = {}
    for budget in budgets:
        key = str(budget)
        layer_deltas = [
            float(item["delta_mass_coverage_at"][key])
            for item in per_layer.values()
            if "delta_mass_coverage_at" in item
        ]
        positive_layers = [index for index, value in enumerate(layer_deltas) if value > 0.0]
        best_layer = None
        worst_layer = None
        if layer_deltas:
            best_idx = max(range(len(layer_deltas)), key=lambda index: layer_deltas[index])
            worst_idx = min(range(len(layer_deltas)), key=lambda index: layer_deltas[index])
            best_layer = {"layer": best_idx, "delta_mass": layer_deltas[best_idx]}
            worst_layer = {"layer": worst_idx, "delta_mass": layer_deltas[worst_idx]}
        layer_summary[key] = {
            "positive_layer_count": len(positive_layers),
            "positive_layers": positive_layers,
            "best_layer": best_layer,
            "worst_layer": worst_layer,
        }

    return {
        "metrics_path": str(metrics_path),
        "ok": bool(metrics.get("ok", False)),
        "seed": metrics.get("seed"),
        "trained_steps": metrics.get("trained_steps"),
        "best_step": metrics.get("best_step"),
        "best_val_loss": metrics.get("best_val_loss"),
        "stopped_early": metrics.get("stopped_early"),
        "delta_mass": val.get("mass_coverage_delta_vs_transition", {}),
        "delta_top1": val.get("top1_hit_delta_vs_transition", {}),
        "delta_weighted_top1_miss": val.get("weighted_top1_miss_delta_vs_transition", {}),
        "model_mass": {
            str(m): float(val["model"]["mass_coverage_at"][str(m)]["coverage"])
            for m in budgets
        },
        "transition_mass": {
            str(m): float(
                val["baselines"]["transition_prior"]["mass_coverage_at"][str(m)]["coverage"]
            )
            for m in budgets
        },
        "model_top1": {
            str(m): float(val["model"]["top1_risk_at"][str(m)]["top1_hit_rate"])
            for m in budgets
        },
        "transition_top1": {
            str(m): float(
                val["baselines"]["transition_prior"]["top1_risk_at"][str(m)]["top1_hit_rate"]
            )
            for m in budgets
        },
        "logit_diagnostics": val.get("logit_diagnostics", {}),
        "per_layer_summary": layer_summary,
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _aggregate_runs(runs: list[dict[str, Any]], *, budgets: list[int]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        grouped.setdefault(str(run["variant"]), []).append(run)
    aggregate = {}
    for variant, variant_runs in grouped.items():
        item: dict[str, Any] = {"num_runs": len(variant_runs)}
        for budget in budgets:
            key = str(budget)
            item[f"mean_delta_mass_at_{budget}"] = _mean(
                [float(run["summary"]["delta_mass"][key]) for run in variant_runs]
            )
            item[f"mean_delta_top1_at_{budget}"] = _mean(
                [float(run["summary"]["delta_top1"][key]) for run in variant_runs]
            )
            item[f"mean_delta_weighted_top1_miss_at_{budget}"] = _mean(
                [float(run["summary"]["delta_weighted_top1_miss"][key]) for run in variant_runs]
            )
            item[f"mean_positive_layer_count_at_{budget}"] = _mean(
                [
                    float(
                        run["summary"]["per_layer_summary"][key]["positive_layer_count"]
                    )
                    for run in variant_runs
                ]
            )
        aggregate[variant] = item
    return aggregate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep hidden residual predictor settings.")
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    sweep_config = load_yaml(resolve_path(args.config, base_dir=project_root))
    base_config_path = resolve_path(sweep_config["base_config"], base_dir=project_root)
    base_config = load_yaml(base_config_path)
    output_dir = resolve_path(sweep_config["output_dir"], base_dir=project_root)
    configs_dir = output_dir / "configs"
    logs_dir = output_dir / "logs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    sweep = sweep_config.get("sweep", {})
    seeds = [int(seed) for seed in _as_list(sweep.get("seeds"), default=[0])]
    residual_scales = [float(scale) for scale in _as_list(sweep.get("residual_scales"), default=[])]
    gamma_initials = [
        float(value) for value in _as_list(sweep.get("learnable_gamma_initials"), default=[])
    ]
    gamma_scopes = [
        str(value)
        for value in _as_list(sweep.get("learnable_gamma_scopes"), default=["scalar"])
    ]
    budgets = [int(value) for value in _as_list(sweep.get("budgets"), default=[8, 16, 32])]
    overrides = sweep.get("overrides", {})

    run_specs = []
    for seed in seeds:
        for scale in residual_scales:
            run_specs.append(
                {
                    "variant": f"scale_{scale:g}",
                    "seed": seed,
                    "model": {
                        "residual_scale": scale,
                        "learnable_residual_gamma": False,
                    },
                }
            )
        for scope in gamma_scopes:
            for initial in gamma_initials:
                run_specs.append(
                    {
                        "variant": f"gamma_{scope}_{initial:g}",
                        "seed": seed,
                        "model": {
                            "residual_scale": initial,
                            "learnable_residual_gamma": True,
                            "initial_residual_gamma": initial,
                            "residual_gamma_scope": scope,
                        },
                    }
                )

    runs = []
    train_script = project_root / "scripts" / "train_hidden_residual_predictor_smoke.py"
    for run_index, spec in enumerate(run_specs):
        run_name = f"{run_index:03d}_{spec['variant']}_seed_{spec['seed']}"
        run_output_dir = output_dir / "runs" / run_name
        config = _deep_update(base_config, overrides)
        config["output_dir"] = str(run_output_dir.relative_to(project_root))
        config.setdefault("model", {}).update(spec["model"])
        config.setdefault("training", {})["seed"] = int(spec["seed"])
        config_path = configs_dir / f"{run_name}.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        log_path = logs_dir / f"{run_name}.log"
        metrics_path = run_output_dir / "metrics.json"
        skipped = metrics_path.exists()
        if not skipped:
            completed = subprocess.run(
                [sys.executable, str(train_script), str(config_path)],
                cwd=project_root,
                text=True,
                capture_output=True,
                check=False,
            )
            log_path.write_text(
                completed.stdout + "\n\n[stderr]\n" + completed.stderr,
                encoding="utf-8",
            )
            if completed.returncode != 0:
                msg = f"Run {run_name} failed with code {completed.returncode}; see {log_path}"
                raise RuntimeError(msg)
        summary = _run_summary(metrics_path, budgets=budgets)
        runs.append(
            {
                "name": run_name,
                "variant": spec["variant"],
                "seed": spec["seed"],
                "skipped_existing": skipped,
                "config_path": str(config_path),
                "log_path": str(log_path),
                "summary": summary,
            }
        )

    summary = {
        "ok": True,
        "base_config": str(base_config_path),
        "output_dir": str(output_dir),
        "num_runs": len(runs),
        "budgets": budgets,
        "runs": runs,
        "aggregate_by_variant": _aggregate_runs(runs, budgets=budgets),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
