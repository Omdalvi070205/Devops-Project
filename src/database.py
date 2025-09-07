"""
Database manager for SQLite operations focused on free tier usage tracking.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional


class DatabaseManager:
    """Manages SQLite database operations for free tier cost tracking."""
    
    def __init__(self, db_path: str = "data/finops_dashboard.db"):
        """Initialize database manager."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize_tables(self):
        """Initialize database tables for free tier tracking."""
        with self.get_connection() as conn:
            # AWS Free Tier usage tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS aws_free_tier_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    service TEXT NOT NULL,
                    usage_type TEXT NOT NULL,
                    usage_amount REAL NOT NULL,
                    usage_unit TEXT NOT NULL,
                    free_tier_limit REAL,
                    limit_unit TEXT,
                    cost REAL DEFAULT 0.0,
                    is_free_tier BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, service, usage_type)
                )
            ''')
            
            # Free tier limits reference table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS free_tier_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    usage_type TEXT NOT NULL,
                    monthly_limit REAL NOT NULL,
                    unit TEXT NOT NULL,
                    description TEXT,
                    reset_day INTEGER DEFAULT 1,
                    UNIQUE(service, usage_type)
                )
            ''')
            
            # Alerts for free tier breaches
            conn.execute('''
                CREATE TABLE IF NOT EXISTS free_tier_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    usage_type TEXT NOT NULL,
                    current_usage REAL NOT NULL,
                    limit_value REAL NOT NULL,
                    usage_percentage REAL NOT NULL,
                    alert_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    date TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Daily cost summary for tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_cost_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_cost REAL NOT NULL,
                    free_tier_cost REAL DEFAULT 0.0,
                    paid_cost REAL DEFAULT 0.0,
                    service_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            
            # Initialize AWS Free Tier limits
            self._populate_free_tier_limits(conn)
            conn.commit()
            self.logger.info("Database tables initialized for free tier tracking")
    
    def _populate_free_tier_limits(self, conn):
        """Populate AWS Free Tier limits (12 months free)."""
        free_tier_limits = [
            # EC2
            ('Amazon Elastic Compute Cloud - Compute', 't2.micro', 750, 'hours', 't2.micro instance hours per month'),
            
            # S3
            ('Amazon Simple Storage Service', 'Standard Storage', 5, 'GB', '5 GB of Standard Storage'),
            ('Amazon Simple Storage Service', 'Requests', 20000, 'requests', 'GET Requests'),
            ('Amazon Simple Storage Service', 'Requests', 2000, 'requests', 'PUT, COPY, POST, LIST requests'),
            
            # Lambda
            ('AWS Lambda', 'Requests', 1000000, 'requests', 'Free requests per month'),
            ('AWS Lambda', 'Duration', 400000, 'GB-seconds', 'Compute time per month'),
            
            # RDS
            ('Amazon Relational Database Service', 'db.t2.micro', 750, 'hours', 'db.t2.micro database hours'),
            ('Amazon Relational Database Service', 'Storage', 20, 'GB', 'General Purpose SSD storage'),
            
            # CloudWatch
            ('Amazon CloudWatch', 'Metrics', 10, 'metrics', 'Custom metrics'),
            ('Amazon CloudWatch', 'Alarms', 10, 'alarms', 'Alarms'),
            ('Amazon CloudWatch', 'API Requests', 1000000, 'requests', 'API requests'),
            
            # DynamoDB
            ('Amazon DynamoDB', 'Storage', 25, 'GB', 'Storage'),
            ('Amazon DynamoDB', 'Read Capacity', 25, 'RCU', 'Read Capacity Units'),
            ('Amazon DynamoDB', 'Write Capacity', 25, 'WCU', 'Write Capacity Units'),
            
            # SNS
            ('Amazon Simple Notification Service', 'Notifications', 1000000, 'notifications', 'Published notifications'),
            
            # SQS
            ('Amazon Simple Queue Service', 'Requests', 1000000, 'requests', 'Requests per month')
        ]
        
        for service, usage_type, limit, unit, description in free_tier_limits:
            conn.execute('''
                INSERT OR IGNORE INTO free_tier_limits 
                (service, usage_type, monthly_limit, unit, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (service, usage_type, limit, unit, description))
    
    def insert_usage_data(self, usage_records: List[Dict[str, Any]]):
        """Insert usage data and check against free tier limits."""
        with self.get_connection() as conn:
            for record in usage_records:
                # Get free tier limit for this service/usage type
                limit_cursor = conn.execute('''
                    SELECT monthly_limit, unit FROM free_tier_limits 
                    WHERE service = ? AND usage_type = ?
                ''', (record.get('service'), record.get('usage_type')))
                
                limit_row = limit_cursor.fetchone()
                free_tier_limit = limit_row['monthly_limit'] if limit_row else None
                limit_unit = limit_row['unit'] if limit_row else record.get('usage_unit', '')
                
                # Insert usage record
                conn.execute('''
                    INSERT OR REPLACE INTO aws_free_tier_usage
                    (date, service, usage_type, usage_amount, usage_unit, 
                     free_tier_limit, limit_unit, cost, is_free_tier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.get('date'),
                    record.get('service'),
                    record.get('usage_type'),
                    record.get('usage_amount', 0.0),
                    record.get('usage_unit', ''),
                    free_tier_limit,
                    limit_unit,
                    record.get('cost', 0.0),
                    record.get('cost', 0.0) == 0.0  # Assume free if cost is 0
                ))
            
            conn.commit()
            self.logger.info(f"Inserted {len(usage_records)} usage records")
    
    def check_free_tier_usage(self, month: str = None) -> List[Dict[str, Any]]:
        """
        Check current month's usage against free tier limits.
        
        Args:
            month: Month to check (YYYY-MM format), defaults to current month
            
        Returns:
            List of services with their usage status
        """
        if not month:
            month = datetime.now().strftime('%Y-%m')
        
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    u.service,
                    u.usage_type,
                    SUM(u.usage_amount) as total_usage,
                    u.usage_unit,
                    u.free_tier_limit,
                    u.limit_unit,
                    AVG(u.cost) as avg_cost,
                    COUNT(*) as days_tracked
                FROM aws_free_tier_usage u
                WHERE strftime('%Y-%m', u.date) = ?
                GROUP BY u.service, u.usage_type
                ORDER BY u.service, u.usage_type
            ''', (month,))
            
            usage_status = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                if row_dict['free_tier_limit']:
                    usage_percentage = (row_dict['total_usage'] / row_dict['free_tier_limit']) * 100
                    row_dict['usage_percentage'] = round(usage_percentage, 2)
                    row_dict['remaining'] = max(0, row_dict['free_tier_limit'] - row_dict['total_usage'])
                    
                    # Determine alert level
                    if usage_percentage >= 90:
                        row_dict['alert_level'] = 'critical'
                    elif usage_percentage >= 75:
                        row_dict['alert_level'] = 'warning'
                    elif usage_percentage >= 50:
                        row_dict['alert_level'] = 'info'
                    else:
                        row_dict['alert_level'] = 'ok'
                else:
                    row_dict['usage_percentage'] = 0
                    row_dict['remaining'] = 'unlimited'
                    row_dict['alert_level'] = 'unknown'
                
                usage_status.append(row_dict)
            
            return usage_status
    
    def create_free_tier_alert(self, service: str, usage_type: str, 
                              current_usage: float, limit_value: float):
        """Create an alert for free tier usage."""
        usage_percentage = (current_usage / limit_value) * 100
        
        if usage_percentage >= 90:
            alert_level = 'critical'
            message = f"CRITICAL: {service} {usage_type} usage at {usage_percentage:.1f}% of free tier limit"
        elif usage_percentage >= 75:
            alert_level = 'warning'
            message = f"WARNING: {service} {usage_type} usage at {usage_percentage:.1f}% of free tier limit"
        else:
            return  # Don't create alert for lower usage
        
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO free_tier_alerts
                (service, usage_type, current_usage, limit_value, usage_percentage, 
                 alert_level, message, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                service, usage_type, current_usage, limit_value,
                usage_percentage, alert_level, message,
                datetime.now().strftime('%Y-%m-%d')
            ))
            conn.commit()
    
    def get_cost_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily cost trend for visualization."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    date,
                    SUM(cost) as daily_cost,
                    COUNT(DISTINCT service) as active_services,
                    SUM(CASE WHEN cost > 0 THEN cost ELSE 0 END) as paid_cost
                FROM aws_free_tier_usage
                WHERE date >= date('now', '-{} days')
                GROUP BY date
                ORDER BY date
            '''.format(days))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def export_free_tier_report(self) -> Dict[str, Any]:
        """Export comprehensive free tier usage report."""
        current_month = datetime.now().strftime('%Y-%m')
        
        usage_status = self.check_free_tier_usage(current_month)
        
        # Calculate summary statistics
        total_services = len(usage_status)
        at_risk_services = len([s for s in usage_status if s['usage_percentage'] >= 75])
        critical_services = len([s for s in usage_status if s['usage_percentage'] >= 90])
        
        with self.get_connection() as conn:
            # Get recent alerts
            cursor = conn.execute('''
                SELECT * FROM free_tier_alerts 
                WHERE date >= date('now', '-7 days')
                ORDER BY created_at DESC
                LIMIT 10
            ''')
            recent_alerts = [dict(row) for row in cursor.fetchall()]
            
            # Get cost trend
            cursor = conn.execute('''
                SELECT 
                    date,
                    SUM(cost) as daily_cost
                FROM aws_free_tier_usage
                WHERE date >= date('now', '-30 days')
                GROUP BY date
                ORDER BY date
            ''')
            cost_trend = [dict(row) for row in cursor.fetchall()]
        
        return {
            'report_month': current_month,
            'summary': {
                'total_services_tracked': total_services,
                'at_risk_services': at_risk_services,
                'critical_services': critical_services,
                'total_monthly_cost': sum(s.get('avg_cost', 0) * 30 for s in usage_status)
            },
            'usage_status': usage_status,
            'recent_alerts': recent_alerts,
            'cost_trend': cost_trend,
            'generated_at': datetime.now().isoformat()
        }
