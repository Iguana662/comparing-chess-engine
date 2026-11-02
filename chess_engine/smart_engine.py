
"""Smart chess engine using Negamax and Alpha-Beta pruning.

Uses the existing UCIEngine interface and the TV1 search contract.

Run:
    python -m chess_engine.smart_engine
"""

from __future__ import annotations

import sys

import chess

from chess_engine.contracts import SearchLimits
from chess_engine.levels import (
    LEVELS,
    build_evaluator,
    build_search_config,
)
from chess_engine.search import Searcher
from chess_engine.uci import UCIEngine


class SmartEngine(UCIEngine):
    """UCI engine backed by Alpha-Beta search."""

    def __init__(self) -> None:
        super().__init__(
            name="SmartEngine",
            author="CO3061-Team",
        )
        self._level = 5
        self._rebuild()

    # -- Configuration -----------------------------------------

    def _rebuild(self) -> None:
        spec = LEVELS[self._level]
        self._evaluator = build_evaluator(spec)
        self._search_cfg = build_search_config(spec)

    def _on_setoption(self, name: str, value: str) -> None:
        if name == "Skill Level":
            lv = int(value)
            if 1 <= lv <= 10:
                self._level = lv
                self._rebuild()

    def _on_new_game(self) -> None:
        self._rebuild()

    def _print_options(self) -> None:
        print(
            "option name Skill Level "
            "type spin default 5 min 1 max 10"
        )

    # -- Alpha-Beta search -------------------------------------

    def _think(
        self,
        board: chess.Board,
    ) -> chess.Move | None:

        searcher = Searcher(
            self._evaluator,
            self._search_cfg,
        )

        # Temporary compatibility with existing UCIEngine.
        # TV4 will integrate external go movetime later.
        limits = SearchLimits(
            time_ms=max(
                1,
                int(self._search_cfg.time_limit * 1000),
            )
        )

        result = searcher.search(board, limits)
        move = result.move
        stats = result.stats

        # Standard UCI search statistics.
        print(
            f"info depth {stats.depth or 0} "
            f"score cp {stats.score_cp or 0} "
            f"nodes {stats.nodes or 0} "
            f"time {stats.elapsed_ms}"
        )

        sys.stdout.flush()

        return move


def main() -> None:
    SmartEngine().run()


if __name__ == "__main__":
    main()
