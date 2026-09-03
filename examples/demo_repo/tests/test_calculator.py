import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator import add, mul, sub


def test_add():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, 1) == 0


def test_sub():
    assert sub(5, 2) == 3


def test_mul():
    assert mul(3, 4) == 12
