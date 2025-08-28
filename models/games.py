# models/games.py
# Game logic and models

import random
import json
import logging
from datetime import datetime
from incentive_service import adjust_points, award_mini_game, play_mini_game


def get_game_odds_and_prizes(conn, game_type):
    """Get game odds and available prizes from database."""
    # Get odds
    odds_row = conn.execute(
        "SELECT win_probability, jackpot_probability FROM game_odds WHERE game_type=?", 
        (game_type,)
    ).fetchone()
    
    if not odds_row:
        # Default fallback odds
        odds = {'win_probability': 0.3, 'jackpot_probability': 0.05}
    else:
        odds = {'win_probability': odds_row['win_probability'], 'jackpot_probability': odds_row['jackpot_probability']}
    
    # Get available prizes
    prizes = conn.execute(
        "SELECT prize_type, prize_amount, prize_description, probability, is_jackpot FROM game_prizes WHERE game_type=? ORDER BY probability DESC",
        (game_type,)
    ).fetchall()
    
    if not prizes:
        # Default fallback prizes
        prizes = [
            {'prize_type': 'points', 'prize_amount': 5, 'prize_description': '5 Points', 'probability': 0.2, 'is_jackpot': 0},
            {'prize_type': 'points', 'prize_amount': 10, 'prize_description': '10 Points', 'probability': 0.1, 'is_jackpot': 0}
        ]
    
    return odds, prizes


def select_prize_by_probability(prizes):
    """Select a prize based on probability weights."""
    total_prob = sum(p['probability'] for p in prizes)
    rand_val = random.random() * total_prob
    
    cumulative = 0
    for prize in prizes:
        cumulative += prize['probability']
        if rand_val <= cumulative:
            return prize
    
    # Fallback to first prize
    return prizes[0] if prizes else None


def record_mini_game_payout(conn, game_id, employee_id, game_type, prize_type, prize_amount, dollar_value):
    """Record payout for analytics and tracking."""
    try:
        conn.execute("""
            INSERT INTO mini_game_payouts 
            (game_id, employee_id, game_type, prize_type, prize_amount, dollar_value, payout_date)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (game_id, employee_id, game_type, prize_type, prize_amount, dollar_value))
        logging.debug(f"Recorded payout: Game {game_id}, Employee {employee_id}, ${dollar_value}")
    except Exception as e:
        logging.error(f"Failed to record mini-game payout: {e}")


def play_slot_machine_game(conn, config):
    """Professional 3-reel slot machine with database-driven odds."""
    odds, prizes = get_game_odds_and_prizes(conn, 'slot')
    
    symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '🔔', '7️⃣']
    weights = [20, 18, 15, 12, 10, 8, 5, 2]  # Weighted probability
    
    reels = []
    for _ in range(3):
        reel = random.choices(symbols, weights=weights)[0]
        reels.append(reel)
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {'reels': reels, 'pattern': 'slots'},
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description,
        'dollar_value': dollar_value
    }


def play_scratch_off_game(conn, config):
    """Scratch-off lottery with database-driven prizes."""
    odds, prizes = get_game_odds_and_prizes(conn, 'scratch')
    
    # Generate scratch pattern
    scratch_symbols = ['💰', '⭐', '🍀', '🎁', '❌', '💎', '🍒']
    scratch_grid = []
    for _ in range(3):
        row = [random.choice(scratch_symbols) for _ in range(3)]
        scratch_grid.append(row)
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    winning_symbol = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
            
        # Add some winning symbols to the grid for visual effect
        flat_grid = [item for row in scratch_grid for item in row]
        symbol_counts = {symbol: flat_grid.count(symbol) for symbol in set(flat_grid)}
        winning_symbol = max(symbol_counts, key=symbol_counts.get)
    
    return {
        'outcome': {
            'grid': scratch_grid, 
            'winning_symbol': winning_symbol
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description,
        'dollar_value': dollar_value
    }


def play_roulette_game(conn, config):
    """Mini roulette with database-driven odds."""
    odds, prizes = get_game_odds_and_prizes(conn, 'roulette')
    
    winning_number = random.randint(0, 36)
    color = 'green' if winning_number == 0 else ('red' if winning_number % 2 == 1 else 'black')
    
    # Simple betting system - bet on color
    player_bet = random.choice(['red', 'black', 'green'])
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {
            'number': winning_number,
            'color': color,
            'bet': player_bet
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def play_wheel_game(conn, config):
    """Wheel of Fortune style spinning wheel game with database-driven odds."""
    odds, prizes = get_game_odds_and_prizes(conn, 'wheel')
    
    # Define wheel segments for visual display
    segments = [
        {'name': '6 Points', 'color': '#4CAF50'},
        {'name': '12 Points', 'color': '#2196F3'},
        {'name': '20 Points', 'color': '#FF9800'},
        {'name': 'Early Lunch', 'color': '#9C27B0'},
        {'name': 'WHEEL WINNER!', 'color': '#FFD700'},
        {'name': '6 Points', 'color': '#607D8B'},
        {'name': '12 Points', 'color': '#E91E63'},
        {'name': 'Try Again', 'color': '#F44336'}
    ]
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    # Select segment for animation (random for visual effect)
    selected_segment = random.choice(segments)
    
    # Calculate final spin position (for animation)
    segment_angle = 360 / len(segments)
    segment_index = segments.index(selected_segment)
    final_angle = segment_index * segment_angle + random.uniform(0, segment_angle)
    
    # Add multiple rotations for spinning effect
    spin_rotations = random.randint(3, 8)
    total_angle = (spin_rotations * 360) + final_angle
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {
            'winning_segment': selected_segment,
            'angle': total_angle,
            'segments': segments  # Include all segments for wheel display
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def play_dice_game(conn, config):
    """Vegas-style dice game with database-driven odds."""
    odds, prizes = get_game_odds_and_prizes(conn, 'dice')
    
    # Roll two dice
    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    total = die1 + die2
    
    # Determine if this is a win based on database odds
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    # Special winning conditions for visual appeal
    is_double = (die1 == die2)
    is_lucky_seven = (total == 7)
    is_snake_eyes = (die1 == 1 and die2 == 1)
    is_boxcars = (die1 == 6 and die2 == 6)
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        # Select prize based on configured probabilities
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
            
            # Special messaging for dice combinations
            if is_snake_eyes:
                prize_description = f"SNAKE EYES! {prize_description}"
            elif is_boxcars:
                prize_description = f"BOXCARS! {prize_description}"  
            elif is_lucky_seven:
                prize_description = f"LUCKY SEVEN! {prize_description}"
            elif is_double:
                prize_description = f"DOUBLE {die1}s! {prize_description}"
    
    return {
        'outcome': {
            'dice': [die1, die2],
            'total': total,
            'is_double': is_double,
            'is_lucky_seven': is_lucky_seven,
            'is_snake_eyes': is_snake_eyes,
            'is_boxcars': is_boxcars
        },
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def play_generic_game(conn, config):
    """Fallback generic game with database-driven odds."""
    # Try to get odds from database, fallback to defaults
    try:
        odds, prizes = get_game_odds_and_prizes(conn, 'generic')
    except:
        odds = {'win_probability': 0.3, 'jackpot_probability': 0.05}
        prizes = [{'prize_type': 'points', 'prize_amount': 5, 'prize_description': '5 Points', 'probability': 0.2, 'is_jackpot': 0}]
    
    win_roll = random.random()
    win = win_roll < odds['win_probability']
    
    prize_amount = 0
    prize_type = 'points'
    dollar_value = 0.0
    prize_description = None
    
    if win:
        selected_prize = select_prize_by_probability(prizes)
        if selected_prize:
            prize_amount = selected_prize['prize_amount'] or 0
            prize_type = selected_prize['prize_type']
            prize_description = selected_prize['prize_description']
            dollar_value = getattr(selected_prize, 'dollar_value', 0.0) or 0.0
    
    return {
        'outcome': {'type': 'generic', 'roll': random.randint(1, 100)},
        'win': win,
        'prize_type': prize_type,
        'prize_amount': prize_amount,
        'prize_description': prize_description
    }


def execute_game_logic(conn, game_id, game_type, employee_id, settings):
    """Execute game logic and handle prizes."""
    cfg = json.loads(settings.get('mini_game_settings', '{}'))
    
    # Play the specific game type with database-driven odds
    if game_type == 'slot':
        result = play_slot_machine_game(conn, cfg)
    elif game_type == 'scratch':
        result = play_scratch_off_game(conn, cfg)
    elif game_type == 'wheel':
        result = play_wheel_game(conn, cfg)
    elif game_type == 'roulette':
        result = play_roulette_game(conn, cfg)
    elif game_type == 'dice':
        result = play_dice_game(conn, cfg)
    else:
        result = play_generic_game(conn, cfg)
    
    # Process the game outcome
    outcome_data = {
        'game_type': game_type,
        'result': result['outcome'],
        'win': result['win'],
        'prize_type': result.get('prize_type'),
        'prize_amount': result.get('prize_amount', 0),
        'prize_description': result.get('prize_description'),
        'dollar_value': result.get('dollar_value', 0.0),
        'timestamp': datetime.now().isoformat()
    }
    
    # Award prizes if won
    if result['win']:
        prize_type = result.get('prize_type')
        prize_amount = result.get('prize_amount', 0)
        dollar_value = result.get('dollar_value', 0.0)
        
        # Handle different prize types
        if prize_type == 'points' and prize_amount > 0:
            # Award points
            adjust_points(
                conn, 
                employee_id, 
                prize_amount, 
                "SYSTEM",
                f"Vegas {game_type.title()} Game Win",
                f"Automated prize from {game_type} mini-game (Game ID: {game_id})"
            )
        elif prize_type == 'mini_game':
            # Award another random mini game
            award_mini_game(conn, employee_id, random.choice(['slot', 'scratch', 'roulette', 'wheel', 'dice']))
        
        # Track payout regardless of prize type
        record_mini_game_payout(
            conn, game_id, employee_id, game_type,
            prize_type, prize_amount, dollar_value
        )
    
    # Record the game play
    play_mini_game(conn, game_id, json.dumps(outcome_data))
    
    return result, outcome_data