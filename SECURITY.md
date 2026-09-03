# Security Policy

## Reporting
Email the maintainer privately (GitHub → profile → email, or open a
**confidential** draft advisory). Include: what broke, minimal repro, which
runtime (docker/local), and whether real API keys were involved.

## Expectations
- We triage within ~1 week; fixes ship in point releases.
- Sandbox-escape and prompt-injection-to-host-exec chains are always in scope.
- The command denylist is defense-in-depth: bypasses that *only* break the
  denylist but not the container boundary are low severity — still report them.

## Supported versions
| Version | Status |
|---|---|
| 0.1.x | ✅ active |
| < 0.1 | best-effort |

Read [docs/security.md](docs/security.md) for the runtime threat model.
