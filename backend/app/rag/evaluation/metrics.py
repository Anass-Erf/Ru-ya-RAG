import statistics
import time


def metrics(ranked, relevant, k):
    if k < 1 or not relevant:
        raise ValueError('Positive k and nonempty relevance labels required')
    unique = list(dict.fromkeys(ranked))[:k]
    hits = len(set(unique) & set(relevant))
    return {'recall': hits / len(set(relevant)), 'precision': hits / k,
            'reciprocal_rank': next((1 / rank for rank, item in enumerate(unique, 1) if item in relevant), 0.0)}


def evaluate(index, dataset, modes=('bm25','dense','hybrid'), ks=(1,2)):
    if dataset['judgment_status'] != 'assisted_source_review':
        raise ValueError('Evaluation labels require explicit source review; drafts are not scored')
    available = {c.parent_entry_id for c in index.chunks}
    if any(not set(row['relevant_passage_ids']) <= available for row in dataset['queries']):
        raise ValueError('Relevant passages absent from this index')
    rows=[]
    # Warm the encoder explicitly; report query latency separately from model loading.
    if index.embedder:
        index.embedder.encode(['رؤيا'])
    for mode in modes:
        for query in dataset['queries']:
            result=index.search(query['query'],mode=mode,top_k=min(50,len(index.chunks)))
            ranked=[h['chunk']['parent_entry_id'] for h in result['hits']]
            rows.append({'id':query['id'],'mode':mode,'ranked_passage_ids':list(dict.fromkeys(ranked)),
                         'latency_ms':result['latency_ms'],
                         'metrics':{str(k):metrics(ranked,query['relevant_passage_ids'],k) for k in ks}})
    aggregate={}
    for mode in modes:
        selected=[r for r in rows if r['mode']==mode]
        aggregate[mode]={'query_count':len(selected),'mean_latency_ms':statistics.mean(r['latency_ms'] for r in selected),
                         'max_latency_ms':max(r['latency_ms'] for r in selected),
                         'at_k':{str(k):{name:statistics.mean(r['metrics'][str(k)][name] for r in selected)
                                         for name in ['recall','precision','reciprocal_rank']} for k in ks}}
    return {'dataset_id':dataset['id'],'judgment_status':dataset['judgment_status'],
            'limitation':dataset['limitation'],'corpus_policy':index.config['policy'],
            'corpus_checksum':index.config['corpus_checksum'],'latency_scope':'warm query only; excludes model/index loading',
            'aggregate':aggregate,'queries':rows}
