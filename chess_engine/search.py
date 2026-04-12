"""Negamax search with alpha-beta pruning, quiescence, and iterative deepening."""

from __future__ import annotations

import time
from dataclasses import dataclass

import chess

from chess_engine.evaluation import Evaluator, evaluate
from chess_engine.move_ordering import order_moves


# =====================================================================
#  Search configuration (passed per-call, no globals)
# =====================================================================
@dataclass
class SearchConfig:
    """Parameters that control a single search invocation."""

    max_depth: int = 3
    use_quiescence: bool = True
    use_ordering: bool = True
    check_bonus: bool = False
    time_limit: float = 5.0  # seconds


# =====================================================================
#  Searcher  (stateful only for the current search invocation)
# =====================================================================
@dataclass
class SearchStats:
    """Statistics collected during a single search invocation."""

    depth: int = 0
    score: int = 0
    nodes: int = 0
    time_ms: int = 0


class Searcher:
    """Encapsulates a single search invocation with its own timer state."""

    def __init__(self, evaluator: Evaluator, config: SearchConfig) -> None:
        self._eval = evaluator
        self._cfg = config
        self._start: float = 0.0
        self._time_up: bool = False
        self._nodes: int = 0
        self.last_stats: SearchStats = SearchStats()

    # -- time management ------------------------------------------------
    def _check_time(self) -> bool:
        if not self._time_up and (time.time() - self._start > self._cfg.time_limit):
            self._time_up = True
        return self._time_up

    # -- quiescence -----------------------------------------------------
    def _quiescence(
        self,
        board: chess.Board,
        alpha: int,
        beta: int,
        qdepth: int = 4,
    ) -> int:
        if self._check_time():
            return evaluate(board, self._eval)

        self._nodes += 1
        stand_pat = evaluate(board, self._eval)
        if qdepth == 0:
            return stand_pat
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        captures = [m for m in board.legal_moves if board.is_capture(m)]
        if self._cfg.use_ordering:
            captures = order_moves(board, captures, use_ordering=True)

        for m in captures:
            board.push(m)
            score = -self._quiescence(board, -beta, -alpha, qdepth - 1)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    # -- negamax --------------------------------------------------------
    def _negamax(
        self,
        board: chess.Board,
        depth: int,
        alpha: int,
        beta: int,
    ) -> tuple[int, chess.Move | None]:
        if self._check_time():
            return evaluate(board, self._eval), None

        self._nodes += 1

        if board.is_game_over():
            return evaluate(board, self._eval), None

        if depth == 0:
            if self._cfg.use_quiescence:
                return self._quiescence(board, alpha, beta), None
            return evaluate(board, self._eval), None

        moves = order_moves(
            board,
            board.legal_moves,
            use_ordering=self._cfg.use_ordering,
            check_bonus=self._cfg.check_bonus,
        )
        if not moves:
            return evaluate(board, self._eval), None

        best_move = moves[0]
        best_score = -999999

        for m in moves:
            board.push(m)
            score, _ = self._negamax(board, depth - 1, -beta, -alpha)
            score = -score
            board.pop()

            if self._time_up:
                break

            if score > best_score:
                best_score = score
                best_move = m

            alpha = max(alpha, score)
            if alpha >= beta:
                break

        return best_score, best_move

    # -- public entry point (iterative deepening) -----------------------
    def search(self, board: chess.Board) -> chess.Move | None:
        """Run iterative-deepening search and return the best move."""
        self._start = time.time()
        self._time_up = False
        self._nodes = 0

        best_move: chess.Move | None = None
        last_depth = 0
        last_score = 0

        for depth in range(1, self._cfg.max_depth + 1):
            # Don't start a new iteration if >60 % of budget is spent
            if time.time() - self._start > self._cfg.time_limit * 0.6:
                break

            score, move = self._negamax(board, depth, -999999, 999999)

            if self._time_up:
                break

            last_depth = depth
            last_score = score

            if move:
                best_move = move

            if abs(score) > 90000:
                break  # mate found

        elapsed = int((time.time() - self._start) * 1000)
        self.last_stats = SearchStats(
            depth=last_depth,
            score=last_score,
            nodes=self._nodes,
            time_ms=elapsed,
        )

        # Fallback
        if best_move is None:
            legal = list(board.legal_moves)
            if legal:
                best_move = legal[0]

        return best_move
