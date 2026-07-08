#!/usr/bin/env python3
"""Generate an image with Azure AI Foundry (gpt-image-2) and save it to a file.

Usage:
  generate_image.py --prompt "PROMPT" --out FILENAME [--size SIZE] [--quality Q]
  generate_image.py "PROMPT" FILENAME            # positional shorthand

Options:
  --prompt, -p    Text prompt describing the image (required)
  --out, -o       Output file path. Extension .png is added if missing (required)
  --size, -s      1024x1024 (default) | 1024x1536 | 1536x1024 | auto
  --quality, -q   high (default) | medium | low | auto

Credentials/config (env, with sensible defaults):
  AZURE_OPENAI_API_KEY            required (auto-sourced from ~/ai-models-out/foundry.env)
  AZURE_OPENAI_ENDPOINT          default https://paul-ai-models.cognitiveservices.azure.com/
  AZURE_OPENAI_IMAGE_DEPLOYMENT  default gpt-image-2
  AZURE_OPENAI_IMAGE_API_VERSION default 2025-04-01-preview
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.request
import urllib.error

FOUNDRY_ENV = os.path.expanduser("~/ai-models-out/foundry.env")


def load_env_file(path):
    if not os.path.isfile(path):
        return
    pat = re.compile(r'^\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*"?([^"\n]*)"?\s*$')
    with open(path) as fh:
        for line in fh:
            m = pat.match(line)
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2)


def parse_args(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--prompt", "-p")
    ap.add_argument("--out", "-o", "--output")
    ap.add_argument("--size", "-s", default="1024x1024")
    ap.add_argument("--quality", "-q", default="high")
    ap.add_argument("pos", nargs="*", help="positional: PROMPT OUTFILE")
    a = ap.parse_args(argv)
    if not a.prompt and len(a.pos) >= 1:
        a.prompt = a.pos[0]
    if not a.out and len(a.pos) >= 2:
        a.out = a.pos[1]
    if not a.prompt or not a.out:
        ap.error("both a prompt and an output filename are required")
    if not os.path.splitext(a.out)[1]:
        a.out += ".png"
    return a


def main(argv):
    args = parse_args(argv)
    load_env_file(FOUNDRY_ENV)

    key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: AZURE_OPENAI_API_KEY not set (and not found in %s)" % FOUNDRY_ENV)

    endpoint = os.environ.get(
        "AZURE_OPENAI_ENDPOINT", "https://paul-ai-models.cognitiveservices.azure.com/"
    ).rstrip("/")
    deployment = os.environ.get("AZURE_OPENAI_IMAGE_DEPLOYMENT", "gpt-image-2")
    api_version = os.environ.get("AZURE_OPENAI_IMAGE_API_VERSION", "2025-04-01-preview")

    url = f"{endpoint}/openai/deployments/{deployment}/images/generations?api-version={api_version}"
    payload = json.dumps(
        {"prompt": args.prompt, "size": args.size, "quality": args.quality, "n": 1}
    ).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"ERROR: image API returned HTTP {e.code}\n{body}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: could not reach image endpoint: {e.reason}")

    items = data.get("data") or []
    if not items or not items[0].get("b64_json"):
        sys.exit("ERROR: no image in response:\n" + json.dumps(data)[:800])

    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(base64.b64decode(items[0]["b64_json"]))

    size_kb = os.path.getsize(out) // 1024
    print(f"OK: saved {args.size} image -> {out} ({size_kb} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
