from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass
from .safety import validate_command

@dataclass
class Result:
    argv: list[str]
    stdout: str
    stderr: str
    returncode: int

    def json(self):
        return json.loads(self.stdout or "{}")

class CommandRunner:
    def run(self, argv: list[str], timeout: int = 60, check: bool = True) -> Result:
        validate_command(argv)
        p = subprocess.run(argv, text=True, capture_output=True, timeout=timeout)
        result = Result(argv, p.stdout, p.stderr, p.returncode)
        if check and p.returncode != 0:
            raise RuntimeError(f"Read-only command failed ({p.returncode}): {argv[0]} {argv[1] if len(argv)>1 else ''}: {p.stderr[:500]}")
        return result
