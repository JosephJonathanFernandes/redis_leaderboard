"""
Monitoring and Performance Tools for Redis Leaderboard
Real-time monitoring, alerting, and performance optimization
"""

import redis
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    timestamp: datetime
    redis_memory_used: int
    redis_connected_clients: int
    operations_per_second: float
    avg_response_time: float
    cpu_usage: float
    memory_usage: float
    active_leaderboards: int
    total_players: int

@dataclass
class Alert:
    """Alert for monitoring thresholds"""
    level: str  # INFO, WARNING, CRITICAL
    message: str
    timestamp: datetime
    metric: str
    value: float
    threshold: float

class RedisLeaderboardMonitor:
    """
    Real-time monitoring and alerting for Redis leaderboard system
    """
    
    def __init__(self, redis_client: redis.Redis, alert_thresholds: Dict = None):
        self.redis = redis_client
        self.alerts: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self.metrics_history: deque = deque(maxlen=1440)  # Keep 24 hours (1 min intervals)
        self.operation_times: deque = deque(maxlen=1000)  # Keep last 1000 operation times
        self.monitoring = False
        self.monitor_thread = None
        
        # Default alert thresholds
        self.thresholds = {
            'memory_usage_mb': 500,  # MB
            'cpu_usage_percent': 80,  # %
            'avg_response_time_ms': 100,  # milliseconds
            'connected_clients': 100,
            'operations_per_second': 1000
        }
        
        if alert_thresholds:
            self.thresholds.update(alert_thresholds)
    
    def start_monitoring(self, interval_seconds: int = 60):
        """Start real-time monitoring"""
        if self.monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Started monitoring with {interval_seconds}s intervals")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("Stopped monitoring")
    
    def _monitor_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                self._check_alerts(metrics)
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval_seconds)
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        try:
            # Redis metrics
            redis_info = self.redis.info()
            redis_memory = redis_info.get('used_memory', 0)
            redis_clients = redis_info.get('connected_clients', 0)
            
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Application metrics
            leaderboard_keys = self.redis.keys("*leaderboard*")
            active_leaderboards = len(leaderboard_keys)
            
            total_players = 0
            for key in leaderboard_keys:
                try:
                    total_players += self.redis.zcard(key)
                except:
                    pass
            
            # Calculate operations per second
            ops_per_second = self._calculate_ops_per_second()
            avg_response_time = self._calculate_avg_response_time()
            
            return PerformanceMetrics(
                timestamp=datetime.now(),
                redis_memory_used=redis_memory,
                redis_connected_clients=redis_clients,
                operations_per_second=ops_per_second,
                avg_response_time=avg_response_time,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                active_leaderboards=active_leaderboards,
                total_players=total_players
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                redis_memory_used=0, redis_connected_clients=0,
                operations_per_second=0, avg_response_time=0,
                cpu_usage=0, memory_usage=0,
                active_leaderboards=0, total_players=0
            )
    
    def _calculate_ops_per_second(self) -> float:
        """Calculate operations per second from recent history"""
        if len(self.operation_times) < 2:
            return 0.0
        
        # Count operations in last second
        now = time.time()
        recent_ops = sum(1 for t in self.operation_times if now - t <= 1)
        return float(recent_ops)
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time from recent operations"""
        if not self.operation_times:
            return 0.0
        
        # For simplicity, measure Redis ping time
        start = time.time()
        self.redis.ping()
        response_time = (time.time() - start) * 1000  # Convert to ms
        return response_time
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """Check metrics against thresholds and generate alerts"""
        checks = [
            ('memory_usage_mb', metrics.redis_memory_used / 1024 / 1024, self.thresholds['memory_usage_mb']),
            ('cpu_usage_percent', metrics.cpu_usage, self.thresholds['cpu_usage_percent']),
            ('avg_response_time_ms', metrics.avg_response_time, self.thresholds['avg_response_time_ms']),
            ('connected_clients', metrics.redis_connected_clients, self.thresholds['connected_clients']),
            ('operations_per_second', metrics.operations_per_second, self.thresholds['operations_per_second'])
        ]
        
        for metric_name, value, threshold in checks:
            if value > threshold:
                level = "CRITICAL" if value > threshold * 1.5 else "WARNING"
                alert = Alert(
                    level=level,
                    message=f"{metric_name} is {value:.2f}, above threshold {threshold}",
                    timestamp=datetime.now(),
                    metric=metric_name,
                    value=value,
                    threshold=threshold
                )
                self.alerts.append(alert)
                logger.warning(f"ALERT: {alert.message}")
    
    def get_current_status(self) -> Dict:
        """Get current system status"""
        if not self.metrics_history:
            return {"status": "No metrics available"}
        
        latest_metrics = self.metrics_history[-1]
        recent_alerts = [a for a in self.alerts if a.timestamp > datetime.now() - timedelta(hours=1)]
        
        return {
            "timestamp": latest_metrics.timestamp.isoformat(),
            "status": "healthy" if not recent_alerts else "alerts",
            "metrics": asdict(latest_metrics),
            "recent_alerts": len(recent_alerts),
            "critical_alerts": len([a for a in recent_alerts if a.level == "CRITICAL"]),
            "monitoring_active": self.monitoring
        }
    
    def get_alerts(self, level: Optional[str] = None, hours: int = 24) -> List[Alert]:
        """Get alerts from the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_alerts = [a for a in self.alerts if a.timestamp > cutoff_time]
        
        if level:
            filtered_alerts = [a for a in filtered_alerts if a.level == level]
        
        return list(filtered_alerts)
    
    def get_performance_report(self, hours: int = 24) -> Dict:
        """Generate performance report"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"message": "No metrics available for the specified period"}
        
        # Calculate averages and trends
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.avg_response_time for m in recent_metrics) / len(recent_metrics)
        
        # Growth metrics
        if len(recent_metrics) > 1:
            player_growth = recent_metrics[-1].total_players - recent_metrics[0].total_players
            leaderboard_growth = recent_metrics[-1].active_leaderboards - recent_metrics[0].active_leaderboards
        else:
            player_growth = leaderboard_growth = 0
        
        return {
            "period_hours": hours,
            "metrics_collected": len(recent_metrics),
            "averages": {
                "cpu_usage": round(avg_cpu, 2),
                "memory_usage": round(avg_memory, 2),
                "response_time_ms": round(avg_response_time, 2)
            },
            "growth": {
                "players": player_growth,
                "leaderboards": leaderboard_growth
            },
            "latest": asdict(recent_metrics[-1]) if recent_metrics else None,
            "alerts_summary": {
                "total": len(self.get_alerts(hours=hours)),
                "critical": len(self.get_alerts(level="CRITICAL", hours=hours)),
                "warning": len(self.get_alerts(level="WARNING", hours=hours))
            }
        }


class PerformanceOptimizer:
    """
    Performance optimization utilities for Redis leaderboard
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def optimize_memory(self, leaderboard_pattern: str = "*leaderboard*") -> Dict:
        """Optimize memory usage by cleaning up old data"""
        results = {
            "keys_analyzed": 0,
            "keys_optimized": 0,
            "memory_freed_estimate": 0
        }
        
        try:
            keys = self.redis.keys(leaderboard_pattern)
            results["keys_analyzed"] = len(keys)
            
            for key in keys:
                # Remove players with very low scores (bottom 1%)
                total_players = self.redis.zcard(key)
                if total_players > 100:  # Only optimize large leaderboards
                    bottom_count = max(1, total_players // 100)  # Bottom 1%
                    removed = self.redis.zremrangebyrank(key, 0, bottom_count - 1)
                    if removed:
                        results["keys_optimized"] += 1
                        results["memory_freed_estimate"] += removed * 50  # Rough estimate
        
        except Exception as e:
            logger.error(f"Error in memory optimization: {e}")
            results["error"] = str(e)
        
        return results
    
    def analyze_slow_operations(self) -> List[Dict]:
        """Analyze potentially slow operations"""
        # This would typically analyze Redis SLOWLOG
        try:
            slowlog = self.redis.slowlog_get(10)  # Get last 10 slow queries
            
            analysis = []
            for entry in slowlog:
                analysis.append({
                    "id": entry["id"],
                    "timestamp": datetime.fromtimestamp(entry["start_time"]).isoformat(),
                    "duration_microseconds": entry["duration"],
                    "command": entry["command"],
                    "optimization_suggestion": self._suggest_optimization(entry["command"])
                })
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing slow operations: {e}")
            return []
    
    def _suggest_optimization(self, command: List) -> str:
        """Suggest optimization for slow commands"""
        if not command:
            return "No specific optimization available"
        
        cmd = command[0].upper()
        
        suggestions = {
            "ZREVRANGE": "Consider using smaller ranges or implementing pagination",
            "ZADD": "Use batch operations with pipelines for multiple adds",
            "ZREM": "Consider batch removal operations",
            "KEYS": "Use SCAN instead of KEYS for large datasets"
        }
        
        return suggestions.get(cmd, "Consider using pipelines for multiple operations")


# Demo monitoring
def demo_monitoring():
    """Demonstrate monitoring capabilities"""
    print("📊 Redis Leaderboard Monitoring Demo")
    print("=" * 40)
    
    import redis
    r = redis.Redis(decode_responses=True)
    
    # Set custom thresholds
    thresholds = {
        'memory_usage_mb': 100,  # Lower threshold for demo
        'cpu_usage_percent': 50,
        'avg_response_time_ms': 50
    }
    
    monitor = RedisLeaderboardMonitor(r, thresholds)
    
    print("\n📈 Collecting current metrics...")
    metrics = monitor.collect_metrics()
    print(f"Redis Memory: {metrics.redis_memory_used / 1024 / 1024:.1f} MB")
    print(f"Connected Clients: {metrics.redis_connected_clients}")
    print(f"CPU Usage: {metrics.cpu_usage:.1f}%")
    print(f"Active Leaderboards: {metrics.active_leaderboards}")
    print(f"Total Players: {metrics.total_players}")
    
    print(f"\n🔧 Performance Optimization Analysis...")
    optimizer = PerformanceOptimizer(r)
    slow_ops = optimizer.analyze_slow_operations()
    if slow_ops:
        print(f"Found {len(slow_ops)} slow operations")
        for op in slow_ops[:3]:  # Show first 3
            print(f"  - {op['command'][0]} took {op['duration_microseconds']}μs")
    else:
        print("No slow operations detected")
    
    print("\n✅ Monitoring demo completed!")


if __name__ == "__main__":
    demo_monitoring()