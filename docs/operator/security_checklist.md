# Central Security Checklist

Use this checklist before exposing ROOT-MCP as a shared Streamable HTTP
service.

## Startup Policy

- [ ] `deployment.profile` is `central`.
- [ ] `deployment.transport` is `streamable_http`.
- [ ] `auth.required` is `true`.
- [ ] `auth.provider` is `trusted_headers` or `external_bearer`, never `none`.
- [ ] `http.origin_allowlist` contains only approved client origins.
- [ ] `http.require_origin_header` is `true`.
- [ ] Public bind addresses use `http.allow_public_bind: true` only when the
  network boundary is intentional.
- [ ] `policy.default_tool_action` is `deny`.
- [ ] `policy.allow_tools` contains only approved central tools.
- [ ] `switch_mode`, `run_root_code`, `run_rdataframe`, and `run_root_macro`
  are denied or absent from the allow-list.

## Data Access

- [ ] Central callers use named resources, not raw host paths.
- [ ] `policy.require_named_resources` is `true`.
- [ ] `policy.allow_central_absolute_paths` is `false`.
- [ ] `policy.disable_local_absolute_paths` is `true` for remote-only
  deployments.
- [ ] Local mounted data resources have matching `security.allowed_roots`.
- [ ] Mounted input volumes are read-only.
- [ ] Resource `allowed_roles` or `allowed_principals` reflect the intended
  audience.
- [ ] `allow_export` is enabled only for resources where server-side exports
  are acceptable.
- [ ] `allowed_patterns` and `excluded_patterns` limit resource traversal to
  intended ROOT files.

## Native ROOT

- [ ] `features.enable_root` is `false` in central deployments.
- [ ] `root_native.execution_backend` is `disabled`.
- [ ] Operators understand that `local_subprocess` is local-only and must not
  be used as a central arbitrary-code sandbox.

## Quotas And Runtime Limits

- [ ] Per-principal and per-tenant concurrency limits are configured.
- [ ] `quotas.max_request_seconds` is set to a bounded value.
- [ ] Row and output byte quotas are set for the expected workloads.
- [ ] Container CPU and memory limits are configured.
- [ ] Export directories have filesystem quotas or retention automation.
- [ ] Cache sizing is appropriate for the service memory budget.

## Container And Kubernetes

- [ ] The container runs as a non-root user.
- [ ] Root filesystem is read-only where possible.
- [ ] Writable mounts are limited to exports, temporary files, and explicit
  work/cache directories.
- [ ] No host root, Docker socket, broad home directory, or ambient credential
  mounts are present.
- [ ] Kubernetes Service is internal unless intentionally exposed through an
  authenticated ingress or gateway.
- [ ] NetworkPolicy or equivalent firewalling limits inbound traffic to the
  proxy/client path.
- [ ] Egress is limited to required identity provider, data endpoints, DNS, and
  log sinks.
- [ ] Secrets are provided by the platform secret store, not committed YAML.

## Audit And Incident Response

- [ ] `root_mcp.security.audit` logs are collected centrally.
- [ ] JSONL audit output is configured when logger collection alone is not
  sufficient.
- [ ] Audit retention covers allowed calls, denied calls, failures, and
  timeouts.
- [ ] Operators can search by `request_id`, principal, tenant, tool, resource,
  and status.
- [ ] A runbook exists for rotating OIDC/JWKS or reverse-proxy credentials.
- [ ] A runbook exists for disabling one resource quickly.
- [ ] A runbook exists for disabling one tool by editing `policy.allow_tools`
  or `policy.deny_tools`.
- [ ] A runbook exists for purging scoped exports for a tenant or principal.
- [ ] `root-mcp cleanup-exports --dry-run` is tested against the configured
  retention policy.
- [ ] A runbook exists for increasing deny logging and preserving evidence
  during suspected abuse.
- [ ] An external MCP client smoke test has been run against the deployed HTTP
  endpoint before broad access is granted.

## Incident Actions

Credential issue:

1. Rotate the upstream identity provider or reverse-proxy credential.
2. Restart or reload the proxy and ROOT-MCP deployment if cached config is in
   use.
3. Search audit logs for calls from affected principals and tenants.

Resource exposure:

1. Remove or disable the affected `resources` entry.
2. Set `allow_listing`, `allow_read`, and `allow_export` to `false` while
   investigating.
3. Restart the deployment with the restricted config.
4. Review audit logs for matching resource references.

Tool abuse:

1. Remove the tool from `policy.allow_tools`.
2. Add it to `policy.deny_tools` for an explicit denial record.
3. Lower quotas if the issue involves expensive but otherwise allowed tools.
4. Preserve audit logs and exported artifacts before cleanup.

Export cleanup:

1. Identify the scoped export directory by tenant, principal, and session.
2. Archive or preserve files needed for investigation.
3. Purge only the affected scoped directory.
4. Confirm the service account cannot write outside `output.export_base_path`.
