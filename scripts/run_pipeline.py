"""Run full data pipeline (ingest -> normalize -> compute) with a lock file."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def _pipeline_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_payload = {
        "pid": os.getpid(),
        "started_at_utc": _utc_now(),
    }

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Pipeline is already running (lock exists: {lock_path})") from exc

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(lock_payload, f)
        yield
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Acknowledge that this command will update data artifacts.",
    )
    args = parser.parse_args()

    if not args.yes:
        print("Refusing to run without --yes.")
        return 2

    root = Path(args.root).resolve()
    lock_path = root / "data" / "compute" / ".pipeline.lock"

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(root) + (os.pathsep + existing if existing else "")

    steps = [
        (
            "ingest",
            [
                sys.executable,
                "-m",
                "src.ingest.run_ingest",
                "--root",
                str(root),
                "--log-level",
                args.log_level,
            ],
        ),
        (
            "normalize",
            [
                sys.executable,
                "-m",
                "src.normalize.run_normalize",
                "--root",
                str(root),
                "--log-level",
                args.log_level,
            ],
        ),
        (
            "compute",
            [
                sys.executable,
                "-m",
                "src.compute.run_compute",
                "--root",
                str(root),
                "--log-level",
                args.log_level,
            ],
        ),
    ]

    try:
        with _pipeline_lock(lock_path):
            print(f"[pipeline] started at {_utc_now()} UTC")
            for step_name, cmd in steps:
                print(f"[pipeline] running step={step_name}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(root),
                    env=env,
                )
                if result.stdout:
                    print(result.stdout.rstrip())
                if result.stderr:
                    print(result.stderr.rstrip(), file=sys.stderr)

                if result.returncode != 0:
                    print(f"[pipeline] FAILED step={step_name} exit_code={result.returncode}")
                    return result.returncode

            print(f"[pipeline] completed at {_utc_now()} UTC")
            return 0
    except RuntimeError as exc:
        print(str(exc))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
