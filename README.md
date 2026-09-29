# Harness Engineering for Browser Agents

Companion repository for the O'Reilly live course **Harness Engineering for Browser
Agents**, taught by Sajal Sharma.

The course has two instructor-led demos on IKEA Canada. You can follow both in class without
installing anything. This repository lets you read the code during the session and run the
demos yourself afterwards.

## Repository map

```text
demos/01_building_browser_tools/                  Demo 1: snapshot, click, and type built from Chrome DevTools Protocol commands
demos/02_integrating_a_production_browser_tool/   Demo 2: the same agent loop with agent-browser, mounted through a skill
tests/                                            Checks that drive each demo by hand on IKEA, with no model
pyproject.toml                                    Pinned Python dependencies
.env.example                                      Template for the Anthropic API key
```

Each demo directory has its own README with setup, the walkthrough, what to look for, and
troubleshooting.

## The demos

| | Demo 1: Building Browser Tools | Demo 2: Integrating a Production Browser Tool |
|---|---|---|
| Question | What does it take to let a model read a web page and act on it? | What does a production browser tool add, and what stays with the harness? |
| Shows | Chrome's accessibility tree turned into a short snapshot with element refs, clicks and typing sent as Chrome DevTools Protocol commands, a ref that goes stale, and Claude comparing IKEA desks with the three tools | agent-browser mounted through a skill, a saved sign-in loaded into a session the harness owns, an identity check, page content marked for the model, permission checks that allow, ask before the cart, or refuse, a check that the cart changed, a run record, and annotated screenshots of what Claude can click |
| Start here | [demos/01_building_browser_tools](demos/01_building_browser_tools/README.md) | [demos/02_integrating_a_production_browser_tool](demos/02_integrating_a_production_browser_tool/README.md) |

## Requirements

- macOS, Python 3.12 or newer, and [uv](https://docs.astral.sh/uv/)
- Node.js 24 or newer
- An Anthropic API key. Both demos use Claude Sonnet 5.5
- For Demo 2's signed-in run, an IKEA Canada account

## Setup

From this directory:

```bash
uv sync
npx @puppeteer/browsers@3.2.3 install chrome@154.0.8037.57 --path .browsers
cp .env.example .env
```

The second command downloads Chrome for Testing into `.browsers/`, about 370 MB. Both demos run
it with a new, empty profile, so they never touch your own Chrome or its profiles. The scripts
expect the Apple silicon build; on another system, put the path the command prints in `.env` as
`CHROME_PATH`. Add your Anthropic API key to `.env`.

## Tests

```bash
uv run python tests/run_demo_1.py
uv run python tests/run_demo_2.py
```

Each script calls its demo's tools directly, the way a model would, on IKEA Canada, and checks the
output. They open a browser window for up to a minute and call no model. Demo 1's
check only reads. Demo 2's check runs as a guest and puts one desk in the guest cart of a
throwaway session. It needs `npm install` in its demo directory first.
