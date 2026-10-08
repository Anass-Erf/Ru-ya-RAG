
import json
import re
from pathlib import Path

from .paths import DATA_DIR

INPUT = DATA_DIR / "processed" / "structure_candidates.jsonl"
OUTPUT = DATA_DIR / "processed" / "normalized_headings.jsonl"

ARABIC_LETTERS = (
    "الألف|الباء|التاء|الثاء|الجيم|الحاء|الخاء|"
    "الدال|الذال|الراء|الزاي|السين|الشين|"
    "الصاد|الضاد|الطاء|الظاء|العين|الغين|"
    "الفاء|القاف|الكاف|اللام|الميم|النون|"
    "الهاء|الواو|الياء"
)

def normalize_heading(heading):
    text = " ".join(heading.split())

    # Repair split final hamza in known chapter labels
    text = re.sub(
        r"\b(البا|التا|الثا|الحا|الخا|الرا|الزا|"
        r"السا|الشا|الفا|الها)\s+ء\b",
        r"\1ء",
        text
    )

    # Known PDF extraction artifact
    text = text.replace("االله", "الله")

    return text


def main():
    records = []

    with open(INPUT, encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)

            record["original_heading"] = record["heading"]
            record["heading"] = normalize_heading(
                record["heading"]
            )

            # Normalization is NOT human validation
            record["validated"] = False

            records.append(record)

    with open(OUTPUT, "w", encoding="utf-8") as file:
        for record in records:
            file.write(
                json.dumps(record, ensure_ascii=False)
                + "\n"
            )

    print(f"Processed {len(records)} headings")

    for record in records[:10]:
        print(
            record["original_heading"],
            "=>",
            record["heading"]
        )


if __name__ == "__main__":
    main()
