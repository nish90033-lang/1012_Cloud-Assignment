"""Cold start (Task 4 step 7): delete all Pods, measure Pod creation -> Ready for each new Pod, three runs, report the median."""
import json
import statistics
import subprocess
import sys
from datetime import datetime

NS, SEL = "app", "app=cmdparser"


def sh(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def main(runs=3):
    times = []
    for i in range(1, runs + 1):
        sh("kubectl", "-n", NS, "delete", "pods", "-l", SEL, "--wait=true")
        sh("kubectl", "-n", NS, "wait", "--for=condition=Ready", "pod", "-l", SEL, "--timeout=600s")
        pods = json.loads(sh("kubectl", "-n", NS, "get", "pods", "-l", SEL, "-o", "json"))["items"]
        for p in pods:
            ready = next(c for c in p["status"]["conditions"] if c["type"] == "Ready")
            dt = (ts(ready["lastTransitionTime"]) - ts(p["metadata"]["creationTimestamp"])).total_seconds()
            times.append(dt)
            print(f"run {i}: {p['metadata']['name']} created->Ready {dt:.0f}s")
            print(sh("kubectl", "-n", NS, "logs", p["metadata"]["name"]).strip().splitlines()[:6])
    # Timestamps have 1 s resolution. With 2 replicas per run, 'three runs' gives six samples; the per-run median is reported too.
    print("all samples:", times, " median:", statistics.median(times))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
