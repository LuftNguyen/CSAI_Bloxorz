"""Person 5: implement and verify heuristics; compare A* with h=0 against UCS.

Values must be finite, nonnegative and zero at goals. Revalidate admissibility
after teleport or cost changes. Upstream Manhattan is an unverified reference.
"""


def zero(problem, state) -> float:
    """Contract baseline for UCS/A* integration; no domain heuristic yet."""
    return 0.0
