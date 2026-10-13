# Blocker Inbox

A one-page inbox where one person clears the decisions, approvals and questions that a fleet of AI agents has queued. It runs as a [claude.ai Artifact](https://claude.ai): agents write items into the artifact's shared store, the page shows each one as a card, and every answer goes back into the same store as structured JSON that the agent reads.

<p>
  <img src="docs/screenshots/phone-light.png" alt="Phone view: a one-line summary, then your own decisions as cards, the recommended option filled in blue" width="300">
  <img src="docs/screenshots/phone-dark.png" alt="The same view in dark mode, with a confirmation step on an item marked as irreversible" width="300">
</p>

> **日本語の概要** — AI エージェントがためた「判断待ち」（決めてほしいこと・承認・質問）を、1人がスマホで片づけるためのページのテンプレートです。1件1カードで、何が止まっているか、選択肢とその結果、おすすめと理由、待ち時間、取り消せない・外部に出る・お金がかかる、の印を並べます。ほとんどの項目は1タップで返せて、回答はエージェントが読める JSON として保存されます。画面の文言は日本語と英語があり、ほかの言語も足せます。

## What the page does

- **One card per item.** What is stopped, why it matters, 2 to 4 options with what happens if each is picked, the asker's recommendation with its reason, evidence links, how long it has waited, and visible markers for *irreversible*, *external* and *money*.
- **Your items first.** Items waiting 48 hours or more move to the top as stuck; after 24 hours they show "re-ask". Everyone else's items are compact rows grouped by owner, so you can see what is stuck elsewhere and answer for them.
- **One tap answers.** An undo button stays up for 8 seconds. Items with a marker take a second tap. "Not mine" hands the item to another owner, and "Reply with a note" answers in words.
- **Unmarked items can be accepted together** after one review list, so routine approvals do not eat attention that marked items need.
- **Answered and finished items fold away**, and stay visible until the agent closes them, so you can see that an answer was picked up.

## How it works

```
agent ── set ──▶ items/<id>      one document per question (agents write)
page  ── set ──▶ answers/<id>    same id, latest answer wins (people write)
agent ◀─ get ─── answers/<id>    act, then mark the item done
                 config/inbox    optional: owner labels, whose items are "yours"
```

The page never edits items and agents never edit answers, so the two writers do not collide.

## Schema (v1)

The JSON Schemas are in [`schema/`](schema). Validate your own documents with `uv run scripts/validate.py my-item.json`.

### Item — `items/<id>` (written by agents)

- `v` — always `1`.
- `id` — equal to the document id. Letters, digits and `_ . ~ : @ + -`.
- `rev` — starts at `1`. Add 1 whenever the question changes. An answer only counts for the `rev` it was given for, so a person never answers a question you have since rewritten.
- `status` — `open` until you have acted, then `done`.
- `title` — the decision, phrased as a question.
- `blocked` — what is stopped, as a short noun phrase. Optional.
- `why` — why it matters, in one line.
- `owner` — who should decide, as an owner key (for example `lead`, `ux`, `repo`, `agent`).
- `asker` — the agent's name.
- `options` — 2 to 4 of `{ key, label, consequence }`. `consequence` says in plain words what happens if this option is picked.
- `recommend` — `{ key, reason }`. Optional, but cards without it are slower to answer.
- `stakes` — any of `irreversible`, `external`, `money`. Each shows as a marker and makes the page ask for a second tap.
- `blocking` — `true` if your work is stopped until the answer arrives (default), `false` if you keep working.
- `evidence` — up to 5 `{ label, url }` links (http or https).
- `asked_at`, `reasked_at`, `due` — ISO 8601 times with an offset.
- `if_no_answer` — `{ at, key }`: if nobody answers by `at`, you will go ahead with option `key`. The card says so. Do not use it on items with stakes.
- `outcome`, `done_at` — set when you close the item.
- `demo` — `true` marks a made-up example. `meta` — free-form data for your own use.

See [`examples/item.json`](examples/item.json).

### Answer — `answers/<item id>` (written by the page)

- `item_id`, `item_rev` — which question, and which version of it, this answers.
- `kind` — `choose` (see `key`), `reply` (see `note`) or `reassign` (see `reassign_to`).
- `key` — the picked option, for `choose`.
- `note` — free text. Required for `reply`, optional otherwise.
- `reassign_to` — the owner key who should decide instead, or `null` for "I don't know".
- `answered_at`, `answered_by` (an opaque claude.ai user id, or `null`), `via` (`card` or `batch`).

See [`examples/answer.json`](examples/answer.json).

### Config — `config/inbox` (optional)

`{ v, self, owners: [{ key, label }], locale }`. `owners` sets labels and group order. `self` is the owner key whose items count as "yours"; each viewer can change it on the page. See [`examples/config.json`](examples/config.json).

## For agents: post, read, close

1. **Post** the item with `rev: 1`, `status: "open"` and `asked_at` set to now.
2. **Read** `answers/<id>`. Use it only if `item_rev` equals your current `rev`.
3. **Act** on it:
   - `choose` → do option `key` (and read `note` if there is one).
   - `reply` → read `note`. Either act on it, or update the item with what was asked and add 1 to `rev`, which puts the card back in front of the person.
   - `reassign` → set `owner` to `reassign_to` (or find the right person when it is `null`) and add 1 to `rev`.
4. **Close** with `status: "done"`, a one-line `outcome` and `done_at`.
5. **Waiting too long?** After 24 hours without an answer, re-ask once in your usual channel and set `reasked_at`. After 48 hours the page shows the item as stuck at the top.

A person can withdraw or change an answer until you close the item. Read the answer right before you act, especially on items with stakes, and treat a missing answer document as "no answer".

### Claude Code

Claude Code reaches the store with its `ArtifactData` tool. Pass the artifact's URL in every call.

```jsonc
// post
{ "action": "set", "url": "https://claude.ai/…", "collection": "items", "doc_id": "db-migration-tonight", "data": { /* the item */ } }

// read one answer, or every answer at once
{ "action": "get", "url": "https://claude.ai/…", "collection": "answers", "doc_id": "db-migration-tonight" }
{ "action": "list", "url": "https://claude.ai/…", "collection": "answers" }

// close (pass the version you last read)
{ "action": "update", "url": "https://claude.ai/…", "collection": "items", "doc_id": "db-migration-tonight",
  "data": { "status": "done", "outcome": "Migrated at 23:00, 22 minutes of slow search.", "done_at": "2026-10-14T23:40:00+09:00" },
  "if_version": 2 }
```

### Other agents (Codex, OpenClaw, scripts)

Today only Claude Code's `ArtifactData` tool can reach a claude.ai Artifact's store. Other agents write the same JSON (check it with `scripts/validate.py`) and hand it to a Claude Code session that posts it and passes the answer back. If you host the page yourself, replace the `liveStore` function in `inbox.html` (about 15 lines) with one that talks to your own backend; the rest of the page does not change.

## Publish it as a Claude artifact

1. In Claude Code, ask Claude to publish `inbox.html` as an Artifact with these capabilities:

   ```json
   { "db": { "rules": [ { "path": "items", "write": "admin" }, { "path": "config", "write": "admin" } ] }, "user": {} }
   ```

   Only editors, and agents acting as the owner through `ArtifactData`, can then write items and config. Anyone who can use the page can write answers.
2. Write `config/inbox` with your owner keys and set `self` to your own key.
3. Optional: seed the example items from the `demo-data` block in `inbox.html` (they carry `demo: true` and show an "Example" chip). Delete them when real items arrive.
4. Give your agents the artifact URL and this README.

Artifacts are private until you share them. Share with people who answer for an owner key, and give them at least Contributor access so they can answer.

## Try it locally

`scripts/preview.sh` writes `preview/index.html`. Opened outside claude.ai, the page has no store, so it runs in demo mode with the made-up example items, and answers last until you close the page.

## Change the language or the rules

- All UI text is in the `STRINGS` object in `inbox.html` (Japanese and English). Copy a block and translate it to add a language; pick it with `SETTINGS.locale` or `locale` in `config/inbox`.
- `SETTINGS` also holds the 24-hour and 48-hour thresholds, how long finished items stay, and the undo window.

## Design rules

These come from looking at where approval queues fail. The main failure is approval fatigue: people stop reading and start rubber-stamping.

- **Show only what needs a human.** Everything else folds away.
- **Every item has an owner and a waiting-since**, and stale items look stale: "re-ask" after 24 hours, "stuck" and on top after 48.
- **Put the recommendation and the consequence of each option in plain words**, on the card, next to the button.
- **Make the stakes visible.** Irreversible, external and money get a marker, and a second tap. Everything else is one tap with undo.
- **"Not mine" is an answer**, so a wrongly routed item moves on instead of sitting.
- **A small fixed set of answers that returns structured data**: choose, reply, reassign. The idea of a fixed answer set comes from LangChain's [Agent Inbox](https://github.com/langchain-ai/agent-inbox) (now archived); no code is reused.
- **No tables, plain language, jargon explained.** The page is built for a phone first.

## License

[MIT](LICENSE)
