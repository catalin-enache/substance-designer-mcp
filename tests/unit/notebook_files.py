"""Jupyter notebooks written for the tests of the hook that sizes PyCharm's `read_file` of one (REVIEW.md AGT-46)."""

import json
from pathlib import Path
from typing import TypedDict


class Output(TypedDict):
    """A code cell's output, of a stream."""

    name: str
    output_type: str
    text: list[str]


class Cell(TypedDict, total=False):
    """A notebook's cell. A test writes one with only the keys the hook reads, and a source that isn't text."""

    cell_type: str
    id: str
    metadata: dict[str, list[str]]
    source: object  # text, or a list of texts: the test of a source the hook can't read passes a number
    execution_count: int
    outputs: list[Output]


class Notebook(TypedDict):
    """A notebook in Jupyter's format 4."""

    cells: list[Cell]
    metadata: dict[str, object]
    nbformat: int
    nbformat_minor: int


def write_notebook(path: Path, *cells: Cell) -> Path:
    """A notebook of `cells` at `path`, as Jupyter writes one in its format 4."""
    notebook: Notebook = {'cells': list(cells), 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
    path.write_text(json.dumps(notebook, ensure_ascii=False), encoding='utf-8')
    return path


def cell(kind: str, source: str | list[str]) -> Cell:
    """A notebook's cell, with metadata and, for code, an output: read_file shows neither (measured 2026-11-19)."""
    made: Cell = {'cell_type': kind, 'id': kind, 'metadata': {'tags': ['not shown']}, 'source': source}
    if kind == 'code':
        made['execution_count'] = 1
        made['outputs'] = [{'name': 'stdout', 'output_type': 'stream', 'text': ['not shown\n']}]
    return made
