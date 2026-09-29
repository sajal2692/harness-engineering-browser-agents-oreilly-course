"""Call Demo 2's browser tool directly on IKEA Canada, the way Claude would, and check each step.

Opens Chrome for Testing through agent-browser for about a minute, only reads, and calls no model.
Needs `npm install` in the demo directory first.
"""

import contextlib
import io
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

DEMO_DIR = Path(__file__).resolve().parents[1] / "demos" / "02_integrating_a_production_browser_tool"
sys.path.insert(0, str(DEMO_DIR))
load_dotenv()  # reads CHROME_PATH, if set

import browser  # noqa: E402
from tools import run_tool  # noqa: E402

failures = []


def call(*args, show=25):
    """Run one browser command the way the agent loop does, and return its result plus everything it printed."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        result = run_tool("browser", {"args": list(args)})
    output = printed.getvalue() + result
    lines = output.splitlines()
    print(f"> {' '.join(args)}\n" + "\n".join(lines[:show]) + (f"\n... {len(lines) - show} more lines" if len(lines) > show else ""))
    return output


def check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}  {label}\n")
    if not condition:
        failures.append(label)


screenshots_before = set((DEMO_DIR / "screenshots").glob("*.png"))
runs_before = set((DEMO_DIR / "runs").glob("*.log"))
browser.open_session()

offsite = call("open", "https://example.com")
check("agent-browser refuses a site outside IKEA, and the harness prints it",
      "[refused]" in offsite and "not in the allowed domains list" in offsite)
check("opening IKEA Canada works", "The page is now https://www.ikea.com/ca/en/" in call("open", "https://www.ikea.com/ca/en/"))
home = call("snapshot")
check("the snapshot comes from agent-browser with refs, on IKEA Canada's home page",
      "[ref=e" in home and "origin=https://www.ikea.com/ca/en/" in home)
check("the snapshot is marked as page content with a nonce",
      "--- PAGE_CONTENT nonce=" in home and "--- END_PAGE_CONTENT nonce=" in home)
check("each snapshot saves an annotated screenshot",
      len(set((DEMO_DIR / "screenshots").glob("*.png")) - screenshots_before) == 1)
check("the harness refuses a ref that is not in the latest snapshot", "not in your latest snapshot" in call("click", "@e99999"))
check("the harness keeps its own helpers from Claude", "blocked: the harness keeps eval for itself" in call("eval", "1"))
scrolled = call("scroll", "down")
check("agent-browser refuses an action policy.json does not list, and the harness prints it",
      "[refused]" in scrolled and "denied by policy" in scrolled)

desks = re.search(r'link "Desks & desk chairs" \[ref=(e\d+)\]', home).group(1)
clicked = call("click", f"@{desks}")
check("after a click, the harness reports what changed and the new address",
      "The harness compared the page before and after" in clicked and "address changed to https://www.ikea.com/ca/en/cat/" in clicked)
check("read returns the page text with prices, marked as page content",
      "Price $" in (text := call("read", show=5)) and "--- PAGE_CONTENT nonce=" in text)

check("the run wrote a run record", len(set((DEMO_DIR / "runs").glob("*.log")) - runs_before) >= 1)

print("All checks passed" if not failures else f"{len(failures)} checks failed: {failures}")
sys.exit(1 if failures else 0)  # the harness closes its session on exit
