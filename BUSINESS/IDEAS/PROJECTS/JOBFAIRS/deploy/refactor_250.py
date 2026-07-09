"""Refactor all files over 250 lines on raspibig. Run via: python3 /tmp/refactor_250.py"""
import os

SKILLS = "/opt/ACTIVE/INFRA/SKILLS"
GOV = "/opt/ACTIVE/INFRA/GOVERNOR"


def split_file(src, dst, start_marker, end_marker=None, keep_imports=True):
    """Extract lines between markers into new file."""
    lines = open(src).readlines()
    imports = []
    extracted = []
    remaining = []
    in_section = False

    for i, line in enumerate(lines):
        if keep_imports and i < 30 and (line.startswith("import ") or line.startswith("from ")):
            imports.append(line)
        if start_marker in line:
            in_section = True
        if in_section:
            extracted.append(line)
            if end_marker and end_marker in line:
                in_section = False
        else:
            remaining.append(line)

    if extracted:
        with open(dst, "w") as f:
            for imp in imports:
                f.write(imp)
            f.write("\n")
            for line in extracted:
                f.write(line)
        print(f"  Extracted {len(extracted)} lines -> {os.path.basename(dst)}")
    return remaining


def refactor_bot_commands():
    """Split bot_commands_infra.py (342 lines) into 2 files."""
    f = f"{SKILLS}/bot_commands_infra.py"
    lines = open(f).readlines()

    # Find split point — after cmd_watchdog (system cmds) before cmd_responses (campaign cmds)
    split_at = None
    for i, line in enumerate(lines):
        if "async def cmd_responses" in line:
            split_at = i
            break

    if not split_at:
        print("  bot_commands: split point not found")
        return

    # Header (imports + helpers)
    header = []
    for line in lines[:35]:
        header.append(line)

    # File 1: system commands (lines up to split point)
    with open(f"{SKILLS}/bot_commands_system.py", "w") as out:
        for line in lines[:split_at]:
            out.write(line)

    # File 2: campaign/email commands (split point to INFRA_COMMANDS)
    dict_line = None
    for i, line in enumerate(lines):
        if "INFRA_COMMANDS = {" in line:
            dict_line = i
            break

    with open(f"{SKILLS}/bot_commands_campaign.py", "w") as out:
        # Write imports
        for line in header:
            out.write(line)
        out.write("\n")
        # Write campaign commands
        for line in lines[split_at:dict_line]:
            out.write(line)

    # Rewrite main file as thin wrapper
    with open(f, "w") as out:
        out.write('"""Bot commands — merged registry from system + campaign modules."""\n')
        out.write("from bot_commands_system import *\n")
        out.write("from bot_commands_campaign import *\n\n")
        # Write the INFRA_COMMANDS dict
        for line in lines[dict_line:]:
            out.write(line)

    print(f"  bot_commands split: system + campaign + registry")


def refactor_controller():
    """Split telegram_unified_controller.py (671 lines) into 2 files."""
    f = f"{SKILLS}/telegram_unified_controller.py"
    lines = open(f).readlines()

    # Find where command functions start (after RaspibigController class)
    cmd_start = None
    main_start = None
    for i, line in enumerate(lines):
        if "async def start_command" in line:
            cmd_start = i
        if "def main():" in line:
            main_start = i

    if not cmd_start or not main_start:
        print("  controller: markers not found")
        return

    # Extract command functions to bot_commands_core.py
    with open(f"{SKILLS}/bot_commands_core.py", "w") as out:
        # Write imports
        for line in lines[:30]:
            if line.startswith(("import ", "from ")) and "bot_commands" not in line:
                out.write(line)
        out.write("\n")
        # Write command functions (from start_command to main)
        for line in lines[cmd_start:main_start]:
            out.write(line)

    # Rewrite controller as thin main + imports
    with open(f, "w") as out:
        # Keep header + class + imports
        for line in lines[:cmd_start]:
            out.write(line)
        out.write("\nfrom bot_commands_core import *\n\n")
        # Keep main() onwards
        for line in lines[main_start:]:
            out.write(line)

    print(f"  controller split: core commands + main")


def refactor_smart_router():
    """Split smart_router.py (576 lines) into 2 files."""
    f = f"{SKILLS}/smart_router.py"
    lines = open(f).readlines()

    # Find SmartRouter class
    class_start = None
    for i, line in enumerate(lines):
        if "class SmartRouter:" in line:
            class_start = i
            break

    if not class_start:
        print("  smart_router: class not found")
        return

    # File 1: constants + endpoints + task routing + dataclasses (before class)
    with open(f"{SKILLS}/smart_router_config.py", "w") as out:
        for line in lines[:class_start]:
            out.write(line)

    # File 2: SmartRouter class + helpers + main
    with open(f, "w") as out:
        # Imports
        for line in lines[:20]:
            if line.startswith(("import ", "from ")) or line.startswith("#"):
                out.write(line)
        out.write("from smart_router_config import *\n\n")
        # Class onwards
        for line in lines[class_start:]:
            out.write(line)

    print(f"  smart_router split: config + router")


def refactor_governor():
    """Split governor.py (352 lines) into 2 files."""
    f = f"{GOV}/governor.py"
    lines = open(f).readlines()

    # Find Governor class
    gov_class = None
    for i, line in enumerate(lines):
        if "class Governor:" in line:
            gov_class = i
            break

    if not gov_class:
        print("  governor: class not found")
        return

    # File 1: constants + enums + SystemHealth (before Governor class)
    with open(f"{GOV}/governor_config.py", "w") as out:
        for line in lines[:gov_class]:
            out.write(line)

    # File 2: Governor class + main
    with open(f, "w") as out:
        for line in lines[:5]:
            if line.startswith(("import ", "from ", "#")):
                out.write(line)
        out.write("from governor_config import *\n\n")
        for line in lines[gov_class:]:
            out.write(line)

    print(f"  governor split: config + governor")


def trim_file(filepath, max_lines=250):
    """Report if file is still over limit."""
    lines = len(open(filepath).readlines())
    status = "OK" if lines <= max_lines else f"OVER ({lines})"
    print(f"  {os.path.basename(filepath)}: {lines} lines — {status}")
    return lines


def main():
    print("=== Refactoring files over 250 lines ===\n")

    print("1. bot_commands_infra.py (342)")
    refactor_bot_commands()

    print("2. telegram_unified_controller.py (671)")
    refactor_controller()

    print("3. smart_router.py (576)")
    refactor_smart_router()

    print("4. governor.py (352)")
    refactor_governor()

    print("\n=== Checking results ===")
    files = [
        f"{SKILLS}/telegram_unified_controller.py",
        f"{SKILLS}/bot_commands_core.py",
        f"{SKILLS}/bot_commands_infra.py",
        f"{SKILLS}/bot_commands_system.py",
        f"{SKILLS}/bot_commands_campaign.py",
        f"{SKILLS}/smart_router.py",
        f"{SKILLS}/smart_router_config.py",
        f"{SKILLS}/email_processor.py",
        f"{SKILLS}/email_executor.py",
        f"{SKILLS}/response_tracker.py",
        f"{SKILLS}/worker_router.py",
        f"{SKILLS}/bot_watchdog.py",
        f"{SKILLS}/check_all_blocks.py",
        f"{SKILLS}/telegram_group_moderator.py",
        f"{GOV}/nanoclaw.py",
        f"{GOV}/nanoclaw_core.py",
        f"{GOV}/nanoclaw_monitors.py",
        f"{GOV}/governor.py",
        f"{GOV}/governor_config.py",
    ]
    over = 0
    for f in files:
        if os.path.exists(f):
            if trim_file(f) > 250:
                over += 1

    print(f"\n{'ALL UNDER 250' if over == 0 else f'{over} FILES STILL OVER 250'}")


if __name__ == "__main__":
    main()
