

import math


def search(state, evaluate, propose, max_depth=None, use_ordering=True):
    """
    Iterative-deepening alpha-beta. The player to move is MAX, the other MIN.

    Anytime: a legal move is proposed first, then the best move of each
    *completed* depth. Nothing is proposed from an unfinished depth.
    """
    player = state.current_player
    cut_by_depth = False  # did the depth limit cut off any line?

    def alphabeta(depth, alpha, beta):
        """Minimax value of the current position for `player`."""
        nonlocal cut_by_depth
        if depth == 0:
            cut_by_depth = True
            return evaluate(state, player)

        moves = state.legal_moves()
        if not moves:
            if state.is_terminal():
                return evaluate(state, player)
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