"""
Game engine for Competitive Sudoku.

'State' is the game model the search walks through. It can list the legal
moves, play a move, pass, and take back the last move or pass.

Rules:

- A move is legal when the cell is empty, the cell is allowed for the
  current player, the value is not already in the cell's row, column or
  block, and the (cell, value) pair has not been declared taboo.
- Allowed cells are the player's starting cells plus the cells next to
  (including diagonally) cells that player occupies. In 'classic' mode
  every empty cell is allowed.
- Completing 0, 1, 2 or 3 regions with one move scores 0, 1, 3 or 7 points.
- A player without a legal move passes. The game is over when the board is
  full, or when neither player has a legal move.

"""

import copy

from competitive_sudoku.sudoku import GameState, Move, SudokuBoard

# Points scored for completing 0, 1, 2 or 3 regions with a single move.
POINTS = {0: 0, 1: 1, 2: 3, 3: 7}

# Marker stored in the history when a player passes.
PASS = None


class State:
    """
    A copy of the game that moves can be played on and taken back.

    We keep a private copy of GameState and change it in
    place. That way we can reuse the framework's own rule for allowed cells
    (GameState.player_squares) instead of writing it again.
    """

    def __init__(self, game_state: GameState):
        # Copy, so the search never changes the game state of the real game.
        self.game_state = copy.deepcopy(game_state)
        self.board = self.game_state.board
        self.scores = self.game_state.scores

        # Region size. Regions are m rows by n columns; they are not always
        # square (for example 2x3), so we never assume m == n.
        self.m = self.board.region_height()
        self.n = self.board.region_width()
        self.N = self.board.N

        # Taboo moves as (square, value) pairs, for fast lookup.
        self.taboo = {(move.square, move.value) for move in game_state.taboo_moves}

        # One entry per apply() or pass_turn(), so undo() knows what to revert.
        # A move is stored as (move, points scored); a pass as PASS.
        self.history = []

    @property
    def current_player(self) -> int:
        """The player whose turn it is: 1 or 2."""
        return self.game_state.current_player

    # Moves

    def legal_moves(self) -> list[Move]:
        """
        All legal moves for the current player.
        An empty list means the player has no move and must pass.
        """
        moves = []
        for square in self.allowed_squares():
            for value in range(1, self.N + 1):
                if self.fits(square, value) and (square, value) not in self.taboo:
                    moves.append(Move(square, value))
        return moves

    def allowed_squares(self) -> list[tuple[int, int]]:
        """The empty cells the current player may fill."""
        squares = self.game_state.player_squares()
        if squares is None:
            # Classic mode: every empty cell is allowed.
            squares = [
                (i, j)
                for i in range(self.N)
                for j in range(self.N)
                if self.board.get((i, j)) == SudokuBoard.empty
            ]
        return squares

    def fits(self, square: tuple[int, int], value: int) -> bool:
        """True if `value` is not yet in the row, column or block of `square`."""
        return all(
            self.board.get(cell) != value
            for region in self.regions_of(square)
            for cell in region
        )

    def regions_of(self, square: tuple[int, int]):
        """The cells of the row, the column and the block that contain `square`."""
        i, j = square
        row = [(i, c) for c in range(self.N)]
        column = [(r, j) for r in range(self.N)]

        # Top-left corner of the block: round the row down to a multiple of
        # the block height, and the column down to a multiple of the width.
        top = (i // self.m) * self.m
        left = (j // self.n) * self.n
        block = [
            (r, c) for r in range(top, top + self.m) for c in range(left, left + self.n)
        ]

        return row, column, block

    # Playing and taking back moves

    def apply(self, move: Move) -> None:
        """Play `move` for the current player, add its points, switch players."""
        player = self.current_player

        self.board.put(move.square, move.value)

        occupied = self.game_state.occupied_squares()
        if occupied is not None:  # None in classic mode
            occupied.append(move.square)

        points = POINTS[self.regions_completed(move.square)]
        self.scores[player - 1] += points

        self.game_state.current_player = 3 - player
        self.history.append((move, points))

    def pass_turn(self) -> None:
        """The current player passes: only the turn changes."""
        self.game_state.current_player = 3 - self.current_player
        self.history.append(PASS)

    def undo(self) -> None:
        """Take back the last apply() or pass_turn()."""
        last = self.history.pop()

        # Give the turn back to the player who made the move or passed.
        self.game_state.current_player = 3 - self.current_player
        if last is PASS:
            return

        move, points = last
        self.scores[self.current_player - 1] -= points

        occupied = self.game_state.occupied_squares()
        if occupied is not None:
            occupied.pop()  # apply() appended this square last

        self.board.put(move.square, SudokuBoard.empty)

    def regions_completed(self, square: tuple[int, int]) -> int:
        """How many of the row, column and block of `square` are full (0 to 3)."""
        return sum(
            all(self.board.get(cell) != SudokuBoard.empty for cell in region)
            for region in self.regions_of(square)
        )

    # End of the game

    def is_terminal(self) -> bool:
        """True if the board is full, or if neither player has a legal move."""
        if SudokuBoard.empty not in self.board.squares:
            return True
        if self.legal_moves():
            return False

        # The current player is stuck. The game is only over if the
        # opponent is stuck too, so look at the position from their side.
        self.pass_turn()
        opponent_stuck = not self.legal_moves()
        self.undo()
        return opponent_stuck
