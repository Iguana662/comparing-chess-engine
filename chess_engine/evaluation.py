"""Evaluation functions using the **Strategy** pattern.

Each evaluator implements `score(board) -> int` (centipawns, White-positive).
`CompositeEvaluator` combines multiple strategies — the active set is
determined by the skill-level configuration.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

import chess

from chess_engine.constants import (
    PIECE_VALUE,
    PST,
    PST_KING_END,
)


# =====================================================================
#  Strategy interface
# =====================================================================
class Evaluator(ABC):
    """Abstract base for a single evaluation component."""

    @abstractmethod
    def score(self, board: chess.Board) -> int:
        """Return centipawn score from White's perspective."""


# =====================================================================
#  Concrete strategies
# =====================================================================
class MaterialEvaluator(Evaluator):
    """Raw material balance."""

    def score(self, board: chess.Board) -> int:
        s = 0
        for pt, val in PIECE_VALUE.items():
            s += len(board.pieces(pt, chess.WHITE)) * val
            s -= len(board.pieces(pt, chess.BLACK)) * val
        return s


class PositionalEvaluator(Evaluator):
    """Piece-square table bonuses (switches King table in endgame)."""

    @staticmethod
    def _is_endgame(board: chess.Board) -> bool:
        queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(
            board.pieces(chess.QUEEN, chess.BLACK)
        )
        minor_major = 0
        for c in (chess.WHITE, chess.BLACK):
            minor_major += len(board.pieces(chess.ROOK, c))
            minor_major += len(board.pieces(chess.BISHOP, c))
            minor_major += len(board.pieces(chess.KNIGHT, c))
        return queens == 0 or (queens <= 2 and minor_major <= 4)

    def score(self, board: chess.Board) -> int:
        endgame = self._is_endgame(board)
        s = 0
        for sq in chess.SQUARES:
            pc = board.piece_at(sq)
            if pc is None:
                continue
            if pc.piece_type == chess.KING and endgame:
                table = PST_KING_END
            else:
                table = PST.get(pc.piece_type)
            if table is None:
                continue
            v = table[sq ^ 56] if pc.color == chess.WHITE else table[sq]
            s += v if pc.color == chess.WHITE else -v
        return s


class MobilityEvaluator(Evaluator):
    """Weighted legal-move count difference."""

    def score(self, board: chess.Board) -> int:
        side_mob = board.legal_moves.count()
        if not board.is_check():
            board.push(chess.Move.null())
            opp_mob = board.legal_moves.count()
            board.pop()
        else:
            # In check: can't use null move; estimate opponent mobility
            # from symmetry — assume average ~20 moves (neutral contribution)
            opp_mob = side_mob
        if board.turn == chess.WHITE:
            return (side_mob - opp_mob) * 10
        else:
            return (opp_mob - side_mob) * 10


class KingSafetyEvaluator(Evaluator):
    """Penalises having enemy attackers near the king zone."""

    _PIECE_WEIGHT = {
        chess.QUEEN: 4,
        chess.ROOK: 3,
        chess.BISHOP: 2,
        chess.KNIGHT: 2,
        chess.PAWN: 1,
    }

    def _danger(self, board: chess.Board, king_color: chess.Color) -> int:
        ksq = board.king(king_color)
        if ksq is None:
            return 0
        enemy = not king_color
        zone = chess.SquareSet(chess.BB_KING_ATTACKS[ksq])
        zone.add(ksq)
        d = 0
        for sq in zone:
            for att_sq in board.attackers(enemy, sq):
                att = board.piece_at(att_sq)
                if att is not None:
                    d += self._PIECE_WEIGHT.get(att.piece_type, 1)
        return d

    def score(self, board: chess.Board) -> int:
        return (
            self._danger(board, chess.BLACK) - self._danger(board, chess.WHITE)
        ) * 15


# =====================================================================
#  Composite  (combines multiple strategies)
# =====================================================================
class CompositeEvaluator(Evaluator):
    """Aggregates a list of evaluation strategies and optional random noise."""

    def __init__(self, strategies: list[Evaluator], noise: int = 0) -> None:
        self._strategies = strategies
        self._noise = noise

    def score(self, board: chess.Board) -> int:
        total = sum(s.score(board) for s in self._strategies)
        if self._noise > 0:
            total += random.randint(-self._noise, self._noise)
        return total


# =====================================================================
#  Full position evaluator (handles terminal states + side-to-move flip)
# =====================================================================
def evaluate(board: chess.Board, evaluator: Evaluator) -> int:
    """Return centipawn score **from the side-to-move's perspective**.

    Terminal conditions (checkmate / stalemate / draw) are handled first.
    """
    if board.is_checkmate():
        return -99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    if board.can_claim_draw():
        return 0

    score = evaluator.score(board)
    return score if board.turn == chess.WHITE else -score
