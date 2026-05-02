#!/usr/bin/env python3
"""Cache Layer - Stores analysis summaries to avoid re-reading files."""

import json
import hashlib
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

CACHE_DIR = Path("/opt/ACTIVE/INFRA/SKILLS/token_optimizer/cache")
CACHE_DB = CACHE_DIR / "summaries.db"

# TTL by analysis type (hours)
TTL_CONFIG: Dict[str, int] = {
    "csv_analysis": 24,
    "code_audit": 12,
    "scraper_status": 1,
    "directory_listing": 6,
    "grep_results": 2,
    "default": 12
}


class TokenCache:
    """Cache analysis results - returns summaries, not raw content."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or CACHE_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    path TEXT,
                    analysis_type TEXT,
                    file_hash TEXT,
                    summary TEXT,
                    created_at TIMESTAMP,
                    ttl_hours INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON cache(path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON cache(analysis_type)")

    def _file_hash(self, path: str) -> str:
        """Hash based on path + mtime (fast, no content read)."""
        try:
            stat = Path(path).stat()
            return hashlib.md5(f"{path}:{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()
        except (OSError, FileNotFoundError):
            return hashlib.md5(f"{path}:missing".encode()).hexdigest()

    def _cache_key(self, path: str, analysis_type: str) -> str:
        """Generate unique cache key."""
        return hashlib.md5(f"{path}:{analysis_type}".encode()).hexdigest()

    def get(self, path: str, analysis_type: str = "default") -> Optional[str]:
        """
        Return cached summary if valid, else None.

        Args:
            path: File or directory path that was analyzed
            analysis_type: Type of analysis (csv_analysis, code_audit, etc.)

        Returns:
            Cached summary string or None if cache miss/expired
        """
        key = self._cache_key(path, analysis_type)
        current_hash = self._file_hash(path)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT summary, file_hash, created_at, ttl_hours FROM cache WHERE key = ?",
                (key,)
            ).fetchone()

        if not row:
            return None

        summary, cached_hash, created_at, ttl_hours = row

        # Check file hash (invalidate if file changed)
        if cached_hash != current_hash:
            self.invalidate(path, analysis_type)
            return None

        # Check TTL
        created = datetime.fromisoformat(created_at)
        if datetime.now() - created > timedelta(hours=ttl_hours):
            self.invalidate(path, analysis_type)
            return None

        return summary

    def set(self, path: str, analysis_type: str, summary: str) -> None:
        """
        Store analysis summary.

        Args:
            path: File or directory path that was analyzed
            analysis_type: Type of analysis
            summary: The summary to cache
        """
        key = self._cache_key(path, analysis_type)
        file_hash = self._file_hash(path)
        ttl = TTL_CONFIG.get(analysis_type, TTL_CONFIG["default"])

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache
                (key, path, analysis_type, file_hash, summary, created_at, ttl_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, path, analysis_type, file_hash, summary, datetime.now().isoformat(), ttl))

    def invalidate(self, path: str = None, analysis_type: str = None) -> int:
        """
        Clear cache entries.

        Args:
            path: Invalidate entries for this path (None = all paths)
            analysis_type: Invalidate entries of this type (None = all types)

        Returns:
            Number of entries deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            if path and analysis_type:
                key = self._cache_key(path, analysis_type)
                result = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            elif path:
                result = conn.execute("DELETE FROM cache WHERE path = ?", (path,))
            elif analysis_type:
                result = conn.execute("DELETE FROM cache WHERE analysis_type = ?", (analysis_type,))
            else:
                result = conn.execute("DELETE FROM cache")
            return result.rowcount

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT analysis_type, COUNT(*) FROM cache GROUP BY analysis_type"
            ).fetchall())
            size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_entries": total,
            "by_type": by_type,
            "db_size_kb": size / 1024
        }


def cached_analyze(path: str, analysis_type: str, analyzer_func, *args, **kwargs) -> str:
    """
    Wrapper to cache any analysis function.

    Args:
        path: Path being analyzed
        analysis_type: Type for TTL lookup
        analyzer_func: Function to call on cache miss
        *args, **kwargs: Passed to analyzer_func

    Returns:
        Cached or fresh analysis result
    """
    cache = TokenCache()

    # Check cache first
    cached = cache.get(path, analysis_type)
    if cached:
        return f"[CACHED] {cached}"

    # Run analysis
    result = analyzer_func(path, *args, **kwargs)

    # Cache result
    cache.set(path, analysis_type, result)

    return result


# Integration with exec_runtime
def cached_csv_analyze(path: str) -> str:
    """Cached CSV analysis using exec_runtime."""
    cache = TokenCache()
    cached = cache.get(path, "csv_analysis")
    if cached:
        return f"[CACHED - 0 tokens used]\n{cached}"

    try:
        import sys
        sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
        from exec_runtime import CSVOps

        p = Path(path)
        result = CSVOps.analyze_csvs(p.name, str(p.parent))
        cache.set(path, "csv_analysis", result)
        return result
    except ImportError:
        return f"exec_runtime not available, cannot analyze {path}"


if __name__ == "__main__":
    import sys

    cache = TokenCache()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            print(json.dumps(cache.stats(), indent=2))
        elif cmd == "clear":
            deleted = cache.invalidate()
            print(f"Cleared {deleted} cache entries")
        elif cmd == "get" and len(sys.argv) > 3:
            result = cache.get(sys.argv[2], sys.argv[3])
            print(result or "Cache miss")
    else:
        print("Usage: cache_layer.py [stats|clear|get <path> <type>]")
        print("\nCurrent stats:")
        print(json.dumps(cache.stats(), indent=2))
