from __future__ import annotations
import shlex

KUBECTL_ALLOWED = {"get", "describe", "logs", "top", "api-resources", "api-versions", "version", "cluster-info", "config"}
KUBECTL_DENIED = {
    "delete", "patch", "edit", "apply", "replace", "scale", "drain", "cordon",
    "uncordon", "create", "set", "annotate", "label", "taint", "exec", "cp",
    "attach", "port-forward", "proxy", "run", "expose"
}
AWS_DENIED_FRAGMENTS = {
    "terminate", "delete", "modify", "update", "create", "put-", "start-", "stop-",
    "reboot", "detach", "attach", "set-", "register-", "deregister-"
}

class SafetyViolation(RuntimeError):
    pass

def validate_command(argv: list[str]) -> None:
    if not argv:
        raise SafetyViolation("Empty command")
    exe = argv[0].split("/")[-1]

    if exe == "kubectl":
        if len(argv) < 2:
            raise SafetyViolation("kubectl subcommand required")
        sub = argv[1]
        if sub in KUBECTL_DENIED or sub not in KUBECTL_ALLOWED:
            raise SafetyViolation(f"kubectl operation blocked by read-only policy: {sub}")
        if sub == "config":
            # Only context inspection is permitted.
            if len(argv) < 3 or argv[2] not in {"current-context", "view"}:
                raise SafetyViolation("kubectl config mutation blocked")
        return

    if exe == "aws":
        joined = " ".join(argv[1:]).lower()
        if any(fragment in joined for fragment in AWS_DENIED_FRAGMENTS):
            raise SafetyViolation(f"AWS write-like operation blocked: {shlex.join(argv)}")
        return

    if exe == "kconnect":
        return

    raise SafetyViolation(f"Executable not allowlisted: {exe}")
