import copy
import xml.etree.ElementTree as ET

import pytest

from conftest import server


def test_graph_model(sbs_path):
    m = server._graph_model(sbs_path, 'alpha')
    n = m['nodes']
    assert n['200']['kind'] == 'instance:gradient_linear_1'
    assert n['200']['params'] == {'rotation': '0.25'}
    assert n['201']['kind'] == 'blend'
    assert n['201']['params'] == {'blendingmode': '6', 'opacitymult': 'function'}
    assert n['201']['links'] == {('source', '200')}
    assert n['201']['display'] == {('source', '200'): 'wire'}
    assert n['202']['kind'] == 'output'
    assert n['202']['display'] == {('inputNodeOutput', '201'): 'portal'}
    assert n['202']['pos'] == '200 0 0'
    assert m['inputs'] == {'roughness': '0.5'}
    assert m['size'] == {'outputsize': '0 0 (relative to parent)', 'defaultParentSize': '9x9'}


def test_graph_model_unknown_graph(sbs_path):
    with pytest.raises(server.ToolError, match="graph 'nope' not found"):
        server._graph_model(sbs_path, 'nope')


def test_diff_identical(sbs_path):
    m = server._graph_model(sbs_path, 'alpha')
    summary, lines = server._diff_models(m, copy.deepcopy(m), show_positions=True)
    assert lines == [] and summary == '0 added, 0 removed, 0 changed line(s), 0 node(s) moved'


def test_diff_every_kind_of_change(sbs_path):
    old = server._graph_model(sbs_path, 'alpha')
    new = copy.deepcopy(old)
    n = new['nodes']
    n['201']['params']['blendingmode'] = '3'                    # changed
    n['201']['params']['opacity'] = '0.5'                       # set from default
    del n['200']['params']['rotation']                          # back to default
    n['201']['links'] = {('destination', '200')}                # one link removed, one added
    n['202']['display'][('inputNodeOutput', '201')] = 'wire'    # portal -> wire
    n['202']['pos'] = '300 0 0'                                 # moved
    n['999'] = {'kind': 'levels', 'params': {}, 'links': set(), 'display': {}, 'pos': ''}
    new['inputs'] = {'roughness': '0.7', 'metal': '1'}
    new['size']['defaultParentSize'] = '11x11'
    del n['200']
    summary, lines = server._diff_models(old, new, show_positions=False)
    assert summary == '1 added, 1 removed, 7 changed line(s), 1 node(s) moved'
    assert lines == [
        '+ node 999 levels',
        '- node 200 instance:gradient_linear_1',
        '~ node 201 blend: blendingmode 6 -> 3',
        '~ node 201 blend: opacity (default) -> 0.5',
        '~ node 201 blend: link destination <- 200 added',
        '~ node 201 blend: link source <- 200 removed',
        '~ node 202 output: link inputNodeOutput <- 201 shown as wire (was portal)',
        '+ graph input metal = 1',
        '~ graph input roughness: 0.5 -> 0.7',
        '~ graph defaultParentSize: 9x9 -> 11x11',
    ]
    _, with_pos = server._diff_models(old, new, show_positions=True)
    assert '~ node 202 output: moved 200 0 0 -> 300 0 0' in with_pos


def test_diff_param_back_to_default(sbs_path):
    old = server._graph_model(sbs_path, 'alpha')
    new = copy.deepcopy(old)
    del new['nodes']['200']['params']['rotation']
    del new['inputs']['roughness']
    _, lines = server._diff_models(old, new, False)
    assert lines == ['~ node 200 instance:gradient_linear_1: rotation 0.25 -> (default)', '- graph input roughness']


@pytest.mark.parametrize('graph, expected', [('alpha', 9), ('beta', 11), ('pkg://beta', 11),
                                             (None, None),     # the two graphs disagree: no single size
                                             ('missing', None)])
def test_default_parent_log2(sbs_path, graph, expected):
    assert server._default_parent_log2(sbs_path, graph) == expected


def test_default_parent_log2_not_an_sbs(tmp_path, sbs_path):
    assert server._default_parent_log2(str(tmp_path / 'nope.sbs')) is None
    broken = tmp_path / 'broken.sbs'
    broken.write_text('<package><unclosed>')
    assert server._default_parent_log2(str(broken)) is None
    assert server._default_parent_log2(sbs_path.replace('.sbs', '.sbsar')) is None


def test_fixture_is_well_formed(sbs_path):
    assert [g.find('identifier').get('v') for g in ET.parse(sbs_path).getroot().iter('graph')] == ['alpha', 'beta']


def test_sbsar_default_size(sbs_path):
    # cooked by sbscooker from a graph with an overridable size and a 512 px (9x9) default parent
    # size: the .sbsar keeps 256 px (8), not 512
    sbsar = sbs_path.replace('two_graphs.sbs', 'overridable_512.sbsar')
    assert server._sbsar_default_log2(sbsar) == 8
    assert server._sbsar_default_log2(sbsar, 'pkg://probe_size') == 8
    assert server._sbsar_default_log2(sbsar, 'other') is None
    assert server._sbsar_default_log2(sbs_path) is None                  # not an archive


# ---- fixes from the review
def test_size_inheritance_labels(tmp_path, sbs_path):
    # measured in Designer 16: 0 absolute, 1 relative to parent, 2 relative to input; a graph's
    # default (relative to parent) isn't stored
    assert server._graph_model(sbs_path, 'beta')['size']['outputsize'] == '(default: relative to parent)'
    for code, label in (('0', 'absolute'), ('2', 'relative to input')):
        tree = ET.parse(sbs_path)
        g = server._xml_graph(tree.getroot(), 'alpha', sbs_path)
        g.find('baseParameters/parameter/relativeTo').set('v', code)
        path = tmp_path / ('size_%s.sbs' % code)
        tree.write(path)
        assert server._graph_model(str(path), 'alpha')['size']['outputsize'] == '0 0 (%s)' % label


def test_diff_sees_a_link_moving_to_another_output(tmp_path, sbs_path):
    tree = ET.parse(sbs_path)
    node = next(n for n in server._xml_graph(tree.getroot(), 'alpha', sbs_path).find('compNodes')
                if n.find('uid').get('v') == '201')
    c = next(x for x in node.findall('connections/connection') if x.find('identifier').get('v') == 'source')
    ET.SubElement(c, 'connRefOutput').set('v', '777')
    path = tmp_path / 'other_output.sbs'
    tree.write(path)
    summary, lines = server._diff_models(server._graph_model(sbs_path, 'alpha'),
                                         server._graph_model(str(path), 'alpha'), False)
    assert '~ node 201 blend: link source <- 200.777 added' in lines
    assert '~ node 201 blend: link source <- 200 removed' in lines


def test_select_links_ignores_function_graph_links(sbs_path):
    g = server._xml_graph(ET.parse(sbs_path).getroot(), 'alpha', sbs_path)
    chosen, total = server._select_links(g, 'portal', longer_than=1)
    assert total == 2                                    # source<-200 and inputNodeOutput<-201, not a<-1
    assert [c.find('identifier').get('v') for c in chosen] == ['source']   # the other is a portal already
    chosen, _ = server._select_links(g, 'wire', fanout_at_least=1)
    assert [c.find('identifier').get('v') for c in chosen] == ['inputNodeOutput']
    chosen, _ = server._select_links(g, 'portal', links=[['202', 'inputNodeOutput']])
    assert chosen == []                                  # already a portal: nothing to change
    chosen, _ = server._select_links(g, 'portal', from_nodes=['200'])
    assert [c.find('connRef').get('v') for c in chosen] == ['200']


def test_default_parent_sizes(sbs_path):
    assert server._default_parent_sizes(sbs_path) == {'alpha': 9, 'beta': 11}
