"""Runs inside Designer (run_designer_script), for functions' "designer facts" checks (checks.py): every definition of
the `sbs::function` module, printed as one line of JSON, `DEFINITIONS={id: {'inputs': [...], 'outputs': [...]}}`.
Each input is {'id', 'types', 'connectable'} and each output {'id', 'types'}, the types read with getTypes():
getType() gives only the first of them. Then, a line each as `<what> | <value>`: the definitions whose label is None
or empty, and those whose description is."""

import json
from typing import cast

import sd
from sd.api.sdmodule import SDModule
from sd.api.sdproperty import SDProperty, SDPropertyCategory

module = cast(SDModule, sd.getContext().getSDApplication().getModuleMgr().getModuleFromId('sbs::function'))
found = module.getDefinitions()


def types(prop: SDProperty) -> list[str]:
    return [t.getId() for t in prop.getTypes()]


definitions = {
    d.getId(): {
        'inputs': [
            {'id': p.getId(), 'types': types(p), 'connectable': p.isConnectable()}
            for p in d.getProperties(SDPropertyCategory.Input) or []
        ],
        'outputs': [{'id': p.getId(), 'types': types(p)} for p in d.getProperties(SDPropertyCategory.Output) or []],
    }
    for d in found
}
print('DEFINITIONS=' + json.dumps(definitions, sort_keys=True))
print('with no label | %s' % sorted(d.getId() for d in found if not d.getLabel()))
print('with no description | %s' % sorted(d.getId() for d in found if not d.getDescription()))
