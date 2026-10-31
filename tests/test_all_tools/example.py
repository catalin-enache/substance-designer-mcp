"""README's full example: examples/build_dwarf_trimsheet.py, renamed so it can't touch a trim sheet
you have open (it closes earlier builds of its graph id) and saved to the scratch folder."""

import os
import re

from .common import BUNDLE, EXAMPLE_GRAPH, GRAPH_OF, TEST_GRAPH, Ctx, check, helpers_source, text


async def run(ctx: Ctx) -> None:
    c, scratch = ctx.c, ctx.scratch
    # --- README's full example: examples/build_dwarf_trimsheet.py, renamed so it can't touch
    # a trim sheet you have open (it closes earlier builds of its graph id) and saved to scratch
    E = 'example script'
    with open(os.path.join(BUNDLE, 'examples', 'build_dwarf_trimsheet.py')) as f:
        source = f.read()
    example_sbs = os.path.join(scratch, 'example', EXAMPLE_GRAPH + '.sbs')
    source, n_out = re.subn(r'^OUT_SBS = .*$', 'OUT_SBS = %r' % example_sbs, source, flags=re.M)
    source, n_id = re.subn(r'^GRAPH_ID = .*$', 'GRAPH_ID = %r' % EXAMPLE_GRAPH, source, flags=re.M)
    if (n_out, n_id) != (1, 1):
        check(E, 'output path and graph id can be redirected', False, 'OUT_SBS/GRAPH_ID lines changed?')
    else:
        # a run that fails before its first save closes its own unsaved package, so failed
        # runs don't pile up packages with the graph's name (REVIEW.md INS-13), also when it
        # fails while setting the package up (INS-17)
        for where, old, new in (
            ('in the build', '\n    b.layout()\n', "\n    raise RuntimeError('fails on purpose')\n"),
            ('setting up', 'self._set_graph_size()\n', "raise RuntimeError('fails on purpose')\n"),
        ):
            failing = os.path.join(scratch, 'build_example_failing.py')
            with open(failing, 'w') as f:
                f.write(source.replace(old, new, 1))
            r_ = await c('run_designer_script', {'path': failing, 'timeout_s': 300})
            t = text(
                await c(
                    'execute_designer_code',
                    {
                        'code': (
                            'import sd\npm = sd.getContext().getSDApplication().getPackageMgr()\n'
                            "print('UNSAVED_LEFT=%%d' %% sum(1 for p in pm.getUserPackages() if not p.getFilePath() and "
                            'any(r.getIdentifier() == %r for r in p.getChildrenResources(False))))'
                        )
                        % EXAMPLE_GRAPH
                    },
                )
            )
            ran = text(r_)  # a script's traceback comes back as text, not a tool error
            check(
                E,
                'a run failing %s closes its own unsaved package' % where,
                old in source and 'fails on purpose' in ran and 'UNSAVED_LEFT=0' in t,
                t.strip() + ' | ' + ran.strip()[-160:],
            )
        example = os.path.join(scratch, 'build_example.py')
        with open(example, 'w') as f:
            f.write(source)
        t = text_build = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
        check(
            E,
            'builds and saves',
            'Saved trim sheet to' in t and 'ERROR' not in t and 'WARNING' not in t and os.path.isfile(example_sbs),
            t[-300:],
        )
        # the readable-graph finish (ROADMAP item, now in the script): a frame per
        # section, overridable size, portals written into the saved file
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': GRAPH_OF % EXAMPLE_GRAPH
                    + (
                        'from sd.api.sdgraphobjectframe import SDGraphObjectFrame\n'
                        'from sd.api.sdproperty import SDPropertyCategory\n'
                        "p=g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)\n"
                        "print('FRAMES=%d SIZE=%s PARENT=%d' % (sum(isinstance(o, SDGraphObjectFrame) for o in g.getGraphObjects()),"
                        ' g.getPropertyInheritanceMethod(p).name, g.getDefaultParentSize().x))'
                    )
                },
            )
        )
        check(E, 'frames per section, overridable 2048 size', 'FRAMES=17 SIZE=RelativeToParent PARENT=2048' in t, t)
        with open(example_sbs, encoding='utf-8') as f:
            portals = len(re.findall(r'<displayType v="1"\s*/>', f.read()))
        reported = re.search(r'(\d+) of (\d+) links as portals', text_build)
        check(
            E,
            'long links between sections saved as portals',
            reported is not None and portals == int(reported.group(1)) > 0,
            '%d in the file; %s' % (portals, reported.group(0) if reported else 'no count printed'),
        )
        # a section larger than the view: fitting it zooms out below 100 %
        t = text(await c('open_graph', {'graph': EXAMPLE_GRAPH, 'frame': 'K: wood planks'}))
        m = re.search(r'zoom (\d+)%', t)
        check('open_graph', 'a large frame zooms out to fit', m is not None and 5 < int(m.group(1)) < 100, t)
        await c('open_graph', {'graph': EXAMPLE_GRAPH})  # so you can see it
        t = text(
            await c('export_outputs', {'graph': EXAMPLE_GRAPH, 'output_dir': os.path.join(scratch, 'example_maps')})
        )
        names = ('basecolor', 'normal', 'roughness', 'metallic', 'height', 'ambientocclusion')
        check(E, '6 maps at 2048', 'exported 6 file(s)' in t and all('%s.png  2048x2048' % m in t for m in names), t)
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': (
                        'import sd\ng=[r for p in sd.getContext().getSDApplication().getPackageMgr().getUserPackages() '
                        "for r in p.getChildrenResources(False) if r.getIdentifier()=='%s'][0]\n"
                        "print(' '.join('%%s=%%s' %% (n.getAnnotationPropertyValueFromId('identifier').get(), n.getIdentifier()) "
                        'for n in g.getOutputNodes()))'
                    )
                    % EXAMPLE_GRAPH
                },
            )
        )
        outs = dict(re.findall(r'(\w+)=(\d+)', t))
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': GRAPH_OF % EXAMPLE_GRAPH
                    + (
                        "n=g.getNodeFromId(%r)\nu=n.getAnnotationPropertyValueFromId('usages').get()[0].get()\n"
                        "print('USAGE=%%s %%s %%s' %% (u.getName(), u.getComponents(), u.getColorSpace()))"
                    )
                    % outs.get('basecolor', '0')
                },
            )
        )
        check('designer facts', 'output usages read back (baseColor RGBA sRGB)', 'USAGE=baseColor RGBA sRGB' in t, t)
        t = text(
            await c(
                'check_tiling', {'node_id': outs.get('basecolor', '?'), 'graph': EXAMPLE_GRAPH, 'axis': 'horizontal'}
            )
        )
        ratio = re.search(r'ratio ([\d.]+)', t)
        check(
            E, 'tiles horizontally (trim sheet)', ratio is not None and float(ratio.group(1)) <= 3, t.splitlines()[-1]
        )
        await c('open_graph', {'graph': TEST_GRAPH})
        # the fit refuses to zoom a view that shows another graph (here: fit the trim
        # sheet's frame while the self-test graph is in the editor, via the helper itself)
        helpers = helpers_source()
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': helpers
                    + (
                        "\ntry:\n    _fit_view_to(find_graph(%r), frame='K: wood planks')\n    print('FITTED')\n"
                        "except RuntimeError as e:\n    print('REFUSED', e)\n"
                    )
                    % EXAMPLE_GRAPH
                },
            )
        )
        check(
            'open_graph',
            'never fits a view showing another graph',
            'REFUSED' in t and 'not %s' % EXAMPLE_GRAPH in t,
            t.strip()[-200:],
        )

        # re-running the example never discards edits (REVIEW.md INS-8): a copy of its
        # graph saved elsewhere and edited is left open, and unsaved edits to the
        # previous build make it refuse instead of unloading them
        decoy_sbs = os.path.join(scratch, 'example', 'my_copy.sbs')
        edit_both = GRAPH_OF % EXAMPLE_GRAPH + (
            'pm=sd.getContext().getSDApplication().getPackageMgr()\npm.saveCopyOfPackageAs(g.getPackage(), %r)\n'
            "copy=pm.loadUserPackage(%r)\ncopy.getChildrenResources(False)[0].newNode('sbs::compositing::blur')\n"
            "print('DECOY_MODIFIED=%%s' %% copy.isModified())"
        ) % (decoy_sbs, decoy_sbs)
        state = (
            'import os\n'
            + GRAPH_OF.replace('[0]\n', '\n') % EXAMPLE_GRAPH
            + (
                "print('OPEN=' + ','.join('%s:%s' % (os.path.basename(r.getPackage().getFilePath() or '-'), "
                'r.getPackage().isModified()) for r in g))'
            )
        )
        t = text(await c('execute_designer_code', {'code': edit_both}))
        t = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
        after = text(await c('execute_designer_code', {'code': state}))
        check(
            E,
            'a re-run leaves an edited copy elsewhere open',
            'Saved trim sheet to' in t and 'my_copy.sbs:True' in after,
            t.strip()[-150:] + ' / ' + after.strip(),
        )
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': (
                        'import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\n'
                        'for p in pm.getUserPackages():\n'
                        "    if (p.getFilePath() or '') == %r:\n        p.getChildrenResources(False)[0].newNode('sbs::compositing::blur')\n"
                        "        print('EDITED', p.isModified())"
                    )
                    % example_sbs
                },
            )
        )
        t = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
        after = text(await c('execute_designer_code', {'code': state}))
        check(
            E,
            'a re-run refuses to discard unsaved edits',
            'ERROR' in t and 'unsaved' in t and '%s:True' % os.path.basename(example_sbs) in after,
            t.strip()[-150:] + ' / ' + after.strip(),
        )
        # ...also when its graph was renamed: the package at OUT_SBS is matched by its path
        # (REVIEW.md INS-22)
        t = text(
            await c(
                'execute_designer_code',
                {
                    'code': (
                        'import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\n'
                        'for p in pm.getUserPackages():\n'
                        "    if (p.getFilePath() or '') == %r:\n"
                        "        p.getChildrenResources(False)[0].setIdentifier('mcp_selftest_trimsheet_renamed')\n"
                        "        print('RENAMED', p.isModified(), p.getChildrenResources(False)[0].getIdentifier())"
                    )
                    % example_sbs
                },
            )
        )
        t2 = text(await c('run_designer_script', {'path': example, 'timeout_s': 300}))
        check(
            E,
            'a re-run refuses to discard unsaved edits to a renamed previous build',
            # the new name read back, so a rename that did nothing can't pass (REVIEW.md TST-50)
            'RENAMED True mcp_selftest_trimsheet_renamed' in t and 'ERROR' in t2 and 'unsaved' in t2,
            t.strip() + ' / ' + t2.strip()[-150:],
        )
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import sd\npm=sd.getContext().getSDApplication().getPackageMgr()\n'
                    "for p in list(pm.getUserPackages()):\n    if (p.getFilePath() or '') == %r:\n        pm.unloadUserPackage(p)"
                )
                % decoy_sbs
            },
        )
