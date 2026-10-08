"""Build an explicit reviewed or experimental corpus index."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from backend.app.rag.embeddings.minilm import MiniLM
    from backend.app.rag.retrieval.index import build_index
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',choices=['reviewed','experimental'],default='reviewed')
    parser.add_argument('--max-tokens',type=int,default=120)
    parser.add_argument('--overlap',type=int,default=16)
    parser.add_argument('--download-model',action='store_true')
    args=parser.parse_args()
    model=MiniLM(local_only=not args.download_model)
    path,reused=build_index(ROOT,ROOT/'storage/indexes',model,args.policy,args.max_tokens,args.overlap)
    print(f'{path}\nreused={reused}')


if __name__=='__main__':main()
