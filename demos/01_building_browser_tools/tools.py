"""The three browser tools Claude can call, snapshot, click, and type, built from CDP commands."""

import itertools
import json
import time

from browser import cdp
from output import tagged
from utils import highlight, remove_highlight

ACTIONABLE = {"link", "button", "textbox", "searchbox", "combobox"}
refs = {}  # ref -> backendDOMNodeId, for the latest snapshot only
ref_numbers = itertools.count(1)


# 1. snapshot: one line per useful node of the accessibility tree; elements you can act on get a ref
def snapshot():
    nodes = cdp("Accessibility.getFullAXTree")["nodes"]
    by_id = {node["nodeId"]: node for node in nodes}
    url = cdp("Runtime.evaluate", expression="location.href")["result"]["value"]
    refs.clear()
    lines = [f"page {url}"]

    def visit(node, inside_named):  # page order: a node, then its children
        role = node.get("role", {}).get("value")
        name = node.get("name", {}).get("value", "").strip()
        if name and not node.get("ignored") and not inside_named:
            if role in ACTIONABLE:
                ref = f"@e{next(ref_numbers)}"
                refs[ref] = node["backendDOMNodeId"]
                value = node.get("value", {}).get("value")
                lines.append(f'{ref} {role} "{name}"' + (f' value="{value}"' if value else ""))
            elif role in ("heading", "StaticText"):
                lines.append(f'{role} "{name}"')
        for child_id in node.get("childIds", []):
            visit(by_id[child_id], inside_named or role in ACTIONABLE or role == "heading")

    visit(nodes[0], False)
    text = "\n".join(lines)
    print(tagged("snapshot", f"Chrome sent {len(nodes):,} nodes ({len(json.dumps(nodes)):,} characters). "
                             f"The model gets {len(lines)} lines ({len(text):,} characters) and {len(refs)} refs."))
    return text


# 2. click: scroll the element into view, find its centre on screen, then move, press, and release the mouse
def click(ref):
    node_id = refs[ref]
    cdp("DOM.scrollIntoViewIfNeeded", backendNodeId=node_id)
    highlight(node_id, "Claude: click")
    time.sleep(1)
    remove_highlight()
    quads = cdp("DOM.getContentQuads", backendNodeId=node_id)["quads"]  # the element's corners on screen
    if not quads:
        return f"error: {ref} has no area on screen, so it cannot be clicked. Take a new snapshot."
    x, y = (quads[0][0] + quads[0][4]) / 2, (quads[0][1] + quads[0][5]) / 2  # halfway between two opposite corners
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
    return f"clicked {ref} at ({x:.0f}, {y:.0f})"


# 3. type: focus the field, select any old text, and insert the new text in its place
def type_text(ref, text):
    cdp("DOM.focus", backendNodeId=refs[ref])
    highlight(refs[ref], f'Claude: type "{text}"')
    time.sleep(1)
    remove_highlight()
    cdp("Runtime.evaluate", expression="document.activeElement.select()")
    cdp("Input.insertText", text=text)
    return f'typed "{text}" into {ref}'


# 4. run_tool: check the ref, run the tool, and turn Chrome's errors into text the model can read
def run_tool(name, args):
    ref = args.get("ref")
    if name in ("click", "type") and ref not in refs:
        return f"error: {ref} is not in the latest snapshot. Take a new snapshot."
    try:
        remove_highlight()  # take down the --step preview from utils.py, if there is one
        if name == "snapshot":
            return snapshot()
        if name == "click":
            return click(ref)
        if name == "type":
            return type_text(ref, args.get("text", ""))
        return f"error: there is no tool called {name}"
    except RuntimeError as error:  # for example, the element has left the page
        return f'error: Chrome said "{error}". Take a new snapshot.'
    except TimeoutError:  # the input may still have reached the page
        return "timeout: Chrome did not answer within 30 seconds. The action may have happened. Take a new snapshot."


# 5. The tool definitions Claude sees
TOOLS = [
    {"name": "snapshot", "description": "Read the current page as text. Elements you can act on have a ref like @e3.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "click", "description": "Click an element, using its ref from the latest snapshot.",
     "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]}},
    {"name": "type", "description": "Replace the text in a field, using its ref from the latest snapshot.",
     "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}, "text": {"type": "string"}},
                      "required": ["ref", "text"]}},
]
