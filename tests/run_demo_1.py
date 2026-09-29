"""Call Demo 1's browser tools directly on IKEA Canada, the way Claude would, and check each step.

Starts on IKEA Canada's home page, opens the desks section and one product page, and types into
the search box without submitting it. Opens Chrome for Testing for about half a minute, only
reads, and calls no model.
"""

import contextlib
import io
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

DEMO = Path(__file__).resolve().parents[1] / "demos" / "01_building_browser_tools"
sys.path.insert(0, str(DEMO))
load_dotenv()  # reads CHROME_PATH, if set

import browser  # noqa: E402
from tools import run_tool  # noqa: E402

failures = []


def call(name, settle=0.0, show=40, **args):
    """Run one tool the way the agent loop does, and return its result plus everything it printed."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        result = run_tool(name, args)
    time.sleep(settle)
    output = printed.getvalue() + result
    lines = output.splitlines()
    print(f"> {name} {args}\n" + "\n".join(lines[:show]) + (f"\n... {len(lines) - show} more lines" if len(lines) > show else ""))
    return output


def ref(snapshot, pattern):
    match = re.search(r"(@e\d+) " + pattern, snapshot)
    return match.group(1) if match else "@missing"


def snapshot_when_loaded():
    """Take snapshots until the page has content, as a person would wait for a slow page."""
    for _ in range(4):
        output = call("snapshot", show=12)
        if "0 refs" not in output:
            return output
        time.sleep(3)
    return output


def check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}  {label}\n")
    if not condition:
        failures.append(label)


startup = io.StringIO()
with contextlib.redirect_stdout(startup):
    browser.launch("https://www.ikea.com/ca/en/")
print(startup.getvalue())
check("Chrome for Testing starts with a new profile and a WebSocket to the tab", "connected to ws://" in startup.getvalue())
time.sleep(8)  # let IKEA's page finish loading, as a person would

home = call("snapshot", show=12)
check("the snapshot is IKEA Canada's home page", "page https://www.ikea.com/ca/en/" in home)
check("the snapshot reports how much smaller it is than Chrome's tree", "[snapshot] Chrome sent" in home)

clicked = call("click", settle=8.0, ref=ref(home, 'link "Desks & desk chairs"'))
check("click highlights the element, then sends three mouse events",
      "Runtime.callFunctionOn" in clicked and clicked.count("Input.dispatchMouseEvent") == 3)
listing = snapshot_when_loaded()
check("the click opened the desks section, with product names and prices",
      "page https://www.ikea.com/ca/en/cat/" in listing and "Desk," in listing and "Price $" in listing)

product = ref(listing, 'link "(?!Option)[^"]*Desk, ')
call("click", settle=6.0, ref=product)
stale = call("click", ref=ref(listing, 'combobox "Search'))
check("a ref to an element on the previous page fails with Chrome's own error",
      'error: Chrome said "' in stale and "Input.dispatchMouseEvent" not in stale)
page = snapshot_when_loaded()
check("the product click opened a product page", "page https://www.ikea.com/ca/en/p/" in page and "Price $" in page)
check("the harness refuses a ref from an earlier snapshot", "is not in the latest snapshot" in call("click", ref=product))
typed = call("type", settle=1.0, ref=ref(page, 'combobox "Search'), text="desk")
check("type highlights the field, then sends focus, select, and insertText",
      all(method in typed for method in ("Runtime.callFunctionOn", "DOM.focus", "Input.insertText")))

print("All checks passed" if not failures else f"{len(failures)} checks failed: {failures}")
sys.exit(1 if failures else 0)  # Chrome closes and its profile is deleted on exit
