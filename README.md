# generate-image

An [OpenCode](https://opencode.ai) **skill** that generates an image from a text
prompt using Azure AI Foundry (`gpt-image-2`) and saves it to a file.

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
| `AZURE_OPENAI_IMAGE_DEPLOYMENT` | — | `gpt-image-2` |
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

Options: `--size` (`1024x1024` default, `1024x1536`, `1536x1024`, `auto`) ·
`--quality` (`high` default, `medium`, `low`, `auto`). If the filename has no
extension, `.png` is appended.

See [`SKILL.md`](SKILL.md) for full details and examples.

## License

MIT
