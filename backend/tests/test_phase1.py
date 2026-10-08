"""Offline checks of relocation and preservation, not segmentation accuracy."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PhaseOneTests(unittest.TestCase):
    def test_preserved_data_checksums(self):
        baseline = json.loads((ROOT / 'storage/manifests/phase1-baseline.json').read_text())
        for record in baseline['files']:
            relative = record['path']
            if relative.startswith('src/') or relative.endswith('.py'):
                continue
            if relative.startswith('v1/'):
                relative = 'archive/previous_lessons/' + relative
            path = ROOT / relative
            if not path.exists() and relative.startswith('data/processed/'):
                path = ROOT / 'data/quarantine' / path.name
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'])

    def test_pipeline_reproduces_existing_outputs_from_another_directory(self):
        from archive.previous_lessons.phase1_pipeline.run import STAGES
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            shutil.copytree(ROOT / 'data/extracted', data / 'extracted')
            for stage, (_, folder, outputs) in STAGES.items():
                if stage == 'extract':
                    continue
                result = subprocess.run([sys.executable, str(ROOT / 'archive/previous_lessons/phase1_pipeline/run.py'), stage,
                                         '--data-dir', str(data)], cwd=directory, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in outputs:
                    with self.subTest(stage=stage, name=name):
                        self.assertEqual((data / folder / name).read_bytes(),
                                         (ROOT / 'data' / folder / name).read_bytes())

    def test_existing_outputs_are_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data / 'processed').mkdir()
            sentinel = data / 'processed/pages.jsonl'
            sentinel.write_text('preserve me')
            result = subprocess.run([sys.executable, str(ROOT / 'archive/previous_lessons/phase1_pipeline/run.py'), 'all',
                                     '--data-dir', directory], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refusing to overwrite', result.stderr)
            self.assertEqual(sentinel.read_text(), 'preserve me')
            self.assertFalse((data / 'extracted').exists())


if __name__ == '__main__':
    unittest.main()
