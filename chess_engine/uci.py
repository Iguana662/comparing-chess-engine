"""UCI protocol handler using the **Template Method** pattern.

``UCIEngine`` implements the full UCI read-parse-respond loop.
Subclasses override ``_think(board) -> chess.Move`` to supply their own
move-selection logic.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod

import chess


class UCIEngine(ABC):
    """Base UCI engine — handles protocol, delegates thinking to subclasses."""

    def __init__(self, name: str = "UCIEngine", author: str = "Team") -> None:
        self._name = name
        self._author = author
        self._board = chess.Board()

    # ------------------------------------------------------------------
    #  Template hooks (subclasses override)
    # ------------------------------------------------------------------
    @abstractmethod
    def _think(self, board: chess.Board, time_limit_ms: int | None = None, depth_limit: int | None = None) -> chess.Move | None:
        """Select a move for the current position."""

    def _on_setoption(self, name: str, value: str) -> None:
        """Called for ``setoption name <n> value <v>``.  Override to handle."""

    def _on_new_game(self) -> None:
        """Called on ``ucinewgame``.  Override to clear caches etc."""

    # ------------------------------------------------------------------
    #  UCI protocol loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Blocking stdin/stdout UCI loop."""
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            if line == "uci":
                self._cmd_uci()
            elif line == "isready":
                self._cmd_isready()
            elif line == "ucinewgame":
                self._on_new_game()
            elif line.startswith("position"):
                self._cmd_position(line)
            elif line.startswith("go"):
                self._cmd_go(line)
            elif line.startswith("setoption"):
                self._cmd_setoption(line)
            elif line == "quit":
                break

    # ------------------------------------------------------------------
    #  Built-in UCI commands
    # ------------------------------------------------------------------
    def _cmd_uci(self) -> None:
        print(f"id name {self._name}")
        print(f"id author {self._author}")
        self._print_options()
        print("uciok")
        sys.stdout.flush()

    def _cmd_isready(self) -> None:
        print("readyok")
        sys.stdout.flush()

    def _cmd_position(self, line: str) -> None:
        parts = line.split()
        if "startpos" in parts:
            self._board = chess.Board()
        elif "fen" in parts:
            idx = parts.index("fen")
            fen = " ".join(parts[idx + 1 : idx + 7])
            self._board = chess.Board(fen)

        if "moves" in parts:
            idx = parts.index("moves")
            for m in parts[idx + 1 :]:
                self._board.push_uci(m)

    def _cmd_go(self, line: str) -> None:
        parts = line.split()
        time_limit_ms = None
        depth_limit = None
        try:
            if "depth" in parts:
                idx = parts.index("depth")
                depth_limit = int(parts[idx + 1])
                
            if "movetime" in parts:
                idx = parts.index("movetime")
                time_limit_ms = int(parts[idx + 1])
            elif "wtime" in parts and "btime" in parts:
                wtime = int(parts[parts.index("wtime") + 1])
                btime = int(parts[parts.index("btime") + 1])
                my_time = wtime if self._board.turn == chess.WHITE else btime
                time_limit_ms = max(50, int(my_time / 40))
        except (ValueError, IndexError):
            pass

        move = self._think(self._board, time_limit_ms, depth_limit)
        if move is not None:
            print(f"bestmove {move.uci()}")
        else:
            print("bestmove 0000")
        sys.stdout.flush()

    def _cmd_setoption(self, line: str) -> None:
        # setoption name Skill Level value 5
        parts = line.split()
        if "name" in parts and "value" in parts:
            ni = parts.index("name")
            vi = parts.index("value")
            name = " ".join(parts[ni + 1 : vi])
            value = " ".join(parts[vi + 1 :])
            self._on_setoption(name, value)

    def _print_options(self) -> None:
        """Override to advertise engine-specific UCI options."""
