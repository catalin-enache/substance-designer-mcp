import pytest

from conftest import patch_server, server
from server_tools.discovery import _FunctionEntry, _LibraryEntry, _LibraryIndex


def _entry(
    file: str, graph: str, label: str = '', category: str = '', description: str = '', hidden: bool = False
) -> _LibraryEntry:
    return {
        'file': file,
        'graph': graph,
        'label': label,
        'category': category,
        'description': description,
        'hidden': hidden,
        'url': graph,
    }


def _function(name: str, label: str, description: str) -> _FunctionEntry:
    return {'definition': 'sbs::function::' + name, 'label': label, 'description': description}


@pytest.fixture(autouse=True)
def library(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fake library index, so search_nodes never asks Designer."""
    cache: _LibraryIndex = {
        'atomic': ['sbs::compositing::levels', 'sbs::compositing::blend', 'sbs::compositing::blur'],
        'entries': [
            _entry('levels_plus.sbs', 'levels_plus', 'Levels plus', 'Filter', 'More levels'),
            _entry('auto_levels.sbs', 'auto_levels', 'Auto Levels', 'Filter', '<b>Stretches</b>\n the  range'),
            _entry(
                'slope_blur.sbs',
                'slope_blur_grayscale_2',
                'Slope Blur Grayscale',
                'Filter',
                'Directional blur driven by levels of slope',
            ),
            _entry('secret.sbs', 'secret_levels', 'Secret levels', 'Filter', hidden=True),
            # holds "add" in its name, listed before the function nodes: ranked by its name, it comes after add
            _entry('add_noise.sbs', 'add_noise', 'Add Noise', 'Filter', 'Adds noise'),
        ],
        'pkg_dir': '/nowhere',
        # Designer's function nodes, as its sbs::function module describes them
        'functions': [
            _function('add', 'Add', 'The <b>Add</b> function adds two same type values: A+B'),
            _function(
                'lr',
                'Lower',
                'The <b>Lower</b> function returns true if first entry is lower than second entry: A&lt;B',
            ),
            _function('samplecol', 'Sample color', 'Returns the color pixel value of input image.'),
            # "gray" in its label alone
            _function('samplelum', 'Sample Gray', 'Returns the luminance pixel value of input image.'),
        ],
    }
    patch_server(monkeypatch, '_LIBRARY_CACHE', cache)


def _names(text: str) -> list[str]:
    return [line.split()[1] for line in text.splitlines() if not line.startswith('...')]


def test_exact_atomic_name_ranks_first() -> None:
    out = server.search_nodes('levels')
    assert out.splitlines()[0].startswith('atomic   levels')
    # exact, then prefix, then all words in the name, then description-only
    assert _names(out) == ['levels', 'Levels', 'Auto', 'Slope']


def test_definition_formats() -> None:
    out = server.search_nodes('levels')
    assert "definition='levels_plus'" in out  # graph named like its file
    assert "definition='slope_blur.sbs/slope_blur_grayscale_2'" in out  # graph inside another file


def test_description_html_is_flattened() -> None:
    assert '[Filter]  Stretches the range' in server.search_nodes('auto levels')


def test_all_words_must_match() -> None:
    assert _names(server.search_nodes('slope directional')) == ['Slope']
    assert server.search_nodes('slope nothing') == "No node types match 'slope nothing'."


def test_hidden_entries() -> None:
    assert (
        server.search_nodes('secret')
        == "No node types match 'secret'. 1 hidden graph(s) match too: include_hidden=True"
    )
    shown = server.search_nodes('secret', include_hidden=True)
    assert "definition='secret.sbs/secret_levels'" in shown and 'Secret levels' in shown


def test_limit() -> None:
    out = server.search_nodes('levels', limit=2)
    assert len(out.splitlines()) == 3 and out.endswith('... 2 more (refine the query or raise limit)')


def test_a_function_node_is_found_by_its_description_or_its_label() -> None:
    # the definition describe_node takes, and the description flattened as a library graph's, its entities read as the
    # characters they stand for (REVIEW.md HLP-246). "than" is in lr's description alone, and of the entries holding
    # "sample", "gray" is in samplelum's label alone (TST-755)
    lower = server.search_nodes('lower than')
    assert lower == (
        "function lr                           definition='sbs::function::lr'  [Lower]  The Lower function returns true "
        'if first entry is lower than second entry: A<B'
    )
    assert _names(server.search_nodes('sample gray')) == ['samplelum']


def test_a_function_nodes_exact_name_ranks_first() -> None:
    # Add Noise is listed first, and "add" starts its name: add ranks first by its exact name (REVIEW.md TST-755)
    assert _names(server.search_nodes('add')) == ['add', 'Add']
