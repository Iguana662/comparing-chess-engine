import sys
import chess
import chess.engine
import time

def run_match():
    # 1. Spawn the engines
    dumb_engine = chess.engine.SimpleEngine.popen_uci([sys.executable, "dumb_engine.py"])
    smart_engine = chess.engine.SimpleEngine.popen_uci([sys.executable, "smart_engine.py"])
    
    # 2. Create the UI's internal board state
    board = chess.Board()
    print("--- Initial Board ---")
    print(board)
    print("\n")

    # Map the engines to colors: White = Dumb, Black = Smart
    players = {
        chess.WHITE: ("Dumb Engine", dumb_engine),
        chess.BLACK: ("Smart Engine", smart_engine)
    }

    # 3. Game loop
    turn = 1
    while not board.is_game_over():
        name, engine = players[board.turn]
        print(f"Turn {turn} - {name} is thinking...")
        
        result = engine.play(board, chess.engine.Limit(time=0.1))
        if result.move is None:
            print(f"Error: {name} returned no move!")
            break
            
        board.push(result.move)
        print(f"--- {name} played {result.move} ---")
        print(board)
        print("\n")
        
        # Turn based pause (similar to your previous flow preferences)
        input("Press Enter to continue to the next turn...")
        turn += 1

    # 4. Result
    print("--- Game Over ---")
    print("Result:", board.result())
    
    if board.is_checkmate():
        winner = "Smart Engine" if board.turn == chess.WHITE else "Dumb Engine"
        print(f"Winner: {winner}")
    elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        print("Game ended in a draw.")

    # 5. Clean up
    dumb_engine.quit()
    smart_engine.quit()

if __name__ == "__main__":
    run_match()