"""
Advanced Gamification Features
Achievements, streaks, power-ups, and game mechanics
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as aioredis


class PowerUpType(Enum):
    DOUBLE_POINTS = "double_points"
    SHIELD = "shield"
    SCORE_BOOST = "score_boost"
    RANK_FREEZE = "rank_freeze"


class StreakType(Enum):
    DAILY_LOGIN = "daily_login"
    CONSECUTIVE_WINS = "consecutive_wins"
    SCORE_INCREASES = "score_increases"


@dataclass
class PowerUp:
    type: PowerUpType
    name: str
    description: str
    duration_minutes: int
    effect_multiplier: float
    cost_points: int
    icon: str
    rarity: str  # common, rare, epic, legendary


@dataclass
class Streak:
    type: StreakType
    current_count: int
    best_count: int
    last_activity: datetime
    bonus_multiplier: float


@dataclass
class PlayerProfile:
    player_name: str
    level: int
    experience: int
    total_games: int
    total_score: int
    achievements: Set[str]
    active_powerups: Dict[str, datetime]  # powerup_type -> expiry_time
    streaks: Dict[str, Streak]
    created_at: datetime
    last_active: datetime
    title: str = "Newcomer"


class GamificationEngine:
    """
    Advanced gamification features for the leaderboard
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.powerups = self._init_powerups()
        self.level_thresholds = [100, 250, 500, 1000, 2000, 4000, 8000, 15000, 30000, 50000]
        self.titles = {
            1: "Newcomer", 2: "Beginner", 3: "Player", 4: "Competitor", 5: "Skilled",
            6: "Expert", 7: "Master", 8: "Champion", 9: "Legend", 10: "Grandmaster"
        }
    
    def _init_powerups(self) -> Dict[str, PowerUp]:
        """Initialize available power-ups"""
        return {
            "double_points": PowerUp(
                PowerUpType.DOUBLE_POINTS, "Double Points", "2x score for 10 minutes",
                10, 2.0, 500, "⚡", "common"
            ),
            "mega_boost": PowerUp(
                PowerUpType.SCORE_BOOST, "Mega Boost", "3x score for 5 minutes",
                5, 3.0, 1000, "🚀", "rare"
            ),
            "shield": PowerUp(
                PowerUpType.SHIELD, "Rank Shield", "Protect from rank drops for 30 minutes",
                30, 1.0, 750, "🛡️", "uncommon"
            ),
            "time_freeze": PowerUp(
                PowerUpType.RANK_FREEZE, "Time Freeze", "Freeze all rankings for 15 minutes",
                15, 1.0, 2000, "⏰", "epic"
            )
        }
    
    async def get_player_profile(self, player_name: str) -> Optional[PlayerProfile]:
        """Get comprehensive player profile"""
        try:
            profile_key = f"profile:{player_name}"
            profile_data = await self.redis.hgetall(profile_key)
            
            if not profile_data:
                # Create new profile if none exists
                return await self.create_player_profile(player_name)
            
            # Get achievements
            achievements_key = f"achievements:{player_name}"
            achievements = set(await self.redis.smembers(achievements_key))
            
            # Get active powerups with error handling
            powerups_key = f"powerups:{player_name}"
            powerup_data = await self.redis.hgetall(powerups_key)
            active_powerups = {}
            for k, v in powerup_data.items():
                try:
                    expiry = datetime.fromisoformat(v)
                    if expiry > datetime.now():
                        active_powerups[k] = expiry
                except:
                    continue
            
            # Get streaks with error handling
            streaks_key = f"streaks:{player_name}"
            streak_data = await self.redis.hgetall(streaks_key)
            streaks = {}
            for streak_type, data in streak_data.items():
                try:
                    streak_info = json.loads(data)
                    streaks[streak_type] = Streak(
                        type=StreakType(streak_type),
                        current_count=streak_info['current_count'],
                        best_count=streak_info['best_count'],
                        last_activity=datetime.fromisoformat(streak_info['last_activity']),
                        bonus_multiplier=streak_info['bonus_multiplier']
                    )
                except:
                    continue
            
            level = int(profile_data.get('level', 1))
            
            return PlayerProfile(
                player_name=player_name,
                level=level,
                experience=int(profile_data.get('experience', 0)),
                total_games=int(profile_data.get('total_games', 0)),
                total_score=int(profile_data.get('total_score', 0)),
                achievements=achievements,
                active_powerups=active_powerups,
                streaks=streaks,
                created_at=datetime.fromisoformat(profile_data.get('created_at', datetime.now().isoformat())),
                last_active=datetime.fromisoformat(profile_data.get('last_active', datetime.now().isoformat())),
                title=self.titles.get(level, "Unknown")
            )
            
        except Exception as e:
            print(f"Error getting player profile: {e}")
            # Return a new profile if there's any error
            return await self.create_player_profile(player_name)
    
    async def create_player_profile(self, player_name: str) -> PlayerProfile:
        """Create new player profile"""
        try:
            profile = PlayerProfile(
                player_name=player_name,
                level=1,
                experience=0,
                total_games=0,
                total_score=0,
                achievements=set(),
                active_powerups={},
                streaks={},
                created_at=datetime.now(),
                last_active=datetime.now(),
                title="Newcomer"
            )
            
            await self._save_player_profile(profile)
            return profile
            
        except Exception as e:
            print(f"Error creating player profile: {e}")
            # Return a basic profile even if save fails
            return PlayerProfile(
                player_name=player_name,
                level=1,
                experience=0,
                total_games=0,
                total_score=0,
                achievements=set(),
                active_powerups={},
                streaks={},
                created_at=datetime.now(),
                last_active=datetime.now(),
                title="Newcomer"
            )
    
    async def _save_player_profile(self, profile: PlayerProfile):
        """Save player profile to Redis (compatible with older Redis versions)"""
        try:
            profile_key = f"profile:{profile.player_name}"
            
            # Use individual hset calls for older Redis compatibility
            await self.redis.hset(profile_key, 'level', profile.level)
            await self.redis.hset(profile_key, 'experience', profile.experience)
            await self.redis.hset(profile_key, 'total_games', profile.total_games)
            await self.redis.hset(profile_key, 'total_score', profile.total_score)
            await self.redis.hset(profile_key, 'created_at', profile.created_at.isoformat())
            await self.redis.hset(profile_key, 'last_active', profile.last_active.isoformat())
            await self.redis.hset(profile_key, 'title', profile.title)
            
            # Save achievements
            if profile.achievements:
                achievements_key = f"achievements:{profile.player_name}"
                await self.redis.sadd(achievements_key, *profile.achievements)
        except Exception as e:
            print(f"Error saving player profile: {e}")
        
        # Save streaks
        streaks_key = f"streaks:{profile.player_name}"
        for streak_type, streak in profile.streaks.items():
            streak_data = {
                'current_count': streak.current_count,
                'best_count': streak.best_count,
                'last_activity': streak.last_activity.isoformat(),
                'bonus_multiplier': streak.bonus_multiplier
            }
            await self.redis.hset(streaks_key, streak_type, json.dumps(streak_data))
    
    async def award_experience(self, player_name: str, base_points: int) -> Dict:
        """Award experience points and check for level ups"""
        try:
            profile = await self.get_player_profile(player_name) or await self.create_player_profile(player_name)
            
            # Calculate bonus from active powerups and streaks
            bonus_multiplier = 1.0
            
            # Apply powerup bonuses
            active_powerups = []
            for powerup_type, expiry in profile.active_powerups.items():
                if expiry > datetime.now():
                    if powerup_type in ["double_points", "mega_boost"]:
                        powerup = self.powerups[powerup_type]
                        bonus_multiplier *= powerup.effect_multiplier
                        active_powerups.append(powerup_type)
            
            # Apply streak bonuses
            for streak in profile.streaks.values():
                bonus_multiplier *= streak.bonus_multiplier
            
            # Calculate final experience
            experience_gained = int(base_points * bonus_multiplier)
            old_level = profile.level
            profile.experience += experience_gained
            
            # Check for level up
            new_level = self._calculate_level(profile.experience)
            level_up = new_level > old_level
            
            if level_up:
                profile.level = new_level
                profile.title = self.titles.get(new_level, "Master")
            
            # Update profile
            profile.total_games += 1
            profile.total_score += base_points
            profile.last_active = datetime.now()
            
            await self._save_player_profile(profile)
            
            return {
                "experience_gained": experience_gained,
                "total_experience": profile.experience,
                "level": profile.level,
                "level_up": level_up,
                "old_level": old_level,
                "title": profile.title,
                "bonus_multiplier": bonus_multiplier,
                "active_powerups": active_powerups
            }
            
        except Exception as e:
            print(f"Error awarding experience: {e}")
            return {"experience_gained": 0, "error": str(e)}
    
    def _calculate_level(self, experience: int) -> int:
        """Calculate level based on experience"""
        level = 1
        for threshold in self.level_thresholds:
            if experience >= threshold:
                level += 1
            else:
                break
        return min(level, 10)  # Max level 10
    
    async def purchase_powerup(self, player_name: str, powerup_type: str, leaderboard_name: str) -> Dict:
        """Purchase and activate a powerup"""
        try:
            if powerup_type not in self.powerups:
                return {"success": False, "error": "Invalid powerup"}
            
            powerup = self.powerups[powerup_type]
            profile = await self.get_player_profile(player_name)
            
            if not profile:
                return {"success": False, "error": "Player profile not found"}
            
            # Check if player has enough points (using their current score as currency)
            current_score_key = f"currency:{leaderboard_name}:{player_name}"
            current_currency = int(await self.redis.get(current_score_key) or 0)
            
            if current_currency < powerup.cost_points:
                return {"success": False, "error": f"Need {powerup.cost_points} points, have {current_currency}"}
            
            # Deduct cost
            await self.redis.decrby(current_score_key, powerup.cost_points)
            
            # Activate powerup
            expiry_time = datetime.now() + timedelta(minutes=powerup.duration_minutes)
            powerups_key = f"powerups:{player_name}"
            await self.redis.hset(powerups_key, powerup_type, expiry_time.isoformat())
            
            return {
                "success": True,
                "powerup": asdict(powerup),
                "expiry_time": expiry_time.isoformat(),
                "remaining_currency": current_currency - powerup.cost_points
            }
            
        except Exception as e:
            print(f"Error purchasing powerup: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_streak(self, player_name: str, streak_type: StreakType, success: bool = True) -> Dict:
        """Update player's streak"""
        try:
            profile = await self.get_player_profile(player_name) or await self.create_player_profile(player_name)
            
            streak_key = streak_type.value
            if streak_key not in profile.streaks:
                profile.streaks[streak_key] = Streak(
                    type=streak_type,
                    current_count=0,
                    best_count=0,
                    last_activity=datetime.now(),
                    bonus_multiplier=1.0
                )
            
            streak = profile.streaks[streak_key]
            
            if success:
                # Check if streak continues (within reasonable time frame)
                time_diff = datetime.now() - streak.last_activity
                
                if streak_type == StreakType.DAILY_LOGIN and time_diff.days <= 1:
                    streak.current_count += 1
                elif streak_type in [StreakType.CONSECUTIVE_WINS, StreakType.SCORE_INCREASES]:
                    streak.current_count += 1
                else:
                    streak.current_count = 1  # Reset streak if too much time passed
                
                # Update best count
                streak.best_count = max(streak.best_count, streak.current_count)
                
                # Calculate bonus multiplier based on streak
                streak.bonus_multiplier = min(1.0 + (streak.current_count * 0.1), 3.0)  # Max 3x bonus
                
            else:
                # Streak broken
                streak.current_count = 0
                streak.bonus_multiplier = 1.0
            
            streak.last_activity = datetime.now()
            await self._save_player_profile(profile)
            
            return {
                "streak_type": streak_type.value,
                "current_count": streak.current_count,
                "best_count": streak.best_count,
                "bonus_multiplier": streak.bonus_multiplier,
                "streak_broken": not success
            }
            
        except Exception as e:
            print(f"Error updating streak: {e}")
            return {"error": str(e)}
    
    async def get_daily_challenges(self, player_name: str) -> List[Dict]:
        """Get daily challenges for player"""
        challenges = [
            {
                "id": "daily_score",
                "name": "Daily Scorer",
                "description": "Score 1000 points today",
                "target": 1000,
                "reward_xp": 100,
                "reward_currency": 50,
                "icon": "🎯"
            },
            {
                "id": "win_streak",
                "name": "Winning Streak",
                "description": "Increase score 5 times in a row",
                "target": 5,
                "reward_xp": 200,
                "reward_currency": 100,
                "icon": "🔥"
            },
            {
                "id": "top_player",
                "name": "Top Performer",
                "description": "Reach top 10 ranking",
                "target": 1,
                "reward_xp": 300,
                "reward_currency": 200,
                "icon": "⭐"
            }
        ]
        
        return challenges
    
    async def get_shop_items(self) -> List[Dict]:
        """Get available shop items"""
        items = []
        for powerup_type, powerup in self.powerups.items():
            items.append({
                "id": powerup_type,
                "name": powerup.name,
                "description": powerup.description,
                "cost": powerup.cost_points,
                "duration_minutes": powerup.duration_minutes,
                "icon": powerup.icon,
                "rarity": powerup.rarity,
                "effect_multiplier": powerup.effect_multiplier
            })
        
        return items


# Demo function
async def demo_gamification():
    """Demo gamification features"""
    print("🎮 Gamification Engine Demo")
    print("=" * 40)
    
    # Connect to Redis
    redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    gamification = GamificationEngine(redis_client)
    
    player_name = "GamerAlice"
    
    # Create player profile
    print(f"\n👤 Creating profile for {player_name}...")
    profile = await gamification.create_player_profile(player_name)
    print(f"   Level: {profile.level} ({profile.title})")
    print(f"   Experience: {profile.experience}")
    
    # Award some experience
    print(f"\n⭐ Awarding experience...")
    xp_result = await gamification.award_experience(player_name, 150)
    print(f"   Experience gained: {xp_result['experience_gained']}")
    print(f"   Total experience: {xp_result['total_experience']}")
    print(f"   Level: {xp_result['level']} ({xp_result['title']})")
    
    # Show shop items
    print(f"\n🛒 Shop Items Available:")
    shop_items = await gamification.get_shop_items()
    for item in shop_items[:3]:
        print(f"   {item['icon']} {item['name']}: {item['cost']} points")
        print(f"      {item['description']}")
    
    # Show daily challenges
    print(f"\n📋 Daily Challenges:")
    challenges = await gamification.get_daily_challenges(player_name)
    for challenge in challenges:
        print(f"   {challenge['icon']} {challenge['name']}")
        print(f"      {challenge['description']} (Reward: {challenge['reward_xp']} XP)")
    
    await redis_client.close()
    print(f"\n✅ Gamification demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_gamification())