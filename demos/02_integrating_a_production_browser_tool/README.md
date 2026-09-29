# Demo 2: Integrating a Production Browser Tool

Demo 1's agent loop, with [agent-browser](https://github.com/vercel-labs/agent-browser) in place of
the browser tools we built. agent-browser is mounted through a skill, `skill/SKILL.md`, next to one
`browser` tool that runs its commands. The harness turns on the tool's domain limit, action policy,
and page-content markers, and checks what each action changed.

The task is Demo 1's, with one step added at the start that the domain limit refuses:

> First open https://example.com. Then open IKEA Canada at https://www.ikea.com/ca/en/ and find
> three desks under CAD $200 that are no wider than 120 cm, then open the cheapest one. Give each
> desk's name, price, and width, and the cheapest one's page URL.

```text
main.py ──> agent.py ──> Claude          skill/SKILL.md in the system prompt, one browser tool
               │
               └──> tools.py ──> browser.py ──> agent-browser (session demo2) ──> Chrome for Testing ──> ikea.com/ca only
```

## Setup

Do the repository setup in the top-level README first. Everything below runs from this directory.
Install the pinned agent-browser:

```bash
npm install
```

npm may warn that it skipped agent-browser's install script. agent-browser sets itself up the first
time it runs.

## Files

| File | What it does |
|---|---|
| `main.py` | The task, and the skill and harness rules |
| `browser.py` | Runs agent-browser commands with the harness's settings |
| `policy.json` | The only actions agent-browser will carry out; it refuses everything else |
| `tools.py` | The `browser` tool Claude can call, and the harness checks around it |
| `agent.py` | The agent loop, the same file as in Demo 1 |
| `utils.py` | The red box that shows the audience what Claude is acting on. Not a tool |
| `output.py` | The colored `[tag]` on every line, also written to a run record in `runs/` |
| `skill/SKILL.md` | The skill, adapted from agent-browser's own (Apache-2.0) |

`policy.json` also lists the actions the harness itself uses, such as `evaluate` for the red box.
`tools.py` keeps those from Claude; every other command goes to agent-browser, and its policy decides.

## Running it

```bash
uv run main.py --step
uv run main.py
```

`--step` pauses at each hand-off in the loop, as in Demo 1. When agent-browser's domain limit or
action policy refuses something, a `[refused]` line prints in the terminal. After each click or fill,
`[verify]` and `[diff]` show what changed on the page, and after each snapshot `[refs]` shows how many
refs carried over from the last one. Screenshots in `screenshots/` and run
records in `runs/` stay on your machine.

## Troubleshooting

- **`[error] agent-browser is not installed`:** run `npm install` in this directory.
- **A browser from an earlier run is still open:** `node_modules/.bin/agent-browser --session demo2 close`
