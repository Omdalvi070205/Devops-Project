"""
AWS Cost Explorer API client for fetching cloud cost and usage data.
"""

import boto3
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError


class AWSCostClient:
    """Client for interacting with AWS Cost Explorer API."""
    
    def __init__(self, config):
        """Initialize AWS Cost Explorer client."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        try:
            # Initialize boto3 client
            if config.aws_profile:
                session = boto3.Session(profile_name=config.aws_profile)
                self.cost_client = session.client('ce', region_name=config.aws_region)
            else:
                self.cost_client = boto3.client('ce', region_name=config.aws_region)
                
        except NoCredentialsError:
            self.logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
    
    def get_cost_and_usage(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Fetch cost and usage data from AWS Cost Explorer.
        
        Args:
            start_date: Start date for cost data
            end_date: End date for cost data
            
        Returns:
            List of cost and usage records
        """
        try:
            response = self.cost_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
                ]
            )
            
            cost_data = []
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service = group['Keys'][0] if group['Keys'] else 'Unknown'
                    usage_type = group['Keys'][1] if len(group['Keys']) > 1 else 'Unknown'
                    
                    blended_cost = float(group['Metrics']['BlendedCost']['Amount'])
                    usage_quantity = float(group['Metrics']['UsageQuantity']['Amount'])
                    
                    cost_data.append({
                        'date': result['TimePeriod']['Start'],
                        'service': service,
                        'usage_type': usage_type,
                        'cost': blended_cost,
                        'usage_quantity': usage_quantity,
                        'currency': group['Metrics']['BlendedCost']['Unit']
                    })
            
            self.logger.info(f"Retrieved {len(cost_data)} AWS cost records")
            return cost_data
            
        except ClientError as e:
            self.logger.error(f"AWS API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching AWS cost data: {e}")
            raise
    
    def get_service_usage_forecast(self, service: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get usage forecast for a specific AWS service.
        
        Args:
            service: AWS service name
            days: Number of days to forecast
            
        Returns:
            Forecast data or None if unavailable
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date.replace(day=1)  # Start of current month
            
            response = self.cost_client.get_usage_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric='USAGE_QUANTITY',
                Granularity='MONTHLY',
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service]
                    }
                }
            )
            
            if response.get('ForecastResultsByTime'):
                forecast = response['ForecastResultsByTime'][0]
                return {
                    'service': service,
                    'forecasted_usage': float(forecast['MeanValue']),
                    'period': forecast['TimePeriod']
                }
                
        except ClientError as e:
            self.logger.warning(f"Could not get forecast for {service}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error getting forecast for {service}: {e}")
            return None
    
    def get_free_tier_usage(self) -> List[Dict[str, Any]]:
        """
        Get AWS Free Tier usage information.
        
        Returns:
            List of free tier usage records
        """
        try:
            # Get current month data
            now = datetime.now()
            start_date = now.replace(day=1).date()
            end_date = now.date()
            
            response = self.cost_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'RECORD_TYPE',
                        'Values': ['Usage']
                    }
                }
            )
            
            free_tier_services = [
                'Amazon Elastic Compute Cloud - Compute',
                'Amazon Simple Storage Service',
                'Amazon Relational Database Service',
                'AWS Lambda',
                'Amazon CloudWatch'
            ]
            
            usage_data = []
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service = group['Keys'][0] if group['Keys'] else 'Unknown'
                    usage_type = group['Keys'][1] if len(group['Keys']) > 1 else 'Unknown'
                    
                    if service in free_tier_services:
                        usage_quantity = float(group['Metrics']['UsageQuantity']['Amount'])
                        
                        usage_data.append({
                            'service': service,
                            'usage_type': usage_type,
                            'usage_quantity': usage_quantity,
                            'month': result['TimePeriod']['Start'][:7]  # YYYY-MM format
                        })
            
            return usage_data
            
        except ClientError as e:
            self.logger.error(f"Error fetching free tier usage: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching free tier usage: {e}")
            raise
