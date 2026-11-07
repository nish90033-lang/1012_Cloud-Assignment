import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
for sub in ("service", "worker", "scripts", "tools"):
    sys.path.insert(0, os.path.join(ROOT, sub))
os.environ.setdefault("SKIP_MODEL_LOAD", "1")
