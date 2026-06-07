from pathlib import Path

from archive import apply_local_retention, create_archive, extract_archive, sha256sum


def test_archive_roundtrip_and_sha(tmp_path: Path):
    src = tmp_path / "src"
    (src / "database").mkdir(parents=True)
    (src / "database" / "database.dump").write_bytes(b"dummy-dump")
    (src / "manifest.json").write_text("{}")

    archive = tmp_path / "snap.tar.gz"
    create_archive(src, archive)
    assert archive.exists()
    assert len(sha256sum(archive)) == 64

    out = extract_archive(archive, tmp_path / "out")
    assert (out / "database" / "database.dump").read_bytes() == b"dummy-dump"


def test_local_retention_keeps_newest(tmp_path: Path):
    for name in ["2026-01-01_00-00-00", "2026-02-01_00-00-00", "2026-03-01_00-00-00"]:
        (tmp_path / f"{name}.tar.gz").write_bytes(b"x")
        (tmp_path / f"{name}.manifest.json").write_text("{}")

    deleted = apply_local_retention(tmp_path, keep=2)
    assert deleted == 1
    remaining = sorted(p.name for p in tmp_path.glob("*.tar.gz"))
    assert remaining == ["2026-02-01_00-00-00.tar.gz", "2026-03-01_00-00-00.tar.gz"]
    # oldest manifest pruned too
    assert not (tmp_path / "2026-01-01_00-00-00.manifest.json").exists()
