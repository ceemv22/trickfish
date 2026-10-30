import json
import os
import pathlib
import uuid

from export_matches import render_game, validate_profile_provenance, validate_schedule


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def save_checkpoint(path, configuration, games):
    target = pathlib.Path(path).resolve()
    temporary = target.with_name("." + target.name + "." + uuid.uuid4().hex + ".tmp")
    encoded = json.dumps({"checkpoint_version": 1, "configuration": configuration, "games": games},
        indent=2, allow_nan=False) + "\n"
    created = False
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            created = True
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if created:
            temporary.unlink(missing_ok=True)


def load_checkpoint(path, configuration):
    checkpoint = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if (not isinstance(checkpoint, dict) or set(checkpoint) != {"checkpoint_version", "configuration", "games"} or
        type(checkpoint["checkpoint_version"]) is not int or checkpoint["checkpoint_version"] != 1):
        raise ValueError("unsupported match checkpoint")
    if canonical(checkpoint["configuration"]) != canonical(configuration):
        raise ValueError("checkpoint configuration differs from current inputs")
    games = checkpoint["games"]
    if not isinstance(games, list):
        raise ValueError("checkpoint games must be a list")
    report = dict(configuration, games=games)
    validate_schedule(report, allow_partial=True)
    validate_profile_provenance(report)
    openings = {opening["id"]: opening for opening in configuration["opening_cases"]}
    for game in games:
        opening = openings[game["opening"]]
        prefix = opening.get("moves", [])
        if (game["root_fen"] != opening["fen"] or game["opening_plies"] != len(prefix) or
            game["moves"][:len(prefix)] != prefix):
            raise ValueError("checkpoint game differs from source opening")
        render_game(game, configuration["engines"], configuration["policy"])
    return games
