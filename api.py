"""
FastAPI Web Interface for Redis Leaderboard
Provides REST API endpoints for leaderboard operations
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv

from leaderboard import RedisLeaderboard

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Redis Leaderboard API",
    description="A fast, Redis-powered leaderboard system with RESTful API",
    version="1.0.0"
)

# Initialize Redis connection
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_db = int(os.getenv('REDIS_DB', 0))
redis_password = os.getenv('REDIS_PASSWORD', None)

try:
    leaderboard = RedisLeaderboard(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password
    )
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
    leaderboard = None


# Pydantic models for request/response
class PlayerScore(BaseModel):
    player_name: str
    score: int

class ScoreUpdate(BaseModel):
    score_increment: int

class PlayerInfo(BaseModel):
    player_name: str
    score: int
    rank: Optional[int] = None

class LeaderboardEntry(BaseModel):
    rank: int
    player_name: str
    score: int

class LeaderboardResponse(BaseModel):
    leaderboard_name: str
    total_players: int
    entries: List[LeaderboardEntry]

class BatchPlayers(BaseModel):
    players: Dict[str, int]  # player_name -> score


# Health check
@app.get("/")
async def root():
    """Health check endpoint"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis connection failed")
    
    return {
        "message": "Redis Leaderboard API is running!",
        "status": "healthy",
        "redis_connected": True
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis connection failed")
    
    try:
        # Test Redis connection
        leaderboard.redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis error: {str(e)}")


# Player operations
@app.post("/leaderboards/{leaderboard_name}/players")
async def add_player(leaderboard_name: str, player: PlayerScore):
    """Add a new player to the leaderboard"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    success = leaderboard.add_player(leaderboard_name, player.player_name, player.score)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add player")
    
    return {
        "message": f"Player {player.player_name} added successfully",
        "leaderboard": leaderboard_name,
        "player_name": player.player_name,
        "score": player.score
    }


@app.post("/leaderboards/{leaderboard_name}/players/batch")
async def add_players_batch(leaderboard_name: str, batch: BatchPlayers):
    """Add multiple players at once"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    count = leaderboard.batch_add_players(leaderboard_name, batch.players)
    
    return {
        "message": f"Added {count} players successfully",
        "leaderboard": leaderboard_name,
        "players_added": count
    }


@app.put("/leaderboards/{leaderboard_name}/players/{player_name}/score")
async def update_player_score(leaderboard_name: str, player_name: str, update: ScoreUpdate):
    """Update a player's score by incrementing it"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    new_score = leaderboard.update_score(leaderboard_name, player_name, update.score_increment)
    
    if new_score == 0 and update.score_increment != 0:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {
        "message": f"Score updated successfully",
        "player_name": player_name,
        "previous_increment": update.score_increment,
        "new_score": new_score
    }


@app.put("/leaderboards/{leaderboard_name}/players/{player_name}/score/absolute")
async def set_player_score(leaderboard_name: str, player_name: str, player: PlayerScore):
    """Set a player's score to an absolute value"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    success = leaderboard.set_score(leaderboard_name, player_name, player.score)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to set score")
    
    return {
        "message": f"Score set successfully",
        "player_name": player_name,
        "score": player.score
    }


@app.delete("/leaderboards/{leaderboard_name}/players/{player_name}")
async def remove_player(leaderboard_name: str, player_name: str):
    """Remove a player from the leaderboard"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    success = leaderboard.remove_player(leaderboard_name, player_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {
        "message": f"Player {player_name} removed successfully",
        "leaderboard": leaderboard_name
    }


# Leaderboard queries
@app.get("/leaderboards/{leaderboard_name}/top")
async def get_top_players(
    leaderboard_name: str, 
    count: int = Query(10, ge=1, le=100, description="Number of top players to retrieve")
) -> LeaderboardResponse:
    """Get top N players from the leaderboard"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    top_players = leaderboard.get_top_players(leaderboard_name, count)
    total_players = leaderboard.get_leaderboard_size(leaderboard_name)
    
    entries = [
        LeaderboardEntry(rank=i+1, player_name=player, score=score)
        for i, (player, score) in enumerate(top_players)
    ]
    
    return LeaderboardResponse(
        leaderboard_name=leaderboard_name,
        total_players=total_players,
        entries=entries
    )


@app.get("/leaderboards/{leaderboard_name}/players/{player_name}")
async def get_player_info(leaderboard_name: str, player_name: str) -> PlayerInfo:
    """Get a player's rank and score"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    rank = leaderboard.get_player_rank(leaderboard_name, player_name)
    score = leaderboard.get_player_score(leaderboard_name, player_name)
    
    if rank is None or score is None:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return PlayerInfo(player_name=player_name, score=score, rank=rank)


@app.get("/leaderboards/{leaderboard_name}/players/{player_name}/context")
async def get_player_context(
    leaderboard_name: str, 
    player_name: str,
    count: int = Query(5, ge=3, le=20, description="Number of players around target player")
):
    """Get players around a specific player for context"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    around_players = leaderboard.get_players_around(leaderboard_name, player_name, count)
    
    if not around_players:
        raise HTTPException(status_code=404, detail="Player not found")
    
    context = [
        {
            "rank": rank,
            "player_name": player,
            "score": score,
            "is_target": player == player_name
        }
        for player, score, rank in around_players
    ]
    
    return {
        "leaderboard_name": leaderboard_name,
        "target_player": player_name,
        "context": context
    }


@app.get("/leaderboards/{leaderboard_name}/stats")
async def get_leaderboard_stats(leaderboard_name: str):
    """Get leaderboard statistics"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    size = leaderboard.get_leaderboard_size(leaderboard_name)
    
    if size == 0:
        return {
            "leaderboard_name": leaderboard_name,
            "total_players": 0,
            "message": "Leaderboard is empty"
        }
    
    # Get all players to calculate stats
    all_players = leaderboard.get_top_players(leaderboard_name, size)
    
    if all_players:
        scores = [score for _, score in all_players]
        highest_score = max(scores)
        lowest_score = min(scores)
        total_score = sum(scores)
        avg_score = total_score / len(scores)
        
        # Get top 3
        top_3 = leaderboard.get_top_players(leaderboard_name, 3)
    
    return {
        "leaderboard_name": leaderboard_name,
        "total_players": size,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "average_score": round(avg_score, 2),
        "total_score": total_score,
        "top_3": [
            {"rank": i+1, "player_name": player, "score": score}
            for i, (player, score) in enumerate(top_3)
        ]
    }


@app.delete("/leaderboards/{leaderboard_name}")
async def clear_leaderboard(leaderboard_name: str):
    """Clear all players from a leaderboard"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    size = leaderboard.get_leaderboard_size(leaderboard_name)
    success = leaderboard.clear_leaderboard(leaderboard_name)
    
    if not success and size > 0:
        raise HTTPException(status_code=400, detail="Failed to clear leaderboard")
    
    return {
        "message": f"Leaderboard cleared successfully",
        "leaderboard_name": leaderboard_name,
        "players_removed": size
    }


@app.get("/leaderboards/{leaderboard_name}/range")
async def get_players_by_score_range(
    leaderboard_name: str,
    min_score: int = Query(description="Minimum score (inclusive)"),
    max_score: int = Query(description="Maximum score (inclusive)")
):
    """Get all players within a score range"""
    if leaderboard is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    if min_score > max_score:
        raise HTTPException(status_code=400, detail="min_score cannot be greater than max_score")
    
    players = leaderboard.get_score_range(leaderboard_name, min_score, max_score)
    
    # Sort by score descending and add ranks
    players_sorted = sorted(players, key=lambda x: x[1], reverse=True)
    
    result = [
        {
            "player_name": player,
            "score": score,
            "rank": leaderboard.get_player_rank(leaderboard_name, player)
        }
        for player, score in players_sorted
    ]
    
    return {
        "leaderboard_name": leaderboard_name,
        "score_range": f"{min_score} - {max_score}",
        "players_found": len(result),
        "players": result
    }


# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)