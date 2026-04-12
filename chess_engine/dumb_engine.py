"""Dumb chess engine — picks a random legal move.

Extends ``UCIEngine`` (Template Method) — overrides ``_think()`` with
``random.choice()``.

Run directly::

    python -m chess_engine.dumb_engine
"""

from __future__ import annotations

import random

import chess

from chess_engine.uci import UCIEngine


class DumbEngine(UCIEngine):
    """UCI engine that plays uniformly random legal moves."""

    def __init__(self) -> None:
        super().__init__(name="DumbEngine", author="CO3061-Team")

    def _think(self, board: chess.Board, time_limit_ms: int | None = None, depth_limit: int | None = None) -> chess.Move | None:
        moves = list(board.legal_moves)
        return random.choice(moves) if moves else None


def main() -> None:
    DumbEngine().run()


if __name__ == "__main__":
    main()
