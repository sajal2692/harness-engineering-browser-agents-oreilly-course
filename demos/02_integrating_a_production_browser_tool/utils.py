"""Display helpers for the audience, not tools Claude can call: the --step preview of what Claude asked for."""

import base64
import json

from browser import agent_browser


# 1. preview: with --step, dim the page and show what Claude asked for until you press Enter: a pulsing red
#    box around the element for click and fill, or the label alone otherwise. run_tool removes it.
MARKER = """(([r, label]) => {
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
})(ARGS)"""


def preview(name, tool_input, refs):
    args = tool_input.get("args", [])
    labels = {"open": f"Claude wants to open {args[1] if len(args) > 1 else 'a page'}",
              "snapshot": "Claude wants to take a snapshot", "read": "Claude wants to read the page text",
              "click": "Claude wants to click", "fill": f'Claude wants to type "{" ".join(args[2:])}"'}
    label = labels.get(args[0], f'Claude wants to run "{" ".join(args)}"') if args else "Claude sent no command"
    box = None
    if len(args) > 1 and args[0] in ("click", "fill") and args[1].lstrip("@") in refs:
        agent_browser("scrollintoview", args[1])
        box = agent_browser("get", "box", args[1]).get("data", {})  # position in the window, after scrolling
        box = {"left": box["x"], "top": box["y"], "width": box["width"], "height": box["height"]} if "x" in box else None
    script = MARKER.replace("ARGS", json.dumps([box, label]))
    agent_browser("eval", "-b", base64.b64encode(script.encode()).decode())


# 2. remove_preview: take the label off the page before the command runs
def remove_preview():
    agent_browser("eval", 'document.getElementById("claude-target")?.remove()')
