"""Display helpers for the audience, not tools Claude can call: the red box around a target, and the --step preview."""

import json

from browser import cdp


# 1. highlight: dim the page and draw a pulsing red box with a label around the element, so everyone sees the target.
#    With no element, as for a snapshot, it shows the label alone. The box is added to the page, hidden from the
#    accessibility tree, and lets clicks pass through.
MARKER = """function (label) {
  const r = this instanceof Element ? this.getBoundingClientRect() : null;
  document.getElementById("claude-target")?.remove();
  const box = document.createElement("div");
  box.id = "claude-target";
  box.setAttribute("aria-hidden", "true");
  Object.assign(box.style, {position: "fixed", boxSizing: "border-box", pointerEvents: "none", zIndex: 2147483647,
    border: "5px solid #ff1f4b", borderRadius: "10px",
    boxShadow: "0 0 0 100vmax rgba(0, 0, 0, 0.6), 0 0 30px 10px #ff1f4b"});
  const tag = document.createElement("div");
  tag.textContent = label;
  Object.assign(tag.style, {padding: "6px 12px", background: "#ff1f4b", color: "white", whiteSpace: "nowrap",
    font: "bold 20px system-ui, sans-serif"});
  if (r) {  // a box around the element, with its label
    Object.assign(box.style, {left: r.left - 8 + "px", top: r.top - 8 + "px",
      width: r.width + 16 + "px", height: r.height + 16 + "px"});
    Object.assign(tag.style, r.top > 50  // near the top of the window, the label goes below the box
      ? {position: "absolute", left: "-5px", bottom: "100%", borderRadius: "8px 8px 0 0"}
      : {position: "absolute", left: "-5px", top: "100%", borderRadius: "0 0 8px 8px"});
  } else {  // no element, such as a snapshot: the label alone, in the middle of the window
    Object.assign(box.style, {left: "0", right: "0", top: "40%", width: "fit-content", margin: "0 auto"});
    Object.assign(tag.style, {font: "bold 28px system-ui, sans-serif", padding: "14px 26px"});
  }
  box.append(tag);
  document.body.append(box);
  box.animate([{transform: "scale(1)"}, {transform: "scale(1.08)"}],
              {duration: 600, direction: "alternate", iterations: Infinity});
}"""


def highlight(node_id, label):
    if node_id is None:
        cdp("Runtime.evaluate", expression=f"({MARKER}).call(null, {json.dumps(label)})")
        return
    element = cdp("DOM.resolveNode", backendNodeId=node_id)["object"]["objectId"]
    cdp("Runtime.callFunctionOn", objectId=element, functionDeclaration=MARKER, arguments=[{"value": label}])


def remove_highlight():
    try:
        cdp("Runtime.evaluate", expression='document.getElementById("claude-target")?.remove()')
    except RuntimeError:  # a page that is still loading has no box to remove
        pass


# 2. preview: with --step, show what Claude asked for and leave it on screen until you press Enter
def preview(name, args, refs):
    labels = {"snapshot": "Claude wants to take a snapshot", "click": "Claude wants to click",
              "type": f'Claude wants to type "{args.get("text", "")}"'}
    node_id = refs.get(args.get("ref"))
    try:
        if node_id:
            cdp("DOM.scrollIntoViewIfNeeded", backendNodeId=node_id)
        highlight(node_id, labels.get(name, f"Claude wants to {name}"))
    except (RuntimeError, TimeoutError):  # the element has gone; run_tool will report it
        pass
