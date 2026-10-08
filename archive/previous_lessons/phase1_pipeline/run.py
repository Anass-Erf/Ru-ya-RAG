"""Run the preserved ingestion stages without overwriting outputs by default."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

STAGES = {
    "extract": ("pdf_extractor", "extracted", [
        "nabulsi_raw.txt", "nabulsi_candidate.txt", "ibn-Shahin_raw.txt",
        "ibn-Shahin_candidate.txt", "report.json"]),
    "clean": ("clean_validate", "processed", ["pages.jsonl", "quality_report.json", "review_samples.txt"]),
    "structure": ("detect_structure", "processed", ["structure_candidates.jsonl", "structure_report.json"]),
    "headings": ("validate_headings", "processed", ["normalized_headings.jsonl"]),
    "detect": ("detect_nabulsi_entries", "processed", ["nabulsi_entry_candidates_v3.jsonl", "nabulsi_entry_report_v3.json"]),
    "entries": ("build_nabulsi_entries", "processed", ["nabulsi_entries_review.jsonl", "nabulsi_entries_report.json", "nabulsi_entries_samples.txt"]),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=[*STAGES, "all"])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace existing generated outputs")
    args = parser.parse_args()
    data = args.data_dir.resolve()
    selected = list(STAGES) if args.stage == "all" else [args.stage]
    existing = [data / folder / name for stage in selected
                for _, folder, names in [STAGES[stage]] for name in names
                if (data / folder / name).exists()]
    if existing and not args.overwrite:
        parser.error("Refusing to overwrite existing outputs; use a separate --data-dir or --overwrite: "
                     + ", ".join(str(p) for p in existing))
    os.environ["RUYA_DATA_DIR"] = str(data)
    for stage in selected:
        module_name, folder, _ = STAGES[stage]
        (data / folder).mkdir(parents=True, exist_ok=True)
        module = importlib.import_module(f"archive.previous_lessons.phase1_pipeline.{module_name}")
        if stage == "extract":
            results = [module.extract_one(name) for name in module.BOOKS]
            (data / folder / "report.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            module.main()


if __name__ == "__main__":
    main()
