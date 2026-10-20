from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Command:
    argv: list[str]
    cwd: Path
    stdout_path: Optional[Path] = None
    stdout_disk_path: Optional[Path] = None
    stdout_fifo_path: Optional[Path] = None


@dataclass
class ProcessHandle:
    pid: int
    command: Command
    started_at: datetime
    popen: Optional[subprocess.Popen] = None


class SubprocessRunner:
    def __init__(self, *, dry_run: bool = False):
        self.dry_run = bool(dry_run)

    def _pump_stdout(
        self, pipe, primary_path: Path, mirror_path: Optional[Path]
    ) -> None:
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        primary_fh = primary_path.open("wb")
        mirror_fh = None
        try:
            if mirror_path is not None:
                mirror_path.parent.mkdir(parents=True, exist_ok=True)
                mirror_fh = mirror_path.open("wb")

            while True:
                chunk = pipe.read(65536)
                if not chunk:
                    break
                primary_fh.write(chunk)
                if mirror_fh is not None:
                    mirror_fh.write(chunk)

            primary_fh.flush()
            if mirror_fh is not None:
                mirror_fh.flush()
        finally:
            try:
                pipe.close()
            except Exception:
                pass
            primary_fh.close()
            if mirror_fh is not None:
                mirror_fh.close()

    def start(self, cmd: Command) -> ProcessHandle:
        cmd.cwd.mkdir(parents=True, exist_ok=True)

        if self.dry_run:

            if cmd.stdout_path is not None and not cmd.stdout_path.exists():
                cmd.stdout_path.parent.mkdir(parents=True, exist_ok=True)
                cmd.stdout_path.write_text(
                    "[dry_run] subprocess not executed\n", encoding="utf-8"
                )

            if (
                cmd.stdout_disk_path is not None
                and not cmd.stdout_disk_path.exists()
            ):
                cmd.stdout_disk_path.parent.mkdir(parents=True, exist_ok=True)
                cmd.stdout_disk_path.write_text(
                    "[dry_run] subprocess not executed\n", encoding="utf-8"
                )
            return ProcessHandle(
                pid=0, command=cmd, started_at=datetime.now(), popen=None
            )

        if cmd.stdout_path is None:
            p = subprocess.Popen(
                cmd.argv,
                cwd=str(cmd.cwd),
                stderr=subprocess.STDOUT,
                text=True,
            )
            return ProcessHandle(
                pid=p.pid, command=cmd, started_at=datetime.now(), popen=p
            )

        if cmd.stdout_disk_path is None or Path(cmd.stdout_disk_path) == Path(
            cmd.stdout_path
        ):
            cmd.stdout_path.parent.mkdir(parents=True, exist_ok=True)
            out_fh = cmd.stdout_path.open("w", encoding="utf-8")
            p = subprocess.Popen(
                cmd.argv,
                cwd=str(cmd.cwd),
                stdout=out_fh,
                stderr=subprocess.STDOUT,
                text=True,
            )
            p._py_mcmd_out_fh = out_fh  # type: ignore[attr-defined]
            return ProcessHandle(
                pid=p.pid, command=cmd, started_at=datetime.now(), popen=p
            )

        if cmd.stdout_fifo_path is not None:
            if self.dry_run:
                if (
                    cmd.stdout_disk_path is not None
                    and not cmd.stdout_disk_path.exists()
                ):
                    cmd.stdout_disk_path.parent.mkdir(
                        parents=True, exist_ok=True
                    )
                    cmd.stdout_disk_path.write_text(
                        "[dry_run] subprocess not executed\n", encoding="utf-8"
                    )
                return ProcessHandle(
                    pid=0, command=cmd, started_at=datetime.now(), popen=None
                )

            p = subprocess.Popen(
                cmd.argv,
                cwd=str(cmd.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                bufsize=0,
            )

            def _pump_fifo(
                pipe, fifo_path: Path, mirror_path: Optional[Path]
            ) -> None:
                fifo_fh = None
                mirror_fh = None
                try:
                    fifo_fd = os.open(str(fifo_path), os.O_RDWR | os.O_NONBLOCK)
                    fifo_fh = os.fdopen(fifo_fd, "wb", buffering=0)

                    if mirror_path is not None:
                        mirror_path.parent.mkdir(parents=True, exist_ok=True)
                        mirror_fh = mirror_path.open("wb")

                    while True:
                        chunk = pipe.read(65536)
                        if not chunk:
                            break
                        fifo_fh.write(chunk)
                        if mirror_fh is not None:
                            mirror_fh.write(chunk)
                finally:
                    try:
                        pipe.close()
                    except Exception:
                        pass
                    if fifo_fh is not None:
                        fifo_fh.close()
                    if mirror_fh is not None:
                        mirror_fh.close()

            pump_thread = threading.Thread(
                target=_pump_fifo,
                args=(
                    p.stdout,
                    Path(cmd.stdout_fifo_path),
                    cmd.stdout_disk_path,
                ),
                daemon=True,
            )
            pump_thread.start()
            p._py_mcmd_pump_thread = pump_thread  # type: ignore[attr-defined]
            return ProcessHandle(
                pid=p.pid, command=cmd, started_at=datetime.now(), popen=p
            )
        p = subprocess.Popen(
            cmd.argv,
            cwd=str(cmd.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            bufsize=0,
        )
        pump_thread = threading.Thread(
            target=self._pump_stdout,
            args=(p.stdout, Path(cmd.stdout_path), Path(cmd.stdout_disk_path)),
            daemon=True,
        )
        pump_thread.start()
        p._py_mcmd_pump_thread = pump_thread  # type: ignore[attr-defined]
        return ProcessHandle(
            pid=p.pid, command=cmd, started_at=datetime.now(), popen=p
        )

    def wait(self, handle: ProcessHandle) -> int:
        if handle.popen is None:
            return 0

        rc = int(handle.popen.wait())

        pump_thread = getattr(handle.popen, "_py_mcmd_pump_thread", None)
        if pump_thread is not None:
            pump_thread.join()

        out_fh = getattr(handle.popen, "_py_mcmd_out_fh", None)
        if out_fh is not None:
            try:
                out_fh.close()
            except Exception:
                pass
        return rc

    def run_and_wait(self, cmd: Command) -> int:
        return self.wait(self.start(cmd))


class DryRunSubprocessRunner(SubprocessRunner):
    def __init__(self):
        super().__init__(dry_run=True)
