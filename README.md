# Harness Engineering for Browser Agents

Companion repository for the O'Reilly live course **Harness Engineering for Browser
Agents**, taught by Sajal Sharma.

The course has two instructor-led demos on IKEA Canada. You can follow both in class without
installing anything. This repository lets you read the code during the session and run the
demos yourself afterwards.

## Repository map

```text
demos/01_building_browser_tools/                  Demo 1: snapshot, click, and type built from Chrome DevTools Protocol commands
demos/02_integrating_a_production_browser_tool/   Demo 2: the same task and agent loop with agent-browser, mounted through a skill
tests/                                            Checks that call each demo's tools on IKEA, with no model
pyproject.toml                                    Pinned Python dependencies
.env.example                                      Template for the Anthropic API key
```

Each demo directory has its own README with setup, how to run it, and troubleshooting.

## The demos

| | Demo 1: Building Browser Tools | Demo 2: Integrating a Production Browser Tool |
|---|---|---|
| Question | What does it take to let a model read a web page and act on it? | Why use a production browser tool instead of building on Demo 1's? |
| Shows | Browser tools built from Chrome DevTools Protocol commands, and Claude comparing IKEA desks with them | The same task with agent-browser, the tool's own domain limit and action policy refusing what they should, marked page content, a check of what each action changed, and a run record |
| Start here | [demos/01_building_browser_tools](demos/01_building_browser_tools/README.md) | [demos/02_integrating_a_production_browser_tool](demos/02_integrating_a_production_browser_tool/README.md) |

## Requirements

- macOS, Python 3.12 or newer, and [uv](https://docs.astral.sh/uv/)
- Node.js 24 or newer
- An Anthropic API key. Both demos use Claude Sonnet 5.5

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
output. They open a browser window for up to a minute, only read, and call no model. Demo 2's
check needs `npm install` in its demo directory first.
