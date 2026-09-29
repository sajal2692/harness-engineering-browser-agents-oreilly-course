"""The Claude agent loop: send the conversation, run the one tool Claude asks for, and send back the result."""

import json
import sys

import anthropic

from output import tagged
from tools import TOOLS, refs, run_tool
from utils import preview

MODEL = "claude-sonnet-5-5"


def run(task, system, step=False):
    # 1. With step on, wait for Enter at each hand-off in the loop
    def pause(message):
        if step:
            input(tagged("step", message) + " ")

    # 2. Send the conversation to Claude. The SDK retries rate limits, overloads, and dropped connections.
    client = anthropic.Anthropic(max_retries=5)
    messages = [{"role": "user", "content": task}]
    pause("Press Enter to send the task to Claude.")
    for turn in range(1, 21):
        try:
            response = client.messages.create(
                model=MODEL, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
                thinking={"type": "adaptive", "display": "summarized"},  # return a summary of Claude's reasoning
                output_config={"effort": "medium"},
                tool_choice={"type": "auto", "disable_parallel_tool_use": True},  # at most one tool call per turn
                cache_control={"type": "ephemeral"},  # reuse the unchanged start of the conversation
            )
        except anthropic.AuthenticationError:
            sys.exit("[error] The API key was rejected. Check ANTHROPIC_API_KEY in .env.")
        except anthropic.APIError as error:
            sys.exit(f"[error] The Claude API call failed: {error}")

        # 3. Show what Claude read, thought, and said, and keep its reply in the conversation
        usage = response.usage
        cached = usage.cache_read_input_tokens or 0
        total = usage.input_tokens + cached + (usage.cache_creation_input_tokens or 0)
        print(f"\n{'─' * 36} turn {turn} {'─' * 36}")
        print(tagged("claude", f"read {total:,} input tokens ({cached:,} from cache) and wrote {usage.output_tokens:,}"))
        for block in response.content:
            if block.type == "thinking" and block.thinking:
                print(tagged("thinking", block.thinking))
            elif block.type == "text":
                print(tagged("claude", block.text))
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            if response.stop_reason != "end_turn":
                print(tagged("stopped", f"Claude stopped early: {response.stop_reason}"))
            return

        # 4. Run the one tool Claude asked for, and send back the result
        call = next(block for block in response.content if block.type == "tool_use")
        print(tagged("claude", f"calls {call.name} {json.dumps(call.input)}"))
        if step:
            preview(call.name, call.input, refs)  # show the call in the browser while you explain it
        pause("Press Enter to run it in the browser.")
        result = run_tool(call.name, call.input)
        lines = result.splitlines()
        print(tagged("result", "\n".join(lines[:12]) + (f"\n... and {len(lines) - 12} more lines" if len(lines) > 12 else "")))
        pause("Press Enter to send the result to Claude.")
        messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": call.id, "content": result}]})
    print(tagged("stopped", "The run reached its limit of 20 turns without an answer."))
