"""The C cosine extension returns correct values."""

import array

import pytest

import csim


def cos(a, b):
    return csim.cosine(array.array("d", a), array.array("d", b))


def test_identical_vectors():
    assert cos([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


def test_orthogonal_vectors():
    assert cos([1, 0], [0, 1]) == pytest.approx(0.0)


def test_known_value():
    # cosine([1,2,3], [3,2,1]) = 10 / 14
    assert cos([1, 2, 3], [3, 2, 1]) == pytest.approx(10 / 14)


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        cos([1, 2], [1, 2, 3])


def test_zero_vector_raises():
    with pytest.raises(ValueError):
        cos([0, 0, 0], [1, 2, 3])
