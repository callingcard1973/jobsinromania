# Redis Cache Infrastructure - Task 6 Implementation

## Overview

Comprehensive Redis caching layer implemented for raspibig production infrastructure to optimize database query performance and reduce load on PostgreSQL.

## Architecture

### Components Deployed

1. **Redis Server** - Production-configured with 4GB memory limit, persistence, and optimized settings
2. **CacheManager** - Core caching library with PostgreSQL integration
3. **Cache Monitor** - Health checking and metrics export
4. **Integration Examples** - Email and company data caching patterns
5. **Systemd Services** - Automated monitoring and maintenance

### Directory Structure

```
/opt/ACTIVE/INFRA/CACHE/
├── cache_manager.py              # Core cache management library
├── cache_monitor.py              # Health monitoring and metrics
├── email_cache_example.py        # Email campaign caching patterns
├── company_cache_example.py      # Company data caching patterns
└── README.md                     # This documentation
```

## Cache Configuration

### Redis Configuration
- **Location**: `/etc/redis/redis.conf`
- **Memory Limit**: 4GB (25% of system RAM)
- **Persistence**: RDB + AOF hybrid for durability
- **Eviction Policy**: allkeys-lru (Least Recently Used)
- **Network**: localhost-only for security

### TTL Policies
```python
default_ttl = {
    'company_lookup': 3600,      # 1 hour for company data
    'contact_list': 1800,        # 30 min for contact lists  
    'campaign_data': 600,        # 10 min for active campaigns
    'dashboard_stats': 300,      # 5 min for dashboard aggregations
    'scraper_cache': 7200,       # 2 hours for scraper results
    'email_validation': 86400,   # 24 hours for email validation
    'system_config': 3600,       # 1 hour for system settings
    'metadata': 1800             # 30 min for metadata
}
```

## Usage Examples

### Basic Query Caching

```python
from cache_manager import cache

# Execute query with automatic caching
companies = cache.execute_cached_query(
    "SELECT * FROM companies WHERE country = %s", 
    ('RO',), 
    'company_lookup'
)
```

### Email Validation Caching

```python
from email_cache_example import cache_email_validation, get_cached_email_validation

# Cache validation result
cache_email_validation("test@example.com", True, None)

# Retrieve cached validation
validation = get_cached_email_validation("test@example.com")
```

### Company Data Caching

```python
from company_cache_example import cache_company_lookup

# Cache company lookup (with automatic cache hit/miss handling)
companies = cache_company_lookup("RO")
```

## Monitoring and Alerting

### Health Checks

```bash
# Manual health check
python3 /opt/ACTIVE/INFRA/CACHE/cache_monitor.py

# Systemd service status
sudo systemctl status redis-server
sudo systemctl status redis-cache-monitor.timer
```

### Metrics Export

- **Location**: `/opt/ACTIVE/INFRA/PERFORMANCE/metrics/redis_cache_metrics.json`
- **Update Frequency**: Every 5 minutes via systemd timer
- **Grafana Integration**: Metrics compatible with existing dashboards

### Key Metrics Monitored

- **Performance**: Hit rate, ops/sec, response time
- **Memory**: Usage, fragmentation ratio, peak memory
- **Health**: Redis connectivity, PostgreSQL connectivity
- **Keys**: Total count, distribution by type

## Cache Key Patterns

```
cache:*                    # General database query cache
email_validation:*         # Email validation results
domain_reputation:*        # Email domain reputation
scraper:url:*             # Cached webpage content
scraper:company:*         # Scraped company data
dnc_list:*                # Do Not Contact lists
companies:*               # Company lookup cache
contacts:*                # Contact list cache
```

## Performance Impact

### Expected Performance Improvements

1. **Dashboard Queries**: 80-90% reduction in database load
2. **Email Campaigns**: 70-85% faster contact list generation
3. **Company Lookups**: 60-80% improvement in response time
4. **Scraper Operations**: 50-70% reduction in duplicate processing

### Memory Allocation

- **Redis Limit**: 4GB (configurable in redis.conf)
- **Current Usage**: ~1MB (baseline)
- **Expected Peak**: 2-3GB under full load
- **Monitoring**: Automated alerts at 80% memory usage

## Integration Points

### Email Campaigns

```python
# Check DNC list (cached)
dnc_emails = get_cached_dnc_list()

# Validate email (with caching)
validation = get_cached_email_validation(email)

# Get campaign contacts (cached query)
contacts = cache.execute_cached_query(contact_query, params, 'contact_list')
```

### Web Scrapers

```python
# Cache scraped content
cache_scraped_url(url, html_content, status_code)

# Cache company data with duplicate detection
cache_company_data(company_data, source)

# Check for duplicates
existing = check_company_duplicate(company_data)
```

### Dashboard Analytics

```python
# Cached dashboard statistics
stats = cache.get_dashboard_stats()

# Country-based company counts (cached)
companies = cache.get_companies_by_country('RO')
```

## Maintenance Operations

### Cache Invalidation

```python
# Invalidate by pattern
cache.invalidate_pattern('company_lookup')

# Invalidate specific country data
invalidate_company_cache('RO')
```

### Memory Optimization

```bash
# Manual optimization
python3 -c "from cache_monitor import *; optimize_memory_usage()"

# Automated via systemd timer (every 5 minutes)
sudo systemctl status redis-cache-monitor.timer
```

### Backup and Recovery

- **Redis Persistence**: RDB snapshots + AOF logs
- **Backup Location**: `/var/lib/redis/`
- **Recovery**: Automatic on Redis restart
- **Monitoring**: Integrated with existing backup systems

## Security Considerations

1. **Network Access**: Redis bound to localhost only (127.0.0.1)
2. **Authentication**: Uses existing PostgreSQL credentials
3. **Data Encryption**: None (localhost-only, sensitive data excluded)
4. **Access Control**: Service runs as `tudor` user with limited permissions

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   sudo systemctl restart redis-server
   redis-cli ping
   ```

2. **High Memory Usage**
   ```bash
   redis-cli info memory
   redis-cli config get maxmemory
   ```

3. **Low Hit Rate**
   ```python
   # Check TTL settings and query patterns
   cache.get_cache_stats()
   ```

### Log Locations

- **Redis Logs**: `/var/log/redis/redis-server.log`
- **Cache Monitor**: `journalctl -u redis-cache-monitor`
- **Application Logs**: `/opt/ACTIVE/INFRA/LOGS/`

## Future Enhancements

### Phase 2 Features
1. **Redis Cluster**: Multi-node setup for high availability
2. **Advanced Analytics**: Cache usage patterns and optimization
3. **Automated Scaling**: Dynamic memory allocation
4. **Cross-Region Sync**: Cache synchronization across machines

### Performance Tuning
1. **Query Optimization**: Identify and cache slow queries
2. **TTL Tuning**: Adjust based on data update patterns
3. **Memory Optimization**: Implement cache size limits per category
4. **Compression**: Enable for large cached objects

## Service Status

```bash
# Redis server status
sudo systemctl status redis-server

# Cache monitoring status  
sudo systemctl status redis-cache-monitor.timer

# Performance metrics
cat /opt/ACTIVE/INFRA/PERFORMANCE/metrics/redis_cache_metrics.json
```

## Success Metrics

✅ **Redis Installation**: Production-ready configuration deployed  
✅ **Cache Library**: Core CacheManager with PostgreSQL integration  
✅ **Monitoring**: Health checks and metrics export functional  
✅ **Integration**: Email and company caching examples working  
✅ **Automation**: Systemd services for monitoring and maintenance  
✅ **Documentation**: Complete usage and maintenance guide  

**Implementation Complete**: Redis caching infrastructure successfully deployed and operational on raspibig.