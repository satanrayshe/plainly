"""Build the Lambda deployment zip from backend/, byte-for-byte reproducibly.

    python scripts/package_lambda.py            # prints build/lambda-<sha256[:12]>.zip

Contents: backend/*.py (minus tests and conftest) and backend/registry.json, flat at
the zip root so the handler is app.handler. dev_mock.py ships only if another module
imports it. Entries are sorted and carry a fixed timestamp and mode, so the same
sources always give the same hash, and the S3 key doubles as the version.

The build fails if a module imports something the Lambda runtime does not have
(anything outside the standard library, boto3/botocore, and backend's own modules).
"""
from __future__ import annotations

import ast
import hashlib
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
BUILD = ROOT / "build"

DATA_FILES = ["registry.json"]
DEV_ONLY = "dev_mock"
RUNTIME_PROVIDED = {"boto3", "botocore"}
# PEP 594 modules: present in a local 3.12 install, gone from the python3.13 runtime.
REMOVED_IN_313 = {"aifc", "audioop", "cgi", "cgitb", "chunk", "crypt", "imghdr", "lib2to3", "mailcap",
                  "msilib", "nis", "nntplib", "ossaudiodev", "pipes", "sndhdr", "spwd", "sunau",
                  "telnetlib", "uu", "xdrlib"}
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def top_level_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        sys.exit(f"Refusing to package: {path.name} line {exc.lineno}: {exc.msg}")
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def is_test_module(path: Path) -> bool:
    return path.name.startswith("test_") or path.name.endswith("_test.py") or path.name == "conftest.py"


def select_sources() -> list[Path]:
    modules = [p for p in BACKEND.glob("*.py") if not is_test_module(p)]
    if not any(p.name == "app.py" for p in modules):
        sys.exit("backend/app.py not found; the handler is app.handler")

    dev_mock = BACKEND / f"{DEV_ONLY}.py"
    if dev_mock in modules:
        used = any(DEV_ONLY in top_level_imports(p) for p in modules if p != dev_mock)
        if not used:
            modules.remove(dev_mock)

    files = sorted(modules)
    for name in DATA_FILES:
        path = BACKEND / name
        if not path.is_file():
            sys.exit(f"backend/{name} is missing")
        files.append(path)
    return files


def check_sources(files: list[Path]) -> None:
    local = {p.stem for p in BACKEND.glob("*.py")}
    allowed = (set(sys.stdlib_module_names) - REMOVED_IN_313) | RUNTIME_PROVIDED | local
    problems = []
    for path in files:
        if path.suffix == ".py":
            for name in sorted(top_level_imports(path) - allowed):
                problems.append(f"{path.name}: imports '{name}', which is not in the Lambda runtime")
    if problems:
        sys.exit("Refusing to package:\n  " + "\n  ".join(problems))


def build_zip(files: list[Path]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            info = zipfile.ZipInfo(path.name, date_time=FIXED_DATE)
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # unix, so the mode bits above are honoured on any build host
            data = path.read_bytes()
            if path.suffix in (".py", ".json"):
                data = data.replace(b"\r\n", b"\n")  # same hash from Windows and Linux checkouts
            zf.writestr(info, data)
    return buffer.getvalue()


def main() -> None:
    files = select_sources()
    check_sources(files)
    payload = build_zip(files)
    BUILD.mkdir(exist_ok=True)
    digest = hashlib.sha256(payload).hexdigest()[:12]
    target = BUILD / f"lambda-{digest}.zip"
    target.write_bytes(payload)

    listing = ", ".join(p.name for p in files)
    print(f"{len(files)} files, {len(payload) / 1024:.1f} KiB: {listing}", file=sys.stderr)
    print(target.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
