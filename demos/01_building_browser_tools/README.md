# Demo 1: Building Browser Tools

Claude gets three browser tools, `snapshot`, `click`, and `type`, built directly from Chrome
DevTools Protocol (CDP) commands. The script runs Chrome for Testing with a new, empty profile and
prints every CDP command it sends.

The task starts on IKEA Canada's home page and only reads:

> Find three desks under CAD $200 that are no wider than 120 cm, then open the cheapest one. Give
> each desk's name, price, and width, and the cheapest one's page URL.

```text
main.py ──> agent.py ──> Claude          the model chooses the next tool call
               │
               └──> tools.py ──> browser.py ──> WebSocket (CDP) ──> Chrome for Testing ──> ikea.com/ca
```

## Setup

Do the repository setup in the top-level README first. Everything below runs from this directory.

## Files

| File | What it does |
|---|---|
| `main.py` | The start page, the task, and the system prompt |
| `browser.py` | Starts Chrome for Testing and sends it CDP commands |
| `tools.py` | The three tools Claude can call, and `TOOLS`, the definitions Claude sees |
| `agent.py` | The agent loop |
| `utils.py` | The red box that shows the audience what Claude is acting on. Not a tool |
| `output.py` | The colored `[tag]` at the start of every printed line |

## Running it

```bash
uv run main.py --step
```

`--step` pauses at each hand-off in the loop: before the task goes to Claude, before each tool call
runs, and before each result goes back. While it waits, the browser shows what Claude asked for.
Press Enter to continue.

```bash
uv run main.py
```

Without `--step`, it runs straight through. Prices and stock on IKEA change, so results differ
between runs.

## What this harness leaves out

These gaps are on purpose; Demo 2 covers several of them. It does not wait for pages to load, check
what covers a click point, confirm that an action worked, limit which sites the browser visits, or
trim old snapshots from the conversation.

## Troubleshooting

- **`[error] Chrome for Testing is not at ...`:** run the install command from the top-level README,
  or set `CHROME_PATH` in `.env`.
- **The first snapshot has only a page line:** the page was still loading. Claude usually takes
  another snapshot.
- **The browser window closes by itself:** some blocking apps close browsers that lack their
  extension. Pause the app while you run the demo.
