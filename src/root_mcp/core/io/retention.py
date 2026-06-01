"""Export retention and cleanup helpers."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from root_mcp.config import Config


def cleanup_exports(
    config: Config, *, dry_run: bool = False, now: float | None = None
) -> dict[str, Any]:
    """Apply configured export retention policy under ``output.export_base_path``.

    Retention is intentionally explicit and operator-driven. The server does
    not delete artifacts during tool calls; deployments can run
    ``root-mcp cleanup-exports`` from cron, a Kubernetes CronJob, or another
    controlled maintenance path.
    """
    export_base = Path(config.output.export_base_path).resolve()
    result: dict[str, Any] = {
        "export_base_path": str(export_base),
        "dry_run": dry_run,
        "retention_days": config.output.retention_days,
        "max_total_bytes": config.output.max_total_bytes,
        "deleted_files": [],
        "deleted_bytes": 0,
        "remaining_bytes": 0,
    }

    if not export_base.exists():
        return result
    if not export_base.is_dir():
        raise ValueError(f"export_base_path is not a directory: {export_base}")

    files = _export_files(export_base)
    to_delete: dict[Path, int] = {}

    timestamp = time.time() if now is None else now
    if config.output.retention_days is not None:
        cutoff = timestamp - (config.output.retention_days * 24 * 60 * 60)
        for file_path, size, mtime in files:
            if mtime < cutoff:
                to_delete[file_path] = size

    max_total = config.output.max_total_bytes
    remaining = [(path, size, mtime) for path, size, mtime in files if path not in to_delete]
    total_remaining = sum(size for _, size, _ in remaining)
    if max_total is not None and total_remaining > max_total:
        for file_path, size, _mtime in sorted(remaining, key=lambda item: item[2]):
            if total_remaining <= max_total:
                break
            to_delete[file_path] = size
            total_remaining -= size

    for file_path, size in sorted(to_delete.items(), key=lambda item: str(item[0])):
        result["deleted_files"].append(str(file_path))
        result["deleted_bytes"] += size
        if not dry_run:
            file_path.unlink(missing_ok=True)

    if not dry_run:
        _remove_empty_dirs(export_base)
        files = _export_files(export_base)
    else:
        files = [(path, size, mtime) for path, size, mtime in files if path not in to_delete]
    result["remaining_bytes"] = sum(size for _, size, _ in files)
    return result


def _export_files(export_base: Path) -> list[tuple[Path, int, float]]:
    files: list[tuple[Path, int, float]] = []
    for path in export_base.rglob("*"):
        if not path.is_file():
            continue
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(export_base)
            stat = resolved.stat()
        except (OSError, ValueError):
            continue
        files.append((resolved, stat.st_size, stat.st_mtime))
    return files


def _remove_empty_dirs(export_base: Path) -> None:
    for path in sorted(export_base.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path == export_base or not path.is_dir():
            continue
        try:
            path.rmdir()
        except OSError:
            pass
