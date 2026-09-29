# Demo 2: Integrating a Production Browser Tool

The agent loop from Demo 1, with agent-browser in place of the browser code we wrote. agent-browser
is Vercel's browser automation CLI for agents. It is mounted through a skill: a short instruction
file that goes into the system prompt, next to one `browser` tool that runs agent-browser commands.

The task starts on IKEA Canada's home page, signed in to your account, and changes one thing:

> Find the cheapest desk under CAD $200 that is no wider than 120 cm and add it to my cart.
> Tell me its name, price, and width.

agent-browser takes over the browser work. The harness keeps the decisions:

- **Session:** the harness names the session, starts it with a new profile, loads your saved
  sign-in, and closes it at the end.
- **Identity:** before Claude starts, the harness reads who IKEA thinks is signed in, and stops if
  nobody is.
- **Permission:** before each command, the harness checks that the page is still on IKEA Canada and
  that the ref came from Claude's latest snapshot. It refuses checkout and sign-out, and a click that
  adds to the cart waits for your yes or no. A refusal goes back to Claude as a `blocked:` result.
- **Page content as data:** every snapshot and `read` result goes back to Claude between
  `PAGE_CONTENT` markers that carry agent-browser's random nonce, and the harness rules tell Claude
  never to follow instructions inside them. The markers help the model; the permission checks still
  apply when it is fooled.
- **Verification:** after an approved click, the harness re-reads the cart count for up to five
  seconds and checks that it went up. A `clicked` reply only means the input was sent. The count
  cannot tell which desk was added.
- **Recovery:** after every click, Claude takes a new snapshot, deals with anything unexpected
  such as IKEA's cart message or chat button, and retries once or stops.
- **Run record:** every printed line also goes into `runs/<date>_<time>.log`, with the account
  name in IKEA's greeting redacted. Claude's copy of the page has the name redacted too.
- **Pictures:** every snapshot also saves an annotated screenshot in `screenshots/`, with a
  numbered box on each element Claude can act on. The boxes flash in the browser window too.
  Screenshots are not redacted, so a signed-in one can show your name.

```text
main.py ──> agent.py ──> Claude          skill/SKILL.md in the system prompt, one browser tool
               │
               └──> tools.py ──> browser.py ──> agent-browser (session demo2) ──> Chrome for Testing ──> ikea.com/ca
```

## Setup

Do the repository setup in the top-level README first. Then install the pinned agent-browser in
this directory:

```bash
npm install
```

npm may warn that it skipped agent-browser's install script. That is fine: agent-browser sets
itself up the first time it runs.

## Before class: save a signed-in session

Run this once, before the demo, never during it:

```bash
uv run save_sign_in.py
```

A browser window opens on IKEA Canada. Choose **Hej! Log in or join** and sign in by hand. Then
press Enter in the terminal. The script saves the session's cookies and storage to
`ikea_sign_in.json` and closes the window. It never sees your password, and neither does Claude.

Anyone with `ikea_sign_in.json` is signed in as you. It is in `.gitignore`; delete it after class.
If IKEA signs you out later, run the script again.

## The walkthrough

Run everything from this directory.

**1. Compare the files with Demo 1's.** The layout is the same, and `agent.py` is the same file
in both demos. What changes is the browser code and the tools:

| File | Demo 1 | Demo 2 |
|---|---|---|
| `main.py` | Start page, task, system prompt, checks | The same, plus mounting the skill, loading the saved sign-in, the identity check, and a second session at the end |
| `browser.py` | `launch()` starts Chrome for Testing; `cdp()` sends one CDP command | `open_session()` starts agent-browser's session; `agent_browser()` runs one command and reads its JSON reply |
| `tools.py` | Three tools built from CDP: `snapshot`, `click`, `type` | One `browser` tool: `snapshot` for refs, `read` for text, `click`, `fill`; plus the permission check, cart check, page-content markers, and screenshots |
| `agent.py` | The agent loop | The same file |
| `output.py` | The colored `[tag]` on every line | The same, with tags for the session, identity, approval, refusals, and cart check, and a run record with the account name redacted |

At the level of each action:

| Demo 1 | Demo 2 |
|---|---|
| `snapshot()` over the accessibility tree | `snapshot` for refs, `read` for the page's text |
| `click()`: scroll, find the centre, send three mouse events | `click @eN`: the same steps, plus a check of what is on top of the click point |
| `type_text()`: focus, select, insert text | `fill @eN text`: clear, then type |
| `run_tool()` checks refs | `run_tool()` allows four commands on IKEA Canada, checks refs, refuses checkout, asks before cart clicks, checks the cart, marks page content |

**2. Play the model.**

```bash
uv run main.py --manual
```

The first lines show the session and who IKEA thinks is signed in:

```text
[session] demo2: Chrome for Testing, new profile, cookies from ikea_sign_in.json
[identity] IKEA says: Hej ...
```

Type `snapshot`, then open the newest picture in `screenshots/` to see what the refs point at.
Click the ref of `link "Desks & desk chairs"`, take another snapshot, and type `read` to see the
prices. Find an `Add "..." to cart` button in the snapshot and click it:

```text
browser> click @e257
[approval] Claude wants to click: Add "MICKE Desk" to cart. Allow? [y/N] y
[approval] approved
[verify] cart: 0 -> 1 items, added
clicked @e257. The harness checked the cart: 0 items before, 1 after.
```

Try a ref that is not in the latest snapshot, such as `click @e99999`. The harness answers
`blocked: e99999 is not in your latest snapshot` and sends nothing to the browser.

That output is from a guest run on 2026-09-28. Signed in, the counts start from what is already
in your cart. Remove the desk from your cart afterwards if you want it gone.

**3. Let Claude run it.**

```bash
uv run main.py
```

Look for the identity check before the first turn, `read` for prices and `snapshot` for refs, the
`PAGE_CONTENT` markers around each result, the approval prompt, the cart check, and at the end a
second session that IKEA sees as a guest, because the sign-in belongs to the first session only.
Add `--step` to press Enter at each hand-off, as in Demo 1. Afterwards, open the newest file in
`runs/` to read the run record.

The approval is built in harness code, not with agent-browser's `--confirm-actions` or
`--action-policy`. Here it matches a button's name, which is the weak part of this check: a button
IKEA renames would slip past it. The site limit is harness code too, because agent-browser 0.38.1
does not allow its `--allowed-domains` option with a saved sign-in (`--state`).

**4. Without the saved sign-in.** `--guest` skips it, for a dry run or if the sign-in has
expired:

```bash
uv run main.py --guest
```

## What agent-browser adds, measured on IKEA's desks page

| | Demo 1 tools | agent-browser 0.38.1 |
|---|---|---|
| Elements the model can act on | 288 refs: links, buttons, text fields | 561 refs, adding radio buttons, checkboxes, and clickable labels |
| Reading the page | One snapshot of 35,000 characters | `read`: the page's text in 18,700 characters, with the prices |
| Showing the model's view | Text | `screenshot --annotate`: numbered boxes that match the refs |
| Clicking | Blind, with no wait | Waits for navigation, refuses a click when something covers the target |
| Sessions | One throwaway profile per run | Named sessions, saved and loaded state, `close` |

## Troubleshooting

- **`No signed-in account, so the agent does not start`:** IKEA ended the saved session. Run `uv run save_sign_in.py` again, or
  use `--guest`.
- **A browser from an earlier run is still open:** `node_modules/.bin/agent-browser --session demo2 close`
- **`[error] agent-browser is not installed`:** run `npm install` in this directory.
- **A click is refused with `covered by`:** something sits on top of the target, often the cookie
  banner or the chat button. Take a snapshot and choose another way, which is what the skill tells
  Claude to do.
