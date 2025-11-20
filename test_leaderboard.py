"""
Test suite for Redis Leaderboard
Comprehensive testing for all features
"""

import pytest
import redis
import time
import asyncio
from datetime import datetime

# Import our modules
from leaderboard import RedisLeaderboard
from async_leaderboard import AsyncRedisLeaderboard
from advanced_features import AdvancedRedisLeaderboard, ScoreUpdateType
from monitoring import RedisLeaderboardMonitor, PerformanceOptimizer


class TestRedisLeaderboard:
    """Test the basic leaderboard functionality"""
    
    @pytest.fixture(scope="function")
    def redis_client(self):
        """Create a test Redis client"""
        client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)  # Use db 15 for testing
        client.flushdb()  # Clear test database
        yield client
        client.flushdb()  # Clean up after test
        client.close()
    
    @pytest.fixture
    def leaderboard(self, redis_client):
        """Create a test leaderboard instance"""
        return RedisLeaderboard(host='localhost', port=6379, db=15)
    
    def test_add_player(self, leaderboard):
        """Test adding players to leaderboard"""
        result = leaderboard.add_player("test_lb", "Alice", 1500)
        assert result is True
        
        score = leaderboard.get_player_score("test_lb", "Alice")
        assert score == 1500
        
        rank = leaderboard.get_player_rank("test_lb", "Alice")
        assert rank == 1
    
    def test_update_score(self, leaderboard):
        """Test score updates"""
        leaderboard.add_player("test_lb", "Alice", 1000)
        leaderboard.add_player("test_lb", "Bob", 1200)
        
        # Update Alice's score
        new_score = leaderboard.update_score("test_lb", "Alice", 500)
        assert new_score == 1500
        
        # Alice should now be rank 1
        alice_rank = leaderboard.get_player_rank("test_lb", "Alice")
        bob_rank = leaderboard.get_player_rank("test_lb", "Bob")
        assert alice_rank == 1
        assert bob_rank == 2
    
    def test_top_players(self, leaderboard):
        """Test getting top players"""
        # Add multiple players
        players = {"Alice": 1500, "Bob": 1200, "Charlie": 1800, "Diana": 1600}
        leaderboard.batch_add_players("test_lb", players)
        
        top_3 = leaderboard.get_top_players("test_lb", 3)
        assert len(top_3) == 3
        assert top_3[0] == ("Charlie", 1800)
        assert top_3[1] == ("Diana", 1600)
        assert top_3[2] == ("Alice", 1500)
    
    def test_players_around(self, leaderboard):
        """Test getting players around a specific player"""
        players = {"A": 1000, "B": 1100, "C": 1200, "D": 1300, "E": 1400}
        leaderboard.batch_add_players("test_lb", players)
        
        around_c = leaderboard.get_players_around("test_lb", "C", 3)
        assert len(around_c) <= 3
        
        # Find C in the results
        c_found = any(player == "C" for player, score, rank in around_c)
        assert c_found
    
    def test_remove_player(self, leaderboard):
        """Test removing players"""
        leaderboard.add_player("test_lb", "Alice", 1500)
        leaderboard.add_player("test_lb", "Bob", 1200)
        
        result = leaderboard.remove_player("test_lb", "Alice")
        assert result is True
        
        # Alice should no longer exist
        alice_score = leaderboard.get_player_score("test_lb", "Alice")
        assert alice_score is None
        
        # Bob should now be rank 1
        bob_rank = leaderboard.get_player_rank("test_lb", "Bob")
        assert bob_rank == 1


class TestAsyncLeaderboard:
    """Test async leaderboard functionality"""
    
    @pytest.fixture
    async def async_leaderboard(self):
        """Create async leaderboard for testing"""
        lb = AsyncRedisLeaderboard(host='localhost', port=6379, db=15)
        await lb.connect()
        # Clear test data
        await lb.redis_client.flushdb()
        yield lb
        await lb.close()
    
    @pytest.mark.asyncio
    async def test_async_add_player(self, async_leaderboard):
        """Test async player addition"""
        result = await async_leaderboard.add_player("async_test", "Alice", 1500)
        assert result is True
        
        score = await async_leaderboard.get_player_score("async_test", "Alice")
        assert score == 1500
    
    @pytest.mark.asyncio
    async def test_async_batch_operations(self, async_leaderboard):
        """Test async batch operations"""
        players = {"Alice": 1500, "Bob": 1200, "Charlie": 1800}
        count = await async_leaderboard.batch_add_players("async_test", players)
        assert count == 3
        
        top_players = await async_leaderboard.get_top_players("async_test", 3)
        assert len(top_players) == 3
        assert top_players[0][0] == "Charlie"
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self, async_leaderboard):
        """Test concurrent score updates"""
        # Add initial players
        await async_leaderboard.add_player("async_test", "Alice", 1000)
        await async_leaderboard.add_player("async_test", "Bob", 1000)
        
        # Concurrent updates
        await asyncio.gather(
            async_leaderboard.update_score("async_test", "Alice", 100),
            async_leaderboard.update_score("async_test", "Bob", 200),
            async_leaderboard.update_score("async_test", "Alice", 50)
        )
        
        alice_score = await async_leaderboard.get_player_score("async_test", "Alice")
        bob_score = await async_leaderboard.get_player_score("async_test", "Bob")
        
        assert alice_score == 1150  # 1000 + 100 + 50
        assert bob_score == 1200    # 1000 + 200


class TestAdvancedFeatures:
    """Test advanced leaderboard features"""
    
    @pytest.fixture
    def redis_client(self):
        """Redis client for advanced features"""
        client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        client.flushdb()
        yield client
        client.flushdb()
        client.close()
    
    @pytest.fixture
    def advanced_lb(self, redis_client):
        """Advanced leaderboard instance"""
        return AdvancedRedisLeaderboard(redis_client, namespace="test_advanced")
    
    def test_snapshot_creation(self, advanced_lb, redis_client):
        """Test snapshot functionality"""
        # Add some test data
        redis_client.zadd("test_leaderboard", {"Alice": 1500, "Bob": 1200})
        
        result = advanced_lb.create_snapshot("test_leaderboard", "Test snapshot")
        assert result is True
        
        snapshots = advanced_lb.get_snapshots("test_leaderboard", 1)
        assert len(snapshots) == 1
        assert snapshots[0].total_players == 2
    
    def test_player_analytics(self, advanced_lb, redis_client):
        """Test player analytics tracking"""
        # Add player and track activity
        redis_client.zadd("analytics_test", {"Alice": 1000})
        
        advanced_lb.track_player_activity(
            "analytics_test", "Alice", 100, ScoreUpdateType.INCREMENT
        )
        
        stats = advanced_lb.get_player_stats("analytics_test", "Alice")
        assert stats is not None
        assert stats.games_played == 1
        assert stats.total_score_earned == 100
    
    def test_leaderboard_analytics(self, advanced_lb, redis_client):
        """Test leaderboard analytics"""
        # Add test data
        test_scores = {"Alice": 1500, "Bob": 1200, "Charlie": 1800, "Diana": 1600}
        redis_client.zadd("analytics_test", test_scores)
        
        analytics = advanced_lb.get_leaderboard_analytics("analytics_test")
        
        assert analytics["total_players"] == 4
        assert "score_stats" in analytics
        assert analytics["score_stats"]["highest"] == 1800
        assert analytics["score_stats"]["lowest"] == 1200


class TestMonitoring:
    """Test monitoring and performance features"""
    
    @pytest.fixture
    def redis_client(self):
        """Redis client for monitoring tests"""
        client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        yield client
        client.close()
    
    @pytest.fixture
    def monitor(self, redis_client):
        """Monitoring instance"""
        return RedisLeaderboardMonitor(redis_client)
    
    def test_metrics_collection(self, monitor):
        """Test metrics collection"""
        metrics = monitor.collect_metrics()
        
        assert metrics.timestamp is not None
        assert isinstance(metrics.redis_memory_used, int)
        assert isinstance(metrics.cpu_usage, float)
        assert metrics.cpu_usage >= 0
    
    def test_performance_optimizer(self, redis_client):
        """Test performance optimizer"""
        optimizer = PerformanceOptimizer(redis_client)
        
        # Add test data
        test_data = {f"player_{i}": i for i in range(200)}
        redis_client.zadd("perf_test", test_data)
        
        results = optimizer.optimize_memory("perf_test")
        assert "keys_analyzed" in results
        assert results["keys_analyzed"] >= 1


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.fixture(scope="class")
    def system_setup(self):
        """Set up complete system for integration testing"""
        # This would set up Redis, API server, etc.
        yield
        # Cleanup
    
    def test_full_workflow(self, system_setup):
        """Test complete leaderboard workflow"""
        lb = RedisLeaderboard(host='localhost', port=6379, db=15)
        
        # Clear any existing data
        lb.clear_leaderboard("integration_test")
        
        # 1. Add players
        players = {"Alice": 1500, "Bob": 1200, "Charlie": 1800}
        for name, score in players.items():
            lb.add_player("integration_test", name, score)
        
        # 2. Verify initial state
        top_players = lb.get_top_players("integration_test", 3)
        assert len(top_players) == 3
        assert top_players[0][0] == "Charlie"
        
        # 3. Update scores
        lb.update_score("integration_test", "Bob", 700)  # Bob: 1200 + 700 = 1900
        
        # 4. Verify new rankings
        top_players = lb.get_top_players("integration_test", 3)
        assert top_players[0][0] == "Bob"  # Bob should now be first
        
        # 5. Test player context
        context = lb.get_players_around("integration_test", "Alice", 3)
        alice_found = any(player == "Alice" for player, score, rank in context)
        assert alice_found
        
        # 6. Cleanup
        lb.clear_leaderboard("integration_test")


# Benchmark tests
class TestPerformance:
    """Performance benchmark tests"""
    
    def test_batch_vs_individual_adds(self):
        """Compare batch vs individual player additions"""
        lb = RedisLeaderboard(host='localhost', port=6379, db=15)
        lb.clear_leaderboard("perf_test")
        
        # Individual adds
        start_time = time.time()
        for i in range(100):
            lb.add_player("perf_test", f"player_{i}", i * 10)
        individual_time = time.time() - start_time
        
        lb.clear_leaderboard("perf_test")
        
        # Batch add
        start_time = time.time()
        batch_players = {f"batch_player_{i}": i * 10 for i in range(100)}
        lb.batch_add_players("perf_test", batch_players)
        batch_time = time.time() - start_time
        
        print(f"Individual adds: {individual_time:.4f}s")
        print(f"Batch add: {batch_time:.4f}s")
        
        # Batch should be significantly faster
        assert batch_time < individual_time
        
        lb.clear_leaderboard("perf_test")


if __name__ == "__main__":
    # Run tests with: python -m pytest test_leaderboard.py -v
    print("Run tests with: python -m pytest test_leaderboard.py -v")
    print("For async tests: python -m pytest test_leaderboard.py::TestAsyncLeaderboard -v")
    print("For performance tests: python -m pytest test_leaderboard.py::TestPerformance -v -s")