import sys
import chess
import random

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        
        if line == "uci":
            print("id name DumbEngine")
            print("id author You")
            print("uciok")
            sys.stdout.flush()
            
        elif line == "isready":
            print("readyok")
            sys.stdout.flush()
            
        elif line.startswith("position"):
            parts = line.split(" ")
            if "startpos" in parts:
                board.reset()
            if "moves" in parts:
                idx = parts.index("moves")
                for m in parts[idx+1:]:
                    board.push_uci(m)
                    
        elif line.startswith("go"):
            moves = list(board.legal_moves)
            if moves:
                move = random.choice(moves)
                print(f"bestmove {move.uci()}")
            else:
                print("bestmove 0000")
            sys.stdout.flush()
            
        elif line == "quit":
            break

if __name__ == "__main__":
    main()