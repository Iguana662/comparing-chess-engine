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
    def _think(self, board: chess.Board) -> chess.Move | None:
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
