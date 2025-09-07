"""
Configuration management for Free Tier FinOps Dashboard.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration manager for the FinOps Dashboard."""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """Initialize configuration."""
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # Default configuration values
        self.defaults = {
            'database_path': 'data/finops_dashboard.db',
            'aws_region': 'us-east-1',
            'aws_profile': None,
            'aws_enabled': True,
            'gcp_enabled': False,
            'alert_thresholds': {
                'warning': 75.0,
                'critical': 90.0
            },
            'monitoring': {
                'check_interval_hours': 6,
                'report_email': None,
                'enable_cost_alerts': True
            },
            'free_tier_focus': True,
            'max_monthly_cost_alert': 1.0  # Alert if monthly cost exceeds $1
        }
        
        # Load configuration
        self._config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables."""
        config = self.defaults.copy()
        
        # Try to load from YAML file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                    config.update(file_config)
                self.logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                self.logger.warning(f"Could not load config file {self.config_file}: {e}")
        
        # Override with environment variables
        config.update(self._load_from_env())
        
        return config
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # AWS Configuration
        if os.getenv('AWS_REGION'):
            env_config['aws_region'] = os.getenv('AWS_REGION')
        
        if os.getenv('AWS_PROFILE'):
            env_config['aws_profile'] = os.getenv('AWS_PROFILE')
        
        # Database
        if os.getenv('DATABASE_PATH'):
            env_config['database_path'] = os.getenv('DATABASE_PATH')
        
        # Monitoring
        if os.getenv('REPORT_EMAIL'):
            env_config.setdefault('monitoring', {})['report_email'] = os.getenv('REPORT_EMAIL')
        
        if os.getenv('MAX_MONTHLY_COST'):
            try:
                env_config['max_monthly_cost_alert'] = float(os.getenv('MAX_MONTHLY_COST'))
            except ValueError:
                self.logger.warning("Invalid MAX_MONTHLY_COST value in environment")
        
        return env_config
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Ensure config directory exists
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Could not save config to {self.config_file}: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value):
        """Set configuration value."""
        keys = key.split('.')
        config_dict = self._config
        
        # Navigate to the parent dict
        for k in keys[:-1]:
            if k not in config_dict:
                config_dict[k] = {}
            config_dict = config_dict[k]
        
        # Set the value
        config_dict[keys[-1]] = value
    
    # Convenient property accessors
    @property
    def database_path(self) -> str:
        return self.get('database_path')
    
    @property
    def aws_region(self) -> str:
        return self.get('aws_region')
    
    @property
    def aws_profile(self) -> Optional[str]:
        return self.get('aws_profile')
    
    @property
    def aws_enabled(self) -> bool:
        return self.get('aws_enabled', True)
    
    @property
    def gcp_enabled(self) -> bool:
        return self.get('gcp_enabled', False)
    
    @property
    def alert_thresholds(self) -> Dict[str, float]:
        return self.get('alert_thresholds', {'warning': 75.0, 'critical': 90.0})
    
    @property
    def free_tier_focus(self) -> bool:
        return self.get('free_tier_focus', True)
    
    @property
    def max_monthly_cost_alert(self) -> float:
        return self.get('max_monthly_cost_alert', 1.0)
    
    @property
    def report_email(self) -> Optional[str]:
        return self.get('monitoring.report_email')
    
    @property
    def check_interval_hours(self) -> int:
        return self.get('monitoring.check_interval_hours', 6)
    
    def validate_aws_credentials(self) -> bool:
        """Validate AWS credentials are available."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            
            # Try to create a session and check credentials
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile)
            else:
                session = boto3.Session()
            
            # Try to get caller identity (minimal API call)
            sts_client = session.client('sts', region_name=self.aws_region)
            sts_client.get_caller_identity()
            
            return True
            
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            return False
        except ClientError as e:
            self.logger.error(f"AWS credentials validation failed: {e}")
            return False
        except ImportError:
            self.logger.error("boto3 not installed")
            return False
    
    def get_aws_free_tier_services(self) -> Dict[str, Dict[str, Any]]:
        """Get AWS Free Tier service definitions with limits."""
        return {
            'ec2': {
                'name': 'Amazon Elastic Compute Cloud - Compute',
                'limits': {
                    't2.micro': {'value': 750, 'unit': 'hours', 'period': 'monthly'}
                },
                'description': 'Free t2.micro instance for 750 hours per month'
            },
            's3': {
                'name': 'Amazon Simple Storage Service',
                'limits': {
                    'Standard Storage': {'value': 5, 'unit': 'GB', 'period': 'monthly'},
                    'GET Requests': {'value': 20000, 'unit': 'requests', 'period': 'monthly'},
                    'PUT Requests': {'value': 2000, 'unit': 'requests', 'period': 'monthly'}
                },
                'description': '5 GB storage, 20K GET requests, 2K PUT requests per month'
            },
            'lambda': {
                'name': 'AWS Lambda',
                'limits': {
                    'Requests': {'value': 1000000, 'unit': 'requests', 'period': 'monthly'},
                    'Duration': {'value': 400000, 'unit': 'GB-seconds', 'period': 'monthly'}
                },
                'description': '1M free requests and 400K GB-seconds per month'
            },
            'rds': {
                'name': 'Amazon Relational Database Service',
                'limits': {
                    'db.t2.micro': {'value': 750, 'unit': 'hours', 'period': 'monthly'},
                    'Storage': {'value': 20, 'unit': 'GB', 'period': 'monthly'}
                },
                'description': 'db.t2.micro for 750 hours and 20 GB storage per month'
            },
            'dynamodb': {
                'name': 'Amazon DynamoDB',
                'limits': {
                    'Storage': {'value': 25, 'unit': 'GB', 'period': 'monthly'},
                    'Read Capacity': {'value': 25, 'unit': 'RCU', 'period': 'monthly'},
                    'Write Capacity': {'value': 25, 'unit': 'WCU', 'period': 'monthly'}
                },
                'description': '25 GB storage, 25 RCU, 25 WCU per month'
            }
        }
