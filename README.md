# Comparing Chess Engine

> **CO3061 — Introduction to Artificial Intelligence**   
> **Semester 252 — Academic Year 2025-2026**    
> Ho Chi Minh City University of Technology (HCMUT)

## Table of Contents

1. [Introduction](#1-introduction)
2. [Project Structure](#2-project-structure)
3. [Getting Started](#3-getting-started)
4. [Search Algorithms](#4-search-algorithms-searchpy)
5. [Evaluation Function](#5-evaluation-function-evaluationpy)
6. [Move Ordering](#6-move-ordering-move_orderingpy)
7. [Skill Levels](#7-skill-levels-levelspy)
8. [Engine Communication — UCI Protocol](#8-engine-communication--uci-protocol-ucipy)
9. [The Two Engines](#9-the-two-engines)
10. [Chess Rules and Special Cases](#10-chess-rules-and-special-cases)
11. [GUI](#11-gui-guipy)

---

## 1. Introduction

This project builds a **chess-playing agent** — referred to as the _Smart Engine_ — that decides its moves through classical game-tree search rather than machine learning. To measure how well it plays, the agent is pitted against a **random-move baseline** (the _Dumb Engine_, which simply picks a legal move at random) across 10 configurable skill levels.

The project is the course assignment for CO3061. The specific requirements, and how each one is addressed, are listed below.

### Assignment Requirements

| #   | Requirement                                                                            | How It Is Met                                                                                           |
| --- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1   | The agent must play a complete, legal game of chess                                    | All rules (en passant, castling, promotion, draw conditions) are enforced by the `python-chess` library |
| 2   | Must defeat a random agent 10 out of 10 matches, regardless of playing first or second | Verified through the built-in tournament mode                                                           |
| 3   | Must support multiple skill levels (1-10), with a way to measure playing strength      | 10 levels with progressively deeper search, richer evaluation, and less noise                           |
| 4   | Must use search algorithms only (no ML)                                                | Negamax with Alpha-Beta pruning, Quiescence search, and Iterative Deepening                             |

---

## 2. Project Structure

The codebase is organised as a single Python package. Each module has a focused responsibility, and they interact through well-defined interfaces:

```
comparing-chess-engine/
├── chess_engine/                  # Main Python package
│   ├── __init__.py
│   ├── constants.py               # Piece values, piece-square tables, MVV-LVA tables
│   ├── evaluation.py              # Position evaluation (material, PST, mobility, king safety)
│   ├── move_ordering.py           # Move ordering heuristics — MVV-LVA, promotions, checks
│   ├── search.py                  # Search algorithms — Negamax, Alpha-Beta, Quiescence
│   ├── levels.py                  # Skill-level definitions (1-10)
│   ├── uci.py                     # UCI protocol handler
│   ├── smart_engine.py            # Smart Engine — search-based agent
│   ├── dumb_engine.py             # Dumb Engine — random legal moves
│   ├── tournament.py              # CLI for running matches and comparisons
│   └── gui.py                     # Graphical interface (CustomTkinter)
├── pyproject.toml                 # Build configuration & dependencies
└── README.md
```

The data flows roughly like this: `levels.py` defines what search depth and evaluation components to use for a given level. `smart_engine.py` reads that configuration, builds a `Searcher` (from `search.py`) and a `CompositeEvaluator` (from `evaluation.py`), and uses them to pick moves. The `Searcher` calls `move_ordering.py` to decide which moves to examine first. Communication between the engine processes and the GUI or tournament runner happens over the UCI protocol, implemented in `uci.py`.

---

## 3. Getting Started

### 3.1. Prerequisites

- **Python** from 3.9 to 3.12 (some newer py does not support pygame)
- **python-chess** 1.0 or later — provides chess rules, legal move generation, and UCI protocol support
- **customtkinter** 5.0 or later — provides the graphical user interface

### 3.2. Installation

```bash
cd comparing-chess-engine
pip install -e .
```

### 3.3. Running

There are four ways to interact with the engines.

**GUI** — watch the two engines play in real time with a graphical board, evaluation bar, and live statistics:

```bash
python -m chess_engine.gui                    # Default: Smart as Black, Level 5
python -m chess_engine.gui --level 8          # Set a specific skill level
python -m chess_engine.gui --flip             # Smart plays White instead
```

**Tournament** — run multiple matches and collect win/draw/loss statistics:

```bash
python -m chess_engine.tournament --mode tournament --level 5 --matches 10
```

**Level comparison** — run a mini-tournament at every level from 1 to 10 and print a summary table:

```bash
python -m chess_engine.tournament --mode compare --matches 4
```

**Interactive** — step through a single game move by move, pressing Enter after each turn:

```bash
python -m chess_engine.tournament --mode interactive --level 5
```

---

## 4. Search Algorithms (`search.py`)

At its core, the engine works by looking ahead: it considers every legal move, imagines the opponent's best response, then its own best reply to that, and so on, until it reaches a certain depth. It then evaluates the resulting position and backtracks to find the move that leads to the best outcome. This section explains the three techniques that make this process both correct and practical.

### 4.1. Negamax with Alpha-Beta Pruning

**Negamax** is a compact reformulation of the Minimax algorithm. It exploits the zero-sum nature of chess — what is good for one side is equally bad for the other. Instead of writing separate maximising and minimising functions, a single recursive function negates the score at each level:

```
negamax(board, depth, alpha, beta):
    if depth == 0:
        return evaluate(board)

    for move in ordered_moves(board):
        board.push(move)
        score = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()

        if score > alpha:
            alpha = score
        if alpha >= beta:
            break                  # beta cutoff — prune this branch

    return alpha
```

On its own, Negamax would explore every possible sequence of moves — far too many to handle within a reasonable time. **Alpha-Beta Pruning** solves this by maintaining a window $[\alpha, \beta]$ that narrows as the search progresses:

- $\alpha$ is the best score the current player can guarantee so far (a lower bound).
- $\beta$ is the best score the opponent can guarantee (an upper bound).
- Whenever $\alpha \geq \beta$, the current branch cannot produce a result better than what has already been found elsewhere, so the remaining moves are **skipped entirely**.

In the best case — when moves happen to be examined in roughly best-first order — Alpha-Beta reduces the effective branching factor from $b$ to roughly $\sqrt{b}$. This means the engine can search to approximately **twice the depth** in the same amount of time compared to a plain Minimax search.

### 4.2. Quiescence Search

Even with Alpha-Beta, the search has a fixed depth limit. If the engine stops evaluating a position right before the opponent is about to capture an undefended queen, the static evaluation will look fine — but the position is actually losing. This is known as the **horizon effect**.

To guard against this, the engine does not stop at depth 0 if the position is still "noisy" (material is actively being exchanged). Instead, **quiescence search** takes over and continues exploring **capture moves only** for up to 4 additional plies:

```
quiescence(board, alpha, beta, qdepth = 4):
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta                          # position is already good enough — cut
    if stand_pat > alpha:
        alpha = stand_pat

    for capture in capture_moves_only(board):
        score = -quiescence(after_capture, -beta, -alpha, qdepth - 1)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha
```

By the time quiescence search finishes, queries are resolved — no more pieces are hanging — and the static evaluation can be trusted.

### 4.3. Iterative Deepening with Time Management

Searching directly at the maximum depth is risky: the engine cannot predict exactly how long it will take, and it might exceed its time budget with no move to show for it. **Iterative Deepening** solves this by searching progressively deeper — depth 1 first, then depth 2, then depth 3, and so on:

```
best_move = None
for depth in 1 .. max_depth:
    if elapsed > 60% of time budget:
        break                                # not enough time for the next iteration
    score, move = negamax(board, depth, -INF, +INF)
    if time_up:
        break                                # mid-search timeout — keep previous best
    best_move = move
    if abs(score) > 90000:
        break                                # checkmate found — no point going deeper
```

This approach has three important benefits. First, the engine **always has a move ready**: even if time runs out halfway through a deeper pass, the best move from the last completed iteration is still valid. Second, the engine manages its clock by refusing to start a new iteration if more than 60% of the time budget has already been spent — because each successive iteration typically takes longer than all previous ones combined. Third, if the engine discovers a forced checkmate, it stops immediately, since no deeper search could improve on a guaranteed win.

---

## 5. Evaluation Function (`evaluation.py`)

The search algorithms described above tell the engine _which_ sequences of moves to explore. But at the leaves of the search tree, a different question arises: _how good is this position?_ The evaluation function answers that question by returning a score in **centipawns** (abbreviated cp; 100 cp equals the value of one pawn). A positive score favours White; a negative score favours Black.

Rather than writing one monolithic evaluation function, each evaluation criterion is an independent class implementing the same `Evaluator` interface. Different skill levels activate different combinations of these components, and adding a new criterion requires no changes to the search code.

### 5.1. Material Evaluation

The most fundamental aspect of any chess position is _how much material each side has_. The engine counts the pieces on the board and sums their values:

| Piece  | Value (cp) |
| ------ | ---------- |
| Pawn   | 100        |
| Knight | 320        |
| Bishop | 330        |
| Rook   | 500        |
| Queen  | 900        |

The score is $\\textit{White material} - \\textit{Black material}$. Being up a single pawn ($+100$ cp) is a meaningful advantage; being up a rook ($+500$ cp) is usually decisive.

### 5.2. Positional Evaluation (Piece-Square Tables)

Material counts alone cannot distinguish between a knight stuck in the corner and a knight controlling the centre. **Piece-Square Tables (PST)** address this by assigning a bonus or penalty to every square on the board, separately for each piece type. For example:

- A knight on e4 (a central square) receives $+20$, while a knight on a1 (a corner) receives $-50$.
- Pawns on the 7th rank, one step away from promotion, receive $+50$.
- The king table changes depending on the game phase: in the middlegame the king is encouraged to shelter behind pawns, while in the endgame it should advance towards the centre to support passed pawns.

All tables are stored from White's perspective. For Black, the engine mirrors the square index with a bitwise XOR (`sq ^ 56`), so the same table is reused without duplication.

### 5.3. Mobility Evaluation

A player with more legal moves generally has more flexibility: more squares controlled, more tactical options, and a more active position overall. The mobility evaluator counts the legal moves for each side and returns:

$$\textit{mobility} = (\textit{white moves} - \textit{black moves}) \times 10$$

This rewards piece activity and penalises cramped positions where pieces are blocked or pinned.

### 5.4. King Safety Evaluation

The final evaluation component examines how exposed each king is. It looks at the 9-square zone around the king (the king's square plus all 8 neighbours) and counts how many enemy pieces attack those squares, weighted by piece type:

| Attacker        | Weight |
| --------------- | ------ |
| Queen           | 4      |
| Rook            | 3      |
| Bishop / Knight | 2      |
| Pawn            | 1      |

The total danger score is multiplied by $15$ and converted into a centipawn penalty. A king surrounded by enemy attackers is in serious trouble, and this component makes the engine aware of that — both defensively (protect its own king) and offensively (target the opponent's king).

### 5.5. Composite Evaluator and Noise

Rather than having the search call each evaluator individually, a `CompositeEvaluator` bundles all active components into a single object that returns one aggregate score:

$$\textit{score} = \textit{material} + \textit{positional} + \textit{mobility} + \textit{king safety} + \textit{random}(-\textit{noise},\; +\textit{noise})$$

The noise term is a deliberate imperfection. At lower skill levels, random perturbation of up to $\pm 50$ cp is added to the evaluation, causing the engine to occasionally misjudge positions and make suboptimal moves. This is the primary mechanism for creating weaker play at low levels. At level 6 and above, noise is zero.

### 5.6. Terminal State Handling

Before any evaluator is called, the `evaluate()` function checks whether the game has already ended:

- **Checkmate** returns $-99{,}999$, indicating an immediate loss for the side to move.
- **Stalemate**, **draw by repetition**, and **insufficient material** all return $0$.

After this check, the raw score (which is computed from White's perspective) is flipped when it is Black's turn, so that the Negamax search always sees a positive number as "good for the current player."

---

## 6. Move Ordering (`move_ordering.py`)

Alpha-Beta pruning works best when strong moves are tried first — more branches get cut and the search runs faster. To achieve this, the engine scores every legal move with a heuristic and sorts them in descending order before the search begins. Three heuristics are used:

**MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)** scores capture moves by prioritising captures of high-value pieces by low-value pieces. The formula is $(\textit{victim} + \textit{attacker bonus}) \times 100$. For example, a pawn capturing a queen scores $55$, while a queen capturing a pawn scores only $11$ — so the pawn-takes-queen is examined first. This simple heuristic dramatically improves pruning without any expensive computation.

**Promotion bonus** adds $\textit{promoted piece value} \times 10$ to moves that promote a pawn, since promotion (especially to a queen) almost always represents a major material gain.

**Check bonus** adds $+300$ to moves that put the opponent's king in check. Checks are forcing moves that constrain the opponent's options, so they tend to be tactically important. This bonus is only enabled at skill level 9 and above, as it requires pushing and popping each move to detect the check — a measurable cost.

---

## 7. Skill Levels (`levels.py`)

The assignment asks for agents of varying strength. Rather than building separate engines, the project defines 10 configurations that control four independent axes: **how deep the search goes**, **which evaluation components are active**, **how much random noise is injected**, and **how much time the engine is allowed per move**. As the level increases, the engine sees further ahead, understands the position better, plays more precisely, and gets more time to think.

| Level | Depth | Quiescence | Evaluation Components   |    Noise | Time | Ordering |
| ----: | ----: | :--------: | ----------------------- | -------: | ---: | :------: |
|     1 |     1 |     No     | Material                | +/-50 cp |  1 s |    No    |
|     2 |     1 |     No     | Material                | +/-30 cp |  1 s |    No    |
|     3 |     2 |     No     | + Piece-Square Tables   | +/-15 cp |  2 s |    No    |
|     4 |     2 |    Yes     | + Piece-Square Tables   | +/-10 cp |  2 s |   Yes    |
|     5 |     3 |    Yes     | + Mobility              |  +/-5 cp |  3 s |   Yes    |
|     6 |     3 |    Yes     | + Mobility              |        0 |  3 s |   Yes    |
|     7 |     3 |    Yes     | + King Safety           |        0 |  5 s |   Yes    |
|     8 |     4 |    Yes     | + King Safety           |        0 |  5 s |   Yes    |
|     9 |     4 |    Yes     | Full eval + Check Bonus |        0 |  5 s |   Yes    |
|    10 |     5 |    Yes     | Full eval + Check Bonus |        0 |  8 s |   Yes    |

The progression is designed so that each pair of levels introduces one new capability:

- **Levels 1-2** look only one move ahead and evaluate material only. Heavy noise makes them play almost randomly, though they will usually grab free pieces when available.
- **Levels 3-4** look two moves ahead and add piece-square tables, so the engine starts placing pieces on good squares and developing towards the centre. Level 4 also enables quiescence search and move ordering, which together represent a significant jump in tactical awareness.
- **Levels 5-6** look three moves ahead and add mobility evaluation, rewarding active piece play and penalising cramped positions. Level 6 removes all noise, so the engine plays at full strength for its depth.
- **Levels 7-8** add king safety, so the engine begins to recognise and launch attacks on the opposing king while keeping its own king safe. Level 8 pushes the search depth to 4.
- **Levels 9-10** activate the full evaluation suite and enable check bonus in move ordering, prioritising forcing moves. Level 10 is the strongest setting, searching to depth 5 with 8 seconds per move.

---

## 8. Engine Communication — UCI Protocol (`uci.py`)

The GUI and tournament runner do not call the engines' Python functions directly. Instead, each engine runs as a **separate subprocess**, and all communication happens through the UCI text protocol over stdin/stdout. This keeps the search logic fully decoupled from the interface — the same engine binary works with the custom GUI, the CLI tournament runner, or any third-party UCI-compatible chess GUI such as Arena or CuteChess.

The key commands in the protocol are:

| Command                                 | Direction | Description                                                                    |
| --------------------------------------- | --------- | ------------------------------------------------------------------------------ |
| `uci`                                   | to engine | Initialise; the engine responds with its name and available options            |
| `isready` / `readyok`                   | both      | Synchronisation handshake to confirm the engine is ready                       |
| `setoption name Skill Level value 5`    | to engine | Set the skill level before or between games                                    |
| `position startpos moves e2e4 e7e5 ...` | to engine | Provide the current board position as a starting position plus a list of moves |
| `go`                                    | to engine | Ask the engine to start thinking; it responds with `bestmove e2e4`             |
| `quit`                                  | to engine | Shut down the engine process                                                   |

When the Smart Engine responds to `go`, it also emits an `info` line containing the search depth, evaluation score, node count, and elapsed time. The GUI reads this line to populate the live statistics panel.

---

## 9. The Two Engines

The project contains two engines that share the same UCI interface but differ entirely in how they choose moves.

**Smart Engine** (`smart_engine.py`) is the AI agent under evaluation. It combines all the techniques described in sections 4 through 7 — search, evaluation, move ordering, and level configuration — to find the best move within its time budget.

**Dumb Engine** (`dumb_engine.py`) is the baseline opponent. Its entire decision logic is `random.choice(legal_moves)` — no search, no evaluation. Even at level 1, the Smart Engine wins consistently, since looking just one move ahead is enough to avoid blunders.

---

## 10. Chess Rules and Special Cases

Chess has a number of special rules beyond basic piece movement, and all of them are enforced automatically by the `python-chess` library. The engine does not need any custom logic for these cases:

- **En passant** — when a pawn advances two squares from its starting rank, an adjacent enemy pawn may capture it as if it had only moved one square.
- **Castling** — the king moves two squares towards a rook, and the rook jumps to the other side of the king (available both kingside and queenside, subject to the usual conditions).
- **Pawn promotion** — a pawn reaching the last rank must be promoted to a queen, rook, bishop, or knight. The search considers all four options.
- **Fifty-move rule** — the game is drawn if 50 consecutive full moves pass without a capture or a pawn advance.
- **Threefold repetition** — the game is drawn if the same position (same piece placement, same side to move, same castling rights, same en passant square) occurs three times.
- **Insufficient material** — the game is drawn if neither side has enough pieces remaining to force checkmate (for example, king vs king, or king and bishop vs king).
- **Stalemate** — the game is drawn if the side to move has no legal moves but is not in check.

---

## 11. GUI (`gui.py`)

The graphical interface provides a visual way to watch the two engines play against each other in real time. It is built with CustomTkinter and uses a dark theme with blue and red accents.

The left side of the window shows a 592x592 pixel chessboard rendered with Unicode piece glyphs. The last move is highlighted in blue, and the king's square turns red when in check. Above and below the board, player bars display each engine's name, captured pieces, and material advantage.

The right side is an information panel. At the top, a configuration row lets the user select the skill level (1 through 10) and choose which side the Smart Engine plays (White or Black) — these controls are locked once a game starts. Below that, a real-time evaluation bar shows which side currently has the advantage, followed by an algorithm info card that displays which search features and evaluation components are active for the selected level. A live statistics section updates after every Smart Engine move, showing the search depth reached, the evaluation score in centipawns, the number of nodes visited, and the thinking time. A scrollable move log in standard algebraic notation records the full game history, and Start/Pause and Reset buttons control the game flow.

```bash
python -m chess_engine.gui --level 7 --flip
```
