# --- Piece Definitions ---
EMPTY  = 0

# White pieces (Positive)
w_pawn   = 1
w_rook   = 2
w_knight = 3
w_bishop = 4
w_queen  = 5
w_king   = 6

# Black pieces (Negative)
b_pawn   = -1
b_rook   = -2
b_knight = -3
b_bishop = -4
b_queen  = -5
b_king   = -6

from smartEngine import player_one
from dumbEngine import player_two
from manualMove import manual_player # replace player_one or player_two with manual_player to import move manually

def game_controller():
    board = [
        [ w_rook,  w_knight, w_bishop, w_queen,  w_king,   w_bishop, w_knight, w_rook ], # Row 0
        [ w_pawn,  w_pawn,   w_pawn,   w_pawn,   w_pawn,   w_pawn,   w_pawn,   w_pawn ], # Row 1
        [ EMPTY,   EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY  ], # Row 2
        [ EMPTY,   EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY  ], # Row 3
        [ EMPTY,   EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY  ], # Row 4
        [ EMPTY,   EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY,    EMPTY  ], # Row 5
        [ b_pawn,  b_pawn,   b_pawn,   b_pawn,   b_pawn,   b_pawn,   b_pawn,   b_pawn ], # Row 6
        [ b_rook,  b_knight, b_bishop, b_queen,  b_king,   b_bishop, b_knight, b_rook ]  # Row 7
    ]

    white_turn = True
    game_over = False

    print("--- Game Started ---")

    while not game_over:
        print_board(board)

        if white_turn:
            print("\nPlayer One (White)'s turn:")
            player_one(board)
            
            # Check if Black's King is missing
            if not is_king_alive(board, b_king):
                print("\nBlack King captured! Player One (White) wins!")
                game_over = True
        else:
            print("\nPlayer Two (Black)'s turn:")
            player_two(board)
            
            # Check if White's King is missing
            if not is_king_alive(board, w_king):
                print("\nWhite King captured! Player Two (Black) wins!")
                game_over = True
        
        white_turn = not white_turn
        if not game_over:
            input("Press Enter to continue...")

def is_king_alive(board, king_value):
    """Scans the board for a specific King."""
    for row in board:
        if king_value in row:
            return True 
    return False 

def print_board(board):
    """Visualizes the board with readable symbols instead of numbers"""
    
    # Dictionary to map the integer values to readable strings
    symbols = {
        EMPTY:    ". ",
        w_pawn:   "wP", w_rook: "wR", w_knight: "wN", w_bishop: "wB", w_queen: "wQ", w_king: "wK",
        b_pawn:   "bP", b_rook: "bR", b_knight: "bN", b_bishop: "bB", b_queen: "bQ", b_king: "bK"
    }

    print("\n   0  1  2  3  4  5  6  7")
    
    # Printing in reverse (from row 7 down to 0) so Black is at the top visually
    for row_idx in range(7, -1, -1):
        row_str = f"{row_idx} "
        for col_idx in range(8):
            piece_value = board[row_idx][col_idx]
            # Look up the symbol for this piece, default to "??" if something breaks
            row_str += f" {symbols.get(piece_value, '??')}" 
        print(row_str)

# Run the game
if __name__ == "__main__":
    game_controller()