#!/usr/bin/env python3
"""
CLI interface for Redis Leaderboard
Provides command-line access to leaderboard operations
"""

import click
from leaderboard import RedisLeaderboard
import json


@click.group()
@click.option('--host', default='localhost', help='Redis host')
@click.option('--port', default=6379, help='Redis port') 
@click.option('--db', default=0, help='Redis database number')
@click.pass_context
def cli(ctx, host, port, db):
    """Redis Leaderboard CLI - Manage leaderboards from command line"""
    ctx.ensure_object(dict)
    try:
        ctx.obj['leaderboard'] = RedisLeaderboard(host=host, port=port, db=db)
        ctx.obj['connected'] = True
    except Exception as e:
        click.echo(f"❌ Failed to connect to Redis: {e}")
        ctx.obj['connected'] = False


@cli.command()
@click.argument('leaderboard_name')
@click.argument('player_name')
@click.argument('score', type=int)
@click.pass_context
def add(ctx, leaderboard_name, player_name, score):
    """Add a player to the leaderboard"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    success = lb.add_player(leaderboard_name, player_name, score)
    
    if success:
        click.echo(f"✅ Added {player_name} to {leaderboard_name} with score {score}")
    else:
        click.echo(f"❌ Failed to add {player_name}")


@cli.command()
@click.argument('leaderboard_name')
@click.argument('player_name')
@click.argument('increment', type=int)
@click.pass_context
def update(ctx, leaderboard_name, player_name, increment):
    """Update a player's score by incrementing it"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    new_score = lb.update_score(leaderboard_name, player_name, increment)
    
    if new_score > 0:
        click.echo(f"✅ Updated {player_name}'s score to {new_score} (+{increment})")
    else:
        click.echo(f"❌ Failed to update {player_name}")


@cli.command()
@click.argument('leaderboard_name')
@click.option('--count', '-c', default=10, help='Number of top players to show')
@click.pass_context
def top(ctx, leaderboard_name, count):
    """Show top players in the leaderboard"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    top_players = lb.get_top_players(leaderboard_name, count)
    
    if not top_players:
        click.echo(f"📭 No players found in {leaderboard_name}")
        return
    
    click.echo(f"\n🏆 Top {len(top_players)} players in '{leaderboard_name}':")
    click.echo("=" * 50)
    
    for i, (player, score) in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        click.echo(f"{medal} #{i:2d}. {player:<20} {score:>8} pts")


@cli.command()
@click.argument('leaderboard_name')
@click.argument('player_name')
@click.pass_context
def rank(ctx, leaderboard_name, player_name):
    """Get a player's rank and score"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    rank = lb.get_player_rank(leaderboard_name, player_name)
    score = lb.get_player_score(leaderboard_name, player_name)
    
    if rank is None:
        click.echo(f"❌ Player '{player_name}' not found in {leaderboard_name}")
        return
    
    click.echo(f"📊 {player_name} in '{leaderboard_name}':")
    click.echo(f"   Rank: #{rank}")
    click.echo(f"   Score: {score}")
    
    # Show players around this player
    around = lb.get_players_around(leaderboard_name, player_name, 5)
    if around:
        click.echo(f"\n🔍 Context (players around {player_name}):")
        for player, player_score, player_rank in around:
            marker = " ← YOU" if player == player_name else ""
            click.echo(f"   #{player_rank:2d}. {player:<15} {player_score:>6}{marker}")


@cli.command()
@click.argument('leaderboard_name')
@click.argument('player_name')
@click.pass_context
def remove(ctx, leaderboard_name, player_name):
    """Remove a player from the leaderboard"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    success = lb.remove_player(leaderboard_name, player_name)
    
    if success:
        click.echo(f"✅ Removed {player_name} from {leaderboard_name}")
    else:
        click.echo(f"❌ Failed to remove {player_name} (player might not exist)")


@cli.command()
@click.argument('leaderboard_name')
@click.pass_context
def clear(ctx, leaderboard_name):
    """Clear all players from a leaderboard"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    count = lb.get_leaderboard_size(leaderboard_name)
    
    if count == 0:
        click.echo(f"📭 Leaderboard '{leaderboard_name}' is already empty")
        return
    
    if click.confirm(f"⚠️ This will remove all {count} players from '{leaderboard_name}'. Continue?"):
        success = lb.clear_leaderboard(leaderboard_name)
        if success:
            click.echo(f"✅ Cleared {leaderboard_name}")
        else:
            click.echo(f"❌ Failed to clear {leaderboard_name}")


@cli.command()
@click.argument('leaderboard_name')
@click.pass_context
def stats(ctx, leaderboard_name):
    """Show leaderboard statistics"""
    if not ctx.obj['connected']:
        return
    
    lb = ctx.obj['leaderboard']
    size = lb.get_leaderboard_size(leaderboard_name)
    
    if size == 0:
        click.echo(f"📭 Leaderboard '{leaderboard_name}' is empty")
        return
    
    # Get top and bottom players
    top_players = lb.get_top_players(leaderboard_name, 3)
    all_players = lb.get_top_players(leaderboard_name, size)
    
    if all_players:
        highest_score = all_players[0][1]
        lowest_score = all_players[-1][1]
        total_score = sum(score for _, score in all_players)
        avg_score = total_score / len(all_players)
    
    click.echo(f"\n📈 Statistics for '{leaderboard_name}':")
    click.echo("=" * 40)
    click.echo(f"Total players: {size}")
    click.echo(f"Highest score: {highest_score}")
    click.echo(f"Lowest score:  {lowest_score}")
    click.echo(f"Average score: {avg_score:.1f}")
    click.echo(f"Total score:   {total_score}")
    
    click.echo(f"\n🏆 Top 3:")
    for i, (player, score) in enumerate(top_players, 1):
        click.echo(f"   #{i}. {player}: {score}")


@cli.command()
@click.pass_context
def demo(ctx):
    """Run a demonstration of leaderboard features"""
    if not ctx.obj['connected']:
        return
    
    from leaderboard import demo_leaderboard
    demo_leaderboard()


@cli.command()
@click.argument('leaderboard_name')
@click.argument('file_path')
@click.pass_context
def load(ctx, leaderboard_name, file_path):
    """Load players from a JSON file"""
    if not ctx.obj['connected']:
        return
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        lb = ctx.obj['leaderboard']
        
        if isinstance(data, dict):
            # Format: {"player1": score1, "player2": score2}
            count = lb.batch_add_players(leaderboard_name, data)
            click.echo(f"✅ Loaded {count} players from {file_path}")
        elif isinstance(data, list):
            # Format: [{"name": "player1", "score": score1}, ...]
            players_dict = {item['name']: item['score'] for item in data}
            count = lb.batch_add_players(leaderboard_name, players_dict)
            click.echo(f"✅ Loaded {count} players from {file_path}")
        else:
            click.echo("❌ Invalid JSON format. Expected dict or list.")
    
    except FileNotFoundError:
        click.echo(f"❌ File not found: {file_path}")
    except json.JSONDecodeError:
        click.echo(f"❌ Invalid JSON in file: {file_path}")
    except Exception as e:
        click.echo(f"❌ Error loading file: {e}")


if __name__ == '__main__':
    cli()