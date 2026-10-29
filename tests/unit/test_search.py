import pytest

from conftest import server


def _entry(file, graph, label='', category='', description='', hidden=False):
    return {'file': file, 'graph': graph, 'label': label, 'category': category,
            'description': description, 'hidden': hidden}


@pytest.fixture(autouse=True)
def library(monkeypatch):
    """A fake library index, so search_nodes never asks Designer."""
    cache = {'atomic': ['sbs::compositing::levels', 'sbs::compositing::blend', 'sbs::compositing::blur'],
             'entries': [
                 _entry('levels_plus.sbs', 'levels_plus', 'Levels plus', 'Filter', 'More levels'),
                 _entry('auto_levels.sbs', 'auto_levels', 'Auto Levels', 'Filter', '<b>Stretches</b>\n the  range'),
                 _entry('slope_blur.sbs', 'slope_blur_grayscale_2', 'Slope Blur Grayscale', 'Filter',
                        'Directional blur driven by levels of slope'),
                 _entry('secret.sbs', 'secret_levels', 'Secret levels', 'Filter', hidden=True),
             ], 'pkg_dir': '/nowhere'}
    monkeypatch.setattr(server, '_LIBRARY_CACHE', cache)


def _names(text):
    return [line.split()[1] for line in text.splitlines() if not line.startswith('...')]


def test_exact_atomic_name_ranks_first():
    out = server.search_nodes('levels')
    assert out.splitlines()[0].startswith("atomic   levels")
    # exact, then prefix, then all words in the name, then description-only
    assert _names(out) == ['levels', 'Levels', 'Auto', 'Slope']


def test_definition_formats():
    out = server.search_nodes('levels')
    assert "definition='levels_plus'" in out                                 # graph named like its file
    assert "definition='slope_blur.sbs/slope_blur_grayscale_2'" in out       # graph inside another file


def test_description_html_is_flattened():
    assert '[Filter]  Stretches the range' in server.search_nodes('auto levels')


def test_all_words_must_match():
    assert _names(server.search_nodes('slope directional')) == ['Slope']
    assert server.search_nodes('slope nothing') == "No node types match 'slope nothing'."


def test_hidden_entries():
    assert server.search_nodes('secret') == "No node types match 'secret'."
    assert "definition='secret'" not in server.search_nodes('secret', include_hidden=True)
    assert 'Secret levels' in server.search_nodes('secret', include_hidden=True)


def test_limit():
    out = server.search_nodes('levels', limit=2)
    assert len(out.splitlines()) == 3 and out.endswith('... 2 more (refine the query or raise limit)')
