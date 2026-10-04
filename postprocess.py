"""Local analog look (Pillow only): softens the too-clean AI render towards cheap camcorder / film photos.

Every image gets its own randomly drawn parameters so the grain/softness is never the same twice.
"""

import random

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

NAME = "analog-v2"  # recorded in the metadata with the drawn parameters

NO_GRAIN_PROBABILITY = 0.2
COLOR_GRAIN_PROBABILITY = 0.3


def random_params(rng=random):
    """Draw one set of effect strengths, kept subtle so images stay readable."""
    grain = 0.0 if rng.random() < NO_GRAIN_PROBABILITY else round(rng.uniform(4, 13), 1)
    return {
        "low_res_width": rng.choice([480, 560, 640, 800, 960, None]),  # None: keep full resolution
        "blur": round(rng.uniform(0.0, 0.9), 2),
        "chroma_shift": rng.randint(0, 3),
        "saturation": round(rng.uniform(0.72, 1.0), 2),
        "contrast": round(rng.uniform(0.82, 1.0), 2),
        "black_lift": rng.randint(2, 20),
        "grain": grain,
        "color_grain": grain > 0 and rng.random() < COLOR_GRAIN_PROBABILITY,
    }


def soften(image, low_res_width, blur):
    """Downscale then upscale back (low-resolution softness), then a light blur."""
    width, height = image.size
    if low_res_width and width > low_res_width:
        small = image.resize((low_res_width, round(height * low_res_width / width)), Image.Resampling.BILINEAR)
        image = small.resize((width, height), Image.Resampling.BILINEAR)
    return image.filter(ImageFilter.GaussianBlur(blur)) if blur else image


def chromatic_aberration(image, shift):
    if not shift:
        return image
    red, green, blue = image.split()
    return Image.merge("RGB", (ImageChops.offset(red, shift, 0), green, ImageChops.offset(blue, -shift, 0)))


def fade(image, saturation, contrast, black_lift):
    image = ImageEnhance.Color(image).enhance(saturation)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return image.point(lambda v: black_lift + v * (255 - black_lift) // 255)


def grain(image, sigma, color):
    """Gaussian grain, monochrome or per channel."""
    if not sigma:
        return image
    if color:
        noise = Image.merge("RGB", [Image.effect_noise(image.size, sigma) for _ in range(3)])
    else:
        noise = Image.effect_noise(image.size, sigma).convert("RGB")  # centered on mid-grey (128)
    return ImageChops.add(image, noise, scale=1.0, offset=-128)


def analog_look(image, params):
    """Return a new RGB image with the analog look applied; same size as the input."""
    image = image.convert("RGB")
    image = soften(image, params["low_res_width"], params["blur"])
    image = chromatic_aberration(image, params["chroma_shift"])
    image = fade(image, params["saturation"], params["contrast"], params["black_lift"])
    return grain(image, params["grain"], params["color_grain"])
