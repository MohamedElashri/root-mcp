"""Export retention cleanup tests."""

from __future__ import annotations

import os
from pathlib import Path

from root_mcp.config import Config, OutputConfig
from root_mcp.core.io.retention import cleanup_exports


def _write_file(path: Path, size: int, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    os.utime(path, (mtime, mtime))


def test_cleanup_exports_deletes_files_older_than_retention(tmp_path: Path) -> None:
    export_base = tmp_path / "exports"
    old_file = export_base / "tenant" / "alice" / "session" / "old.json"
    new_file = export_base / "tenant" / "alice" / "session" / "new.json"
    now = 100 + (2 * 24 * 60 * 60)
    _write_file(old_file, 10, mtime=100)
    _write_file(new_file, 20, mtime=now - 100)
    config = Config(output=OutputConfig(export_base_path=str(export_base), retention_days=1))

    result = cleanup_exports(config, now=now)

    assert result["deleted_files"] == [str(old_file.resolve())]
    assert result["deleted_bytes"] == 10
    assert old_file.exists() is False
    assert new_file.exists() is True
    assert result["remaining_bytes"] == 20


def test_cleanup_exports_dry_run_does_not_delete(tmp_path: Path) -> None:
    export_base = tmp_path / "exports"
    old_file = export_base / "old.json"
    _write_file(old_file, 10, mtime=100)
    config = Config(output=OutputConfig(export_base_path=str(export_base), retention_days=1))

    result = cleanup_exports(config, dry_run=True, now=100 + (2 * 24 * 60 * 60))

    assert result["deleted_files"] == [str(old_file.resolve())]
    assert old_file.exists() is True


def test_cleanup_exports_enforces_max_total_bytes_oldest_first(tmp_path: Path) -> None:
    export_base = tmp_path / "exports"
    oldest = export_base / "oldest.json"
    middle = export_base / "middle.json"
    newest = export_base / "newest.json"
    _write_file(oldest, 10, mtime=100)
    _write_file(middle, 10, mtime=200)
    _write_file(newest, 10, mtime=300)
    config = Config(output=OutputConfig(export_base_path=str(export_base), max_total_bytes=15))

    result = cleanup_exports(config)

    assert result["deleted_files"] == [str(middle.resolve()), str(oldest.resolve())]
    assert oldest.exists() is False
    assert middle.exists() is False
    assert newest.exists() is True
    assert result["remaining_bytes"] == 10
