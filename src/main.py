#!/usr/bin/env python3
"""
FinOps Dashboard - Cloud Cost Visibility Tool
Main application entry point for monitoring cloud resource usage and costs.
"""

import logging
import sys
import argparse
from datetime import datetime, timedelta
from typing import Optional

from aws_client import AWSCostClient
from gcp_client import GCPBillingClient
from database import DatabaseManager
from alerts import AlertManager
from config import Config


def setup_logging(level: str = 'INFO') -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data/finops_dashboard.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description='FinOps Dashboard - Cloud Cost Monitoring')
    parser.add_argument('--provider', choices=['aws', 'gcp', 'both'], default='both',
                       help='Cloud provider to monitor (default: both)')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to fetch data for (default: 7)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--log-level', default='INFO',
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = Config(args.config)
        
        # Initialize database
        db_manager = DatabaseManager(config.database_path)
        db_manager.initialize_tables()
        
        # Initialize alert manager
        alert_manager = AlertManager(config)
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.days)
        
        logger.info(f"Fetching cost data from {start_date} to {end_date}")
        
        # Process AWS data if configured
        if args.provider in ['aws', 'both'] and config.aws_enabled:
            logger.info("Processing AWS cost data...")
            aws_client = AWSCostClient(config)
            aws_data = aws_client.get_cost_and_usage(start_date, end_date)
            db_manager.insert_cost_data('aws', aws_data)
            
            # Check for alerts
            aws_alerts = alert_manager.check_aws_alerts(aws_data)
            if aws_alerts:
                logger.warning(f"AWS alerts triggered: {len(aws_alerts)}")
                for alert in aws_alerts:
                    logger.warning(f"Alert: {alert}")
        
        # Process GCP data if configured
        if args.provider in ['gcp', 'both'] and config.gcp_enabled:
            logger.info("Processing GCP billing data...")
            gcp_client = GCPBillingClient(config)
            gcp_data = gcp_client.get_billing_data(start_date, end_date)
            db_manager.insert_cost_data('gcp', gcp_data)
            
            # Check for alerts
            gcp_alerts = alert_manager.check_gcp_alerts(gcp_data)
            if gcp_alerts:
                logger.warning(f"GCP alerts triggered: {len(gcp_alerts)}")
                for alert in gcp_alerts:
                    logger.warning(f"Alert: {alert}")
        
        logger.info("Data processing completed successfully")
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
