#!/usr/bin/env python3
"""
Generate sample data for testing the FinOps Dashboard.
This script creates realistic mock AWS usage data for demonstration purposes.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import DatabaseManager
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_aws_data(days: int = 30) -> list:
    """Generate sample AWS usage data."""
    
    # Free tier services with realistic usage patterns
    services_config = {
        'Amazon Elastic Compute Cloud - Compute': {
            't2.micro': {
                'base_usage': 20,  # hours per day
                'variation': 5,
                'limit': 750,  # monthly limit
                'unit': 'hours',
                'cost_per_unit': 0.0116  # cost if over limit
            }
        },
        'Amazon Simple Storage Service': {
            'Standard Storage': {
                'base_usage': 2.5,  # GB
                'variation': 0.5,
                'limit': 5,
                'unit': 'GB',
                'cost_per_unit': 0.023
            },
            'GET Requests': {
                'base_usage': 500,  # requests per day
                'variation': 200,
                'limit': 20000,  # monthly
                'unit': 'requests',
                'cost_per_unit': 0.0004
            }
        },
        'AWS Lambda': {
            'Requests': {
                'base_usage': 25000,  # requests per day
                'variation': 10000,
                'limit': 1000000,  # monthly
                'unit': 'requests',
                'cost_per_unit': 0.0000002
            },
            'Duration': {
                'base_usage': 8000,  # GB-seconds per day
                'variation': 3000,
                'limit': 400000,  # monthly
                'unit': 'GB-seconds',
                'cost_per_unit': 0.0000166667
            }
        },
        'Amazon Relational Database Service': {
            'db.t2.micro': {
                'base_usage': 18,  # hours per day
                'variation': 2,
                'limit': 750,  # monthly
                'unit': 'hours',
                'cost_per_unit': 0.017
            },
            'Storage': {
                'base_usage': 8,  # GB
                'variation': 2,
                'limit': 20,  # monthly
                'unit': 'GB',
                'cost_per_unit': 0.10
            }
        },
        'Amazon DynamoDB': {
            'Storage': {
                'base_usage': 12,  # GB
                'variation': 3,
                'limit': 25,  # always free
                'unit': 'GB',
                'cost_per_unit': 0.25
            },
            'Read Capacity': {
                'base_usage': 15,  # RCU
                'variation': 5,
                'limit': 25,
                'unit': 'RCU',
                'cost_per_unit': 0.00013
            }
        }
    }
    
    sample_data = []
    end_date = datetime.now().date()
    
    for i in range(days):
        current_date = end_date - timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        
        for service_name, usage_types in services_config.items():
            for usage_type, config in usage_types.items():
                # Generate realistic usage with some randomness
                base = config['base_usage']
                variation = config['variation']
                usage_amount = max(0, base + random.uniform(-variation, variation))
                
                # Add weekly patterns (lower usage on weekends for some services)
                if current_date.weekday() in [5, 6]:  # Weekend
                    if 'Compute' in service_name or 'Database' in service_name:
                        usage_amount *= 0.7  # Reduce weekend usage
                
                # Calculate cost (0 if within free tier for the month)
                monthly_usage = usage_amount * 30  # Rough monthly estimate
                cost = 0.0
                
                if monthly_usage > config['limit']:
                    excess_usage = usage_amount  # Simplified - in reality would need month-to-date tracking
                    cost = excess_usage * config['cost_per_unit']
                
                # Add some random small costs to simulate edge cases
                if random.random() < 0.05:  # 5% chance of small unexpected cost
                    cost += random.uniform(0.01, 0.50)
                
                sample_data.append({
                    'date': date_str,
                    'service': service_name,
                    'usage_type': usage_type,
                    'usage_amount': round(usage_amount, 2),
                    'usage_unit': config['unit'],
                    'cost': round(cost, 4),
                    'currency': 'USD'
                })
    
    return sample_data


def populate_sample_data(db_path: str = "data/finops_dashboard.db", days: int = 30):
    """Populate database with sample data."""
    
    # Initialize database
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_tables()
    
    # Generate and insert sample data
    logger.info(f"Generating {days} days of sample AWS usage data...")
    sample_data = generate_sample_aws_data(days)
    
    logger.info(f"Inserting {len(sample_data)} sample records into database...")
    db_manager.insert_usage_data(sample_data)
    
    # Generate some sample alerts
    logger.info("Generating sample alerts...")
    current_month = datetime.now().strftime('%Y-%m')
    usage_status = db_manager.check_free_tier_usage(current_month)
    
    alerts_created = 0
    for service_usage in usage_status:
        if service_usage.get('usage_percentage', 0) >= 75:
            db_manager.create_free_tier_alert(
                service_usage['service'],
                service_usage['usage_type'],
                service_usage['total_usage'],
                service_usage['free_tier_limit']
            )
            alerts_created += 1
    
    logger.info(f"Created {alerts_created} sample alerts")
    
    # Print summary
    logger.info("Sample data generation complete!")
    logger.info(f"- Database: {db_path}")
    logger.info(f"- Records: {len(sample_data)}")
    logger.info(f"- Date range: {days} days")
    logger.info(f"- Services: {len(set(r['service'] for r in sample_data))}")
    
    return sample_data


def generate_usage_scenarios():
    """Generate specific usage scenarios for testing."""
    scenarios = [
        {
            'name': 'High EC2 Usage',
            'description': 'EC2 instance running 24/7 - will breach 750h limit',
            'service': 'Amazon Elastic Compute Cloud - Compute',
            'usage_type': 't2.micro',
            'daily_usage': 24,  # 24 hours/day = 744 hours/month (close to limit)
        },
        {
            'name': 'S3 Storage Breach',
            'description': 'S3 storage growing beyond 5GB limit',
            'service': 'Amazon Simple Storage Service',
            'usage_type': 'Standard Storage',
            'daily_usage': 6.0,  # 6GB (over 5GB limit)
        },
        {
            'name': 'Lambda Heavy Usage',
            'description': 'High Lambda usage approaching 1M request limit',
            'service': 'AWS Lambda',
            'usage_type': 'Requests',
            'daily_usage': 35000,  # 35K/day = ~1M/month
        },
        {
            'name': 'Safe Usage',
            'description': 'All services well within limits',
            'service': 'Amazon DynamoDB',
            'usage_type': 'Storage',
            'daily_usage': 8,  # 8GB (well under 25GB limit)
        }
    ]
    
    return scenarios


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sample data for FinOps Dashboard')
    parser.add_argument('--days', type=int, default=30, help='Number of days of sample data')
    parser.add_argument('--db-path', default='data/finops_dashboard.db', help='Database path')
    parser.add_argument('--scenarios', action='store_true', help='Generate specific test scenarios')
    
    args = parser.parse_args()
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)
    
    # Generate sample data
    sample_data = populate_sample_data(args.db_path, args.days)
    
    if args.scenarios:
        logger.info("\nAvailable test scenarios:")
        scenarios = generate_usage_scenarios()
        for i, scenario in enumerate(scenarios, 1):
            logger.info(f"{i}. {scenario['name']}: {scenario['description']}")
    
    logger.info(f"\nTo view the dashboard with sample data:")
    logger.info(f"cd src && python dashboard.py")
    logger.info(f"Then visit: http://localhost:8050")
    
    logger.info(f"\nTo check usage status:")
    logger.info(f"cd src && python -c \"from database import DatabaseManager; db=DatabaseManager('{args.db_path}'); status=db.check_free_tier_usage(); print(f'Services tracked: {{len(status)}}')\"")
