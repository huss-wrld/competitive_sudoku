#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import math
import copy
#import random
#import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard#, TabooMove
import competitive_sudoku.sudokuai


 #We define the default weights as those stated in the rules, 0, 1, 3, 7 points scored for
 # 0,1,2,3 regions completed with a move
default_weights = {0:0,1:1,2:3,3:7}

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

        points = default_weights[self.regions_completed(move.square)]
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



class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()
    
    
    def compute_best_move(self, game_state: GameState) -> None:
     
        
        # Check whether a cell is empty, a value in that cell is not taboo, and that cell is allowed

        def search(state, evaluate, propose, max_depth=None, use_ordering=True):
            """
            Iterative-deepening alpha-beta. The player to move is MAX, the other MIN.

            Anytime: a legal move is proposed first, then the best move of each
            *completed* depth. Nothing is proposed from an unfinished depth.
            """
            cut_by_depth = False  # did the depth limit cut off any line?
            player = state.current_player

            def alphabeta(depth, alpha, beta):
                """Minimax value of the current position for `player`."""
                nonlocal cut_by_depth

                if depth == 0:
                    cut_by_depth = True
                    return evaluate(state = state, player = player, current_player = state.current_player)

                moves = state.legal_moves()
                if not moves:
                    if state.is_terminal():
                        return evaluate(state = state, player = player, current_player = state.current_player)
                    state.pass_turn()  # a pass is a ply, not a leaf
                    value = alphabeta(depth - 1, alpha, beta)
                    state.undo()
                    return value

                maximizing = state.current_player == player
                best = -math.inf if maximizing else math.inf
                for move in moves:
                    state.apply(move)
                    value = alphabeta(depth - 1, alpha, beta)
                    state.undo()
                    if maximizing:
                        best = max(best, value)
                        alpha = max(alpha, best)
                    else:
                        best = min(best, value)
                        beta = min(beta, best)
                    if alpha >= beta:
                        break  # cut-off
                return best

            moves = state.legal_moves()
            if not moves:
                return
            propose(moves[0])

            depth = 1
            while max_depth is None or depth <= max_depth:
                cut_by_depth = False

                # Root = a MAX node. Strict '>' keeps the earlier move on ties.
                best_move, best_value = moves[0], -math.inf
                for move in moves:
                    state.apply(move)
                    value = alphabeta(depth - 1, best_value, math.inf)
                    state.undo()
                    if value > best_value:
                        best_move, best_value = move, value

                    propose(best_move)  # this depth is complete
                if not cut_by_depth:
                    break  # every line ended in a finished game: deeper is pointless
                if use_ordering:  # next depth: previous best move first
                    moves.insert(0, moves.pop(moves.index(best_move)))
                depth += 1
                
        def evaluate(state, player: int, current_player: int, weights=default_weights) -> float:
            """ This is the evaluation function, which returns a float that describes how good the current state
                is for each player. specifically it will output between 0 and 1, with 0 being better for 
                player B (minimizing) and 1 being better for player A (maximizing)
            """
            board = state.board
            scores = state.scores
            legal = state.legal_moves()
            
            #First we check that we got 2 scores, one for each player.
            assert len(scores) == 2, "scores should be a list of length 2"
            
            
            #The first idea of the current state is the already computed scores
            if player==1:
                p_value = 1
            else:
                p_value = -1
            
            if current_player == player:
                # if we are maximizing
                current_p = 1
            else:
                #if we are minimizing
                current_p = -1
                    
            
            A_score = scores[0]
            B_score = scores[1]
            
            # If A is maximizing, the evaluation should be A-B, if they are minimizing it should be B-A.
            base_eval = (A_score-B_score)*p_value
            
            #Calculate the size of the board
            
            #region_h = board.region_height()
            #region_w = board.region_width()
            board_h = board.board_height()
            board_w = board.board_width()
            
            eval_value = base_eval + len(legal)/(2*board_h*board_w)*current_p
            
            return eval_value

        #all_moves = [Move((i, j), value) for i in range(N) for j in range(N)
        #             for value in range(1, N+1) if possible(i, j, value)]
        state = State(game_state)
        search(state, evaluate, self.propose_move)
    

