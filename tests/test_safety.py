import pytest
from eks_sre_agent.safety import validate_command, SafetyViolation

@pytest.mark.parametrize("cmd", [
    ["kubectl", "get", "pods", "-A"],
    ["kubectl", "describe", "node", "x"],
    ["kubectl", "logs", "pod/x"],
    ["kubectl", "top", "nodes"],
    ["kubectl", "config", "current-context"],
])
def test_read_commands_allowed(cmd):
    validate_command(cmd)

@pytest.mark.parametrize("cmd", [
    ["kubectl", "delete", "pod", "x"],
    ["kubectl", "apply", "-f", "x.yaml"],
    ["kubectl", "scale", "deploy/x", "--replicas=0"],
    ["kubectl", "rollout", "restart", "deploy/x"],
    ["kubectl", "exec", "x", "--", "sh"],
])
def test_write_or_interactive_commands_blocked(cmd):
    with pytest.raises(SafetyViolation):
        validate_command(cmd)
