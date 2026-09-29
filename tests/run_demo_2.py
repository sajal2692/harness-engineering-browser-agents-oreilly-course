"""Drive Demo 2 in manual mode on IKEA Canada as a guest, the way the walkthrough does, and check each step.

Opens Chrome for Testing through agent-browser for about a minute. Declines one add-to-cart, then
approves one, so a desk lands in the guest cart of a throwaway session. Calls no model.
Needs `npm install` in the demo directory first.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parents[1] / "demos" / "02_integrating_a_production_browser_tool"
AGENT_BROWSER = DEMO_DIR / "node_modules/.bin/agent-browser"
PROMPT, APPROVAL = "browser> ", "[y/N] "

agent = subprocess.Popen(
    [sys.executable, "-u", str(DEMO_DIR / "main.py"), "--guest", "--manual"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
failures = []


def read_until(*markers):
    output = ""
    while not output.endswith(markers):
        char = agent.stdout.read(1)
        if not char:
            break
        output += char
    return output


def send(line, settle=0.0, show=25):
    agent.stdin.write(line + "\n")
    agent.stdin.flush()
    time.sleep(settle)
    output = read_until(PROMPT, APPROVAL)
    lines = output.splitlines()
    print(f"> {line}\n" + "\n".join(lines[:show]) + (f"\n... {len(lines) - show} more lines" if len(lines) > show else ""))
    return output


def check(label, condition):
    print(f"{'PASS' if condition else 'FAIL'}  {label}\n")
    if not condition:
        failures.append(label)


screenshots_before = set((DEMO_DIR / "screenshots").glob("*.png"))
runs_before = set((DEMO_DIR / "runs").glob("*.log"))
try:
    startup = read_until(PROMPT)
    print(startup)
    check("a guest session starts, and the harness reads who IKEA thinks is signed in",
          "[identity] IKEA says: Hej! Log in or join" in startup)

    home = send("snapshot")
    check("the snapshot comes from agent-browser with refs, on IKEA Canada's home page",
          "[ref=e" in home and "origin=https://www.ikea.com/ca/en/" in home)
    check("the snapshot is marked as page content with a nonce",
          "--- PAGE_CONTENT nonce=" in home and "--- END_PAGE_CONTENT nonce=" in home)
    check("each snapshot saves an annotated screenshot",
          len(set((DEMO_DIR / "screenshots").glob("*.png")) - screenshots_before) == 1)
    desks = re.search(r'link "Desks & desk chairs" \[ref=(e\d+)\]', home).group(1)
    send(f"click @{desks}", settle=3.0)
    listing = send("snapshot")
    check("the click opened the desks section", "origin=https://www.ikea.com/ca/en/cat/" in listing)
    unknown = send("click @e99999")
    check("the harness refuses a ref that is not in the latest snapshot",
          "not in your latest snapshot" in unknown and "click @e99999 ->" not in unknown)
    check("read returns the page text with prices", "Price $" in send("read", show=5))

    add = re.search(r'button "Add [^\n]*? to cart" \[ref=(e\d+)\]', listing).group(1)
    asked = send(f"click @{add}")
    check("a click that adds to the cart waits for a person", asked.endswith(APPROVAL))
    check("declining sends nothing", "did not approve" in send("n"))
    send(f"click @{add}")
    approved = send("y", settle=1.0)
    check("approving clicks, and the harness checks the cart count went up", "cart: 0 -> 1 items, added" in approved)
finally:
    agent.stdin.write("\n")
    agent.stdin.flush()
    agent.wait(timeout=60)

runs_after = set((DEMO_DIR / "runs").glob("*.log"))
check("the run wrote a run record", len(runs_after - runs_before) >= 1)
sessions = subprocess.run([AGENT_BROWSER, "--json", "session", "list"], capture_output=True, text=True).stdout
check("the script exits cleanly", agent.returncode == 0)
check("the harness closed its session", '"demo2"' not in sessions)
print("All checks passed" if not failures else f"{len(failures)} checks failed: {failures}")
sys.exit(1 if failures else 0)
