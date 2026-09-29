---
name: agent-browser-course
description: How to use the agent-browser commands this course harness allows. Read before using the browser tool.
---

# agent-browser in the course harness

Adapted from the agent-browser 0.38.1 core skill (vercel-labs/agent-browser, Apache-2.0), cut down
to the commands this task needs.

Call the `browser` tool with one agent-browser command as a list of strings. The harness adds the
session and output flags, so never pass flags yourself.

## Opening a page

`["open", "https://www.ikea.com/ca/en/"]` loads an address. Open only the addresses the task gives
you, then move through the site's menus and links.

## Two views of the page

- `["snapshot"]` lists the elements you can act on, each with a ref shown as `[ref=e3]`. It leaves
  out most plain text, such as prices.
- `["read"]` returns the page's text, including prices and sizes, without refs.

Use `read` to find information and `snapshot` to find the ref you need.

## Acting on a ref

Write the ref with `@`: `["click", "@e3"]` or `["fill", "@e1", "desk"]`. `fill` clears the field,
then types. After a click or fill, the harness tells you what changed on the page and whether the
address changed. Refs stay valid for elements that are still on the page; take a new snapshot when
you need refs for new elements.

## When a command fails

- `Element '@e3' is covered by <...> at its click point` means something sits on top of the target,
  often a dialog, banner, or chat button. No input was sent. Take a snapshot, choose another way to
  the same result, or report what is in the way.
- `denied by policy` or `not in the allowed domains list` means the browser refused the action or
  the site. Do not try to get around it: report it, and carry on with the rest of the task.
