# Docling and GLiNER exploration

This folder contains standalone experiments for one Crop Weather Watch Group
(CWWG) report. They do not import, modify, or otherwise depend on the
production RAG-pipeline Python code in `Crop_Weather_Watch/`.

## What the scripts use

The input is the CWWG report named:

`Minutes of the meeting of CWWG as on 08.06.2026.pdf`

`docling_test.py` first looks for it in `Crop_Weather_Watch/PDFs/`. In this
project the file is currently stored in `Crop_Weather_Watch/data/pdfs/`, which
the script also checks. Only that one PDF is processed.

## Prerequisites

Run the commands below from the repository root (`C:\Web scraping`). The
project virtual environment and dependencies must be available. If required,
install the dependencies first:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

The first GLiNER run downloads the model `urchade/gliner_medium-v2.1` and its
base model from Hugging Face. It can take several minutes and needs internet
access. Later runs reuse the local model cache.

## Run the experiments

Run Docling first. It creates the Markdown input consumed by GLiNER:

```powershell
venv\Scripts\python.exe Webscraping_Methods\docling_test.py
```

Then run GLiNER:

```powershell
venv\Scripts\python.exe Webscraping_Methods\gliner_test.py
```

To use an activated virtual environment instead, run:

```powershell
.\venv\Scripts\Activate.ps1
python Webscraping_Methods\docling_test.py
python Webscraping_Methods\gliner_test.py
```

If PowerShell blocks activation, use the first form with
`venv\Scripts\python.exe`; activation is optional.

## `docling_test.py`

The script converts the PDF with Docling's current `DocumentConverter` API.
It writes these files to `docling_output/`:

| File | Contents |
| --- | --- |
| `cwwg_08_06_2026.md` | Readable Markdown with headings, lists, tables, and image placeholders. |
| `cwwg_08_06_2026.json` | The complete Docling document model, including pages, text items, tables, pictures, hierarchy, and provenance. |
| `cwwg_08_06_2026.txt` | A simple text view of the Markdown export. |

It also prints page, heading, table, image, and total-text statistics. The key
functions are `find_pdf`, `extract_pdf`, `save_markdown`, `save_json`,
`save_text`, `document_statistics`, and `print_summary`.

Docling's JSON is the best file for inspecting document structure: items are
typed (such as text, section headers, tables, and pictures), arranged into a
document hierarchy, and grounded to source pages. Markdown is the more useful
human-readable format and is used as the GLiNER input in this experiment.

## `gliner_test.py`

The script reads `docling_output/cwwg_08_06_2026.md`, splits the long report
into manageable line-boundary chunks, loads GLiNER, and performs zero-shot NER
with these labels:

```text
crop, crop variety, growth stage, disease, pest, insect, state, district,
rainfall, temperature, irrigation, fertilizer, nutrient, weather parameter
```

It writes the following files to `gliner_output/`:

| File | Contents |
| --- | --- |
| `entities.json` | Entity records with `text`, `label`, `score`, and character `start`/`end` offsets in the Markdown input. |
| `entities.csv` | The same entity records in spreadsheet-friendly CSV form. |

The main functions are `read_markdown`, `split_text`, `run_gliner`,
`save_entities`, and `print_summary`. The terminal summary reports the total,
counts by label, and unique values for each label.

### Understanding `entities.csv`

Each CSV row is one GLiNER entity prediction found in the Markdown exported by
Docling. The script splits the report at line boundaries into chunks of at most
3,500 characters, runs `model.predict_entities(chunk, LABELS, threshold=0.45)`
on each chunk, converts the chunk-local positions back to document-level
positions, removes exact duplicates, and writes the remaining records to CSV.

| Column | Meaning and how it is formed | Why it is useful for this objective |
| --- | --- | --- |
| `text` | The exact text span predicted by GLiNER, copied from the Docling Markdown. For example, a crop name or a state name. | This is the agricultural value to inspect, aggregate, filter, or attach as RAG metadata. |
| `label` | One of the labels supplied by this experiment (`crop`, `rainfall`, `state`, etc.). GLiNER selects the label it considers best for the text span. | It makes the extracted value meaningful: `Maharashtra` can be used as a `state` filter, while `rice` can be used as a `crop` filter. |
| `score` | GLiNER's confidence score for the predicted span-and-label pair. It is converted to a float and rounded to six decimal places. Predictions below the configured threshold of `0.45` are not saved. | Use it to review uncertain predictions or set a stricter quality cutoff. It is a model confidence signal, not a calibrated probability or factual guarantee. |
| `start` | Zero-based character offset where `text` begins in the complete Docling Markdown file. GLiNER first returns an offset within its chunk; the script adds that chunk's starting position. | It links the entity back to its exact source context, useful for highlighting it or locating the relevant RAG chunk. |
| `end` | Zero-based, exclusive character offset immediately after `text` in the complete Markdown. In Python terms, `markdown[start:end]` returns the entity text. | Together with `start`, it provides an unambiguous source span even when the same term occurs multiple times. |

The row-creation logic deliberately keeps the original text, label, score, and
source offsets instead of reducing the data to only unique values. This lets
you answer both kinds of questions later: **what agricultural entities occur in
the report?** and **where, how often, and with what model confidence do they
occur?** For a future RAG integration, entity rows can become metadata on
chunks—for example, retrieving only chunks tagged with `crop=rice` and
`state=Punjab`—while `start` and `end` retain traceability to the extracted
document.

GLiNER is zero-shot: the labels are supplied at runtime rather than being a
fixed tag set trained specifically for this report. Treat its scores as a
ranking signal, not a guarantee. Agricultural abbreviations, uncommon crop
varieties, terms spanning table cells, and overlapping categories (for example
`pest` versus `insect`) may need threshold tuning, label refinement, or later
domain fine-tuning.

## Troubleshooting

- **`Markdown input is missing`**: run `docling_test.py` first.
- **Model download is slow**: keep the terminal open while the first GLiNER
  download completes; later runs should be faster.
- **Windows symlink warning from Hugging Face**: this only means model caching
  may use extra disk space. It does not prevent the scripts from running.
- **GLiNER truncation warning**: this indicates an individual line/chunk
  exceeded the model's token limit. The script still completes, but an entity
  near the end of that long input may be missed. Smaller chunks can be explored
  later by lowering `max_characters` in `split_text`.
