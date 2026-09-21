import argparse
import os
import re
from dataclasses import dataclass
from typing import Final

MODELS: Final = ("gpt-image-2", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst")
DEFAULT_MODEL: Final = "gpt-image-2.5-flare"
ALIASES: Final = {"flare": MODELS[1], "sunburst": MODELS[2]}
QUALITIES: Final = ("auto", "low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True, slots=True)
class ImageOptions:
    prompt: str
    out: str
    size: str
    quality: str
    image: tuple[str, ...]
    mask: str | None
    deployment: str


def parse_args(argv: list[str]) -> ImageOptions:
    ap = argparse.ArgumentParser(description="Generate or edit an image on Azure Foundry.")
    ap.add_argument("--prompt", "-p")
    ap.add_argument("--out", "-o", "--output")
    ap.add_argument("--model", "-m", choices=(*MODELS, *ALIASES),
                    help="model profile (default: flare); explicit selection overrides env")
    ap.add_argument("--deployment", help="custom deployment name; overrides --model and env")
    ap.add_argument("--size", "-s", default="1024x1024", help="auto or WIDTHxHEIGHT, e.g. 1536x864")
    ap.add_argument("--quality", "-q", default="high", choices=QUALITIES)
    ap.add_argument("--image", "-i", action="append", default=[],
                    help="input image to edit (repeatable); enables img2img")
    ap.add_argument("--mask", help="optional PNG mask for inpainting (with --image)")
    ap.add_argument("pos", nargs="*", help="positional: PROMPT OUTFILE")
    a = ap.parse_args(argv)
    prompt: str = a.prompt or (a.pos[0] if a.pos else "")
    out: str = a.out or (a.pos[1] if len(a.pos) > 1 else "")
    if not prompt or not out or len(a.pos) > 2:
        ap.error("a prompt and an output filename are required (at most two positional arguments)")
    if not os.path.splitext(out)[1]:
        out += ".png"
    model: str | None = ALIASES.get(a.model, a.model)
    deployment: str = (a.deployment or model
                       or os.environ.get("AZURE_OPENAI_IMAGE_DEPLOYMENT", DEFAULT_MODEL))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", deployment):
        ap.error("deployment must contain only letters, digits, dots, underscores and hyphens")
    profile = model or deployment
    if a.quality in ("xhigh", "max") and profile not in MODELS[1:]:
        ap.error("xhigh/max require --model flare or --model sunburst (also for custom deployments)")
    size: str = a.size
    if size != "auto":
        dimensions = re.fullmatch(r"([0-9]{1,4})x([0-9]{1,4})", size)
        if dimensions is None:
            ap.error("size must be auto or WIDTHxHEIGHT")
        width, height = map(int, dimensions.groups())
        if profile in MODELS and (
            not (0 < width <= 3840 and 0 < height <= 3840)
            or width % 16 or height % 16
            or max(width, height) > 3 * min(width, height)
            or not 655360 <= width * height <= 8294400
        ):
            ap.error("size requires multiples of 16, edges <=3840, aspect ratio <=3:1, "
                     "and 655360–8294400 pixels; use 1536x864 or 2560x1440 for 16:9")
    images = tuple(os.path.expanduser(p) for p in a.image)
    mask = os.path.expanduser(a.mask) if a.mask else None
    for path in images:
        if not os.path.isfile(path):
            ap.error(f"input image not found: {path}")
    if mask and not images:
        ap.error("--mask requires at least one --image")
    if mask and not os.path.isfile(mask):
        ap.error(f"mask not found: {mask}")
    return ImageOptions(prompt, out, size, a.quality, images, mask, deployment)
