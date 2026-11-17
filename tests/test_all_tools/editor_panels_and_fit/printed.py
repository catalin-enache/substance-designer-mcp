"""Reads back what editor_panels_and_fit's snippets print: a value printed with %r, and the shapes the checks expect of
it. It sits beside checks.py, so that checks.py keeps to its checks (REVIEW.md TST-484)."""

import ast
import re
from types import EllipsisType
from typing import TypeGuard

# a value a snippet printed with %r, as ast.literal_eval reads it back
Printed = (
    str
    | bytes
    | int
    | float
    | complex
    | bool
    | EllipsisType
    | None
    | tuple['Printed', ...]
    | list['Printed']
    | dict['Printed', 'Printed']
    | set['Printed']
)


def read_value(said: str, name: str) -> Printed:
    """The value a snippet printed as NAME=<repr>, or None."""
    found = re.search(r'^%s=(.*)$' % name, said, re.M)
    value: Printed = ast.literal_eval(found.group(1)) if found else None
    return value


# The shapes the snippets print. Each predicate tests the outer type only, and takes the items as printed.


def is_events(value: Printed) -> TypeGuard[list[tuple[str, int | None]]]:
    """Whether `value` is a list, as FRAMES' events are: (kind, its count or None) each."""
    return isinstance(value, list)


def is_counts(value: Printed) -> TypeGuard[list[int | None]]:
    """Whether `value` is a list, as FRAMES' counts are: an int or None each."""
    return isinstance(value, list)


def is_asks_hidden(value: Printed) -> TypeGuard[tuple[bool, list[tuple[str, ...]]]]:
    """Whether `value` is a tuple starting with True, as HIDDEN_ASKS is when Designer was hidden: (True, FRAMES' kinds
    of events after each pan)."""
    return isinstance(value, tuple) and value[0] is True


def is_pairs(value: Printed) -> TypeGuard[list[tuple[int | None, int | None]]]:
    """Whether `value` is a list, as READ is: (the count as Designer was hidden, the count as the wait ended) each."""
    return isinstance(value, list)
