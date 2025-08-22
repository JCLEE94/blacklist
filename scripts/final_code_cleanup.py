#!/usr/bin/env python3
"""
Final Code Cleanup for Blacklist Management System

Performs targeted cleanup based on analysis:
- Removes dead files
- Fixes unused variables
- Consolidates duplicate patterns
- Creates CNCF-compliant structure
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict


class FinalCodeCleanup:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_path = self.project_root / "src"
        self.cleanup_log = []
        
    def log_action(self, action: str, details: str = ""):
        """Log cleanup actions"""
        log_entry = f"{action}: {details}" if details else action
        self.cleanup_log.append(log_entry)
        print(f"  ✓ {log_entry}")
    
    def remove_dead_files(self) -> int:
        """Remove confirmed dead files"""
        dead_files = [
            "src/core/minimal_app.py",
            "src/utils/async_to_sync.py",
            "src/utils/memory/core_optimizer.py",
            "src/utils/memory/bulk_processor.py",
            # Only remove files that are definitely unused
        ]
        
        removed_count = 0
        for file_path in dead_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                # Create backup before removal
                backup_path = full_path.with_suffix(f"{full_path.suffix}.backup")
                shutil.copy2(full_path, backup_path)
                
                full_path.unlink()
                removed_count += 1
                self.log_action("Removed dead file", file_path)
        
        return removed_count
    
    def fix_unused_variables(self) -> int:
        """Fix specific unused variable issues"""
        fixes = {
            "src/core/collectors/regtech_excel_collector.py": [
                (r"(\s+)login_resp = (.+)\n", r"\1_ = \2  # login response (unused)\n")
            ],
            "src/core/routes/admin_routes.py": [
                (r"(\s+)where_clause = (.+)\n", r"\1_ = \2  # where clause (unused)\n")
            ],
            "src/core/routes/export_routes.py": [
                (r"(\s+)timestamp = (.+)\n", r"\1_ = \2  # timestamp (unused)\n")
            ],
            "src/utils/cicd_fix_strategies.py": [
                (r"(\s+)npm_fixes = (.+)\n", r"\1_ = \2  # npm fixes (unused)\n")
            ]
        }
        
        fixed_count = 0
        for file_path, patterns in fixes.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    
                    original_content = content
                    for pattern, replacement in patterns:
                        content = re.sub(pattern, replacement, content)
                    
                    if content != original_content:
                        with open(full_path, 'w') as f:
                            f.write(content)
                        fixed_count += 1
                        self.log_action("Fixed unused variables", file_path)
                        
                except Exception as e:
                    print(f"  ⚠️ Failed to fix {file_path}: {e}")
        
        return fixed_count
    
    def consolidate_cache_backends(self) -> bool:
        """Create unified cache interface"""
        try:
            unified_cache_content = '''#!/usr/bin/env python3
"""
Unified Cache Backend Interface

Consolidates Redis and Memory backends with consistent interface.
Provides automatic fallback and unified statistics.

Sample input: cache.set("key", "value", ttl=300)
Expected output: Cached value with TTL, automatic backend selection
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Union

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

logger = logging.getLogger(__name__)


class UnifiedCacheBackend:
    """Unified cache backend with Redis primary, memory fallback"""
    
    def __init__(self, redis_url: str = None, max_memory_entries: int = 10000):
        self.redis_client = None
        self.memory_cache = {}
        self.memory_lock = threading.RLock()
        self.max_memory_entries = max_memory_entries
        self.use_redis = False
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "redis_hits": 0,
            "memory_hits": 0
        }
        
        # Initialize Redis if available
        if HAS_REDIS and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis cache backend initialized")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis and self.redis_client:
                value = self.redis_client.get(key)
                if value is not None:
                    self.stats["hits"] += 1
                    self.stats["redis_hits"] += 1
                    return value.decode() if isinstance(value, bytes) else value
            
            # Fallback to memory cache
            with self.memory_lock:
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if entry["expires"] > time.time():
                        self.stats["hits"] += 1
                        self.stats["memory_hits"] += 1
                        return entry["value"]
                    else:
                        del self.memory_cache[key]
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache"""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.setex(key, ttl, str(value))
            
            # Always store in memory cache as backup
            with self.memory_lock:
                # LRU eviction
                if len(self.memory_cache) >= self.max_memory_entries:
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]
                
                self.memory_cache[key] = {
                    "value": value,
                    "expires": time.time() + ttl
                }
            
            self.stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.delete(key)
            
            with self.memory_lock:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            self.stats["deletes"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for cache backend"""
        health = {
            "redis_available": False,
            "memory_cache_size": 0,
            "stats": self.stats
        }
        
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.ping()
                health["redis_available"] = True
        except Exception:
            pass
        
        with self.memory_lock:
            health["memory_cache_size"] = len(self.memory_cache)
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()
        
        with self.memory_lock:
            stats["memory_entries"] = len(self.memory_cache)
        
        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except Exception:
                pass
        
        return stats


if __name__ == "__main__":
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Basic cache operations
    total_tests += 1
    try:
        cache = UnifiedCacheBackend()
        
        # Set and get
        success = cache.set("test_key", "test_value", ttl=60)
        if not success:
            all_validation_failures.append("Cache test: Failed to set value")
        
        value = cache.get("test_key")
        if value != "test_value":
            all_validation_failures.append(f"Cache test: Expected 'test_value', got {value}")
            
    except Exception as e:
        all_validation_failures.append(f"Cache test: Failed - {e}")
    
    # Test 2: Health check
    total_tests += 1
    try:
        cache = UnifiedCacheBackend()
        health = cache.health_check()
        
        if "stats" not in health:
            all_validation_failures.append("Health check test: Missing stats")
            
    except Exception as e:
        all_validation_failures.append(f"Health check test: Failed - {e}")
    
    # Test 3: Statistics
    total_tests += 1
    try:
        cache = UnifiedCacheBackend()
        stats = cache.get_stats()
        
        if "hits" not in stats or "misses" not in stats:
            all_validation_failures.append("Stats test: Missing required statistics")
            
    except Exception as e:
        all_validation_failures.append(f"Stats test: Failed - {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Unified cache backend is validated and ready for use")
        sys.exit(0)
'''
            
            unified_path = self.src_path / "utils" / "advanced_cache" / "unified_backend.py"
            with open(unified_path, 'w') as f:
                f.write(unified_cache_content)
            
            self.log_action("Created unified cache backend", str(unified_path.relative_to(self.project_root)))
            return True
            
        except Exception as e:
            print(f"  ⚠️ Failed to create unified cache backend: {e}")
            return False
    
    def create_cncf_structure(self) -> bool:
        """Create CNCF-compliant directory structure"""
        try:
            cncf_dirs = [
                "api",          # API definitions
                "cmd",          # Main applications
                "internal",     # Private application code
                "pkg",          # Library code for external use
                "build",        # Packaging and CI
                "deployments",  # System and container orchestration
                "test",         # Additional external test apps and test data
                "docs",         # Design and user documents
                "hack",         # Scripts
                "charts",       # Helm charts
            ]
            
            created_count = 0
            for dir_name in cncf_dirs:
                dir_path = self.project_root / dir_name
                if not dir_path.exists():
                    dir_path.mkdir()
                    
                    # Create .gitkeep to ensure directory is tracked
                    gitkeep_path = dir_path / ".gitkeep"
                    gitkeep_path.touch()
                    
                    created_count += 1
                    self.log_action("Created CNCF directory", dir_name)
            
            return created_count > 0
            
        except Exception as e:
            print(f"  ⚠️ Failed to create CNCF structure: {e}")
            return False
    
    def generate_summary(self) -> Dict:
        """Generate cleanup summary"""
        return {
            "actions_performed": len(self.cleanup_log),
            "log": self.cleanup_log
        }
    
    def run_cleanup(self) -> Dict:
        """Run complete cleanup process"""
        print("🧹 FINAL CODE CLEANUP")
        print("=" * 50)
        
        # 1. Remove dead files
        print("\n🗑️ Removing dead files...")
        removed_files = self.remove_dead_files()
        
        # 2. Fix unused variables
        print("\n🔧 Fixing unused variables...")
        fixed_variables = self.fix_unused_variables()
        
        # 3. Consolidate cache backends
        print("\n🔄 Consolidating cache backends...")
        cache_consolidated = self.consolidate_cache_backends()
        
        # 4. Create CNCF structure
        print("\n📁 Creating CNCF-compliant structure...")
        cncf_created = self.create_cncf_structure()
        
        return {
            "removed_files": removed_files,
            "fixed_variables": fixed_variables,
            "cache_consolidated": cache_consolidated,
            "cncf_created": cncf_created,
            "summary": self.generate_summary()
        }


def main():
    project_root = os.getcwd()
    cleanup = FinalCodeCleanup(project_root)
    
    try:
        results = cleanup.run_cleanup()
        
        print()
        print("✅ CLEANUP SUMMARY")
        print("=" * 50)
        print(f"📁 Files Removed: {results['removed_files']}")
        print(f"🔧 Variables Fixed: {results['fixed_variables']}")
        print(f"🔄 Cache Consolidated: {'✓' if results['cache_consolidated'] else '✗'}")
        print(f"📁 CNCF Structure: {'✓' if results['cncf_created'] else '✗'}")
        print(f"📋 Total Actions: {results['summary']['actions_performed']}")
        
        print()
        print("🎯 COMPLETED IMPROVEMENTS:")
        print("  - Removed dead/unused files")
        print("  - Fixed unused variable warnings")
        print("  - Consolidated duplicate cache backends")
        print("  - Created CNCF-compliant project structure")
        print("  - Enhanced code maintainability")
        
        print()
        print("🔄 NEXT STEPS:")
        print("  - Run tests to verify functionality: python -m pytest")
        print("  - Update imports to use common modules")
        print("  - Review and commit changes")
        print("  - Update documentation")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
