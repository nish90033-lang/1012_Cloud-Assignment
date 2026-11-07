"""Turn Locust output into the Task 7 numbers: latency, throughput, error rate, cost per 1,000 requests, SLO error budget.

    python scripts/report_metrics.py --stats results/loadtest_stats.csv --replicas 2 --cpu-limit 1 --mem-limit-gib 1
"""
import argparse
import csv
import json


def read_aggregate(path):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["Name"] == "Aggregated":
                return {
                    "requests": int(row["Request Count"]),
                    "failures": int(row["Failure Count"]),
                    "p50_ms": float(row["50%"]),
                    "p95_ms": float(row["95%"]),
                    "rps": float(row["Requests/s"]),
                }
    raise SystemExit("no Aggregated row in " + path)


def cost_per_1000(rate_card, replicas, cpu_limit, mem_limit_gib, rps):
    per_replica = cpu_limit * rate_card["vcpu_hour"] + mem_limit_gib * rate_card["gib_memory_hour"]
    hourly = replicas * per_replica
    per_hour = rps * 3600
    return {"per_replica_hourly": per_replica, "hourly_all_replicas": hourly, "requests_per_hour": per_hour,
            "cost_per_1000": hourly / per_hour * 1000}


def slo(requests, failures, target_pct):
    budget = requests * (100 - target_pct) / 100
    return {"target_pct": target_pct, "error_budget_requests": budget, "failures": failures,
            "budget_used_pct": (failures / budget * 100) if budget else None,
            "met": 100 * (requests - failures) / requests >= target_pct}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default="results/loadtest_stats.csv")
    ap.add_argument("--rate-card", default="data/rate_card.json")
    ap.add_argument("--replicas", type=int, required=True)
    ap.add_argument("--cpu-limit", type=float, default=1.0)
    ap.add_argument("--mem-limit-gib", type=float, default=1.0)
    ap.add_argument("--slo-target", type=float, default=99.0)
    a = ap.parse_args()
    s = read_aggregate(a.stats)
    s["error_rate_pct"] = 100 * s["failures"] / s["requests"] if s["requests"] else None
    out = {"load": s,
           "cost": cost_per_1000(json.load(open(a.rate_card)), a.replicas, a.cpu_limit, a.mem_limit_gib, s["rps"]),
           "slo": slo(s["requests"], s["failures"], a.slo_target)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
