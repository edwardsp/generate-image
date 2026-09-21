# generate-image

An [OpenCode](https://opencode.ai) **skill** that generates an image from a text
prompt — or **edits an existing image** (img2img) — using Azure AI Foundry
(`gpt-image-2`, `gpt-image-2.5-flare`, or `gpt-image-2.5-sunburst`) and saves it to a file.

## Install

Clone this repo directly into your OpenCode skills directory (the folder name must
be `generate-image`):

```bash
git clone https://github.com/edwardsp/generate-image \
  ~/.config/opencode/skills/generate-image
```

Update later with:

```bash
git -C ~/.config/opencode/skills/generate-image pull
```

OpenCode will pick up the skill from `SKILL.md` automatically.

## Configure

You need an Azure OpenAI / AI Foundry image deployment. Provide credentials and
config via environment variables:

| Variable | Required | Default |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | ✅ | — |
| `AZURE_OPENAI_ENDPOINT` | — | `https://<your-resource>.cognitiveservices.azure.com/` |
| `AZURE_OPENAI_IMAGE_DEPLOYMENT` | — | `gpt-image-2.5-flare` |
| `AZURE_OPENAI_IMAGE_API_VERSION` | — | `2025-04-01-preview` |

The script also auto-loads variables from `~/ai-models-out/foundry.env` if that file
exists. **Never commit your API key** — it is read from the environment (or a local,
git-ignored env file) at runtime. This repo contains no credentials.

## Usage

```bash
python3 scripts/generate_image.py --prompt "PROMPT TEXT" --out FILENAME
# positional shorthand:
python3 scripts/generate_image.py "PROMPT TEXT" FILENAME
```

Options: `--model gpt-image-2|flare|sunburst` (full IDs also work),
`--deployment CUSTOM_NAME`, `--size WIDTHxHEIGHT|auto` (`1024x1024` default),
`--quality high|medium|low|auto` (plus `xhigh|max` for 2.5).
If the filename has no extension, `.png` is appended.

### Choosing a model

- **Flare (default):** fast iteration and everyday generation; the recommended starting
  point for cinematic slide backgrounds.
- **Sunburst:** final creative assets and precision edits where extra latency is
  acceptable.
- **GPT Image 2:** select explicitly for existing workflows or an established look.

All three were live-tested on Azure on 2026-09-21. A small matched trial supports
the speed/precision distinction, not a universal winner or cost claim. See
[results, limitations, sources and reproducible prompts](references/model-evaluation.md).

```bash
python3 scripts/generate_image.py --model flare -s 2560x1440 -q high \
  -p "cinematic coastal observatory on the right; left side dark empty mist for slide text" \
  -o background.png
```

Use **1536x864 or 2560x1440 for native 16:9**. Both dimensions must be divisible
by 16, edges <=3840, ratio <=3:1, and pixel count 655,360–8,294,400. Thus 1920x1080
is not valid. 2.5 output above 2560x1440 is documented as experimental and was not
tested. The helper never upscales.

Deployment precedence: `--deployment` > explicit `--model` >
`AZURE_OPENAI_IMAGE_DEPLOYMENT` > `gpt-image-2.5-flare`. Existing process or
`foundry.env` deployment overrides are preserved. Remove an old override or use
`--model flare` to explicitly select Flare. For custom deployment names use
`--model sunburst --deployment my-sunburst` to get model-aware validation.
Unknown deployment names retain server-side model-specific size validation.

### Edit an existing image (img2img)

Pass one or more input images with `--image` / `-i` to transform them instead of
generating from scratch. This routes to the `/images/edits` endpoint — ideal for
"keep the scene, change one thing", although exact preservation is not guaranteed:

```bash
python3 scripts/generate_image.py \
  -p "keep the scene identical but turn the night sky to early dawn" \
  -i title.png -o title-dawn.png -s 1536x1024 -q high
```

`--image` is repeatable (multiple references), and `--mask` supplies an optional
PNG mask for inpainting.

**Known limitation:** Sunburst mask requests returned HTTP success but produced a
black rectangle in two live tests. Prefer Sunburst reference edits **without a
mask** until resolved. Flare mask edits also need visual inspection for unwanted
changes. Existing mask request handling is retained, not silently rerouted.

See [`SKILL.md`](SKILL.md) for full details and examples.

## Tests

```bash
uv run --with pytest pytest -q
```

Offline tests cover selection, override precedence, size/quality validation,
generation/edit/mask requests, and real CLI subprocesses against a local HTTP
server. They do not spend inference credits. Live evaluation details are linked above.

Restart OpenCode after updating the skill so its model-selection guidance reloads.

## License

MIT
