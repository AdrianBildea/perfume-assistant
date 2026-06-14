import csv
import json
import re
import sys
from pathlib import Path


def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"", "na", "n/a", "none", "unknown", "nan"} else s


def safe_float(v):
    s = clean(v).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def safe_int(v):
    s = clean(v).replace(",", ".")
    try:
        return int(float(s))
    except ValueError:
        return None


def split_list(v):
    s = clean(v)
    if not s:
        return []
    parts = [p.strip() for p in re.split(r"[,;]\s*", s) if p.strip()]
    return [p for p in parts if p.lower() not in {"unknown", "na", "n/a"}]


def safe_filename(text):
    text = re.sub(r"[^\w\-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:140] or "perfume"


def load_pipe_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="|"))


def load_comma_csv(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    last_error = None
    for enc in encodings:
        try:
            with open(path, encoding=enc, errors="replace", newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "|"])
                return list(csv.DictReader(f, dialect=dialect))
        except UnicodeDecodeError as e:
            last_error = e
    raise last_error


def parse_notes_pyramid(raw):
    result = {"top": [], "middle": [], "base": []}
    if not raw:
        return result
    for level, content in re.findall(r"(top|middle|base|notes)\(([^)]*)\)", raw):
        ids = [e.split(",")[0].strip() for e in content.split(";") if e.strip()]
        result["top" if level == "notes" else level] = ids
    return result


def parse_voting(raw):
    if not raw:
        return []
    out = []
    for part in raw.split(";"):
        p = part.split(":")
        if len(p) >= 3:
            try:
                out.append({"id": p[0], "votes": int(float(p[1])), "pct": float(str(p[2]).replace(",", "."))})
            except ValueError:
                pass
    return out


def parse_brand_field(raw):
    p = clean(raw).split(";")
    return {"name": p[0] if p else "", "id": p[1] if len(p) > 1 else ""}


def fragdb_rows(path):
    rows = load_pipe_csv(path)
    out = []
    for r in rows:
        brand = parse_brand_field(r.get("brand", ""))
        notes_raw = parse_notes_pyramid(r.get("notes_pyramid", ""))
        accords_raw = split_list(r.get("accords", ""))
        rating = r.get("rating", "")
        score = votes = None
        if rating:
            p = rating.split(";")
            score = safe_float(p[0])
            votes = safe_int(p[1]) if len(p) > 1 else None
        out.append({
            "source": "fragdb",
            "id": clean(r.get("pid", "")) or clean(r.get("url", "")),
            "url": clean(r.get("url", "")),
            "name": clean(r.get("name", "")),
            "brand": brand["name"],
            "brand_id": brand["id"],
            "country": clean(r.get("country", "")),
            "year": safe_int(r.get("year")),
            "gender": clean(r.get("gender", "")),
            "collection": clean(r.get("collection", "")),
            "description": clean(r.get("description", "")),
            "rating": {"score": score, "votes": votes},
            "notes_pyramid": notes_raw,
            "all_notes": notes_raw["top"] + notes_raw["middle"] + notes_raw["base"],
            "accords": accords_raw,
            "perfumers": split_list(r.get("perfumers", "")),
            "mainaccords": accords_raw,
        })
    return out


def fragrantica_rows(path):
    rows = load_comma_csv(path)
    out = []
    for r in rows:
        perfumer1 = clean(r.get("Perfumer1", ""))
        perfumer2 = clean(r.get("Perfumer2", ""))
        perfumers = [p for p in [perfumer1, perfumer2] if p]
        perfumers = [p for p in perfumers if p.lower() != "unknown"]
        accords = [clean(r.get(f"mainaccord{i}", "")) for i in range(1, 6)]
        accords = [a for a in accords if a]
        top = split_list(r.get("Top", ""))
        middle = split_list(r.get("Middle", ""))
        base = split_list(r.get("Base", ""))
        out.append({
            "source": "fragrantica_alt",
            "id": clean(r.get("url", "")) or safe_filename(clean(r.get("Perfume", "")) + "-" + clean(r.get("Brand", ""))),
            "url": clean(r.get("url", "")),
            "name": clean(r.get("Perfume", "")),
            "brand": clean(r.get("Brand", "")),
            "brand_id": "",
            "country": clean(r.get("Country", "")),
            "year": safe_int(r.get("Year", "")),
            "gender": clean(r.get("Gender", "")),
            "collection": "",
            "description": "",
            "rating": {
                "score": safe_float(r.get("Rating Value", "")),
                "votes": safe_int(r.get("Rating Count", "")),
            },
            "notes_pyramid": {"top": top, "middle": middle, "base": base},
            "all_notes": top + middle + base,
            "accords": accords,
            "perfumers": perfumers,
            "mainaccords": accords,
        })
    return out


def make_markdown(p):
    n = p.get("notes_pyramid", {})
    r = p.get("rating", {})
    accords = p.get("accords", [])
    perfumers = p.get("perfumers", [])
    return (
        f"---\n"
        f"id: {p.get('id','')}\n"
        f"source: {p.get('source','')}\n"
        f"name: {p.get('name','')}\n"
        f"brand: {p.get('brand','')}\n"
        f"country: {p.get('country','')}\n"
        f"year: {p.get('year','')}\n"
        f"gender: {p.get('gender','')}\n"
        f"---\n\n"
        f"# {p.get('name','')}\n\n"
        f"**Brand:** {p.get('brand','')}  \n"
        f"**Country:** {p.get('country','')}  \n"
        f"**Year:** {p.get('year','N/A')}  \n"
        f"**Gender:** {p.get('gender','N/A')}  \n"
        f"**Source:** {p.get('source','')}  \n"
        f"**URL:** {p.get('url','')}\n\n"
        f"## Notes Pyramid\n\n"
        f"- **Top:** {', '.join(n.get('top', [])) or 'N/A'}\n"
        f"- **Middle:** {', '.join(n.get('middle', [])) or 'N/A'}\n"
        f"- **Base:** {', '.join(n.get('base', [])) or 'N/A'}\n\n"
        f"## Main Accords\n\n"
        f"{chr(10).join(f'- {a}' for a in accords) or 'N/A'}\n\n"
        f"## Rating\n\n"
        f"- **Score:** {r.get('score', 'N/A')}\n"
        f"- **Votes:** {r.get('votes', 'N/A')}\n\n"
        f"## Perfumers\n\n"
        f"{', '.join(perfumers) or 'N/A'}\n\n"
        f"## Description\n\n"
        f"{p.get('description', '') or 'N/A'}\n"
    )


def merge_records(a, b):
    merged = dict(a)
    for k, v in b.items():
        if k not in merged or merged[k] in (None, '', [], {}):
            merged[k] = v
    if not merged.get('all_notes'):
        n = merged.get('notes_pyramid', {})
        merged['all_notes'] = n.get('top', []) + n.get('middle', []) + n.get('base', [])
    return merged


def main(fragdb_csv, fragrantica_csv, output_dir):
    out = Path(output_dir)
    (out / 'perfumes').mkdir(parents=True, exist_ok=True)
    records = fragdb_rows(fragdb_csv) + fragrantica_rows(fragrantica_csv)
    by_key = {}
    for r in records:
        key = r.get('url') or f"{r.get('brand','')}|{r.get('name','')}|{r.get('year','')}"
        by_key[key] = merge_records(by_key[key], r) if key in by_key else r
    merged = list(by_key.values())
    merged.sort(key=lambda x: (x.get('brand',''), x.get('name',''), str(x.get('year',''))))
    with open(out / 'perfumes.jsonl', 'w', encoding='utf-8') as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    for r in merged:
        fname = safe_filename(f"{r.get('brand','')}-{r.get('name','')}-{r.get('year','')}")
        with open(out / 'perfumes' / f'{fname}.md', 'w', encoding='utf-8') as f:
            f.write(make_markdown(r))
    print(f'Wrote {len(merged):,} perfume docs to {out}')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python build_perfume_rag_dataset.py fragdb.csv fragrantica.csv output_dir')
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
