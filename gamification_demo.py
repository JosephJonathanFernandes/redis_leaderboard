"""
Complete Real-Time Gamification Demo
Shows all real-time features, achievements, and game mechanics
"""

import asyncio
import time
from datetime import datetime
import redis.asyncio as aioredis

from gamification import GamificationEngine
from async_leaderboard import AsyncRedisLeaderboard


async def simulate_real_time_game():
    """Simulate a real-time multiplayer game scenario"""
    print("🎮 REAL-TIME GAMIFICATION SIMULATION")
    print("=" * 50)
    
    # Setup
    redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    leaderboard = AsyncRedisLeaderboard()
    await leaderboard.connect()
    gamification = GamificationEngine(redis_client)
    
    game_name = "realtime_battle"
    players = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    
    print(f"\n🏁 Starting real-time battle with {len(players)} players...")
    
    # Initialize players
    for player in players:
        await gamification.create_player_profile(player)
        await leaderboard.add_player(game_name, player, 0)
        print(f"   ✅ {player} joined the game")
    
    print(f"\n⚡ Simulating real-time gameplay...")
    
    # Simulate 30 seconds of intense gameplay
    for round_num in range(1, 11):
        print(f"\n🔥 Round {round_num}:")
        
        # Each player performs random actions
        for player in players:
            # Random score gain
            score_gain = 50 + (round_num * 25) + (hash(player) % 100)
            
            # Award experience with gamification
            xp_result = await gamification.award_experience(player, score_gain)
            
            # Update leaderboard score
            new_score = await leaderboard.update_score(game_name, player, score_gain)
            
            # Check for level ups
            level_up_msg = ""
            if xp_result.get('level_up'):
                level_up_msg = f" 🎉 LEVEL UP! {xp_result['old_level']} → {xp_result['level']} ({xp_result['title']})"
            
            print(f"   {player}: +{score_gain} pts (Total: {new_score}){level_up_msg}")
            
            # Show powerup effects
            if xp_result.get('active_powerups'):
                powerups = ", ".join(xp_result['active_powerups'])
                print(f"      💫 Active powerups: {powerups} ({xp_result['bonus_multiplier']:.1f}x multiplier)")
        
        # Show current leaderboard
        top_3 = await leaderboard.get_top_players(game_name, 3)
        print(f"   🏆 Top 3: ", end="")
        medals = ["🥇", "🥈", "🥉"]
        for i, (name, score) in enumerate(top_3):
            print(f"{medals[i]} {name}({score})", end="  ")
        print()
        
        # Simulate some players buying powerups
        if round_num == 5:
            print(f"\n   🛒 Mid-game powerup purchases:")
            
            # Give players some currency for demo
            for player in players:
                currency_key = f"currency:{game_name}:{player}"
                await redis_client.set(currency_key, 1000)
            
            # Alice buys double points
            powerup_result = await gamification.purchase_powerup("Alice", "double_points", game_name)
            if powerup_result['success']:
                print(f"      ⚡ Alice bought Double Points!")
            
            # Bob buys mega boost  
            powerup_result = await gamification.purchase_powerup("Bob", "mega_boost", game_name)
            if powerup_result['success']:
                print(f"      🚀 Bob bought Mega Boost!")
        
        await asyncio.sleep(0.5)  # Brief pause between rounds
    
    print(f"\n🏁 FINAL RESULTS:")
    print("=" * 30)
    
    # Final leaderboard
    final_standings = await leaderboard.get_top_players(game_name, len(players))
    
    for i, (player, score) in enumerate(final_standings, 1):
        profile = await gamification.get_player_profile(player)
        
        # Get rank emoji
        rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        
        print(f"{rank_emoji} {player}")
        print(f"    Score: {score} points")
        print(f"    Level: {profile.level} ({profile.title})")
        print(f"    Experience: {profile.experience} XP")
        print(f"    Total Games: {profile.total_games}")
        
        # Show achievements (simulated)
        if i == 1:
            print(f"    🏆 Achievements: Champion, Gold League, Top Player")
        elif i <= 3:
            print(f"    🏆 Achievements: Podium Finisher, Silver League")
        else:
            print(f"    🏆 Achievements: Bronze League")
        
        print()
    
    # Show game statistics
    print(f"📊 GAME STATISTICS:")
    print(f"   Total rounds played: 10")
    print(f"   Total score awarded: {sum(score for _, score in final_standings)}")
    print(f"   Average score per player: {sum(score for _, score in final_standings) // len(players)}")
    print(f"   Winner: {final_standings[0][0]} 👑")
    
    # Cleanup
    await leaderboard.close()
    await redis_client.close()
    
    print(f"\n✨ Real-time gamification simulation completed!")
    print(f"\n🚀 To see this in action with live WebSocket updates:")
    print(f"   1. Run: python realtime_leaderboard.py")
    print(f"   2. Open: http://localhost:8001")
    print(f"   3. Enter your name and click buttons to see real-time updates!")


async def demo_gamification_features():
    """Demo specific gamification features"""
    print("\n🎯 GAMIFICATION FEATURES DEMO")
    print("=" * 40)
    
    redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    gamification = GamificationEngine(redis_client)
    
    player = "DemoPlayer"
    
    # 1. Player Profile
    print(f"\n👤 Player Profile System:")
    profile = await gamification.create_player_profile(player)
    print(f"   Created: {profile.player_name} (Level {profile.level}, {profile.title})")
    
    # 2. Experience System
    print(f"\n⭐ Experience & Leveling:")
    for i in range(5):
        xp_gain = 200 + (i * 50)
        result = await gamification.award_experience(player, xp_gain)
        
        if result.get('level_up'):
            print(f"   🎉 LEVEL UP! {result['old_level']} → {result['level']} ({result['title']})")
        else:
            print(f"   +{result['experience_gained']} XP (Total: {result['total_experience']}, Level: {result['level']})")
    
    # 3. Shop System
    print(f"\n🛒 Power-up Shop:")
    shop_items = await gamification.get_shop_items()
    for item in shop_items:
        print(f"   {item['icon']} {item['name']}: {item['cost']} points")
        print(f"      Effect: {item['description']} ({item['effect_multiplier']}x for {item['duration_minutes']}min)")
    
    # 4. Daily Challenges
    print(f"\n📋 Daily Challenges:")
    challenges = await gamification.get_daily_challenges(player)
    for challenge in challenges:
        print(f"   {challenge['icon']} {challenge['name']}")
        print(f"      Goal: {challenge['description']}")
        print(f"      Reward: {challenge['reward_xp']} XP + {challenge['reward_currency']} coins")
    
    await redis_client.close()


if __name__ == "__main__":
    async def main():
        await simulate_real_time_game()
        await demo_gamification_features()
        
        print(f"\n🎮 REAL-TIME FEATURES AVAILABLE:")
        print(f"   🔴 Live WebSocket updates")
        print(f"   🏆 Real-time achievements")
        print(f"   📊 Live leaderboard changes")
        print(f"   ⚡ Power-ups and effects")
        print(f"   🔥 Streak bonuses")
        print(f"   📱 Responsive web interface")
        print(f"   🎯 Daily challenges")
        print(f"   👥 Multiplayer notifications")
    
    asyncio.run(main())