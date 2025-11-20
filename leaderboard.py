import redis
from typing import List, Tuple, Optional, Dict
import json
from datetime import datetime


class RedisLeaderboard:
    """
    A Redis-based leaderboard system supporting multiple leaderboards,
    player stats, and real-time updates.
    """
    
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=host, 
            port=port, 
            db=db, 
            password=password,
            decode_responses=True
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            print("✅ Connected to Redis successfully!")
        except redis.ConnectionError:
            raise Exception("❌ Failed to connect to Redis. Make sure Redis is running.")
    
    def add_player(self, leaderboard_name: str, player_name: str, score: int) -> bool:
        """Add a player to the leaderboard with initial score"""
        try:
            result = self.redis_client.zadd(leaderboard_name, {player_name: score})
            
            # Store player metadata
            self._update_player_metadata(player_name, score)
            
            return result > 0
        except Exception as e:
            print(f"Error adding player: {e}")
            return False
    
    def update_score(self, leaderboard_name: str, player_name: str, score_increment: int) -> int:
        """Update a player's score by incrementing it"""
        try:
            new_score = self.redis_client.zincrby(leaderboard_name, score_increment, player_name)
            
            # Update player metadata
            self._update_player_metadata(player_name, new_score)
            
            return int(new_score)
        except Exception as e:
            print(f"Error updating score: {e}")
            return 0
    
    def set_score(self, leaderboard_name: str, player_name: str, score: int) -> bool:
        """Set a player's score to an absolute value"""
        try:
            result = self.redis_client.zadd(leaderboard_name, {player_name: score})
            
            # Update player metadata
            self._update_player_metadata(player_name, score)
            
            return True
        except Exception as e:
            print(f"Error setting score: {e}")
            return False
    
    def get_top_players(self, leaderboard_name: str, count: int = 10) -> List[Tuple[str, int]]:
        """Get top N players from the leaderboard"""
        try:
            # ZREVRANGE gets highest scores first
            result = self.redis_client.zrevrange(
                leaderboard_name, 0, count - 1, withscores=True
            )
            return [(player, int(score)) for player, score in result]
        except Exception as e:
            print(f"Error getting top players: {e}")
            return []
    
    def get_player_rank(self, leaderboard_name: str, player_name: str) -> Optional[int]:
        """Get a player's rank (1-indexed)"""
        try:
            # ZREVRANK gives rank in descending order (highest score = rank 0)
            rank = self.redis_client.zrevrank(leaderboard_name, player_name)
            return rank + 1 if rank is not None else None
        except Exception as e:
            print(f"Error getting player rank: {e}")
            return None
    
    def get_player_score(self, leaderboard_name: str, player_name: str) -> Optional[int]:
        """Get a player's current score"""
        try:
            score = self.redis_client.zscore(leaderboard_name, player_name)
            return int(score) if score is not None else None
        except Exception as e:
            print(f"Error getting player score: {e}")
            return None
    
    def get_players_around(self, leaderboard_name: str, player_name: str, count: int = 5) -> List[Tuple[str, int, int]]:
        """Get players around a specific player (useful for showing context)"""
        try:
            player_rank = self.redis_client.zrevrank(leaderboard_name, player_name)
            if player_rank is None:
                return []
            
            # Get players around the target player
            start_rank = max(0, player_rank - count // 2)
            end_rank = player_rank + count // 2
            
            result = self.redis_client.zrevrange(
                leaderboard_name, start_rank, end_rank, withscores=True
            )
            
            # Add rank information
            players_with_ranks = []
            for i, (player, score) in enumerate(result):
                rank = start_rank + i + 1
                players_with_ranks.append((player, int(score), rank))
            
            return players_with_ranks
        except Exception as e:
            print(f"Error getting players around: {e}")
            return []
    
    def remove_player(self, leaderboard_name: str, player_name: str) -> bool:
        """Remove a player from the leaderboard"""
        try:
            result = self.redis_client.zrem(leaderboard_name, player_name)
            
            # Clean up player metadata
            self._cleanup_player_metadata(player_name)
            
            return result > 0
        except Exception as e:
            print(f"Error removing player: {e}")
            return False
    
    def get_leaderboard_size(self, leaderboard_name: str) -> int:
        """Get the total number of players in the leaderboard"""
        try:
            return self.redis_client.zcard(leaderboard_name)
        except Exception as e:
            print(f"Error getting leaderboard size: {e}")
            return 0
    
    def clear_leaderboard(self, leaderboard_name: str) -> bool:
        """Clear all players from a leaderboard"""
        try:
            result = self.redis_client.delete(leaderboard_name)
            return result > 0
        except Exception as e:
            print(f"Error clearing leaderboard: {e}")
            return False
    
    def get_score_range(self, leaderboard_name: str, min_score: int, max_score: int) -> List[Tuple[str, int]]:
        """Get all players within a score range"""
        try:
            result = self.redis_client.zrangebyscore(
                leaderboard_name, min_score, max_score, withscores=True
            )
            return [(player, int(score)) for player, score in result]
        except Exception as e:
            print(f"Error getting score range: {e}")
            return []
    
    def _update_player_metadata(self, player_name: str, score: int):
        """Store additional player metadata"""
        try:
            metadata = {
                'last_updated': datetime.now().isoformat(),
                'current_score': str(score)
            }
            self.redis_client.hset(f"player:{player_name}", mapping=metadata)
        except Exception as e:
            # Silently handle metadata errors to not interrupt main functionality
            pass
    
    def _cleanup_player_metadata(self, player_name: str):
        """Clean up player metadata when removing player"""
        self.redis_client.delete(f"player:{player_name}")
    
    def get_player_metadata(self, player_name: str) -> Dict:
        """Get player metadata"""
        try:
            metadata = self.redis_client.hgetall(f"player:{player_name}")
            return metadata if metadata else {}
        except Exception as e:
            print(f"Error getting player metadata: {e}")
            return {}
    
    def batch_add_players(self, leaderboard_name: str, players_scores: Dict[str, int]) -> int:
        """Add multiple players at once for better performance"""
        try:
            result = self.redis_client.zadd(leaderboard_name, players_scores)
            
            # Update metadata for all players
            for player_name, score in players_scores.items():
                self._update_player_metadata(player_name, score)
            
            return result
        except Exception as e:
            print(f"Error batch adding players: {e}")
            return 0


# Example usage and demo functions
def demo_leaderboard():
    """Demonstrate leaderboard functionality"""
    print("🎮 Redis Leaderboard Demo")
    print("=" * 40)
    
    # Initialize leaderboard
    lb = RedisLeaderboard()
    leaderboard_name = "game_leaderboard"
    
    # Clear existing data for clean demo
    lb.clear_leaderboard(leaderboard_name)
    
    # Add some players
    print("\n📝 Adding players...")
    players = {
        "Alice": 1500,
        "Bob": 1200,
        "Charlie": 1800,
        "Diana": 1600,
        "Eve": 1100
    }
    
    for player, score in players.items():
        lb.add_player(leaderboard_name, player, score)
        print(f"   Added {player} with score {score}")
    
    # Show initial leaderboard
    print(f"\n🏆 Top 5 Players:")
    top_players = lb.get_top_players(leaderboard_name, 5)
    for i, (player, score) in enumerate(top_players, 1):
        print(f"   {i}. {player}: {score}")
    
    # Update some scores
    print(f"\n⬆️ Updating scores...")
    lb.update_score(leaderboard_name, "Bob", 300)  # Bob gets 300 points
    lb.update_score(leaderboard_name, "Eve", 600)  # Eve gets 600 points
    
    # Show updated leaderboard
    print(f"\n🏆 Updated Top 5 Players:")
    top_players = lb.get_top_players(leaderboard_name, 5)
    for i, (player, score) in enumerate(top_players, 1):
        print(f"   {i}. {player}: {score}")
    
    # Show player rank and context
    print(f"\n📊 Player Details:")
    for player in ["Alice", "Bob", "Eve"]:
        rank = lb.get_player_rank(leaderboard_name, player)
        score = lb.get_player_score(leaderboard_name, player)
        print(f"   {player}: Rank #{rank}, Score: {score}")
    
    # Show players around Bob
    print(f"\n🔍 Players around Bob:")
    around_bob = lb.get_players_around(leaderboard_name, "Bob", 3)
    for player, score, rank in around_bob:
        marker = " <- Bob" if player == "Bob" else ""
        print(f"   #{rank}. {player}: {score}{marker}")
    
    print(f"\n✅ Demo completed! Leaderboard has {lb.get_leaderboard_size(leaderboard_name)} players")


if __name__ == "__main__":
    demo_leaderboard()