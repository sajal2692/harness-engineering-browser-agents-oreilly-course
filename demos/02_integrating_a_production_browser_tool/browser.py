"""The browser: run agent-browser commands in a named session and read their JSON replies."""

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


# 1. agent_browser: run one agent-browser command in a named session and return its JSON reply
def agent_browser(*args, session="demo2"):
    chrome_path = os.environ.get("CHROME_PATH") or CHROME_FOR_TESTING
    # --content-boundaries adds a random nonce to each reply, which tools.py uses to mark page content
    command = [AGENT_BROWSER, "--session", session, "--headed", "--executable-path", chrome_path, "--json",
               "--content-boundaries", *args]
    try:
        output = subprocess.run(command, capture_output=True, text=True, timeout=60).stdout
        reply = json.loads(output)
    except subprocess.TimeoutExpired:
        reply = {"success": False, "error": f"agent-browser did not answer within 60 seconds: {' '.join(args)}"}
    except ValueError:
        reply = {"success": False, "error": f"agent-browser printed: {output[:200]}"}
    if isinstance(reply.get("data"), dict):
        reply["data"].pop("lifecycle", None)  # launch details the model does not need
    print(tagged("browser", f"{' '.join(args)[:60]} -> {json.dumps(reply)[:80]}"))
    return reply


# 2. open_session: start a named session on a page, loading a saved sign-in if one is given
def open_session(url, sign_in=None, session="demo2"):
    if not Path(os.environ.get("CHROME_PATH") or CHROME_FOR_TESTING).exists():
        sys.exit("[error] Chrome for Testing is missing. Run the install command in the top-level README.")
    if not AGENT_BROWSER.exists():
        sys.exit("[error] agent-browser is not installed. Run npm install in this directory.")
    atexit.register(agent_browser, "close", session=session)  # the harness owns the session, so it closes it
    state = ["--state", str(sign_in)] if sign_in else []
    if not agent_browser(*state, "open", url, session=session).get("success"):
        sys.exit("[error] agent-browser could not open the page. See its message above.")
    print(tagged("session", f"{session}: Chrome for Testing, new profile, "
                            f"{'cookies from ' + sign_in.name if sign_in else 'no saved sign-in'}"))
