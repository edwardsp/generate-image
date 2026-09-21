import json
from pathlib import Path

import generate_image as image
import pytest


@pytest.mark.parametrize(
    ("option", "expected"),
    [("flare", "gpt-image-2.5-flare"), ("sunburst", "gpt-image-2.5-sunburst"),
     ("gpt-image-2", "gpt-image-2"),
     ("gpt-image-2.5-flare", "gpt-image-2.5-flare"),
     ("gpt-image-2.5-sunburst", "gpt-image-2.5-sunburst")],
)
def test_model_selection_when_explicit(option: str, expected: str,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    # Given an environment deployment that must not override explicit selection.
    monkeypatch.setenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "environment-deployment")
    # When a model is selected.
    args = image.parse_args(["prompt", "result", "--model", option])
    # Then its canonical deployment is selected.
    assert args.deployment == expected


def test_deployment_override_when_model_profile_selected() -> None:
    # Given a custom deployment with a known model profile.
    argv = ["prompt", "out", "--model", "sunburst", "--deployment", "custom",
            "--quality", "max"]
    # When parsed.
    args = image.parse_args(argv)
    # Then the custom deployment wins, retaining model-specific validation.
    assert args.deployment == "custom"


def test_environment_deployment_when_model_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given a legacy custom deployment override.
    monkeypatch.setenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "custom-old-deployment")
    # When using positional shorthand.
    args = image.parse_args(["prompt", "result"])
    # Then the override and filename behavior survive.
    assert (args.deployment, args.out) == ("custom-old-deployment", "result.png")


def test_default_when_no_override(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given no configured deployment.
    monkeypatch.delenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", raising=False)
    # When using the default CLI.
    args = image.parse_args(["prompt", "out"])
    # Then Flare is the default.
    assert args.deployment == "gpt-image-2.5-flare"


@pytest.mark.parametrize("size", ["auto", "1536x864", "2560x1440", "3840x2160",
                                  "1024x1024", "1024x1536", "1536x1024"])
def test_size_when_supported(size: str) -> None:
    # Given a supported model and output geometry.
    argv = ["prompt", "out", "--model", "flare", "--size", size]
    # When parsed.
    args = image.parse_args(argv)
    # Then the native size is preserved without resizing.
    assert args.size == size


@pytest.mark.parametrize("extra", [
    ["--model", "not-a-model"], ["--quality", "ultra"],
    ["--model", "gpt-image-2", "--quality", "max"],
    ["--size", "1920x1080"], ["--size", "4096x2160"],
    ["--size", "512x512"], ["--size", "3840x3840"],
    ["--size", "3072x512"], ["--size", "0x1024"],
    ["--size", "garbage"], ["--deployment", "bad/name"],
])
def test_validation_when_unsupported(extra: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Given the known default model and invalid options.
    monkeypatch.delenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", raising=False)
    # When parsed, then fail before making a paid request.
    with pytest.raises(SystemExit) as error:
        image.parse_args(["prompt", "out", *extra])
    assert error.value.code == 2


@pytest.mark.parametrize("quality", ["xhigh", "max"])
def test_extended_quality_when_new_model(quality: str) -> None:
    # Given the new model quality controls.
    argv = ["prompt", "out", "--model", "sunburst", "--quality", quality]
    # When constructing a generation request.
    request = image.build_generation_request("https://example.test", "test-key",
                                             image.parse_args(argv))
    # Then quality is passed through unchanged.
    assert request.data is not None
    assert json.loads(request.data)["quality"] == quality


def test_generation_request_when_no_reference() -> None:
    # Given the legacy generation arguments.
    args = image.parse_args(["prompt", "out"])
    # When constructing the JSON request.
    request = image.build_generation_request("https://example.test", "test-key", args)
    # Then the existing payload is unchanged.
    assert request.data is not None
    assert json.loads(request.data) == {
        "prompt": "prompt", "size": "1024x1024", "quality": "high", "n": 1,
    }


@pytest.mark.parametrize("count", [1, 2])
def test_edit_request_when_references_and_mask(count: int, tmp_path: Path) -> None:
    # Given reference files and a mask.
    source = tmp_path / "source.png"
    mask = tmp_path / "mask.png"
    source.write_bytes(b"reference-content")
    mask.write_bytes(b"mask-content")
    argv = ["prompt", "out", "--mask", str(mask)] + ["-i", str(source)] * count
    # When constructing the multipart edit request.
    request = image.build_edit_request("https://example.test", "test-key",
                                      image.parse_args(argv))
    # Then references and the mask retain their API field names and contents.
    assert request.data is not None
    field = b'name="image"' if count == 1 else b'name="image[]"'
    assert request.data.count(field) == count
    assert b'name="mask"' in request.data
    assert b"mask-content" in request.data


def test_mask_when_reference_missing(tmp_path: Path) -> None:
    # Given an existing mask but no reference image.
    mask = tmp_path / "mask.png"
    mask.write_bytes(b"mask")
    # When parsed, then reject the invalid edit.
    with pytest.raises(SystemExit) as error:
        image.parse_args(["prompt", "out", "--mask", str(mask)])
    assert error.value.code == 2


def test_env_file_when_process_override_exists(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    # Given conflicting process and file values.
    env = tmp_path / "test.env"
    env.write_text('AZURE_OPENAI_IMAGE_DEPLOYMENT="file-deployment"\n')
    monkeypatch.setenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "process-deployment")
    # When loading defaults.
    image.load_env_file(str(env))
    # Then existing environment overrides survive.
    assert image.parse_args(["prompt", "out"]).deployment == "process-deployment"
