import argparse
import hashlib
import json
import pathlib
import platform
import tarfile
import urllib.request
import zipfile

from trickfish.stockfish_profile import ASSETS, RELEASE, verify_stockfish19


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    system = platform.system()
    if system not in ASSETS or platform.machine().lower() not in {"amd64", "x86_64"}:
        parser.error("pinned release supports Linux/Windows x86-64 only")
    asset = ASSETS[system]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    archive = args.output_dir / asset["archive"]
    url = "https://github.com/official-stockfish/Stockfish/releases/download/" + RELEASE + "/" + asset["archive"]
    with urllib.request.urlopen(url, timeout=60) as response, archive.open("xb") as stream:
        while block := response.read(1024 * 1024):
            stream.write(block)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != asset["archive_sha256"]:
        raise ValueError("Stockfish archive hash mismatch")
    if system == "Windows":
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                path = pathlib.PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("unsafe archive entry")
            bundle.extractall(args.output_dir)
    else:
        with tarfile.open(archive) as bundle:
            bundle.extractall(args.output_dir, filter="data")
    executable = args.output_dir / asset["executable"]
    if not executable.resolve().is_relative_to(args.output_dir.resolve()):
        raise ValueError("executable escapes output directory")
    receipt = verify_stockfish19(executable)
    (args.output_dir / "release.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(executable.resolve())


if __name__ == "__main__":
    main()
