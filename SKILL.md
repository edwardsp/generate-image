---
name: generate-image
description: "Generate an image from a text prompt and save it to a file using Azure AI Foundry (gpt-image-2). Use when the user asks to 'generate an image', 'create an image', 'make a picture/logo/icon', 'draw', or 'render an image' and wants it saved to a filename. Requires a prompt and an output filename; optional size and quality. Backed by the paul-ai-models Foundry deployment."
---

# generate-image

Generate an image from a text prompt and write it to a file, using the `gpt-image-2`
deployment on the `paul-ai-models` Azure AI Foundry account.

## When to use

The user wants a picture created from a description and saved locally — e.g.
"generate an image of a mountain sunset and save it as sunset.png", "make a logo
for my project", "create an icon called robot.png".

Two things are always needed: **a prompt** and **an output filename**.

## Prerequisites

- `AZURE_OPENAI_API_KEY` in the environment. It is auto-loaded from
  `~/ai-models-out/foundry.env` if not already set, so this normally just works.
- The `gpt-image-2` deployment on `paul-ai-models` (already provisioned).

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
- `--size`, `-s` — `1024x1024` (default), `1024x1536`, `1536x1024`, or `auto`
- `--quality`, `-q` — `high` (default), `medium`, `low`, or `auto`

### Config overrides (env)

- `AZURE_OPENAI_ENDPOINT` — default `https://paul-ai-models.cognitiveservices.azure.com/`
- `AZURE_OPENAI_IMAGE_DEPLOYMENT` — default `gpt-image-2`
- `AZURE_OPENAI_IMAGE_API_VERSION` — default `2025-04-01-preview`

## Examples

```bash
# Landscape hero image, high quality
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  -p "a serene mountain lake at sunrise, misty, photorealistic" \
  -o ~/Pictures/lake.png -s 1536x1024 -q high

# Quick square icon
python3 ~/.config/opencode/skills/generate-image/scripts/generate_image.py \
  "flat minimalist rocket icon, single color" rocket.png
```

## Notes

- After generating, report the saved path back to the user. Do not print the raw
  base64 payload.
- `gpt-image-2` returns base64 image data (no hosted URL); the script decodes and
  writes the bytes for you.
