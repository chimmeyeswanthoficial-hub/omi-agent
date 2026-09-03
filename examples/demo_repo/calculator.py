"""Tiny demo package with exactly ONE planted bug: add()."""


def add(a: int, b: int) -> int:
    return a - b  # BUG: should be a + b


def sub(a: int, b: int) -> int:
    return a - b


def mul(a: int, b: int) -> int:
    return a * b
