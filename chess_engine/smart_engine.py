"""Smart chess engine — Negamax + Alpha-Beta with configurable skill levels.

Extends ``UCIEngine`` (Template Method) — overrides ``_think()`` to use
the ``Searcher`` with a level-dependent ``CompositeEvaluator``.

Run directly::

    python -m chess_engine.smart_engine
"""

from __future__ import annotations

import sys

import chess

from chess_engine.levels import LEVELS, build_evaluator, build_search_config
from chess_engine.search import Searcher
from chess_engine.uci import UCIEngine


class SmartEngine(UCIEngine):
    """UCI engine backed by Negamax search and composite evaluation."""

    def __init__(self) -> None:
        super().__init__(name="SmartEngine", author="CO3061-Team")
        self._level = 5
        self._rebuild()

    # -- configuration --------------------------------------------------
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
        print("option name Skill Level type spin default 5 min 1 max 10")

    # -- Template Method hook -------------------------------------------
    def _think(self, board: chess.Board, time_limit_ms: int | None = None, depth_limit: int | None = None) -> chess.Move | None:
        if time_limit_ms is not None:
            if time_limit_ms < 100:
                self._level = 1
            elif time_limit_ms < 250:
                self._level = 2
            elif time_limit_ms < 500:
                self._level = 3
            elif time_limit_ms < 750:
                self._level = 4
            elif time_limit_ms < 1000:
                self._level = 5
            elif time_limit_ms < 1250:
                self._level = 6
            elif time_limit_ms < 1500:
                self._level = 7
            elif time_limit_ms < 2000:
                self._level = 8
            elif time_limit_ms < 2500:
                self._level = 9
            else:
                self._level = 10
            
            self._rebuild()
            self._search_cfg.time_limit = time_limit_ms / 1000.0

        if depth_limit is not None:
            self._search_cfg.max_depth = depth_limit
            if time_limit_ms is None:
                self._search_cfg.time_limit = 999999.0

        searcher = Searcher(self._evaluator, self._search_cfg)
        move = searcher.search(board)
        # Send UCI info so the GUI can read live stats
        s = searcher.last_stats
        print(
            f"info depth {s.depth} score cp {s.score} "
            f"nodes {s.nodes} time {s.time_ms}"
        )
        sys.stdout.flush()
        return move


def main() -> None:
    SmartEngine().run()


if __name__ == "__main__":
    main()
