"""Call Demo 2's browser tool directly on IKEA Canada as a guest, the way Claude would, and check each step.

Opens Chrome for Testing through agent-browser for about a minute. Declines one add-to-cart, then
approves one, so a desk lands in the guest cart of a throwaway session. Calls no model.
Needs `npm install` in the demo directory first.
"""

import builtins
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
from tools import run_tool, who_is_signed_in  # noqa: E402

failures = []
answers = []  # what the person types at the approval prompt, in order
builtins.input = lambda prompt="": (print(prompt, end=""), answers.pop(0))[1]


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

browser.open_session("https://www.ikea.com/ca/en/")
account = who_is_signed_in()
print(f"IKEA says: {account}\n")
check("a guest session starts, and the harness reads who IKEA thinks is signed in", account == "Hej! Log in or join")

home = call("snapshot")
check("the snapshot comes from agent-browser with refs, on IKEA Canada's home page",
      "[ref=e" in home and "origin=https://www.ikea.com/ca/en/" in home)
check("the snapshot is marked as page content with a nonce",
      "--- PAGE_CONTENT nonce=" in home and "--- END_PAGE_CONTENT nonce=" in home)
check("each snapshot saves an annotated screenshot",
      len(set((DEMO_DIR / "screenshots").glob("*.png")) - screenshots_before) == 1)
desks = re.search(r'link "Desks & desk chairs" \[ref=(e\d+)\]', home).group(1)
call("click", f"@{desks}")
listing = call("snapshot")
check("the click opened the desks section", "origin=https://www.ikea.com/ca/en/cat/" in listing)
unknown = call("click", "@e99999")
check("the harness refuses a ref that is not in the latest snapshot",
      "not in your latest snapshot" in unknown and "click @e99999 ->" not in unknown)
check("read returns the page text with prices", "Price $" in call("read", show=5))

add = re.search(r'button "Add [^\n]*? to cart" \[ref=(e\d+)\]', listing).group(1)
answers.append("n")
declined = call("click", f"@{add}")
check("a click that adds to the cart waits for a person, and declining sends nothing",
      "Allow? [y/N]" in declined and "did not approve" in declined)
answers.append("y")
approved = call("click", f"@{add}")
check("approving clicks, and the harness checks the cart count went up", "cart: 0 -> 1 items, added" in approved)
check("the run wrote a run record", len(set((DEMO_DIR / "runs").glob("*.log")) - runs_before) >= 1)

print("All checks passed" if not failures else f"{len(failures)} checks failed: {failures}")
sys.exit(1 if failures else 0)  # the harness closes its session on exit
