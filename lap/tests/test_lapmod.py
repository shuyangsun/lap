from pytest import mark, fixture, raises

import numpy as np
from lap import lapjv, lapmod

from .test_utils import (
    get_dense_8x8_int,
    get_dense_100x100_int,
    get_dense_100x100_int_hard,
    get_sparse_100x100_int,
    get_dense_1kx1k_int,
    get_dense_1kx1k_int_hard,
    get_sparse_1kx1k_int,
    get_sparse_4kx4k_int,
    get_dense_eps,
    get_platform_maxint,
    sparse_from_dense,
    sparse_from_masked,
)


@mark.parametrize(
    "cost,expected",
    [
        (
            np.array(
                [
                    [1000, 2, 11, 10, 8, 7, 6, 5],
                    [6, 1000, 1, 8, 8, 4, 6, 7],
                    [5, 12, 1000, 11, 8, 12, 3, 11],
                    [11, 9, 10, 1000, 1, 9, 8, 10],
                    [11, 11, 9, 4, 1000, 2, 10, 9],
                    [12, 8, 5, 2, 11, 1000, 11, 9],
                    [10, 11, 12, 10, 9, 12, 1000, 3],
                    [10, 10, 10, 10, 6, 3, 1, 1000],
                ]
            ),
            (17.0, [1, 2, 0, 4, 5, 3, 7, 6], [2, 0, 1, 5, 3, 4, 7, 6]),
        ),
        # Solved in column reduction.
        (
            np.array([[1000, 4, 1], [1, 1000, 3], [5, 1, 1000]]),
            (3.0, [2, 0, 1], [1, 2, 0]),
        ),
        # Solved in augmenting row reduction.
        (
            np.array([[5, 1000, 3], [1000, 2, 2], [1, 5, 1000]]),
            (6.0, [2, 1, 0], [2, 1, 0]),
        ),
        # Needs augmentating row reduction - only a single row previously assigned.
        (
            np.array([[1000, 1000 + 1, 1000], [1000, 1000, 1000 + 1], [1, 2, 3]]),
            (1000 + 1000 + 1.0, [2, 1, 0], [2, 1, 0]),
        ),
        # Triggers the trackmate bug
        # Solution is ambiguous, [1, 0, 2] gives the same cost, depends on whether
        # in column reduction columns are iterated over from largest to smallest or
        # the other way around.
        (
            np.array([[10, 10, 13], [4, 8, 8], [8, 5, 8]]),
            (13 + 4 + 5, [2, 0, 1], [1, 2, 0]),
        ),
        (
            np.array([[11, 10, 6], [10, 11, 11], [11, 12, 15]]),
            (6 + 10 + 12, [2, 0, 1], [1, 2, 0]),
        ),
        (
            np.array([[12, 4, 9], [16, 15, 14], [19, 13, 17]]),
            (4 + 16 + 17, [1, 0, 2], [1, 0, 2]),
        ),
        (
            np.array([[2, 5, 7], [7, 10, 12], [1, 5, 9]]),
            (7 + 10 + 1, [2, 1, 0], [2, 1, 0]),
        ),
        # This triggered error in augmentation.
        (
            np.array(
                [[10, 6, 14, 1], [17, 18, 17, 15], [14, 17, 15, 8], [11, 13, 11, 4]]
            ),
            (6 + 17 + 14 + 4, [1, 2, 0, 3], [2, 0, 1, 3]),
        ),
        # Test matrix from centrosome
        (np.array([[10, 10, 13], [4, 8, 8], [8, 5, 8]]), (22.0, [2, 0, 1], [1, 2, 0])),
        # Test matrix from centrosome
        (np.array([[2, 5, 7], [7, 10, 12], [1, 5, 9]]), (18.0, [2, 1, 0], [2, 1, 0])),
    ],
)
def test_square(cost, expected):
    ret = lapmod(*sparse_from_dense(cost))
    assert len(ret) == len(expected)
    assert cost[range(cost.shape[0]), ret[1]].sum() == ret[0]
    assert cost[ret[2], range(cost.shape[1])].sum() == ret[0]
    assert ret[0] == expected[0]
    assert np.all(ret[1] == expected[1])
    assert np.all(ret[2] == expected[2])
    dense_ret = lapjv(cost)
    assert ret[0] == dense_ret[0]
    assert np.all(ret[1] == dense_ret[1])
    assert np.all(ret[2] == dense_ret[2])


@mark.parametrize(
    "cost,expected",
    [
        (
            np.array(
                [
                    [11.0, 20.0, np.inf, np.inf, np.inf],
                    [12.0, np.inf, 12.0, np.inf, np.inf],
                    [np.inf, 11.0, 10.0, 15.0, 9.0],
                    [15.0, np.inf, np.inf, 22.0, np.inf],
                    [13.0, np.inf, np.inf, np.inf, 15.0],
                ],
                dtype=float,
            ),
            (11 + 12 + 11 + 22 + 15, [0, 2, 1, 3, 4], [0, 2, 1, 3, 4]),
        ),
    ],
)
def test_sparse_square(cost, expected):
    ret = lapmod(*sparse_from_masked(cost))
    assert len(ret) == len(expected)
    assert cost[range(cost.shape[0]), ret[1]].sum() == ret[0]
    assert cost[ret[2], range(cost.shape[1])].sum() == ret[0]
    assert ret[0] == expected[0]
    assert np.all(ret[1] == expected[1])
    assert np.all(ret[2] == expected[2])
    dense_ret = lapjv(cost)
    assert ret[0] == dense_ret[0]
    assert np.all(ret[1] == dense_ret[1])
    assert np.all(ret[2] == dense_ret[2])


# This test triggers a possibly infinite loop in ARR.
@mark.timeout(60)
def test_infs_unsolvable():
    cost = np.array(
        [
            [0.0, 0.0, 0.0, np.inf, np.inf],
            [np.inf, np.inf, np.inf, 0.0, 0.0],
            [np.inf, np.inf, np.inf, 0.0, 0.0],
            [np.inf, np.inf, np.inf, 0.0, 0.0],
            [0.0, 0.0, 0.0, np.inf, np.inf],
        ],
        dtype=float,
    )
    lapjv_ret = lapjv(cost)
    assert lapjv_ret[0] == np.inf
    ret = lapmod(*sparse_from_masked(cost))
    assert len(ret) == 3
    assert ret[0] == np.inf

    cost = np.array(
        [
            [19.0, 22.0, 16.0, np.inf, np.inf],
            [np.inf, np.inf, np.inf, 4.0, 13.0],
            [np.inf, np.inf, np.inf, 3.0, 14.0],
            [np.inf, np.inf, np.inf, 10.0, 12.0],
            [11.0, 14.0, 13.0, np.inf, np.inf],
        ],
        dtype=float,
    )
    lapjv_ret = lapjv(cost)
    assert lapjv_ret[0] == np.inf
    ret = lapmod(*sparse_from_masked(cost))
    assert len(ret) == 3
    assert ret[0] == np.inf


def test_inf_unique():
    cost = np.array([[1000, 4, 1], [1, 1000, 3], [5, 1, 1000]])
    cost_ext = np.empty((4, 4))
    cost_ext[:] = np.inf
    cost_ext[:3, :3] = cost
    cost_ext[3, 3] = 0
    with raises(ValueError):
        ret = lapmod(*sparse_from_dense(cost_ext))
    ret = lapmod(*sparse_from_masked(cost_ext))
    assert len(ret) == 3
    assert ret[0] == 3.0
    assert np.all(ret[1] == [2, 0, 1, 3])


@mark.timeout(2)
def test_inf_col():
    cost = np.array(
        [
            [0.0, np.inf, 0.0, 0.0, np.inf],
            [np.inf, np.inf, 0.0, 0.0, 0.0],
            [np.inf, np.inf, np.inf, 0.0, np.inf],
            [np.inf, np.inf, np.inf, 0.0, 0.0],
            [0.0, np.inf, 0.0, np.inf, np.inf],
        ],
        dtype=float,
    )
    with raises(ValueError):
        ret = lapmod(*sparse_from_dense(cost))
    ret = lapmod(*sparse_from_masked(cost))
    assert len(ret) == 3
    assert ret[0] == np.inf


@mark.timeout(2)
def test_inf_row():
    cost = np.array(
        [
            [0.0, 0.0, 0.0, 0.0, np.inf],
            [np.inf, np.inf, 0.0, 0.0, 0.0],
            [np.inf, np.inf, np.inf, np.inf, np.inf],
            [np.inf, np.inf, np.inf, 0.0, 0.0],
            [0.0, 0.0, 0.0, np.inf, np.inf],
        ],
        dtype=float,
    )
    with raises(ValueError):
        ret = lapmod(*sparse_from_dense(cost))
    ret = lapmod(*sparse_from_masked(cost))
    assert len(ret) == 3
    assert ret[0] == np.inf


def test_all_inf():
    cost = np.empty((5, 5), dtype=float)
    cost[:] = np.inf
    with raises(ValueError):
        lapmod(*sparse_from_dense(cost))
    with raises(ValueError):
        lapmod(*sparse_from_masked(cost))


@fixture
def dense_8x8_int():
    return get_dense_8x8_int()


@fixture
def dense_100x100_int():
    return get_dense_100x100_int()


@fixture
def dense_100x100_int_hard():
    return get_dense_100x100_int_hard()


@fixture
def sparse_100x100_int():
    return get_sparse_100x100_int()


@fixture
def dense_1kx1k_int():
    return get_dense_1kx1k_int()


@fixture
def dense_1kx1k_int_hard():
    return get_dense_1kx1k_int_hard()


@fixture
def sparse_1kx1k_int():
    return get_sparse_1kx1k_int()


@fixture
def sparse_4kx4k_int():
    return get_sparse_4kx4k_int()


@fixture
def dense_eps():
    return get_dense_eps()


@mark.timeout(60)
def test_eps(dense_eps):
    cost, opt = dense_eps
    ret = lapmod(*sparse_from_dense(cost))
    assert len(ret) == 3
    assert ret[0] == opt


def test_dense_100x100_int(dense_100x100_int):
    cost, opt = dense_100x100_int
    ret = lapmod(*sparse_from_dense(cost))
    assert len(ret) == 3
    assert ret[0] == opt
    lapjv_ret = lapjv(cost)
    assert ret[0] == lapjv_ret[0]


def test_dense_100x100_int_hard(dense_100x100_int_hard):
    cost, opt = dense_100x100_int_hard
    ret = lapmod(*sparse_from_dense(cost))
    assert len(ret) == 3
    assert ret[0] == opt
    lapjv_ret = lapjv(cost)
    assert ret[0] == lapjv_ret[0]


# TODO: too sparse unsolvable matrices cause sometimne IndexError, easily
# generated - just set the mask threshold low enough
def test_sparse_100x100_int(sparse_100x100_int):
    cost, mask, opt = sparse_100x100_int
    ret = lapmod(*sparse_from_masked(cost, mask))
    assert len(ret) == 3
    assert ret[0] == opt


@mark.timeout(60)
def test_dense_1kx1k_int(dense_1kx1k_int):
    cost, opt = dense_1kx1k_int
    ret = lapmod(*sparse_from_dense(cost))
    assert len(ret) == 3
    assert ret[0] == opt
    lapjv_ret = lapjv(cost)
    assert ret[0] == lapjv_ret[0]


@mark.timeout(60)
def test_dense_1kx1k_int_hard(dense_1kx1k_int_hard):
    cost, opt = dense_1kx1k_int_hard
    ret = lapmod(*sparse_from_dense(cost))
    assert len(ret) == 3
    assert ret[0] == opt
    lapjv_ret = lapjv(cost)
    assert ret[0] == lapjv_ret[0]


@mark.timeout(60)
def test_sparse_1kx1k_int(sparse_1kx1k_int):
    cost, mask, opt = sparse_1kx1k_int
    ret = lapmod(*sparse_from_masked(cost, mask))
    assert len(ret) == 3
    assert ret[0] == opt
    cost[~mask] = get_platform_maxint()
    lapjv_ret = lapjv(cost)
    assert ret[0] == lapjv_ret[0]


@mark.timeout(60)
def test_sparse_4kx4k_int(sparse_4kx4k_int):
    cost, mask, opt = sparse_4kx4k_int
    ret = lapmod(*sparse_from_masked(cost, mask))
    assert len(ret) == 3
    assert ret[0] == opt
    cost[~mask] = get_platform_maxint()
    lapjv_ret = lapjv(cost)
    assert ret[0] == lapjv_ret[0]
