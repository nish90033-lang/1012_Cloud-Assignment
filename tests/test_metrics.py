import report_metrics as rm

CARD = {"vcpu_hour": 3.5, "gib_memory_hour": 0.45}


def test_cost_formula_two_replicas():
    c = rm.cost_per_1000(CARD, replicas=2, cpu_limit=1, mem_limit_gib=1, rps=10)
    assert round(c["per_replica_hourly"], 2) == 3.95
    assert round(c["hourly_all_replicas"], 2) == 7.90
    assert c["requests_per_hour"] == 36000
    assert round(c["cost_per_1000"], 4) == round(7.90 / 36000 * 1000, 4)


def test_slo_error_budget():
    s = rm.slo(requests=1200, failures=3, target_pct=99.0)
    assert round(s["error_budget_requests"], 6) == 12 and round(s["budget_used_pct"], 2) == 25.0 and s["met"]
