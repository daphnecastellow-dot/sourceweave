# Sourceweave

**Version:** 0.1  
**Status:** experimental

Sourceweave traces **where details enter a source lineage**.

It is designed for research problems where a story, claim, quotation, or anecdote changes as it moves through records, newspapers, books, websites, videos, and later retellings.

A source graph might look like:

```text
primary record → newspaper → later book → website → modern retelling
```

Sourceweave records both the source-to-source lineage and whether a specific detail is **present, absent, disputed, or unclear** in each source.

Its most important question is:

> Among the sources currently recorded, where does this detail first appear?

That is deliberately narrower than claiming to know the detail's true historical origin.

## What it stores

A Sourceweave project contains:

- sources with dates, types, notes, and optional URLs
- tracked details
- source-to-source relationships
- observations connecting details to sources
- first recorded appearance calculations

Supported source kinds:

- `primary`
- `contemporary-report`
- `later-retelling`
- `reference`
- `analysis`
- `other`

Supported source relations:

- `derived-from`
- `quotes`
- `cites`
- `summarizes`
- `responds-to`
- `unknown`

Detail observations:

- `present`
- `absent`
- `disputed`
- `unclear`

## Quick start

```bash
python sourceweave.py new case.json --title "Source lineage"

python sourceweave.py source case.json "Archive record" \
  --kind primary --date 1900-12-20

python sourceweave.py source case.json "Later book" \
  --kind later-retelling --date 1987

python sourceweave.py detail case.json \
  "An overturned chair is mentioned."

python sourceweave.py observe case.json S001 D001 absent
python sourceweave.py observe case.json S002 D001 present

python sourceweave.py relate case.json S002 S001 derived-from

python sourceweave.py first case.json D001
python sourceweave.py render case.json -o report.md
python sourceweave.py mermaid case.json -o lineage.mmd
```

## Output

Sourceweave can produce:

- plain JSON for durable storage
- Markdown research reports
- Mermaid source-lineage diagrams

The Mermaid output can be rendered by GitHub and many Markdown tools.

## Example

The fictional demo in [`examples/demo.json`](examples/demo.json) follows four sources from 1904 to 2025.

One detail is present from the earliest source. Another detail, a wet footprint inside a locked tower, is explicitly absent from the two early sources and first appears in the 1978 retelling within the recorded source set.

See:

- [`examples/demo.md`](examples/demo.md)
- [`examples/demo.mmd`](examples/demo.mmd)

## What Sourceweave does not claim

Sourceweave does not automatically decide whether a source is true.

It does not equate an old source with an accurate source.

It does not infer that an absent detail was impossible.

It does not claim that the earliest recorded source in a project is the historical origin.

It makes the **recorded evidence structure** inspectable.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development of the project by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Working principle

A strange detail should not become ancient merely because it survived long enough to be repeated.

Sourceweave keeps track of where it entered the weave.
