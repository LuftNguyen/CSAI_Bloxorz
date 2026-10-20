"""Shared interfaces copied from CONTRACT V1; solver rules are in docs/CONTRACT.md."""
from dataclasses import dataclass
from typing import Literal

from gameModel.block import Direction

SearchStatus = Literal["solved", "unsolvable", "timeout", "node_limit"]


@dataclass(frozen=True)
class SearchLimits:
    timeout_seconds: float = 60.0
    max_expanded_nodes: int = 1_000_000


@dataclass(frozen=True)
class SearchResult:
    status: SearchStatus
    actions: tuple[Direction, ...]
    total_cost: float | None
    expanded_nodes: int
    generated_nodes: int
