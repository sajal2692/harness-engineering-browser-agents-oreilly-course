# Demo 2: Integrating a Production Browser Tool

The agent loop from Demo 1, with [agent-browser](https://github.com/vercel-labs/agent-browser) in
place of the browser code from Demo 1. agent-browser is mounted through a skill, `skill/SKILL.md`,
next to one `browser` tool that runs its commands. The harness keeps the session, the identity
check, permission checks, a check of the result, and a run record.

The task starts on IKEA Canada's home page, signed in to your account:

> Find the cheapest desk under CAD $200 that is no wider than 120 cm and add it to my cart.
> Tell me its name, price, and width.

```text
main.py ──> agent.py ──> Claude          skill/SKILL.md in the system prompt, one browser tool
               │
               └──> tools.py ──> browser.py ──> agent-browser (session demo2) ──> Chrome for Testing ──> ikea.com/ca
```

## Setup

Do the repository setup in the top-level README first. Everything below runs from this directory.
Install the pinned agent-browser:

```bash
npm install
```

npm may warn that it skipped agent-browser's install script. agent-browser sets itself up the first
time it runs.

## Before class: save a signed-in session

```bash
uv run save_sign_in.py
```

A browser window opens on IKEA Canada. Sign in by hand, then press Enter in the terminal. The script
saves the session to `ikea_sign_in.json`. It never sees your password, and neither does Claude.
Anyone with that file is signed in as you: it is in `.gitignore`, and you should delete it after
class.

## Files

| File | What it does |
|---|---|
| `main.py` | The start page, the task, the skill and harness rules, the saved sign-in, and the identity check |
| `browser.py` | Runs agent-browser commands in a named session |
| `tools.py` | The `browser` tool Claude can call, and the harness checks around it |
| `agent.py` | The agent loop, the same file as in Demo 1 |
| `utils.py` | The red box that shows the audience what Claude is acting on. Not a tool |
| `output.py` | The colored `[tag]` on every line, also written to a run record in `runs/` |
| `skill/SKILL.md` | The skill, adapted from agent-browser's own (Apache-2.0) |
| `save_sign_in.py` | Saves your IKEA sign-in before class |

## Running it

```bash
uv run main.py --step
```

`--step` pauses at each hand-off in the loop, as in Demo 1. When Claude asks to add a desk to the
cart, the harness asks you first:

```text
[approval] Claude wants to click: Add "MICKE Desk" to cart. Allow? [y/N]
```

```bash
uv run main.py
uv run main.py --guest
```

The first runs straight through. `--guest` skips the saved sign-in, for a dry run. The desk stays
in your cart afterwards; remove it if you want it gone. Screenshots in `screenshots/` and run
records in `runs/` stay on your machine.

## Troubleshooting

- **`No signed-in account, so the agent does not start`:** IKEA ended the saved session. Run
  `uv run save_sign_in.py` again, or use `--guest`.
- **`[error] agent-browser is not installed`:** run `npm install` in this directory.
- **A browser from an earlier run is still open:** `node_modules/.bin/agent-browser --session demo2 close`
