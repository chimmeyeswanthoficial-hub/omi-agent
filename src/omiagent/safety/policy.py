"""Command denylist — the belt to the sandbox's suspenders.

Kept deliberately short and readable. It blocks obviously host-destroying or
escape-yield patterns; containment itself is the runtime's job.
"""

from __future__ import annotations

import re

_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("recursive delete at filesystem root", re.compile(r"rm\s+(-[a-zA-Z]+\s+)*/(\s|$)", re.I)),
    ("recursive delete of home", re.compile(r"rm\s+(-[a-zA-Z]+\s+)*~/?(\s|$)", re.I)),
    ("disk formatting (mkfs)", re.compile(r"\bmkfs(\.\w+)?\b", re.I)),
    ("raw disk write (dd to /dev)", re.compile(r"\bdd\b[^|;&]*of=/dev/", re.I)),
    ("fork bomb", re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;")),
    ("privilege escalation (sudo)", re.compile(r"(^|[\s;&|])sudo\s", re.I)),
    (
        "container escape surface (docker/podman CLI)",
        re.compile(r"(^|[\s;&|])(docker|podman)\s", re.I),
    ),
    ("host service control (systemctl)", re.compile(r"(^|[\s;&|])systemctl\s", re.I)),
    ("power control", re.compile(r"(^|[\s;&|])(shutdown|reboot|poweroff|halt)(\s|$)", re.I)),
    ("filesystem table change (mount)", re.compile(r"(^|[\s;&|])mount\s", re.I)),
    (
        "pipe-to-shell remote execution",
        re.compile(r"(curl|wget)[^|;&]*\|\s*(sudo\s+)?(ba|z)?sh\b", re.I),
    ),
    ("kernel module loading", re.compile(r"(^|[\s;&|])(insmod|modprobe)\s", re.I)),
    ("firewall tampering", re.compile(r"(^|[\s;&|])iptables\s", re.I)),
]


def check_command(cmd: str) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    for label, pat in _RULES:
        if pat.search(cmd):
            return False, f"blocked by policy: {label}"
    return True, ""
