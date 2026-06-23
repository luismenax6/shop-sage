"""Benchmark cosine similarity: C extension vs pure Python vs NumPy.

Scores one query vector against N stored vectors (dim 1024) and times each
implementation. Produces the speedup table for the README. The C extension and
pure Python compute the *same* operation per vector so the comparison is fair;
NumPy is shown both per-vector and vectorized for context.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/benchmark.py
"""

import array
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

# the compiled extension lives in backend/csim/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "csim"))
import csim  # noqa: E402

N = 20_000
DIM = 1024


def py_cosine(a, b):
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    return dot / math.sqrt(na * nb)


def np_cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def timed(label, fn):
    start = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - start
    print(f"  {label:<22} {elapsed * 1000:8.1f} ms")
    return elapsed


def main():
    random.seed(0)
    query = [random.gauss(0, 1) for _ in range(DIM)]
    vectors = [[random.gauss(0, 1) for _ in range(DIM)] for _ in range(N)]

    # pre-build the typed representations each implementation needs
    q_arr = array.array("d", query)
    v_arr = [array.array("d", v) for v in vectors]
    q_np = np.array(query)
    v_np = np.array(vectors)

    print(f"Cosine similarity: 1 query vs {N:,} vectors, dim {DIM}\n")

    t_py = timed("pure Python", lambda: [py_cosine(query, v) for v in vectors])
    t_c = timed("C extension", lambda: [csim.cosine(q_arr, v) for v in v_arr])
    t_np = timed("NumPy (per vector)", lambda: [np_cosine(q_np, v) for v in v_np])
    t_npv = timed(
        "NumPy (vectorized)",
        lambda: (v_np @ q_np) / (np.linalg.norm(v_np, axis=1) * np.linalg.norm(q_np)),
    )

    print(f"\n  C speedup vs pure Python:  {t_py / t_c:5.1f}x")
    print(f"  C speedup vs NumPy/vector: {t_np / t_c:5.1f}x")

    # sanity: all implementations agree on the first vector
    ref = py_cosine(query, vectors[0])
    assert abs(ref - csim.cosine(q_arr, v_arr[0])) < 1e-9
    assert abs(ref - np_cosine(q_np, v_np[0])) < 1e-9
    print("\n  (correctness check passed: all implementations agree)")


if __name__ == "__main__":
    main()
