"""Extract and reconstruct review-only passages into immutable versioned runs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from backend.app.rag.ingestion.catalog import BOOKS
    from backend.app.rag.ingestion.pipeline import run_ingestion
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', nargs='?', choices=['all'], default='all')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--output-root', type=Path, help='Default: DATA_DIR/processed/ingestion')
    parser.add_argument('--books', nargs='+', choices=list(BOOKS), default=list(BOOKS))
    args = parser.parse_args()
    data = args.data_dir.resolve()
    try:
        path, reused = run_ingestion(data, (args.output_root or data / 'processed/ingestion').resolve(), args.books)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Ingestion failed: {exc}\n')
    print(json.dumps({'run_directory': str(path), 'reused': reused, 'report': str(path / 'report.json')}, indent=2))


if __name__ == '__main__':
    main()
