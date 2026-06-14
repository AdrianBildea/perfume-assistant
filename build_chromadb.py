import json
import sys
from pathlib import Path

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    import requests
except ImportError:
    requests = None


def load_jsonl(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def doc_text(p):
    notes = p.get('notes_pyramid', {})
    accords = p.get('accords', [])
    perfumers = p.get('perfumers', [])
    parts = [
        f"Name: {p.get('name','')}",
        f"Brand: {p.get('brand','')}",
        f"Country: {p.get('country','')}",
        f"Year: {p.get('year','')}",
        f"Gender: {p.get('gender','')}",
        f"Rating: {p.get('rating',{}).get('score','')}",
        f"Votes: {p.get('rating',{}).get('votes','')}",
        f"Top notes: {', '.join(notes.get('top', []))}",
        f"Middle notes: {', '.join(notes.get('middle', []))}",
        f"Base notes: {', '.join(notes.get('base', []))}",
        f"Accords: {', '.join(accords)}",
        f"Perfumers: {', '.join(perfumers)}",
        f"URL: {p.get('url','')}",
        f"Source: {p.get('source','')}",
        f"Description: {p.get('description','') or ''}",
    ]
    return '\n'.join([x for x in parts if x and x.strip()])


def build_index(jsonl_path, db_dir='chroma_db', collection_name='perfumes'):
    if chromadb is None:
        raise SystemExit('Install chromadb first: pip install chromadb')

    client = chromadb.PersistentClient(path=db_dir)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    col = client.create_collection(name=collection_name)

    docs, metas, ids = [], [], []
    for i, p in enumerate(load_jsonl(jsonl_path), 1):
        docs.append(doc_text(p))
        metas.append({
            'name': str(p.get('name','')),
            'brand': str(p.get('brand','')),
            'year': str(p.get('year','')),
            'gender': str(p.get('gender','')),
            'country': str(p.get('country','')),
            'source': str(p.get('source','')),
            'url': str(p.get('url','')),
        })
        ids.append(str(p.get('id') or p.get('url') or i))

        if len(docs) >= 100:
            col.add(documents=docs, metadatas=metas, ids=ids)
            print(f'Added batch ending at {i}')
            docs, metas, ids = [], [], []

    if docs:
        col.add(documents=docs, metadatas=metas, ids=ids)
        print('Added final batch')

    return db_dir, collection_name


def rerank_results(results, query):
    q = query.lower()
    kws = [w for w in q.replace('-', ' ').split() if len(w) > 2]
    scored = []
    for r in results:
        doc = (r.get('document') or '').lower()
        meta = r.get('metadata') or {}
        hay = ' '.join([doc, str(meta.get('name','')), str(meta.get('brand','')), str(meta.get('country','')), str(meta.get('gender',''))]).lower()
        score = 0
        for kw in kws:
            if kw in hay:
                score += 1
        if 'coffee' in q and ('coffee' in hay or 'cafe' in hay or 'caff' in hay):
            score += 4
        if 'vanilla' in q and ('vanilla' in hay or 'vanille' in hay):
            score += 3
        if 'winter' in q and any(x in hay for x in ['winter','cold','warm','amber','spice','woody','tonka']):
            score += 2
        if 'summer' in q and any(x in hay for x in ['fresh','citrus','aquatic','marine','ozonic']):
            score += 2
        scored.append((score, r))
    scored.sort(key=lambda x: (x[0], -x[1].get('distance', 9999)), reverse=True)
    return [r for s, r in scored]


def query_index(query, db_dir='chroma_db', collection_name='perfumes', n_results=5):
    if chromadb is None:
        raise SystemExit('Install chromadb first: pip install chromadb')

    client = chromadb.PersistentClient(path=db_dir)
    col = client.get_collection(collection_name)
    res = col.query(query_texts=[query], n_results=n_results)
    items = []
    for i in range(len(res['ids'][0])):
        items.append({
            'id': res['ids'][0][i],
            'distance': res['distances'][0][i] if 'distances' in res else None,
            'metadata': res['metadatas'][0][i],
            'document': res['documents'][0][i],
        })
    return rerank_results(items, query)


def build_index_preview(jsonl_path, limit=5):
    docs = []
    for i, p in enumerate(load_jsonl(jsonl_path), 1):
        docs.append(doc_text(p))
        if i >= limit:
            break
    print(f'Preview loaded {len(docs)} docs')
    for d in docs[:2]:
        print('---')
        print(d[:400])


def format_context(results, query):
    lines = [f'Query: {query}', '', 'Relevant perfumes:']
    for i, r in enumerate(results[:3], 1):
        m = r['metadata']
        doc = (r.get('document') or '').splitlines()
        notes = [x for x in doc if x.lower().startswith('top notes:') or x.lower().startswith('middle notes:') or x.lower().startswith('base notes:') or x.lower().startswith('accords:')]
        lines += [
            '',
            f'{i}. {m.get("name","")} by {m.get("brand","")} ({m.get("year","")})',
            f'Country: {m.get("country","")}',
            f'Gender: {m.get("gender","")}',
            *notes[:4],
            f'URL: {m.get("url","")}',
            '---',
        ]
    return '\n'.join(lines)


def ask_lm_studio(prompt, model='local-model', base_url='http://localhost:1234/v1'):
    if requests is None:
        raise SystemExit('Install requests first: pip install requests')
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a helpful perfume assistant.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.4,
    }
    r = requests.post(f'{base_url}/chat/completions', json=payload, timeout=120)
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python build_chromadb.py build perfumes.jsonl [db_dir]')
        print('   or: python build_chromadb.py query "winter coffee vanilla" [db_dir]')
        print('   or: python build_chromadb.py rag "winter coffee vanilla" [db_dir]')
        raise SystemExit(1)

    mode = sys.argv[1]
    arg = sys.argv[2]
    db_dir = sys.argv[3] if len(sys.argv) > 3 else 'chroma_db'

    if mode == 'build':
        build_index(arg, db_dir=db_dir)
        print(f'Built ChromaDB at {db_dir}')
    elif mode == 'query':
        results = query_index(arg, db_dir=db_dir)
        for r in results:
            print('\n---')
            print(r['metadata'])
            print(r['document'][:400])
    elif mode == 'preview':
        build_index_preview(arg)
    elif mode == 'rag':
        results = query_index(arg, db_dir=db_dir)
        context = format_context(results, arg)
        print(context)
    else:
        raise SystemExit('Unknown mode')
