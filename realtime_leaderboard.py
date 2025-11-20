"""
Real-time WebSocket Leaderboard for Gamification
Live updates, achievements, and real-time notifications
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from async_leaderboard import AsyncRedisLeaderboard


class EventType(Enum):
    SCORE_UPDATE = "score_update"
    RANK_CHANGE = "rank_change" 
    NEW_PLAYER = "new_player"
    ACHIEVEMENT = "achievement"
    LEADERBOARD_UPDATE = "leaderboard_update"
    PLAYER_ONLINE = "player_online"
    PLAYER_OFFLINE = "player_offline"


@dataclass
class GameEvent:
    event_type: EventType
    player_name: str
    data: Dict
    timestamp: datetime = None
    leaderboard_name: str = "default"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    condition: str  # "score_threshold", "rank_achieved", "games_played", etc.
    threshold: int
    icon: str = "🏆"
    points: int = 100


class RealTimeLeaderboard:
    """
    Real-time leaderboard with WebSocket support for gamification
    """
    
    def __init__(self):
        self.app = FastAPI(title="Real-Time Gamified Leaderboard")
        self.connections: Dict[str, Set[WebSocket]] = {}  # leaderboard_name -> websockets
        self.player_connections: Dict[str, WebSocket] = {}  # player_name -> websocket
        self.leaderboard = None
        self.redis_client = None
        
        # Predefined achievements for gamification
        self.achievements = {
            "first_score": Achievement("first_score", "First Steps", "Score your first points!", "score_threshold", 1, "🎯", 50),
            "bronze_league": Achievement("bronze_league", "Bronze League", "Reach 1000 points!", "score_threshold", 1000, "🥉", 100),
            "silver_league": Achievement("silver_league", "Silver League", "Reach 2500 points!", "score_threshold", 2500, "🥈", 200),
            "gold_league": Achievement("gold_league", "Gold League", "Reach 5000 points!", "score_threshold", 5000, "🥇", 300),
            "top_10": Achievement("top_10", "Elite Player", "Reach top 10!", "rank_achieved", 10, "⭐", 150),
            "top_3": Achievement("top_3", "Podium Finisher", "Reach top 3!", "rank_achieved", 3, "🏅", 250),
            "champion": Achievement("champion", "Champion!", "Reach #1 rank!", "rank_achieved", 1, "👑", 500),
            "veteran": Achievement("veteran", "Veteran Player", "Play 50 games!", "games_played", 50, "🎖️", 200),
        }
        
        self.setup_routes()
    
    async def initialize_redis(self):
        """Initialize Redis connection"""
        self.leaderboard = AsyncRedisLeaderboard()
        await self.leaderboard.connect()
        self.redis_client = self.leaderboard.redis_client
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        # Suppress deprecation warnings temporarily
        import warnings
        warnings.filterwarnings("ignore", message="on_event is deprecated")
        
        @self.app.on_event("startup")
        async def startup_event():
            await self.initialize_redis()
        
        @self.app.on_event("shutdown") 
        async def shutdown_event():
            if self.leaderboard:
                await self.leaderboard.close()
        
        @self.app.get("/")
        async def get_dashboard():
            return HTMLResponse(self.get_dashboard_html())
        
        @self.app.websocket("/ws/{leaderboard_name}/{player_name}")
        async def websocket_endpoint(websocket: WebSocket, leaderboard_name: str, player_name: str):
            await self.handle_websocket(websocket, leaderboard_name, player_name)
        
        @self.app.post("/api/score/{leaderboard_name}/{player_name}")
        async def update_score_api(leaderboard_name: str, player_name: str, score_change: int):
            return await self.update_player_score(leaderboard_name, player_name, score_change)
        
        @self.app.get("/api/leaderboard/{leaderboard_name}")
        async def get_leaderboard_api(leaderboard_name: str, limit: int = 10):
            top_players = await self.leaderboard.get_top_players(leaderboard_name, limit)
            return {"leaderboard": top_players, "timestamp": datetime.now().isoformat()}
    
    async def handle_websocket(self, websocket: WebSocket, leaderboard_name: str, player_name: str):
        """Handle WebSocket connections for real-time updates"""
        await websocket.accept()
        
        # Add to connections
        if leaderboard_name not in self.connections:
            self.connections[leaderboard_name] = set()
        self.connections[leaderboard_name].add(websocket)
        self.player_connections[player_name] = websocket
        
        # Notify others that player is online
        await self.broadcast_event(GameEvent(
            event_type=EventType.PLAYER_ONLINE,
            player_name=player_name,
            leaderboard_name=leaderboard_name,
            data={"message": f"{player_name} joined the game!"}
        ))
        
        # Send initial data
        await self.send_initial_data(websocket, leaderboard_name, player_name)
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "score_update":
                    score_change = message.get("score_change", 0)
                    await self.update_player_score(leaderboard_name, player_name, score_change)
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                    
        except WebSocketDisconnect:
            # Clean up connections
            self.connections[leaderboard_name].discard(websocket)
            if player_name in self.player_connections:
                del self.player_connections[player_name]
            
            # Notify others that player went offline
            await self.broadcast_event(GameEvent(
                event_type=EventType.PLAYER_OFFLINE,
                player_name=player_name,
                leaderboard_name=leaderboard_name,
                data={"message": f"{player_name} left the game"}
            ))
    
    async def send_initial_data(self, websocket: WebSocket, leaderboard_name: str, player_name: str):
        """Send initial leaderboard data to new connection"""
        try:
            # Current leaderboard
            top_players = await self.leaderboard.get_top_players(leaderboard_name, 20)
            
            # Player's current position
            player_rank = await self.leaderboard.get_player_rank(leaderboard_name, player_name)
            player_score = await self.leaderboard.get_player_score(leaderboard_name, player_name)
            
            # Players around current player
            context_players = []
            if player_rank:
                # Get players around this player
                all_players = await self.leaderboard.get_top_players(leaderboard_name, 1000)
                start_idx = max(0, player_rank - 3)
                end_idx = min(len(all_players), player_rank + 2)
                context_players = all_players[start_idx:end_idx]
            
            initial_data = {
                "type": "initial_data",
                "leaderboard": top_players,
                "player_info": {
                    "name": player_name,
                    "rank": player_rank,
                    "score": player_score or 0
                },
                "context": context_players,
                "achievements": list(self.achievements.values()),
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_text(json.dumps(initial_data, default=str))
            
        except Exception as e:
            print(f"Error sending initial data: {e}")
    
    async def update_player_score(self, leaderboard_name: str, player_name: str, score_change: int):
        """Update player score and broadcast real-time events"""
        try:
            # Get old rank before update
            old_rank = await self.leaderboard.get_player_rank(leaderboard_name, player_name)
            old_score = await self.leaderboard.get_player_score(leaderboard_name, player_name) or 0
            
            # Update score
            new_score = await self.leaderboard.update_score(leaderboard_name, player_name, score_change)
            new_rank = await self.leaderboard.get_player_rank(leaderboard_name, player_name)
            
            # Create score update event
            score_event = GameEvent(
                event_type=EventType.SCORE_UPDATE,
                player_name=player_name,
                leaderboard_name=leaderboard_name,
                data={
                    "old_score": old_score,
                    "new_score": new_score,
                    "score_change": score_change,
                    "old_rank": old_rank,
                    "new_rank": new_rank
                }
            )
            
            await self.broadcast_event(score_event)
            
            # Check for rank changes
            if old_rank != new_rank and old_rank is not None:
                rank_event = GameEvent(
                    event_type=EventType.RANK_CHANGE,
                    player_name=player_name,
                    leaderboard_name=leaderboard_name,
                    data={
                        "old_rank": old_rank,
                        "new_rank": new_rank,
                        "rank_change": old_rank - new_rank if new_rank else 0
                    }
                )
                await self.broadcast_event(rank_event)
            
            # Check for achievements
            await self.check_achievements(leaderboard_name, player_name, new_score, new_rank)
            
            # Broadcast updated leaderboard
            await self.broadcast_leaderboard_update(leaderboard_name)
            
            return {
                "success": True,
                "player_name": player_name,
                "old_score": old_score,
                "new_score": new_score,
                "old_rank": old_rank,
                "new_rank": new_rank
            }
            
        except Exception as e:
            print(f"Error updating score: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_achievements(self, leaderboard_name: str, player_name: str, score: int, rank: Optional[int]):
        """Check if player has earned any achievements"""
        try:
            # Get player's current achievements
            achieved_key = f"achievements:{leaderboard_name}:{player_name}"
            current_achievements = set(await self.redis_client.smembers(achieved_key))
            
            new_achievements = []
            
            for achievement_id, achievement in self.achievements.items():
                if achievement_id in current_achievements:
                    continue  # Already achieved
                
                earned = False
                
                if achievement.condition == "score_threshold" and score >= achievement.threshold:
                    earned = True
                elif achievement.condition == "rank_achieved" and rank and rank <= achievement.threshold:
                    earned = True
                elif achievement.condition == "games_played":
                    # Would need to track games played separately
                    pass
                
                if earned:
                    # Add to player's achievements
                    await self.redis_client.sadd(achieved_key, achievement_id)
                    new_achievements.append(achievement)
            
            # Broadcast achievement events
            for achievement in new_achievements:
                achievement_event = GameEvent(
                    event_type=EventType.ACHIEVEMENT,
                    player_name=player_name,
                    leaderboard_name=leaderboard_name,
                    data={
                        "achievement": asdict(achievement),
                        "message": f"🎉 {player_name} earned: {achievement.name}!"
                    }
                )
                await self.broadcast_event(achievement_event)
                
        except Exception as e:
            print(f"Error checking achievements: {e}")
    
    async def broadcast_event(self, event: GameEvent):
        """Broadcast event to all connected clients"""
        if event.leaderboard_name in self.connections:
            message = json.dumps({
                "type": event.event_type.value,
                "player_name": event.player_name,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "leaderboard_name": event.leaderboard_name
            }, default=str)
            
            dead_connections = set()
            for websocket in self.connections[event.leaderboard_name]:
                try:
                    await websocket.send_text(message)
                except:
                    dead_connections.add(websocket)
            
            # Clean up dead connections
            for websocket in dead_connections:
                self.connections[event.leaderboard_name].discard(websocket)
    
    async def broadcast_leaderboard_update(self, leaderboard_name: str):
        """Broadcast updated leaderboard to all clients"""
        try:
            top_players = await self.leaderboard.get_top_players(leaderboard_name, 20)
            
            update_event = GameEvent(
                event_type=EventType.LEADERBOARD_UPDATE,
                player_name="system",
                leaderboard_name=leaderboard_name,
                data={"leaderboard": top_players}
            )
            
            await self.broadcast_event(update_event)
            
        except Exception as e:
            print(f"Error broadcasting leaderboard update: {e}")
    
    def get_dashboard_html(self) -> str:
        """HTML dashboard for real-time leaderboard"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>🎮 Real-Time Gamified Leaderboard</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .leaderboard { 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(10px);
            border-radius: 15px; 
            padding: 20px; 
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .player-row { 
            display: flex; 
            justify-content: space-between; 
            padding: 10px 15px; 
            margin: 5px 0; 
            background: rgba(255,255,255,0.1); 
            border-radius: 10px;
            transition: all 0.3s ease;
        }
        .player-row:hover { transform: translateY(-2px); background: rgba(255,255,255,0.2); }
        .rank { font-weight: bold; font-size: 1.2em; }
        .rank.gold { color: #FFD700; }
        .rank.silver { color: #C0C0C0; }
        .rank.bronze { color: #CD7F32; }
        .score { font-weight: bold; color: #4CAF50; }
        .controls { 
            display: flex; 
            gap: 10px; 
            justify-content: center; 
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button { 
            padding: 12px 24px; 
            border: none; 
            border-radius: 25px; 
            background: #4CAF50; 
            color: white; 
            cursor: pointer; 
            font-weight: bold;
            transition: all 0.3s ease;
        }
        button:hover { background: #45a049; transform: scale(1.05); }
        button.danger { background: #f44336; }
        button.danger:hover { background: #d32f2f; }
        .status { 
            text-align: center; 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 10px; 
        }
        .connected { background: rgba(76, 175, 80, 0.3); }
        .disconnected { background: rgba(244, 67, 54, 0.3); }
        .events { 
            height: 300px; 
            overflow-y: auto; 
            background: rgba(0,0,0,0.3); 
            border-radius: 10px; 
            padding: 15px;
            font-family: monospace;
        }
        .event { 
            margin: 5px 0; 
            padding: 8px; 
            border-radius: 5px; 
            background: rgba(255,255,255,0.1);
        }
        .achievement { 
            background: rgba(255, 193, 7, 0.3) !important; 
            border-left: 4px solid #FFC107;
            animation: glow 2s ease-in-out;
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 5px rgba(255, 193, 7, 0.5); }
            50% { box-shadow: 0 0 20px rgba(255, 193, 7, 0.8); }
        }
        .player-info { 
            background: rgba(255,255,255,0.1); 
            border-radius: 10px; 
            padding: 15px; 
            margin-bottom: 20px;
        }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { 
            .grid { grid-template-columns: 1fr; }
            .controls { flex-direction: column; align-items: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Real-Time Gamified Leaderboard</h1>
            <div id="status" class="status disconnected">Connecting...</div>
        </div>

        <div class="player-info">
            <h3>Your Info</h3>
            <div id="playerInfo">Not connected</div>
        </div>

        <div class="controls">
            <button onclick="addScore(10)">+10 Points</button>
            <button onclick="addScore(50)">+50 Points</button>
            <button onclick="addScore(100)">+100 Points</button>
            <button onclick="addScore(500)">🚀 +500 Points</button>
            <button class="danger" onclick="addScore(-25)">-25 Points</button>
        </div>

        <div class="grid">
            <div class="leaderboard">
                <h3>🏆 Live Leaderboard</h3>
                <div id="leaderboard">Loading...</div>
            </div>

            <div>
                <h3>📢 Live Events</h3>
                <div id="events" class="events"></div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let playerName = prompt("Enter your player name:") || "Player" + Math.floor(Math.random() * 1000);
        let leaderboardName = "realtime_game";

        function connect() {
            ws = new WebSocket(`ws://localhost:8000/ws/${leaderboardName}/${playerName}`);
            
            ws.onopen = function(event) {
                document.getElementById('status').innerHTML = '🟢 Connected to Real-Time Leaderboard';
                document.getElementById('status').className = 'status connected';
                addEvent('system', 'Connected to leaderboard!', 'connected');
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };

            ws.onclose = function(event) {
                document.getElementById('status').innerHTML = '🔴 Disconnected - Reconnecting...';
                document.getElementById('status').className = 'status disconnected';
                setTimeout(connect, 3000);
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                addEvent('system', 'Connection error', 'error');
            };
        }

        function handleMessage(data) {
            switch(data.type) {
                case 'initial_data':
                    updateLeaderboard(data.leaderboard);
                    updatePlayerInfo(data.player_info);
                    break;
                case 'score_update':
                    addEvent(data.player_name, 
                        `Score: ${data.data.old_score} → ${data.data.new_score} (${data.data.score_change > 0 ? '+' : ''}${data.data.score_change})`, 
                        'score');
                    break;
                case 'rank_change':
                    const change = data.data.old_rank - data.data.new_rank;
                    const direction = change > 0 ? '⬆️' : '⬇️';
                    addEvent(data.player_name, 
                        `Rank: #${data.data.old_rank} → #${data.data.new_rank} ${direction}`, 
                        'rank');
                    break;
                case 'achievement':
                    addEvent(data.player_name, 
                        `🏆 Achievement: ${data.data.achievement.name} - ${data.data.achievement.description}`, 
                        'achievement');
                    break;
                case 'leaderboard_update':
                    updateLeaderboard(data.data.leaderboard);
                    break;
                case 'player_online':
                case 'player_offline':
                    addEvent('system', data.data.message, 'player');
                    break;
                case 'pong':
                    // Keep-alive response
                    break;
            }
        }

        function updateLeaderboard(players) {
            const leaderboardDiv = document.getElementById('leaderboard');
            leaderboardDiv.innerHTML = '';
            
            players.forEach((player, index) => {
                const rank = index + 1;
                const [name, score] = player;
                const div = document.createElement('div');
                div.className = 'player-row';
                
                let rankClass = '';
                let medal = '';
                if (rank === 1) { rankClass = 'gold'; medal = '🥇'; }
                else if (rank === 2) { rankClass = 'silver'; medal = '🥈'; }
                else if (rank === 3) { rankClass = 'bronze'; medal = '🥉'; }
                
                div.innerHTML = `
                    <span class="rank ${rankClass}">${medal} #${rank} ${name}</span>
                    <span class="score">${score} pts</span>
                `;
                
                leaderboardDiv.appendChild(div);
            });
        }

        function updatePlayerInfo(info) {
            document.getElementById('playerInfo').innerHTML = `
                <strong>${info.name}</strong><br>
                Rank: #${info.rank || 'Not ranked'}<br>
                Score: ${info.score} points
            `;
        }

        function addEvent(player, message, type) {
            const eventsDiv = document.getElementById('events');
            const div = document.createElement('div');
            div.className = `event ${type}`;
            div.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong> [${player}] ${message}`;
            eventsDiv.insertBefore(div, eventsDiv.firstChild);
            
            // Keep only last 50 events
            while (eventsDiv.children.length > 50) {
                eventsDiv.removeChild(eventsDiv.lastChild);
            }
        }

        function addScore(points) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'score_update',
                    score_change: points
                }));
            }
        }

        // Keep connection alive
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'ping'}));
            }
        }, 30000);

        // Start connection
        connect();
    </script>
</body>
</html>
        """


# Create the real-time app instance
realtime_app = RealTimeLeaderboard()
app = realtime_app.app


if __name__ == "__main__":
    print("🎮 Starting Real-Time Gamified Leaderboard Server...")
    print("🌐 Dashboard: http://localhost:8001")
    print("📡 WebSocket: ws://localhost:8001/ws/{leaderboard}/{player}")
    print("🎯 Features: Live updates, achievements, real-time events")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)