# Compute Funnel Eval

Zero-dependency deterministic planning, quota-accounting, and placement verifier for running open-weight language models on intermittent, batch, and memory-constrained compute.

## Research & Benchmark Context

In baseline evaluations of an official 80B `Q4_K_M` checkpoint across constrained multi-GPU and host RAM allocations, unaided model planning frequently drifted on integer arithmetic, startup-time multipliers, and memory-window constraints—causing silent specification failures even when weights loaded cleanly. `calculator.py` separates probabilistic model generation from deterministic resource math (verified across 12,012 synthetic boundary cases) using strict integer/boolean validation and duplicate-key JSON guards. This standalone evaluation package provides the core verification primitives and synthetic fixtures used to benchmark open-weight batch and constrained-GPU workflows.

## Operations

* `quota`: Validates account eligibility (`verified`, `good_standing`, `age_days > 30`), computes per-request quota cost (`duration_seconds * multiplier`), and reports `maximum_full_requests` plus `remaining_quota_seconds`.
* `batch`: Accounts for startup overhead (`startup_seconds * multiplier`) before dividing remaining quota across per-case costs (`case_seconds * multiplier`), failing fast if startup exceeds budget.
* `placement`: Evaluates structured compute offers against required per-GPU memory (`required_gib`), total job duration (`load_minutes + task_minutes`), programmability, and runtime support, returning eligible offers and remaining window slack.

## Quickstart

Requires Python 3.10+ (standard library only; zero external dependencies).

```bash
python calculator.py quota examples/quota_check.json
python calculator.py batch examples/batch_check.json
python calculator.py placement examples/placement_check.json
```

Run the test suite:

```bash
python -m unittest -v
```

## License

Released under the [MIT License](LICENSE).
