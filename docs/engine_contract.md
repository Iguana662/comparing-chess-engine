
# Engine Search Contract – TV1 Alpha-Beta

## 1. Overview

This document describes the shared search interface used by
the Alpha-Beta engine and intended for integration with MCTS.

The contract is implemented in `chess_engine/contracts.py`.

## 2. Input: SearchLimits

```python
SearchLimits(
    time_ms: int,
    seed: int | None = None
)
```

- `time_ms`: Positive search budget in milliseconds.
- `seed`: Optional random seed.
- Alpha-Beta does not use the seed in deterministic benchmark mode.

## 3. Output: SearchResult

```python
SearchResult(
    move: chess.Move | None,
    stats: SearchStats
)
```

- `move`: Selected legal move.
- `None`: Returned when the position is terminal under the
  project's adjudication policy.

## 4. SearchStats

| Field | Meaning |
|---|---|
| elapsed_ms | Actual elapsed search time in milliseconds |
| depth | Last fully completed search depth |
| nodes | Number of visited search nodes |
| score_cp | Evaluation in centipawns from the root side-to-move perspective |
| simulations | Not applicable to Alpha-Beta |
| expected_score | Not applicable to Alpha-Beta |

Non-applicable values are represented by `None`.

## 5. Alpha-Beta Search

The Alpha-Beta engine uses:

- Negamax with Alpha-Beta pruning
- Iterative Deepening
- Quiescence Search
- Move Ordering
- Material Evaluation
- Piece-Square Tables
- Mobility Evaluation
- King Safety Evaluation

## 6. Time Management

Search time is measured using `time.perf_counter()`.

The search deadline is calculated as:

```python
deadline = start + max(1, time_ms - 20) / 1000.0
```

If a search iteration is interrupted, its incomplete result
is discarded. The engine returns the best move from the last
completed iteration or a legal fallback move.

## 7. Benchmark Configuration

| Parameter | Value |
|---|---|
| Max depth | 64 |
| Quiescence | Enabled |
| Quiescence depth | 4 |
| Move ordering | Enabled |
| Check bonus | Enabled |
| Evaluation noise | 0 |
| Time budget | Provided by SearchLimits |

## 8. Board Integrity

The search must not modify the caller's board or move history.

The implementation uses `try/finally` around board push/pop
operations to restore the board even when a timeout occurs.

## 9. Validation

The Alpha-Beta implementation has been tested for:

- Legal move selection
- 200 ms and 1000 ms time budgets
- Check evasion in Quiescence Search
- Checkmate and mate in one
- Stalemate
- Threefold repetition
- Fifty-move rule
- Timeout fallback and board preservation
- Alpha-Beta versus unpruned Negamax at depth 2
- Fixed benchmark configuration at 200, 500 and 1000 ms

All listed tests passed in the local development environment.

## 10. Integration Notes

The Alpha-Beta search interface is:

```python
result = searcher.search(board, SearchLimits(time_ms=1000))
```

The UCI adapter is responsible for parsing `go movetime`
and forwarding the requested budget.

The current SmartEngine adapter uses a temporary level-based
time budget until UCI integration is completed.
