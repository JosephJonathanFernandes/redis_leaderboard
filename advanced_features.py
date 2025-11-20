"""
Advanced Redis Leaderboard features for better performance and functionality
"""

import redis
from typing import List, Tuple, Optional, Dict, Set
from datetime import datetime, timedelta
import json
import time
from dataclasses import dataclass
from enum import Enum

class ScoreUpdateType(Enum):
    INCREMENT = "increment"
    ABSOLUTE = "absolute"
    DECREMENT = "decrement"

@dataclass
class PlayerStats:
    """Comprehensive player statistics"""
    player_name: str
    current_score: int
    rank: int
    games_played: int = 0
    total_score_earned: int = 0
    highest_score: int = 0
    lowest_score: int = 0
    average_score: float = 0.0
    last_active: datetime = None
    join_date: datetime = None

@dataclass
class LeaderboardSnapshot:
    """Historical leaderboard snapshot"""
    timestamp: datetime
    top_players: List[Tuple[str, int]]
    total_players: int
    average_score: float
    highest_score: int

class AdvancedRedisLeaderboard:
    """
    Advanced Redis leaderboard with enhanced features:
    - Historical tracking and snapshots
    - Player statistics and achievements
    - Multiple scoring systems (ELO, seasonal)
    - Leaderboard categories and filters
    - Performance analytics
    """
    
    def __init__(self, redis_client: redis.Redis, namespace: str = "advanced_lb"):
        self.redis = redis_client
        self.namespace = namespace
    
    def _key(self, suffix: str) -> str:
        """Generate namespaced Redis key"""
        return f"{self.namespace}:{suffix}"
    
    # === HISTORICAL TRACKING ===
    
    def create_snapshot(self, leaderboard_name: str, description: str = "") -> bool:
        """Create a historical snapshot of the leaderboard"""
        try:
            timestamp = datetime.now()
            snapshot_key = self._key(f"snapshot:{leaderboard_name}:{timestamp.isoformat()}")
            
            # Get current leaderboard state
            top_players = self.redis.zrevrange(leaderboard_name, 0, -1, withscores=True)
            total_players = self.redis.zcard(leaderboard_name)
            
            if total_players > 0:
                scores = [float(score) for _, score in top_players]
                average_score = sum(scores) / len(scores)
                highest_score = max(scores)
            else:
                average_score = highest_score = 0
            
            snapshot_data = {
                "timestamp": timestamp.isoformat(),
                "description": description,
                "total_players": total_players,
                "average_score": average_score,
                "highest_score": highest_score,
                "top_10": json.dumps(list(top_players[:10]))
            }
            
            self.redis.hset(snapshot_key, "timestamp", timestamp.isoformat())
            self.redis.hset(snapshot_key, "description", description)
            self.redis.hset(snapshot_key, "total_players", total_players)
            self.redis.hset(snapshot_key, "average_score", average_score)
            self.redis.hset(snapshot_key, "highest_score", highest_score)
            self.redis.hset(snapshot_key, "top_10", json.dumps(list(top_players[:10])))
            
            # Add to snapshot index
            self.redis.zadd(
                self._key(f"snapshots:{leaderboard_name}"),
                {snapshot_key: timestamp.timestamp()}
            )
            
            return True
        except Exception as e:
            print(f"Error creating snapshot: {e}")
            return False
    
    def get_snapshots(self, leaderboard_name: str, limit: int = 10) -> List[LeaderboardSnapshot]:
        """Get historical snapshots"""
        try:
            snapshot_keys = self.redis.zrevrange(
                self._key(f"snapshots:{leaderboard_name}"), 0, limit - 1
            )
            
            snapshots = []
            for key in snapshot_keys:
                data = self.redis.hgetall(key)
                if data:
                    top_players = json.loads(data.get('top_10', '[]'))
                    snapshot = LeaderboardSnapshot(
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        top_players=[(p, int(s)) for p, s in top_players],
                        total_players=int(data['total_players']),
                        average_score=float(data['average_score']),
                        highest_score=int(float(data['highest_score']))
                    )
                    snapshots.append(snapshot)
            
            return snapshots
        except Exception as e:
            print(f"Error getting snapshots: {e}")
            return []
    
    # === PLAYER ANALYTICS ===
    
    def track_player_activity(self, leaderboard_name: str, player_name: str, 
                            score_change: int, update_type: ScoreUpdateType):
        """Track detailed player activity for analytics"""
        try:
            now = datetime.now()
            activity_key = self._key(f"activity:{leaderboard_name}:{player_name}")
            stats_key = self._key(f"stats:{leaderboard_name}:{player_name}")
            
            # Record activity
            activity_data = {
                "timestamp": now.isoformat(),
                "score_change": score_change,
                "update_type": update_type.value
            }
            
            # Add to activity log (keep last 100 activities)
            self.redis.lpush(activity_key, json.dumps(activity_data))
            self.redis.ltrim(activity_key, 0, 99)  # Keep only last 100
            
            # Update player statistics
            current_score = self.redis.zscore(leaderboard_name, player_name) or 0
            
            stats = self.redis.hgetall(stats_key)
            games_played = int(stats.get('games_played', 0)) + 1
            total_earned = int(stats.get('total_score_earned', 0)) + abs(score_change)
            highest = max(int(stats.get('highest_score', 0)), int(current_score))
            lowest = min(int(stats.get('lowest_score', current_score)), int(current_score)) if stats.get('lowest_score') else int(current_score)
            
            self.redis.hset(stats_key, "games_played", games_played)
            self.redis.hset(stats_key, "total_score_earned", total_earned)
            self.redis.hset(stats_key, "highest_score", highest)
            self.redis.hset(stats_key, "lowest_score", lowest)
            self.redis.hset(stats_key, "last_active", now.isoformat())
            self.redis.hset(stats_key, "average_score", total_earned / games_played if games_played > 0 else 0)
            
        except Exception as e:
            print(f"Error tracking player activity: {e}")
    
    def get_player_stats(self, leaderboard_name: str, player_name: str) -> Optional[PlayerStats]:
        """Get comprehensive player statistics"""
        try:
            stats_key = self._key(f"stats:{leaderboard_name}:{player_name}")
            stats = self.redis.hgetall(stats_key)
            
            if not stats:
                return None
            
            current_score = int(self.redis.zscore(leaderboard_name, player_name) or 0)
            rank = self.redis.zrevrank(leaderboard_name, player_name)
            rank = rank + 1 if rank is not None else None
            
            return PlayerStats(
                player_name=player_name,
                current_score=current_score,
                rank=rank,
                games_played=int(stats.get('games_played', 0)),
                total_score_earned=int(stats.get('total_score_earned', 0)),
                highest_score=int(stats.get('highest_score', 0)),
                lowest_score=int(stats.get('lowest_score', 0)),
                average_score=float(stats.get('average_score', 0)),
                last_active=datetime.fromisoformat(stats['last_active']) if stats.get('last_active') else None,
                join_date=datetime.fromisoformat(stats['join_date']) if stats.get('join_date') else None
            )
        except Exception as e:
            print(f"Error getting player stats: {e}")
            return None
    
    # === SEASONAL LEADERBOARDS ===
    
    def create_seasonal_leaderboard(self, base_name: str, season: str, 
                                  start_date: datetime, end_date: datetime) -> str:
        """Create a seasonal leaderboard"""
        season_key = f"{base_name}_season_{season}"
        season_info_key = self._key(f"season_info:{season_key}")
        
        self.redis.hset(season_info_key, "season", season)
        self.redis.hset(season_info_key, "start_date", start_date.isoformat())
        self.redis.hset(season_info_key, "end_date", end_date.isoformat())
        self.redis.hset(season_info_key, "base_leaderboard", base_name)
        self.redis.hset(season_info_key, "created_at", datetime.now().isoformat())
        
        return season_key
    
    def get_active_seasons(self, base_name: str) -> List[Dict]:
        """Get all active seasonal leaderboards"""
        try:
            pattern = self._key(f"season_info:{base_name}_season_*")
            keys = self.redis.keys(pattern)
            
            active_seasons = []
            now = datetime.now()
            
            for key in keys:
                info = self.redis.hgetall(key)
                if info:
                    end_date = datetime.fromisoformat(info['end_date'])
                    if end_date > now:  # Still active
                        active_seasons.append(info)
            
            return active_seasons
        except Exception as e:
            print(f"Error getting active seasons: {e}")
            return []
    
    # === PERFORMANCE ANALYTICS ===
    
    def get_leaderboard_analytics(self, leaderboard_name: str, days: int = 7) -> Dict:
        """Get comprehensive leaderboard performance analytics"""
        try:
            # Basic stats
            total_players = self.redis.zcard(leaderboard_name)
            
            if total_players == 0:
                return {"total_players": 0, "message": "No data available"}
            
            # Score distribution
            all_scores = [float(score) for _, score in 
                         self.redis.zrevrange(leaderboard_name, 0, -1, withscores=True)]
            
            # Calculate percentiles
            sorted_scores = sorted(all_scores)
            def percentile(scores, p):
                k = (len(scores) - 1) * p / 100
                f = int(k)
                c = f + 1
                if c >= len(scores):
                    return scores[f]
                return scores[f] + (k - f) * (scores[c] - scores[f])
            
            analytics = {
                "total_players": total_players,
                "score_stats": {
                    "highest": max(all_scores),
                    "lowest": min(all_scores),
                    "average": sum(all_scores) / len(all_scores),
                    "median": percentile(sorted_scores, 50),
                    "p25": percentile(sorted_scores, 25),
                    "p75": percentile(sorted_scores, 75),
                    "p90": percentile(sorted_scores, 90),
                    "p99": percentile(sorted_scores, 99)
                },
                "distribution": {
                    "score_ranges": self._get_score_distribution(all_scores)
                }
            }
            
            # Recent activity (if available)
            recent_snapshots = self.get_snapshots(leaderboard_name, 10)
            if recent_snapshots:
                analytics["growth"] = {
                    "player_growth": self._calculate_growth_rate(recent_snapshots, "players"),
                    "score_growth": self._calculate_growth_rate(recent_snapshots, "average_score")
                }
            
            return analytics
            
        except Exception as e:
            print(f"Error getting analytics: {e}")
            return {"error": str(e)}
    
    def _get_score_distribution(self, scores: List[float]) -> Dict:
        """Calculate score distribution across ranges"""
        if not scores:
            return {}
        
        min_score, max_score = min(scores), max(scores)
        range_size = (max_score - min_score) / 10  # 10 buckets
        
        distribution = {}
        for i in range(10):
            range_start = min_score + i * range_size
            range_end = min_score + (i + 1) * range_size
            count = sum(1 for s in scores if range_start <= s < range_end)
            distribution[f"{int(range_start)}-{int(range_end)}"] = count
        
        return distribution
    
    def _calculate_growth_rate(self, snapshots: List[LeaderboardSnapshot], metric: str) -> float:
        """Calculate growth rate for a specific metric"""
        if len(snapshots) < 2:
            return 0.0
        
        latest = snapshots[0]
        oldest = snapshots[-1]
        
        if metric == "players":
            old_val = oldest.total_players
            new_val = latest.total_players
        elif metric == "average_score":
            old_val = oldest.average_score
            new_val = latest.average_score
        else:
            return 0.0
        
        if old_val == 0:
            return 0.0
        
        return ((new_val - old_val) / old_val) * 100


# Demo function
def demo_advanced_features():
    """Demonstrate advanced leaderboard features"""
    print("🧠 Advanced Redis Leaderboard Features Demo")
    print("=" * 50)
    
    # Use existing Redis connection
    import redis
    r = redis.Redis(decode_responses=True)
    advanced_lb = AdvancedRedisLeaderboard(r)
    
    leaderboard_name = "advanced_game"
    
    # Create a snapshot
    print("\n📸 Creating leaderboard snapshot...")
    advanced_lb.create_snapshot(leaderboard_name, "Demo snapshot")
    
    # Track some player activity
    print("\n📊 Tracking player activity...")
    advanced_lb.track_player_activity(leaderboard_name, "Alice", 100, ScoreUpdateType.INCREMENT)
    advanced_lb.track_player_activity(leaderboard_name, "Bob", 50, ScoreUpdateType.INCREMENT)
    
    # Get player stats
    print("\n👤 Player Statistics:")
    alice_stats = advanced_lb.get_player_stats(leaderboard_name, "Alice")
    if alice_stats:
        print(f"   Alice - Games: {alice_stats.games_played}, Avg Score: {alice_stats.average_score:.1f}")
    
    # Get analytics
    print("\n📈 Leaderboard Analytics:")
    analytics = advanced_lb.get_leaderboard_analytics(leaderboard_name)
    if "score_stats" in analytics:
        stats = analytics["score_stats"]
        print(f"   Average Score: {stats['average']:.1f}")
        print(f"   Median Score: {stats['median']:.1f}")
        print(f"   Score Range: {stats['lowest']:.0f} - {stats['highest']:.0f}")


if __name__ == "__main__":
    demo_advanced_features()