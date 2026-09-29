"""Sign in to IKEA by hand once and save that browser session for Demo 2. Run it before the demo, not during it."""

import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from browser import agent_browser, open_session

load_dotenv()  # reads CHROME_PATH, if set, from the .env file at the top of the repository
SIGN_IN = Path(__file__).parent / "ikea_sign_in.json"
signal.signal(signal.SIGINT, lambda *args: sys.exit("\n[stopped] Ctrl-C, nothing saved"))

# 1. Open IKEA Canada in a new session with a new, empty profile. The session closes when this script ends.
open_session("https://www.ikea.com/ca/en/", session="sign-in")

# 2. You sign in by hand in that window. This script never sees your password.
input("Choose Hej! Log in or join, sign in, then press Enter here. ")

# 3. Save the session's cookies and storage to a file
if not agent_browser("state", "save", str(SIGN_IN), session="sign-in").get("success"):
    sys.exit("[error] The sign-in was not saved. See the message above.")
print(f"Saved {SIGN_IN.name}. Anyone with this file is signed in as you: keep it out of Git and delete it after class.")
