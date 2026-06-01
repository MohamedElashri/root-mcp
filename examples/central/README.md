# Central Deployment Examples

These examples are starting points for the `central` Streamable HTTP profile.
Replace hosts, origins, issuers, resource URIs, roles, image names, and mount
paths before use.

## Files

- `reverse-proxy-trusted-headers.yaml`: central service behind a trusted
  reverse proxy that injects identity headers.
- `oidc-xrootd.yaml`: central service validating OIDC bearer tokens and
  reading remote XRootD resources only.
- `local-readonly-volume.yaml`: central service reading a local data volume
  mounted read-only.
- `kubernetes/`: sample Deployment, Service, ConfigMap, Secret reference, and
  NetworkPolicy.

## Run Locally For Validation

```bash
root-mcp serve-http \
  --config examples/central/reverse-proxy-trusted-headers.yaml \
  --profile central \
  --auth-required \
  --auth-provider trusted-headers \
  --origin https://analysis.example.org
```

For OIDC bearer-token deployments:

```bash
root-mcp serve-http \
  --config examples/central/oidc-xrootd.yaml \
  --profile central \
  --auth-required \
  --auth-provider external-bearer \
  --origin https://analysis.example.org
```

Native ROOT execution remains disabled in all central examples:

```yaml
features:
  enable_root: false

root_native:
  execution_backend: "disabled"
```

## Operator Maintenance

Preview configured export cleanup:

```bash
root-mcp cleanup-exports --config examples/central/reverse-proxy-trusted-headers.yaml --dry-run
```

Run an external-process MCP HTTP smoke test:

```bash
python scripts/smoke_external_http_client.py
```
