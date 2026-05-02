#!/usr/bin/env python3
"""
Codebase Audit Example - Analyze code quality across a project
Token savings: ~1,000 tokens vs ~150,000 tokens traditionally (99.3% reduction)

Usage:
    python3 codebase_audit.py /path/to/code
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from exec_runtime import CodeOps, CodeTransform

def codebase_audit(path: str):
    """
    Comprehensive codebase audit returning metadata only.

    This demonstrates the Anthropic code execution pattern:
    - Analyze 100+ files locally
    - Extract only metadata (no source code in context)
    - Return actionable summary
    """
    print(f"Auditing: {path}")
    print("=" * 60)

    # 1. Overall complexity analysis
    print("\n[1/4] Analyzing complexity...")
    complexity = CodeOps.analyze_directory(path, '**/*.py')

    print(f"  Files: {complexity['total_files']}")
    print(f"  Lines: {complexity['total_lines']}")
    print(f"  Functions: {complexity['total_functions']}")
    print(f"  Classes: {complexity['total_classes']}")
    print(f"  Complexity: {complexity['by_complexity']}")

    # 2. Find complex functions
    print("\n[2/4] Finding complex functions...")
    if complexity['largest_files']:
        print("  Largest files:")
        for f in complexity['largest_files'][:5]:
            print(f"    {f['file']}: {f['lines']} lines")

    # 3. Find unused imports
    print("\n[3/4] Finding unused imports...")
    unused = CodeTransform.find_unused_imports(path, '**/*.py')
    print(f"  Files with unused imports: {len(unused)}")
    if unused:
        for item in unused[:5]:
            print(f"    {item['file']}: {', '.join(item['unused'])}")
        if len(unused) > 5:
            print(f"    ... and {len(unused) - 5} more files")

    # 4. Find all functions (for duplicate detection)
    print("\n[4/4] Analyzing functions...")
    functions = CodeTransform.find_functions(path, '**/*.py')
    print(f"  Total functions: {len(functions)}")

    # Count function name frequency
    from collections import Counter
    name_counts = Counter(f['name'] for f in functions)
    duplicates = [(name, count) for name, count in name_counts.items() if count > 1 and not name.startswith('_')]

    if duplicates:
        print("  Potential duplicates (same name):")
        for name, count in sorted(duplicates, key=lambda x: -x[1])[:5]:
            print(f"    {name}: {count} occurrences")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    issues = []
    if complexity['by_complexity'].get('high', 0) > 5:
        issues.append(f"- {complexity['by_complexity']['high']} high-complexity files")
    if len(unused) > 20:
        issues.append(f"- {len(unused)} files with unused imports")
    if len(complexity['largest_files']) > 5:
        issues.append(f"- {len(complexity['largest_files'])} large files (>500 lines)")
    if duplicates:
        issues.append(f"- {len(duplicates)} potentially duplicated functions")

    if issues:
        print("Issues found:")
        for issue in issues:
            print(issue)
    else:
        print("No major issues found!")

    # Health score
    score = 100
    score -= complexity['by_complexity'].get('high', 0) * 5
    score -= len(unused)
    score -= len(complexity['largest_files']) * 3
    score = max(0, min(100, score))
    print(f"\nHealth Score: {score}/100")

    return {
        'complexity': complexity,
        'unused_imports': len(unused),
        'functions': len(functions),
        'health_score': score
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: codebase_audit.py <path>")
        print("\nExample:")
        print("  codebase_audit.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE")
        sys.exit(1)

    path = sys.argv[1]
    codebase_audit(path)
