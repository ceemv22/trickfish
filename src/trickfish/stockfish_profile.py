import hashlib
import pathlib


RELEASE = "sf_19"
ASSETS = {
    "Windows": {"archive": "stockfish-windows-x86-64-universal.zip",
                "archive_sha256": "3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7",
                "executable": "stockfish/stockfish-windows-x86-64-universal.exe",
                "executable_sha256": "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"},
    "Linux": {"archive": "stockfish-linux-x86-64-universal.tar.gz",
              "archive_sha256": "9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f",
              "executable": "stockfish/stockfish-linux-x86-64-universal",
              "executable_sha256": "0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19"},
}
OPTIONS = {"NumaPolicy": "none", "Threads": 1, "Hash": 16, "MultiPV": 1, "Ponder": False,
           "Skill Level": 20, "UCI_LimitStrength": False, "UCI_Chess960": False, "UCI_ShowWDL": False,
           "Move Overhead": 10, "nodestime": 0, "SyzygyProbeLimit": 0,
           "EvalFile": "nn-1a298aa575a0.nnue"}


def verify_stockfish19(executable):
    digest = hashlib.sha256(pathlib.Path(executable).read_bytes()).hexdigest()
    for system, asset in ASSETS.items():
        if digest == asset["executable_sha256"]:
            return {"id": "stockfish19-controlled-v1", "release": RELEASE, "system_build": system,
                    "archive": asset["archive"], "archive_sha256": asset["archive_sha256"],
                    "executable_sha256": digest}
    raise ValueError("controlled profile requires a pinned official Stockfish 19 executable")
