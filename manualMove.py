EMPTY = 0

def parse_position(pos_str):
    """
    Parses a position string like 'e2' to row and column indices.
    Returns (row, col) or None if invalid.
    """
    if len(pos_str) != 2:
        return None
    
    col_char = pos_str[0].lower()
    row_char = pos_str[1]
    
    if not ('a' <= col_char <= 'h') or not ('1' <= row_char <= '8'):
        return None
        
    col = ord(col_char) - ord('a')
    row = int(row_char) - 1
    
    return row, col

def manual_player(board):
    """
    Asks the user for a move via keyboard in the format 'e2 to e4' or 'e2 e4'.
    Executes the move on the board.
    """
    while True:
        user_input = input("Enter your move (e.g. 'e2 to e4' or 'e2 e4'): ").strip()
        
        # Split by spaces and remove the word 'to' if present
        parts = [p for p in user_input.split() if p.lower() != 'to']
        
        if len(parts) != 2:
            print("Invalid input format. Please use a format like 'e2 e4' or 'e2 to e4'.")
            continue
            
        start_pos = parse_position(parts[0])
        end_pos = parse_position(parts[1])
        
        if start_pos is None or end_pos is None:
            print("Invalid coordinates. Use letters a-h for columns and numbers 1-8 for rows.")
            continue
            
        start_row, start_col = start_pos
        end_row, end_col = end_pos
        
        # Execute the move
        piece = board[start_row][start_col]
        board[end_row][end_col] = piece
        board[start_row][start_col] = EMPTY
        
        print(f"Moved piece from {parts[0].lower()} to {parts[1].lower()}")
        break
