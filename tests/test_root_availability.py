"""Tests for ROOT/PyROOT availability detection."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from root_mcp.common.root_availability import (
    is_root_available,
    get_root_version,
    get_root_features,
    reset_cache,
    _probe_root_subprocess,
)
from root_mcp.config import Config, FeatureFlags


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the cached probe results before and after each test."""
    reset_cache()
    yield
    reset_cache()


class TestProbeRootSubprocess:
    """Tests for the subprocess-based ROOT probe."""

    def test_probe_returns_dict(self):
        """Probe should always return a dict with expected keys."""
        result = _probe_root_subprocess()
        assert isinstance(result, dict)
        assert "available" in result
        assert "version" in result
        assert "features" in result

    def test_probe_handles_timeout(self):
        """Probe should handle subprocess timeout gracefully."""
        import subprocess

        with patch(
            "root_mcp.common.root_availability.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="test", timeout=30),
        ):
            result = _probe_root_subprocess()
            assert result["available"] is False
            assert result["version"] is None

    def test_probe_handles_subprocess_error(self):
        """Probe should handle general subprocess errors gracefully."""
        with patch(
            "root_mcp.common.root_availability.subprocess.run",
            side_effect=OSError("No such file"),
        ):
            result = _probe_root_subprocess()
            assert result["available"] is False

    def test_probe_handles_bad_returncode(self):
        """Probe should handle non-zero return code."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "error"

        with patch(
            "root_mcp.common.root_availability.subprocess.run",
            return_value=mock_proc,
        ):
            result = _probe_root_subprocess()
            assert result["available"] is False

    def test_probe_handles_invalid_json(self):
        """Probe should handle invalid JSON output gracefully."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "not json"
        mock_proc.stderr = ""

        with patch(
            "root_mcp.common.root_availability.subprocess.run",
            return_value=mock_proc,
        ):
            result = _probe_root_subprocess()
            assert result["available"] is False


class TestIsRootAvailable:
    """Tests for is_root_available()."""

    def test_returns_bool(self):
        """Should always return a bool."""
        result = is_root_available()
        assert isinstance(result, bool)

    def test_caches_result(self):
        """Should only probe once, then return cached result."""
        mock_result = {"available": True, "version": "6.32/02", "features": {"rdataframe": True}}
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ) as mock_probe:
            assert is_root_available() is True
            assert is_root_available() is True
            mock_probe.assert_called_once()

    def test_simulated_root_available(self):
        """Simulate ROOT being available."""
        mock_result = {
            "available": True,
            "version": "6.32/02",
            "features": {"rdataframe": True, "roofit": True, "tmva": False, "minuit2": True},
        }
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            assert is_root_available() is True
            assert get_root_version() == "6.32/02"
            features = get_root_features()
            assert features["rdataframe"] is True
            assert features["roofit"] is True
            assert features["tmva"] is False

    def test_simulated_root_not_available(self):
        """Simulate ROOT not being available."""
        mock_result = {"available": False, "version": None, "features": {}}
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            assert is_root_available() is False
            assert get_root_version() is None
            assert get_root_features() == {}


class TestGetRootVersion:
    """Tests for get_root_version()."""

    def test_returns_none_when_unavailable(self):
        """Should return None when ROOT is not installed."""
        mock_result = {"available": False, "version": None, "features": {}}
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            assert get_root_version() is None

    def test_returns_string_when_available(self):
        """Should return version string when ROOT is installed."""
        mock_result = {"available": True, "version": "6.32/02", "features": {}}
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            version = get_root_version()
            assert isinstance(version, str)
            assert version == "6.32/02"


class TestGetRootFeatures:
    """Tests for get_root_features()."""

    def test_returns_empty_dict_when_unavailable(self):
        """Should return empty dict when ROOT is not installed."""
        mock_result = {"available": False, "version": None, "features": {}}
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            assert get_root_features() == {}

    def test_returns_features_when_available(self):
        """Should return feature dict when ROOT is installed."""
        features = {"rdataframe": True, "roofit": True, "tmva": False, "minuit2": True}
        mock_result = {"available": True, "version": "6.32/02", "features": features}
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            result = get_root_features()
            assert result == features


class TestResetCache:
    """Tests for reset_cache()."""

    def test_reset_allows_reprobe(self):
        """After reset, the next call should probe again."""
        mock_result_1 = {"available": False, "version": None, "features": {}}
        mock_result_2 = {"available": True, "version": "6.32/02", "features": {}}

        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result_1,
        ):
            assert is_root_available() is False

        reset_cache()

        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result_2,
        ):
            assert is_root_available() is True


class TestFeatureFlagIntegration:
    """Tests for the enable_root feature flag in Config."""

    def test_default_enable_root_is_false(self):
        """enable_root should default to False."""
        config = Config()
        assert config.features.enable_root is False

    def test_enable_root_can_be_set_true(self):
        """enable_root can be set to True."""
        config = Config(features=FeatureFlags(enable_root=True))
        assert config.features.enable_root is True

    def test_root_native_enabled_logic(self):
        """root_native_enabled should require both flag and availability."""
        mock_result = {"available": True, "version": "6.32/02", "features": {}}

        def _is_enabled(config: Config) -> bool:
            return config.features.enable_root and is_root_available()

        # Flag off, ROOT available -> not enabled
        config = Config(features=FeatureFlags(enable_root=False))
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            assert not _is_enabled(config)

        reset_cache()

        # Flag on, ROOT available -> enabled
        config = Config(features=FeatureFlags(enable_root=True))
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result,
        ):
            assert _is_enabled(config)

        reset_cache()

        # Flag on, ROOT not available -> not enabled
        mock_result_no = {"available": False, "version": None, "features": {}}
        config = Config(features=FeatureFlags(enable_root=True))
        with patch(
            "root_mcp.common.root_availability._probe_root_subprocess",
            return_value=mock_result_no,
        ):
            assert not _is_enabled(config)
