"""The browser: launch Chrome for Testing and send it Chrome DevTools Protocol (CDP) commands."""

import atexit
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from output import tagged

CHROME_FOR_TESTING = Path(__file__).parent / ("../../.browsers/chrome/mac_arm-154.0.8037.57/chrome-mac-arm64/"
                                              "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
ws = None  # the WebSocket to the tab, opened by launch()
message_ids = itertools.count(1)


# 1. launch: start Chrome for Testing with a new, empty profile and a debugging port that Chrome picks
def launch(url):
    global ws
    chrome_path = os.environ.get("CHROME_PATH") or CHROME_FOR_TESTING
    if not Path(chrome_path).exists():
        sys.exit(f"[error] Chrome for Testing is not at {chrome_path}. Run the install command in the top-level README.")
    profile = tempfile.mkdtemp(prefix="demo1-chrome-")
    chrome = subprocess.Popen(
        [chrome_path, f"--user-data-dir={profile}", "--remote-debugging-port=0", "--no-first-run",
         "--no-default-browser-check", "--use-mock-keychain", "--disable-backgrounding-occluded-windows", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    atexit.register(close, chrome, profile)

    # 2. Read the port from the profile folder, find the tab, and open a WebSocket to it
    port_file = Path(profile, "DevToolsActivePort")
    started = time.time()
    while not port_file.exists() or len(port_file.read_text().split()) < 2:
        if time.time() - started > 20:
            sys.exit("[error] Chrome for Testing did not start within 20 seconds.")
        time.sleep(0.1)
    port = port_file.read_text().split()[0]
    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
    tab = next(tab for tab in tabs if tab["type"] == "page")
    # One connection for the whole run. A real page's tree can pass the 1 MB default message size.
    ws = connect(tab["webSocketDebuggerUrl"], max_size=None, legacy=True)
    print(tagged("browser", f"Chrome for Testing with a new profile in {profile}, deleted on exit"))
    print(tagged("browser", f"connected to {tab['webSocketDebuggerUrl']}"))
    cdp("DOM.enable")  # the Overlay domain, which draws highlights, needs the DOM domain
    cdp("Overlay.enable")


def close(chrome, profile):
    chrome.terminate()
    chrome.wait()
    shutil.rmtree(profile, ignore_errors=True)


# 3. cdp: send one command to the tab and wait up to 30 seconds for the reply with the same id
def cdp(method, **params):
    message_id = next(message_ids)
    try:
        ws.send(json.dumps({"id": message_id, "method": method, "params": params}))
        reply = json.loads(ws.recv(timeout=30))  # raises TimeoutError if Chrome does not answer
        while reply.get("id") != message_id:  # skip events, which have no id
            reply = json.loads(ws.recv(timeout=30))
    except ConnectionClosed:
        sys.exit("[error] The connection to Chrome closed. Was the browser window closed?")
    outcome = reply.get("error") or reply["result"]
    print(tagged("cdp", f"{method:<28} {json.dumps(params)[:50]} -> {json.dumps(outcome)[:60]}"))
    if "error" in reply:
        raise RuntimeError(reply["error"]["message"])
    return reply["result"]
