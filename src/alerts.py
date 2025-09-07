"""
Alert manager for AWS Free Tier usage monitoring and breach detection.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import DatabaseManager


class FreeTierAlertManager:
    """Manages alerts for AWS Free Tier usage monitoring."""
    
    def __init__(self, config, db_manager: DatabaseManager):
        """Initialize alert manager."""
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Alert thresholds (percentage of free tier limit)
        self.alert_thresholds = {
            'warning': 75.0,    # 75% of limit
            'critical': 90.0,   # 90% of limit
            'breach': 100.0     # Over limit (incurring charges)
        }
    
    def check_free_tier_alerts(self, usage_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check usage data against free tier limits and generate alerts.
        
        Args:
            usage_data: List of usage records from AWS
            
        Returns:
            List of alerts generated
        """
        alerts = []
        current_month = datetime.now().strftime('%Y-%m')
        
        # Get current month's usage status
        usage_status = self.db_manager.check_free_tier_usage(current_month)
        
        for service_usage in usage_status:
            if service_usage.get('free_tier_limit'):
                usage_percentage = service_usage.get('usage_percentage', 0)
                
                # Check for alerts
                if usage_percentage >= self.alert_thresholds['critical']:
                    alert = self._create_alert(
                        service_usage['service'],
                        service_usage['usage_type'],
                        'critical',
                        usage_percentage,
                        service_usage['total_usage'],
                        service_usage['free_tier_limit']
                    )
                    alerts.append(alert)
                    
                elif usage_percentage >= self.alert_thresholds['warning']:
                    alert = self._create_alert(
                        service_usage['service'],
                        service_usage['usage_type'],
                        'warning',
                        usage_percentage,
                        service_usage['total_usage'],
                        service_usage['free_tier_limit']
                    )
                    alerts.append(alert)
        
        # Log alerts
        if alerts:
            self.logger.warning(f"Generated {len(alerts)} free tier alerts")
            for alert in alerts:
                self.logger.warning(f"Alert: {alert['message']}")
        
        return alerts
    
    def _create_alert(self, service: str, usage_type: str, severity: str,
                     usage_percentage: float, current_usage: float, 
                     limit: float) -> Dict[str, Any]:
        """Create an alert record."""
        messages = {
            'warning': f"⚠️  WARNING: {service} ({usage_type}) is at {usage_percentage:.1f}% of free tier limit",
            'critical': f"🚨 CRITICAL: {service} ({usage_type}) is at {usage_percentage:.1f}% of free tier limit - charges may apply soon!",
            'breach': f"💰 BREACH: {service} ({usage_type}) has exceeded free tier limit - charges are being incurred!"
        }
        
        alert = {
            'service': service,
            'usage_type': usage_type,
            'severity': severity,
            'usage_percentage': usage_percentage,
            'current_usage': current_usage,
            'limit': limit,
            'remaining': max(0, limit - current_usage),
            'message': messages.get(severity, f"Alert for {service}"),
            'timestamp': datetime.now().isoformat(),
            'month': datetime.now().strftime('%Y-%m')
        }
        
        # Store alert in database
        self.db_manager.create_free_tier_alert(
            service, usage_type, current_usage, limit
        )
        
        return alert
    
    def get_service_recommendations(self, usage_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate recommendations for optimizing free tier usage.
        
        Args:
            usage_data: Current usage data
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        current_month = datetime.now().strftime('%Y-%m')
        usage_status = self.db_manager.check_free_tier_usage(current_month)
        
        for service_usage in usage_status:
            service = service_usage['service']
            usage_type = service_usage['usage_type']
            usage_percentage = service_usage.get('usage_percentage', 0)
            
            if usage_percentage >= 80:  # High usage services
                if 'Elastic Compute Cloud' in service and 't2.micro' in usage_type:
                    recommendations.append({
                        'service': service,
                        'type': 'optimization',
                        'priority': 'high',
                        'title': 'EC2 t2.micro Usage Optimization',
                        'description': 'Consider stopping instances when not needed to stay within 750 hours/month limit',
                        'action': 'Schedule automatic stop/start or use spot instances'
                    })
                
                elif 'Simple Storage Service' in service:
                    recommendations.append({
                        'service': service,
                        'type': 'optimization',
                        'priority': 'medium',
                        'title': 'S3 Storage Optimization',
                        'description': 'Review stored data and consider lifecycle policies',
                        'action': 'Delete unnecessary files or move to cheaper storage classes'
                    })
                
                elif 'Lambda' in service:
                    recommendations.append({
                        'service': service,
                        'type': 'optimization',
                        'priority': 'medium',
                        'title': 'Lambda Usage Optimization',
                        'description': 'Optimize function memory allocation and execution time',
                        'action': 'Review function performance and reduce memory/duration if possible'
                    })
        
        # Always-on recommendations
        recommendations.extend([
            {
                'service': 'General',
                'type': 'monitoring',
                'priority': 'high',
                'title': 'Set up AWS Budgets',
                'description': 'Create zero-spend budget to get alerts before charges occur',
                'action': 'Go to AWS Budgets console and create a $0.01 budget with email alerts'
            },
            {
                'service': 'General',
                'type': 'security',
                'priority': 'high',
                'title': 'Enable Cost Anomaly Detection',
                'description': 'AWS service to detect unusual spending patterns',
                'action': 'Enable in AWS Cost Management console (free service)'
            }
        ])
        
        return recommendations
    
    def generate_weekly_alert_summary(self) -> Dict[str, Any]:
        """Generate a summary of alerts from the past week."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    alert_level,
                    COUNT(*) as alert_count,
                    GROUP_CONCAT(DISTINCT service) as affected_services
                FROM free_tier_alerts 
                WHERE date >= date('now', '-7 days')
                GROUP BY alert_level
            ''')
            
            alerts_by_level = {row['alert_level']: {
                'count': row['alert_count'],
                'services': row['affected_services'].split(',') if row['affected_services'] else []
            } for row in cursor.fetchall()}
            
            # Get trend information
            cursor = conn.execute('''
                SELECT 
                    date,
                    COUNT(*) as daily_alerts
                FROM free_tier_alerts 
                WHERE date >= date('now', '-7 days')
                GROUP BY date
                ORDER BY date
            ''')
            
            daily_trend = [{'date': row['date'], 'alerts': row['daily_alerts']} 
                          for row in cursor.fetchall()]
        
        return {
            'period': 'Last 7 days',
            'alerts_by_level': alerts_by_level,
            'daily_trend': daily_trend,
            'total_alerts': sum(level['count'] for level in alerts_by_level.values()),
            'generated_at': datetime.now().isoformat()
        }
    
    def check_cost_anomalies(self, cost_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect cost anomalies that might indicate free tier breaches.
        
        Args:
            cost_data: Daily cost data
            
        Returns:
            List of cost anomaly alerts
        """
        anomalies = []
        
        # Simple anomaly detection: any non-zero cost is suspicious for free tier
        for record in cost_data:
            cost = record.get('cost', 0.0)
            if cost > 0.01:  # More than 1 cent
                anomaly = {
                    'type': 'cost_anomaly',
                    'date': record.get('date'),
                    'service': record.get('service'),
                    'usage_type': record.get('usage_type'),
                    'cost': cost,
                    'currency': record.get('currency', 'USD'),
                    'message': f"Unexpected cost of ${cost:.2f} detected for {record.get('service')} - free tier may be exceeded",
                    'severity': 'critical' if cost > 1.0 else 'warning'
                }
                anomalies.append(anomaly)
        
        return anomalies
    
    def predict_free_tier_breach(self, service: str, usage_type: str) -> Optional[Dict[str, Any]]:
        """
        Predict when a service might breach its free tier limit based on current usage trend.
        
        Args:
            service: AWS service name
            usage_type: Usage type
            
        Returns:
            Prediction data or None if insufficient data
        """
        current_month = datetime.now().strftime('%Y-%m')
        current_day = datetime.now().day
        days_in_month = 31  # Conservative estimate
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    SUM(usage_amount) as month_to_date_usage,
                    free_tier_limit,
                    usage_unit
                FROM aws_free_tier_usage 
                WHERE service = ? AND usage_type = ? 
                AND strftime('%Y-%m', date) = ?
                GROUP BY service, usage_type
            ''', (service, usage_type, current_month))
            
            row = cursor.fetchone()
            if not row or not row['free_tier_limit']:
                return None
            
            month_to_date = row['month_to_date_usage']
            limit = row['free_tier_limit']
            unit = row['usage_unit']
            
            # Calculate daily average and project to end of month
            daily_average = month_to_date / current_day
            projected_monthly_usage = daily_average * days_in_month
            
            if projected_monthly_usage > limit:
                days_to_breach = max(1, int((limit - month_to_date) / daily_average))
                breach_date = datetime.now().replace(day=min(days_in_month, current_day + days_to_breach))
                
                return {
                    'service': service,
                    'usage_type': usage_type,
                    'current_usage': month_to_date,
                    'projected_usage': projected_monthly_usage,
                    'limit': limit,
                    'unit': unit,
                    'daily_average': daily_average,
                    'days_to_breach': days_to_breach,
                    'projected_breach_date': breach_date.strftime('%Y-%m-%d'),
                    'confidence': 'medium' if current_day >= 7 else 'low'
                }
        
        return None
