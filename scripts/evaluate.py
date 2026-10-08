import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from backend.app.rag.embeddings.minilm import MiniLM
    from backend.app.rag.retrieval.index import SearchIndex
    from backend.app.rag.evaluation.metrics import evaluate
    parser=argparse.ArgumentParser(description='Evaluate reviewed passage judgments against a real index.')
    parser.add_argument('--index',required=True,type=Path)
    parser.add_argument('--dataset',type=Path,default=ROOT/'data/evaluation/retrieval-smoke.json')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--k',type=int,nargs='+',default=[1,2])
    args=parser.parse_args()
    if any(k < 1 or k > 50 for k in args.k):
        parser.error('k must be between 1 and 50')
    report=evaluate(SearchIndex(args.index,MiniLM()),json.loads(args.dataset.read_text()),ks=tuple(args.k))
    report['dataset_sha256']=__import__('hashlib').sha256(args.dataset.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['aggregate'],indent=2))


if __name__=='__main__':main()
