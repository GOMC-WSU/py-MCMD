from __future__ import annotations

from pathlib import Path
import subprocess
import os
import stat

from utils.subprocess_runner import Command, DryRunSubprocessRunner, SubprocessRunner


def test_dry_run_creates_stdout_file(tmp_path: Path):
    runner = DryRunSubprocessRunner()
    cmd = Command(argv=["/bin/echo", "hello"], cwd=tmp_path, stdout_path=tmp_path / "out.dat")

    handle = runner.start(cmd)
    rc = runner.wait(handle)

    assert rc == 0
    assert (tmp_path / "out.dat").exists()
    assert "dry_run" in (tmp_path / "out.dat").read_text()


def test_runner_invokes_popen_with_cwd_and_redirect(monkeypatch, tmp_path: Path):
    calls = {}

    class DummyPopen:
        def __init__(self, args, cwd=None, stdout=None, stderr=None, text=None):
            calls["args"] = args
            calls["cwd"] = cwd
            calls["stdout"] = stdout
            calls["stderr"] = stderr
            calls["text"] = text
            self.pid = 12345
            self._py_mcmd_out_fh = stdout

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)

    runner = SubprocessRunner(dry_run=False)
    cmd = Command(argv=["/bin/echo", "hello"], cwd=tmp_path, stdout_path=tmp_path / "out.dat")

    handle = runner.start(cmd)
    rc = runner.wait(handle)

    assert rc == 0
    assert calls["args"] == ["/bin/echo", "hello"]
    assert calls["cwd"] == str(tmp_path)
    assert calls["stderr"] == subprocess.STDOUT
    assert calls["text"] is True
    assert Path(calls["stdout"].name) == tmp_path / "out.dat"

def test_dry_run_fifo_mode_keeps_fifo_and_writes_disk_mirror(tmp_path: Path):
    runner = DryRunSubprocessRunner()

    fifo_path = tmp_path / "stdout.pipe"
    os.mkfifo(fifo_path)
    disk_path = tmp_path / "out.dat"

    cmd = Command(
        argv=["/bin/echo", "hello"],
        cwd=tmp_path,
        stdout_fifo_path=fifo_path,
        stdout_disk_path=disk_path,
    )

    handle = runner.start(cmd)
    rc = runner.wait(handle)

    assert rc == 0
    assert disk_path.exists()
    assert "dry_run" in disk_path.read_text()
    assert stat.S_ISFIFO(fifo_path.stat().st_mode)