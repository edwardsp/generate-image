# GPT Image model evaluation — 2026-09-21

## Recommendation

Use **Flare for fast drafts and most cinematic slide backgrounds**. Use
**Sunburst for final creative assets and selective edits** where preserving
unrequested details matters more than speed. **Flare is now the default**, approved
by the owner after reviewing this comparison on 2026-09-21. GPT Image 2 remains
available explicitly and performed well on this scene. Existing environment
deployment overrides are preserved. A single scene is not a general model ranking.

## Verified Azure deployment and API

| Model | Version | Region / SKU | Capacity | Deployment result |
|---|---|---|---:|---|
| GPT Image 2 | `2026-04-21` | East US 2 / GlobalStandard | 1 | Existing, Succeeded |
| GPT Image 2.5 Flare | `2026-09-08` | East US 2 / GlobalStandard | 1 | Created, Succeeded |
| GPT Image 2.5 Sunburst | `2026-09-08` | East US 2 / GlobalStandard | 1 | Created, Succeeded |

Live catalogue reported GenerallyAvailable, OpenAI format, generation and editing
for all three. Regional quota before provisioning was 0/2 for each 2.5 model and
1/2 for GPT Image 2. Each deployment uses one capacity unit (catalogue rate limit:
one request per 60 seconds per unit). Deployment writes on the same parent account
must be serialized: the initial parallel attempt returned RequestConflict for
Flare; retrying it after Sunburst completed succeeded.

**Successful inference**, not just catalogue listings, verified these routes:

```text
POST /openai/deployments/{deployment}/images/generations?api-version=2025-04-01-preview
POST /openai/deployments/{deployment}/images/edits?api-version=2025-04-01-preview
```

Generation uses JSON; edits use multipart, with `image` for one reference,
`image[]` for multiple references, and optional `mask`. The helper's existing
transport was retained. API version and endpoint environment overrides remain.

## Matched trials

One request per model per trial, `n=1`, quality `high`, identical prompt/settings
within each trial, same source image for all edits. Models ran concurrently;
times include CLI startup, network, service queueing and writing the file.
No seed, repeated samples, latency distribution, or controlled service load.

| Model | Generation 1536×1024 | Edit to 1536×864 | Mask edit 1536×1024 |
|---|---:|---:|---:|
| GPT Image 2 | 97.13 s | 88.49 s | Not retested live |
| Flare | 39.42 s | 27.66 s | 39.93 s |
| Sunburst | 62.16 s | 59.61 s | 64.10 s |

Generation inspection: all three placed a copper-domed observatory on the right
with readable dark negative space on the left, layered mountains, ocean haze,
and warm windows. Flare and Sunburst gave more detailed foreground rock textures;
GPT Image 2 gave a simpler, atmospheric composition. Sunburst's brighter sunset
is more dramatic but slightly less faithful to the requested blue hour. No
visible text, logos or watermarks. All were usable slide-background candidates.

Edit inspection: all three preserved the recognizable source observatory and
coastline, changed the windows to cyan, and returned native 16:9 images. Sunburst
retained more warm exterior/path lights than Flare, which shifted more of the
scene toward blue. GPT Image 2 also retained warm exterior lighting. None is a
pixel-perfect lock; the aspect-ratio change necessarily changes framing.

**Mask visual validation failed for Sunburst:** the API accepted the request and
returned a valid PNG, but the masked rectangle was black. A second trial using
transparent-white instead of transparent-black pixels reproduced the artifact
(62.45 s). No root cause is established; this is not a claim of working inpainting.
Use prompt-led Sunburst reference edits without masks for now. Flare returned a
usable masked-edit image but altered the observatory's architecture, so its mask
is not an exact-preservation guarantee. Existing multipart semantics are retained.
Repeated-reference multipart
construction is covered offline; its live comparison is not part of these trials.

## Native widescreen / quality checks

Additional real CLI requests (not a matched-quality latency comparison):

| Model | Requested and decoded PNG dimensions | Quality | Time |
|---|---|---|---:|
| Flare | 2560×1440 | xhigh | 41.84 s |
| Sunburst | 2560×1440 | max | 160.56 s |

Pillow decoded and fully loaded the eight initial generation/edit/resolution PNGs
and both first mask outputs, confirming their expected dimensions. Bytes were saved directly from API base64;
no resizing or upscaling was performed.

Microsoft documents both edges divisible by 16, maximum edge 3840, aspect ratio
between 1:3 and 3:1, and 655,360–8,294,400 pixels for these model families.
Use **1536×864** or **2560×1440** for exact 16:9. **1920×1080 is invalid** under
this rule (1080 is not divisible by 16). 3840×2160 satisfies the constraints, but
2.5 resolutions above 2560×1440 are documented as experimental and were not tested.

Documented qualities for 2.5: low, medium, high, xhigh, max, auto. Live-tested:
high on both, xhigh on Flare, max on Sunburst. Other combinations are not claimed
as empirically verified. GPT Image 2 keeps low/medium/high/auto compatibility.

## Cost limitations

Azure catalogue `cost` was null, and the public pricing material examined did not
establish usable Azure dollar rates for these models. **Actual billed cost was
not measured**; this evaluation does not claim Flare is cheaper. Direct OpenAI
API token prices are not Azure prices. Confirm the subscription's Azure meters
before large batches, `max`, or experimental high-resolution output.

## Reproducible prompts

Generation (`1536x1024`, `high`, all three models):

> Cinematic photorealistic widescreen presentation background: a remote observatory on a rocky coastal headland at blue hour, one small copper dome on the right third, warm amber windows, layered distant mountains and silver ocean haze, physically plausible architecture, restrained teal and amber color grading, subtle film grain. Keep the entire left 45 percent as smooth dark navy mist with very little detail for readable white slide text. No text, logos, borders or watermark.

Edit (`1536x864`, `high`, all three; source = GPT Image 2 generation above):

> Edit this reference image: preserve the exact observatory design, dome, camera angle, coastline and mountain silhouettes. Change only the warm amber window illumination to soft cyan-blue. Extend the composition sideways as needed for a 16:9 canvas without cropping the dome. Keep the left 45 percent smooth dark navy negative space for slide text. No text or logos.

High-resolution check (`2560x1440`; Flare xhigh, Sunburst max):

> Cinematic photorealistic 16:9 slide background: a remote observatory with one copper dome on the right third of a rocky coast, blue-hour teal and amber lighting, intricate natural rock textures and atmospheric distant mountains. Left 45 percent smooth dark navy mist with low detail for white text. No text, logos or watermark.

Mask check (`1536x1024`, `high`, both 2.5 models):

> Change the observatory windows to soft cyan blue inside the masked area. Preserve the rest of the image and architecture.

Source as above; same-size RGBA PNG mask opaque white except a transparent rectangle
at `(1020,480)`–`(1300,720)`. No private prompts or images used. Output files remain
local, outside the repository, in `/tmp/opencode/image-model-eval-20260921/`.

Example rerun (paid inference):

```bash
python3 scripts/generate_image.py --model flare -p "<generation prompt above>" \
  -s 1536x1024 -q high -o flare-generation.png
python3 scripts/generate_image.py --model sunburst -p "<edit prompt above>" \
  -i gpt-image-2-generation.png -s 1536x864 -q high -o sunburst-edit.png
```

## Sources

- [Microsoft Learn: image generation model comparison, sizes and quality](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/dall-e)
- [OpenAI: Introducing ChatGPT Images 2.5 — vendor speed/precision positioning](https://openai.com/index/introducing-chatgpt-images-2-5/)
- [Microsoft Learn: v1 preview REST reference — alternative API surface, not used in these tests](https://learn.microsoft.com/en-us/azure/foundry/openai/reference-preview-latest)
- [Azure CLI deployment commands](https://learn.microsoft.com/en-us/cli/azure/cognitiveservices/account/deployment)

The public catalogue/reference pages are not fully synchronized. Live deployment
and inference results above take precedence over assumptions based on model listings.
