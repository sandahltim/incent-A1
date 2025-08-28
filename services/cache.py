# cache.py
# Version: 1.0.0
# Comprehensive caching service for employee incentive system
# Provides thread-safe in-memory caching with configurable TTL and automatic invalidation

import time
import threading
import json
import logging
from typing import Any, Optional, Dict, Set, Callable
from functools import wraps
from collections import defaultdict, OrderedDict
import weakref
from datetime import datetime, timedelta

class CacheEntry:
    """Represents a single cache entry with metadata"""
    
    def __init__(self, data: Any, ttl: int = 300, tags: Set[str] = None):
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl
        self.hit_count = 0
        self.last_access = self.created_at
        self.tags = tags or set()
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL"""
        return (time.time() - self.created_at) > self.ttl
    
    @property
    def age(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.created_at
    
    def access(self):
        """Mark entry as accessed, updating hit count and last access time"""
        self.hit_count += 1
        self.last_access = time.time()

class IncentiveCacheManager:
    """Thread-safe cache manager with automatic cleanup and monitoring"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300, cleanup_interval: int = 60):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        
        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0
        self._cleanup_runs = 0
        
        # Tag tracking for invalidation
        self._tag_to_keys: Dict[str, Set[str]] = defaultdict(set)
        
        # Last cleanup timestamp
        self._last_cleanup = time.time()
        
        # Weak references to dependent caches
        self._dependents: Set[weakref.ref] = set()
        
        logging.info(f"IncentiveCacheManager initialized: max_size={max_size}, default_ttl={default_ttl}s")
    
    def _cleanup_expired(self) -> int:
        """Remove expired entries and perform maintenance"""
        if (time.time() - self._last_cleanup) < self._cleanup_interval:
            return 0
            
        with self._lock:
            expired_keys = []
            for key, entry in list(self._cache.items()):
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
            
            self._last_cleanup = time.time()
            self._cleanup_runs += 1
            
            if expired_keys:
                logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def _remove_entry(self, key: str):
        """Remove a cache entry and update tag mappings"""
        if key in self._cache:
            entry = self._cache.pop(key, None)
            if entry:
                # Remove from tag mappings
                for tag in entry.tags:
                    self._tag_to_keys[tag].discard(key)
                    if not self._tag_to_keys[tag]:  # Remove empty tag sets
                        del self._tag_to_keys[tag]
    
    def _evict_lru(self):
        """Evict least recently used entries to make room"""
        with self._lock:
            while len(self._cache) >= self._max_size:
                # Find LRU entry
                lru_key = None
                lru_access_time = float('inf')
                
                for key, entry in self._cache.items():
                    if entry.last_access < lru_access_time:
                        lru_access_time = entry.last_access
                        lru_key = key
                
                if lru_key:
                    self._remove_entry(lru_key)
                    self._evictions += 1
                    logging.debug(f"Evicted LRU cache entry: {lru_key}")
                else:
                    break  # Should not happen but prevent infinite loop
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from cache"""
        self._cleanup_expired()
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None or entry.is_expired:
                self._misses += 1
                if entry and entry.is_expired:
                    self._remove_entry(key)
                return default
            
            # Move to end (most recent) and update access stats
            self._cache.move_to_end(key)
            entry.access()
            self._hits += 1
            
            return entry.data
    
    def set(self, key: str, value: Any, ttl: int = None, tags: Set[str] = None) -> bool:
        """Store value in cache with optional TTL and tags"""
        ttl = ttl or self._default_ttl
        tags = tags or set()
        
        self._cleanup_expired()
        
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)
            
            # Create new entry
            entry = CacheEntry(value, ttl, tags)
            self._cache[key] = entry
            
            # Update tag mappings
            for tag in tags:
                self._tag_to_keys[tag].add(key)
            
            logging.debug(f"Cached key '{key}' with TTL {ttl}s, tags: {tags}")
            return True
    
    def delete(self, key: str) -> bool:
        """Remove specific key from cache"""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                logging.debug(f"Deleted cache key: {key}")
                return True
            return False
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with specific tag"""
        with self._lock:
            keys_to_remove = set(self._tag_to_keys.get(tag, set()))
            count = 0
            
            for key in keys_to_remove:
                if key in self._cache:
                    self._remove_entry(key)
                    count += 1
            
            self._invalidations += count
            
            if count > 0:
                logging.debug(f"Invalidated {count} cache entries with tag: {tag}")
            
            return count
    
    def clear(self) -> int:
        """Clear all cache entries"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._tag_to_keys.clear()
            self._invalidations += count
            
            logging.debug(f"Cleared all {count} cache entries")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests) if total_requests > 0 else 0
            
            # Memory usage estimation (rough)
            estimated_size = sum(
                len(str(key)) + len(str(entry.data)) + 100  # Rough overhead estimate
                for key, entry in self._cache.items()
            )
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_ratio': hit_ratio,
                'evictions': self._evictions,
                'invalidations': self._invalidations,
                'cleanup_runs': self._cleanup_runs,
                'current_size': len(self._cache),
                'max_size': self._max_size,
                'estimated_memory_bytes': estimated_size,
                'active_tags': len(self._tag_to_keys),
                'default_ttl': self._default_ttl,
                'last_cleanup': datetime.fromtimestamp(self._last_cleanup).isoformat()
            }
    
    def get_keys_by_pattern(self, pattern: str) -> list:
        """Get all keys matching a pattern (basic string matching)"""
        with self._lock:
            matching_keys = []
            for key in self._cache.keys():
                if pattern in key:
                    matching_keys.append(key)
            return matching_keys

# Global cache manager instance
_cache_manager = None
_cache_lock = threading.Lock()

def get_cache_manager() -> IncentiveCacheManager:
    """Get or create the global cache manager"""
    global _cache_manager
    with _cache_lock:
        if _cache_manager is None:
            from config import Config
            _cache_manager = IncentiveCacheManager(
                max_size=getattr(Config, 'CACHE_MAX_SIZE', 1000),
                default_ttl=getattr(Config, 'CACHE_DEFAULT_TTL', 300),
                cleanup_interval=getattr(Config, 'CACHE_CLEANUP_INTERVAL', 60)
            )
    return _cache_manager

# Cache decorator for function memoization
def cached(ttl: int = None, tags: Set[str] = None, key_func: Callable = None):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        tags: Tags for cache invalidation
        key_func: Function to generate cache key from function arguments
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        # Add cache management methods to wrapped function
        wrapper.cache_clear = lambda: get_cache_manager().clear()
        wrapper.cache_invalidate_tag = lambda tag: get_cache_manager().invalidate_by_tag(tag)
        wrapper.cache_stats = lambda: get_cache_manager().get_stats()
        
        return wrapper
    return decorator

# Predefined cache configurations for different data types
def _get_cache_configs():
    """Get cache configurations with values from Config"""
    try:
        from config import Config
        return {
            'scoreboard': {
                'ttl': getattr(Config, 'CACHE_TTL_SCOREBOARD', 30),
                'tags': {'scoreboard', 'employee_data'}
            },
            'rules': {
                'ttl': getattr(Config, 'CACHE_TTL_RULES', 300),
                'tags': {'rules', 'configuration'}
            },
            'roles': {
                'ttl': getattr(Config, 'CACHE_TTL_ROLES', 300),
                'tags': {'roles', 'configuration'}
            },
            'settings': {
                'ttl': getattr(Config, 'CACHE_TTL_SETTINGS', 120),
                'tags': {'settings', 'configuration'}
            },
            'pot_info': {
                'ttl': getattr(Config, 'CACHE_TTL_POT_INFO', 120),
                'tags': {'pot_info', 'financial'}
            },
            'voting_results': {
                'ttl': getattr(Config, 'CACHE_TTL_VOTING_RESULTS', 300),
                'tags': {'voting', 'results'}
            },
            'analytics': {
                'ttl': getattr(Config, 'CACHE_TTL_ANALYTICS', 600),
                'tags': {'analytics', 'charts'}
            },
            'employee_games': {
                'ttl': getattr(Config, 'CACHE_TTL_EMPLOYEE_GAMES', 60),
                'tags': {'games', 'employee_data'}
            },
            'admin_data': {
                'ttl': getattr(Config, 'CACHE_TTL_ADMIN_DATA', 600),
                'tags': {'admin', 'configuration'}
            },
            'history': {
                'ttl': getattr(Config, 'CACHE_TTL_HISTORY', 300),
                'tags': {'history', 'employee_data'}
            }
        }
    except ImportError:
        # Fallback configurations
        return {
            'scoreboard': {'ttl': 30, 'tags': {'scoreboard', 'employee_data'}},
            'rules': {'ttl': 300, 'tags': {'rules', 'configuration'}},
            'roles': {'ttl': 300, 'tags': {'roles', 'configuration'}},
            'settings': {'ttl': 120, 'tags': {'settings', 'configuration'}},
            'pot_info': {'ttl': 120, 'tags': {'pot_info', 'financial'}},
            'voting_results': {'ttl': 300, 'tags': {'voting', 'results'}},
            'analytics': {'ttl': 600, 'tags': {'analytics', 'charts'}},
            'employee_games': {'ttl': 60, 'tags': {'games', 'employee_data'}},
            'admin_data': {'ttl': 600, 'tags': {'admin', 'configuration'}},
            'history': {'ttl': 300, 'tags': {'history', 'employee_data'}}
        }

# Initialize configurations
CACHE_CONFIGS = _get_cache_configs()

def get_cache_config(data_type: str) -> Dict[str, Any]:
    """Get cache configuration for specific data type"""
    return CACHE_CONFIGS.get(data_type, {
        'ttl': 300,  # Default 5 minutes
        'tags': {data_type}
    })

# Cache invalidation helpers
class CacheInvalidationManager:
    """Manages cache invalidation triggers"""
    
    def __init__(self, cache_manager: IncentiveCacheManager):
        self.cache = cache_manager
        
    def invalidate_scoreboard(self):
        """Invalidate scoreboard-related caches"""
        tags_to_invalidate = ['scoreboard', 'employee_data', 'analytics']
        for tag in tags_to_invalidate:
            self.cache.invalidate_by_tag(tag)
        logging.debug("Invalidated scoreboard-related caches")
    
    def invalidate_voting(self):
        """Invalidate voting-related caches"""
        tags_to_invalidate = ['voting', 'scoreboard', 'employee_data']
        for tag in tags_to_invalidate:
            self.cache.invalidate_by_tag(tag)
        logging.debug("Invalidated voting-related caches")
    
    def invalidate_configuration(self):
        """Invalidate configuration-related caches"""
        tags_to_invalidate = ['configuration', 'settings', 'rules', 'roles']
        for tag in tags_to_invalidate:
            self.cache.invalidate_by_tag(tag)
        logging.debug("Invalidated configuration-related caches")
    
    def invalidate_financial(self):
        """Invalidate financial/pot-related caches"""
        tags_to_invalidate = ['financial', 'pot_info', 'analytics']
        for tag in tags_to_invalidate:
            self.cache.invalidate_by_tag(tag)
        logging.debug("Invalidated financial-related caches")
    
    def invalidate_games(self):
        """Invalidate mini-games related caches"""
        tags_to_invalidate = ['games', 'employee_data']
        for tag in tags_to_invalidate:
            self.cache.invalidate_by_tag(tag)
        logging.debug("Invalidated games-related caches")

def get_invalidation_manager() -> CacheInvalidationManager:
    """Get cache invalidation manager"""
    return CacheInvalidationManager(get_cache_manager())

# Context manager for cache warming
class CacheWarmer:
    """Pre-loads frequently accessed data into cache"""
    
    def __init__(self, cache_manager: IncentiveCacheManager):
        self.cache = cache_manager
        
    def warm_scoreboard_data(self, conn):
        """Pre-load scoreboard and related data"""
        try:
            from incentive_service import get_scoreboard, get_pot_info, is_voting_active
            
            # Warm scoreboard
            scoreboard = get_scoreboard(conn)
            config = get_cache_config('scoreboard')
            self.cache.set('scoreboard', scoreboard, 
                          ttl=config['ttl'], tags=config['tags'])
            
            # Warm pot info
            pot_info = get_pot_info(conn)
            config = get_cache_config('pot_info')
            self.cache.set('pot_info', pot_info,
                          ttl=config['ttl'], tags=config['tags'])
            
            # Warm voting status
            voting_active = is_voting_active(conn)
            self.cache.set('voting_active', voting_active,
                          ttl=30, tags={'voting'})
            
            logging.info("Cache warmed with scoreboard data")
        except Exception as e:
            logging.error(f"Failed to warm cache with scoreboard data: {e}")
    
    def warm_configuration_data(self, conn):
        """Pre-load configuration data"""
        try:
            from incentive_service import get_rules, get_roles, get_settings
            
            # Warm rules
            rules = get_rules(conn)
            config = get_cache_config('rules')
            self.cache.set('rules', rules,
                          ttl=config['ttl'], tags=config['tags'])
            
            # Warm roles
            roles = get_roles(conn)
            config = get_cache_config('roles')
            self.cache.set('roles', roles,
                          ttl=config['ttl'], tags=config['tags'])
            
            # Warm settings
            settings = get_settings(conn)
            config = get_cache_config('settings')
            self.cache.set('settings', settings,
                          ttl=config['ttl'], tags=config['tags'])
            
            logging.info("Cache warmed with configuration data")
        except Exception as e:
            logging.error(f"Failed to warm cache with configuration data: {e}")

def get_cache_warmer() -> CacheWarmer:
    """Get cache warmer instance"""
    return CacheWarmer(get_cache_manager())

# Performance monitoring
class CacheMetricsCollector:
    """Collects and reports cache performance metrics"""
    
    def __init__(self, cache_manager: IncentiveCacheManager):
        self.cache = cache_manager
        self._start_time = time.time()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        stats = self.cache.get_stats()
        uptime = time.time() - self._start_time
        
        return {
            **stats,
            'uptime_seconds': uptime,
            'requests_per_second': (stats['hits'] + stats['misses']) / uptime if uptime > 0 else 0,
            'memory_efficiency': stats['hits'] / stats['current_size'] if stats['current_size'] > 0 else 0,
            'performance_grade': self._calculate_grade(stats['hit_ratio'])
        }
    
    def _calculate_grade(self, hit_ratio: float) -> str:
        """Calculate performance grade based on hit ratio"""
        if hit_ratio >= 0.9:
            return 'A+'
        elif hit_ratio >= 0.8:
            return 'A'
        elif hit_ratio >= 0.7:
            return 'B+'
        elif hit_ratio >= 0.6:
            return 'B'
        elif hit_ratio >= 0.5:
            return 'C'
        else:
            return 'D'

def get_metrics_collector() -> CacheMetricsCollector:
    """Get cache metrics collector"""
    return CacheMetricsCollector(get_cache_manager())

# Cleanup function for graceful shutdown
def cleanup_cache():
    """Clean up cache resources"""
    global _cache_manager
    if _cache_manager:
        stats = _cache_manager.get_stats()
        logging.info(f"Cache cleanup: Final stats - {stats}")
        _cache_manager.clear()
        _cache_manager = None

# Register cleanup on module exit
import atexit
atexit.register(cleanup_cache)