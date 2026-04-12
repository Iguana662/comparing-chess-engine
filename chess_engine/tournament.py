"""Tournament runner — play SmartEngine vs DumbEngine in bulk.

Modes
-----
- **tournament** : N matches at a given level, alternating colours.
- **compare**    : Run a mini-tournament for every level 1–10.
- **interactive**: Step-through mode (press Enter each turn).

Run directly::

    python -m chess_engine.tournament --mode tournament --level 5 --matches 10
"""

from __future__ import annotations

import argparse
import sys

import chess
import chess.engine

from chess_engine.constants import PIECE_VALUE


# =====================================================================
#  Helpers
# =====================================================================
def _material_balance(board: chess.Board) -> int:
    """Material score from White's perspective (centipawns)."""
    s = 0
    for pt, val in PIECE_VALUE.items():
        s += len(board.pieces(pt, chess.WHITE)) * val
        s -= len(board.pieces(pt, chess.BLACK)) * val
    return s


def _engine_cmd() -> list[str]:
    """Command list to spawn an engine as a subprocess."""
    return [sys.executable, "-m"]


def _print_summary(tag: str, level: int, stats: dict[str, int], total: int) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {tag} RESULTS  (Smart Lv.{level})")
    print(f"{'=' * 60}")
    print(f"  Wins   : {stats['smart_win']}")
    print(f"  Draws  : {stats['draw']}")
    print(f"  Losses : {stats['dumb_win']}")
    wp = stats["smart_win"] / total * 100 if total else 0
    print(f"  Win%   : {wp:.1f}%")
    print(f"{'=' * 60}")


# =====================================================================
#  Single match
# =====================================================================
def run_match(
    smart_level: int,
    smart_is_white: bool,
    verbose: bool = True,
) -> str:
    """Run one game.  Returns ``'smart_win'``, ``'dumb_win'``, or ``'draw'``."""
    dumb = chess.engine.SimpleEngine.popen_uci(
        [sys.executable, "-m", "chess_engine.dumb_engine"]
    )
    smart = chess.engine.SimpleEngine.popen_uci(
        [sys.executable, "-m", "chess_engine.smart_engine"]
    )
    smart.configure({"Skill Level": smart_level})

    board = chess.Board()

    if smart_is_white:
        players = {
            chess.WHITE: ("Smart (White)", smart),
            chess.BLACK: ("Dumb  (Black)", dumb),
        }
    else:
        players = {
            chess.WHITE: ("Dumb  (White)", dumb),
            chess.BLACK: ("Smart (Black)", smart),
        }

    if verbose:
        side = "White" if smart_is_white else "Black"
        print(f"\n{'=' * 50}")
        print(f" Smart Engine Lv.{smart_level} as {side}")
        print(f"{'=' * 50}")
        print(board, "\n")

    move_count = 0
    adjudicated: chess.Color | None = None

    while not board.is_game_over():
        name, engine = players[board.turn]
        result = engine.play(board, chess.engine.Limit(time=15.0))
        if result.move is None:
            break
        board.push(result.move)
        move_count += 1
        if verbose:
            print(f" {name} -> {result.move}")
            print(board, "\n")
        if move_count > 300 or board.can_claim_draw():
            break
        # Material adjudication: auto-win if one side is up ≥ 500 cp
        if move_count >= 20:
            mat = _material_balance(board)
            if abs(mat) >= 500:
                adjudicated = chess.WHITE if mat > 0 else chess.BLACK
                break

    if verbose:
        print(f"Result: {board.result()}  ({move_count} moves)\n")

    dumb.quit()
    smart.quit()

    if adjudicated is not None:
        winner_is_white = adjudicated == chess.WHITE
        return "smart_win" if (winner_is_white == smart_is_white) else "dumb_win"

    if board.is_checkmate():
        loser_is_white = board.turn == chess.WHITE
        winner_is_white = not loser_is_white
        return "smart_win" if (winner_is_white == smart_is_white) else "dumb_win"

    return "draw"


# =====================================================================
#  Tournament
# =====================================================================
def run_tournament(
    num_matches: int = 10,
    smart_level: int = 5,
    verbose: bool = True,
) -> dict[str, int]:
    stats: dict[str, int] = {"smart_win": 0, "dumb_win": 0, "draw": 0}

    print(f"\n{'#' * 60}")
    print(f"  TOURNAMENT  –  {num_matches} matches  |  Smart Lv.{smart_level}")
    print(f"{'#' * 60}")

    for i in range(num_matches):
        smart_is_white = i % 2 == 0
        print(f"\n--- Match {i + 1}/{num_matches} ---")
        res = run_match(smart_level, smart_is_white, verbose=verbose)
        stats[res] += 1
        print(
            f"  -> {res}   "
            f"(W {stats['smart_win']}  D {stats['draw']}  L {stats['dumb_win']})"
        )

    _print_summary("TOURNAMENT", smart_level, stats, num_matches)
    return stats


# =====================================================================
#  Level comparison
# =====================================================================
def run_level_comparison(matches_per_level: int = 4, verbose: bool = False) -> None:
    print(f"\n{'#' * 60}")
    print(f"  LEVEL COMPARISON  –  {matches_per_level} matches per level")
    print(f"{'#' * 60}")

    all_results: dict[int, dict[str, int]] = {}
    for lv in range(1, 11):
        all_results[lv] = run_tournament(matches_per_level, lv, verbose=verbose)

    print(f"\n{'=' * 60}")
    print("  SUMMARY  –  Level Comparison")
    print(f"{'=' * 60}")
    print(f"{'Level':>6} | {'Wins':>5} | {'Draws':>5} | {'Losses':>6} | {'Win%':>6}")
    print(f"{'-' * 6}-+-{'-' * 5}-+-{'-' * 5}-+-{'-' * 6}-+-{'-' * 6}")
    for lv in range(1, 11):
        r = all_results[lv]
        wp = r["smart_win"] / matches_per_level * 100
        print(
            f"{lv:>6} | {r['smart_win']:>5} | {r['draw']:>5} "
            f"| {r['dumb_win']:>6} | {wp:>5.1f}%"
        )
    print(f"{'=' * 60}")


# =====================================================================
#  Interactive
# =====================================================================
def run_interactive(smart_level: int = 5) -> None:
    dumb = chess.engine.SimpleEngine.popen_uci(
        [sys.executable, "-m", "chess_engine.dumb_engine"]
    )
    smart = chess.engine.SimpleEngine.popen_uci(
        [sys.executable, "-m", "chess_engine.smart_engine"]
    )
    smart.configure({"Skill Level": smart_level})

    board = chess.Board()
    players = {
        chess.WHITE: ("Dumb Engine", dumb),
        chess.BLACK: ("Smart Engine", smart),
    }

    print(f"\n--- Interactive: Dumb (White) vs Smart Lv.{smart_level} (Black) ---")
    print(board, "\n")

    turn = 1
    while not board.is_game_over():
        name, engine = players[board.turn]
        print(f"Turn {turn} – {name} is thinking…")
        result = engine.play(board, chess.engine.Limit(time=15.0))
        if result.move is None:
            print(f"Error: {name} returned no move!")
            break
        board.push(result.move)
        print(f"--- {name} played {result.move} ---")
        print(board, "\n")
        input("Press Enter to continue…")
        turn += 1

    print("--- Game Over ---")
    print("Result:", board.result())
    if board.is_checkmate():
        winner = "Smart Engine" if board.turn == chess.WHITE else "Dumb Engine"
        print(f"Winner: {winner}")
    else:
        print("Draw.")

    dumb.quit()
    smart.quit()


# =====================================================================
#  CLI
# =====================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chess Engine Tournament Runner — CO3061 BTL"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "tournament", "compare"],
        default="tournament",
        help="interactive | tournament | compare  (default: tournament)",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=5,
        help="Smart engine skill level 1–10  (default: 5)",
    )
    parser.add_argument(
        "--matches",
        type=int,
        default=10,
        help="Number of matches  (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print board after every move",
    )
    args = parser.parse_args()

    if args.mode == "interactive":
        run_interactive(args.level)
    elif args.mode == "compare":
        run_level_comparison(args.matches, args.verbose)
    else:
        run_tournament(args.matches, args.level, args.verbose)


if __name__ == "__main__":
    main()
