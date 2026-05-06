#!/usr/bin/env python3
"""Health check endpoint for AgentOS.

Usage: python scripts/health_check.py
Returns exit code 0 if healthy, 1 if unhealthy.
"""

import sys
import os
import psycopg
from datetime import datetime, timezone
from typing import Dict, List, Tuple


def check_database() -> Tuple[bool, str]:
    """Check database connectivity and basic health."""
    database_url = os.getenv("DATABASE_URL", "postgresql://agentos:agentos@localhost:5432/agentos")
    
    try:
        conn = psycopg.connect(database_url, connect_timeout=5)
        with conn.cursor() as cur:
            # Basic connectivity
            cur.execute("SELECT 1")
            cur.fetchone()
            
            # Check schema count
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.schemata 
                WHERE schema_name IN ('coverage', 'filings', 'ingestion_raw', 'ops')
            """)
            schema_count = cur.fetchone()[0]
            
            # Check table count
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema IN ('coverage', 'filings', 'ingestion_raw', 'ops')
            """)
            table_count = cur.fetchone()[0]
            
            # Check recent errors
            cur.execute("""
                SELECT COUNT(*) FROM ops.alerts 
                WHERE severity IN ('error', 'critical') 
                AND acknowledged = false
                AND created_at > now() - interval '1 hour'
            """)
            recent_errors = cur.fetchone()[0]
            
        conn.close()
        
        if schema_count < 4:
            return False, f"Only {schema_count}/4 schemas found"
        if table_count < 20:
            return False, f"Only {table_count} tables found (expected 29+)"
        if recent_errors > 0:
            return False, f"{recent_errors} unacknowledged errors in last hour"
            
        return True, f"OK ({schema_count} schemas, {table_count} tables)"
        
    except Exception as e:
        return False, f"Database error: {str(e)}"


def check_disk_space() -> Tuple[bool, str]:
    """Check disk space availability."""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/data")
        free_gb = free / (1024**3)
        percent_used = (used / total) * 100
        
        if free_gb < 5:
            return False, f"Only {free_gb:.1f}GB free"
        if percent_used > 90:
            return False, f"{percent_used:.1f}% disk used"
            
        return True, f"OK ({free_gb:.1f}GB free, {percent_used:.1f}% used)"
        
    except Exception as e:
        return False, f"Disk check error: {str(e)}"


def check_memory() -> Tuple[bool, str]:
    """Check memory availability."""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        mem_total = 0
        mem_available = 0
        
        for line in meminfo.split('\n'):
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1]) / 1024 / 1024  # GB
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1]) / 1024 / 1024  # GB
        
        if mem_available < 1:
            return False, f"Only {mem_available:.1f}GB memory available"
            
        return True, f"OK ({mem_available:.1f}GB available / {mem_total:.1f}GB total)"
        
    except Exception as e:
        return False, f"Memory check error: {str(e)}"


def run_health_checks() -> Dict[str, Tuple[bool, str]]:
    """Run all health checks."""
    checks = {
        "database": check_database(),
        "disk": check_disk_space(),
        "memory": check_memory(),
    }
    return checks


def main():
    """Main health check entry point."""
    print(f"AgentOS Health Check - {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    checks = run_health_checks()
    all_healthy = True
    
    for name, (healthy, message) in checks.items():
        status = "✅" if healthy else "❌"
        print(f"{status} {name.upper()}: {message}")
        if not healthy:
            all_healthy = False
    
    print("=" * 60)
    
    if all_healthy:
        print("Status: HEALTHY")
        sys.exit(0)
    else:
        print("Status: UNHEALTHY")
        sys.exit(1)


if __name__ == "__main__":
    main()
