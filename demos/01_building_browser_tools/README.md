# Demo 1: Building Browser Tools

One Python script gives Claude three browser tools, `snapshot`, `click`, and `type`, built
directly from Chrome DevTools Protocol (CDP) commands. It launches Chrome for Testing with a new,
empty profile, talks to the tab over a WebSocket, and prints every CDP command it sends. Before
each click or type, it outlines the target in red for a second, so you can watch the tool work
on the page.

The task starts on IKEA Canada's home page and only reads:

> Find three desks under CAD $200 that are no wider than 120 cm, then open the cheapest one. Give
> each desk's name, price, and width, and the cheapest one's page URL.

Claude has to find the desks itself, through the site's menus and links. The system prompt keeps
it away from search, filters, the cart, and the cookie banner.

```text
main.py ──> agent.py ──> Claude          the model chooses the next tool call
               │
               └──> tools.py ──> browser.py ──> WebSocket (CDP) ──> Chrome for Testing ──> ikea.com/ca
```

## Setup

From the repository root, once:

```bash
uv sync
npx @puppeteer/browsers@3.2.3 install chrome@154.0.8037.57 --path .browsers
cp .env.example .env
```

The second command downloads Chrome for Testing into `.browsers/`, about 370 MB. It runs apart
from your own Chrome and never touches your profile. Add your Anthropic API key to `.env`.

The script expects the Apple silicon build. On another system the install command prints a
different path; put it in `.env` as `CHROME_PATH`.

## The walkthrough

Run everything from this directory.

**1. Read the code.** Each file has one job and reads top to bottom:

| File | What it does |
|---|---|
| `main.py` | The start page, the task, and the system prompt; the checks; then manual mode or Claude |
| `browser.py` | `launch()` starts Chrome for Testing with a new profile and opens a WebSocket to its tab; `cdp()` sends one command and waits for the reply with the same id |
| `tools.py` | `snapshot()` turns the accessibility tree into short lines with refs; `highlight()`, `click()`, and `type_text()` act on a ref; `run_tool()` checks the ref and turns Chrome's errors into text; `TOOLS` is what Claude sees |
| `agent.py` | The agent loop: send the conversation, run the one tool Claude asks for, send back the result |
| `output.py` | The colored `[tag]` at the start of every printed line |

**2. Play the model.** Manual mode runs the same tools with no API call:

```bash
uv run main.py --manual
```

Wait for the home page to load, then type `snapshot`. The first line says how much the snapshot
throws away. One run on 2026-09-28:

```text
[snapshot] Chrome sent 3,314 nodes (1,482,332 characters). The model gets 484 lines (26,676 characters) and 283 refs.
```

That is about 6,500 input tokens for one look at the page. Find the line
`link "Desks & desk chairs"` and click its ref. The CDP commands behind the click print: scroll
into view, outline the link in red and hide the outline, find the element's corners on screen,
then move, press, and release the mouse at the centre. The browser opens IKEA's Tables & desks section.
Take another snapshot and click one of the desks.

**3. Use a ref that has gone stale.** The browser is now on the desk's page. Without taking a new
snapshot, click a ref from the list page:

```text
tool> click @e...
error: Chrome said "Node does not have a layout object". Take a new snapshot.
```

That element belonged to the page you left, so Chrome refuses it before any input is sent. It
does not always fail this cleanly. IKEA's section pages reuse some elements when they change, so
an old ref can end up on a different element: in one run, a ref taken from the home page later
clicked "Conference & meeting tables". Either way, a ref is only good for the snapshot it came
from. After a new snapshot, the harness refuses old refs itself: `error: @e... is not in the
latest snapshot`. Ref numbers keep counting up across snapshots, so an old number is never reused.

**4. Type.** Take a snapshot, find the search box (`combobox "Search for products..."`), and
type into it with its ref, without pressing Enter: `type @e... desk`. IKEA's suggestion list opens over the
page. Nothing in this script checks what is on top of a click point, so a later click could land
on that list instead.

Press Enter on an empty line to stop. The script closes Chrome and deletes the profile.

**5. Let Claude run it, one step at a time.**

```bash
uv run main.py --step
```

`--step` waits for Enter at each hand-off in the loop: before the task goes to Claude, before the
harness runs the tool Claude asked for, and before the result goes back. Each turn prints its
token count, a summary of Claude's reasoning, and the tool call. Enter runs the call: the CDP
commands print, the target lights up in the browser, and the start of the text Claude gets back
prints. Look at how the snapshot after each click is the only way Claude learns whether the
click worked.

Leave out `--step` to run straight through. Prices and stock on IKEA change, so results differ
between runs.

## What this harness does not do

These gaps are on purpose. Demo 2 and Module 2 cover them.

- It does not wait for a page to finish loading after a click.
- It does not check what is on top of the click point, so a banner or suggestion list can take the click.
- It does not check that an action worked; only the next snapshot shows that.
- It does not limit which sites the browser may visit, and it does not look inside iframes.
- It sends every past snapshot back to Claude on each turn. Watch the input tokens grow; a real
  harness keeps recent observations and a short progress summary instead.
- It does not cap snapshot size. One IKEA page is about 26,000 characters.
- Its only timeout is 30 seconds per CDP command. A command that times out may still have acted.

## Troubleshooting

- **`[error] Chrome for Testing is not at ...`:** run the install command from the repository
  root, or set `CHROME_PATH` in `.env`.
- **The first snapshot has only a page line:** the page was still loading. Take another snapshot.
- **A click does nothing:** something may cover the element, such as the cookie banner or a
  suggestion list. Take a snapshot and look for it.
- **The browser window closes by itself:** some blocking apps close browsers that lack their
  extension. Pause the app while you run the demo.
