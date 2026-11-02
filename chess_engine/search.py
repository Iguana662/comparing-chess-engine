"""Negamax with alpha-beta, bounded quiescence and deadline-based iterative deepening.

TV1 implementation. The caller owns adjudication and the UCI time parser.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import chess

from chess_engine.contracts import SearchLimits, SearchResult, SearchStats
from chess_engine.evaluation import Evaluator, evaluate
from chess_engine.move_ordering import order_moves

INF = 1_000_000
MATE = 99_999


class SearchTimeout(Exception):
    """Abort an incomplete iteration without treating partial scores as valid."""


@dataclass
class SearchConfig:
    max_depth: int = 3
    use_quiescence: bool = True
    use_ordering: bool = True
    check_bonus: bool = False
    time_limit: float = 5.0  # Legacy level/UI default; SearchLimits controls every call.
    qdepth: int = 4


class Searcher:
    def __init__(self, evaluator: Evaluator, config: SearchConfig) -> None:
        self._eval = evaluator
        self._cfg = config
        self._start = 0.0
        self._deadline = 0.0
        self._nodes = 0
        self._time_up = False
        self.last_stats = SearchStats(elapsed_ms=0)

    def _check_time(self) -> bool:
        if not self._time_up and time.perf_counter() >= self._deadline:
            self._time_up = True
        return self._time_up

    def _ensure_time(self) -> None:
        if self._check_time():
            raise SearchTimeout()

    @staticmethod
    def _terminal(board: chess.Board) -> bool:
        return board.is_game_over(claim_draw=True)

    def _quiescence(self, board: chess.Board, alpha: int, beta: int,
                    qdepth: int = 4) -> int:
        self._ensure_time()
        self._nodes += 1

        if self._terminal(board):
            return evaluate(board, self._eval)
        
        in_check = board.is_check()
        if not in_check:
            stand_pat = evaluate(board, self._eval)
            if qdepth <= 0:
                return stand_pat
            if stand_pat >= beta:
                return stand_pat
            alpha = max(alpha, stand_pat)
            moves = [m for m in board.legal_moves if board.is_capture(m)]
        else:
            # Stand-pat is illegal in check: consider ALL check evasions.
            moves = list(board.legal_moves)
            # Bound check extensions; at the safety boundary, still inspect each
            # legal evasion rather than evaluating an illegal stand-pat position.
            if qdepth <= -4:
                best = -INF
                for move in moves:
                    self._ensure_time()
                    board.push(move)
                    try:
                        score = -evaluate(board, self._eval)
                    finally:
                        board.pop()
                    best = max(best, score)
                    alpha = max(alpha, score)
                    if alpha >= beta:
                        break
                return best

        if self._cfg.use_ordering:
            moves = order_moves(board, moves, use_ordering=True)

        for move in moves:
            self._ensure_time()
            board.push(move)
            try:
                score = -self._quiescence(board, -beta, -alpha, qdepth - 1)
            finally:
                board.pop()
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha

    def _negamax(self, board: chess.Board, depth: int,
                 alpha: int, beta: int) -> tuple[int, chess.Move | None]:
        self._ensure_time()
        self._nodes += 1

        if self._terminal(board):
            return evaluate(board, self._eval), None
        if depth <= 0:
            if self._cfg.use_quiescence:
                return self._quiescence(board, alpha, beta, self._cfg.qdepth), None
            return evaluate(board, self._eval), None

        moves = order_moves(
            board, board.legal_moves,
            use_ordering=self._cfg.use_ordering,
            check_bonus=self._cfg.check_bonus,
        )
        best_move = None
        best_score = -INF
        for move in moves:
            self._ensure_time()
            board.push(move)
            try:
                child_score, _ = self._negamax(board, depth - 1, -beta, -alpha)
                score = -child_score
            finally:
                board.pop()
            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best_score, best_move

    def search(self, board: chess.Board, limits: SearchLimits) -> SearchResult:
        """Search without mutating `board`; return last completed iteration.

        score_cp is from the root side-to-move perspective. If time expires
        before depth 1 completes, fallback is the first legal move and score_cp
        is unavailable (None).
        """
        self._start = time.perf_counter()
        self._deadline = self._start + max(1, limits.time_ms - 20) / 1000.0
        self._time_up = False
        self._nodes = 0
        best_move = next(iter(board.legal_moves), None)
        last_depth = 0
        last_score: int | None = None

        if not self._terminal(board):
            for depth in range(1, self._cfg.max_depth + 1):
                if self._check_time():
                    break
                try:
                    score, move = self._negamax(board, depth, -INF, INF)
                except SearchTimeout:
                    break
                # Only accept a fully completed depth.
                if move is not None:
                    best_move = move
                    last_score = score
                    last_depth = depth
                if abs(score) >= 90_000:
                    break
        else:
            best_move = None
            last_score = evaluate(board, self._eval)

        elapsed = int((time.perf_counter() - self._start) * 1000)
        stats = SearchStats(
            elapsed_ms=elapsed,
            nodes=self._nodes,
            depth=last_depth,
            score_cp=last_score,
        )
        self.last_stats = stats
        return SearchResult(move=best_move, stats=stats)
