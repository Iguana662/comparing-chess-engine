"""Move ordering heuristics (MVV-LVA, promotions, checks)."""

from __future__ import annotations

import chess

from chess_engine.constants import MVV_LVA, PIECE_VALUE


def order_moves(
    board: chess.Board,
    moves: chess.LegalMoveGenerator,
    *,
    use_ordering: bool = True,
    check_bonus: bool = False,
) -> list[chess.Move]:
    """Return *moves* sorted best-first using heuristic scores.

    Parameters
    ----------
    use_ordering : bool
        If False, return moves in default generator order (no sorting).
    check_bonus : bool
        If True, push each move to detect checks (slightly expensive).
    """
    if not use_ordering:
        return list(moves)

    scored: list[tuple[int, chess.Move]] = []
    for m in moves:
        s = 0
        # Captures → MVV-LVA
        if board.is_capture(m):
            victim = board.piece_at(m.to_square)
            aggressor = board.piece_at(m.from_square)
            if victim and aggressor:
                s += MVV_LVA.get((victim.piece_type, aggressor.piece_type), 0) * 100
            else:
                s += 500  # en-passant fallback
        # Promotions
        if m.promotion:
            s += PIECE_VALUE.get(m.promotion, 0) * 10
        # Check bonus
        if check_bonus:
            board.push(m)
            if board.is_check():
                s += 300
            board.pop()
        scored.append((s, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored]
