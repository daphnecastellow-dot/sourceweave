#!/usr/bin/env python3
"""Sourceweave: trace where details enter a source lineage.

Standard-library only. Data is stored as plain JSON.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

FORMAT = "sourceweave/0.1"
SOURCE_KINDS = (
    "primary",
    "contemporary-report",
    "later-retelling",
    "reference",
    "analysis",
    "other",
)
RELATIONS = ("derived-from", "quotes", "cites", "summarizes", "responds-to", "unknown")
OBSERVATIONS = ("present", "absent", "disputed", "unclear")


class SourceweaveError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_project(title: str) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise SourceweaveError("title cannot be empty")
    return {
        "format": FORMAT,
        "title": title,
        "created_at": now_utc(),
        "sources": [],
        "details": [],
        "relations": [],
        "observations": [],
    }


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SourceweaveError("project must be a JSON object")
    if data.get("format") != FORMAT:
        raise SourceweaveError(f"unsupported format: {data.get('format')!r}")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise SourceweaveError("project requires a title")
    for key in ("sources", "details", "relations", "observations"):
        if not isinstance(data.get(key), list):
            raise SourceweaveError(f"project requires a {key} list")

    source_ids = set()
    for source in data["sources"]:
        sid = source.get("id")
        if not isinstance(sid, str) or not sid:
            raise SourceweaveError("every source requires an id")
        if sid in source_ids:
            raise SourceweaveError(f"duplicate source id: {sid}")
        source_ids.add(sid)
        if source.get("kind") not in SOURCE_KINDS:
            raise SourceweaveError(f"{sid}: invalid source kind")
        if not isinstance(source.get("label"), str) or not source["label"].strip():
            raise SourceweaveError(f"{sid}: source label cannot be empty")
        date = source.get("date")
        if date and not _valid_date(date):
            raise SourceweaveError(f"{sid}: date must be YYYY, YYYY-MM, or YYYY-MM-DD")

    detail_ids = set()
    for detail in data["details"]:
        did = detail.get("id")
        if not isinstance(did, str) or not did:
            raise SourceweaveError("every detail requires an id")
        if did in detail_ids:
            raise SourceweaveError(f"duplicate detail id: {did}")
        detail_ids.add(did)
        if not isinstance(detail.get("text"), str) or not detail["text"].strip():
            raise SourceweaveError(f"{did}: detail text cannot be empty")

    for rel in data["relations"]:
        if rel.get("from") not in source_ids or rel.get("to") not in source_ids:
            raise SourceweaveError("relation references an unknown source")
        if rel.get("relation") not in RELATIONS:
            raise SourceweaveError("invalid relation type")
        if rel.get("from") == rel.get("to"):
            raise SourceweaveError("a source cannot relate to itself")

    seen_obs = set()
    for obs in data["observations"]:
        key = (obs.get("source"), obs.get("detail"))
        if key in seen_obs:
            raise SourceweaveError(f"duplicate observation for {key[0]} and {key[1]}")
        seen_obs.add(key)
        if obs.get("source") not in source_ids:
            raise SourceweaveError("observation references an unknown source")
        if obs.get("detail") not in detail_ids:
            raise SourceweaveError("observation references an unknown detail")
        if obs.get("state") not in OBSERVATIONS:
            raise SourceweaveError("invalid observation state")


def _valid_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}", value):
        return True
    if re.fullmatch(r"\d{4}-\d{2}", value):
        try:
            dt.date.fromisoformat(value + "-01")
            return True
        except ValueError:
            return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            dt.date.fromisoformat(value)
            return True
        except ValueError:
            return False
    return False


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise SourceweaveError(f"project not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceweaveError(f"invalid JSON in {p}: {exc}") from exc
    validate(data)
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
    highest = 0
    for item in items:
        value = item.get("id", "")
        if value.startswith(prefix) and value[len(prefix):].isdigit():
            highest = max(highest, int(value[len(prefix):]))
    return f"{prefix}{highest + 1:03d}"


def add_source(data: dict[str, Any], label: str, kind: str, date: str | None = None,
               url: str | None = None, note: str | None = None) -> str:
    if kind not in SOURCE_KINDS:
        raise SourceweaveError(f"invalid source kind: {kind}")
    if date and not _valid_date(date):
        raise SourceweaveError("date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    label = label.strip()
    if not label:
        raise SourceweaveError("source label cannot be empty")
    sid = _next_id(data["sources"], "S")
    data["sources"].append({
        "id": sid,
        "label": label,
        "kind": kind,
        "date": date or "",
        "url": url or "",
        "note": note or "",
    })
    return sid


def add_detail(data: dict[str, Any], text: str, note: str | None = None) -> str:
    text = text.strip()
    if not text:
        raise SourceweaveError("detail text cannot be empty")
    did = _next_id(data["details"], "D")
    data["details"].append({"id": did, "text": text, "note": note or ""})
    return did


def find_source(data: dict[str, Any], sid: str) -> dict[str, Any]:
    for source in data["sources"]:
        if source["id"] == sid:
            return source
    raise SourceweaveError(f"source not found: {sid}")


def find_detail(data: dict[str, Any], did: str) -> dict[str, Any]:
    for detail in data["details"]:
        if detail["id"] == did:
            return detail
    raise SourceweaveError(f"detail not found: {did}")


def add_relation(data: dict[str, Any], from_id: str, to_id: str, relation: str,
                 note: str | None = None) -> None:
    find_source(data, from_id)
    find_source(data, to_id)
    if from_id == to_id:
        raise SourceweaveError("a source cannot relate to itself")
    if relation not in RELATIONS:
        raise SourceweaveError(f"invalid relation: {relation}")
    candidate = (from_id, to_id, relation)
    if any((r["from"], r["to"], r["relation"]) == candidate for r in data["relations"]):
        raise SourceweaveError("that relation already exists")
    data["relations"].append({"from": from_id, "to": to_id, "relation": relation, "note": note or ""})


def observe(data: dict[str, Any], source_id: str, detail_id: str, state: str,
            note: str | None = None) -> None:
    find_source(data, source_id)
    find_detail(data, detail_id)
    if state not in OBSERVATIONS:
        raise SourceweaveError(f"invalid observation state: {state}")
    for obs in data["observations"]:
        if obs["source"] == source_id and obs["detail"] == detail_id:
            obs["state"] = state
            obs["note"] = note or ""
            return
    data["observations"].append({
        "source": source_id,
        "detail": detail_id,
        "state": state,
        "note": note or "",
    })


def _date_key(source: dict[str, Any]) -> tuple[int, int, int, str]:
    value = source.get("date") or ""
    if not value:
        return (9999, 12, 31, source["id"])
    parts = [int(p) for p in value.split("-")]
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return (year, month, day, source["id"])


def first_appearance(data: dict[str, Any], detail_id: str) -> dict[str, Any] | None:
    find_detail(data, detail_id)
    present_ids = {o["source"] for o in data["observations"] if o["detail"] == detail_id and o["state"] == "present"}
    if not present_ids:
        return None
    candidates = [s for s in data["sources"] if s["id"] in present_ids]
    dated = [s for s in candidates if s.get("date")]
    pool = dated if dated else candidates
    return min(pool, key=_date_key)


def detail_matrix(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    matrix: dict[str, dict[str, str]] = {d["id"]: {} for d in data["details"]}
    for obs in data["observations"]:
        matrix[obs["detail"]][obs["source"]] = obs["state"]
    return matrix


def render_markdown(data: dict[str, Any]) -> str:
    matrix = detail_matrix(data)
    lines = [f"# {data['title']}", "", f"_Sourceweave format: `{FORMAT}`_", ""]
    lines += ["## Sources", ""]
    if not data["sources"]:
        lines += ["_No sources yet._", ""]
    else:
        for source in sorted(data["sources"], key=_date_key):
            date = source.get("date") or "undated"
            lines.append(f"- **{source['id']} · {date} · {source['kind']}**: {source['label']}")
            if source.get("url"):
                lines.append(f"  - {source['url']}")
            if source.get("note"):
                lines.append(f"  - Note: {source['note']}")
        lines.append("")

    lines += ["## Details", ""]
    if not data["details"]:
        lines += ["_No tracked details yet._", ""]
    else:
        for detail in data["details"]:
            first = first_appearance(data, detail["id"])
            if first:
                first_text = f"{first['id']} · {first.get('date') or 'undated'} · {first['label']}"
            else:
                first_text = "no recorded present observation"
            lines += [f"### {detail['id']} · {detail['text']}", "", f"**First recorded appearance:** {first_text}", ""]
            if detail.get("note"):
                lines += [f"**Note:** {detail['note']}", ""]
            for source in sorted(data["sources"], key=_date_key):
                state = matrix[detail["id"]].get(source["id"], "unrecorded")
                lines.append(f"- {source['id']} · {source['label']}: **{state}**")
            lines.append("")

    lines += ["## Source lineage", ""]
    if not data["relations"]:
        lines += ["_No source-to-source relations recorded._", ""]
    else:
        for rel in data["relations"]:
            lines.append(f"- {rel['from']} → {rel['to']} · **{rel['relation']}**" + (f" · {rel['note']}" if rel.get("note") else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _mermaid_label(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")


def render_mermaid(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for source in sorted(data["sources"], key=_date_key):
        date = source.get("date") or "undated"
        label = _mermaid_label(f"{source['id']} · {date} · {source['label']}")
        lines.append(f'  {source["id"]}["{label}"]')
    arrow_labels = {
        "derived-from": "derived from",
        "quotes": "quotes",
        "cites": "cites",
        "summarizes": "summarizes",
        "responds-to": "responds to",
        "unknown": "relation unclear",
    }
    for rel in data["relations"]:
        lines.append(f"  {rel['from']} -->|{arrow_labels[rel['relation']]}| {rel['to']}")
    return "\n".join(lines) + "\n"


def summary(data: dict[str, Any]) -> str:
    return (
        f"{data['title']}: {len(data['sources'])} source(s), "
        f"{len(data['details'])} detail(s), {len(data['relations'])} relation(s)"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sourceweave", description="Trace where details enter a source lineage.")
    sub = p.add_subparsers(dest="command", required=True)

    n = sub.add_parser("new", help="create a new project")
    n.add_argument("file")
    n.add_argument("--title", required=True)

    s = sub.add_parser("source", help="add a source")
    s.add_argument("file")
    s.add_argument("label")
    s.add_argument("--kind", choices=SOURCE_KINDS, default="other")
    s.add_argument("--date")
    s.add_argument("--url")
    s.add_argument("--note")

    d = sub.add_parser("detail", help="add a tracked detail")
    d.add_argument("file")
    d.add_argument("text")
    d.add_argument("--note")

    r = sub.add_parser("relate", help="record a source-to-source relationship")
    r.add_argument("file")
    r.add_argument("from_id")
    r.add_argument("to_id")
    r.add_argument("relation", choices=RELATIONS)
    r.add_argument("--note")

    o = sub.add_parser("observe", help="record whether a detail appears in a source")
    o.add_argument("file")
    o.add_argument("source_id")
    o.add_argument("detail_id")
    o.add_argument("state", choices=OBSERVATIONS)
    o.add_argument("--note")

    f = sub.add_parser("first", help="show first recorded appearance of a detail")
    f.add_argument("file")
    f.add_argument("detail_id")

    rm = sub.add_parser("render", help="render a Markdown report")
    rm.add_argument("file")
    rm.add_argument("-o", "--output")

    mm = sub.add_parser("mermaid", help="render a Mermaid source-lineage diagram")
    mm.add_argument("file")
    mm.add_argument("-o", "--output")

    sh = sub.add_parser("show", help="show project summary")
    sh.add_argument("file")

    ch = sub.add_parser("check", help="validate a project file")
    ch.add_argument("file")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "new":
            path = Path(args.file)
            if path.exists():
                raise SourceweaveError(f"refusing to overwrite existing file: {path}")
            save(path, new_project(args.title))
            print(f"created {path}")
            return 0

        data = load(args.file)
        if args.command == "source":
            sid = add_source(data, args.label, args.kind, args.date, args.url, args.note)
            save(args.file, data)
            print(sid)
        elif args.command == "detail":
            did = add_detail(data, args.text, args.note)
            save(args.file, data)
            print(did)
        elif args.command == "relate":
            add_relation(data, args.from_id, args.to_id, args.relation, args.note)
            save(args.file, data)
            print(f"{args.from_id}->{args.to_id}")
        elif args.command == "observe":
            observe(data, args.source_id, args.detail_id, args.state, args.note)
            save(args.file, data)
            print(f"{args.source_id}:{args.detail_id}={args.state}")
        elif args.command == "first":
            source = first_appearance(data, args.detail_id)
            if source is None:
                print("none")
            else:
                print(f"{source['id']} [{source.get('date') or 'undated'}] {source['label']}")
        elif args.command == "render":
            output = render_markdown(data)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(args.output)
            else:
                print(output, end="")
        elif args.command == "mermaid":
            output = render_mermaid(data)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(args.output)
            else:
                print(output, end="")
        elif args.command == "show":
            print(summary(data))
        elif args.command == "check":
            print(f"ok: {args.file}")
        return 0
    except SourceweaveError as exc:
        print(f"sourceweave: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
