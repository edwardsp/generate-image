#!/usr/bin/env python3
"""Generate or edit an image with Azure AI Foundry (gpt-image-2) and save it to a file.

Usage:
  generate_image.py --prompt "PROMPT" --out FILENAME [--size SIZE] [--quality Q]
  generate_image.py "PROMPT" FILENAME            # positional shorthand
  # image-edit (img2img): pass one or more input images to transform
  generate_image.py -p "PROMPT" -i in.png -o out.png [--mask mask.png]

Options:
  --prompt, -p    Text prompt describing the image (required)
  --out, -o       Output file path. Extension .png is added if missing (required)
  --size, -s      1024x1024 (default) | 1024x1536 | 1536x1024 | auto
  --quality, -q   high (default) | medium | low | auto
  --image, -i     Input image to edit (repeatable). When supplied, the /images/edits
                  endpoint is used instead of /images/generations (img2img).
  --mask          Optional mask PNG for inpainting (only used with --image).

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
import uuid
import urllib.request
import urllib.error

FOUNDRY_ENV = os.path.expanduser("~/ai-models-out/foundry.env")

_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


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
    ap.add_argument("--image", "-i", action="append", default=[],
                    help="input image to edit (repeatable); enables img2img")
    ap.add_argument("--mask", help="optional mask PNG for inpainting (with --image)")
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
    for p in a.image:
        if not os.path.isfile(p):
            ap.error("input image not found: %s" % p)
    if a.mask and not os.path.isfile(a.mask):
        ap.error("mask not found: %s" % a.mask)
    if a.mask and not a.image:
        ap.error("--mask requires at least one --image")
    return a


def _mime_for(path):
    return _MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")


def encode_multipart(fields, files):
    """Build a multipart/form-data body (stdlib only, no requests).

    fields: list of (name, value) text parts.
    files:  list of (name, filename, bytes, content_type) file parts.
    Returns (content_type_header, body_bytes).
    """
    boundary = "----genimg" + uuid.uuid4().hex
    crlf = b"\r\n"
    buf = []
    for name, value in fields:
        buf.append(b"--" + boundary.encode() + crlf)
        buf.append(('Content-Disposition: form-data; name="%s"' % name).encode() + crlf + crlf)
        buf.append(str(value).encode() + crlf)
    for name, filename, content, ctype in files:
        buf.append(b"--" + boundary.encode() + crlf)
        buf.append(
            ('Content-Disposition: form-data; name="%s"; filename="%s"' % (name, filename)).encode()
            + crlf
        )
        buf.append(("Content-Type: %s" % ctype).encode() + crlf + crlf)
        buf.append(content + crlf)
    buf.append(b"--" + boundary.encode() + b"--" + crlf)
    return "multipart/form-data; boundary=%s" % boundary, b"".join(buf)


def build_generation_request(url, key, args):
    payload = json.dumps(
        {"prompt": args.prompt, "size": args.size, "quality": args.quality, "n": 1}
    ).encode()
    return urllib.request.Request(
        url,
        data=payload,
        headers={"api-key": key, "Content-Type": "application/json"},
        method="POST",
    )


def build_edit_request(url, key, args):
    fields = [("prompt", args.prompt), ("size", args.size), ("quality", args.quality), ("n", 1)]
    files = []
    # When more than one image is supplied, use the image[] array field name.
    img_field = "image" if len(args.image) == 1 else "image[]"
    for p in args.image:
        with open(p, "rb") as fh:
            files.append((img_field, os.path.basename(p), fh.read(), _mime_for(p)))
    if args.mask:
        with open(args.mask, "rb") as fh:
            files.append(("mask", os.path.basename(args.mask), fh.read(), _mime_for(args.mask)))
    ctype, body = encode_multipart(fields, files)
    return urllib.request.Request(
        url,
        data=body,
        headers={"api-key": key, "Content-Type": ctype},
        method="POST",
    )


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

    mode = "edits" if args.image else "generations"
    url = f"{endpoint}/openai/deployments/{deployment}/images/{mode}?api-version={api_version}"
    if args.image:
        req = build_edit_request(url, key, args)
    else:
        req = build_generation_request(url, key, args)

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
    verb = "edited" if args.image else "saved"
    print(f"OK: {verb} {args.size} image -> {out} ({size_kb} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
