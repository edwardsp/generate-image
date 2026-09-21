---
name: generate-image
description: "Generate or edit an image and save it to a file using Azure AI Foundry (GPT Image 2, Flare, or Sunburst). Use when the user asks to 'generate an image', 'create an image', 'make a picture/logo/icon', 'draw', or 'render an image', including cinematic slide backgrounds and reference-image edits. Requires a prompt and output filename; supports model, size, quality and mask selection."
---

# generate-image

Generate or edit an image and write it to a file using the `paul-ai-models` Azure
AI Foundry account. **Flare is the recommended default**, approved after live
comparison (2026-09-21). Sunburst and GPT Image 2 remain available explicitly.

## Which model to use

| Choose | When | CLI |
|---|---|---|
| **Flare (default)** | Fast iteration, everyday images, batches of slide backgrounds. Best starting point for cinematic backgrounds. | `--model flare` (or omit if no env override) |
| **Sunburst** | Final hero images and precise reference-image edits when fidelity matters more than latency. | `--model sunburst` |
| **GPT Image 2** | Existing workflows or reproducing an established look. | `--model gpt-image-2` |

In a matched one-shot `high`-quality trial, generation/edit took **39/28 s** for
Flare, **62/60 s** for Sunburst, and **97/88 s** for GPT Image 2. All kept useful
left-side negative space; Sunburst preserved more warm exterior lighting during
a selective window-color edit, whereas Flare shifted more of the scene blue.
This small sample supports Flare for drafts and Sunburst for precision, not a
universal quality ranking. Azure dollar pricing was not verified; do not claim
Flare is cheaper or substitute direct OpenAI prices for Azure billing.

See [evaluation and reproducible prompts](references/model-evaluation.md).

## When to use

The user wants a picture created from a description and saved locally — e.g.
"generate an image of a mountain sunset and save it as sunset.png", "make a logo
for my project", "create an icon called robot.png".

Two things are always needed: **a prompt** and **an output filename**.

## Prerequisites

- `AZURE_OPENAI_API_KEY` in the environment. It is auto-loaded from
  `~/ai-models-out/foundry.env` if not already set, so this normally just works.
- Deployments `gpt-image-2`, `gpt-image-2.5-flare`, and `gpt-image-2.5-sunburst`
  on `paul-ai-models` (already provisioned, GlobalStandard, East US 2).

## How to run

Invoke the helper script with a prompt and an output path:

```bash
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  --prompt "PROMPT TEXT" --out FILENAME
```

Positional shorthand also works:

```bash
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py "PROMPT TEXT" FILENAME
```

The script prints `OK: saved <size> image -> <absolute path> (<KB>)` on success and
exits non-zero with the API error text on failure. If the filename has no extension,
`.png` is appended.

### Options

- `--prompt`, `-p` — the image description (required)
- `--out`, `-o` — output file path (required; `.png` added if missing)
- `--model`, `-m` — `gpt-image-2`, `flare`, `sunburst`, or the full 2.5 model ID.
  Explicit selection overrides `AZURE_OPENAI_IMAGE_DEPLOYMENT`.
- `--deployment` — custom deployment name; overrides both `--model` and the env
  deployment. Pair with `--model` to apply the right validation to custom names.
- `--size`, `-s` — `1024x1024` (default), `auto`, or `WIDTHxHEIGHT`.
  For known models: both edges must be multiples of 16, no edge above 3840,
  aspect ratio at most 3:1, and 655,360–8,294,400 total pixels.
  **Use `1536x864` or `2560x1440` for exact 16:9.** `1536x1024` is 3:2, not 16:9;
  `1920x1080` is invalid because 1080 is not divisible by 16.
  Above 2560x1440 is documented as experimental for 2.5 and was not live-tested.
- `--quality`, `-q` — `high` (default), `medium`, `low`, `auto`;
  2.5 models additionally accept `xhigh` and `max`. Start with `high`.
  Flare `xhigh` and Sunburst `max` were live-tested at 2560x1440; not every
  model/quality/size combination has been tested.
- `--image`, `-i` — input image to edit (repeatable). When supplied, the script uses
  the `/images/edits` endpoint (img2img) to transform the source instead of generating
  from scratch. Ask explicitly for composition preservation; it is not guaranteed.
- `--mask` — optional PNG mask for inpainting (only used with `--image`).
  **Avoid Sunburst masks for now:** two live tests returned a black rectangle in
  the masked area despite HTTP success. Use a prompt-led edit without `--mask`
  instead. Flare's mask test produced an image but changed some architecture;
  inspect output rather than assuming exact preservation.

### Config overrides (env)

- `AZURE_OPENAI_ENDPOINT` — default `https://paul-ai-models.cognitiveservices.azure.com/`
- `AZURE_OPENAI_IMAGE_DEPLOYMENT` — default `gpt-image-2.5-flare`. Existing process
  or `foundry.env` overrides are preserved; remove an old override or pass
  `--model flare` to select Flare explicitly.
- `AZURE_OPENAI_IMAGE_API_VERSION` — default `2025-04-01-preview`

## Examples

```bash
# Fast native 16:9 cinematic slide background
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  --model flare -s 2560x1440 -q high \
  -p "cinematic coastal observatory on the right, left 45 percent dark empty mist for slide text, no text" \
  -o ~/Pictures/observatory-slide.png

# Precision reference edit for a final asset
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  --model sunburst -s 1536x864 -q high \
  -p "preserve the scene and architecture; change only the window light to cyan" \
  -i ~/Pictures/observatory-slide.png -o ~/Pictures/observatory-cyan.png

# Landscape hero image, high quality
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  -p "a serene mountain lake at sunrise, misty, photorealistic" \
  -o ~/Pictures/lake.png -s 1536x1024 -q high

# Quick square icon
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  "flat minimalist rocket icon, single color" rocket.png

# Edit an existing image (img2img) — keep the scene, change one thing
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  -p "keep the scene identical but turn the night sky to early dawn" \
  -i title.png -o title-dawn.png -s 1536x1024 -q high
```

## Notes

- After generating, report the saved path back to the user. Do not print the raw
  base64 payload.
- `gpt-image-2` returns base64 image data (no hosted URL); the script decodes and
  writes the bytes for you.
- With `--image`, the script calls `/images/edits` (multipart upload) instead of
  `/images/generations`; the success line reads `OK: edited ...`.
- All three models were tested on the existing deployment-scoped
  `2025-04-01-preview` API. No API migration or silent model fallback is performed.
- The helper saves the API bytes without resizing/upscaling. Inspect actual image
  dimensions before calling an output native high resolution (especially `auto`).
- Masks and repeated references retain their existing multipart behavior. Mask
  requests were accepted on both 2.5 models, but Sunburst failed visual validation
  (see warning above); edits are not pixel-lock guarantees.
- For custom deployment names without `--model`, the server validates model-specific
  size support; `xhigh/max` require a known 2.5 profile. Environment endpoint/key/API
  version overrides and env-file loading remain supported.
