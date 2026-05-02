#!/usr/bin/env python3
"""
General Brainstorming - Structured design for any feature
Usage: python3 brainstorm.py [scraper|campaign|feature] [--interactive]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import subprocess
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path('/opt/ACTIVE/SCRAPERS/EUROPE/docs/plans')

MODES = {
    'scraper': {
        'script': '/opt/ACTIVE/INFRA/SKILLS/brainstorm_scraper.py',
        'desc': 'Design a new web scraper'
    },
    'campaign': {
        'script': '/opt/ACTIVE/INFRA/SKILLS/brainstorm_campaign.py',
        'desc': 'Plan an email campaign'
    },
    'feature': {
        'script': None,  # Built-in
        'desc': 'Design a general feature'
    }
}

FEATURE_QUESTIONS = {
    'category': {
        'q': 'What category is this feature?',
        'opts': ['Scraper enhancement', 'Email system', 'Data processing', 'Monitoring/alerts', 'Integration', 'Other']
    },
    'problem': {
        'q': 'What problem does this solve?',
        'opts': ['Missing functionality', 'Performance issue', 'Manual task automation', 'Data quality', 'User request']
    },
    'scope': {
        'q': 'What is the scope?',
        'opts': ['Single script', 'Multiple files', 'Cross-system (raspibig+raspi)', 'New system/module']
    },
    'priority': {
        'q': 'Priority level?',
        'opts': ['Critical (blocking work)', 'High (needed soon)', 'Medium (nice to have)', 'Low (future improvement)']
    },
    'complexity': {
        'q': 'Estimated complexity?',
        'opts': ['Simple (< 1 hour)', 'Medium (1-4 hours)', 'Complex (1-2 days)', 'Large (week+)']
    },
    'dependencies': {
        'q': 'External dependencies?',
        'opts': ['None - standalone', 'New Python packages', 'External API', 'Database changes', 'Multiple systems']
    }
}

def show_menu():
    """Show available modes"""
    print(f"\n{'='*60}")
    print("BRAINSTORMING SKILL")
    print(f"{'='*60}\n")
    print("Available modes:\n")
    for mode, info in MODES.items():
        print(f"  {mode:12} - {info['desc']}")
    print(f"\nUsage: brainstorm.py <mode> [--interactive]")
    print(f"       brainstorm.py feature --interactive")

def run_specialized(mode):
    """Run a specialized brainstorming script"""
    script = MODES[mode]['script']
    if script and Path(script).exists():
        subprocess.run(['/opt/ACTIVE/INFRA/venv/bin/python3', script, '--interactive'])
    else:
        print(f"Script not found: {script}")

def feature_interactive():
    """Run feature brainstorming"""
    print(f"\n{'='*60}")
    print("FEATURE DESIGN BRAINSTORMING")
    print(f"{'='*60}\n")

    answers = {}

    # Get feature name first
    answers['name'] = input("Feature name (short): ").strip() or "unnamed_feature"
    answers['description'] = input("Brief description: ").strip() or "TBD"

    for key, item in FEATURE_QUESTIONS.items():
        print(f"\n{item['q']}")
        for i, opt in enumerate(item['opts'], 1):
            print(f"  {i}. {opt}")

        while True:
            try:
                choice = input(f"\nChoice [1-{len(item['opts'])}]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(item['opts']):
                    answers[key] = item['opts'][int(choice)-1]
                    break
                elif choice:
                    answers[key] = choice
                    break
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return None

    # Explore approaches
    print("\n" + "="*60)
    print("EXPLORING APPROACHES")
    print("="*60)

    approaches = []
    print("\nDescribe up to 3 possible approaches (Enter to skip):\n")

    for i in range(1, 4):
        approach = input(f"Approach {i}: ").strip()
        if approach:
            pros = input(f"  Pros: ").strip() or "TBD"
            cons = input(f"  Cons: ").strip() or "TBD"
            approaches.append({'name': approach, 'pros': pros, 'cons': cons})
        else:
            break

    answers['approaches'] = approaches

    # Get recommendation
    if approaches:
        print(f"\nWhich approach do you recommend? [1-{len(approaches)}]: ", end='')
        rec = input().strip()
        if rec.isdigit() and 1 <= int(rec) <= len(approaches):
            answers['recommended'] = int(rec) - 1
        else:
            answers['recommended'] = 0

    return answers

def generate_feature_design(answers):
    """Generate feature design document"""
    date = datetime.now().strftime('%Y-%m-%d')
    name = answers.get('name', 'feature')

    # Build approaches section
    approaches_text = ""
    for i, app in enumerate(answers.get('approaches', []), 1):
        rec = " **(RECOMMENDED)**" if i-1 == answers.get('recommended', -1) else ""
        approaches_text += f"""
### Approach {i}: {app['name']}{rec}
- **Pros**: {app['pros']}
- **Cons**: {app['cons']}
"""

    design = f"""# Feature Design: {answers.get('name', 'Unnamed')}
Generated: {date}

## Overview
**Description**: {answers.get('description', 'TBD')}

## Analysis

| Aspect | Value |
|--------|-------|
| Category | {answers.get('category', 'TBD')} |
| Problem | {answers.get('problem', 'TBD')} |
| Scope | {answers.get('scope', 'TBD')} |
| Priority | {answers.get('priority', 'TBD')} |
| Complexity | {answers.get('complexity', 'TBD')} |
| Dependencies | {answers.get('dependencies', 'TBD')} |

## Approaches Considered
{approaches_text if approaches_text else "No approaches documented yet."}

## Implementation Plan

### Phase 1: Setup
- [ ] Create feature branch or directory
- [ ] Install dependencies if needed
- [ ] Set up test environment

### Phase 2: Core Implementation
- [ ] Implement main functionality
- [ ] Add error handling
- [ ] Add logging

### Phase 3: Integration
- [ ] Integrate with existing systems
- [ ] Add to Node-RED if scheduled
- [ ] Update CLAUDE.md documentation

### Phase 4: Validation
- [ ] Test with small dataset
- [ ] Full test run
- [ ] Monitor for issues

## Files to Create/Modify

```
/opt/ACTIVE/INFRA/SKILLS/{name}.py          # Main script (if applicable)
/opt/ACTIVE/INFRA/SKILLS/CLAUDE.md          # Update documentation
~/.node-red/flows.json         # Add to Node-RED (if scheduled)
```

## Success Criteria

- [ ] Feature works as described
- [ ] No errors in logs
- [ ] Documentation updated
- [ ] Added to monitoring if applicable

## Rollback Plan

If issues arise:
1. Disable in Node-RED (if scheduled)
2. Revert file changes
3. Document issue for future reference

---
Design generated by /opt/ACTIVE/INFRA/SKILLS/brainstorm.py
"""
    return design, name

def save_design(design, name):
    """Save design document"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')
    filename = DOCS_DIR / f"{date}-{name}-design.md"

    with open(filename, 'w') as f:
        f.write(design)

    return filename

def main():
    args = sys.argv[1:]

    if not args:
        show_menu()
        sys.exit(0)

    mode = args[0].lower()

    if mode not in MODES:
        print(f"Unknown mode: {mode}")
        show_menu()
        sys.exit(1)

    if mode in ['scraper', 'campaign']:
        run_specialized(mode)
    elif mode == 'feature':
        answers = feature_interactive()
        if answers:
            design, name = generate_feature_design(answers)
            filepath = save_design(design, name)
            print(f"\n{'='*60}")
            print("FEATURE DESIGN GENERATED")
            print(f"{'='*60}")
            print(design)
            print(f"\nSaved to: {filepath}")

if __name__ == '__main__':
    main()
