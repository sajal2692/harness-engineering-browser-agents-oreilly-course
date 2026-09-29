"""The one browser tool Claude can call, backed by agent-browser, and the harness checks around it."""

import json
import re
import time
from pathlib import Path

from browser import agent_browser
from output import redact, tagged

ALLOWED = {"snapshot", "read", "click", "fill"}
ALLOWED_SITE = "https://www.ikea.com/ca/"
REFUSED = ("checkout", "check out", "log out", "sign out")  # the task never needs these, so the harness refuses them
SCREENSHOTS = Path(__file__).parent / "screenshots"
refs = {}  # ref -> role and name, from the latest snapshot


# 1. who_is_signed_in: read the greeting in IKEA's header, which names the signed-in account
def who_is_signed_in(session="demo2"):
    reply = agent_browser("snapshot", "-i", session=session)
    match = re.search(r'link "(Hej[^"]*)"', reply["data"]["snapshot"]) if reply.get("success") else None
    return match.group(1) if match else "unknown"


# 2. cart_count: read the number of items in the cart from IKEA's header
def cart_count():
    reply = agent_browser("snapshot", "-i")
    if not reply.get("success"):
        return None  # the harness could not read the cart
    match = re.search(r'link "Shopping cart, (\d+) item', reply["data"]["snapshot"])
    return int(match.group(1)) if match else 0


# 3. permission: before a command runs, allow it, ask a person, or refuse it. Returns a refusal, or None to go ahead.
def permission(args):
    if not args or args[0] not in ALLOWED or any(arg.startswith("-") for arg in args):
        return "blocked: this harness allows only snapshot, read, click @e3, and fill @e1 text, with no flags."
    url = agent_browser("get", "url").get("data", {}).get("url", "")
    if not url.startswith(ALLOWED_SITE):
        return f"blocked: the page is on {url}, outside IKEA Canada. The harness will not read it or act on it."
    if args[0] in ("click", "fill"):
        ref = args[1].lstrip("@") if len(args) > 1 else ""
        if ref not in refs:
            return f"blocked: {ref or 'no ref'} is not in your latest snapshot. Take a new snapshot."
        name = refs[ref].get("name", "")
        if any(word in name.lower() for word in REFUSED):
            return f'blocked: the task does not permit "{name}".'
        if "to cart" in name.lower():
            answer = input(tagged("approval", f"Claude wants to click: {name}. Allow? [y/N]") + " ").strip().lower()
            print(tagged("approval", "approved" if answer == "y" else "declined"))
            if answer != "y":
                return "blocked: the person did not approve adding this to the cart."
    return None


# 4. verify_cart: re-read the cart count until it goes up, for up to five seconds
def verify_cart(ref, before):
    for _ in range(5):
        time.sleep(1)
        after = cart_count()
        if before is not None and after is not None and after > before:
            break
    added = before is not None and after is not None and after > before
    print(tagged("verify", f"cart: {before} -> {after} items, {'added' if added else 'NOT added'}"))
    return (f"clicked {ref}. The harness checked the cart: {before} items before, {after} after."
            + ("" if added else " The desk was not added."))


# 5. mark: wrap page content in markers with agent-browser's random nonce, so the model can tell it from instructions
def mark(reply, text):
    nonce, origin = reply["_boundary"]["nonce"], reply["_boundary"]["origin"]
    return f"--- PAGE_CONTENT nonce={nonce} origin={origin}\n{redact(text)}\n--- END_PAGE_CONTENT nonce={nonce}"


# 6. run_tool: check permission, run the command, and return marked page content or the checked result
def run_tool(name, tool_input):
    args = tool_input.get("args", [])
    refusal = permission(args)
    if refusal:
        print(tagged("blocked", refusal))
        return refusal
    adds_to_cart = args[0] == "click" and "to cart" in refs[args[1].lstrip("@")].get("name", "").lower()
    before = cart_count() if adds_to_cart else None
    reply = agent_browser(*(["snapshot", "-i"] if args[0] == "snapshot" else args))
    if not reply.get("success"):
        return f"error: {reply.get('error')}"
    data = reply["data"]
    if args[0] == "snapshot":
        refs.clear()
        refs.update(data.get("refs", {}))
        SCREENSHOTS.mkdir(exist_ok=True)  # every snapshot also saves a picture with numbered boxes on the refs
        agent_browser("screenshot", "--annotate", str(SCREENSHOTS / f"{time.strftime('%H%M%S')}.png"))
        return mark(reply, data.get("snapshot", ""))
    if args[0] == "read":
        return mark(reply, data.get("content", ""))
    if adds_to_cart:
        return verify_cart(args[1], before)
    return json.dumps(data)


# 7. The tool definition Claude sees
TOOLS = [{"name": "browser",
          "description": 'Run one agent-browser command in the browser session this harness owns, for example '
                         '["snapshot"], ["read"], ["click", "@e3"], or ["fill", "@e1", "desk"].',
          "input_schema": {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}},
                           "required": ["args"]}}]
