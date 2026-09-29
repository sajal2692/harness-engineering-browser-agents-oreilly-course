---
name: agent-browser-course
description: How to use the agent-browser commands this course harness allows. Read before using the browser tool.
---

# agent-browser in the course harness

Adapted from the agent-browser 0.38.1 core skill (vercel-labs/agent-browser, Apache-2.0), cut down
to the four commands this harness allows.

Call the `browser` tool with one agent-browser command as a list of strings. The harness adds the
session and output flags, so never pass flags yourself.

## Two views of the page

- `["snapshot"]` lists the elements you can act on, each with a ref shown as `[ref=e3]`. It leaves
  out most plain text, such as prices.
- `["read"]` returns the page's text, including prices and sizes, without refs.

Use `read` to find information and `snapshot` to find the ref you need.

## Acting on a ref

Write the ref with `@`: `["click", "@e3"]` or `["fill", "@e1", "desk"]`. `fill` clears the field,
then types. Take a new snapshot after every click or fill to see what changed. Refs stay valid for
elements that are still on the page.

## When a click fails

`Element '@e3' is covered by <...> at its click point` means something sits on top of the target,
often a dialog, banner, or chat button. No input was sent. Take a snapshot, choose another way to
the same result, or report what is in the way.
