#!/usr/bin/env python3
"""
Extract Functions Example - Move utility functions to separate file
Token savings: ~800 tokens vs ~15,000 tokens traditionally (94.7% reduction)

Usage:
    python3 extract_functions.py /path/to/code function_pattern output_file.py
"""
import sys
import os
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from exec_runtime import CodeTransform, BulkOps

def extract_functions(path: str, pattern: str, output_file: str):
    """
    Find functions matching pattern and generate extraction plan.

    This demonstrates the Anthropic code execution pattern:
    - Find all functions matching pattern (metadata only)
    - Generate extraction plan
    - Return actionable summary
    """
    print(f"Finding functions matching '{pattern}' in {path}")
    print("=" * 60)

    # Find matching functions
    functions = CodeTransform.find_functions(path, '**/*.py', name_filter=pattern)

    if not functions:
        print(f"No functions found matching '{pattern}'")
        return

    print(f"Found {len(functions)} functions:\n")

    # Group by file
    by_file = {}
    for func in functions:
        file_path = func['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(func)

    # Print extraction plan
    print("EXTRACTION PLAN:")
    print("-" * 40)

    for file_path, funcs in by_file.items():
        print(f"\nFrom: {file_path}")
        for func in funcs:
            args = ', '.join(func['args']) if func['args'] else ''
            async_prefix = 'async ' if func.get('is_async') else ''
            print(f"  Line {func['line']}: {async_prefix}def {func['name']}({args})")

    # Generate output file template
    print(f"\n{'=' * 60}")
    print(f"OUTPUT FILE: {output_file}")
    print("=" * 60)

    template_lines = [
        '#!/usr/bin/env python3',
        '"""',
        f'Extracted utility functions matching "{pattern}"',
        f'Source: {path}',
        '"""',
        '',
    ]

    # Collect unique imports needed
    imports_needed = set()
    for func in functions:
        if func.get('is_async'):
            imports_needed.add('import asyncio')

    if imports_needed:
        template_lines.extend(sorted(imports_needed))
        template_lines.append('')

    template_lines.append('# TODO: Copy function implementations from source files')
    template_lines.append('')

    for func in functions:
        args = ', '.join(func['args']) if func['args'] else ''
        async_prefix = 'async ' if func.get('is_async') else ''
        template_lines.append(f'{async_prefix}def {func["name"]}({args}):')
        template_lines.append(f'    """From {func["file"]}:{func["line"]}"""')
        template_lines.append('    pass  # TODO: Copy implementation')
        template_lines.append('')

    template = '\n'.join(template_lines)
    print(template)

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Functions to extract: {len(functions)}")
    print(f"Source files: {len(by_file)}")
    print(f"Output file: {output_file}")
    print("\nNext steps:")
    print("1. Review the extraction plan above")
    print("2. Copy function implementations from source files")
    print("3. Update imports in source files to use new module")
    print("4. Run tests to verify")

    return {
        'functions': len(functions),
        'source_files': len(by_file),
        'output_file': output_file
    }

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: extract_functions.py <path> <pattern> <output_file>")
        print("\nExample:")
        print("  extract_functions.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE fetch utils/fetchers.py")
        print("  extract_functions.py /opt/ACTIVE/INFRA/SKILLS parse helpers/parsers.py")
        sys.exit(1)

    path = sys.argv[1]
    pattern = sys.argv[2]
    output_file = sys.argv[3]

    extract_functions(path, pattern, output_file)
