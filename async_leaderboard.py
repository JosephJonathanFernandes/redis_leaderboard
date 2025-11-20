import asyncio
import redis.asyncio as aioredis
from typing import List, Tuple, Optional, Dict
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AsyncRedisLeaderboard:
    """
    Async version of Redis Leaderboard for high-concurrency applications
    Perfect for web APIs handling many simultaneous requests
    """
    
    def __init__(self, host='localhost', port=6379, db=0, password=None, max_connections=20):
        """Initialize async Redis connection"""
        self.pool = aioredis.ConnectionPool.from_url(
            f"redis://{host}:{port}/{db}",
            password=password,
            max_connections=max_connections,
            decode_responses=True
        )
        self.redis_client = aioredis.Redis(connection_pool=self.pool)
    
    async def connect(self):
        """Test connection"""
        try:
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis (async) successfully!")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis (async): {e}")
            return False
    
    async def close(self):
        """Close connection pool"""
        await self.redis_client.aclose()
        await self.pool.disconnect()
    
    async def add_player(self, leaderboard_name: str, player_name: str, score: int) -> bool:
        """Add a player to the leaderboard"""
        try:
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Add to leaderboard and update metadata atomically
                await pipe.zadd(leaderboard_name, {player_name: score})
                await pipe.hset(f"player:{player_name}", "last_updated", datetime.now().isoformat())
                await pipe.hset(f"player:{player_name}", "current_score", str(score))
                results = await pipe.execute()
                
            return results[0] > 0
        except Exception as e:
            logger.error(f"Error adding player {player_name}: {e}")
            return False
    
    async def update_score(self, leaderboard_name: str, player_name: str, score_increment: int) -> int:
        """Update a player's score by incrementing it"""
        try:
            async with self.redis_client.pipeline(transaction=True) as pipe:
                await pipe.zincrby(leaderboard_name, score_increment, player_name)
                new_score = await pipe.execute()
                
                # Update metadata
                await self.redis_client.hset(f"player:{player_name}", "last_updated", datetime.now().isoformat())
                await self.redis_client.hset(f"player:{player_name}", "current_score", str(int(new_score[0])))
                
            return int(new_score[0])
        except Exception as e:
            logger.error(f"Error updating score for {player_name}: {e}")
            return 0
    
    async def get_top_players(self, leaderboard_name: str, count: int = 10) -> List[Tuple[str, int]]:
        """Get top N players from the leaderboard"""
        try:
            result = await self.redis_client.zrevrange(
                leaderboard_name, 0, count - 1, withscores=True
            )
            return [(player, int(score)) for player, score in result]
        except Exception as e:
            logger.error(f"Error getting top players: {e}")
            return []
    
    async def get_player_rank(self, leaderboard_name: str, player_name: str) -> Optional[int]:
        """Get a player's rank (1-indexed)"""
        try:
            rank = await self.redis_client.zrevrank(leaderboard_name, player_name)
            return rank + 1 if rank is not None else None
        except Exception as e:
            logger.error(f"Error getting player rank: {e}")
            return None
    
    async def get_player_score(self, leaderboard_name: str, player_name: str) -> Optional[int]:
        """Get a player's current score"""
        try:
            score = await self.redis_client.zscore(leaderboard_name, player_name)
            return int(score) if score is not None else None
        except Exception as e:
            logger.error(f"Error getting player score: {e}")
            return None
    
    async def batch_add_players(self, leaderboard_name: str, players_scores: Dict[str, int]) -> int:
        """Add multiple players at once using pipeline for better performance"""
        try:
            async with self.redis_client.pipeline(transaction=True) as pipe:
                await pipe.zadd(leaderboard_name, players_scores)
                
                # Update metadata for all players
                for player_name, score in players_scores.items():
                    await pipe.hset(f"player:{player_name}", "last_updated", datetime.now().isoformat())
                    await pipe.hset(f"player:{player_name}", "current_score", str(score))
                
                results = await pipe.execute()
                return results[0]
        except Exception as e:
            logger.error(f"Error batch adding players: {e}")
            return 0


# Example usage for async leaderboard
async def async_demo():
    """Demonstrate async leaderboard functionality"""
    print("\n🚀 Async Redis Leaderboard Demo")
    print("=" * 40)
    
    lb = AsyncRedisLeaderboard()
    
    if not await lb.connect():
        print("❌ Failed to connect to Redis")
        return
    
    leaderboard_name = "async_game_leaderboard"
    
    try:
        # Batch add players
        players = {
            "AsyncAlice": 1500,
            "AsyncBob": 1200,
            "AsyncCharlie": 1800,
            "AsyncDiana": 1600,
            "AsyncEve": 1100
        }
        
        print("\n📝 Adding players concurrently...")
        await lb.batch_add_players(leaderboard_name, players)
        
        # Get top players
        print(f"\n🏆 Top 5 Players (Async):")
        top_players = await lb.get_top_players(leaderboard_name, 5)
        for i, (player, score) in enumerate(top_players, 1):
            print(f"   {i}. {player}: {score}")
        
        # Concurrent score updates
        print(f"\n⬆️ Updating scores concurrently...")
        await asyncio.gather(
            lb.update_score(leaderboard_name, "AsyncBob", 300),
            lb.update_score(leaderboard_name, "AsyncEve", 600),
            lb.update_score(leaderboard_name, "AsyncAlice", 100)
        )
        
        # Show updated leaderboard
        print(f"\n🏆 Updated Top 5 Players (Async):")
        top_players = await lb.get_top_players(leaderboard_name, 5)
        for i, (player, score) in enumerate(top_players, 1):
            print(f"   {i}. {player}: {score}")
    
    finally:
        await lb.close()
        print("\n✅ Async demo completed!")


if __name__ == "__main__":
    asyncio.run(async_demo())