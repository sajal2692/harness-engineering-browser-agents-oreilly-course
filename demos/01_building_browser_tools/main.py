"""Demo 1: browser tools built from Chrome DevTools Protocol commands, used by Claude on IKEA Canada.

uv run main.py            Claude does the task
uv run main.py --step     Claude does the task, and you press Enter at each hand-off
uv run main.py --manual   you play the model and type the tool calls yourself
"""

import os
import signal
import sys

from dotenv import load_dotenv

import agent
import browser
from output import tagged
from tools import run_tool

load_dotenv()  # reads ANTHROPIC_API_KEY, and CHROME_PATH if set, from the .env file at the top of the repository
START_URL = "https://www.ikea.com/ca/en/"
TASK = ("Find three desks under CAD $200 that are no wider than 120 cm, then open the cheapest one. "
        "Give each desk's name, price, and width, and the cheapest one's page URL.")
SYSTEM = ("You use a web browser through three tools. It is open on IKEA Canada. Take a snapshot to read the "
          "page, and use only refs from the latest snapshot. After every click or type, take a new snapshot to "
          "check what changed. Get around through the site's menus and links. Only read: leave the cookie "
          "banner, search, filters, and cart alone. Answer only with facts you read on the page.")

# 1. Stop early if the API key is missing, and stop cleanly on Ctrl-C (Chrome still closes)
if "--manual" not in sys.argv and not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("[error] ANTHROPIC_API_KEY is not set. Copy .env.example to .env at the top of the repository.")
signal.signal(signal.SIGINT, lambda *args: sys.exit("\n[stopped] Ctrl-C"))

# 2. Launch Chrome for Testing on IKEA Canada's home page and connect to it
browser.launch(START_URL)

# 3. Manual mode: you play the model and type the tool calls yourself
if "--manual" in sys.argv:
    print(tagged("step", "You are the model. Type snapshot, click @e3, or type @e1 some text. An empty line stops."))
    while line := input("tool> ").strip():
        name, *rest = line.split(maxsplit=2)
        print(tagged("result", run_tool(name, dict(zip(["ref", "text"], rest)))))
    sys.exit()

# 4. Claude does the task with the three tools
agent.run(TASK, SYSTEM, step="--step" in sys.argv)
