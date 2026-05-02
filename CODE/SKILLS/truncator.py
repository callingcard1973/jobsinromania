#!/usr/bin/env python3
"""Response Truncator - Auto-truncates verbose tool outputs to save tokens."""

import sys
import json
from typing import Optional

# Token limits by output type (approximate chars, ~4 chars per token)
LIMITS = {
    "bash": 8000,       # ~2000 tokens
    "file_read": 12000, # ~3000 tokens
    "grep": 6000,       # ~1500 tokens
    "csv": 10000,       # ~2500 tokens
    "json": 8000,       # ~2000 tokens
    "log": 4000,        # ~1000 tokens
    "default": 8000     # ~2000 tokens
}

# Minimum content to preserve (don't truncate below this)
MIN_CONTENT = 500


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for code/text)."""
    return len(text) // 4


def truncate(output: str, output_type: str = "default", limit: int = None) -> str:
    """
    Smart truncation preserving useful parts (head + tail + summary).

    Args:
        output: Raw output string
        output_type: Type of output for limit lookup
        limit: Override character limit

    Returns:
        Truncated output with summary
    """
    if not output:
        return output

    char_limit = limit or LIMITS.get(output_type, LIMITS["default"])

    if len(output) <= char_limit:
        return output

    lines = output.split('\n')
    total_lines = len(lines)
    total_chars = len(output)

    # Calculate head/tail sizes (60% head, 30% tail, 10% summary)
    head_chars = int(char_limit * 0.6)
    tail_chars = int(char_limit * 0.3)

    # Build head (keep complete lines)
    head_lines = []
    head_size = 0
    for line in lines:
        if head_size + len(line) + 1 > head_chars:
            break
        head_lines.append(line)
        head_size += len(line) + 1

    # Build tail (keep complete lines)
    tail_lines = []
    tail_size = 0
    for line in reversed(lines):
        if tail_size + len(line) + 1 > tail_chars:
            break
        tail_lines.insert(0, line)
        tail_size += len(line) + 1

    # Avoid overlap
    head_count = len(head_lines)
    tail_start = total_lines - len(tail_lines)
    if head_count >= tail_start:
        # Too much overlap, just return head
        return '\n'.join(head_lines) + f"\n\n... [{total_lines - head_count} more lines truncated]"

    truncated_lines = tail_start - head_count
    chars_saved = total_chars - head_size - tail_size
    tokens_saved = chars_saved // 4

    head = '\n'.join(head_lines)
    tail = '\n'.join(tail_lines)

    return f"""{head}

... [{truncated_lines} lines truncated, ~{tokens_saved} tokens saved] ...

{tail}

[OUTPUT SUMMARY: {total_lines} lines, {total_chars} chars -> {head_size + tail_size} chars shown]"""


def truncate_csv(output: str, max_rows: int = 10) -> str:
    """
    CSV-specific truncation: keep header + sample rows + stats.

    Args:
        output: CSV output string
        max_rows: Maximum data rows to show

    Returns:
        Truncated CSV with header, sample, and stats
    """
    lines = output.strip().split('\n')

    if len(lines) <= max_rows + 1:  # +1 for header
        return output

    header = lines[0]
    data_lines = lines[1:]
    total_rows = len(data_lines)

    # Take first and last rows
    sample_start = data_lines[:max_rows // 2]
    sample_end = data_lines[-(max_rows // 2):]

    result = [header]
    result.extend(sample_start)
    result.append(f"... [{total_rows - max_rows} rows hidden] ...")
    result.extend(sample_end)
    result.append(f"\n[CSV: {total_rows} rows total, showing {max_rows}]")

    return '\n'.join(result)


def truncate_json(output: str, max_items: int = 20) -> str:
    """
    JSON-specific truncation for arrays/objects.

    Args:
        output: JSON string
        max_items: Max items to show in arrays

    Returns:
        Truncated JSON string
    """
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return truncate(output, "json")

    def truncate_recursive(obj, depth=0):
        if depth > 3:
            return "..."

        if isinstance(obj, list):
            if len(obj) > max_items:
                return obj[:max_items // 2] + [f"... {len(obj) - max_items} items hidden ..."] + obj[-max_items // 2:]
            return [truncate_recursive(item, depth + 1) for item in obj]

        if isinstance(obj, dict):
            if len(obj) > max_items:
                keys = list(obj.keys())
                truncated = {k: truncate_recursive(obj[k], depth + 1) for k in keys[:max_items]}
                truncated["..."] = f"{len(obj) - max_items} more keys"
                return truncated
            return {k: truncate_recursive(v, depth + 1) for k, v in obj.items()}

        if isinstance(obj, str) and len(obj) > 500:
            return obj[:250] + "..." + obj[-100:]

        return obj

    truncated = truncate_recursive(data)
    return json.dumps(truncated, indent=2)


def detect_output_type(output: str) -> str:
    """Auto-detect output type from content."""
    first_line = output.split('\n')[0] if output else ""

    # CSV detection
    if ',' in first_line and first_line.count(',') >= 2:
        return "csv"

    # JSON detection
    if output.strip().startswith('{') or output.strip().startswith('['):
        return "json"

    # Log detection
    if any(x in first_line.lower() for x in ['error', 'warning', 'info', 'debug', '[202']):
        return "log"

    return "default"


def auto_truncate(output: str) -> str:
    """Auto-detect type and truncate appropriately."""
    output_type = detect_output_type(output)

    if output_type == "csv":
        return truncate_csv(output)
    elif output_type == "json":
        return truncate_json(output)
    else:
        return truncate(output, output_type)


# PostToolUse hook interface
def process_hook_input():
    """Process input from Claude Code PostToolUse hook."""
    # Hook passes JSON on stdin
    try:
        hook_input = json.load(sys.stdin)
        tool_name = hook_input.get("tool_name", "").lower()
        tool_output = hook_input.get("tool_output", "")

        # Map tool name to output type
        type_map = {
            "bash": "bash",
            "read": "file_read",
            "grep": "grep"
        }
        output_type = type_map.get(tool_name, "default")

        # Truncate if needed
        truncated = truncate(tool_output, output_type)

        # Return modified output
        print(json.dumps({"tool_output": truncated}))

    except (json.JSONDecodeError, KeyError):
        # Passthrough on error
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # File mode: truncate file contents
        with open(sys.argv[1]) as f:
            content = f.read()
        output_type = sys.argv[2] if len(sys.argv) > 2 else "default"
        print(truncate(content, output_type))
    elif not sys.stdin.isatty():
        # Pipe mode: truncate stdin
        content = sys.stdin.read()
        print(auto_truncate(content))
    else:
        # Demo mode
        demo = "Line " + "\nLine ".join(str(i) for i in range(1, 201))
        print("=== Demo: 200 lines truncated ===")
        print(truncate(demo, "bash"))
