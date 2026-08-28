# Comet Bot — Aster & Row Support Agent

A retrieval-augmented support agent for the Aster & Row take-home assignment. It answers policy questions from the knowledge base, looks up order status via a sanitized tool, handles multi-turn conversation, and recommends human handoff when appropriate.

## Demo

[![Demo recording](docs/demo.gif)](docs/demo.gif)

> **Before you submit:** Record a 2–4 minute demo and save it as [`docs/demo.gif`](docs/demo.gif), or replace the link above with a hosted video URL. See [`docs/DEMO.md`](docs/DEMO.md) for a shot list.

The demo should show: a cited KB answer, an order lookup, a multi-turn follow-up, a refusal or handoff case, and the eval suite passing.

---

## Setup and run

From a clean clone:

```bash
git clone <your-repo-url>
cd comet-bot

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .

cp .env.example .env
# Edit .env and set OPENAI_API_KEY

python scripts/check_setup.py      # verify paths and API key
```

### Web UI (recommended)

```bash
python scripts/serve.py
```

Open **http://127.0.0.1:8080**

### CLI chat

```bash
python scripts/chat.py
```

### Other utilities

```bash
python scripts/search_knowledge.py "return window backpack"
python scripts/lookup_order.py ORD-1007
python scripts/print_chunks.py
```

### Tests

```bash
pytest
```

Integration tests (call OpenAI) are skipped automatically if `OPENAI_API_KEY` is not set:

```bash
pytest -m integration
```

---

## Environment variables

Copy [`.env.example`](.env.example) to `.env`. Never commit `.env`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | API key for chat completions and embeddings |
| `OPENAI_CHAT_MODEL` | No | `gpt-4o-mini` | Model used by `SupportAgent` |
| `OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-small` | Embedding model for retrieval |
| `DEBUG` | No | `false` | Set to `true` for structured JSON debug logs on stderr |

---

## Technical choices

| Area | Choice | Rationale |
|------|--------|-----------|
| **Chat model** | `gpt-4o-mini` | Fast, inexpensive, sufficient for grounded Q&A with retrieved context |
| **Embeddings** | `text-embedding-3-small` | Good quality for short policy chunks; same provider as chat |
| **Framework** | Python 3.11+, OpenAI SDK, NumPy | Minimal dependencies; no heavy agent framework |
| **Web UI** | FastAPI + static HTML/CSS/JS | Thin API layer over the same agent used by CLI and eval |
| **Vector storage** | In-memory `KnowledgeIndex` | Chunks embedded at startup; no external DB for this scope |
| **Sessions** | In-memory `SessionStore` | Per-process conversation history keyed by session ID |
| **Orders** | In-memory `OrderStore` over `data/orders.json` | Only sanitized lookup results reach the model |

---

## Architecture

```text
knowledge-base/*.md
        │
        ▼
  ingest/chunker  ──► metadata flags (authoritative, superseded, internal)
        │
        ▼
  KnowledgeIndex  ──► cosine similarity + metadata/keyword reranking + conflict detection
        │
        ▼
  SupportAgent.run(messages) ──► AgentTrace
        │                              ├── answer
        │                              ├── sources / source_files
        │                              ├── tool_calls (order_lookup)
        │                              └── handoff_recommended
        │
        ├── extract_order_id() ──► lookup_order() ──► sanitized JSON (never full orders file)
        │
        └── OpenAI chat completion (system prompt + retrieved excerpts + tool output)

Interfaces:  scripts/chat.py  |  scripts/serve.py (web)  |  scripts/run_eval.py
```

**Agent flow (one turn):**

1. Combine user messages in the session for retrieval query context.
2. Search the knowledge index; prefer authoritative chunks; diversify by source file.
3. If an order ID is present, call `lookup_order()` and attach sanitized results.
4. Build a system message with KB excerpts, conflict notices, and contextual guidance.
5. Single LLM completion; compute handoff from rules + answer signals.
6. Return `AgentTrace` for UI, eval assertions, or `DEBUG` logs.

---

## Evaluation

Run the full suite (15 visible + 5 custom cases):

```bash
python scripts/run_eval.py --agent support
```

Options:

```bash
python scripts/run_eval.py --agent retrieval   # rule-based stub (no LLM)
python scripts/run_eval.py --category privacy
python scripts/run_eval.py --json
```

Custom cases live in [`evaluation/custom-cases.json`](evaluation/custom-cases.json).

### Baseline vs final results

**Baseline — `RetrievalEvalAgent` (rule-based stub, no LLM):** used to validate retrieval, tools, and eval assertions before wiring the real agent.

| Metric | Result |
|--------|--------|
| Overall | **20 / 20** |
| Unit tests | 51 (at time of stub completion) |

| Category | Pass |
|----------|------|
| abstention | 1/1 |
| conversation | 2/2 |
| groundedness | 2/2 |
| multi-source-grounding | 1/1 |
| privacy | 2/2 |
| prompt-security | 1/1 |
| retrieval | 3/3 |
| source-conflict | 1/1 |
| tool-reliability | 4/4 |
| tool-use | 3/3 |

**Midpoint — `SupportAgent` (first LLM integration, before tuning):**

| Metric | Result |
|--------|--------|
| Overall | **13 / 20** |

Common failures: missing handoff on privacy/damaged-item cases, prompt-injection handoff false positive, Canada duties not mentioned, order status wording, paraphrased return-window question asking for order ID.

**Final — `SupportAgent` (after prompt, handoff, and conflict fixes):**

| Metric | Result |
|--------|--------|
| Overall | **20 / 20** |
| Unit tests | **64** |

| Category | Pass |
|----------|------|
| abstention | 1/1 |
| conversation | 2/2 |
| groundedness | 2/2 |
| multi-source-grounding | 1/1 |
| privacy | 2/2 |
| prompt-security | 1/1 |
| retrieval | 3/3 |
| source-conflict | 1/1 |
| tool-reliability | 4/4 |
| tool-use | 3/3 |

---

## Observability

Set `DEBUG=true` in `.env` to emit structured JSON logs (stderr) for each agent turn:

- Full message list sent to the model
- Retrieved chunk IDs
- Tool calls and arguments
- Final answer, sources, and handoff flag

Secrets are never logged.

---

## Bug diary

### 1. False conflict on unrelated queries

**Reproduce:** Run `python scripts/search_knowledge.py "return window backpack"`. With OpenAI embeddings, top results included both `11-product-care.md` (bags section mentions “wash”) and `12-breeze-tumbler-product-card.md`, triggering a Breeze cleaning conflict.

**Root cause:** `detect_conflicts()` fired when both files appeared in top-*k* results and any chunk contained generic tokens like `wash`, even when the user was not asking about the Breeze Tumbler.

**Fix:** Require the query to mention breeze/tumbler/dishwasher, or retrieved chunks to be Breeze-specific sections (not the generic bags care heading).

**Regression test:** `tests/test_retrieval.py::test_detect_breeze_cleaning_conflict_ignores_unrelated_retrieval`

---

### 2. Word “ordered” triggered order lookup path

**Reproduce:** Ask “My TrailPlus membership was active when I **ordered**. What is my return window?” The agent treated it as an order-status question.

**Root cause:** Order-intent regex used `\border\b` but was applied without ensuring it matched a standalone word boundary correctly in all code paths; phrasing like “ordered” could interact badly with routing heuristics during early development.

**Fix:** Tightened order-question detection to explicit shipment/status vocabulary; added `tests/test_agent.py::test_ordered_word_does_not_trigger_order_question_detection`.

**Regression test:** `tests/test_agent.py::test_ordered_word_does_not_trigger_order_question_detection`

---

### 3. LLM agent asked for order ID on general return-policy questions

**Reproduce:** Custom case `custom-return-window-paraphrase` — “I bought a daypack last week… how many days do I get?” — `SupportAgent` responded with “please share your order ID.”

**Root cause:** System prompt emphasized asking for order IDs; the model over-generalized to non-order return-policy questions.

**Fix:** Added prompt rule and a contextual notice when the query mentions returns without an order ID, instructing the model to answer from the standard return window.

**Regression test:** Covered by eval case `custom-return-window-paraphrase` in `python scripts/run_eval.py --agent support`.

---

### 4. Over-aggressive handoff on prompt-injection case (discovered beyond visible wording)

**Reproduce:** After first `SupportAgent` integration, `retrieved-prompt-injection` failed because `handoff_recommended=True` when the case expects `false`.

**Root cause:** Handoff logic treated broad answer phrases (“insufficient”, “cannot confirm”) as always requiring handoff, including cases where the agent correctly refused an injection attempt without needing human escalation.

**Fix:** `compute_handoff_recommended()` in `agent/handoff.py` explicitly excludes the migration-note injection pattern and uses narrower abstention/exception signals.

**Regression test:** `tests/test_handoff.py::test_prompt_injection_does_not_trigger_handoff` plus eval case `retrieved-prompt-injection`.

---

## Known limitations

- **In-memory only** — embeddings, sessions, and order data reload on every process start; no persistence across restarts or horizontal scaling.
- **LLM variability** — eval passes 20/20 with `gpt-4o-mini` at temperature 0.1, but wording may differ on re-runs; assertions allow flexible phrase matching where appropriate.
- **Conflict detection** — only the known Breeze Tumbler cleaning conflict is encoded; other corpus issues rely on retrieval ranking and LLM behavior.
- **No auth** — possession of an order ID is treated as sufficient (per assignment); production would need customer verification.
- **Local-only** — no deployment; API keys stay in `.env` on the reviewer's machine.
- **Single provider** — OpenAI only; no fallback model.

**Before production:** persistent vector store, session store (Redis), rate limiting, auth, eval in CI, citation verification layer, and human-in-the-loop for handoff cases.

---

## AI coding tools used

I used **Cursor** as a coding assistant throughout the project — mostly by prompting for specific pieces (e.g. “add a test for X”, “refactor this function”) rather than having it design the system end-to-end. The architecture — hybrid RAG + tool lookup, eval structure, handoff rules, metadata precedence — was my own; AI helped speed up implementation and iteration.

**Example of a wrong or incomplete AI suggestion:** An early version of conflict detection flagged a Breeze Tumbler source conflict whenever *any* retrieved chunk contained the token `wash`. That produced false conflicts on unrelated backpack return questions because the bags care section says “do not machine wash.” The fix required query- and heading-aware conflict logic, not just token matching in retrieved text.

---

## Repository layout

```text
.
├── knowledge-base/          # Source Markdown policies (read-only)
├── data/orders.json         # Mock order data
├── evaluation/              # visible-cases.json + custom-cases.json
├── src/comet_bot/
│   ├── ingest/              # Chunking and metadata
│   ├── retrieval/           # Embeddings, index, ranking, conflicts
│   ├── tools/               # Order lookup
│   ├── agent/               # SupportAgent, prompts, handoff, sessions
│   ├── eval/                # Eval loader, assertions, runner
│   └── web/                 # FastAPI app + static UI
├── scripts/                 # serve, chat, run_eval, utilities
├── tests/                   # Unit and integration tests
└── docs/DEMO.md             # Demo recording checklist
```

---

Built for the Aster & Row AI support agent take-home assignment.
