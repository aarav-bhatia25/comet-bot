# Recording the demo GIF

Before submitting, add a 2–4 minute screen recording at **`docs/demo.gif`** (or link a video in the README).

Suggested flow:

1. **Knowledge-base question with citations** — e.g. “How long do I have to return a backpack?” — show source tags in the UI.
2. **Order lookup** — e.g. “Where is ORD-1007 and when should it arrive?” — show carrier and delivery date.
3. **Multi-turn** — “Do you ship internationally?” then “What about Canada?” — same session.
4. **Refusal / handoff** — e.g. damaged final-sale item, or “Are all fabrics vegan?” — show handoff banner or abstention.
5. **Evaluation suite** — run `python scripts/run_eval.py --agent support` in a terminal and show 20/20.

**macOS:** QuickTime → File → New Screen Recording, then convert to GIF with [gifski](https://gif.ski/) or upload MP4 to GitHub and link it in the README.

```bash
# Example (gifski installed via brew)
gifski -o docs/demo.gif --width 1280 --fps 10 recording.mov
```
