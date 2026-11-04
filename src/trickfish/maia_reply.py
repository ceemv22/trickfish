import hashlib
import importlib.metadata
import math
import os
import pathlib


def normalize_maia_replies(raw, legal):
    if not isinstance(raw, dict) or set(raw) != set(legal):
        raise ValueError("Maia legal reply coverage disagrees with the reference engine")
    if any(type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1
           for value in raw.values()):
        raise ValueError("Maia returned invalid probabilities")
    mass = math.fsum(raw.values())
    if mass <= 0 or abs(mass - 1) > len(raw) * 0.00005 + 1e-7:
        raise ValueError("Maia probability mass exceeds four-decimal rounding tolerance")
    return {move: value / mass for move, value in raw.items()}, mass


class MaiaReplyModel:
    def __init__(self, kind, cache_directory, player_rating, device="cpu"):
        if kind not in {"rapid", "blitz"}:
            raise ValueError("Maia model must be rapid or blitz")
        if type(player_rating) is not int or player_rating <= 0:
            raise ValueError("player rating must be a positive integer")
        try:
            version = importlib.metadata.version("maia2")
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError("install the optional practical dependencies to use Maia") from error
        if version != "0.11.0":
            raise RuntimeError("this adapter requires maia2==0.11.0")
        from maia2 import inference, model

        self.network = model.from_pretrained(type=kind, device=device, save_root=str(cache_directory))
        self.prepared = inference.prepare()
        self.infer = inference.inference_each
        checkpoint = pathlib.Path(cache_directory) / (kind + "_model.pt")
        self.metadata = {"source": "Maia-2", "package_version": version, "kind": kind,
                         "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                         "player_rating": player_rating, "device": device,
                         "dependency_versions": {name: importlib.metadata.version(name) for name in ("torch", "chess", "numpy")},
                         "thread_environment": {name: os.environ.get(name) for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS")},
                         "rating_buckets": "below 1100; 100-point bins 1100..1999; 2000 and above",
                         "calibration": "pretrained human policy; not validated for this application",
                         "rounding": "four-decimal outputs divided by recorded raw probability mass"}
        self.used = {}

    def __call__(self, position, rating):
        if type(rating) is not int or rating <= 0:
            raise ValueError("opponent rating must be a positive integer")
        fen = position.to_fen()
        key = (fen, rating)
        if key not in self.used:
            raw, _ = self.infer(self.network, self.prepared, fen, rating, self.metadata["player_rating"])
            probabilities, mass = normalize_maia_replies(raw, {move.to_uci() for move in position.legal_moves()})
            self.used[key] = {"fen": fen, "active_rating": rating,
                              "other_rating": self.metadata["player_rating"],
                              "raw_mass": mass, "raw_probabilities": raw,
                              "probabilities": probabilities}
        return dict(self.used[key]["probabilities"])

    def provenance(self):
        return {**self.metadata, "positions": list(self.used.values())}
