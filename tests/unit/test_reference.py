"""analyze_reference (ROADMAP item 119): a reference image's palette as Gradient Map keys, with the fit's error, read
from synthetic images. The tool called through MCP: the bitmaps check of the live self-test."""

import json
import types
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from image_files import DARK, LIGHT, MID, RGB8, halves_png, png, swatch_strip, tiff_32, tiff_float
from reference_results import assert_keys, result_keys, result_line

from conftest import patch_server, server
from server_tools.reference import _palette


def _value(text: str, label: str) -> float:
    """The number after `label` at the start of a line of the result: 'fit error ', 'least error ' or "one key's
    error "."""
    return float(result_line(text, label)[len(label) :].split()[0].rstrip(':,'))


def _error(text: str) -> float:
    """The result's fit error."""
    return _value(text, 'fit error ')


def _one_luminance() -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """A red and a blue of one luminance, the mean of R, G and B; Rec.709's luma tells them apart."""
    red, blue = np.array([0.8, 0.1, 0.1]), np.array([0.1, 0.2, 0.7])
    assert blue.mean() == pytest.approx(red.mean())
    return red, blue


def _grey(colour: RGB8) -> float:
    """An 8-bit colour's luminance, 0..1: its grey, the mean of its R, G and B."""
    return float(np.mean(colour) / 255)


def _positions(*colours: RGB8) -> list[float]:
    """Each colour's luminance, stretched from the darkest's to the brightest's to 0..1."""
    greys = [_grey(c) for c in colours]
    return [(y - greys[0]) / (greys[-1] - greys[0]) for y in greys]


def _ramp(*colours: RGB8) -> list[tuple[float, RGB8]]:
    """The keys of these colours, darkest first: each at its stretched luminance (_positions)."""
    return list(zip(_positions(*colours), colours, strict=True))


def test_flat_swatches_give_their_colours_as_keys(tmp_path: Path, sent: list[str]) -> None:
    path = png(tmp_path / 'swatches.png', swatch_strip(MID, LIGHT, DARK))
    text = server.analyze_reference(path, keys=3)
    assert_keys(text, _ramp(DARK, MID, LIGHT))
    assert result_line(text, 'swatches.png: ') == 'swatches.png: 30x10 pixels'
    assert result_line(text, 'luminance ').startswith(
        'luminance %.4f to %.4f (the 1st and 99th percentiles of ' % (_grey(DARK), _grey(LIGHT))
    )
    assert _error(text) == 0
    assert 'asked' not in text
    assert server.analyze_reference(path, keys=3) == text  # no seed: the same image gives the same result
    assert sent == []  # the file alone, with Designer closed


def test_more_keys_than_colours_give_one_key_per_colour(tmp_path: Path) -> None:
    path = png(tmp_path / 'swatches.png', swatch_strip(DARK, MID, LIGHT))
    text = server.analyze_reference(path)  # 5 keys by default
    assert_keys(text, _ramp(DARK, MID, LIGHT))
    assert 'keys: 3 of the 5 asked: the image has 3 of the 64 luminance levels' in text


def test_fewer_keys_than_colours_keep_the_ends_and_fit_the_rest(tmp_path: Path) -> None:
    """2 keys for 3 colours: at 0 and 1, their colours fitted to all three swatches by least squares, which for two
    keys is a straight line through each channel against the position (colours whose line stays within 0..1, as the
    keys are clipped to it)."""
    colours = (60, 40, 30), (170, 90, 60), (220, 210, 170)
    text = server.analyze_reference(png(tmp_path / 'swatches.png', swatch_strip(*colours)), keys=2)
    keys = result_keys(text)
    swatches, x = np.array(colours) / 255, _positions(*colours)
    lines = np.stack([np.polyval(np.polyfit(x, swatches[:, c], 1), [0, 1, *x]) for c in range(3)], axis=1)
    assert [p for p, _ in keys] == [0, 1]
    np.testing.assert_allclose([c[:3] for _, c in keys], lines[:2], atol=1e-4)
    assert _error(text) == pytest.approx(np.sqrt(((lines[2:] - swatches) ** 2).mean()), abs=1e-4)


def test_keys_built_from_known_colours_round_trip() -> None:
    """A ramp coloured by known keys, darkest first: its palette is those keys, and their Gradient Map on its luminance
    lands on it."""
    known = np.array([[0.1, 0.05, 0.02], [0.7, 0.3, 0.15], [0.95, 0.9, 0.75]])
    t = np.linspace(0, 1, 4096)
    rgb = np.stack([np.interp(t, [0, 0.4, 1], known[:, c]) for c in range(3)], axis=1)
    palette = _palette(rgb, 3)
    assert palette.error < 0.005 and palette.floor <= palette.error
    np.testing.assert_allclose(palette.colours, known, atol=0.02)
    low, high = np.percentile(rgb.mean(axis=1), [1, 99])
    assert (palette.low, palette.high) == pytest.approx((low, high))
    assert list(palette.positions[[0, 2]]) == [0, 1]
    assert palette.positions[1] == pytest.approx((known[1].mean() - low) / (high - low), abs=1 / 64)


def test_colour_varying_at_one_luminance_shows_in_the_error() -> None:
    """Two colours of one luminance: no keys tell them apart, so the error stays, whatever the keys, and is the least
    any keys reach. With 2 keys for its 3 levels, the least error is still that, and the fit error above it."""
    red, blue = _one_luminance()
    rgb = np.array([[0.05, 0.05, 0.05]] * 100 + [red] * 100 + [blue] * 100 + [[0.9, 0.9, 0.9]] * 100)
    palette = _palette(rgb, 5)
    # half the pixels at that luminance are off by half the difference of the two colours
    expected = np.sqrt(0.5 * ((red - blue) / 2) ** 2 @ np.ones(3) / 3)
    assert palette.error == pytest.approx(expected, abs=1e-6)
    assert palette.floor == pytest.approx(expected, abs=1e-6)
    np.testing.assert_allclose(palette.colours[1], (red + blue) / 2, atol=1e-9)
    fewer = _palette(rgb, 2)
    assert fewer.floor == pytest.approx(expected, abs=1e-6) and fewer.error > expected + 0.005


def test_one_keys_error_is_what_the_two_errors_read_against(tmp_path: Path) -> None:
    """One key, the image's mean colour everywhere, is the baseline. With too few keys the fit error is above the least
    error, and both are below one key's; the result says how to read them."""
    text = server.analyze_reference(png(tmp_path / 'swatches.png', swatch_strip(DARK, MID, LIGHT)), keys=2)
    swatches = np.array([DARK, MID, LIGHT]) / 255
    assert _value(text, "one key's error ") == pytest.approx(
        np.sqrt(((swatches - swatches.mean(0)) ** 2).mean()), abs=1e-4
    )
    assert _value(text, 'least error ') < _value(text, 'fit error ') < _value(text, "one key's error ")
    reading = result_line(text, 'reading the errors: ')
    assert "more keys won't help" in reading
    assert (
        'parts of different colours, a mask may split them' in reading and 'on one material it is its grain' in reading
    )


def test_a_least_error_at_one_keys_means_the_colour_doesnt_follow_luminance() -> None:
    """Red and blue of one luminance, with 1% of pixels darker and 1% lighter: the 1st and 99th percentiles fall
    between those and red and blue, so red and blue share a level however their greys round. The least error is then
    theirs, near one key's. A colour that follows luminance has a least error of 0."""
    red, blue = _one_luminance()
    rgb = np.array([[0.05, 0.05, 0.05]] * 10 + [red] * 490 + [blue] * 490 + [[0.9, 0.9, 0.9]] * 10)
    apart = _palette(rgb, 5)
    half = (red - blue) / 2  # what each red or blue pixel misses, their level's mean colour being between them
    assert apart.floor == pytest.approx(np.sqrt(0.98 * (half**2).mean()), abs=1e-9)
    assert apart.one_key == pytest.approx(np.sqrt(((rgb - rgb.mean(0)) ** 2).mean()), abs=1e-9)
    assert 0.9 * apart.one_key < apart.floor < apart.one_key
    follows = _palette(np.array([[0.1, 0.05, 0.02]] * 100 + [[0.9, 0.8, 0.6]] * 100), 5)
    assert follows.floor == pytest.approx(0, abs=1e-9) and follows.one_key > 0.1


def test_a_small_colour_of_its_own_at_one_luminance_takes_keys_as_a_spike() -> None:
    """The recipe in GUIDE.md (Which tool for what, Measure): red flecks, every 20th pixel of a brown ramp, take three close
    keys of 5, the middle one red, and raise the least error. With 2 keys they show as a fit error far above the least
    error. The ramp alone has neither."""
    t = np.linspace(0, 1, 2000)
    brown = np.stack([np.interp(t, [0, 1], ends) for ends in ((0.15, 0.85), (0.08, 0.7), (0.04, 0.5))], axis=1)
    flecked = brown.copy()
    flecked[::20] = [0.9, 0.1, 0.05]
    spiked = _palette(flecked, 5)
    reds = [i for i, (r, g, _) in enumerate(spiked.colours) if r - g > 0.5]
    assert len(reds) == 1 and 0 < reds[0] < 4, spiked
    assert spiked.positions[reds[0] + 1] - spiked.positions[reds[0] - 1] < 0.05, spiked
    assert spiked.floor > 0.02 and spiked.error < 1.1 * spiked.floor
    assert _palette(flecked, 2).error > 2 * spiked.floor
    plain = _palette(brown, 5)
    assert all(r - g < 0.2 for r, g, _ in plain.colours) and plain.floor < 0.001


def test_transparent_pixels_are_left_out(tmp_path: Path) -> None:
    image = swatch_strip((*DARK, 255), (*LIGHT, 255), (0, 255, 0, 0), (0, 255, 0, 0))  # right half transparent green
    text = server.analyze_reference(png(tmp_path / 'cut_out.png', image))
    assert_keys(text, [(0, DARK), (1, LIGHT)])
    assert 'ignoring 50.0% transparent reference pixels' in text
    with pytest.raises(server.ToolError, match='fully transparent'):
        server.analyze_reference(png(tmp_path / 'clear.png', swatch_strip((0, 255, 0, 0))))


def test_a_grey_image_gives_grey_keys(tmp_path: Path) -> None:
    ramp = np.tile(np.arange(256, dtype=np.uint8), (8, 1))  # mode L
    text = server.analyze_reference(png(tmp_path / 'ramp.png', ramp), keys=4)
    keys = result_keys(text)
    assert len(keys) == 4 and [keys[0][0], keys[-1][0]] == [0, 1]
    assert all(r == g == b and a == 1 for _, (r, g, b, a) in keys), keys
    assert _error(text) < 0.005


def test_equal_percentiles_stretch_over_the_minimum_and_maximum(tmp_path: Path) -> None:
    """A decal on a plain background: 99% of the pixels at one luminance make the 1st and 99th percentiles equal, so the
    luminance is stretched from its minimum to its maximum, and the result says so."""
    decal = np.full((10, 100, 3), MID, np.uint8)
    decal[0, :5], decal[0, 5:10] = DARK, LIGHT
    text = server.analyze_reference(png(tmp_path / 'decal.png', decal))
    assert_keys(text, _ramp(DARK, MID, LIGHT))
    assert result_line(text, 'luminance ').startswith(
        'luminance %.4f to %.4f (the minimum and maximum of ' % (_grey(DARK), _grey(LIGHT))
    )


def test_a_flat_image_gives_one_key(tmp_path: Path) -> None:
    text = server.analyze_reference(png(tmp_path / 'flat.png', swatch_strip(MID)), keys=3)
    assert_keys(text, [(0, MID)])
    assert 'keys: 1 of the 3 asked: the image has 1 of the 64 luminance levels' in text
    assert result_line(text, 'luminance ').startswith('luminance %.4f to %.4f ' % (_grey(MID), _grey(MID)))


def test_one_key_is_the_mean_colour(tmp_path: Path) -> None:
    keys = result_keys(server.analyze_reference(png(tmp_path / 'two.png', swatch_strip(DARK, LIGHT)), keys=1))
    assert len(keys) == 1
    assert keys[0][1] == pytest.approx([*((np.array(DARK) + LIGHT) / 2 / 255), 1], abs=1e-4)


def test_a_region_reads_only_its_pixels(tmp_path: Path) -> None:
    path = halves_png(tmp_path)
    text = server.analyze_reference(path, reference_region=(10, 0, 20, 10))
    assert_keys(text, [(0, LIGHT)])
    assert result_line(text, 'halves.png: ') == 'halves.png: 10x10 pixels in reference_region [10, 0, 20, 10]'


@pytest.mark.parametrize('region', [(30, 0, 40, 10), (5, 5, 5, 9)], ids=['outside', 'empty'])
def test_a_bad_region_is_refused(tmp_path: Path, region: tuple[int, int, int, int]) -> None:
    path = halves_png(tmp_path)
    with pytest.raises(server.ToolError, match=r'reference_region \[.*\] is empty for the 20x10 image'):
        server.analyze_reference(path, reference_region=region)


def test_keys_below_one_are_refused(tmp_path: Path) -> None:
    path = halves_png(tmp_path)
    with pytest.raises(server.ToolError, match='keys is 1 or more, not 0'):
        server.analyze_reference(path, keys=0)


def test_a_large_image_is_sampled_not_averaged(tmp_path: Path) -> None:
    """Over about 1 MP the image is sampled down first: one-pixel stripes keep their two colours, which averaging would
    blend into others."""
    stripes = np.zeros((1024, 2048, 3), np.uint8)
    stripes[:, 0::2], stripes[:, 1::2] = DARK, LIGHT
    text = server.analyze_reference(png(tmp_path / 'stripes.png', stripes))
    assert result_line(text, 'stripes.png: ') == 'stripes.png: 2048x1024 pixels, sampled down to 1448x724'
    assert_keys(text, [(0, DARK), (1, LIGHT)])


def test_a_region_of_a_large_image_is_cut_before_the_sampling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The region is cut first, in the image's own pixels: a region of a larger image, under the sampling limit, isn't
    sampled, and holds only its own colour."""
    patch_server(monkeypatch, '_MOST_PIXELS', 4096)  # the image has 8192 pixels, the region 2048
    image = np.full((64, 128, 3), LIGHT, np.uint8)
    image[:, :32] = DARK
    text = server.analyze_reference(png(tmp_path / 'big.png', image), reference_region=(0, 0, 32, 64))
    assert result_line(text, 'big.png: ') == 'big.png: 32x64 pixels in reference_region [0, 0, 32, 64]'
    assert_keys(text, [(0, DARK)])


def _assert_read_as_compare_reads(text: str, path: str, region: tuple[int, int, int, int] | None = None) -> None:
    """The result's one key is the grey compare_to_reference reads (_load_reference) at the region's top-left:
    100/65535, the 16-bit range of the whole 32-bit image."""
    [(position, colour)] = result_keys(text)
    grey = float(server._load_reference(path, region)[0][0, 0, 0])
    assert grey == pytest.approx(100 / 65535)
    assert position == 0 and colour == pytest.approx([grey] * 3 + [1], abs=1e-4)


def test_a_region_of_a_32_bit_image_keeps_the_whole_images_range(tmp_path: Path) -> None:
    """A plain 32-bit image is 16-bit when any of its values is over 255 (image_reading.py's _reference_pixels): a dark
    region of it too, as compare_to_reference reads it."""
    values = np.full((4, 8), 100, np.int32)
    values[:, 4:] = 40000
    path = tiff_32(tmp_path / 'i32.tif', values)
    _assert_read_as_compare_reads(server.analyze_reference(path, (0, 0, 4, 4)), path, (0, 0, 4, 4))


def test_a_sample_of_a_32_bit_image_keeps_the_whole_images_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_server(monkeypatch, '_MOST_PIXELS', 4096)  # the image has 8192 pixels
    values = np.full((64, 128), 100, np.int32)
    values[0, 1] = 40000  # a pixel the sampling down to 90x45 leaves out
    path = tiff_32(tmp_path / 'i32.tif', values)
    text = server.analyze_reference(path)
    assert 'sampled down to 90x45' in text
    _assert_read_as_compare_reads(text, path)


def test_pixels_that_arent_finite_numbers_are_left_out(tmp_path: Path) -> None:
    """A float image's NaN and infinite pixels are left out, as transparent ones are, and the result says how many; an
    image of none but those is refused."""
    values = np.full((4, 8), 0.25, np.float32)
    values[:, 4:] = 0.75
    values[0, 0], values[1, 5] = np.nan, np.inf
    text = server.analyze_reference(tiff_float(tmp_path / 'float.tif', values))
    assert result_keys(text) == [(0, [0.25, 0.25, 0.25, 1]), (1, [0.75, 0.75, 0.75, 1])], text
    assert 'ignoring 2 non-finite pixels (NaN or infinite)' in text
    values[1, 5] = 0.75
    text = server.analyze_reference(tiff_float(tmp_path / 'one.tif', values))
    assert 'ignoring 1 non-finite pixel (NaN or infinite)' in text
    with pytest.raises(server.ToolError, match='no pixel of the reference is a finite number'):
        server.analyze_reference(tiff_float(tmp_path / 'none.tif', np.full((4, 8), np.nan, np.float32)))


def test_values_beyond_0_to_1_are_clipped_first(tmp_path: Path) -> None:
    """A float image's values are clipped to 0..1 before the palette, as the keys are: half 0.5 and half 4.0 reads as
    0.5 and 1, the errors keep their order and the keys fit exactly."""
    values = np.full((4, 8), 0.5, np.float32)
    values[:, 4:] = 4.0
    text = server.analyze_reference(tiff_float(tmp_path / 'bright.tif', values))
    assert result_keys(text) == [(0, [0.5, 0.5, 0.5, 1]), (1, [1, 1, 1, 1])], text
    assert result_line(text, 'luminance ').startswith('luminance 0.5000 to 1.0000 ')
    assert _error(text) == 0 and _value(text, "one key's error ") == pytest.approx(0.25, abs=1e-4)


def test_the_keys_go_into_set_as_they_are(tmp_path: Path, faked_helpers: types.ModuleType) -> None:
    # apply_edits' set reads a Gradient Map's keys with _given_keys (designer_helpers/edits.py)
    keys = result_keys(server.analyze_reference(png(tmp_path / 'swatches.png', swatch_strip(DARK, MID, LIGHT))))
    given = faked_helpers._given_keys('gradientrgba', faked_helpers._GRADIENT_KEY, json.loads(json.dumps(keys)))
    assert len(given) == 3 and [(k['position'], k['value']) for k in given] == [(p, c) for p, c in keys]


def test_the_result_names_the_luminance_weights(tmp_path: Path) -> None:
    """The luminance is the mean of R, G and B, the grey Designer's Grayscale Conversion gives at its default, and the
    result says so in weights."""
    text = server.analyze_reference(halves_png(tmp_path))
    assert '0.333333 R + 0.333333 G + 0.333333 B' in result_line(text, 'luminance ')


def test_the_description_says_the_keys_are_for_interpmode_0() -> None:
    """The fit is linear between keys and the nearest key's colour outside them, which a Gradient Map computes at its
    default interpmode 0 (GUIDE.md, Which tool for what, Gradients and curves; REVIEW.md SRV-240)."""
    assert 'interpmode 0' in ' '.join((server.analyze_reference.__doc__ or '').split())


@pytest.mark.parametrize(
    'line',
    [
        'gradientrgba: {"0": [1, 0, 0, 1]}',
        'gradientrgba: [[0, "red"]]',
        'gradientrgba: [[0, [1, 0, "0"]]]',
        'gradientrgba: [0.5]',
    ],
    ids=['not a list', 'a colour not a list', 'a value not a number', 'a key not a pair'],
)
def test_the_keys_line_of_another_shape_is_refused(line: str) -> None:
    """result_keys checks each key's position and colour before giving them typed (REVIEW.md TST-789)."""
    with pytest.raises(AssertionError):
        result_keys(line)
