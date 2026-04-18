#!/usr/bin/env python3
"""
Redis Cache Manager for raspibig infrastructure
Comprehensive caching layer for high-volume database queries
"""

import json
import hashlib
import logging
import time
from typing import Optional, Union, List, Dict, Any
from datetime import datetime, timedelta
from functools import wraps
import redis
import psycopg2
import psycopg2.extras

class CacheManager:
    """Production-ready Redis caching layer for PostgreSQL queries"""

    def __init__(self, redis_host='127.0.0.1', redis_port=6379, redis_db=0,
                 pg_host='localhost', pg_user='tudor', pg_password='tudor', pg_db='interjob_master'):
        """Initialize cache manager with Redis and PostgreSQL connections"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30
        )

        # PostgreSQL connection parameters
        self.pg_config = {
            'host': pg_host,
            'user': pg_user,
            'password': pg_password,
            'database': pg_db,
            'cursor_factory': psycopg2.extras.RealDictCursor
        }

        # Cache configuration
        self.default_ttl = {
            'company_lookup': 3600,      # 1 hour for company data
            'contact_list': 1800,        # 30 min for contact lists
            'campaign_data': 600,        # 10 min for active campaigns
            'dashboard_stats': 300,      # 5 min for dashboard aggregations
            'scraper_cache': 7200,       # 2 hours for scraper results
            'email_validation': 86400,   # 24 hours for email validation
            'system_config': 3600,       # 1 hour for system settings
            'metadata': 1800             # 30 min for metadata
        }

        # Performance tracking
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_queries': 0
        }

        # Setup logging
        self.logger = logging.getLogger('CacheManager')

    def _generate_key(self, query: str, params: tuple = ()) -> str:
        """Generate consistent cache key from query and parameters"""
        # Create unique key from query + params
        key_data = f"{query}::{str(params)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"cache:{key_hash}"

    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        try:
            return json.dumps(data, default=str, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Serialization error: {e}")
            return json.dumps({"error": "serialization_failed"})

    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from Redis"""
        try:
            return json.loads(data)
        except Exception as e:
            self.logger.error(f"Deserialization error: {e}")
            return None

    def get_cached_query(self, query: str, params: tuple = (), cache_type: str = 'metadata') -> Optional[Any]:
        """Retrieve cached query result"""
        try:
            self.stats['total_queries'] += 1
            cache_key = self._generate_key(query, params)

            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                self.stats['hits'] += 1
                self.logger.debug(f"Cache HIT for key: {cache_key[:20]}...")
                return self._deserialize_data(cached_data)
            else:
                self.stats['misses'] += 1
                self.logger.debug(f"Cache MISS for key: {cache_key[:20]}...")
                return None

        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Cache retrieval error: {e}")
            return None

    def set_cached_query(self, query: str, params: tuple, result: Any, cache_type: str = 'metadata') -> bool:
        """Store query result in cache"""
        try:
            cache_key = self._generate_key(query, params)
            ttl = self.default_ttl.get(cache_type, self.default_ttl['metadata'])

            serialized_data = self._serialize_data(result)
            success = self.redis_client.setex(cache_key, ttl, serialized_data)

            if success:
                self.logger.debug(f"Cache SET for key: {cache_key[:20]}... (TTL: {ttl}s)")

            return bool(success)

        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Cache storage error: {e}")
            return False

    def execute_cached_query(self, query: str, params: tuple = (), cache_type: str = 'metadata') -> Optional[List[Dict]]:
        """Execute PostgreSQL query with automatic caching"""
        # Check cache first
        cached_result = self.get_cached_query(query, params, cache_type)
        if cached_result is not None:
            return cached_result

        # Execute query
        try:
            with psycopg2.connect(**self.pg_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchall()

                    # Convert to list of dicts
                    result_list = [dict(row) for row in result]

                    # Cache the result
                    self.set_cached_query(query, params, result_list, cache_type)

                    return result_list

        except Exception as e:
            self.logger.error(f"Database query error: {e}")
            self.stats['errors'] += 1
            return None

    def get_companies_by_country(self, country_code: str) -> Optional[List[Dict]]:
        """Get companies by country with caching"""
        query = """
            SELECT country, COUNT(*) as company_count,
                   COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email
            FROM companies
            WHERE country = %s
            GROUP BY country
        """
        return self.execute_cached_query(query, (country_code,), 'company_lookup')

    def get_dashboard_stats(self) -> Optional[Dict]:
        """Get dashboard statistics with caching"""
        queries = {
            'total_companies': "SELECT COUNT(*) as count FROM companies",
            'companies_with_email': "SELECT COUNT(*) as count FROM companies WHERE email IS NOT NULL",
            'companies_by_country': """
                SELECT country, COUNT(*) as count
                FROM companies
                WHERE country IS NOT NULL
                GROUP BY country
                ORDER BY count DESC
                LIMIT 10
            """
        }

        stats = {}
        for key, query in queries.items():
            result = self.execute_cached_query(query, (), 'dashboard_stats')
            if result:
                if key == 'companies_by_country':
                    stats[key] = result
                else:
                    stats[key] = result[0]['count'] if result else 0

        return stats if stats else None

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        try:
            keys = self.redis_client.keys(f"cache:*{pattern}*")
            if keys:
                deleted = self.redis_client.delete(*keys)
                self.logger.info(f"Invalidated {deleted} cache entries matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            self.logger.error(f"Cache invalidation error: {e}")
            return 0

    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        try:
            redis_info = self.redis_client.info('memory')
            redis_stats = self.redis_client.info('stats')

            hit_rate = (self.stats['hits'] / max(self.stats['total_queries'], 1)) * 100

            return {
                'performance': {
                    'hit_rate': f"{hit_rate:.2f}%",
                    'total_queries': self.stats['total_queries'],
                    'cache_hits': self.stats['hits'],
                    'cache_misses': self.stats['misses'],
                    'errors': self.stats['errors']
                },
                'redis_memory': {
                    'used_memory': redis_info.get('used_memory_human', 'N/A'),
                    'used_memory_peak': redis_info.get('used_memory_peak_human', 'N/A'),
                    'memory_fragmentation_ratio': redis_info.get('mem_fragmentation_ratio', 'N/A')
                },
                'redis_stats': {
                    'total_commands_processed': redis_stats.get('total_commands_processed', 'N/A'),
                    'instantaneous_ops_per_sec': redis_stats.get('instantaneous_ops_per_sec', 'N/A'),
                    'keyspace_hits': redis_stats.get('keyspace_hits', 'N/A'),
                    'keyspace_misses': redis_stats.get('keyspace_misses', 'N/A')
                }
            }
        except Exception as e:
            self.logger.error(f"Stats collection error: {e}")
            return {'error': str(e)}

    def health_check(self) -> Dict:
        """Check cache system health"""
        try:
            # Test Redis connection
            redis_ok = self.redis_client.ping()

            # Test PostgreSQL connection
            pg_ok = False
            try:
                with psycopg2.connect(**self.pg_config) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        pg_ok = cur.fetchone()[0] == 1
            except:
                pass

            return {
                'timestamp': datetime.now().isoformat(),
                'redis_connection': redis_ok,
                'postgresql_connection': pg_ok,
                'overall_health': redis_ok and pg_ok
            }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'overall_health': False
            }

# Global cache instance
cache = CacheManager()

if __name__ == '__main__':
    # Test the cache manager
    print("Testing Cache Manager...")

    # Health check
    health = cache.health_check()
    print(f"Health check: {health}")

    # Test company lookup
    companies = cache.get_companies_by_country('RO')
    print(f"Romanian companies: {companies}")

    # Get stats
    stats = cache.get_cache_stats()
    print(f"Cache stats: {json.dumps(stats, indent=2)}")