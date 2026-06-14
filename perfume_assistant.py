import sys
import requests
from build_chromadb import query_index, format_context

BASE_URL = "http://127.0.0.1:1234/v1"
MODEL = "qwen/qwen3-4b-2507"


def ask(query, db_dir="chroma_db", top_k=3):
    results = query_index(query, db_dir=db_dir, n_results=top_k)
    context = format_context(results[:top_k], query)
    prompt = context + " " + "Return a ranked recommendation with a short explanation for each item. Keep it concise but a little more detailed than a list."
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a perfume recommendation assistant. Output only final answers, never reasoning traces. Stop after recommending 2 perfumes."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 300,
        "stream": False,
    }
    r = requests.post(f"{BASE_URL}/chat/completions", json=payload, timeout=120)
    if not r.ok:
        raise RuntimeError(f"LM Studio error {r.status_code}: {r.text}")
    data = r.json()
    msg = data["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning_content") or str(data)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "winter coffee vanilla"
    print(ask(query))