"""Drive Demo 1 in manual mode on IKEA Canada, the way the walkthrough does, and check each step.

Starts on IKEA Canada's home page, opens the desks section and one product page, and types into
the search box without submitting it. Opens Chrome for Testing for about half a minute, only
reads, and calls no model.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "demos" / "01_building_browser_tools" / "main.py"
PROMPT = "tool> "

agent = subprocess.Popen(
    [sys.executable, "-u", str(DEMO), "--manual"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
failures = []


def read_until_prompt():
    output = ""
    while not output.endswith(PROMPT):
        char = agent.stdout.read(1)
        if not char:
            break
        output += char
    return output


def send(line, settle=0.0, show=40):
    agent.stdin.write(line + "\n")
    agent.stdin.flush()
    time.sleep(settle)
    output = read_until_prompt()
    lines = output.removesuffix(PROMPT).splitlines()
    print(f"{PROMPT}{line}\n" + "\n".join(lines[:show]) + (f"\n... {len(lines) - show} more lines" if len(lines) > show else ""))
    return output


def ref(snapshot, pattern):
    match = re.search(r"(@e\d+) " + pattern, snapshot)
    return match.group(1) if match else "@missing"


def snapshot_when_loaded():
    """Take snapshots until the page has content, as a person would wait for a slow page."""
    for _ in range(4):
        output = send("snapshot", show=12)
        if "0 refs" not in output:
            return output
        time.sleep(3)
    return output


def check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}  {label}\n")
    if not condition:
        failures.append(label)


profile = "unknown"
try:
    startup = read_until_prompt()
    print(startup.removesuffix(PROMPT))
    profile = re.search(r"new profile in (\S+),", startup).group(1)
    check("Chrome for Testing starts with a new profile and a WebSocket to the tab", "connected to ws://" in startup)
    time.sleep(8)  # let IKEA's page finish loading, as a person would

    home = send("snapshot", show=12)
    check("the snapshot is IKEA Canada's home page", "page https://www.ikea.com/ca/en/" in home)
    check("the snapshot reports how much smaller it is than Chrome's tree", "[snapshot] Chrome sent" in home)

    clicked = send(f"click {ref(home, 'link \"Desks & desk chairs\"')}", settle=8.0)
    check("click highlights the element, then sends three mouse events",
          "Overlay.highlightNode" in clicked and clicked.count("Input.dispatchMouseEvent") == 3)
    listing = snapshot_when_loaded()
    check("the click opened the desks section, with product names and prices",
          "page https://www.ikea.com/ca/en/cat/" in listing and "Desk," in listing and "Price $" in listing)

    product = ref(listing, 'link "(?!Option)[^"]*Desk, ')
    send(f"click {product}", settle=6.0)
    stale = send(f"click {ref(listing, 'combobox \"Search')}")
    check("a ref to an element on the previous page fails with Chrome's own error",
          'error: Chrome said "' in stale and "Input.dispatchMouseEvent" not in stale)
    page = snapshot_when_loaded()
    check("the product click opened a product page", "page https://www.ikea.com/ca/en/p/" in page and "Price $" in page)
    check("the harness refuses a ref from an earlier snapshot", "is not in the latest snapshot" in send(f"click {product}"))
    typed = send(f"type {ref(page, 'combobox \"Search')} desk", settle=1.0)
    check("type highlights the field, then sends focus, select, and insertText",
          all(method in typed for method in ("Overlay.highlightNode", "DOM.focus", "Input.insertText")))
finally:
    agent.stdin.write("\n")
    agent.stdin.flush()
    agent.wait(timeout=30)

check("the script exits cleanly", agent.returncode == 0)
check("the temporary profile is deleted", not Path(profile).exists())
print("All checks passed" if not failures else f"{len(failures)} checks failed: {failures}")
sys.exit(1 if failures else 0)
