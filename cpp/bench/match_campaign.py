import argparse
import json
import pathlib
import re
import sys

from search_benchmark import digest, validate_output_path


def load_campaign(path):
    from uci_matches import load_openings, load_profiles, opening_position, repetition_identity
    source = pathlib.Path(path).resolve(strict=True)
    source_hash = digest(source)
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("duplicate campaign JSON key")
            result[key] = value
        return result
    data = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    fields = {"version", "name", "openings", "openings_sha256", "opening_ids", "profiles", "profiles_sha256",
        "search_budget", "rounds", "seed", "max_plies", "timeout"}
    if not isinstance(data, dict) or set(data) != fields or type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("campaign requires exact version-1 fields")
    if not isinstance(data["name"], str) or not data["name"].strip() or any(ord(c) < 32 or ord(c) == 127 for c in data["name"]):
        raise ValueError("invalid campaign name")
    for key in ("openings", "profiles"):
        if key == "profiles" and data[key] is None: continue
        if not isinstance(data[key], str) or not data[key]: raise ValueError("campaign source path must be nonempty")
    budget = data["search_budget"]
    if (not isinstance(budget, dict) or set(budget) != {"kind", "value"} or
        not isinstance(budget["kind"], str) or budget["kind"] not in {"depth", "nodes", "movetime"}):
        raise ValueError("invalid campaign search budget")
    if type(budget["value"]) is not int or not 1 <= budget["value"] <= (64 if budget["kind"] == "depth" else (1 << 64) - 1):
        raise ValueError("campaign budget out of range")
    for key, minimum, maximum in (("rounds", 1, (1 << 31) - 1), ("seed", 0, (1 << 64) - 1), ("max_plies", 1, (1 << 31) - 1), ("timeout", 1, 3600)):
        if type(data[key]) is not int or not minimum <= data[key] <= maximum:
            raise ValueError(f"invalid campaign {key}")
    if budget["kind"] == "movetime" and budget["value"] >= data["timeout"] * 1000:
        raise ValueError("campaign movetime must be shorter than watchdog")
    opening_path = (source.parent / data["openings"]).resolve(strict=True)
    profile_path = (source.parent / data["profiles"]).resolve(strict=True) if data["profiles"] is not None else None
    for key, input_path in (("openings_sha256", opening_path), ("profiles_sha256", profile_path)):
        expected = data[key]
        if input_path is None:
            if expected is not None: raise ValueError("absent campaign profile must have null hash")
        elif not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None or digest(input_path) != expected:
            raise ValueError("campaign input hash mismatch")
    openings = load_openings(opening_path)
    if data["opening_ids"] != [opening["id"] for opening in openings]:
        raise ValueError("campaign opening IDs/order differ from source")
    identities = [repetition_identity(opening_position(opening)[0]) for opening in openings]
    if len(set(identities)) != len(identities):
        raise ValueError("campaign contains duplicate final opening positions")
    profiles = load_profiles(profile_path)
    if digest(source) != source_hash or digest(opening_path) != data["openings_sha256"] or (
        profile_path is not None and digest(profile_path) != data["profiles_sha256"]):
        raise ValueError("campaign sources changed during validation")
    metadata = {"path": str(source), "sha256": source_hash, "specification": data}
    return {"metadata": metadata, "opening_path": opening_path, "profile_path": profile_path,
        "openings": openings, "profiles": profiles}


def audit_campaign(report, path):
    from analyze_matches import analyze_report
    from uci_matches import build_schedule, DRAW_POLICY
    campaign = load_campaign(path)
    metadata = campaign["metadata"]
    data = metadata["specification"]
    canonical = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
    if canonical(report.get("campaign")) != canonical(metadata):
        raise ValueError("report campaign provenance differs from supplied plan")
    openings = campaign["openings"]
    policy = report["policy"]
    required = {"go": f"go {data['search_budget']['kind']} {data['search_budget']['value']}",
        "search_budget": data["search_budget"], "rounds": data["rounds"], "searched_ply_limit": data["max_plies"],
        "watchdog_seconds": data["timeout"], "schedule_seed": data["seed"],
        "pair_schedule": build_schedule(openings, data["rounds"], data["seed"]), "draws": DRAW_POLICY,
        "errors": "abort run without assigning a game result", "ply_limit_result": "unfinished"}
    if any(canonical(policy.get(key)) != canonical(value) for key, value in required.items()):
        raise ValueError("reported controls differ from campaign")
    if report.get("openings") != {"path": str(campaign["opening_path"]), "sha256": digest(campaign["opening_path"])}:
        raise ValueError("campaign opening provenance mismatch")
    profile_source = {"path": str(campaign["profile_path"]), "sha256": digest(campaign["profile_path"])} if campaign["profile_path"] else None
    if report.get("profiles") != campaign["profiles"] or report.get("profile_source") != profile_source:
        raise ValueError("campaign profile provenance mismatch")
    analysis = analyze_report(report)
    by_name = {opening["id"]: opening for opening in openings}
    for game in report["games"]:
        opening = by_name[game["opening"]]
        prefix = opening.get("moves", [])
        if game["root_fen"] != opening["fen"] or game["opening_plies"] != len(prefix) or game["moves"][:len(prefix)] != prefix:
            raise ValueError("game differs from campaign opening history")
    if (digest(pathlib.Path(path)) != metadata["sha256"] or digest(campaign["opening_path"]) != data["openings_sha256"] or
        (campaign["profile_path"] is not None and digest(campaign["profile_path"]) != data["profiles_sha256"])):
        raise ValueError("campaign sources changed during audit")
    return {"campaign_audit_schema_version": 1, "campaign": metadata, "plan_controls_match": True,
        "opening_histories_match": True, "completed_schedule_replayed": True,
        "analysis": analysis, "inference": "none; declared controls are not authenticated engine execution or strength evidence"}


def main():
    parser = argparse.ArgumentParser(description="Replay and audit a completed match against its declared campaign")
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--campaign", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    source = args.report.resolve(strict=True)
    campaign = load_campaign(args.campaign)
    validate_output_path(args.output, [source, args.campaign, campaign["opening_path"], campaign["profile_path"]])
    source_hash = digest(source)
    result = audit_campaign(json.loads(source.read_text(encoding="utf-8")), args.campaign)
    if digest(source) != source_hash: raise ValueError("match report changed during audit")
    result["source_report"] = {"path": str(source), "sha256": source_hash}
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output is None: sys.stdout.write(encoded)
    else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
