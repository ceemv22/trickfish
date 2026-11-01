import argparse
import copy
import pathlib
import platform
import sys

from analyze_matches import half_points
from assess_match import read_json
from export_matches import export_report
from match_campaign import load_campaign
from match_checkpoint import load_checkpoint, save_checkpoint
from run_experiment import atomic_write, encoded, method_hashes
from search_benchmark import digest
from sequential_test import assess_signs, validate_parameters
from uci_matches import DRAW_POLICY, build_schedule, play_game, score_games


FILES = ("checkpoint.json", "assessment.json", "games.pgn")


def methods():
    result = method_hashes()
    for name in ("sequential_test.py", "sequential_experiment.py"):
        result["cpp/bench/" + name] = digest(pathlib.Path(__file__).with_name(name))
    return result


def configuration(campaign, binaries):
    data = campaign["metadata"]["specification"]
    go = "go " + data["search_budget"]["kind"] + " " + str(data["search_budget"]["value"])
    return {"engines": {label: {"path": str(path), "sha256": digest(path), "arguments": []} for label, path in binaries.items()},
        "profiles": campaign["profiles"], "opening_cases": campaign["openings"],
        "openings": {"path": str(campaign["opening_path"]), "sha256": digest(campaign["opening_path"])},
        "profile_source": {"path": str(campaign["profile_path"]), "sha256": digest(campaign["profile_path"])} if campaign["profile_path"] else None,
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "policy": {"go": go, "search_budget": data["search_budget"], "rounds": 1, "searched_ply_limit": data["max_plies"],
            "watchdog_seconds": data["timeout"], "schedule_seed": data["seed"],
            "pair_schedule": build_schedule(campaign["openings"], 1, data["seed"]), "draws": DRAW_POLICY,
            "errors": "abort run without assigning a game result", "ply_limit_result": "unfinished"}}


def initialize(directory, candidate, baseline, campaign_path, parameters):
    validate_parameters(parameters)
    root = pathlib.Path(directory).resolve()
    if root.exists(): raise ValueError("sequential directory already exists; use resume or a new path")
    source = load_campaign(campaign_path)
    data = source["metadata"]["specification"]
    if data["rounds"] != 1 or len(source["openings"]) != parameters["max_pairs"]:
        raise ValueError("sequential plan requires one round and exactly max_pairs unique openings")
    binaries = {label: pathlib.Path(path).resolve(strict=True) for label, path in (("a", candidate), ("b", baseline))}
    hashes = {label: digest(path) for label, path in binaries.items()}
    contents = {"source-campaign.json": pathlib.Path(source["metadata"]["path"]).read_bytes(),
        "openings.json": source["opening_path"].read_bytes()}
    specification = copy.deepcopy(data)
    specification["openings"] = "openings.json"
    if source["profile_path"] is not None:
        contents["profiles.json"] = source["profile_path"].read_bytes()
        specification["profiles"] = "profiles.json"
    contents["campaign.json"] = encoded(specification)
    if load_campaign(campaign_path)["metadata"] != source["metadata"]: raise ValueError("campaign changed before snapshot")
    root.mkdir(parents=True)
    for name, content in contents.items(): (root / name).write_bytes(content)
    campaign = load_campaign(root / "campaign.json")
    config = configuration(campaign, binaries)
    if any(config["engines"][label]["sha256"] != value for label, value in hashes.items()):
        raise ValueError("engine changed during sequential setup")
    plan = {"sequential_version": 1, "directory": str(root), "parameters": parameters,
        "inputs": {name: digest(root / name) for name in contents}, "configuration": config, "methods": methods()}
    with (root / "plan.json").open("xb") as stream: stream.write(encoded(plan))
    load(root, require_engines=True)
    return root


def load(directory, require_engines=False):
    root = pathlib.Path(directory).resolve(strict=True)
    plan_hash = digest(root / "plan.json")
    plan = read_json(root / "plan.json")
    if (not isinstance(plan, dict) or set(plan) != {"sequential_version", "directory", "parameters", "inputs", "configuration", "methods"} or
            type(plan["sequential_version"]) is not int or plan["sequential_version"] != 1 or plan["directory"] != str(root)):
        raise ValueError("invalid or relocated sequential plan")
    validate_parameters(plan["parameters"])
    if plan["methods"] != methods(): raise ValueError("sequential method sources changed")
    required = {"source-campaign.json", "campaign.json", "openings.json"}
    if not isinstance(plan["inputs"], dict) or not required <= plan["inputs"].keys() <= required | {"profiles.json"}:
        raise ValueError("invalid sequential snapshot inventory")
    for name, expected in plan["inputs"].items():
        if digest(root / name) != expected: raise ValueError("sequential snapshot changed: " + name)
    campaign = load_campaign(root / "campaign.json")
    original = read_json(root / "source-campaign.json")
    original["openings"] = "openings.json"
    if original["profiles"] is not None: original["profiles"] = "profiles.json"
    if original != campaign["metadata"]["specification"]: raise ValueError("sequential controls changed")
    config = plan["configuration"]
    data = campaign["metadata"]["specification"]
    if data["rounds"] != 1 or len(campaign["openings"]) != plan["parameters"]["max_pairs"]:
        raise ValueError("sequential horizon differs from snapshot")
    expected = copy.deepcopy(config)
    expected.update(profiles=campaign["profiles"], opening_cases=campaign["openings"],
        openings={"path": str(campaign["opening_path"]), "sha256": digest(campaign["opening_path"])},
        profile_source={"path": str(campaign["profile_path"]), "sha256": digest(campaign["profile_path"])} if campaign["profile_path"] else None)
    policy = expected["policy"]
    wanted = {"go": "go " + data["search_budget"]["kind"] + " " + str(data["search_budget"]["value"]),
        "search_budget": data["search_budget"], "rounds": 1, "searched_ply_limit": data["max_plies"],
        "watchdog_seconds": data["timeout"], "schedule_seed": data["seed"], "pair_schedule": build_schedule(campaign["openings"], 1, data["seed"]),
        "draws": DRAW_POLICY, "errors": "abort run without assigning a game result", "ply_limit_result": "unfinished"}
    if expected != config or policy != wanted: raise ValueError("sequential configuration differs from snapshot")
    if not isinstance(config["engines"], dict) or set(config["engines"]) != {"a", "b"}:
        raise ValueError("invalid sequential engine inventory")
    for engine in config["engines"].values():
        if set(engine) != {"path", "sha256", "arguments"} or engine["arguments"] != []:
            raise ValueError("invalid sequential engine specification")
        if require_engines and digest(pathlib.Path(engine["path"])) != engine["sha256"]:
            raise ValueError("sequential binary changed")
    if digest(root / "plan.json") != plan_hash: raise ValueError("sequential plan changed during loading")
    return root, plan, plan_hash


def assessment(plan, games):
    signs = []
    for index in range(0, len(games), 2):
        pair = [half_points(game, "a") for game in games[index:index + 2]]
        if len(pair) != 2: raise ValueError("sequential state contains a partial color pair")
        signs.append(None if None in pair else (sum(pair) > 2) - (sum(pair) < 2))
    def profile(label):
        defaults = {"eval pawn weight": 100, "eval activity weight": 100, "eval king safety weight": 100}
        defaults.update({key.casefold(): value for key, value in plan["configuration"]["profiles"][label].items()})
        return defaults
    identical = (plan["configuration"]["engines"]["a"]["sha256"] == plan["configuration"]["engines"]["b"]["sha256"] and
        profile("a") == profile("b"))
    return assess_signs(signs, plan["parameters"], identical)


def derive(root, plan):
    games = load_checkpoint(root / "checkpoint.json", plan["configuration"])
    result = assessment(plan, games)
    report = {key: copy.deepcopy(value) for key, value in plan["configuration"].items() if key != "opening_cases"}
    report["policy"]["pair_schedule"] = report["policy"]["pair_schedule"][:len(games) // 2]
    report.update(schema_version=1, games=games, scores=score_games(games))
    pgn = export_report(report) if games else ""
    return {"assessment.json": encoded(result), "games.pgn": pgn.encode("utf-8")}, result


def verify(directory):
    root, plan, plan_hash = load(directory)
    receipt = read_json(root / "receipt.json")
    if (not isinstance(receipt, dict) or set(receipt) != {"receipt_version", "plan_sha256", "artifacts", "decision"} or
        type(receipt["receipt_version"]) is not int or receipt["receipt_version"] != 1 or
        receipt["plan_sha256"] != plan_hash or set(receipt["artifacts"]) != set(FILES)):
        raise ValueError("invalid sequential receipt")
    for name, value in receipt["artifacts"].items():
        if digest(root / name) != value: raise ValueError("sequential artifact changed: " + name)
    derived, result = derive(root, plan)
    if result["decision"] == "continue" or receipt["decision"] != result["decision"]:
        raise ValueError("sequential receipt has no matching stopping decision")
    for name, content in derived.items():
        if (root / name).read_bytes() != content: raise ValueError("fabricated sequential derived output: " + name)
    if load(root)[2] != plan_hash or any(digest(root / name) != value for name, value in receipt["artifacts"].items()):
        raise ValueError("sequential evidence changed during verification")
    return receipt


def execute(directory, player=None):
    root, plan, plan_hash = load(directory)
    if (root / "receipt.json").exists(): return verify(root)
    load(root, require_engines=True)
    config = plan["configuration"]
    checkpoint = root / "checkpoint.json"
    if checkpoint.exists(): games = load_checkpoint(checkpoint, config)
    else:
        games = []
        save_checkpoint(checkpoint, config, games)
    status = assessment(plan, games)
    by_name = {opening["id"]: opening for opening in config["opening_cases"]}
    binaries = {label: pathlib.Path(engine["path"]) for label, engine in config["engines"].items()}
    for pair in config["policy"]["pair_schedule"][len(games) // 2:]:
        if status["decision"] != "continue": break
        completed = []
        for pair_game, white in enumerate(pair["white_order"], 1):
            game = (play_game if player is None else player)(by_name[pair["opening"]], binaries, white,
                config["policy"]["go"], config["policy"]["searched_ply_limit"], config["policy"]["watchdog_seconds"], profiles=config["profiles"])
            game.update(round=1, pair=pair["pair"], pair_game=pair_game)
            completed.append(game)
        load(root, require_engines=True)
        games.extend(completed)
        save_checkpoint(checkpoint, config, games)
        games = load_checkpoint(checkpoint, config)
        status = assessment(plan, games)
    derived, result = derive(root, plan)
    if result["decision"] == "continue": raise ValueError("sequential run ended before its stopping condition")
    for name, content in derived.items(): atomic_write(root / name, content)
    load(root, require_engines=True)
    receipt = {"receipt_version": 1, "plan_sha256": plan_hash, "artifacts": {name: digest(root / name) for name in FILES},
        "decision": result["decision"]}
    atomic_write(root / "receipt.json", encoded(receipt))
    try: return verify(root)
    except Exception:
        (root / "receipt.json").unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Run/resume/replay-verify a capped exact paired-sign SPRT")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("run")
    start.add_argument("candidate", type=pathlib.Path)
    start.add_argument("baseline", type=pathlib.Path)
    start.add_argument("--campaign", type=pathlib.Path, required=True)
    start.add_argument("--directory", type=pathlib.Path, required=True)
    for name, default in (("p0", "0.5"), ("p1", "0.55"), ("alpha", "0.05"), ("beta", "0.05")):
        start.add_argument("--" + name, default=default)
    for name in ("resume", "verify"):
        command = commands.add_parser(name)
        command.add_argument("directory", type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "run":
        campaign = load_campaign(args.campaign)
        parameters = {name: getattr(args, name) for name in ("p0", "p1", "alpha", "beta")}
        parameters["max_pairs"] = len(campaign["openings"])
        result = execute(initialize(args.directory, args.candidate, args.baseline, args.campaign, parameters))
    else: result = execute(args.directory) if args.command == "resume" else verify(args.directory)
    sys.stdout.buffer.write(encoded(result))


if __name__ == "__main__":
    main()
