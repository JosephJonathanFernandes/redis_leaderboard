# Redis Leaderboard Pro

A high-performance, production-ready Redis-powered leaderboard system with advanced features for modern applications.

## 🚀 Features

### Core Features
- **Ultra-fast leaderboards** with Redis sorted sets
- **High performance** - handles millions of players with connection pooling
- **Multiple interfaces**: CLI, REST API, Python library, Async API
- **Rich functionality**: rankings, score updates, player context, batch operations
- **Real-time updates** with sub-millisecond response times

### Advanced Features ✨
- **Async Support** - High-concurrency async leaderboard for web APIs
- **Historical Tracking** - Snapshots and timeline analysis
- **Player Analytics** - Detailed statistics and activity tracking
- **Monitoring & Alerting** - Real-time system monitoring with thresholds
- **Performance Optimization** - Automatic memory management and slow query analysis
- **Seasonal Leaderboards** - Time-based leaderboard management
- **Rate Limiting** - Protection against abuse
- **Caching Layer** - Improved response times for frequent queries
- **Data Validation** - Input sanitization and error handling
- **Comprehensive Testing** - Full test suite with performance benchmarks

### Production Ready 🏭
- **Connection Pooling** for optimal Redis performance
- **Logging & Monitoring** with configurable alerts
- **Environment Configuration** for dev/staging/production
- **Docker Support** with multi-stage builds
- **Security Features** including rate limiting and input validation
- **Performance Analytics** and optimization recommendations

## 📋 Prerequisites

### 1. Install Redis

**Windows (using Docker):**
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install redis-server

# macOS with Homebrew
brew install redis
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install individual packages:
```bash
pip install redis fastapi uvicorn click python-dotenv
```

## ⚡ Quick Start

### 1. Test Basic Connection

```python
import redis

# Test Redis connection
r = redis.Redis(host='localhost', port=6379, db=0)
r.set("test", "Hello Redis!")
print(r.get("test"))  # Should print: b'Hello Redis!'
```

### 2. Run the Demo

```bash
python leaderboard.py
```

### 3. Try Advanced Features

```bash
# Async demo
python async_leaderboard.py

# Advanced analytics
python advanced_features.py

# System monitoring
python monitoring.py
```

### 4. Use the CLI

```bash
# Basic operations
python cli.py add game_leaderboard Alice 1500
python cli.py top game_leaderboard
python cli.py demo
```

### 5. Start the API Server

```bash
python api.py
# Visit: http://localhost:8000/docs
```

## 📚 Usage Examples

### Basic Python Library

```python
from leaderboard import RedisLeaderboard

# Initialize with connection pooling
lb = RedisLeaderboard(max_connections=20, cache_ttl=60)

# Add players
lb.add_player("my_game", "Alice", 1500)
lb.add_player("my_game", "Bob", 1200)

# Batch operations for better performance
players = {"Charlie": 1800, "Diana": 1600, "Eve": 1100}
lb.batch_add_players("my_game", players)

# Get top players with caching
top_players = lb.get_top_players("my_game", 10)
for rank, (player, score) in enumerate(top_players, 1):
    print(f"#{rank}: {player} - {score}")
```

### Async API (High Performance)

```python
import asyncio
from async_leaderboard import AsyncRedisLeaderboard

async def high_performance_example():
    lb = AsyncRedisLeaderboard(max_connections=50)
    await lb.connect()
    
    # Concurrent operations
    await asyncio.gather(
        lb.add_player("game1", "Alice", 1500),
        lb.add_player("game1", "Bob", 1200),
        lb.update_score("game1", "Alice", 100)
    )
    
    top_players = await lb.get_top_players("game1", 10)
    await lb.close()
    
asyncio.run(high_performance_example())
```

### Advanced Analytics

```python
from advanced_features import AdvancedRedisLeaderboard, ScoreUpdateType
import redis

r = redis.Redis(decode_responses=True)
advanced_lb = AdvancedRedisLeaderboard(r)

# Create historical snapshots
advanced_lb.create_snapshot("my_game", "End of tournament")

# Track player activity for analytics
advanced_lb.track_player_activity(
    "my_game", "Alice", 250, ScoreUpdateType.INCREMENT
)

# Get detailed player statistics
stats = advanced_lb.get_player_stats("my_game", "Alice")
print(f"Games played: {stats.games_played}")
print(f"Average score: {stats.average_score:.1f}")
print(f"Highest score: {stats.highest_score}")

# Get comprehensive leaderboard analytics
analytics = advanced_lb.get_leaderboard_analytics("my_game")
print(f"Total players: {analytics['total_players']}")
print(f"Average score: {analytics['score_stats']['average']:.1f}")
print(f"Score distribution: {analytics['distribution']['score_ranges']}")
```

### Real-time Monitoring

```python
from monitoring import RedisLeaderboardMonitor
import redis

r = redis.Redis(decode_responses=True)

# Set up monitoring with custom thresholds
thresholds = {
    'memory_usage_mb': 500,
    'cpu_usage_percent': 80,
    'avg_response_time_ms': 100
}

monitor = RedisLeaderboardMonitor(r, thresholds)

# Start real-time monitoring
monitor.start_monitoring(interval_seconds=60)

# Get current system status
status = monitor.get_current_status()
print(f"Status: {status['status']}")
print(f"CPU Usage: {status['metrics']['cpu_usage']:.1f}%")
print(f"Memory Usage: {status['metrics']['memory_usage']:.1f}%")

# Get performance report
report = monitor.get_performance_report(hours=24)
print(f"Average response time: {report['averages']['response_time_ms']:.2f}ms")
```

### CLI Interface

```bash
# Basic operations
python cli.py add leaderboard_name player_name score
python cli.py update leaderboard_name player_name increment
python cli.py top leaderboard_name --count 20
python cli.py rank leaderboard_name player_name
python cli.py remove leaderboard_name player_name

# Bulk operations
python cli.py load leaderboard_name sample_players.json
python cli.py clear leaderboard_name

# Statistics
python cli.py stats leaderboard_name

# Demo
python cli.py demo
```

### REST API

```bash
# Start server
python api.py

# Add player
curl -X POST "http://localhost:8000/leaderboards/game/players" \
     -H "Content-Type: application/json" \
     -d '{"player_name": "Alice", "score": 1500}'

# Get top players
curl "http://localhost:8000/leaderboards/game/top?count=10"

# Update score
curl -X PUT "http://localhost:8000/leaderboards/game/players/Alice/score" \
     -H "Content-Type: application/json" \
     -d '{"score_increment": 100}'

# Get player info
curl "http://localhost:8000/leaderboards/game/players/Alice"
```

## 🔧 Configuration

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Edit `.env`:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_password

API_HOST=0.0.0.0
API_PORT=8000
```

## 📊 API Endpoints

### Players
- `POST /leaderboards/{name}/players` - Add player
- `POST /leaderboards/{name}/players/batch` - Add multiple players
- `PUT /leaderboards/{name}/players/{player}/score` - Update score
- `PUT /leaderboards/{name}/players/{player}/score/absolute` - Set absolute score
- `DELETE /leaderboards/{name}/players/{player}` - Remove player
- `GET /leaderboards/{name}/players/{player}` - Get player info
- `GET /leaderboards/{name}/players/{player}/context` - Get players around

### Leaderboards
- `GET /leaderboards/{name}/top` - Get top players
- `GET /leaderboards/{name}/stats` - Get statistics
- `GET /leaderboards/{name}/range` - Get players by score range
- `DELETE /leaderboards/{name}` - Clear leaderboard

### System
- `GET /` - Health check
- `GET /health` - Detailed health check
- `GET /docs` - API documentation (Swagger UI)

## ⚡ Performance Tips

1. **Use batch operations** when adding multiple players:
   ```python
   # Good - single Redis call
   lb.batch_add_players("game", {"player1": 100, "player2": 200})
   
   # Avoid - multiple Redis calls
   lb.add_player("game", "player1", 100)
   lb.add_player("game", "player2", 200)
   ```

2. **Connection pooling** for high-traffic applications:
   ```python
   import redis
   
   pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
   lb = RedisLeaderboard(connection_pool=pool)
   ```

3. **Use pipelines** for multiple operations:
   ```python
   pipe = lb.redis_client.pipeline()
   pipe.zadd("game", {"player1": 100})
   pipe.zadd("game", {"player2": 200})
   pipe.execute()
   ```

## 🎯 Advanced Features

### Multiple Leaderboards
```python
# Different game modes
lb.add_player("classic_mode", "Alice", 1500)
lb.add_player("speed_mode", "Alice", 2200)
lb.add_player("challenge_mode", "Alice", 900)
```

### Player Metadata
```python
# Automatic metadata storage
metadata = lb.get_player_metadata("Alice")
print(metadata)  # {'last_updated': '2025-01-20T...', 'current_score': 1600}
```

### Score Range Queries
```python
# Get all players with scores between 1000-2000
players = lb.get_score_range("game", 1000, 2000)
```

### Context Queries
```python
# Get players around a specific player
context = lb.get_players_around("game", "Alice", 5)
# Returns: [(player, score, rank), ...]
```

## 🚀 Production Deployment

### Docker Deployment

1. Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "api.py"]
```

2. Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      
  leaderboard-api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379

volumes:
  redis_data:
```

3. Run:
```bash
docker-compose up -d
```

### Production Considerations

- **Redis persistence**: Configure RDB/AOF
- **Connection pooling**: Use connection pools
- **Monitoring**: Set up Redis monitoring
- **Scaling**: Consider Redis Cluster for large datasets
- **Security**: Use Redis AUTH and SSL/TLS
- **Backup**: Regular Redis backups

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   ❌ Failed to connect to Redis
   ```
   - Check if Redis is running: `redis-cli ping`
   - Verify host/port in configuration
   - Check firewall settings

2. **Import Errors**
   ```
   ImportError: No module named 'redis'
   ```
   - Install dependencies: `pip install -r requirements.txt`

3. **Permission Denied**
   ```
   NOAUTH Authentication required
   ```
   - Set password in `.env`: `REDIS_PASSWORD=your_password`

### Testing Redis Connection

```bash
# Test Redis CLI
redis-cli ping  # Should return "PONG"

# Test from Python
python -c "import redis; r=redis.Redis(); print(r.ping())"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and test
4. Commit: `git commit -m "Add new feature"`
5. Push: `git push origin feature/new-feature`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🔗 Resources

- [Redis Documentation](https://redis.io/docs/)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Sorted Sets Guide](https://redis.io/docs/data-types/sorted-sets/)

---

**Happy coding! 🎮**