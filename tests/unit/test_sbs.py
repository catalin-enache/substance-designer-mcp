import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, cast

import pytest

from conftest import server


def test_graph_model(sbs_path: str) -> None:
    m = server._graph_model(sbs_path, 'alpha')
    n = m['nodes']
    assert n['200']['kind'] == 'instance:gradient_linear_1'
    assert n['200']['params'] == {'rotation': '0.25'}
    assert n['201']['kind'] == 'blend'
    assert n['201']['params'] == {'blendingmode': '6', 'opacitymult': 'function 22e2d023'}
    assert n['201']['links'] == {('source', '200')}
    assert n['201']['display'] == {('source', '200'): 'wire'}
    assert n['202']['kind'] == 'output'
    assert n['202']['display'] == {('inputNodeOutput', '201'): 'portal'}
    assert n['202']['pos'] == '200 0 0'
    assert m['inputs'] == {'roughness': '0.5'}
    assert m['size'] == {'outputsize': '0 0 (relative to parent)', 'defaultParentSize': '9x9'}


def test_graph_model_unknown_graph(sbs_path: str) -> None:
    with pytest.raises(server.ToolError, match="graph 'nope' not found"):
        server._graph_model(sbs_path, 'nope')


def test_diff_identical(sbs_path: str) -> None:
    m = server._graph_model(sbs_path, 'alpha')
    summary, lines = server._diff_models(m, copy.deepcopy(m), show_positions=True)
    assert lines == [] and summary == '0 added, 0 removed, 0 changed line(s), 0 node(s) moved'


def test_diff_every_kind_of_change(sbs_path: str) -> None:
    old = server._graph_model(sbs_path, 'alpha')
    new = copy.deepcopy(old)
    n = new['nodes']
    n['201']['params']['blendingmode'] = '3'  # changed
    n['201']['params']['opacity'] = '0.5'  # set from default
    del n['200']['params']['rotation']  # back to default
    n['201']['links'] = {('destination', '200')}  # one link removed, one added
    n['202']['display'][('inputNodeOutput', '201')] = 'wire'  # portal -> wire
    n['202']['pos'] = '300 0 0'  # moved
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


def test_diff_param_back_to_default(sbs_path: str) -> None:
    old = server._graph_model(sbs_path, 'alpha')
    new = copy.deepcopy(old)
    del new['nodes']['200']['params']['rotation']
    del new['inputs']['roughness']
    _, lines = server._diff_models(old, new, False)
    assert lines == ['~ node 200 instance:gradient_linear_1: rotation 0.25 -> (default)', '- graph input roughness']


@pytest.mark.parametrize(
    'graph, expected',
    [
        ('alpha', 9),
        ('beta', 11),
        ('pkg://beta', 11),
        (None, None),  # the two graphs disagree: no single size
        ('missing', None),
    ],
)
def test_default_parent_log2(sbs_path: str, graph: str | None, expected: int | None) -> None:
    assert server._default_parent_log2(sbs_path, graph) == expected


def test_default_parent_log2_not_an_sbs(tmp_path: Path, sbs_path: str) -> None:
    assert server._default_parent_log2(str(tmp_path / 'nope.sbs')) is None
    broken = tmp_path / 'broken.sbs'
    broken.write_text('<package><unclosed>')
    assert server._default_parent_log2(str(broken)) is None
    assert server._default_parent_log2(sbs_path.replace('.sbs', '.sbsar')) is None


def test_fixture_is_well_formed(sbs_path: str) -> None:
    assert [cast(ET.Element, g.find('identifier')).get('v') for g in ET.parse(sbs_path).getroot().iter('graph')] == [
        'alpha',
        'beta',
    ]


def test_sbsar_default_size(sbs_path: str) -> None:
    # cooked by sbscooker from a graph with an overridable size and a 512 px (9x9) default parent
    # size: the .sbsar keeps 256 px (8), not 512
    sbsar = sbs_path.replace('two_graphs.sbs', 'overridable_512.sbsar')
    assert server._sbsar_default_log2(sbsar) == 8
    assert server._sbsar_default_log2(sbsar, 'pkg://probe_size') == 8
    assert server._sbsar_default_log2(sbsar, 'other') is None
    assert server._sbsar_default_log2(sbs_path) is None  # not an archive


# ---- fixes from the review
def test_size_inheritance_labels(tmp_path: Path, sbs_path: str) -> None:
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


def test_diff_sees_a_link_moving_to_another_output(tmp_path: Path, sbs_path: str) -> None:
    tree = ET.parse(sbs_path)
    node = next(
        n
        for n in server._xml_graph(tree.getroot(), 'alpha', sbs_path).find('compNodes')
        if n.find('uid').get('v') == '201'
    )
    c = next(x for x in node.findall('connections/connection') if x.find('identifier').get('v') == 'source')
    ET.SubElement(c, 'connRefOutput').set('v', '777')
    path = tmp_path / 'other_output.sbs'
    tree.write(path)
    _summary, lines = server._diff_models(
        server._graph_model(sbs_path, 'alpha'), server._graph_model(str(path), 'alpha'), False
    )
    assert '~ node 201 blend: link source <- 200.777 added' in lines
    assert '~ node 201 blend: link source <- 200 removed' in lines


def test_select_links_ignores_function_graph_links(sbs_path: str) -> None:
    g = server._xml_graph(ET.parse(sbs_path).getroot(), 'alpha', sbs_path)
    chosen, _, total = server._select_links(g, 'portal', longer_than=1)
    assert total == 2  # source<-200 and inputNodeOutput<-201, not a<-1
    assert [c.find('identifier').get('v') for c in chosen] == ['source']  # the other is a portal already
    chosen, _, _ = server._select_links(g, 'wire', fanout_at_least=1)
    assert [c.find('identifier').get('v') for c in chosen] == ['inputNodeOutput']
    chosen, _, _ = server._select_links(g, 'portal', links=[['202', 'inputNodeOutput']])
    assert chosen == []  # already a portal: nothing to change
    chosen, _, _ = server._select_links(g, 'portal', from_nodes=['200'])
    assert [c.find('connRef').get('v') for c in chosen] == ['200']


def test_default_parent_sizes(sbs_path: str) -> None:
    assert server._default_parent_sizes(sbs_path) == {'alpha': 9, 'beta': 11}


def test_select_links_counts_selected_and_changed_apart(sbs_path: str) -> None:
    # REVIEW.md SRV-7: the messages said "N of N selected" (or "0 of 0"): the selection count
    # was lost once links already in the wanted mode were filtered out
    g = server._xml_graph(ET.parse(sbs_path).getroot(), 'alpha', sbs_path)
    chosen, selected, total = server._select_links(g, 'portal', longer_than=1)
    assert (len(chosen), selected, total) == (1, 2, 2)  # both selected, one is a portal already
    chosen, selected, total = server._select_links(g, 'portal', links=[['202', 'inputNodeOutput']])
    assert (len(chosen), selected) == (0, 1)


def test_links_of_a_graph_without_nodes() -> None:
    # REVIEW.md SRV-12: a graph without <compNodes> raised TypeError instead of counting 0 links
    import xml.etree.ElementTree as ET

    g = ET.fromstring('<graph><identifier v="g"/></graph>')
    assert server._select_links(g, 'portal', fanout_at_least=1) == ([], 0, 0)


def test_a_diff_names_the_output_of_a_link(tmp_path: Path) -> None:
    # REVIEW.md SRV-59: connRefOutput is a uid, so a rewired map read "<- 11.1102 added"; the name is in the source
    # node's outputBridging
    def model(output_uid: str) -> Any:
        path = tmp_path / (output_uid + '.sbs')
        path.write_text(
            '<package><content><graph><identifier v="g"/><compNodes>'
            '<compNode><uid v="11"/><compImplementation><compInstance><path v="pkg:///m"/><outputBridgings>'
            '<outputBridging><uid v="1101"/><identifier v="diffuse"/></outputBridging>'
            '<outputBridging><uid v="1102"/><identifier v="basecolor"/></outputBridging>'
            '</outputBridgings></compInstance></compImplementation></compNode>'
            '<compNode><uid v="21"/><connections><connection><identifier v="inputNodeOutput"/><connRef v="11"/>'
            '<connRefOutput v="%s"/></connection></connections>'
            '<compImplementation><compOutputBridge/></compImplementation></compNode>'
            '</compNodes></graph></content></package>' % output_uid
        )
        return server._graph_model(str(path), 'g')

    _, lines = server._diff_models(model('1101'), model('1102'), False)
    assert any('<- 11.basecolor added' in line for line in lines), lines
    assert any('<- 11.diffuse removed' in line for line in lines), lines
    # an output with no name stays its uid: an atomic node's
    _, lines = server._diff_models(model('1101'), model('777'), False)
    assert any('<- 11.777 added' in line for line in lines), lines


def _levels_with(tmp_path: Path, name: str, value_xml: str) -> str:
    """What _graph_model reads as a levels node's levelinlow, stored as this XML."""
    sbs = tmp_path / name
    sbs.write_text(
        '<package><content><graph><identifier v="g"/><compNodes><compNode><uid v="1"/><compImplementation><compFilter>'
        '<filter v="levels"/><parameters><parameter><name v="levelinlow"/><paramValue>%s</paramValue></parameter>'
        '</parameters></compFilter></compImplementation></compNode></compNodes></graph></content></package>' % value_xml
    )
    return cast(str, server._graph_model(str(sbs), 'g')['nodes']['1']['params']['levelinlow'])


def _function(root: str = '<rootnode v="7"/>', get: str = 'a', x: str = '0') -> str:
    return (
        '<dynamicValue>%s<paramNodes><paramNode><uid v="7"/><GUILayout><gpos v="%s 0 0"/></GUILayout>'
        '<function v="get_float4"/><funcDatas><funcData><constantValueString v="%s"/></funcData></funcDatas>'
        '</paramNode></paramNodes></dynamicValue>'
    ) % (root, x, get)


def test_diff_values_tell_functions_apart(tmp_path: Path) -> None:
    """REVIEW.md SRV-63: every function used to read 'function', so no change inside one showed."""
    base = _levels_with(tmp_path, 'a.sbs', _function())
    assert base.startswith('function')
    assert _levels_with(tmp_path, 'b.sbs', _function(get='b')) != base  # retargeted
    no_output = _levels_with(tmp_path, 'c.sbs', _function(root=''))
    assert no_output != base and 'no output' in no_output


def test_moving_a_function_node_is_no_change(tmp_path: Path) -> None:
    assert _levels_with(tmp_path, 'a.sbs', _function()) == _levels_with(tmp_path, 'b.sbs', _function(x='500'))


def test_a_diff_value_says_what_a_function_reads(tmp_path: Path) -> None:
    assert "reads 'a'" in _levels_with(tmp_path, 'a.sbs', _function())
    assert "reads 'b'" in _levels_with(tmp_path, 'b.sbs', _function(get='b'))


def test_each_paramset_of_an_fx_map_keeps_its_own_parameters(tmp_path: Path) -> None:
    """Same-named parameters of two paramsets used to overwrite each other, hiding a change in the first."""

    def paramset(uid: str, value: str) -> str:
        return (
            '<paramsGraphData><uid v="%s"/><type v="paramset"/><parameters><parameter><name v="opacity"/>'
            '<paramValue><constantValueFloat1 v="%s"/></paramValue></parameter></parameters></paramsGraphData>'
        ) % (uid, value)

    sbs = tmp_path / 'fx.sbs'
    sbs.write_text(
        '<package><content><graph><identifier v="g"/><compNodes><compNode><uid v="1"/><compImplementation><compFilter>'
        '<filter v="fxmaps"/><parameters><parameter><name v="colorswitch"/><paramValue><constantValueBool v="1"/>'
        '</paramValue></parameter></parameters><paramsGraphs><paramsGraph><paramsGraphDatas>%s%s</paramsGraphDatas>'
        '</paramsGraph></paramsGraphs></compFilter></compImplementation></compNode></compNodes></graph></content>'
        '</package>' % (paramset('7', '0.25'), paramset('8', '0.75'))
    )
    params = server._graph_model(str(sbs), 'g')['nodes']['1']['params']
    assert params['colorswitch'] == '1'
    assert params['paramset 7 opacity'] == '0.25' and params['paramset 8 opacity'] == '0.75'


def _filter_node(tmp_path: Path, name: str, body: str) -> dict[str, str]:
    sbs = tmp_path / name
    sbs.write_text(
        '<package><content><graph><identifier v="g"/><compNodes><compNode><uid v="1"/><compImplementation><compFilter>'
        '<filter v="f"/>%s</compFilter></compImplementation></compNode></compNodes></graph></content></package>' % body
    )
    return cast('dict[str, str]', server._graph_model(str(sbs), 'g')['nodes']['1']['params'])


def _gradient(*positions: str) -> str:
    cells = ''.join(
        '<paramsArrayCell><uid v="%d"/><parameters><parameter><name v="position"/><paramValue>'
        '<constantValueFloat1 v="%s"/></paramValue></parameter></parameters></paramsArrayCell>' % (i, position)
        for i, position in enumerate(positions)
    )
    return (
        '<paramsArrays><paramsArray><name v="gradientrgba"/><uid v="9"/><paramsArrayCells>%s</paramsArrayCells>'
        '</paramsArray></paramsArrays>' % cells
    )


def test_each_gradient_key_counts(tmp_path: Path) -> None:
    """REVIEW.md SRV-66: same-named keys overwrote each other, so only the last one was compared."""
    base = _filter_node(tmp_path, 'a.sbs', _gradient('0.1', '0.9'))
    assert base == {'gradientrgba cells': '2', 'gradientrgba[0] position': '0.1', 'gradientrgba[1] position': '0.9'}
    assert _filter_node(tmp_path, 'b.sbs', _gradient('0.2', '0.9')) != base  # the first key moved
    assert _filter_node(tmp_path, 'c.sbs', _gradient('0.9'))['gradientrgba cells'] == '1'  # one deleted


def _fx_graph(link: str = '', root: str = '<rootnode v="10"/>') -> str:
    return (
        '<paramsGraphs><paramsGraph><uid v="5"/>%s<paramsGraphDatas><paramsGraphData><uid v="11"/><type v="paramset"/>'
        '<parameters><parameter><name v="opacity"/><paramValue><constantValueFloat1 v="0.5"/></paramValue></parameter>'
        '</parameters></paramsGraphData></paramsGraphDatas><paramsGraphNodes><paramsGraphNode><uid v="10"/>'
        '<GUILayout><gpos v="0 0 0"/></GUILayout><type v="paramset"/><data v="11"/>%s</paramsGraphNode>'
        '</paramsGraphNodes></paramsGraph></paramsGraphs>'
    ) % (root, link)


def test_an_fx_map_parameter_uses_the_id_describe_graph_prints(tmp_path: Path) -> None:
    """REVIEW.md SRV-68: measured, an inner node's getIdentifier() is the file's node uid, not its data's."""
    assert _filter_node(tmp_path, 'a.sbs', _fx_graph())['paramset 10 opacity'] == '0.5'


def test_an_fx_map_wiring_change_shows(tmp_path: Path) -> None:
    """REVIEW.md SRV-67."""
    base = _filter_node(tmp_path, 'a.sbs', _fx_graph())
    assert _filter_node(tmp_path, 'b.sbs', _fx_graph(link='<connections><connection/></connections>')) != base
    assert _filter_node(tmp_path, 'c.sbs', _fx_graph(root='<rootnode v="11"/>')) != base
    moved = _fx_graph().replace('0 0 0', '5 5 0')
    assert _filter_node(tmp_path, 'd.sbs', moved) == base


def test_a_node_size_parameters_inheritance_shows(tmp_path: Path) -> None:
    """REVIEW.md SRV-69, HLP-74: the same value at another inheritance is another size."""

    def size(relative: str) -> str:
        return (
            '<parameters><parameter><name v="outputsize"/>%s<paramValue><constantValueInt2 v="3 3"/></paramValue>'
            '</parameter></parameters>' % relative
        )

    absolute = _filter_node(tmp_path, 'a.sbs', size('<relativeTo v="0"/>'))['outputsize']
    relative = _filter_node(tmp_path, 'b.sbs', size(''))['outputsize']
    assert absolute != relative and 'absolute' in absolute


def test_a_float_parameters_relative_to_is_no_noise(tmp_path: Path) -> None:
    body = '<parameters><parameter><name v="luminance"/><relativeTo v="0"/><paramValue><constantValueFloat1 v="0.5"/></paramValue></parameter></parameters>'
    assert _filter_node(tmp_path, 'a.sbs', body)['luminance'] == '0.5'


def test_a_resource_paths_package_id_is_no_change(tmp_path: Path) -> None:
    """REVIEW.md SRV-70: the id differs after a reload, so a diff reported a bitmap as changed with no edit."""
    value = '<constantValueString v="pkg:///bitmap?dependency=%s"/>'
    assert (
        _levels_with(tmp_path, 'a.sbs', value % '1') == _levels_with(tmp_path, 'b.sbs', value % '2') == 'pkg:///bitmap'
    )
