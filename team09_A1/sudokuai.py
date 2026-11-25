#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import random
import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
import competitive_sudoku.sudokuai


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()
    
    
    def compute_best_move(self, game_state: GameState) -> None:
        N = game_state.board.N
        #We define the default weights as those stated in the rules, 0, 1, 3, 7 points scored for
        # 0,1,2,3 regions completed with a move
        default_weights = {0:0,1:1,2:3,3:7}
        
        # Check whether a cell is empty, a value in that cell is not taboo, and that cell is allowed
        def possible(i, j, value):
            return game_state.board.get((i, j)) == SudokuBoard.empty \
                   and not TabooMove((i, j), value) in game_state.taboo_moves \
                       and (i, j) in game_state.player_squares()

        
        def evaluate(board: SudokuBoard, scores: list[int], move, player: int, weights=default_weights) -> float:
            """ This is the evaluation function, which returns a float that describes how good the current state
                is for each player. specifically it will output between 0 and 1, with 0 being better for 
                player B (minimizing) and 1 being better for player A (maximizing)
            """
            #First we check that we got 2 scores, one for each player.
            assert len(scores) == 2, "scores should be a list of length 2"
            
            #The first idea of the current state is the already computed scores
            A_score = scores[0]
            B_score = scores[1]
            base_eval = A_score-B_score
            
            #For player 2 we want a negative value, so:
            if player==1:
                p_value = 1
            else:
                p_value = -1
            #Now we check if we are increasing our score by playing this move
            square_x, square_y = move.square
            # To do this, we check for the row, column and block if they contain 3 values before this move/
            # if they are full after this move. then we use the weights to calculate the score gain.
            
            # by base we complete nothing
            region_h = board.region_height()
            region_w = board.region_width()
            board_h = board.board_height()
            board_w = board.board_width()
            
            # For the column, row and region we check if all others are filled,
            # we make the following variables for this
            full_col = True
            full_row = True
            full_region = True
            
            # If this move completes a col, completions += 1
            for y in range(board_h):
                # For each square in the column that is not our current move
                if y != square_y:
                    # if it is not filled, change col value to False
                    if not board.get(square=(square_x, y)):
                        full_col = False
            
            # If this move completes a row, completions += 1
            for x in range(board_w):
                # For each square in the row that is not our current move
                if x != square_x:
                    # if it is not filled, change row value to False
                    if not board.get(square=(x, square_y)):
                        full_row = False
                
            # If this move completes a region, completions += 1
            for x in range(region_w):
                for y in range(region_h):
                    # For each square in the region that is not our current move
                    # We go through each square in the base region, checking that they are not in 
                    # the location that our candidate square would be
                    if (x,y) != (square_x%region_w, square_y%region_h):
                        
                        # Next we transform these new squares into the places in the region our candidate square is in.
                        # Thus we add the width of a region an amount of times equal to how many regions our candidate square
                        # is to the right or down.
                        if not board.get(square=(x+ region_w * (square_x//region_w), y+ region_h * (square_y//region_h))):
                            full_region = False
                
            
            completions = full_col+full_row+full_region
            
            if completions>=1:
                print(completions)

            score_change = p_value * weights[completions]
            
            eval_value = base_eval + score_change
            
            return eval_value

        all_moves = [Move((i, j), value) for i in range(N) for j in range(N)
                     for value in range(1, N+1) if possible(i, j, value)]
        
        
        best_score = -10

        for prop_move in all_moves:
            value = evaluate(board = game_state.board, scores = game_state.scores, move=prop_move, player = 1)
            if value > best_score:
                best_score = value
                self.propose_move(prop_move)
    

