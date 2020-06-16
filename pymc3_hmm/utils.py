import numpy as np

import theano.tensor as tt

from scipy.special import logsumexp


def compute_steady_state(P):
    """Compute the steady state of a transition probability matrix.

    Parameters
    ----------
    P: Theano matrix
        A transition probability matrix for K states with shape (K, K)

    Returns
    -------
    A tensor representing the steady state.
    """

    N_states = P.shape[0]
    Lam = (tt.eye(N_states) - P + tt.ones((N_states, N_states))).T
    u = tt.slinalg.solve(Lam, tt.ones((N_states,)))
    return u


def compute_trans_freqs(states, N_states, counts_only=False):
    """Compute empirical state transition frequencies.

    Each row, `r`, corresponds to transitions from state `r` to each other
    state.

    Parameters
    ----------
    states: a pymc object or ndarray
        Vector sequence of states.
    N_states: int
        Total number of observable states.
    counts_only: boolean
        Return only the transition counts for each state.

    Returns
    -------
        Unless `counts_only` is `True`, return the empirical state transition
        frequencies; otherwise, return the transition counts for each state.
    """
    states_ = getattr(states, "values", states).ravel()

    if any(np.isnan(states_)):
        states_ = np.ma.masked_invalid(states_).astype(np.uint)
        states_mask = np.ma.getmask(states_)
        valid_pairs = ~states_mask[:-1] & ~states_mask[1:]
        state_pairs = (states_[:-1][valid_pairs], states_[1:][valid_pairs])
    else:
        state_pairs = (states_[:-1], states_[1:])

    counts = np.zeros((N_states, N_states))
    flat_coords = np.ravel_multi_index(state_pairs, counts.shape)
    counts.flat += np.bincount(flat_coords, minlength=counts.size)
    counts = np.nan_to_num(counts, nan=0)

    if counts_only:
        res = counts
    else:
        res = counts / np.maximum(1, counts.sum(axis=1, keepdims=True))

    return res


def tt_logsumexp(x, axis=None, keepdims=False):
    # Adapted from https://github.com/Theano/Theano/issues/1563
    x_max_ = tt.max(x, axis=axis, keepdims=False)
    x_max = tt.basic.makeKeepDims(x, x_max_, axis)
    res = tt.log(tt.sum(tt.exp(x - x_max), axis=axis, keepdims=keepdims)) + x_max_
    return res


def tt_logdotexp(A, b):
    """Compute a numerically stable log-scale dot product for Theano tensors.

    The result is equivalent to `tt.log(tt.exp(A).dot(tt.exp(b)))`

    """
    A_bcast = A.dimshuffle(list(range(A.ndim)) + ["x"])

    sqz = False
    shape_b = ["x"] + list(range(b.ndim))
    if len(shape_b) < 3:
        shape_b += ["x"]
        sqz = True

    b_bcast = b.dimshuffle(shape_b)
    res = tt_logsumexp(A_bcast + b_bcast, axis=1)
    return res.squeeze() if sqz else res


def logdotexp(A, b):
    """Compute a numerically stable log-scale dot product.

    The result is equivalent to `np.log(np.exp(A).dot(np.exp(b)))`

    """
    sqz = False
    b_bcast = np.expand_dims(b, 0)
    if b.ndim < 2:
        b_bcast = np.expand_dims(b_bcast, -1)
        sqz = True

    A_bcast = np.expand_dims(A, -1)

    res = logsumexp(A_bcast + b_bcast, axis=1)
    return res.squeeze() if sqz else res
