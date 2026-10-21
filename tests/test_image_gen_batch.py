import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))

import image_gen


class _FakeProvider:
    provider_key = "fake"

    def __init__(self, delays=None, fail_times=0):
        self.delays = delays or []
        self.fail_times = fail_times
        self.calls = 0

    def resolve_size(self, size):
        return size

    def generate(self, prompt, size):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient error")
        import time

        time.sleep(self.delays[self.calls - 1] if self.calls <= len(self.delays) else 0)
        return b"fake-image-bytes"


def test_retry_succeeds_after_transient_failure(monkeypatch):
    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda cfg: [_FakeProvider(fail_times=1)])
    monkeypatch.setattr(image_gen.time, "sleep", lambda s: None)
    monkeypatch.setattr(image_gen, "_warn_size_mismatch", lambda *a: None)
    monkeypatch.setattr(image_gen, "_center_crop_to_ratio", lambda b, s: b)
    monkeypatch.setattr(image_gen, "_ensure_output_format", lambda b, p: b)
    out = Path("/tmp/opencode/test-retry.jpg")
    path = image_gen.generate_image("p", str(out), config={"image": {}})
    assert path == str(out)
    assert out.read_bytes() == b"fake-image-bytes"


def test_retry_exhausted_falls_to_next_provider(monkeypatch):
    bad = _FakeProvider(fail_times=99)
    good = _FakeProvider()
    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda cfg: [bad, good])
    monkeypatch.setattr(image_gen.time, "sleep", lambda s: None)
    monkeypatch.setattr(image_gen, "_warn_size_mismatch", lambda *a: None)
    monkeypatch.setattr(image_gen, "_center_crop_to_ratio", lambda b, s: b)
    monkeypatch.setattr(image_gen, "_ensure_output_format", lambda b, p: b)
    out = Path("/tmp/opencode/test-fallback.jpg")
    image_gen.generate_image("p", str(out), config={"image": {}})
    assert bad.calls == 3
    assert good.calls == 1


def test_batch_runs_concurrently(monkeypatch):
    import time

    def slow_generate(self, prompt, size):
        time.sleep(0.6)
        return b"img"

    monkeypatch.setattr(_FakeProvider, "generate", slow_generate)
    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda cfg: [_FakeProvider()])
    monkeypatch.setattr(image_gen, "_warn_size_mismatch", lambda *a: None)
    monkeypatch.setattr(image_gen, "_center_crop_to_ratio", lambda b, s: b)
    monkeypatch.setattr(image_gen, "_ensure_output_format", lambda b, p: b)
    monkeypatch.setattr(_FakeProvider, "resolve_size", lambda self, s: s)

    tasks = [
        {"prompt": f"p{i}", "output": f"/tmp/opencode/batch-{i}.jpg", "size": "square"}
        for i in range(4)
    ]
    t0 = time.time()
    results = image_gen.generate_images_batch(tasks, config={"image": {}}, max_workers=4)
    elapsed = time.time() - t0
    assert len(results["ok"]) == 4
    assert not results["failed"]
    assert elapsed < 4 * 0.6, f"expected concurrent run, took {elapsed:.2f}s"


def test_batch_reports_failures(monkeypatch):
    class _BoomProvider(_FakeProvider):
        provider_key = "boom"

        def generate(self, prompt, size):
            raise RuntimeError("api down")

    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda cfg: [_BoomProvider()])
    monkeypatch.setattr(image_gen, "_warn_size_mismatch", lambda *a: None)
    monkeypatch.setattr(image_gen, "_center_crop_to_ratio", lambda b, s: b)
    monkeypatch.setattr(image_gen, "_ensure_output_format", lambda b, p: b)
    monkeypatch.setattr(_FakeProvider, "resolve_size", lambda self, s: s)

    tasks = [{"prompt": "p", "output": "/tmp/opencode/batch-fail.jpg", "size": "square"}]
    results = image_gen.generate_images_batch(tasks, config={"image": {}}, max_workers=1)
    assert not results["ok"]
    assert "api down" in results["failed"]["/tmp/opencode/batch-fail.jpg"]
