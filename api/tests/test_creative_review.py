"""M3 acceptance: automated creative review (15s 1080p approved, vertical pillarboxed,
3s rejected). Exercises the real ffprobe path on ffmpeg-generated clips."""
import subprocess

from app.models.creative import ReviewStatus
from app.services.creative_processing import probe, review_decision, transcode_1080p


def _gen(path: str, dur: int, w: int, h: int) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration={dur}:size={w}x{h}:rate=30",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", path],
        capture_output=True, text=True, check=True,
    )


def test_review_decision_rules():
    assert review_decision(4000, 1920, 1080)[0] == ReviewStatus.rejected
    assert review_decision(95000, 1920, 1080)[0] == ReviewStatus.rejected
    assert review_decision(15000, 1920, 1080)[0] == ReviewStatus.approved
    status, note = review_decision(15000, 1080, 1920)  # vertical → pillarboxed, still approved
    assert status == ReviewStatus.approved and "pillar" in note.lower()
    assert review_decision(0, 0, 0)[0] == ReviewStatus.rejected


def test_ffmpeg_probe_and_review(tmp_path):
    cases = [
        (tmp_path / "good.mp4", 15, 1920, 1080, ReviewStatus.approved),
        (tmp_path / "vertical.mp4", 10, 1080, 1920, ReviewStatus.approved),
        (tmp_path / "short.mp4", 3, 1920, 1080, ReviewStatus.rejected),
    ]
    for path, dur, w, h, expected in cases:
        _gen(str(path), dur, w, h)
        d_ms, pw, ph = probe(str(path))
        assert (pw, ph) == (w, h)
        assert review_decision(d_ms, pw, ph)[0] == expected


def test_transcode_outputs_1080p(tmp_path):
    src = tmp_path / "vertical.mp4"
    _gen(str(src), 6, 720, 1280)  # vertical source
    out = tmp_path / "out.mp4"
    transcode_1080p(str(src), str(out))
    assert out.exists()
    w, h = probe(str(out))[1:]
    assert (w, h) == (1920, 1080)  # pillarboxed to 16:9 1080p
