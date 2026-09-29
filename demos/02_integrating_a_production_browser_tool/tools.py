"""The one browser tool Claude can call, backed by agent-browser, and the harness checks around it."""

import tempfile
import time
from pathlib import Path

from browser import agent_browser
from output import tagged
from utils import remove_preview

HARNESS_ONLY = {"eval", "diff", "screenshot", "scrollintoview", "scrollinto", "get", "close"}  # the harness's own helpers
SCREENSHOTS = Path(__file__).parent / "screenshots"
BEFORE = Path(tempfile.gettempdir()) / "demo2-page-before.txt"  # the page as it was before the latest click or fill
refs = {}  # ref -> role and name, from the latest snapshot


# 1. check: before a command runs, refuse flags and the harness's own helpers, and refs not in the latest snapshot.
#    Everything else goes to agent-browser, whose action policy decides.
def check(args):
    if not args or any(arg.startswith("-") for arg in args):
        return "blocked: send one agent-browser command, with no flags."
    if args[0] in HARNESS_ONLY:
        return f"blocked: the harness keeps {args[0]} for itself."
    if args[0] in ("click", "fill") and (len(args) < 2 or args[1].lstrip("@") not in refs):
        return f"blocked: {args[1] if len(args) > 1 else 'no ref'} is not in your latest snapshot. Take a new snapshot."
    return None


# 2. mark: wrap page content in markers with agent-browser's random nonce, so the model can tell it from instructions
def mark(reply, text):
    nonce, origin = reply["_boundary"]["nonce"], reply["_boundary"]["origin"]
    return f"--- PAGE_CONTENT nonce={nonce} origin={origin}\n{text}\n--- END_PAGE_CONTENT nonce={nonce}"


# 3. what_changed: compare the page with the copy saved before the action, using agent-browser's diff
def what_changed(url_before):
    time.sleep(1)  # give the page a moment to react
    diff = agent_browser("diff", "snapshot", "--baseline", str(BEFORE))
    url_after = agent_browser("get", "url").get("data", {}).get("url", "unknown")
    data = diff.get("data", {})
    added, removed = data.get("additions", 0), data.get("removals", 0)
    moved = f"the address changed to {url_after}" if url_after != url_before else f"the address stayed {url_before}"
    summary = f"The harness compared the page before and after: {added} lines added, {removed} removed, and {moved}."
    print(tagged("verify", summary))
    changes = [line for line in data.get("diff", "").splitlines() if line[:1] in "+-" and line[:3] not in ("+++", "---")]
    named = [f"{line[0]} {line[1:].strip()}" for line in changes if '"' in line and "StaticText" not in line]
    named.sort(key=lambda line: "heading" not in line)  # headings first: they say best what the page became
    if named:  # show the room what appeared (+) and disappeared (-), leaving out the page's structure
        more = f"\n... and {len(named) - 8} more named elements" if len(named) > 8 else ""
        print(tagged("diff", "\n".join(line[:100] for line in named[:8]) + more))
    if 0 < added + removed <= 40:  # a small change is worth showing in full
        summary += "\n" + mark(diff, data.get("diff", ""))
    return summary


# 4. run_tool: check the command, run it, and return marked page content or what the action changed
def run_tool(name, tool_input):
    args = tool_input.get("args", [])
    remove_preview()  # take down the --step preview from utils.py, if there is one
    refusal = check(args)
    if refusal:
        print(tagged("blocked", refusal))
        return refusal
    if args[0] in ("click", "fill"):  # save the page first, so the harness can say what the action changed
        before = agent_browser("snapshot")
        BEFORE.write_text(before.get("data", {}).get("snapshot", ""))
        url_before = before.get("data", {}).get("origin", "unknown")
    reply = agent_browser(*(["snapshot", "-i"] if args[0] == "snapshot" else args))
    if not reply.get("success"):
        error = reply.get("error", "")
        if any(reason in error for reason in ("denied by policy", "allowed domains", "covered by")):  # the tool said no
            print(tagged("refused", f"agent-browser refused it: {error}"))
        return f"error: {error}"
    data = reply["data"]
    if args[0] == "snapshot":
        kept = refs.keys() & data.get("refs", {}).keys()  # agent-browser keeps a ref while its element is on the page
        print(tagged("refs", f"{len(kept)} kept from the last snapshot, {len(data.get('refs', {})) - len(kept)} new, "
                             f"{len(refs) - len(kept)} gone"))
        refs.clear()
        refs.update(data.get("refs", {}))
        SCREENSHOTS.mkdir(exist_ok=True)  # every snapshot also saves a picture with numbered boxes on the refs
        agent_browser("screenshot", "--annotate", str(SCREENSHOTS / f"{time.strftime('%H%M%S')}.png"))
        return mark(reply, data.get("snapshot", ""))
    if args[0] == "read":
        return mark(reply, data.get("content", ""))
    if args[0] in ("click", "fill"):
        return f"{' '.join(args)}: done. " + what_changed(url_before)
    return f"{' '.join(args)}: done. The page is now {data.get('url', 'unknown')}."


# 5. The tool definition Claude sees
TOOLS = [{"name": "browser",
          "description": 'Run one agent-browser command in the browser session this harness owns, for example '
                         '["open", "https://example.com"], ["snapshot"], ["read"], ["click", "@e3"], or '
                         '["fill", "@e1", "desk"].',
          "input_schema": {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}},
                           "required": ["args"]}}]
