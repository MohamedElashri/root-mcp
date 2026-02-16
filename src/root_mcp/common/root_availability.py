"""Detection and availability checking for native ROOT/PyROOT."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

# Cached results — computed once per process
_root_available: bool | None = None
_root_version: str | None = None
_root_features: dict[str, bool] | None = None


def _probe_root_subprocess() -> dict[str, Any]:
    """
    Probe for ROOT in a subprocess to avoid polluting the main process.

    ROOT's import can install signal handlers, modify global state, and in
    rare cases segfault. Running the probe in a subprocess keeps the MCP
    server process clean.

    Returns:
        Dict with keys: available, version, features
    """
    probe_code = """
import json, sys
result = {"available": False, "version": None, "features": {}}
try:
    import ROOT
    result["available"] = True
    result["version"] = ROOT.gROOT.GetVersion()

    # Probe for optional ROOT components
    features = {}

    # RDataFrame
    try:
        _ = ROOT.RDataFrame
        features["rdataframe"] = True
    except AttributeError:
        features["rdataframe"] = False

    # RooFit
    try:
        _ = ROOT.RooRealVar
        features["roofit"] = True
    except Exception:
        features["roofit"] = False

    # TMVA
    try:
        _ = ROOT.TMVA
        features["tmva"] = True
    except Exception:
        features["tmva"] = False

    # Minuit2
    try:
        _ = ROOT.Minuit2.Minuit2Minimizer
        features["minuit2"] = True
    except Exception:
        features["minuit2"] = False

    result["features"] = features
except ImportError:
    pass
except Exception as e:
    result["error"] = str(e)

print(json.dumps(result))
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", probe_code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            import json

            return json.loads(proc.stdout.strip())
        else:
            logger.debug(
                "ROOT probe subprocess failed: rc=%d stderr=%s",
                proc.returncode,
                proc.stderr[:200] if proc.stderr else "",
            )
            return {"available": False, "version": None, "features": {}}
    except subprocess.TimeoutExpired:
        logger.warning("ROOT probe subprocess timed out after 30s")
        return {"available": False, "version": None, "features": {}}
    except Exception as e:
        logger.warning("ROOT probe subprocess error: %s", e)
        return {"available": False, "version": None, "features": {}}


def _ensure_probed() -> None:
    """Run the ROOT probe if not already done, caching results."""
    global _root_available, _root_version, _root_features

    if _root_available is not None:
        return

    logger.info("Probing for native ROOT/PyROOT installation...")
    result = _probe_root_subprocess()

    _root_available = result.get("available", False)
    _root_version = result.get("version")
    _root_features = result.get("features", {})

    if _root_available:
        logger.info("Native ROOT %s detected", _root_version)
    else:
        logger.info("Native ROOT not available")


def is_root_available() -> bool:
    """
    Check whether native ROOT/PyROOT is importable.

    Result is cached after the first call.
    """
    _ensure_probed()
    return _root_available  # type: ignore[return-value]


def get_root_version() -> str | None:
    """
    Get the ROOT version string (e.g. '6.32/02'), or None if not available.

    Result is cached after the first call.
    """
    _ensure_probed()
    return _root_version


def get_root_features() -> dict[str, bool]:
    """
    Get a dict of optional ROOT feature availability.

    Example return:
        {"rdataframe": True, "roofit": True, "tmva": False, "minuit2": True}

    Returns empty dict if ROOT is not available.
    Result is cached after the first call.
    """
    _ensure_probed()
    return _root_features or {}


def reset_cache() -> None:
    """
    Reset the cached probe results.

    Useful for testing or after environment changes.
    """
    global _root_available, _root_version, _root_features
    _root_available = None
    _root_version = None
    _root_features = None
