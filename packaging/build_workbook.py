import argparse
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Build an internal Windows workbook folder and ZIP")
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        parser.error("Build with 64-bit Python on Windows x64")
    output = args.output.resolve()
    if output.exists():
        parser.error("Output directory must be new")
    repo = pathlib.Path(__file__).resolve().parents[1]
    versions = {name: importlib.metadata.version(name) for name in
                ("pyinstaller", "pyinstaller-hooks-contrib", "chess", "reportlab", "pillow", "charset-normalizer")}
    output.mkdir(parents=True)
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
               "--noupx", "--name", "TrickfishWorkbook", "--paths", str(repo / "src"),
               "--distpath", str(output / "app"), "--workpath", str(output / "build"),
               "--specpath", str(output / "spec"), "--collect-data", "reportlab",
               "--add-data", str(repo / "src/trickfish/data") + ";trickfish/data",
               str(repo / "packaging/workbook_entry.py")]
    subprocess.run(command, check=True, cwd=repo)
    app = output / "app/TrickfishWorkbook"
    notices = app / "THIRD-PARTY-NOTICES"
    notices.mkdir()
    for name in ("chess", "reportlab", "pillow", "charset-normalizer"):
        distribution = importlib.metadata.distribution(name)
        for file in distribution.files or []:
            if any(word in str(file).lower() for word in ("license", "copying")):
                source = pathlib.Path(distribution.locate_file(file))
                if source.is_file():
                    target = notices / name / str(file)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    python_root = pathlib.Path(sys.base_prefix)
    python_license = python_root / "LICENSE.txt"
    if not python_license.is_file():
        raise ValueError("Python LICENSE.txt missing; cannot finalize package")
    shutil.copyfile(python_license, notices / "Python-LICENSE.txt")
    for folder in (python_root / "tcl").glob("*"):
        for name in ("license.terms", "license.txt"):
            source = folder / name
            if source.is_file():
                shutil.copyfile(source, notices / (folder.name + "-" + name))
    shutil.copyfile(repo / "packaging/WINDOWS-READ-ME.txt", app / "READ-ME.txt")
    subprocess.run([str(app / "TrickfishWorkbook.exe"), "--smoke-test", str(output / "smoke")],
                   check=True, timeout=120, cwd=output)
    smoke = json.loads((output / "smoke/smoke.json").read_text())
    if smoke.get("frozen") is not True:
        raise ValueError("Smoke did not execute the frozen application")
    hashes = {str(p.relative_to(app)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(app.rglob("*")) if p.is_file()}
    record = {"schema": "trickfish.windows-workbook-build.v1", "python": platform.python_version(),
              "platform": platform.platform(), "dependencies": versions, "smoke": smoke,
              "files": hashes, "release_status": "internal prototype; no project license selected; not a public release"}
    (output / "build-receipt.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    archive = pathlib.Path(shutil.make_archive(str(output / "TrickfishWorkbook-windows-x64"), "zip", app.parent, app.name))
    (output / "archive.sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="utf-8")
    print(archive)


if __name__ == "__main__":
    main()
