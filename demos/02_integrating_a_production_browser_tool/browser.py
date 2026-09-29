"""The browser: run agent-browser commands in the session this harness owns, and read their JSON replies."""

import atexit
import json
import os
import subprocess
import sys
from pathlib import Path

from output import tagged

DEMO_DIR = Path(__file__).parent
CHROME_FOR_TESTING = DEMO_DIR / ("../../.browsers/chrome/mac_arm-154.0.8037.57/chrome-mac-arm64/"
                                 "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
AGENT_BROWSER = DEMO_DIR / "node_modules/.bin/agent-browser"  # version 0.38.1, pinned in package.json
SESSION = "demo2"


# 1. agent_browser: run one agent-browser command with the harness's settings and return its JSON reply
def agent_browser(*args):
    chrome_path = os.environ.get("CHROME_PATH") or CHROME_FOR_TESTING
    command = [AGENT_BROWSER, "--session", SESSION, "--headed", "--executable-path", chrome_path, "--json",
               "--allowed-domains", "ikea.com,*.ikea.com,*.cdtapps.com",  # only IKEA, including its product search API
               "--action-policy", str(DEMO_DIR / "policy.json"),    # agent-browser refuses actions not listed there
               "--content-boundaries",                              # each reply carries a random nonce for marking
               *args]
    try:
        output = subprocess.run(command, capture_output=True, text=True, timeout=60).stdout
        reply = json.loads(output)
    except subprocess.TimeoutExpired:
        reply = {"success": False, "error": f"agent-browser did not answer within 60 seconds: {' '.join(args)}"}
    except ValueError:
        reply = {"success": False, "error": f"agent-browser printed: {output[:200]}"}
    if isinstance(reply.get("data"), dict):
        reply["data"].pop("lifecycle", None)  # launch details the model does not need
        reply["data"].pop("webmcp", None)     # tools the page offers to agents; this demo does not use them
    print(tagged("browser", f"{' '.join(args)[:60]} -> {json.dumps(reply)[:80]}"))
    return reply


# 2. open_session: start the session on a blank page with a new, empty profile, and close it when the script ends
def open_session():
    if not Path(os.environ.get("CHROME_PATH") or CHROME_FOR_TESTING).exists():
        sys.exit("[error] Chrome for Testing is missing. Run the install command in the top-level README.")
    if not AGENT_BROWSER.exists():
        sys.exit("[error] agent-browser is not installed. Run npm install in this directory.")
    atexit.register(agent_browser, "close")  # the harness owns the session, so it closes it
    if not agent_browser("get", "url").get("success"):  # any command starts the browser; this one just reads the address
        sys.exit("[error] agent-browser could not start the browser. See its message above.")
    print(tagged("session", f"{SESSION}: Chrome for Testing, new profile, IKEA domains only, actions from policy.json"))
