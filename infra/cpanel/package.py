"""Build the two zips to upload to cPanel.

    python infra/cpanel/package.py

Output (gitignored) in dist/cpanel/:
    frontend.zip  contents of frontend/dist + .htaccess  -> unzip into the domain's document root
    backend.zip   backend/ without venv, tests, data, secrets -> unzip into ~/astronode/backend

The frontend is built with VITE_BACKEND_URL empty so it calls same-origin /api.
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist" / "cpanel"

BACKEND_SKIP_DIRS = {
    "venv",
    ".venv",
    "tests",
    "data",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
BACKEND_SKIP_FILES = {".env", ".env.local", "requirements-dev.txt"}


def build_frontend() -> None:
    env = {**os.environ, "VITE_BACKEND_URL": ""}
    subprocess.run(
        "npm run build", cwd=ROOT / "frontend", env=env, shell=True, check=True
    )


def zip_frontend() -> Path:
    dist = ROOT / "frontend" / "dist"
    target = OUT / "frontend.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dist.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(dist).as_posix())
        z.write(ROOT / "infra" / "cpanel" / "htaccess", ".htaccess")
    return target


def zip_backend() -> Path:
    src = ROOT / "backend"
    target = OUT / "backend.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if not p.is_file() or set(rel.parts[:-1]) & BACKEND_SKIP_DIRS:
                continue
            if rel.name in BACKEND_SKIP_FILES or rel.suffix == ".pyc":
                continue
            z.write(p, rel.as_posix())
    return target


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    build_frontend()
    for z in (zip_frontend(), zip_backend()):
        print(f"{z}  {z.stat().st_size / 1e6:.1f} MB")
