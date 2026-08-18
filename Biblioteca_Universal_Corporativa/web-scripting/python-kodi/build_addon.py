from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a platform-specific Kodi module ZIP.")
    parser.add_argument("--platform", required=True, choices=("win_amd64", "manylinux2014_x86_64", "macosx_11_0_arm64"))
    parser.add_argument("--python-version", default="311")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="mbuc-kodi-") as temporary:
        staging = Path(temporary) / "script.module.mbuc.security"
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns("dist", "__pycache__", "*.pyc"))
        target = staging / "resources" / "lib"
        command = [sys.executable, "-m", "pip", "install", "--only-binary=:all:", "--platform", args.platform, "--python-version", args.python_version, "--implementation", "cp", "--abi", f"cp{args.python_version}", "--target", str(target), "cryptography>=42,<47"]
        subprocess.run(command, check=True)
        args.output.mkdir(parents=True, exist_ok=True)
        archive = shutil.make_archive(str(args.output / "script.module.mbuc.security-1.0.0"), "zip", staging.parent, staging.name)
        print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
