"""Publish a reviewed derivative from explicit decisions tied to one ingestion run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from backend.app.rag.ingestion.models import Passage
    from backend.app.rag.ingestion.pipeline import verify_run, write_jsonl, json_text, file_sha256
    from backend.app.rag.ingestion.review import Decision, apply_decisions
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--decisions', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = verify_run(args.run)
        document = json.loads(args.decisions.read_text(encoding='utf-8'))
        if document['run_id'] != manifest['run_id']:
            raise ValueError('Decisions refer to a different ingestion run')
        decisions = [Decision.model_validate(row) for row in document['decisions']]
        if not decisions:
            raise ValueError('No decisions supplied')
        passages = [Passage.model_validate_json(line) for line in (args.run / 'passages.jsonl').read_text(encoding='utf-8').splitlines()]
        reviewed = apply_decisions(passages, decisions)
        decision_text = json_text({'run_id': manifest['run_id'], 'decisions': [d.model_dump(mode='json') for d in decisions]})
        review_id = hashlib.sha256(decision_text.encode()).hexdigest()[:24]
        target = args.output_root / review_id
        if target.exists():
            verify_run(target)
            print(target)
            return
        args.output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.review-', dir=args.output_root) as temporary:
            stage = Path(temporary) / 'run'
            stage.mkdir()
            write_jsonl(stage / 'passages.jsonl', reviewed)
            (stage / 'decisions.json').write_text(decision_text, encoding='utf-8')
            output_manifest = {'run_id': review_id, 'parent_run_id': manifest['run_id'],
                               'outputs': {p.name: file_sha256(p) for p in stage.iterdir()},
                               'reviewed_count': len(decisions),
                               'verified_count': sum(p.validation_status == 'verified' for p in reviewed)}
            (stage / 'manifest.json').write_text(json_text(output_manifest), encoding='utf-8')
            stage.rename(target)
        print(target)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Review failed: {exc}\n')


if __name__ == '__main__':
    main()
