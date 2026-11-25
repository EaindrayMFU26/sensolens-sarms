"""tools/product_batch.py's per-repository timeout stops the run, not just its launcher.

The batch starts `uv run sarms auto ...`; uv starts sarms as a child. subprocess.run(timeout=...) killed only uv,
sarms kept running with the output pipes open, and on Windows the timeout was raised only when sarms finished:
sqlfluff passed its one-hour limit and ran on until it was done.
"""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("product_batch", ROOT / "tools" / "product_batch.py")
product_batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(product_batch)

# a launcher like `uv run`: it starts a child that inherits stdout/stderr and waits for it
LAUNCHER = [sys.executable, "-c", "import subprocess, sys; subprocess.run([sys.executable, '-c', 'import time; time.sleep(60)'])"]


def test_the_timeout_stops_the_launched_child_too():
    t0 = time.time()
    with pytest.raises(subprocess.TimeoutExpired):
        product_batch.run_bounded(LAUNCHER, timeout=2)
    assert time.time() - t0 < 30          # the old way waited the child's full 60 s


def test_a_run_inside_the_limit_returns_its_output():
    p = product_batch.run_bounded([sys.executable, "-c", "print('caf\\u00e9 \\u2192 ok')"], timeout=30)
    assert p.returncode == 0 and p.stdout.strip() == "café → ok"
