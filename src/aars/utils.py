import operator
from itertools import *


def subslices(seq):
    """
    Return all contiguous non-empty subslices of a sequence.
    Taken from more_itertools.

    Example:
        list(subslices([1, 2, 3])) == [[1], [1, 2], [1, 2, 3], [2], [2, 3], [3]]
    """
    #
    slices = starmap(slice, combinations(range(len(seq) + 1), 2))
    return map(operator.getitem, repeat(seq), slices)


def possible_index_names(seq):
    """
    Return all possible index names for a sequence of properties.

    Example:
        list(possible_index_names(['A', 'B', 'C'])) == [['A'], ['A.B'], ['A.B.C'], ['B'], ['B.C'], ['C']]
    """
    return map('.'.join, subslices(seq))
