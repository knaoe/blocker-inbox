# /// script
# requires-python = ">=3.9"
# dependencies = ["jsonschema[format-nongpl]>=4.18"]
# ///
"""Validate Blocker Inbox JSON against the schemas.

    uv run scripts/validate.py                  # examples/ and the demo data inside inbox.html
    uv run scripts/validate.py my-item.json     # your own files (item, answer or config is guessed)

Besides the JSON Schema, it checks what a schema cannot express: option keys are unique,
recommend.key names one of the options, an item the agent owns itself (owner == asker)
has a recommendation and a due time and no stakes, and received matches the current rev.
"""
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
VALIDATORS = {
    kind: Draft202012Validator(json.loads((ROOT / "schema" / f"{kind}.schema.json").read_text()), format_checker=FormatChecker())
    for kind in ("item", "answer", "config")
}


def kind_of(doc):
    if "item_id" in doc:
        return "answer"
    if "owners" in doc or "self" in doc or set(doc) <= {"v", "locale"}:
        return "config"
    return "item"


def check(label, doc, kind=None):
    kind = kind or kind_of(doc)
    problems = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in VALIDATORS[kind].iter_errors(doc)]
    if kind == "item":
        keys = [o.get("key") for o in doc.get("options", []) if isinstance(o, dict)]
        if len(keys) != len(set(keys)):
            problems.append("options: keys must be unique")
        key = (doc.get("recommend") or {}).get("key")
        if key is not None and key not in keys:
            problems.append(f"recommend.key {key!r} is not one of the option keys {keys}")
        if doc.get("owner") and doc.get("owner") == doc.get("asker"):
            # owner == asker: the agent goes ahead with the recommendation at `due` unless someone answers.
            if doc.get("stakes"):
                problems.append("owner equals asker, so stakes must be empty: a marked item needs a person to decide")
            if not doc.get("recommend"):
                problems.append("owner equals asker: add recommend, the option you will go ahead with")
            if not doc.get("due"):
                problems.append("owner equals asker: add due, the time you will go ahead")
        received = doc.get("received")
        if isinstance(received, dict) and received.get("item_rev") not in (None, doc.get("rev")):
            problems.append("received.item_rev differs from rev: remove received whenever you add 1 to rev")
    for p in problems:
        print(f"FAIL {label} [{kind}] {p}")
    if not problems:
        print(f"ok   {label} [{kind}]")
    return not problems


def main(paths):
    ok = True
    if paths:
        for p in paths:
            ok &= check(p, json.loads(Path(p).read_text()))
    else:
        for p in sorted((ROOT / "examples").glob("*.json")):
            ok &= check(str(p.relative_to(ROOT)), json.loads(p.read_text()))
        html = (ROOT / "inbox.html").read_text()
        demo = json.loads(re.search(r'<script type="application/json" id="demo-data">(.*?)</script>', html, re.S).group(1))
        for lang, cfg in demo["config"].items():
            ok &= check(f"demo config {lang}", cfg, "config")
        for lang, items in demo["items"].items():
            for it in items:
                ok &= check(f"demo item {lang}/{it.get('id')}", it, "item")
        for a in demo["answers"]:
            ok &= check(f"demo answer {a.get('item_id')}", a, "answer")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
