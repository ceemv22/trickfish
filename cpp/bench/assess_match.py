import argparse
from decimal import Decimal, localcontext
import json
import math
import pathlib
import re
import sys

from match_campaign import audit_campaign, load_campaign
from search_benchmark import digest, validate_output_path


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def alpha_ratio(text):
    if not isinstance(text, str) or re.fullmatch(r"0\.[0-9]{1,12}", text) is None:
        raise ValueError("alpha must be a decimal string with 1..12 fractional digits")
    value = Decimal(text)
    if not Decimal("0") < value < Decimal("0.5"):
        raise ValueError("alpha must be strictly between zero and 0.5")
    return value.as_integer_ratio()


def exact_sign_tail(wins, losses):
    if any(type(value) is not int or value < 0 for value in (wins, losses)) or wins + losses > 4096:
        raise ValueError("sign counts must be nonnegative integers totaling at most 4096")
    count = wins + losses
    return sum(math.comb(count, index) for index in range(wins, count + 1)), 1 << count


def sign_result(wins, losses, ties, alpha):
    numerator, denominator = exact_sign_tail(wins, losses)
    if type(ties) is not int or ties < 0 or wins + losses + ties > 4096:
        raise ValueError("invalid tied pair count")
    a, b = alpha_ratio(alpha)
    with localcontext() as context:
        context.prec = 17
        probability = str(Decimal(numerator) / Decimal(denominator))
    rejected = numerator * b <= denominator * a
    return {"wins": wins, "losses": losses, "ties": ties, "decisive_pairs": wins + losses,
        "p_value_decimal": probability, "p_value_display_precision": 17,
        "null_rejected": rejected, "decision": "null_rejected" if rejected else "not_rejected"}


def campaign_inputs(campaign):
    return [campaign["metadata"]["path"], campaign["opening_path"], campaign["profile_path"]]


def create_plan(candidate, baseline, campaign_path, alpha="0.05"):
    alpha_ratio(alpha)
    campaign = load_campaign(campaign_path)
    data = campaign["metadata"]["specification"]
    if data["rounds"] != 1 or not 1 <= len(campaign["openings"]) <= 4096:
        raise ValueError("sign plan requires one round and 1..4096 unique openings")
    return {"version": 1, "test": "fixed_horizon_paired_sign", "campaign": str(pathlib.Path(campaign_path).resolve()),
        "campaign_sha256": campaign["metadata"]["sha256"], "candidate_sha256": digest(candidate),
        "baseline_sha256": digest(baseline), "candidate_label": "a", "pairs": len(campaign["openings"]), "alpha": alpha}


def load_plan(path, campaign_override=None):
    source = pathlib.Path(path).resolve(strict=True)
    source_hash = digest(source)
    data = read_json(source)
    fields = {"version", "test", "campaign", "campaign_sha256", "candidate_sha256", "baseline_sha256",
        "candidate_label", "pairs", "alpha"}
    if (not isinstance(data, dict) or set(data) != fields or type(data["version"]) is not int or data["version"] != 1 or
        data["test"] != "fixed_horizon_paired_sign" or data["candidate_label"] != "a"):
        raise ValueError("expected exact version-1 sign plan fields with candidate a")
    if type(data["pairs"]) is not int or not 1 <= data["pairs"] <= 4096:
        raise ValueError("invalid fixed pair horizon")
    for key in ("campaign_sha256", "candidate_sha256", "baseline_sha256"):
        if not isinstance(data[key], str) or re.fullmatch(r"[0-9a-f]{64}", data[key]) is None:
            raise ValueError("invalid plan hash")
    if not isinstance(data["campaign"], str) or not data["campaign"]:
        raise ValueError("missing campaign path")
    alpha_ratio(data["alpha"])
    campaign_path = source.parent / data["campaign"] if campaign_override is None else pathlib.Path(campaign_override)
    campaign = load_campaign(campaign_path.resolve(strict=True))
    if (campaign["metadata"]["sha256"] != data["campaign_sha256"] or
        campaign["metadata"]["specification"]["rounds"] != 1 or len(campaign["openings"]) != data["pairs"]):
        raise ValueError("campaign differs from fixed sign plan")
    if digest(source) != source_hash: raise ValueError("plan changed during loading")
    return data, campaign, {"path": str(source), "sha256": source_hash}


def assess_report(report, plan_path, campaign_override=None):
    plan, campaign, source = load_plan(plan_path, campaign_override)
    audit = audit_campaign(report, campaign["metadata"]["path"])
    if audit["campaign"] != campaign["metadata"]: raise ValueError("campaign changed during assessment")
    for label, key in (("a", "candidate_sha256"), ("b", "baseline_sha256")):
        if report["engines"][label]["sha256"] != plan[key]: raise ValueError("engine differs from sign plan")
    pairs = audit["analysis"]["paired"]
    if not pairs["available"] or pairs["pairs"] != plan["pairs"]: raise ValueError("fixed horizon not completed")
    blockers = []
    if pairs["unfinished_pairs"]: blockers.append("unfinished_pairs")
    if plan["candidate_sha256"] == plan["baseline_sha256"]: blockers.append("identical_binary_bytes")
    bins = pairs["bin_counts"]
    statistic = None if blockers else sign_result(bins[3] + bins[4], bins[0] + bins[1], bins[2], plan["alpha"])
    if digest(pathlib.Path(source["path"])) != source["sha256"]: raise ValueError("plan changed during assessment")
    if load_campaign(campaign["metadata"]["path"])["metadata"] != campaign["metadata"]:
        raise ValueError("campaign changed during assessment")
    return {"match_assessment_schema_version": 1, "source_plan": source, "plan": plan,
        "campaign_audit": audit, "status": "inconclusive" if blockers else "evaluated", "blockers": blockers,
        "statistic": statistic, "method": {"kind": "one-sided exact paired sign test", "candidate": "a",
            "null": "candidate wins at most half of decisive color pairs", "tied_pair_policy": "excluded from sign statistic",
            "unfinished_policy": "any unfinished pair blocks hypothesis evaluation",
            "decision_arithmetic": "exact integer tail compared with exact decimal alpha",
            "assumptions": ["conditional on which pairs tie, independent decisive signs with null success probability at most one half",
                "plan fixed before outcomes; evaluate only once at the fixed horizon",
                "opening selection and engine configuration fixed independently of outcomes"],
            "limitations": "does not test mean score or Elo; no SPRT, authenticated execution, prespecification proof or general strength claim"}}


def main():
    parser = argparse.ArgumentParser(description="Plan and assess a fixed-horizon paired sign test")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("plan")
    prepare.add_argument("candidate", type=pathlib.Path)
    prepare.add_argument("baseline", type=pathlib.Path)
    prepare.add_argument("--campaign", type=pathlib.Path, required=True)
    prepare.add_argument("--alpha", default="0.05")
    prepare.add_argument("--output", type=pathlib.Path, required=True)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("report", type=pathlib.Path)
    evaluate.add_argument("--plan", type=pathlib.Path, required=True)
    evaluate.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "plan":
        campaign = load_campaign(args.campaign)
        validate_output_path(args.output, [args.candidate, args.baseline, *campaign_inputs(campaign)])
        result = create_plan(args.candidate, args.baseline, args.campaign, args.alpha)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    else:
        _, campaign, plan_source = load_plan(args.plan)
        validate_output_path(args.output, [args.report, args.plan, *campaign_inputs(campaign)])
        report_hash = digest(args.report)
        report = read_json(args.report)
        binary_paths = [engine["path"] for engine in report.get("engines", {}).values()
            if isinstance(engine, dict) and isinstance(engine.get("path"), str) and pathlib.Path(engine["path"]).exists()]
        validate_output_path(args.output, binary_paths)
        result = assess_report(report, args.plan)
        if result["source_plan"] != plan_source: raise ValueError("plan changed during assessment")
        if digest(args.report) != report_hash: raise ValueError("report changed during assessment")
        result["source_report"] = {"path": str(args.report.resolve()), "sha256": report_hash}
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output is None: sys.stdout.write(encoded)
        else: args.output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
