import argparse
import copy
import json
import os
import pathlib
import subprocess
import sys
import uuid

from assess_match import assess_report, create_plan, load_plan, read_json
from export_matches import export_report
from match_campaign import audit_campaign, load_campaign
from match_checkpoint import load_checkpoint
from search_benchmark import digest


BENCH = pathlib.Path(__file__).resolve().parent
METHOD_FILES = ("run_experiment.py", "uci_matches.py", "match_checkpoint.py", "match_campaign.py",
    "assess_match.py", "analyze_matches.py", "export_matches.py", "search_benchmark.py")
ARTIFACTS = ("matches.json", "checkpoint.json", "audit.json", "assessment.json", "games.pgn", "summary.md")


def method_hashes():
    files = {"cpp/bench/" + name: BENCH / name for name in METHOD_FILES}
    for name in ("__init__.py", "position.py", "move.py", "zobrist.py"):
        files["src/trickfish/" + name] = BENCH.parents[1] / "src" / "trickfish" / name
    return {name: digest(path) for name, path in files.items()}


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def recorded_path(text):
    if not isinstance(text, str) or not text: raise ValueError("missing recorded path")
    path = pathlib.PureWindowsPath(text) if pathlib.PureWindowsPath(text).drive else pathlib.PurePosixPath(text)
    if not path.is_absolute(): raise ValueError("recorded path must be absolute")
    return path


def atomic_write(path, content):
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if created: temporary.unlink(missing_ok=True)


def initialize(directory, candidate, baseline, campaign_path, alpha="0.05", provenance=None):
    root = pathlib.Path(directory).resolve()
    if root.exists(): raise ValueError("experiment directory already exists; use resume or a new directory")
    binaries = {label: pathlib.Path(path).resolve(strict=True) for label, path in (("a", candidate), ("b", baseline))}
    source = load_campaign(campaign_path)
    original = pathlib.Path(source["metadata"]["path"]).read_bytes()
    if digest(pathlib.Path(source["metadata"]["path"])) != source["metadata"]["sha256"]:
        raise ValueError("campaign changed before snapshot")
    if source["metadata"]["specification"]["rounds"] != 1:
        raise ValueError("experiment requires a one-round sign-test campaign")
    hashes = {label: digest(path) for label, path in binaries.items()}
    create_plan(binaries["a"], binaries["b"], campaign_path, alpha)
    build = None if provenance is None else read_json(provenance)
    if build is not None and not isinstance(build, dict): raise ValueError("build provenance must be a JSON object")
    root.mkdir(parents=True)
    inputs = {"source-campaign.json": original, "openings.json": source["opening_path"].read_bytes()}
    specification = copy.deepcopy(source["metadata"]["specification"])
    specification["openings"] = "openings.json"
    if source["profile_path"] is not None:
        inputs["profiles.json"] = source["profile_path"].read_bytes()
        specification["profiles"] = "profiles.json"
    if build is not None: inputs["build-provenance.json"] = encoded(build)
    inputs["campaign.json"] = encoded(specification)
    for name, content in inputs.items():
        (root / name).write_bytes(content)
    campaign = load_campaign(root / "campaign.json")
    if load_campaign(campaign_path)["metadata"] != source["metadata"]:
        raise ValueError("campaign changed during snapshot")
    plan = create_plan(binaries["a"], binaries["b"], root / "campaign.json", alpha)
    if plan["candidate_sha256"] != hashes["a"] or plan["baseline_sha256"] != hashes["b"]:
        raise ValueError("engine changed during experiment setup")
    (root / "sign-plan.json").write_bytes(encoded(plan))
    manifest = {"experiment_version": 1, "directory": str(root), "source_campaign": source["metadata"],
        "engines": {label: {"path": str(path), "sha256": hashes[label]} for label, path in binaries.items()},
        "inputs": {name: digest(root / name) for name in inputs}, "sign_plan_sha256": digest(root / "sign-plan.json"),
        "method_sources": method_hashes()}
    with (root / "experiment.json").open("xb") as stream: stream.write(encoded(manifest))
    load_experiment(root, require_engines=True)
    return root


def load_experiment(directory, require_engines=False):
    root = pathlib.Path(directory).resolve(strict=True)
    manifest_path = root / "experiment.json"
    manifest = read_json(manifest_path)
    fields = {"experiment_version", "directory", "source_campaign", "engines", "inputs", "sign_plan_sha256", "method_sources"}
    if (not isinstance(manifest, dict) or set(manifest) != fields or type(manifest["experiment_version"]) is not int or
        manifest["experiment_version"] != 1):
        raise ValueError("invalid experiment manifest")
    original_root = recorded_path(manifest["directory"])
    if require_engines and manifest["directory"] != str(root):
        raise ValueError("relocated experiments support verification only; resume at the original directory")
    if manifest["method_sources"] != method_hashes(): raise ValueError("experiment method sources changed")
    inputs = manifest["inputs"]
    required = {"source-campaign.json", "campaign.json", "openings.json"}
    if not isinstance(inputs, dict) or not required <= inputs.keys() <= required | {"profiles.json", "build-provenance.json"}:
        raise ValueError("invalid experiment input inventory")
    for name, expected in inputs.items():
        if digest(root / name) != expected: raise ValueError("experiment snapshot changed: " + name)
    if digest(root / "sign-plan.json") != manifest["sign_plan_sha256"]: raise ValueError("experiment sign plan changed")
    plan, campaign, _ = load_plan(root / "sign-plan.json", root / "campaign.json")
    if recorded_path(plan["campaign"]) != original_root / "campaign.json": raise ValueError("sign plan escaped experiment")
    original = read_json(root / "source-campaign.json")
    original["openings"] = "openings.json"
    if original["profiles"] is not None: original["profiles"] = "profiles.json"
    if original != campaign["metadata"]["specification"]: raise ValueError("snapshot changed campaign controls")
    if digest(root / "source-campaign.json") != manifest["source_campaign"]["sha256"]:
        raise ValueError("original campaign hash differs")
    if read_json(root / "source-campaign.json") != manifest["source_campaign"]["specification"]:
        raise ValueError("original campaign specification differs")
    if not isinstance(manifest["engines"], dict) or set(manifest["engines"]) != {"a", "b"}:
        raise ValueError("experiment requires exactly two engine records")
    for label, key in (("a", "candidate_sha256"), ("b", "baseline_sha256")):
        engine = manifest["engines"][label]
        if (not isinstance(engine, dict) or set(engine) != {"path", "sha256"} or not isinstance(engine["path"], str) or
            engine["sha256"] != plan[key]):
            raise ValueError("invalid experiment engine identity")
        recorded_path(engine["path"])
        if require_engines and digest(pathlib.Path(engine["path"])) != engine["sha256"]:
            raise ValueError("experiment engine bytes changed")
    reserved = [root / name for name in (*inputs, "sign-plan.json", "experiment.json", *ARTIFACTS, "receipt.json")]
    existing = [path for path in reserved if path.exists()]
    for index, path in enumerate(existing):
        if path.is_symlink() or not path.is_file(): raise ValueError("experiment paths must be regular files")
        for other in existing[index + 1:]:
            if path.samefile(other): raise ValueError("experiment artifacts must not alias each other")
        for engine in manifest["engines"].values():
            binary = pathlib.Path(engine["path"])
            if binary.exists() and path.samefile(binary): raise ValueError("experiment output aliases engine input")
    return root, manifest


def render_summary(assessment):
    analysis = assessment["campaign_audit"]["analysis"]
    plan = assessment["plan"]
    lines = ["# Trickfish match experiment", "", "Candidate SHA-256: `" + plan["candidate_sha256"] + "`",
        "", "Baseline SHA-256: `" + plan["baseline_sha256"] + "`", "",
        "Search budget: `" + analysis["match_policy"]["go"] + "`. Planned color pairs: " + str(plan["pairs"]) + ".",
        "", "Assessment status: **" + assessment["status"] + "**."]
    if assessment["blockers"]: lines += ["", "Blocked by: " + ", ".join(assessment["blockers"]) + "."]
    statistic = assessment["statistic"]
    if statistic is not None:
        lines += ["", "Sign test: " + statistic["decision"] + "; p=" + statistic["p_value_decimal"] +
            ", alpha=" + plan["alpha"] + "; pair wins/losses/ties=" +
            "/".join(str(statistic[key]) for key in ("wins", "losses", "ties")) + "."]
    lines += ["", "| Engine | Wins | Losses | Draws | Unfinished | Points |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for label in ("a", "b"):
        score = analysis["overall"]["scores"][label]
        values = [label] + [str(score[key]) for key in ("wins", "losses", "draws", "unfinished")]
        values.append(str(analysis["overall"]["points"][label]["points"]))
        lines.append("| " + " | ".join(values) + " |")
    lines += ["", "| Opening | Completed games | Unfinished games | Candidate points |",
        "| --- | ---: | ---: | ---: |"]
    for name, result in analysis["by_opening"].items():
        title = name.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        lines.append("| " + title + " | " + " | ".join(str(value) for value in
            (result["completed"], result["unfinished"], result["points"]["a"]["points"])) + " |")
    lines += ["", "The sign test concerns decisive pair-win frequency under its stated conditional independence and fixed-horizon assumptions.",
        "It does not establish mean-score improvement, Elo, general playing strength or equivalence after non-rejection.",
        "Hashes bind recorded inputs; they do not authenticate engine execution or prove that planning preceded observations.", ""]
    return "\n".join(lines)


def derive_outputs(root, manifest):
    report = read_json(root / "matches.json")
    if report["engines"] != {label: {**engine, "arguments": []} for label, engine in manifest["engines"].items()}:
        raise ValueError("match report engine identities differ from experiment")
    campaign = load_campaign(root / "campaign.json")
    original_root = recorded_path(manifest["directory"])
    original_campaign = {**campaign["metadata"], "path": str(original_root / "campaign.json")}
    original_openings = {"path": str(original_root / "openings.json"), "sha256": digest(root / "openings.json")}
    original_profile = None if campaign["profile_path"] is None else {
        "path": str(original_root / "profiles.json"), "sha256": digest(root / "profiles.json")}
    if (report.get("campaign") != original_campaign or report.get("openings") != original_openings or
        report.get("profile_source") != original_profile):
        raise ValueError("report snapshot provenance differs from experiment")
    replay = copy.deepcopy(report)
    replay["campaign"] = campaign["metadata"]
    replay["openings"] = {**original_openings, "path": str(campaign["opening_path"])}
    if original_profile is not None: replay["profile_source"] = {**original_profile, "path": str(campaign["profile_path"])}
    audit = audit_campaign(replay, root / "campaign.json")
    assessment = assess_report(replay, root / "sign-plan.json", root / "campaign.json")
    audit["campaign"] = original_campaign
    assessment["campaign_audit"]["campaign"] = original_campaign
    assessment["source_plan"]["path"] = str(original_root / "sign-plan.json")
    configuration = {key: value for key, value in report.items() if key not in {"schema_version", "created_utc", "scores", "games"}}
    configuration["opening_cases"] = campaign["openings"]
    if load_checkpoint(root / "checkpoint.json", configuration) != report["games"]:
        raise ValueError("completed checkpoint differs from final report")
    return {"audit.json": encoded(audit), "assessment.json": encoded(assessment),
        "games.pgn": export_report(report).encode("utf-8"), "summary.md": render_summary(assessment).encode("utf-8")}, assessment


def verify(directory):
    root, manifest = load_experiment(directory)
    receipt = read_json(root / "receipt.json")
    if (not isinstance(receipt, dict) or set(receipt) != {"receipt_version", "experiment_sha256", "artifacts", "status", "statistical_decision"} or
        type(receipt["receipt_version"]) is not int or receipt["receipt_version"] != 1 or
        receipt["experiment_sha256"] != digest(root / "experiment.json") or
        not isinstance(receipt["artifacts"], dict) or set(receipt["artifacts"]) != set(ARTIFACTS)):
        raise ValueError("invalid experiment receipt")
    for name, expected in receipt["artifacts"].items():
        if digest(root / name) != expected: raise ValueError("experiment artifact changed: " + name)
    derived, assessment = derive_outputs(root, manifest)
    for name, content in derived.items():
        if (root / name).read_bytes() != content: raise ValueError("derived experiment artifact differs: " + name)
    decision = None if assessment["statistic"] is None else assessment["statistic"]["decision"]
    if receipt["status"] != assessment["status"] or receipt["statistical_decision"] != decision:
        raise ValueError("receipt decision differs from replay")
    load_experiment(root)
    if digest(root / "experiment.json") != receipt["experiment_sha256"] or any(
        digest(root / name) != expected for name, expected in receipt["artifacts"].items()):
        raise ValueError("experiment changed during verification")
    return receipt


def execute(directory, runner=None):
    root, manifest = load_experiment(directory)
    if (root / "receipt.json").exists(): return verify(root)
    load_experiment(root, require_engines=True)
    if not (root / "matches.json").exists():
        command = [sys.executable, str(BENCH / "uci_matches.py"), manifest["engines"]["a"]["path"],
            manifest["engines"]["b"]["path"], "--campaign", str(root / "campaign.json"),
            "--checkpoint", str(root / "checkpoint.json"), "--output", str(root / "matches.json")]
        if (root / "checkpoint.json").exists(): command.append("--resume")
        if runner is None: subprocess.run(command, check=True)
        else: runner(command)
    load_experiment(root, require_engines=True)
    manifest_hash = digest(root / "experiment.json")
    report_hashes = {name: digest(root / name) for name in ("matches.json", "checkpoint.json")}
    derived, assessment = derive_outputs(root, manifest)
    for name, content in derived.items(): atomic_write(root / name, content)
    load_experiment(root, require_engines=True)
    if manifest_hash != digest(root / "experiment.json") or any(digest(root / name) != expected for name, expected in report_hashes.items()):
        raise ValueError("experiment inputs changed during finalization")
    decision = None if assessment["statistic"] is None else assessment["statistic"]["decision"]
    receipt = {"receipt_version": 1, "experiment_sha256": manifest_hash,
        "artifacts": {name: digest(root / name) for name in ARTIFACTS}, "status": assessment["status"], "statistical_decision": decision}
    atomic_write(root / "receipt.json", encoded(receipt))
    try:
        return verify(root)
    except Exception:
        (root / "receipt.json").unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Run, resume and replay-verify a fixed-horizon engine experiment")
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("run")
    start.add_argument("candidate", type=pathlib.Path)
    start.add_argument("baseline", type=pathlib.Path)
    start.add_argument("--campaign", type=pathlib.Path, required=True)
    start.add_argument("--directory", type=pathlib.Path, required=True)
    start.add_argument("--alpha", default="0.05")
    start.add_argument("--provenance", type=pathlib.Path)
    for name in ("resume", "verify"):
        command = commands.add_parser(name)
        command.add_argument("directory", type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "run":
        root = initialize(args.directory, args.candidate, args.baseline, args.campaign, args.alpha, args.provenance)
        result = execute(root)
    elif args.command == "resume": result = execute(args.directory)
    else: result = verify(args.directory)
    sys.stdout.write(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
