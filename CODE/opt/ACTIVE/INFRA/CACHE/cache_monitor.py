#!/usr/bin/env python3
"""
Simple Cache Monitor for Redis infrastructure
"""

import json
import time
from datetime import datetime
from cache_manager import cache

def check_cache_health():
    """Check cache system health"""
    try:
        health = cache.health_check()
        stats = cache.get_cache_stats()

        # Get Redis memory info
        memory_info = cache.redis_client.info('memory')

        return {
            'timestamp': datetime.now().isoformat(),
            'redis_healthy': health.get('redis_connection', False),
            'postgres_healthy': health.get('postgresql_connection', False),
            'overall_healthy': health.get('overall_health', False),
            'memory_usage': memory_info.get('used_memory_human', '0B'),
            'fragmentation_ratio': memory_info.get('mem_fragmentation_ratio', 1.0),
            'total_keys': cache.redis_client.info().get('db0', {}).get('keys', 0),
            'ops_per_sec': cache.redis_client.info('stats').get('instantaneous_ops_per_sec', 0)
        }

    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'overall_healthy': False
        }

def export_metrics():
    """Export metrics for monitoring"""
    health = check_cache_health()

    # Save to metrics file
    metrics_file = '/opt/ACTIVE/INFRA/PERFORMANCE/metrics/redis_cache_metrics.json'
    try:
        with open(metrics_file, 'w') as f:
            json.dump(health, f, indent=2)
        print(f"Metrics exported to {metrics_file}")
    except Exception as e:
        print(f"Failed to export metrics: {e}")

    return health

if __name__ == '__main__':
    print("Redis Cache Monitor")
    print("=" * 40)

    health = export_metrics()

    print(f"Overall Health: {health.get('overall_healthy', False)}")
    print(f"Redis: {health.get('redis_healthy', False)}")
    print(f"PostgreSQL: {health.get('postgres_healthy', False)}")
    print(f"Memory Usage: {health.get('memory_usage', 'N/A')}")
    print(f"Total Keys: {health.get('total_keys', 0)}")
    print(f"Ops/sec: {health.get('ops_per_sec', 0)}")

    if not health.get('overall_healthy', False):
        print(f"ERROR: {health.get('error', 'Unknown issue')}")