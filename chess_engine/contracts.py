
"""Shared search contract for Alpha-Beta and MCTS."""

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class SearchLimits:
    time_ms: int
    seed: int | None = None

    def __post_init__(self):
        if self.time_ms <= 0:
            raise ValueError("time_ms must be positive")


@dataclass
class SearchStats:
    elapsed_ms: int
    nodes: int | None = None
    depth: int | None = None
    simulations: int | None = None
    score_cp: int | None = None
    expected_score: float | None = None


@dataclass
class SearchResult:
    move: chess.Move | None
    stats: SearchStats
