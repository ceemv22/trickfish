import argparse
import ast
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile


def source_snapshot(repo, output, versions, chess_source=None):
    source = output / "source/TrickfishWorkbook-source"
    names = ["LICENSE-WORKBOOK.txt", "WORKBOOK-LICENSE-SCOPE.md", "src/trickfish/workbook.py",
             "src/trickfish/workbook_gui.py", "src/trickfish/workbook_smoke.py",
             "src/trickfish/data/workbook-demo.pgn", "packaging/workbook_package_init.py",
             "packaging/workbook_entry.py", "packaging/build_workbook.py",
             "packaging/requirements-workbook-build.txt", "packaging/WINDOWS-READ-ME.txt",
             "packaging/SOURCE-READ-ME.txt", "tests/test_workbook.py", "examples/workbook-demo.pgn",
             "examples/workbook-edge-cases.pgn", "docs/pgn-workbook.md", ".github/workflows/workbook-windows.yml"]
    for name in names:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, target)
    shutil.copyfile(repo / "packaging/workbook_package_init.py", source / "src/trickfish/__init__.py")
    shutil.copyfile(repo / "packaging/SOURCE-READ-ME.txt", source / "READ-ME.txt")
    version = versions["chess"]
    manifest = repo / "third-party-source.json"
    if chess_source is not None and manifest.is_file():
        saved = json.loads(manifest.read_text(encoding="utf-8"))
        if saved["package"] != "chess" or saved["version"] != version:
            raise ValueError("Source manifest does not match installed chess")
        asset = {"url": saved["url"], "filename": saved["filename"], "digests": {"sha256": saved["sha256"]}}
    else:
        with urllib.request.urlopen(f"https://pypi.org/pypi/chess/{version}/json", timeout=30) as response:
            metadata = json.load(response)
        assets = [asset for asset in metadata["urls"] if asset["packagetype"] == "sdist"]
        if len(assets) != 1:
            raise ValueError("Expected exactly one chess source distribution")
        asset = assets[0]
    from urllib.parse import urlparse

    if urlparse(asset["url"]).scheme != "https" or urlparse(asset["url"]).hostname != "files.pythonhosted.org":
        raise ValueError("Unexpected chess source host")
    if chess_source is None:
        with urllib.request.urlopen(asset["url"], timeout=60) as response:
            raw = response.read()
    else:
        raw = chess_source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != asset["digests"]["sha256"]:
        raise ValueError("Chess source SHA-256 mismatch")
    target = source / "third-party-source" / pathlib.Path(asset["filename"]).name
    target.parent.mkdir()
    target.write_bytes(raw)
    distribution = importlib.metadata.distribution("chess")
    with tarfile.open(target) as archive:
        for file in distribution.files or []:
            if str(file).replace("\\", "/").startswith("chess/") and str(file).endswith(".py"):
                stream = archive.extractfile(f"chess-{version}/" + str(file).replace("\\", "/"))
                if stream is None or stream.read() != pathlib.Path(distribution.locate_file(file)).read_bytes():
                    raise ValueError("Installed chess code differs from the source distribution")
    source_info = {"package": "chess", "version": version, "url": asset["url"], "sha256": digest,
                   "filename": target.name, "installed_python_sources": "matched"}
    (source / "third-party-source.json").write_text(json.dumps(source_info, indent=2), encoding="utf-8")
    return source, source_info


def audit_modules(path):
    allowed = {"trickfish", "trickfish.workbook", "trickfish.workbook_gui", "trickfish.workbook_smoke"}
    toc = ast.literal_eval(path.read_text(encoding="utf-8"))
    found = set()

    def visit(value):
        if isinstance(value, (tuple, list)):
            if value and isinstance(value[0], str) and (value[0] == "trickfish" or value[0].startswith("trickfish.")):
                found.add(value[0])
            for child in value:
                visit(child)

    visit(toc)
    if not allowed <= found or found - allowed:
        raise ValueError("Unexpected frozen Workbook module set: " + str(sorted(found)))
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(description="Build Windows Workbook with matching GPL source snapshot")
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--chess-source", type=pathlib.Path)
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
    snapshot, source_info = source_snapshot(repo, output, versions, args.chess_source)
    font = pathlib.Path(importlib.metadata.distribution("reportlab").locate_file("reportlab/fonts/Vera.ttf"))
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
               "--noupx", "--name", "TrickfishWorkbook", "--paths", str(snapshot / "src"),
               "--distpath", str(output / "app"), "--workpath", str(output / "build"),
               "--specpath", str(output / "spec"), "--add-data", str(font) + ";reportlab/fonts",
               "--add-data", str(snapshot / "src/trickfish/data") + ";trickfish/data",
               str(snapshot / "packaging/workbook_entry.py")]
    subprocess.run(command, check=True, cwd=snapshot)
    modules = audit_modules(output / "build/TrickfishWorkbook/PYZ-00.toc")
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
    shutil.copyfile(repo / "LICENSE-WORKBOOK.txt", app / "LICENSE-WORKBOOK.txt")
    shutil.copyfile(repo / "WORKBOOK-LICENSE-SCOPE.md", app / "WORKBOOK-LICENSE-SCOPE.md")
    subprocess.run([str(app / "TrickfishWorkbook.exe"), "--smoke-test", str(output / "smoke")],
                   check=True, timeout=120, cwd=output)
    smoke = json.loads((output / "smoke/smoke.json").read_text())
    if smoke.get("frozen") is not True:
        raise ValueError("Smoke did not execute the frozen application")
    (snapshot / "BUILD-ENVIRONMENT.json").write_text(json.dumps({"python": platform.python_version(),
        "dependencies": versions, "workbook_modules": modules}, indent=2), encoding="utf-8")
    source_files = {str(p.relative_to(snapshot)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(snapshot.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    source_archive = output / "TrickfishWorkbook-source.zip"
    with zipfile.ZipFile(source_archive, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in source_files:
            archive.write(snapshot / name, "TrickfishWorkbook-source/" + name)
    shutil.copyfile(source_archive, app / "SOURCE-CODE.zip")
    hashes = {str(p.relative_to(app)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(app.rglob("*")) if p.is_file()}
    record = {"schema": "trickfish.windows-workbook-build.v1", "python": platform.python_version(),
              "platform": platform.platform(), "dependencies": versions, "smoke": smoke,
              "files": hashes, "workbook_modules": modules, "chess_source": source_info,
              "source_files": source_files,
              "release_status": "GPL-3.0-or-later Workbook scope; prepared build, not a public release"}
    (output / "build-receipt.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    archive = pathlib.Path(shutil.make_archive(str(output / "TrickfishWorkbook-windows-x64"), "zip", app.parent, app.name))
    (output / "archive.sha256").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                                                  for p in (archive, source_archive)), encoding="utf-8")
    print(archive)


if __name__ == "__main__":
    main()
