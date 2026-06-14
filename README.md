# Perfume Assistant

A local perfume recommendation assistant that uses semantic search over a perfume dataset and a local LM Studio model to rank fragrances for a query.

## Overview

Perfume Assistant is a lightweight Python project that turns a text prompt like `winter coffee vanilla` into ranked perfume recommendations with short explanations. It uses ChromaDB for retrieval and a local model served by LM Studio for final ranking and response generation.

## Features

- Semantic search over a perfume dataset.
- Ranked recommendations with short explanations.
- Local inference through LM Studio.
- Simple command-line interface.
- Easy to extend with filters, new prompts, or JSON output.

## Example queries

- `winter coffee vanilla`
- `fresh citrus clean`
- `sweet vanilla dessert`
- `dark woody smoky`
- `rose musky elegant`

## Requirements

- Python 3.10 or newer.
- LM Studio running locally.
- A local model loaded in LM Studio.
- A ChromaDB index available in `chroma_db`.

## Project structure

```text
perfume-assistant/
├─ perfume_assistant.py
├─ build_chromadb.py
├─ fra_perfumes.csv
├─ chroma_db/
├─ README.md
├─ requirements.txt
├─ .gitignore
└─ LICENSE
```

## Setup

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/yourusername/perfume-assistant.git
cd perfume-assistant
python -m venv .venv

# IMPORTANT: Generate the chroma_db index first
# Replace <path_to_dataset> with your actual .jsonl dataset path
python build_chromadb.py build <path_to_dataset>
```

Activate it:

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Make sure LM Studio is running at:

```text
http://127.0.0.1:1234/v1
```

## Usage

Run the assistant with the default query:

```bash
python perfume_assistant.py
```

Run it with your own query:

```bash
python perfume_assistant.py winter coffee vanilla
```

More examples:

```bash
python perfume_assistant.py fresh citrus clean
python perfume_assistant.py sweet vanilla dessert
python perfume_assistant.py dark woody smoky
python perfume_assistant.py rose musky elegant
```

## Example output

```text
1. Chestnut-Cream-French-Vanilla by Jousset-Parfums
A rich, warm fragrance with coffee and vanilla notes that fits a cozy winter profile.

2. Vanilla-Milk by Ellis-Brooklyn
A soft creamy vanilla option that feels smooth, warm, and comforting.
```

## How it works

1. The script reads your query from the command line.
2. It searches the ChromaDB index for matching perfumes.
3. It formats the retrieved results into a compact context block.
4. It sends the prompt to the local LM Studio API.
5. It prints the final ranked recommendation list.

## Configuration

Key settings in `perfume_assistant.py`:

- `BASE_URL` — LM Studio API endpoint.
- `MODEL` — model name loaded in LM Studio.
- `top_k` — number of retrieved results.
- `max_tokens` — maximum response length.

## Future improvements

- Add command-line flags for top-k and output format.
- Add filters for season, sweetness, and note families.
- Export results as JSON or CSV.
- Add a small web UI.
- Improve metadata parsing and ranking.

## Credits

The dataset used for this project is derived from the [Fragrantica.com Fragrance Dataset](https://www.kaggle.com/datasets/olgagmiufana1/fragrantica-com-fragrance-dataset) available on Kaggle.

Built as a portfolio project for experimenting with retrieval-augmented generation, local LLMs, and fragrance recommendation.

## License

MIT License.
