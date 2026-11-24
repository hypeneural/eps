from __future__ import annotations


def depth_passes(final_depth: float, pass_depth: float) -> list[float]:
    if final_depth <= 0:
        raise ValueError("final_depth must be > 0")
    if pass_depth <= 0:
        raise ValueError("pass_depth must be > 0")
    passes: list[float] = []
    current = pass_depth
    while current < final_depth:
        passes.append(round(current, 4))
        current += pass_depth
    if not passes or passes[-1] != final_depth:
        passes.append(round(final_depth, 4))
    return passes
