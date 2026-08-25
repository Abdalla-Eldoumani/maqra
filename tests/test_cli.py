import json
import subprocess
import sys
from pathlib import Path


def _run(*args, cwd: Path, env=None):
    return subprocess.run([sys.executable, "-m", "maqra", *args], capture_output=True, text=True, cwd=cwd, env=env)


def test_cli_list_and_status(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path / "data"
    res = _run("list", "--root", str(root), cwd=repo)
    assert res.returncode == 0, res.stderr
    assert "mishari-alafasy-64kbps" in res.stdout and res.stdout.strip().endswith("80 sets")
    res = _run("status", "--root", str(root), cwd=repo)
    assert res.returncode == 0
    assert "pending 80" in res.stdout


def test_cli_only_selector_rejects_unknown(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    res = _run("list", "--root", str(tmp_path), "--only", "nobody", cwd=repo)
    assert res.returncode != 0
    assert "unknown reciter selector" in res.stderr
