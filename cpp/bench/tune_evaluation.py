import argparse
import copy
import itertools
import math
import pathlib
import sys

from analyze_matches import half_points
from assess_match import read_json
from match_campaign import load_campaign
import run_experiment as fixed
import sequential_experiment as sequential
from sequential_test import validate_parameters
from search_benchmark import digest
from uci_matches import opening_position, repetition_identity


WEIGHTS = ("Eval Pawn Weight", "Eval Activity Weight", "Eval King Safety Weight")


def weights(profile):
    if not isinstance(profile, dict) or set(profile) != set(WEIGHTS): raise ValueError("evaluation profile needs exactly three weight names")
    if any(type(value) is not int or not 0 <= value <= 200 for value in profile.values()):
        raise ValueError("evaluation weights must be integer percentages in 0..200")
    return {name: profile[name] for name in WEIGHTS}


def load_spec(path):
    source = pathlib.Path(path).resolve(strict=True)
    data = read_json(source)
    if (not isinstance(data, dict) or set(data) != {"version", "baseline", "grid", "training_campaign", "confirmation_campaign", "sequential"} or
        type(data["version"]) is not int or data["version"] != 1): raise ValueError("invalid version-1 tuning specification")
    baseline = weights(data["baseline"])
    grid = data["grid"]
    if not isinstance(grid, dict) or set(grid) != set(WEIGHTS): raise ValueError("grid needs exactly three axes")
    for axis in grid.values():
        if (not isinstance(axis, list) or not axis or any(type(value) is not int or not 0 <= value <= 200 for value in axis) or
            len(axis) != len(set(axis))): raise ValueError("grid axes must contain unique integer percentages in 0..200")
    if not 1 <= math.prod(len(grid[name]) for name in WEIGHTS) <= 64: raise ValueError("grid must contain 1..64 profiles")
    profiles = [dict(zip(WEIGHTS, values)) for values in itertools.product(*(grid[name] for name in WEIGHTS))]
    campaigns = {}
    for key in ("training_campaign", "confirmation_campaign"):
        if not isinstance(data[key], str) or not data[key]: raise ValueError("missing tuning campaign path")
        campaign = load_campaign(source.parent / data[key])
        if campaign["profile_path"] is not None or campaign["metadata"]["specification"]["rounds"] != 1:
            raise ValueError("tuning campaigns must have one round and no external profile")
        campaigns[key] = campaign
    if not isinstance(data["sequential"], dict) or set(data["sequential"]) != {"p0", "p1", "alpha", "beta"}:
        raise ValueError("invalid confirmation parameters")
    parameters = dict(data["sequential"], max_pairs=len(campaigns["confirmation_campaign"]["openings"]))
    validate_parameters(parameters)
    identities = [{repetition_identity(opening_position(opening)[0]) for opening in campaign["openings"]} for campaign in campaigns.values()]
    if identities[0] & identities[1]: raise ValueError("training and confirmation opening roots overlap")
    if any(len(campaign["openings"]) > 4096 for campaign in campaigns.values()): raise ValueError("tuning campaign exceeds pair limit")
    return data, baseline, profiles, campaigns


def methods():
    return {**sequential.methods(), "cpp/bench/tune_evaluation.py": digest(pathlib.Path(__file__))}


def write_once(path, value):
    if path.exists():
        if path.read_bytes() != value: raise ValueError("immutable tuning input differs: " + path.name)
    else:
        with path.open("xb") as stream: stream.write(value)


def profiled_campaign(directory, campaign, candidate, baseline):
    directory.mkdir(exist_ok=True)
    profile = {"version": 1, "engines": {"a": candidate, "b": baseline}}
    write_once(directory / "profiles.json", fixed.encoded(profile))
    write_once(directory / "openings.json", campaign["opening_path"].read_bytes())
    data = copy.deepcopy(campaign["metadata"]["specification"])
    data.update(openings="openings.json", profiles="profiles.json", profiles_sha256=digest(directory / "profiles.json"))
    write_once(directory / "campaign.json", fixed.encoded(data))
    return directory / "campaign.json"


def initialize(directory, binary, spec_path):
    root = pathlib.Path(directory).resolve()
    if root.exists(): raise ValueError("tuning directory exists; use resume or a new directory")
    binary = pathlib.Path(binary).resolve(strict=True)
    binary_hash = digest(binary)
    data, baseline, profiles, campaigns = load_spec(spec_path)
    root.mkdir(parents=True)
    inputs = {}
    for key, name in (("training_campaign", "training"), ("confirmation_campaign", "confirmation")):
        target = root / name
        target.mkdir()
        campaign = campaigns[key]
        (target / "openings.json").write_bytes(campaign["opening_path"].read_bytes())
        specification = copy.deepcopy(campaign["metadata"]["specification"])
        specification["openings"] = "openings.json"
        (target / "campaign.json").write_bytes(fixed.encoded(specification))
        for file in target.iterdir(): inputs[str(file.relative_to(root)).replace("\\", "/")] = digest(file)
    snapshot = copy.deepcopy(data)
    snapshot.update(training_campaign="training/campaign.json", confirmation_campaign="confirmation/campaign.json")
    (root / "spec.json").write_bytes(fixed.encoded(snapshot))
    inputs["spec.json"] = digest(root / "spec.json")
    training = load_campaign(root / "training/campaign.json")
    trials = []
    for index, profile in enumerate(profiles):
        name = "trial-" + str(index).zfill(3)
        path = profiled_campaign(root / (name + "-inputs"), training, profile, baseline)
        for file in path.parent.iterdir(): inputs[str(file.relative_to(root)).replace("\\", "/")] = digest(file)
        trials.append({"id": name, "profile": profile, "campaign": str(path.relative_to(root)).replace("\\", "/")})
    if digest(binary) != binary_hash: raise ValueError("tuning binary changed during setup")
    plan = {"tuning_version": 1, "directory": str(root), "binary": {"path": str(binary), "sha256": binary_hash},
        "methods": methods(), "inputs": inputs, "trials": trials,
        "selection": "eligible profile has all training games completed; maximum half-points; nearest baseline by L1; grid order"}
    (root / "tuning-plan.json").write_bytes(fixed.encoded(plan))
    load(root, require_engine=True)
    return root


def load(directory, require_engine=False):
    root = pathlib.Path(directory).resolve(strict=True)
    source_hash = digest(root / "tuning-plan.json")
    plan = read_json(root / "tuning-plan.json")
    if (not isinstance(plan, dict) or set(plan) != {"tuning_version", "directory", "binary", "methods", "inputs", "trials", "selection"} or
        type(plan["tuning_version"]) is not int or plan["tuning_version"] != 1 or plan["directory"] != str(root) or plan["methods"] != methods()):
        raise ValueError("invalid, relocated or method-changed tuning plan")
    if not isinstance(plan["inputs"], dict): raise ValueError("invalid tuning input inventory")
    for name, expected in plan["inputs"].items():
        path = pathlib.PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name: raise ValueError("tuning input escaped its directory")
        if digest(root / name) != expected: raise ValueError("tuning snapshot changed: " + name)
    _, baseline, profiles, _ = load_spec(root / "spec.json")
    expected_trials = [{"id": "trial-" + str(index).zfill(3), "profile": profile,
        "campaign": "trial-" + str(index).zfill(3) + "-inputs/campaign.json"} for index, profile in enumerate(profiles)]
    if plan["trials"] != expected_trials: raise ValueError("tuning grid differs from specification")
    for trial in plan["trials"]:
        campaign = load_campaign(root / trial["campaign"])
        if campaign["profiles"] != {"a": trial["profile"], "b": baseline}: raise ValueError("tuning trial profile changed")
    if require_engine and digest(pathlib.Path(plan["binary"]["path"])) != plan["binary"]["sha256"]:
        raise ValueError("tuning binary changed")
    if digest(root / "tuning-plan.json") != source_hash: raise ValueError("tuning plan changed during loading")
    return root, plan, source_hash


def selection(root, plan):
    _, baseline, _, _ = load_spec(root / "spec.json")
    rankings = []
    for index, trial in enumerate(plan["trials"]):
        receipt = fixed.verify(root / trial["id"])
        manifest = read_json(root / trial["id"] / "experiment.json")
        if (manifest["source_campaign"]["sha256"] != digest(root / trial["campaign"]) or
            any(engine["sha256"] != plan["binary"]["sha256"] for engine in manifest["engines"].values())):
            raise ValueError("training evidence differs from tuning plan")
        report = read_json(root / trial["id"] / "matches.json")
        points = [half_points(game, "a") for game in report["games"]]
        complete = bool(points) and None not in points
        rankings.append({"id": trial["id"], "profile": trial["profile"], "complete": complete,
            "half_points": sum(points) if complete else None,
            "distance": sum(abs(trial["profile"][name] - baseline[name]) for name in WEIGHTS),
            "grid_index": index, "receipt_sha256": digest(root / trial["id"] / "receipt.json")})
    eligible = [entry for entry in rankings if entry["complete"]]
    best = min(eligible, key=lambda value: (-value["half_points"], value["distance"], value["grid_index"])) if eligible else None
    return {"selection_version": 1, "status": "selected_exploratory" if best else "blocked_training_unfinished",
        "winner": best, "trials": rankings, "inference": "exploratory finite-grid training selection; no statistical acceptance or automatic default change"}


def verify(directory):
    root, plan, plan_hash = load(directory)
    receipt = read_json(root / "receipt.json")
    selected = selection(root, plan)
    if (root / "selection.json").read_bytes() != fixed.encoded(selected): raise ValueError("fabricated tuning selection")
    expected = {"selection.json": digest(root / "selection.json")}
    decision = "blocked_training_unfinished"
    if selected["winner"]:
        expected.update(confirmation_receipt=digest(root / "confirmation-run/receipt.json"))
        confirmation = sequential.verify(root / "confirmation-run")
        confirmation_plan = read_json(root / "confirmation-run/plan.json")
        _, baseline, _, campaigns = load_spec(root / "spec.json")
        if confirmation_plan["configuration"]["profiles"] != {"a": selected["winner"]["profile"], "b": baseline}:
            raise ValueError("confirmation profile differs from frozen selected profile")
        actual_campaign = load_campaign(root / "confirmation-run/campaign.json")
        if actual_campaign["openings"] != campaigns["confirmation_campaign"]["openings"]:
            raise ValueError("confirmation evidence used different opening roots")
        controls = copy.deepcopy(campaigns["confirmation_campaign"]["metadata"]["specification"])
        controls.update(openings="openings.json", profiles="profiles.json",
            profiles_sha256=digest(root / "confirmation-run/profiles.json"))
        if actual_campaign["metadata"]["specification"] != controls:
            raise ValueError("confirmation budget or campaign controls changed")
        for engine in confirmation_plan["configuration"]["engines"].values():
            if engine["sha256"] != plan["binary"]["sha256"]: raise ValueError("confirmation binary differs from tuning binary")
        parameters = dict(read_json(root / "spec.json")["sequential"], max_pairs=len(actual_campaign["openings"]))
        if confirmation_plan["parameters"] != parameters: raise ValueError("confirmation statistical controls changed")
        expected["selected-profile.json"] = digest(root / "selected-profile.json")
        if read_json(root / "selected-profile.json") != selected["winner"]["profile"]: raise ValueError("selected profile artifact changed")
        decision = confirmation["decision"]
    wanted = {"tuning_receipt_version": 1, "plan_sha256": plan_hash, "artifacts": expected, "confirmation_decision": decision}
    if receipt != wanted: raise ValueError("tuning receipt differs from replayed evidence")
    if load(root)[2] != plan_hash: raise ValueError("tuning plan changed during verification")
    for trial in selected["trials"]:
        target = root / trial["id"]
        if digest(target / "receipt.json") != trial["receipt_sha256"]: raise ValueError("training receipt changed during verification")
        evidence = read_json(target / "receipt.json")
        if any(digest(target / name) != value for name, value in evidence["artifacts"].items()):
            raise ValueError("training evidence changed during verification")
    for name, value in expected.items():
        path = root / "confirmation-run/receipt.json" if name == "confirmation_receipt" else root / name
        if digest(path) != value: raise ValueError("tuning artifact changed during verification")
    return receipt


def execute(directory, runner=None, player=None):
    root, plan, plan_hash = load(directory)
    if (root / "receipt.json").exists(): return verify(root)
    load(root, require_engine=True)
    binary = pathlib.Path(plan["binary"]["path"])
    for trial in plan["trials"]:
        target = root / trial["id"]
        if not target.exists(): fixed.initialize(target, binary, binary, root / trial["campaign"])
        fixed.execute(target, runner)
    selected = selection(root, plan)
    write_once(root / "selection.json", fixed.encoded(selected))
    artifacts = {"selection.json": digest(root / "selection.json")}
    decision = "blocked_training_unfinished"
    if selected["winner"]:
        spec, baseline, _, campaigns = load_spec(root / "spec.json")
        write_once(root / "selected-profile.json", fixed.encoded(selected["winner"]["profile"]))
        campaign_path = profiled_campaign(root / "confirmation-inputs", campaigns["confirmation_campaign"], selected["winner"]["profile"], baseline)
        target = root / "confirmation-run"
        if not target.exists():
            parameters = dict(spec["sequential"], max_pairs=len(campaigns["confirmation_campaign"]["openings"]))
            sequential.initialize(target, binary, binary, campaign_path, parameters)
        result = sequential.execute(target, player)
        decision = result["decision"]
        artifacts.update(confirmation_receipt=digest(target / "receipt.json"))
        artifacts["selected-profile.json"] = digest(root / "selected-profile.json")
    load(root, require_engine=True)
    receipt = {"tuning_receipt_version": 1, "plan_sha256": plan_hash, "artifacts": artifacts, "confirmation_decision": decision}
    fixed.atomic_write(root / "receipt.json", fixed.encoded(receipt))
    try: return verify(root)
    except Exception:
        (root / "receipt.json").unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Finite evaluation grid self-play with disjoint-opening sequential confirmation")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("run")
    start.add_argument("binary", type=pathlib.Path)
    start.add_argument("--spec", type=pathlib.Path, required=True)
    start.add_argument("--directory", type=pathlib.Path, required=True)
    for name in ("resume", "verify"):
        command = commands.add_parser(name)
        command.add_argument("directory", type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "run": result = execute(initialize(args.directory, args.binary, args.spec))
    else: result = execute(args.directory) if args.command == "resume" else verify(args.directory)
    sys.stdout.buffer.write(fixed.encoded(result))


if __name__ == "__main__":
    main()
