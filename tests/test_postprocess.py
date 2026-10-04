import random

from PIL import Image, ImageStat

import postprocess

STRONG = {"low_res_width": 480, "blur": 0.8, "chroma_shift": 2, "saturation": 0.8, "contrast": 0.85,
          "black_lift": 15, "grain": 8.0, "color_grain": False}


def sample(size=(1344, 768)):
    image = Image.new("RGB", size, (200, 180, 40))
    for x in range(0, size[0], 40):  # sharp vertical lines to measure softening
        image.paste((0, 0, 0), (x, 0, x + 2, size[1]))
    return image


def test_random_params_vary_and_stay_in_bounds():
    rng = random.Random(0)
    drawn = [postprocess.random_params(rng) for _ in range(200)]
    assert len({(p["grain"], p["blur"], p["low_res_width"]) for p in drawn}) > 150
    assert any(p["grain"] == 0 for p in drawn) and any(p["color_grain"] for p in drawn)
    for p in drawn:
        assert 0 <= p["grain"] <= 13 and 0 <= p["blur"] <= 0.9 and 0.72 <= p["saturation"] <= 1.0
        assert not (p["color_grain"] and p["grain"] == 0)


def test_keeps_size_and_returns_rgb_for_any_params():
    rng = random.Random(1)
    for source in (sample(), sample((512, 288)), Image.new("RGBA", (300, 200))):
        for _ in range(5):
            result = postprocess.analog_look(source, postprocess.random_params(rng))
            assert result.size == source.size and result.mode == "RGB"


def test_lifts_blacks():
    result = postprocess.analog_look(Image.new("RGB", (100, 60), (0, 0, 0)), STRONG)
    assert ImageStat.Stat(result).mean[0] > 5


def test_softens_sharp_edges():
    source = sample()
    result = postprocess.analog_look(source, STRONG)
    edge = lambda img: ImageStat.Stat(img.convert("L").crop((0, 300, 400, 310))).stddev[0]
    assert edge(result) < edge(source)
