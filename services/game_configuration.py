# services/game_configuration.py
"""
Game Configuration Management System
Provides settings-driven configuration for the dual game system with admin controls.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from incentive_service import DatabaseConnection

@dataclass
class DualGameConfig:
    """Master configuration for dual game system"""
    
    # System Enable/Disable
    system_enabled: bool = True
    category_a_enabled: bool = True
    category_b_enabled: bool = True
    
    # Difficulty Settings
    difficulty_levels: Dict[str, Dict] = field(default_factory=lambda: {
        'trivial': {
            'name': 'Trivial Tasks',
            'multiplier': 0.5,
            'examples': ['Daily attendance', 'Basic data entry'],
            'category_a_weight': 0.2,
            'category_b_weight': 0.8
        },
        'easy': {
            'name': 'Easy Tasks', 
            'multiplier': 1.0,
            'examples': ['Meeting targets', 'Helping colleagues'],
            'category_a_weight': 0.3,
            'category_b_weight': 0.7
        },
        'moderate': {
            'name': 'Moderate Achievements',
            'multiplier': 1.5,
            'examples': ['Exceeding targets', 'Process improvements'],
            'category_a_weight': 0.5,
            'category_b_weight': 0.5
        },
        'hard': {
            'name': 'Hard Accomplishments',
            'multiplier': 2.0,
            'examples': ['Major sales', 'Critical problem solving'],
            'category_a_weight': 0.8,
            'category_b_weight': 0.2
        },
        'extreme': {
            'name': 'Exceptional Performance',
            'multiplier': 3.0,
            'examples': ['Record breaking', 'Innovation awards'],
            'category_a_weight': 1.0,
            'category_b_weight': 0.0
        }
    })
    
    # Boost Algorithm Settings
    boost_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'threshold_percentile': 30.0,
        'max_multiplier': 2.0,
        'frequency_hours': 24,
        'random_variance': 0.1,
        'consecutive_loss_trigger': 5,
        'score_deficit_trigger': 100
    })
    
    # Win Cap Settings
    win_cap_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'multiplier': 1.5,
        'period_days': 30,
        'warning_threshold': 0.8,
        'hard_cap_points': 5000,
        'exclude_categories': []
    })
    
    # Exchange System Settings
    exchange_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'base_rates': {
            'bronze': {'points_per_token': 10, 'daily_limit': 50},
            'silver': {'points_per_token': 8, 'daily_limit': 100},
            'gold': {'points_per_token': 6, 'daily_limit': 200},
            'platinum': {'points_per_token': 5, 'daily_limit': 500}
        },
        'reverse_fee_percent': 20,
        'cooldown_hours': 6,
        'min_exchange': 5,
        'max_exchange': 1000
    })
    
    # Expiration Settings
    expiration_config: Dict[str, Any] = field(default_factory=lambda: {
        'category_a_expire_monthly': True,
        'category_b_token_hold_days': 60,
        'auto_reverse_threshold': 500,
        'warning_days_before': 7,
        'grace_period_days': 3
    })
    
    # Prize Pool Configuration
    prize_pools: Dict[str, Any] = field(default_factory=lambda: {
        'category_a': {
            'bronze': {
                'cash': {'monthly_limit': 1, 'value': 25},
                'pto': {'monthly_limit': 2, 'value': 2},
                'points': {'monthly_limit': 5, 'value': 100},
                'swag': {'monthly_limit': 10, 'value': 'item'}
            },
            'silver': {
                'cash': {'monthly_limit': 2, 'value': 50},
                'pto': {'monthly_limit': 4, 'value': 4},
                'points': {'monthly_limit': 8, 'value': 200},
                'swag': {'monthly_limit': 15, 'value': 'item'}
            },
            'gold': {
                'cash': {'monthly_limit': 3, 'value': 100},
                'pto': {'monthly_limit': 6, 'value': 6},
                'points': {'monthly_limit': 12, 'value': 300},
                'swag': {'monthly_limit': 20, 'value': 'item'}
            },
            'platinum': {
                'cash': {'monthly_limit': 5, 'value': 200},
                'pto': {'monthly_limit': 8, 'value': 8},
                'points': {'monthly_limit': 20, 'value': 500},
                'swag': {'monthly_limit': 30, 'value': 'item'}
            }
        },
        'category_b': {
            'global_daily_limits': {
                'jackpot': 1,
                'major': 5,
                'minor': 20,
                'basic': 100
            },
            'prizes': {
                'jackpot': {'pto': 8, 'swag': 'premium'},
                'major': {'pto': 4, 'swag': 'standard'},
                'minor': {'pto': 2, 'swag': 'basic'},
                'basic': {'points': 10, 'tokens': 5}
            }
        }
    })
    
    # Game-specific Settings
    game_settings: Dict[str, Any] = field(default_factory=lambda: {
        'slots': {
            'enabled': True,
            'token_cost': {'base': 5, 'scaling': True},
            'win_rates': {'jackpot': 0.01, 'major': 0.05, 'minor': 0.15, 'basic': 0.30}
        },
        'roulette': {
            'enabled': True,
            'token_cost': {'base': 10, 'scaling': True},
            'win_rates': {'jackpot': 0.005, 'major': 0.03, 'minor': 0.12, 'basic': 0.25}
        },
        'dice': {
            'enabled': True,
            'token_cost': {'base': 7, 'scaling': True},
            'win_rates': {'jackpot': 0.02, 'major': 0.08, 'minor': 0.20, 'basic': 0.35}
        },
        'wheel': {
            'enabled': True,
            'token_cost': {'base': 15, 'scaling': True},
            'win_rates': {'jackpot': 0.008, 'major': 0.04, 'minor': 0.10, 'basic': 0.28}
        }
    })
    
    # Voting Integration
    voting_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'positive_vote_game_chance': 80,
        'negative_vote_game_chance': 20,
        'vote_streak_bonus': True,
        'streak_threshold': 3,
        'guaranteed_category_a_on_streak': True
    })
    
    # Performance Settings
    performance_config: Dict[str, Any] = field(default_factory=lambda: {
        'cache_ttl_seconds': 30,
        'max_concurrent_users': 6,
        'batch_size': 10,
        'db_pool_size': 5,
        'request_timeout': 30
    })

class GameConfigurationManager:
    """Manages game configuration with database persistence"""
    
    def __init__(self):
        self.config_key = 'dual_game_config'
        self._config_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 60  # 1 minute cache
    
    def load_config(self, conn: Optional[DatabaseConnection] = None) -> DualGameConfig:
        """Load configuration from database or use defaults"""
        
        # Check cache
        if self._config_cache and self._cache_timestamp:
            if (datetime.now() - self._cache_timestamp).seconds < self._cache_ttl:
                return self._config_cache
        
        try:
            if conn:
                return self._load_from_db(conn)
            else:
                with DatabaseConnection() as db_conn:
                    return self._load_from_db(db_conn)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return DualGameConfig()
    
    def _load_from_db(self, conn) -> DualGameConfig:
        """Load configuration from database"""
        result = conn.execute("""
            SELECT value FROM settings WHERE key = ?
        """, (self.config_key,)).fetchone()
        
        if result:
            try:
                config_dict = json.loads(result['value'])
                config = DualGameConfig(**config_dict)
                
                # Cache the config
                self._config_cache = config
                self._cache_timestamp = datetime.now()
                
                return config
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Error parsing config JSON: {e}")
        
        # Return defaults and save them
        config = DualGameConfig()
        self.save_config(conn, config)
        return config
    
    def save_config(self, conn, config: DualGameConfig) -> bool:
        """Save configuration to database"""
        try:
            config_json = json.dumps(asdict(config), indent=2)
            
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, (self.config_key, config_json))
            
            conn.commit()
            
            # Update cache
            self._config_cache = config
            self._cache_timestamp = datetime.now()
            
            # Log config change
            conn.execute("""
                INSERT INTO history (employee_id, action, points_change, admin_id, created_at)
                VALUES ('SYSTEM', 'Game configuration updated', 0, 'ADMIN', CURRENT_TIMESTAMP)
            """)
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            return False
    
    def update_setting(self, conn, category: str, setting: str, value: Any) -> bool:
        """Update a specific configuration setting"""
        try:
            config = self.load_config(conn)
            
            # Navigate to the setting
            if hasattr(config, category):
                category_obj = getattr(config, category)
                if isinstance(category_obj, dict) and setting in category_obj:
                    category_obj[setting] = value
                else:
                    setattr(config, category, value)
            
            return self.save_config(conn, config)
            
        except Exception as e:
            logging.error(f"Error updating setting {category}.{setting}: {e}")
            return False
    
    def get_difficulty_for_rule(self, conn, rule_id: int) -> int:
        """Determine difficulty level for a rule"""
        result = conn.execute("""
            SELECT points, description FROM rules WHERE rule_id = ?
        """, (rule_id,)).fetchone()
        
        if not result:
            return 2  # Default to easy
        
        points = abs(result['points'])
        
        # Map points to difficulty
        if points <= 5:
            return 1  # Trivial
        elif points <= 10:
            return 2  # Easy
        elif points <= 20:
            return 3  # Moderate
        elif points <= 50:
            return 4  # Hard
        else:
            return 5  # Extreme
    
    def get_tier_config(self, tier: str) -> Dict:
        """Get configuration for a specific tier"""
        config = self.load_config()
        
        tier_settings = {
            'exchange_rate': config.exchange_config['base_rates'].get(tier, {}).get('points_per_token', 10),
            'daily_limit': config.exchange_config['base_rates'].get(tier, {}).get('daily_limit', 50),
            'prize_limits': config.prize_pools['category_a'].get(tier, {}),
            'boost_eligible': tier in ['bronze', 'silver']
        }
        
        return tier_settings
    
    def validate_config(self, config: DualGameConfig) -> List[str]:
        """Validate configuration for consistency and errors"""
        errors = []
        
        # Check boost settings
        if config.boost_config['threshold_percentile'] < 0 or config.boost_config['threshold_percentile'] > 100:
            errors.append("Boost threshold percentile must be between 0 and 100")
        
        if config.boost_config['max_multiplier'] < 1:
            errors.append("Boost max multiplier must be at least 1")
        
        # Check win cap settings
        if config.win_cap_config['multiplier'] < 1:
            errors.append("Win cap multiplier must be at least 1")
        
        # Check exchange rates
        for tier, settings in config.exchange_config['base_rates'].items():
            if settings['points_per_token'] <= 0:
                errors.append(f"Exchange rate for {tier} must be positive")
            if settings['daily_limit'] <= 0:
                errors.append(f"Daily limit for {tier} must be positive")
        
        # Check game settings
        for game, settings in config.game_settings.items():
            if settings['token_cost']['base'] <= 0:
                errors.append(f"Token cost for {game} must be positive")
            
            total_rate = sum(settings['win_rates'].values())
            if total_rate > 1.0:
                errors.append(f"Win rates for {game} exceed 100%")
        
        return errors
    
    def export_config(self, conn) -> str:
        """Export current configuration as JSON string"""
        config = self.load_config(conn)
        return json.dumps(asdict(config), indent=2)
    
    def import_config(self, conn, config_json: str) -> Tuple[bool, List[str]]:
        """Import configuration from JSON string"""
        try:
            config_dict = json.loads(config_json)
            config = DualGameConfig(**config_dict)
            
            # Validate before saving
            errors = self.validate_config(config)
            if errors:
                return False, errors
            
            success = self.save_config(conn, config)
            return success, []
            
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except TypeError as e:
            return False, [f"Invalid configuration structure: {e}"]
    
    def get_admin_display_config(self) -> Dict:
        """Get configuration formatted for admin UI display"""
        config = self.load_config()
        
        return {
            'system_status': {
                'enabled': config.system_enabled,
                'category_a': config.category_a_enabled,
                'category_b': config.category_b_enabled
            },
            'difficulty_levels': [
                {
                    'id': key,
                    'name': val['name'],
                    'multiplier': val['multiplier'],
                    'examples': ', '.join(val['examples']),
                    'category_a_weight': f"{val['category_a_weight']*100:.0f}%",
                    'category_b_weight': f"{val['category_b_weight']*100:.0f}%"
                }
                for key, val in config.difficulty_levels.items()
            ],
            'boost_algorithm': {
                'enabled': config.boost_config['enabled'],
                'threshold': f"Bottom {config.boost_config['threshold_percentile']:.0f}%",
                'max_boost': f"{config.boost_config['max_multiplier']}x",
                'cooldown': f"{config.boost_config['frequency_hours']} hours"
            },
            'win_caps': {
                'enabled': config.win_cap_config['enabled'],
                'max_win': f"{config.win_cap_config['multiplier']}x non-gambling max",
                'period': f"{config.win_cap_config['period_days']} days",
                'hard_cap': f"{config.win_cap_config['hard_cap_points']} points"
            },
            'exchange_rates': config.exchange_config['base_rates'],
            'expiration': {
                'category_a': 'End of month' if config.expiration_config['category_a_expire_monthly'] else 'Never',
                'tokens': f"{config.expiration_config['category_b_token_hold_days']} days",
                'auto_reverse': f"At {config.expiration_config['auto_reverse_threshold']} tokens"
            },
            'games': {
                game: {
                    'enabled': settings['enabled'],
                    'cost': f"{settings['token_cost']['base']} tokens",
                    'jackpot_rate': f"{settings['win_rates']['jackpot']*100:.1f}%"
                }
                for game, settings in config.game_settings.items()
            }
        }

# Global instance
game_config_manager = GameConfigurationManager()

# Convenience functions
def get_config() -> DualGameConfig:
    """Get current game configuration"""
    return game_config_manager.load_config()

def update_config(category: str, setting: str, value: Any) -> bool:
    """Update a configuration setting"""
    with DatabaseConnection() as conn:
        return game_config_manager.update_setting(conn, category, setting, value)

def validate_current_config() -> List[str]:
    """Validate current configuration"""
    config = get_config()
    return game_config_manager.validate_config(config)

from typing import Tuple