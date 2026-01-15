from pathlib import Path


def test_run_ps1_default_command():
    content = Path("run.ps1").read_text(encoding="utf-8-sig")
    assert '$Command = "all"' in content
