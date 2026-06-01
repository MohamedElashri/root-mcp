"""End-to-end checks for central deployment examples."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from root_mcp.config import Config, validate_deployment_config

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "central"


def _load_config(path: Path) -> Config:
    return Config(**yaml.safe_load(path.read_text()))


def _load_kubernetes_configmap_config() -> Config:
    manifest = yaml.safe_load((EXAMPLES_DIR / "kubernetes" / "configmap.yaml").read_text())
    return Config(**yaml.safe_load(manifest["data"]["config.yaml"]))


def _all_central_configs() -> list[tuple[str, Config]]:
    configs = [(path.name, _load_config(path)) for path in sorted(EXAMPLES_DIR.glob("*.yaml"))]
    configs.append(("kubernetes/configmap.yaml", _load_kubernetes_configmap_config()))
    return configs


def test_all_central_yaml_examples_parse() -> None:
    yaml_files = sorted(EXAMPLES_DIR.rglob("*.yaml"))

    assert yaml_files
    for path in yaml_files:
        assert list(yaml.safe_load_all(path.read_text())), path


def test_root_mcp_central_examples_validate() -> None:
    for name, config in _all_central_configs():
        validate_deployment_config(config), name


def test_central_examples_keep_restrictive_security_posture() -> None:
    for name, config in _all_central_configs():
        assert config.deployment.profile == "central", name
        assert config.deployment.transport == "streamable_http", name
        assert config.auth.required is True, name
        assert config.auth.provider != "none", name
        assert config.http.origin_allowlist, name
        assert config.http.require_origin_header is True, name
        assert config.policy.default_tool_action == "deny", name
        assert config.policy.require_named_resources is True, name
        assert config.policy.allow_central_absolute_paths is False, name
        assert "switch_mode" in config.policy.deny_tools, name
        assert "run_root_code" in config.policy.deny_tools, name
        assert "run_rdataframe" in config.policy.deny_tools, name
        assert "run_root_macro" in config.policy.deny_tools, name
        assert config.features.enable_root is False, name
        assert config.root_native.execution_backend == "disabled", name


def test_remote_only_examples_disable_local_paths() -> None:
    for filename in ("oidc-xrootd.yaml",):
        config = _load_config(EXAMPLES_DIR / filename)

        assert config.policy.disable_local_absolute_paths is True
        assert config.security.allowed_roots == []
        assert "file" not in config.security.allowed_protocols


def test_local_volume_examples_pin_allowed_roots() -> None:
    for filename in ("reverse-proxy-trusted-headers.yaml", "local-readonly-volume.yaml"):
        config = _load_config(EXAMPLES_DIR / filename)

        assert config.security.allowed_roots
        for resource in config.resources:
            if resource.uri.startswith("file://"):
                assert any(
                    resource.uri.removeprefix("file://").startswith(root)
                    for root in config.security.allowed_roots
                )


def test_kubernetes_deployment_uses_container_hardening_defaults() -> None:
    manifest: dict[str, Any] = yaml.safe_load(
        (EXAMPLES_DIR / "kubernetes" / "deployment.yaml").read_text()
    )
    pod_spec = manifest["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]

    assert pod_spec["automountServiceAccountToken"] is False
    assert pod_spec["securityContext"]["runAsNonRoot"] is True
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert "requests" in container["resources"]
    assert "limits" in container["resources"]
