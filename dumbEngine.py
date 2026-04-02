EMPTY = 0

def player_two(board):
    """Dummy function for Player Two (Black)"""
    # Example: Black moves E7 pawn to E5
    # E7 is board[6][4], E5 is board[4][4]
    board[4][4] = board[6][4]
    board[6][4] = EMPTY
