
import chess

from chess_engine.contracts import SearchLimits
from chess_engine.evaluation import CompositeEvaluator, MaterialEvaluator
from chess_engine.search import SearchConfig, Searcher


board = chess.Board()

evaluator = CompositeEvaluator(
    strategies=[MaterialEvaluator()],
    noise=0,
)

config = SearchConfig(
    max_depth=64,
    use_quiescence=True,
    use_ordering=True,
    check_bonus=True,
)

for budget in [200, 1000]:
    searcher = Searcher(evaluator, config)

    result = searcher.search(
        board,
        SearchLimits(time_ms=budget),
    )

    print(f"\nBudget: {budget} ms")
    print(f"Best move: {result.move}")
    print(f"Elapsed: {result.stats.elapsed_ms} ms")
    print(f"Depth: {result.stats.depth}")
    print(f"Nodes: {result.stats.nodes}")

    assert result.move in board.legal_moves

# ===== TV1: Quiescence check-evasion test =====

check_board = chess.Board(
    "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1"
)

print("\n=== QUIESCENCE CHECK TEST ===")
print("White in check:", check_board.is_check())

original_fen = check_board.fen()
original_stack = list(check_board.move_stack)

searcher = Searcher(
    evaluator,
    config,
)

searcher._start = __import__("time").perf_counter()
searcher._deadline = searcher._start + 5.0
searcher._time_up = False
searcher._nodes = 0

score = searcher._quiescence(
    check_board,
    -999999,
    999999,
    qdepth=0,
)

print("Quiescence score:", score)
print("Nodes visited:", searcher._nodes)
print("Board unchanged:", check_board.fen() == original_fen)

assert check_board.is_check()
assert check_board.fen() == original_fen
assert check_board.move_stack == original_stack

print("PASS: Quiescence handles check without modifying board")



# ===== TV1: Checkmate terminal test =====

print("\n=== CHECKMATE TEST ===")

mate_board = chess.Board()

# Fool's Mate: Black checkmates White.
for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
    mate_board.push_uci(move)

print("Checkmate:", mate_board.is_checkmate())

original_fen = mate_board.fen()
original_stack = list(mate_board.move_stack)

mate_searcher = Searcher(evaluator, config)

result = mate_searcher.search(
    mate_board,
    SearchLimits(time_ms=200),
)

print("Best move:", result.move)
print("Board unchanged:", mate_board.fen() == original_fen)

assert mate_board.is_checkmate()
assert result.move is None
assert mate_board.fen() == original_fen
assert mate_board.move_stack == original_stack

print("PASS: Checkmate terminal handled correctly")



# ===== TV1: Mate in 1 test =====

print("\n=== MATE IN 1 TEST ===")

mate1_board = chess.Board(
    "6k1/5ppp/8/8/8/8/5PPP/5RK1 w - - 0 1"
)

# Use a known forced mate-in-one position.
mate1_board = chess.Board(
    "7k/6pp/5KQ1/8/8/8/8/8 w - - 0 1"
)

original_fen = mate1_board.fen()
original_stack = list(mate1_board.move_stack)

mate1_searcher = Searcher(evaluator, config)

result = mate1_searcher.search(
    mate1_board,
    SearchLimits(time_ms=1000),
)

print("Best move:", result.move)

assert result.move is not None
assert result.move in mate1_board.legal_moves

mate1_board.push(result.move)
try:
    print("Checkmate after move:", mate1_board.is_checkmate())
    assert mate1_board.is_checkmate()
finally:
    mate1_board.pop()

assert mate1_board.fen() == original_fen
assert mate1_board.move_stack == original_stack

print("PASS: Alpha-Beta finds mate in 1")



# ===== TV1: Stalemate test =====

print("\n=== STALEMATE TEST ===")

stalemate_board = chess.Board(
    "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
)

original_fen = stalemate_board.fen()
original_stack = list(stalemate_board.move_stack)

print("Stalemate:", stalemate_board.is_stalemate())
print("In check:", stalemate_board.is_check())

stalemate_searcher = Searcher(evaluator, config)

result = stalemate_searcher.search(
    stalemate_board,
    SearchLimits(time_ms=200),
)

print("Best move:", result.move)

assert stalemate_board.is_stalemate()
assert not stalemate_board.is_check()
assert result.move is None
assert stalemate_board.fen() == original_fen
assert stalemate_board.move_stack == original_stack

print("PASS: Stalemate handled correctly")



# ===== TV1: Threefold repetition test =====

print("\n=== THREEFOLD REPETITION TEST ===")

repetition_board = chess.Board()

# Repeat the starting position three times.
moves = [
    "g1f3", "g8f6", "f3g1", "f6g8",
    "g1f3", "g8f6", "f3g1", "f6g8",
]

for move in moves:
    repetition_board.push_uci(move)

original_fen = repetition_board.fen()
original_stack = list(repetition_board.move_stack)

print("Threefold repetition:",
      repetition_board.is_repetition(3))

print("Can claim draw:",
      repetition_board.can_claim_threefold_repetition())

searcher = Searcher(evaluator, config)

result = searcher.search(
    repetition_board,
    SearchLimits(time_ms=200),
)

print("Best move:", result.move)
print("Board unchanged:",
      repetition_board.fen() == original_fen)

assert repetition_board.is_repetition(3)
assert repetition_board.can_claim_threefold_repetition()
assert result.move is None
assert repetition_board.fen() == original_fen
assert repetition_board.move_stack == original_stack

print("PASS: Threefold repetition handled correctly")



# ===== TV1: Fifty-move rule test =====

print("\n=== FIFTY-MOVE RULE TEST ===")

fifty_board = chess.Board(
    "8/8/8/8/8/8/4K3/6kR w - - 100 51"
)

original_fen = fifty_board.fen()
original_stack = list(fifty_board.move_stack)

print("Can claim fifty-move draw:",
      fifty_board.can_claim_fifty_moves())

print("Game over (claim draw):",
      fifty_board.is_game_over(claim_draw=True))

fifty_searcher = Searcher(evaluator, config)

result = fifty_searcher.search(
    fifty_board,
    SearchLimits(time_ms=200),
)

print("Best move:", result.move)
print("Board unchanged:",
      fifty_board.fen() == original_fen)

assert fifty_board.can_claim_fifty_moves()
assert fifty_board.is_game_over(claim_draw=True)
assert result.move is None
assert fifty_board.fen() == original_fen
assert fifty_board.move_stack == original_stack

print("PASS: Fifty-move rule handled correctly")



# ===== TV1: Timeout and board integrity test =====

print("\n=== TIMEOUT AND BOARD INTEGRITY TEST ===")

timeout_board = chess.Board()

# Create a position with move history.
for move in ["e2e4", "e7e5", "g1f3", "b8c6"]:
    timeout_board.push_uci(move)

original_fen = timeout_board.fen()
original_stack = list(timeout_board.move_stack)

timeout_searcher = Searcher(evaluator, config)

result = timeout_searcher.search(
    timeout_board,
    SearchLimits(time_ms=1),
)

print("Best move:", result.move)
print("Elapsed:", result.stats.elapsed_ms, "ms")
print("Completed depth:", result.stats.depth)
print("Board unchanged:", timeout_board.fen() == original_fen)
print("Move stack unchanged:",
      timeout_board.move_stack == original_stack)

assert result.move in timeout_board.legal_moves
assert timeout_board.fen() == original_fen
assert timeout_board.move_stack == original_stack

print("PASS: Timeout returns legal move and preserves board")



# ===== TV1: Alpha-Beta vs plain Negamax =====

from chess_engine.evaluation import evaluate

print("\n=== ALPHA-BETA VS NEGAMAX TEST ===")


def plain_negamax(board, depth, evaluator):
    """Negamax without alpha-beta pruning."""
    if board.is_game_over(claim_draw=True) or depth == 0:
        return evaluate(board, evaluator)

    best = -999999

    for move in list(board.legal_moves):
        board.push(move)
        try:
            score = -plain_negamax(
                board, depth - 1, evaluator
            )
        finally:
            board.pop()

        best = max(best, score)

    return best


test_board = chess.Board()

for move in ["e2e4", "e7e5", "g1f3", "b8c6"]:
    test_board.push_uci(move)

original_fen = test_board.fen()
original_stack = list(test_board.move_stack)

# Disable quiescence for a fair comparison.
compare_config = SearchConfig(
    max_depth=2,
    use_quiescence=False,
    use_ordering=True,
    check_bonus=False,
)

ab_searcher = Searcher(evaluator, compare_config)

ab_result = ab_searcher.search(
    test_board,
    SearchLimits(time_ms=5000),
)

plain_score = plain_negamax(
    test_board, 2, evaluator
)

print("Alpha-Beta score:", ab_result.stats.score_cp)
print("Plain Negamax score:", plain_score)
print("Completed depth:", ab_result.stats.depth)

assert ab_result.stats.depth == 2
assert ab_result.stats.score_cp == plain_score
assert test_board.fen() == original_fen
assert test_board.move_stack == original_stack

print("PASS: Alpha-Beta matches plain Negamax")



# ===== TV1: Multiple-position Alpha-Beta validation =====

print("\n=== MULTIPLE POSITION COMPARISON ===")

positions = [
    ("Starting position", []),
    ("King pawn opening", ["e2e4", "e7e5"]),
    ("Italian opening", [
        "e2e4", "e7e5", "g1f3", "b8c6", "f1c4"
    ]),
    ("Queen pawn opening", ["d2d4", "d7d5"]),
]

for name, moves in positions:
    board = chess.Board()

    for move in moves:
        board.push_uci(move)

    original_fen = board.fen()
    original_stack = list(board.move_stack)

    ab = Searcher(evaluator, compare_config)
    result = ab.search(board, SearchLimits(time_ms=5000))

    plain_score = plain_negamax(board, 2, evaluator)

    print(
        f"{name}: AB={result.stats.score_cp}, "
        f"Negamax={plain_score}"
    )

    assert result.stats.depth == 2
    assert result.stats.score_cp == plain_score
    assert board.fen() == original_fen
    assert board.move_stack == original_stack

print("PASS: All positions match plain Negamax")



# ===== TV1: Full benchmark configuration test =====

from chess_engine.levels import (
    build_benchmark_config,
    build_benchmark_evaluator,
)

print("\n=== FULL ALPHA-BETA BENCHMARK TEST ===")

benchmark_board = chess.Board()

benchmark_searcher = Searcher(
    build_benchmark_evaluator(),
    build_benchmark_config(),
)

original_fen = benchmark_board.fen()
original_stack = list(benchmark_board.move_stack)

for budget in [200, 500, 1000]:
    result = benchmark_searcher.search(
        benchmark_board,
        SearchLimits(time_ms=budget),
    )

    print(f"\nBudget: {budget} ms")
    print("Best move:", result.move)
    print("Elapsed:", result.stats.elapsed_ms, "ms")
    print("Depth:", result.stats.depth)
    print("Nodes:", result.stats.nodes)
    print("Score:", result.stats.score_cp, "cp")

    assert result.move in benchmark_board.legal_moves
    assert benchmark_board.fen() == original_fen
    assert benchmark_board.move_stack == original_stack

print("\nPASS: Full Alpha-Beta benchmark configuration works")
