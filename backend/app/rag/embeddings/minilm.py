import numpy as np

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'


class MiniLM:
    def __init__(self, model_name=MODEL, revision=REVISION, local_only=True):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(2)
        self.model = SentenceTransformer(model_name, revision=revision, device='cpu', local_files_only=local_only)
        self.tokenizer = self.model.tokenizer
        self.max_tokens = self.model.max_seq_length - self.tokenizer.num_special_tokens_to_add(pair=False)
        self.identity = {'name': model_name, 'revision': revision,
                         'dimension': self.model.get_embedding_dimension(),
                         'normalized': True, 'max_seq_length': self.model.max_seq_length,
                         'input_normalization': 'display-text-NFKC; no search-folding'}

    def encode(self, texts):
        if any(len(self.tokenizer(t, add_special_tokens=False, verbose=False)['input_ids']) > self.max_tokens for t in texts):
            raise ValueError('Embedding input exceeds model token budget; truncation is forbidden')
        vectors = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True,
                                    batch_size=32, show_progress_bar=False)
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or not np.isfinite(vectors).all():
            raise ValueError('Invalid embedding vectors')
        return vectors
