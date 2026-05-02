#!/usr/bin/env python3
"""
RAG Search using LM Studio
Search docs, campaigns, and data using natural language.

Usage:
    python3 rag_search.py "find campaigns targeting Poland"
    python3 rag_search.py "show factory contacts with emails"

# [AI: Claude Code]
Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import sys
import os
import glob
import json
import argparse
from typing import List, Dict, Optional

sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
from lmstudio_client import LMStudioClient, get_embedding, is_lmstudio_available

# Data sources to search
SOURCES = {
    'memory': '/opt/ACTIVE/LLM/MEMORY/*.md',
    'campaigns': '/opt/ACTIVE/EMAIL/CAMPAIGNS/*/state.json',
    'logs': '/opt/ACTIVE/INFRA/LOGS/*.log',
    'data': '/opt/ACTIVE/OPENDATA/DATA/**/*.csv'
}


def load_documents(source_pattern: str, max_docs: int = 50) -> List[Dict]:
    """Load documents from a glob pattern."""
    docs = []
    for filepath in glob.glob(source_pattern, recursive=True)[:max_docs]:
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read()[:5000]  # Limit content size
            docs.append({
                'path': filepath,
                'content': content,
                'name': os.path.basename(filepath)
            })
        except:
            pass
    return docs


def search_with_context(query: str, sources: List[str] = None) -> Optional[str]:
    """Search using LM Studio with document context."""
    if not is_lmstudio_available():
        print("[ERROR] LM Studio not available")
        return None

    # Load documents from specified sources
    all_docs = []
    source_patterns = sources or list(SOURCES.values())

    for pattern in source_patterns:
        docs = load_documents(pattern)
        all_docs.extend(docs)

    if not all_docs:
        print("[WARN] No documents found")
        return None

    # Build context from documents
    context_parts = []
    for doc in all_docs[:20]:  # Limit to 20 docs
        context_parts.append(f"[{doc['name']}]\n{doc['content'][:1000]}")

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""Based on these documents, answer the query.

DOCUMENTS:
{context[:8000]}

QUERY: {query}

Answer concisely based on the documents above:"""

    client = LMStudioClient(timeout=300)
    return client.query(prompt, temperature=0.3, max_tokens=1000)


def simple_search(query: str, source_pattern: str) -> List[Dict]:
    """Simple keyword search in files."""
    results = []
    query_lower = query.lower()

    for filepath in glob.glob(source_pattern, recursive=True):
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read()
            if query_lower in content.lower():
                # Find matching lines
                matches = []
                for i, line in enumerate(content.split('\n')):
                    if query_lower in line.lower():
                        matches.append(f"L{i+1}: {line[:100]}")
                results.append({
                    'path': filepath,
                    'matches': matches[:5]
                })
        except:
            pass

    return results


def main():
    parser = argparse.ArgumentParser(description='RAG Search using LM Studio')
    parser.add_argument('query', help='Search query')
    parser.add_argument('--source', choices=list(SOURCES.keys()),
                        help='Limit to specific source')
    parser.add_argument('--simple', action='store_true',
                        help='Simple keyword search (no LLM)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode')

    args = parser.parse_args()

    if args.test:
        print("Testing LM Studio...")
        if is_lmstudio_available():
            print("[OK] LM Studio available")
            print(f"Sources: {list(SOURCES.keys())}")
        else:
            print("[FAIL] LM Studio not available")
        return

    if args.simple:
        # Keyword search
        pattern = SOURCES.get(args.source, '/opt/**/*')
        results = simple_search(args.query, pattern)
        for r in results:
            print(f"\n{r['path']}:")
            for m in r['matches']:
                print(f"  {m}")
    else:
        # LLM-powered search
        sources = [SOURCES[args.source]] if args.source else None
        result = search_with_context(args.query, sources)
        if result:
            print(result)
        else:
            print("[ERROR] No results")


if __name__ == '__main__':
    main()
