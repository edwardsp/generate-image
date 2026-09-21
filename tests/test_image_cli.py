import base64
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_image.py"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
)


@pytest.mark.parametrize("edit", [False, True])
def test_cli_when_explicit_model_overrides_environment(edit: bool, tmp_path: Path) -> None:
    # Given a local HTTP endpoint that checks the actual CLI request on the wire.
    paths: list[str] = []
    bodies: list[bytes] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            paths.append(self.path)
            bodies.append(self.rfile.read(int(self.headers["Content-Length"])))
            body = json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}]}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.timeout = 10
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()
        output = tmp_path / "output.png"
        source = tmp_path / "source.png"
        source.write_bytes(PNG)
        env = dict(os.environ, AZURE_OPENAI_API_KEY="test-key",
                   AZURE_OPENAI_ENDPOINT=f"http://127.0.0.1:{server.server_port}",
                   AZURE_OPENAI_IMAGE_DEPLOYMENT="wrong-deployment",
                   AZURE_OPENAI_IMAGE_API_VERSION="test-version")
        argv = [sys.executable, str(SCRIPT), "prompt", str(output), "--model", "flare",
                "--size", "1536x864"]
        if edit:
            argv.extend(["--image", str(source), "--mask", str(source)])
        # When invoking the real executable.
        result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=15, check=False)
        thread.join(timeout=12)
    # Then the selected deployment, API version and payload reach the server and output is saved.
    assert result.returncode == 0, result.stderr
    mode = "edits" if edit else "generations"
    assert paths == [f"/openai/deployments/gpt-image-2.5-flare/images/{mode}?api-version=test-version"]
    assert output.read_bytes() == PNG
    if edit:
        assert b'name="mask"' in bodies[0]
        assert b'name="image"' in bodies[0]
    else:
        assert json.loads(bodies[0])["size"] == "1536x864"


def test_cli_when_size_invalid(tmp_path: Path) -> None:
    # Given invalid geometry and no reachable inference service.
    output = tmp_path / "output.png"
    env = dict(os.environ, AZURE_OPENAI_ENDPOINT="http://127.0.0.1:1")
    # When invoking the real executable.
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "prompt", str(output), "--model", "sunburst",
         "--size", "1920x1080"], env=env, capture_output=True, text=True, timeout=10, check=False,
    )
    # Then argument validation fails without producing an image.
    assert result.returncode == 2
    assert not output.exists()
