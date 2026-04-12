"""Modern Chess GUI — watch SmartEngine vs DumbEngine with algorithm detail.

Uses CustomTkinter for a polished dark/green theme inspired by chess.com.

Run::

    python -m chess_engine.gui                  # default level 5
    python -m chess_engine.gui --level 8
    python -m chess_engine.gui --flip           # smart plays White
"""

from __future__ import annotations

import argparse
import sys
import threading

import chess
import chess.engine

try:
    import customtkinter as ctk
except ImportError:
    raise SystemExit("customtkinter required: pip install customtkinter")

import math
import tkinter as tk

from chess_engine.levels import LEVELS

# --- Layout -----------------------------------------------------------
SQ = 74
BOARD_PX = SQ * 8  # 592
PANEL_W = 440

# --- Colour palette (modern blue & red) --------------------------------
BG = "#16181d"
BG2 = "#11131a"
CARD = "#1c1f28"
CARD2 = "#262a35"
SEP = "#333845"
SQ_L = "#e8edf5"
SQ_D = "#7b8bb5"
HL_L = "#a8c4f0"
HL_D = "#5e85c4"
CHECK_C = "#e05252"
ACCENT = "#4d8df7"
ACCENT2 = "#3a73d4"
RED_A = "#e05252"
RED_A2 = "#c43e3e"
GLD = "#e8ac2a"
RED_C = "#e05252"
BLUE = "#4d8df7"
TXT = "#e4e8f0"
TXT2 = "#8890a4"
TXT3 = "#5a6178"
W_PC = "#ffffff"
B_PC = "#1a1a1a"
OL_W = "#2a2a2a"
OL_B = "#b0b0b0"
TAG_ON_BG = "#1a2844"
TAG_ON_FG = "#6da4f7"
TAG_OFF_BG = "#1e2028"
TAG_OFF_FG = "#4a4e5a"
EVAL_W = "#e8edf5"
EVAL_B = "#252830"
BOARD_BORDER = "#0e1016"

# Unicode pieces — filled glyphs for consistent weight
_PC = {
    (chess.KING, True): "\u265a",
    (chess.KING, False): "\u265a",
    (chess.QUEEN, True): "\u265b",
    (chess.QUEEN, False): "\u265b",
    (chess.ROOK, True): "\u265c",
    (chess.ROOK, False): "\u265c",
    (chess.BISHOP, True): "\u265d",
    (chess.BISHOP, False): "\u265d",
    (chess.KNIGHT, True): "\u265e",
    (chess.KNIGHT, False): "\u265e",
    (chess.PAWN, True): "\u265f",
    (chess.PAWN, False): "\u265f",
}
_PC_CAP = {
    (chess.KING, True): "\u2654",
    (chess.KING, False): "\u265a",
    (chess.QUEEN, True): "\u2655",
    (chess.QUEEN, False): "\u265b",
    (chess.ROOK, True): "\u2656",
    (chess.ROOK, False): "\u265c",
    (chess.BISHOP, True): "\u2657",
    (chess.BISHOP, False): "\u265d",
    (chess.KNIGHT, True): "\u2658",
    (chess.KNIGHT, False): "\u265e",
    (chess.PAWN, True): "\u2659",
    (chess.PAWN, False): "\u265f",
}
_PV = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

_EVAL_NAMES = {
    1: ["Material"],
    2: ["Material", "Piece-Square Tables"],
    3: ["Material", "Piece-Square Tables", "Mobility"],
    4: ["Material", "Piece-Square Tables", "Mobility", "King Safety"],
    5: ["Material", "Piece-Square Tables", "Mobility", "King Safety"],
}

_ALL_EVAL = ["Material", "PST", "Mobility", "King Safety"]
_ALL_SEARCH = [
    ("Quiescence", lambda sp: sp.quiescence),
    ("MVV-LVA", lambda sp: sp.ordering),
    ("Iterative Deepening", lambda sp: True),
    ("Check Bonus", lambda sp: sp.eval_level >= 5),
]

PIECE_FONT = ("Apple Symbols", 46)
COORD_FONT = ("Helvetica Neue", 9, "bold")
# 8-direction offsets for smooth piece outline
_OUTLINE_OFFSETS = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
]


# --- Helpers ----------------------------------------------------------


def _mat(board: chess.Board) -> tuple[int, int]:
    w = b = 0
    for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        w += len(board.pieces(pt, chess.WHITE)) * _PV[pt]
        b += len(board.pieces(pt, chess.BLACK)) * _PV[pt]
    return w, b


def _caps(board: chess.Board, color: chess.Color) -> list[str]:
    init = {
        chess.PAWN: 8,
        chess.KNIGHT: 2,
        chess.BISHOP: 2,
        chess.ROOK: 2,
        chess.QUEEN: 1,
    }
    out: list[str] = []
    # Count pawns that promoted (extra pieces beyond initial counts)
    promoted = 0
    for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
        extra = len(board.pieces(pt, color)) - init[pt]
        if extra > 0:
            promoted += extra
    # Adjust pawn initial count: promoted pawns are not "captured"
    init[chess.PAWN] -= promoted
    for pt, n in init.items():
        cur = len(board.pieces(pt, color))
        ch = _PC_CAP.get((pt, color == chess.WHITE), "?")
        out.extend(ch for _ in range(max(n - cur, 0)))
    return out


# --- GUI --------------------------------------------------------------


class ChessGUI(ctk.CTk):

    def __init__(self, level: int = 5, smart_white: bool = False) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.title(f"Chess Engine  —  Level {level}")
        self.configure(fg_color=BG)
        self.resizable(False, False)

        # State
        self.board = chess.Board()
        self.level = level
        self.spec = LEVELS[level]
        self.smart_white = smart_white
        self.move_list: list[str] = []
        self.last_move: chess.Move | None = None
        self.status_text = "Ready"
        self.game_over = False
        self.thinking = False
        self.auto = False
        self._closed = False

        # Engines
        self.smart: chess.engine.SimpleEngine | None = None
        self.dumb: chess.engine.SimpleEngine | None = None
        self.players: dict[chess.Color, tuple[str, str]] = (
            {chess.WHITE: ("Smart", "smart"), chess.BLACK: ("Dumb", "dumb")}
            if smart_white
            else {chess.WHITE: ("Dumb", "dumb"), chess.BLACK: ("Smart", "smart")}
        )

        self._build_ui()
        self._draw_board()
        self._update_bars()

        # Let tkinter compute the size, then lock it
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- UI construction -----------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # ── Left: board area ──
        left = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")

        # Black player bar (top)
        self.bar_top = ctk.CTkFrame(left, fg_color=CARD, corner_radius=8, height=44)
        self.bar_top.pack(fill="x", padx=14, pady=(14, 4))
        self.bar_top.pack_propagate(False)
        self._bar_top_dot = ctk.CTkLabel(self.bar_top, text="", width=0)
        self._bar_top_name = ctk.CTkLabel(
            self.bar_top,
            text="",
            font=("Helvetica Neue", 14, "bold"),
            text_color=TXT,
        )
        self._bar_top_name.pack(side="left", padx=(12, 0))
        self._bar_top_tag = ctk.CTkFrame(
            self.bar_top, fg_color=TAG_OFF_BG, corner_radius=4
        )
        self._bar_top_tag.pack(side="left", padx=(8, 0))
        self._bar_top_tag_lbl = ctk.CTkLabel(
            self._bar_top_tag,
            text="",
            font=("Helvetica Neue", 11, "bold"),
            text_color=TAG_OFF_FG,
        )
        self._bar_top_tag_lbl.pack(padx=6, pady=2)
        self._bar_top_caps = ctk.CTkLabel(
            self.bar_top,
            text="",
            font=("Apple Symbols", 13),
            text_color=TXT2,
        )
        self._bar_top_caps.pack(side="left", padx=(8, 0))
        self._bar_top_diff = ctk.CTkLabel(
            self.bar_top,
            text="",
            font=("Menlo", 13, "bold"),
            text_color=ACCENT,
        )
        self._bar_top_diff.pack(side="right", padx=(0, 12))

        # Board
        board_frame = ctk.CTkFrame(left, fg_color=BOARD_BORDER, corner_radius=4)
        board_frame.pack(padx=14, pady=0)
        self.canvas = tk.Canvas(
            board_frame,
            width=BOARD_PX,
            height=BOARD_PX,
            bg=BOARD_BORDER,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(padx=3, pady=3)

        # White player bar (bottom)
        self.bar_bot = ctk.CTkFrame(left, fg_color=CARD, corner_radius=8, height=44)
        self.bar_bot.pack(fill="x", padx=14, pady=(4, 14))
        self.bar_bot.pack_propagate(False)
        self._bar_bot_dot = ctk.CTkLabel(self.bar_bot, text="", width=0)
        self._bar_bot_name = ctk.CTkLabel(
            self.bar_bot,
            text="",
            font=("Helvetica Neue", 14, "bold"),
            text_color=TXT,
        )
        self._bar_bot_name.pack(side="left", padx=(12, 0))
        self._bar_bot_tag = ctk.CTkFrame(
            self.bar_bot, fg_color=TAG_OFF_BG, corner_radius=4
        )
        self._bar_bot_tag.pack(side="left", padx=(8, 0))
        self._bar_bot_tag_lbl = ctk.CTkLabel(
            self._bar_bot_tag,
            text="",
            font=("Helvetica Neue", 11, "bold"),
            text_color=TAG_OFF_FG,
        )
        self._bar_bot_tag_lbl.pack(padx=6, pady=2)
        self._bar_bot_caps = ctk.CTkLabel(
            self.bar_bot,
            text="",
            font=("Apple Symbols", 13),
            text_color=TXT2,
        )
        self._bar_bot_caps.pack(side="left", padx=(8, 0))
        self._bar_bot_diff = ctk.CTkLabel(
            self.bar_bot,
            text="",
            font=("Menlo", 13, "bold"),
            text_color=ACCENT,
        )
        self._bar_bot_diff.pack(side="right", padx=(0, 12))

        # ── Right: info panel (NO scrollbar) ──
        panel = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, width=PANEL_W)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_propagate(False)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=12)

        # ── Header + config ──
        ctk.CTkLabel(
            inner,
            text="Chess Engine",
            font=("Helvetica Neue", 18, "bold"),
            text_color=TXT,
        ).pack(anchor="w")
        self._lbl_subtitle = ctk.CTkLabel(
            inner,
            text=f"Smart as {'White' if self.smart_white else 'Black'}  |  Level {self.level}  |  Move 1",
            font=("Helvetica Neue", 13),
            text_color=TXT2,
        )
        self._lbl_subtitle.pack(anchor="w")

        cfg = ctk.CTkFrame(inner, fg_color=CARD, corner_radius=8)
        cfg.pack(fill="x", pady=(6, 0))
        cfg_inner = ctk.CTkFrame(cfg, fg_color="transparent")
        cfg_inner.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            cfg_inner,
            text="Level",
            font=("Helvetica Neue", 13),
            text_color=TXT2,
        ).pack(side="left")
        self._level_menu = ctk.CTkOptionMenu(
            cfg_inner,
            values=[str(i) for i in range(1, 11)],
            command=self._on_level_change,
            width=64,
            height=30,
            font=("Menlo", 13, "bold"),
            fg_color=BG2,
            button_color=CARD2,
            button_hover_color=SEP,
            dropdown_fg_color=CARD,
            dropdown_hover_color=CARD2,
            text_color=TXT,
            corner_radius=6,
        )
        self._level_menu.set(str(self.level))
        self._level_menu.pack(side="left", padx=(6, 16))

        ctk.CTkLabel(
            cfg_inner,
            text="Smart plays",
            font=("Helvetica Neue", 13),
            text_color=TXT2,
        ).pack(side="left")
        self._side_seg = ctk.CTkSegmentedButton(
            cfg_inner,
            values=["Black", "White"],
            command=self._on_side_change,
            font=("Helvetica Neue", 13, "bold"),
            height=30,
            corner_radius=6,
            fg_color=BG2,
            selected_color=ACCENT,
            selected_hover_color=ACCENT2,
            unselected_color=BG2,
            unselected_hover_color=CARD2,
            text_color=TXT,
        )
        self._side_seg.set("White" if self.smart_white else "Black")
        self._side_seg.pack(side="left", padx=(6, 0))

        # ── Eval bar ──
        ebar_frame = ctk.CTkFrame(inner, fg_color=EVAL_B, corner_radius=6, height=24)
        ebar_frame.pack(fill="x", pady=(8, 0))
        ebar_frame.pack_propagate(False)
        self._eval_bar_w = ctk.CTkFrame(ebar_frame, fg_color=EVAL_W, corner_radius=5)
        self._eval_bar_w.place(relx=0.01, rely=0.1, relwidth=0.48, relheight=0.8)
        self._eval_bar_b = ctk.CTkFrame(ebar_frame, fg_color=EVAL_B, corner_radius=5)
        self._eval_bar_b.place(relx=0.5, rely=0.1, relwidth=0.49, relheight=0.8)
        self._eval_bar_lbl = ctk.CTkLabel(
            ebar_frame,
            text="0.0",
            font=("Menlo", 10, "bold"),
            text_color=TXT,
            fg_color="transparent",
        )
        self._eval_bar_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # ── Search + Eval cards (rebuildable) ──
        self._cards_container = ctk.CTkFrame(inner, fg_color="transparent")
        self._cards_container.pack(fill="x", pady=(8, 0))
        self._rebuild_info_cards()

        # ── Live Stats — 4-column, compact ──
        ctk.CTkLabel(
            inner,
            text="LIVE STATS",
            font=("Helvetica Neue", 12, "bold"),
            text_color=TXT3,
        ).pack(anchor="w", pady=(8, 4))
        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        stat_grid = ctk.CTkFrame(inner, fg_color="transparent")
        stat_grid.pack(fill="x")
        stat_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for col, key in enumerate(["Depth", "Score", "Nodes", "Time"]):
            cell = ctk.CTkFrame(stat_grid, fg_color=CARD, corner_radius=6)
            cell.grid(row=0, column=col, padx=2, sticky="nsew")
            ctk.CTkLabel(
                cell,
                text=key.upper(),
                font=("Helvetica Neue", 10),
                text_color=TXT3,
            ).pack(pady=(6, 0))
            lbl = ctk.CTkLabel(
                cell,
                text="\u2014",
                font=("Menlo", 15, "bold"),
                text_color=ACCENT,
            )
            lbl.pack(pady=(1, 6))
            self._stat_labels[key] = lbl

        # ── Status ──
        self._lbl_status = ctk.CTkLabel(
            inner,
            text="Ready",
            font=("Helvetica Neue", 14, "bold"),
            text_color=TXT2,
            anchor="w",
        )
        self._lbl_status.pack(fill="x", pady=(8, 2))

        # ── Move log (takes remaining space) ──
        ctk.CTkLabel(
            inner,
            text="MOVES",
            font=("Helvetica Neue", 12, "bold"),
            text_color=TXT3,
        ).pack(anchor="w", pady=(2, 4))
        self._movelog = ctk.CTkTextbox(
            inner,
            font=("Menlo", 12),
            fg_color=CARD,
            text_color=TXT2,
            corner_radius=6,
            activate_scrollbars=True,
            wrap="word",
            border_width=1,
            border_color=SEP,
        )
        self._movelog.pack(fill="both", expand=True, pady=(0, 8))
        self._movelog.configure(state="disabled")

        # ── Buttons ──
        bf = ctk.CTkFrame(inner, fg_color="transparent")
        bf.pack(fill="x")
        self._btn_go = ctk.CTkButton(
            bf,
            text="Start",
            command=self._on_go,
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="#1a1a1a",
            font=("Helvetica Neue", 14, "bold"),
            corner_radius=8,
            height=38,
        )
        self._btn_go.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._btn_rst = ctk.CTkButton(
            bf,
            text="Reset",
            command=self._on_rst,
            fg_color=CARD,
            hover_color=CARD2,
            text_color=TXT,
            font=("Helvetica Neue", 14, "bold"),
            corner_radius=8,
            height=38,
            border_width=1,
            border_color=SEP,
        )
        self._btn_rst.pack(side="right", expand=True, fill="x", padx=(3, 0))

    # -- Panel helper widgets ------------------------------------------

    def _section_label(self, parent: ctk.CTkFrame, text: str) -> None:
        """Not used in the new layout — kept for compatibility."""
        pass

    def _kv_row(
        self,
        parent: ctk.CTkFrame,
        key: str,
        val: str,
        val_color: str = TXT,
        font_size: int = 11,
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(
            row,
            text=key,
            font=("Helvetica Neue", font_size),
            text_color=TXT3,
            width=50,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=val,
            font=("Helvetica Neue", font_size, "bold"),
            text_color=val_color,
            anchor="w",
        ).pack(side="left")

    def _htag(self, parent: ctk.CTkFrame, text: str, on: bool) -> None:
        bg = TAG_ON_BG if on else TAG_OFF_BG
        fg = TAG_ON_FG if on else TAG_OFF_FG
        tag = ctk.CTkFrame(parent, fg_color=bg, corner_radius=4)
        tag.pack(side="left", padx=(0, 4), pady=1)
        ctk.CTkLabel(
            tag,
            text=text,
            font=("Helvetica Neue", 11, "bold"),
            text_color=fg,
        ).pack(padx=7, pady=3)

    def _rebuild_info_cards(self) -> None:
        for w in self._cards_container.winfo_children():
            w.destroy()
        sp = self.spec
        card = ctk.CTkFrame(
            self._cards_container,
            fg_color=CARD,
            corner_radius=8,
            border_width=1,
            border_color=SEP,
        )
        card.pack(fill="x")

        # ── SEARCH header + detail below ──
        ctk.CTkLabel(
            card,
            text="SEARCH",
            font=("Helvetica Neue", 12, "bold"),
            text_color=TXT3,
        ).pack(anchor="w", padx=10, pady=(10, 0))
        parts = ["Negamax + Alpha-Beta", f"Depth {sp.depth}", f"{sp.time:.0f}s"]
        if sp.noise > 0:
            parts.append(f"\u00b1{sp.noise}cp")
        ctk.CTkLabel(
            card,
            text="  \u00b7  ".join(parts),
            font=("Helvetica Neue", 13),
            text_color=TXT2,
        ).pack(anchor="w", padx=10, pady=(2, 0))

        # ── Search feature tags — horizontal ──
        stag = ctk.CTkFrame(card, fg_color="transparent")
        stag.pack(fill="x", padx=8, pady=(6, 0))
        for label, check_fn in _ALL_SEARCH:
            self._htag(stag, label, check_fn(sp))

        # ── Separator ──
        ctk.CTkFrame(card, fg_color=SEP, height=1).pack(fill="x", padx=8, pady=(8, 0))

        # ── EVALUATION header ──
        ctk.CTkLabel(
            card,
            text="EVALUATION",
            font=("Helvetica Neue", 12, "bold"),
            text_color=TXT3,
        ).pack(anchor="w", padx=10, pady=(8, 0))

        # ── Eval feature tags — grid, full width ──
        active_evals = _EVAL_NAMES.get(sp.eval_level, [])
        etag = ctk.CTkFrame(card, fg_color="transparent")
        etag.pack(fill="x", padx=8, pady=(6, 10))
        _eval_names = ["Material", "Piece-Square Tables", "Mobility", "King Safety"]
        etag.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for col, name in enumerate(_eval_names):
            on = name in active_evals
            bg = TAG_ON_BG if on else TAG_OFF_BG
            fg = TAG_ON_FG if on else TAG_OFF_FG
            cell = ctk.CTkFrame(etag, fg_color=bg, corner_radius=4)
            cell.grid(row=0, column=col, padx=2, sticky="ew")
            ctk.CTkLabel(
                cell,
                text=name,
                font=("Helvetica Neue", 11, "bold"),
                text_color=fg,
            ).pack(padx=5, pady=3)

    def _on_level_change(self, value: str) -> None:
        new_level = int(value)
        if new_level == self.level:
            return
        self.level = new_level
        self.spec = LEVELS[new_level]
        self._rebuild_info_cards()
        self._update_bars()
        self.title(f"Chess Engine  \u2014  Level {self.level}")

    def _on_side_change(self, value: str) -> None:
        new_smart_white = value == "White"
        if new_smart_white == self.smart_white:
            return
        self.smart_white = new_smart_white
        self.players = (
            {chess.WHITE: ("Smart", "smart"), chess.BLACK: ("Dumb", "dumb")}
            if self.smart_white
            else {chess.WHITE: ("Dumb", "dumb"), chess.BLACK: ("Smart", "smart")}
        )
        self._update_bars()

    def _update_subtitle(self) -> None:
        side = "White" if self.smart_white else "Black"
        self._lbl_subtitle.configure(
            text=f"Smart as {side}  |  Level {self.level}  |  Move {self.board.fullmove_number}"
        )

    # -- Board drawing -------------------------------------------------

    def _draw_board(self) -> None:
        c = self.canvas
        c.delete("all")

        hl: set[int] = set()
        if self.last_move:
            hl.add(self.last_move.from_square)
            hl.add(self.last_move.to_square)

        check_sq = self.board.king(self.board.turn) if self.board.is_check() else None

        for sq in chess.SQUARES:
            r, f = chess.square_rank(sq), chess.square_file(sq)
            x1, y1 = f * SQ, (7 - r) * SQ
            x2, y2 = x1 + SQ, y1 + SQ
            light = (r + f) % 2 == 1

            if sq == check_sq:
                col = CHECK_C
            elif sq in hl:
                col = HL_L if light else HL_D
            else:
                col = SQ_L if light else SQ_D

            c.create_rectangle(x1, y1, x2, y2, fill=col, outline="")

            pc = self.board.piece_at(sq)
            if pc:
                ch = _PC[(pc.piece_type, pc.color == chess.WHITE)]
                cx, cy = x1 + SQ // 2, y1 + SQ // 2
                oc = OL_W if pc.color == chess.WHITE else OL_B
                mc = W_PC if pc.color == chess.WHITE else B_PC
                # 8-direction outline for smoother edges
                for dx, dy in _OUTLINE_OFFSETS:
                    c.create_text(
                        cx + dx,
                        cy + dy,
                        text=ch,
                        fill=oc,
                        font=PIECE_FONT,
                    )
                c.create_text(cx, cy, text=ch, fill=mc, font=PIECE_FONT)

        # Coordinates
        for i in range(8):
            fc = SQ_D if i % 2 == 0 else SQ_L
            c.create_text(
                i * SQ + SQ - 6,
                BOARD_PX - 7,
                text=chr(97 + i),
                fill=fc,
                font=COORD_FONT,
            )
            rc = SQ_L if i % 2 == 0 else SQ_D
            c.create_text(
                7,
                i * SQ + 8,
                text=str(8 - i),
                fill=rc,
                font=COORD_FONT,
            )

    # -- Player bars ---------------------------------------------------

    def _update_bars(self) -> None:
        for color, bar, dot, name_lbl, caps_lbl, diff_lbl, tag_frame, tag_lbl in [
            (
                chess.BLACK,
                self.bar_top,
                self._bar_top_dot,
                self._bar_top_name,
                self._bar_top_caps,
                self._bar_top_diff,
                self._bar_top_tag,
                self._bar_top_tag_lbl,
            ),
            (
                chess.WHITE,
                self.bar_bot,
                self._bar_bot_dot,
                self._bar_bot_name,
                self._bar_bot_caps,
                self._bar_bot_diff,
                self._bar_bot_tag,
                self._bar_bot_tag_lbl,
            ),
        ]:
            pname, kind = self.players[color]
            is_smart = kind == "smart"
            is_turn = color == self.board.turn
            bar.configure(fg_color=CARD2 if is_turn else CARD)
            name_lbl.configure(text=f"{pname} Engine")

            # Player type tag
            if is_smart:
                tag_frame.configure(fg_color=TAG_ON_BG)
                tag_lbl.configure(
                    text=f"AI Lv.{self.level}" if is_smart else "RANDOM",
                    text_color=TAG_ON_FG,
                )
            else:
                tag_frame.configure(fg_color="#3a1a1e")
                tag_lbl.configure(text="RANDOM", text_color=RED_A)

            captured = _caps(self.board, not color)
            caps_lbl.configure(text=" ".join(captured) if captured else "")

            wm, bm = _mat(self.board)
            diff = (wm - bm) if color == chess.WHITE else (bm - wm)
            if diff > 0:
                diff_lbl.configure(text=f"+{diff}", text_color=ACCENT)
            else:
                diff_lbl.configure(text="")

        self._update_subtitle()

    # -- Status helpers ------------------------------------------------

    def _set_status(self, text: str, kind: str = "normal") -> None:
        self.status_text = text
        cmap = {"thinking": GLD, "win": ACCENT, "draw": "#46b4c8", "normal": TXT2}
        self._lbl_status.configure(text=text[:50], text_color=cmap.get(kind, TXT2))

    def _append_moves(self) -> None:
        self._movelog.configure(state="normal")
        self._movelog.delete("1.0", "end")
        self._movelog.insert("end", "\n".join(self.move_list))
        self._movelog.see("end")
        self._movelog.configure(state="disabled")

    # -- Engines -------------------------------------------------------

    def _spawn(self) -> None:
        try:
            self.dumb = chess.engine.SimpleEngine.popen_uci(
                [sys.executable, "-m", "chess_engine.dumb_engine"]
            )
            self.smart = chess.engine.SimpleEngine.popen_uci(
                [sys.executable, "-m", "chess_engine.smart_engine"]
            )
            self.smart.configure({"Skill Level": self.level})
            self._set_status("Engines ready")
        except Exception as e:
            self._set_status(f"Error: {e}")

    def _kill(self) -> None:
        for e in (self.smart, self.dumb):
            if e:
                try:
                    e.quit()
                except Exception:
                    pass
        self.smart = self.dumb = None

    # -- Callbacks -----------------------------------------------------

    def _on_go(self) -> None:
        if self.game_over:
            return
        if not self.auto:
            self.auto = True
            self._level_menu.configure(state="disabled")
            self._side_seg.configure(state="disabled")
            self._btn_go.configure(
                text="Pause",
                fg_color=CARD,
                hover_color=CARD2,
                text_color=TXT,
                border_width=1,
                border_color=SEP,
            )
            if not self.smart:
                self._spawn()
            self._tick()
        else:
            self.auto = False
            self._btn_go.configure(
                text="Start",
                fg_color=ACCENT,
                hover_color=ACCENT2,
                text_color="#0a0a1a",
                border_width=0,
            )

    def _on_rst(self) -> None:
        self._kill()
        self.board = chess.Board()
        self.move_list.clear()
        self.last_move = None
        self.game_over = self.thinking = self.auto = False
        self._set_status("Ready")
        self._btn_go.configure(
            text="Start",
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="#0a0a1a",
            border_width=0,
        )
        self._level_menu.configure(state="normal")
        self._side_seg.configure(state="normal")
        self._draw_board()
        self._update_bars()
        self._movelog.configure(state="normal")
        self._movelog.delete("1.0", "end")
        self._movelog.configure(state="disabled")
        for lbl in self._stat_labels.values():
            lbl.configure(text="\u2014", text_color=ACCENT)
        self._eval_bar_w.place(relx=0.01, rely=0.1, relwidth=0.48, relheight=0.8)
        self._eval_bar_b.place(relx=0.5, rely=0.1, relwidth=0.49, relheight=0.8)
        self._eval_bar_lbl.configure(text="0.0")
        self._eval_bar_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self.title(f"Chess Engine  —  Level {self.level}")

    def _on_close(self) -> None:
        self._closed = True
        self.auto = False
        self._kill()
        self.destroy()

    # -- Game loop (via after) -----------------------------------------

    def _tick(self) -> None:
        if self._closed or not self.auto:
            return
        if not self.thinking and not self.game_over:
            self.thinking = True
            name, kind = self.players[self.board.turn]
            self._set_status(f"{name} thinking\u2026", "thinking")
            threading.Thread(target=self._compute_move, daemon=True).start()
        if not self._closed:
            self.after(350, self._tick)

    def _compute_move(self) -> None:
        name, kind = self.players[self.board.turn]
        eng = self.smart if kind == "smart" else self.dumb
        if not eng:
            self.thinking = False
            return
        try:
            res = eng.play(
                self.board, chess.engine.Limit(time=15.0), info=chess.engine.INFO_ALL
            )
            info = res.info if res.info else {}
            if self._closed:
                return
            if res.move:
                self.after(
                    0,
                    lambda m=res.move, n=name, i=info, k=kind: self._apply_move(
                        m, n, i, k
                    ),
                )
            else:
                self.after(0, self._handle_no_move)
        except Exception as e:
            if self._closed:
                return
            self.after(0, lambda err=str(e): self._handle_error(err))

    def _apply_move(
        self, move: chess.Move, name: str, info: dict | None = None, kind: str = ""
    ) -> None:
        san = self.board.san(move)
        mn = self.board.fullmove_number
        is_white = self.board.turn == chess.WHITE
        self.board.push(move)
        self.last_move = move

        if is_white:
            self.move_list.append(f"{mn}. {san}")
        elif self.move_list:
            self.move_list[-1] += f"  {san}"
        else:
            self.move_list.append(f"1. ... {san}")

        if self.board.is_game_over() or self.board.can_claim_draw():
            self._end()
        else:
            self._set_status(f"{name} played {san}")

        # Update live stats if this was a Smart engine move
        if kind == "smart" and info:
            self._update_live_stats(info)

        self._draw_board()
        self._update_bars()
        self._append_moves()
        self.thinking = False

    def _update_live_stats(self, info: dict) -> None:
        depth = info.get("depth", "\u2014")
        self._stat_labels["Depth"].configure(text=str(depth))

        score = info.get("score")
        if score is not None:
            pov = score.white()
            if pov.is_mate():
                m = pov.mate()
                self._stat_labels["Score"].configure(
                    text=f"M{m}", text_color=ACCENT if m > 0 else RED_C
                )
            else:
                cp = pov.score() or 0
                if abs(cp) >= 9000:
                    self._stat_labels["Score"].configure(
                        text="Mate", text_color=ACCENT if cp > 0 else RED_C
                    )
                else:
                    sc_text = f"+{cp}" if cp >= 0 else str(cp)
                    sc_col = ACCENT if cp > 50 else (RED_C if cp < -50 else TXT)
                    self._stat_labels["Score"].configure(
                        text=f"{sc_text}cp", text_color=sc_col
                    )
        else:
            self._stat_labels["Score"].configure(text="\u2014", text_color=TXT)

        nodes = info.get("nodes", 0)
        if nodes >= 1_000_000:
            n_text = f"{nodes / 1_000_000:.1f}M"
        elif nodes >= 1_000:
            n_text = f"{nodes / 1_000:.1f}K"
        else:
            n_text = str(nodes)
        self._stat_labels["Nodes"].configure(text=n_text)

        time_ms = info.get("time", 0)
        if isinstance(time_ms, (int, float)):
            self._stat_labels["Time"].configure(text=f"{time_ms:.2f}s")
        else:
            self._stat_labels["Time"].configure(text="\u2014")

        # Update eval bar
        self._refresh_eval_bar(info)

    def _refresh_eval_bar(self, info: dict) -> None:
        score = info.get("score")
        if score is None:
            return
        pov = score.white()
        if pov.is_mate():
            cp = 10000 if pov.mate() > 0 else -10000
        else:
            cp = pov.score() or 0
        pct = 0.5 + math.atan(cp / 300) / math.pi
        pct = max(0.04, min(0.96, pct))
        self._eval_bar_w.place(
            relx=0.01, rely=0.1, relwidth=max(pct - 0.01, 0.02), relheight=0.8
        )
        self._eval_bar_b.place(
            relx=pct, rely=0.1, relwidth=max(0.99 - pct, 0.02), relheight=0.8
        )
        sc = cp / 100
        sc_text = f"+{sc:.1f}" if sc >= 0 else f"{sc:.1f}"
        self._eval_bar_lbl.place(relx=pct, rely=0.5, anchor="center")
        self._eval_bar_lbl.configure(text=sc_text)

    def _handle_no_move(self) -> None:
        self._set_status("No legal move")
        self.game_over = self.auto = False
        self.thinking = False

    def _handle_error(self, msg: str) -> None:
        self._set_status(f"Error: {msg}")
        self.game_over = True
        self.auto = False
        self.thinking = False

    def _end(self) -> None:
        self.game_over = True
        self.auto = False
        self._btn_go.configure(
            text="Start",
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="#0a0a1a",
            border_width=0,
        )
        self._level_menu.configure(state="normal")
        self._side_seg.configure(state="normal")
        if self.board.is_checkmate():
            w = self.players[not self.board.turn][0]
            self._set_status(f"Checkmate! {w} wins", "win")
            self.title(f"Checkmate — {w} Engine wins!")
        elif self.board.is_stalemate():
            self._set_status("Stalemate \u2014 Draw", "draw")
        else:
            self._set_status(f"Draw \u2014 {self.board.result()}", "draw")


# --- CLI --------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Chess Engine GUI")
    parser.add_argument(
        "--level", type=int, default=5, help="Smart engine level 1-10 (default: 5)"
    )
    parser.add_argument(
        "--flip", action="store_true", help="Smart plays White (default: Black)"
    )
    args = parser.parse_args()
    app = ChessGUI(level=args.level, smart_white=args.flip)
    app.mainloop()


if __name__ == "__main__":
    main()
