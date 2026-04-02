EMPTY = 0

def player_one(board):
    """Dummy function for Player One (White)"""
    # Example: White moves E2 pawn to E4
    # E2 is board[1][4], E4 is board[3][4]
    board[3][4] = board[1][4]
    board[1][4] = EMPTY
