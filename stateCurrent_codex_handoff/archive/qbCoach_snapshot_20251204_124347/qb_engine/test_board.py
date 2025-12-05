# qb_engine/test_board.py

from qb_engine.board_state import BoardState


def main():
    board = BoardState.create_initial_board()
    print("Initial Board:")
    board.print_board()


if __name__ == "__main__":
    main()
