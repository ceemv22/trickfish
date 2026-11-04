import argparse
import json
import pathlib
import subprocess
import sys

from trickfish.practical_review import ReviewPolicy
from dataclasses import asdict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen-dir", required=True, type=pathlib.Path)
    parser.add_argument("--verification-dir", required=True, type=pathlib.Path)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument("--policy", type=pathlib.Path)
    args = parser.parse_args()
    policy = ReviewPolicy(**json.loads(args.policy.read_text())) if args.policy else ReviewPolicy()
    manifest = pathlib.Path(__file__).with_name("practical-positions.json").read_bytes()
    cases = json.loads(manifest)["positions"]
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "manifest.json").write_bytes(manifest)
    guide = pathlib.Path(__file__).resolve().parents[1] / "docs" / "expert-pilot.md"
    (args.output_dir / "pilot-guide.md").write_bytes(guide.read_bytes())
    policy_path = args.output_dir / "policy.json"
    policy_path.write_text(json.dumps(asdict(policy), indent=2), encoding="utf-8")
    rows = []
    for case in cases:
        name = case["name"]
        command = [sys.executable, "-m", "trickfish.practical_review",
                   str(args.screen_dir / (name + ".json")), str(args.verification_dir / (name + ".json")),
                   "--output-dir", str(args.output_dir / name), "--policy", str(policy_path)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode:
            row = {"case": name, "status": "incomplete", "error": completed.stderr}
        else:
            assessment = json.loads((args.output_dir / name / "assessment.json").read_text())
            row = {"case": name, **{key: assessment[key] for key in ("status", "nominee", "verification_selection",
                   "verified_objective_loss_cp", "modeled_advantage_over_objective_cp", "reasons")}}
        rows.append(row)
        print(name, row["status"], flush=True)
        (args.output_dir / "index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = ["# Expert review package", "", "This inspected integration set is not held-out validation. No human benefit or payment readiness is established.", "",
             "Start with [the coach pilot guide](pilot-guide.md). Each completed case includes an unfilled feedback.json bound to its assessment hash.", "",
             "Thresholds are in policy.json; raw source analyses and their hashes accompany each worksheet.", "",
             "| Case | Status | Screening nominee | Verification selection | Reasons | Review |",
             "| --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        name = row["case"]
        link = "incomplete" if row["status"] == "incomplete" else f"[worksheet]({name}/worksheet.md), [PGN]({name}/verification.pgn)"
        if row.get("nominee") is not None:
            link += f", [nominee check]({name}/nominee.pgn)"
        lines.append(f"| {name} | {row['status']} | {row.get('nominee', '-')} | {row.get('verification_selection', '-')} | {', '.join(row.get('reasons', []))} | {link} |")
    count = sum(row["status"] == "review_candidate" for row in rows)
    lines += ["", f"Review candidates under the recorded policy: {count}/{len(rows)}. This is not a success rate or a monetization percentage.", ""]
    (args.output_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")
    return int(any(row["status"] == "incomplete" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
