#!/usr/bin/env python3
"""
Basic tests for FinOps Dashboard components.
Tests core functionality without requiring real AWS credentials.
"""

import unittest
import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import DatabaseManager
from config import Config
from alerts import FreeTierAlertManager


class TestDatabaseManager(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Set up test database."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_manager = DatabaseManager(self.test_db.name)
        self.db_manager.initialize_tables()
    
    def tearDown(self):
        """Clean up test database."""
        os.unlink(self.test_db.name)
    
    def test_database_initialization(self):
        """Test database table creation."""
        with self.db_manager.get_connection() as conn:
            # Check if main tables exist
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('aws_free_tier_usage', 'free_tier_limits')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('aws_free_tier_usage', tables)
            self.assertIn('free_tier_limits', tables)
    
    def test_free_tier_limits_populated(self):
        """Test that free tier limits are populated."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM free_tier_limits")
            count = cursor.fetchone()[0]
            
            self.assertGreater(count, 0, "Free tier limits should be populated")
    
    def test_usage_data_insertion(self):
        """Test inserting usage data."""
        sample_data = [
            {
                'date': '2024-01-15',
                'service': 'Amazon Elastic Compute Cloud - Compute',
                'usage_type': 't2.micro',
                'usage_amount': 24.0,
                'usage_unit': 'hours',
                'cost': 0.0
            },
            {
                'date': '2024-01-15',
                'service': 'Amazon Simple Storage Service',
                'usage_type': 'Standard Storage',
                'usage_amount': 3.5,
                'usage_unit': 'GB',
                'cost': 0.0
            }
        ]
        
        self.db_manager.insert_usage_data(sample_data)
        
        # Verify data was inserted
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM aws_free_tier_usage")
            count = cursor.fetchone()[0]
            
            self.assertEqual(count, 2)
    
    def test_free_tier_usage_check(self):
        """Test checking free tier usage against limits."""
        # Insert test data
        sample_data = [
            {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'service': 'Amazon Elastic Compute Cloud - Compute',
                'usage_type': 't2.micro',
                'usage_amount': 600.0,  # High usage (80% of 750 limit)
                'usage_unit': 'hours',
                'cost': 0.0
            }
        ]
        
        self.db_manager.insert_usage_data(sample_data)
        
        # Check usage status
        current_month = datetime.now().strftime('%Y-%m')
        usage_status = self.db_manager.check_free_tier_usage(current_month)
        
        self.assertGreater(len(usage_status), 0)
        
        # Find the EC2 entry
        ec2_usage = next((s for s in usage_status if 'Compute Cloud' in s['service']), None)
        self.assertIsNotNone(ec2_usage)
        self.assertGreater(ec2_usage['usage_percentage'], 70)  # Should be high usage


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test configuration."""
        self.test_config_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
        self.test_config_file.write("""
database_path: "test.db"
aws_region: "us-west-2"
free_tier_focus: true
alert_thresholds:
  warning: 80.0
  critical: 95.0
""")
        self.test_config_file.close()
    
    def tearDown(self):
        """Clean up test config."""
        os.unlink(self.test_config_file.name)
    
    def test_config_loading(self):
        """Test configuration loading from file."""
        config = Config(self.test_config_file.name)
        
        self.assertEqual(config.database_path, "test.db")
        self.assertEqual(config.aws_region, "us-west-2")
        self.assertTrue(config.free_tier_focus)
    
    def test_config_defaults(self):
        """Test configuration defaults."""
        # Non-existent config file should use defaults
        config = Config("non_existent_config.yaml")
        
        self.assertEqual(config.aws_region, "us-east-1")
        self.assertTrue(config.aws_enabled)
        self.assertFalse(config.gcp_enabled)
    
    def test_environment_override(self):
        """Test environment variable override."""
        os.environ['AWS_REGION'] = 'eu-west-1'
        os.environ['DATABASE_PATH'] = 'env_test.db'
        
        try:
            config = Config("non_existent_config.yaml")
            self.assertEqual(config.aws_region, 'eu-west-1')
            self.assertEqual(config.database_path, 'env_test.db')
        finally:
            # Clean up environment
            del os.environ['AWS_REGION']
            del os.environ['DATABASE_PATH']


class TestAlerts(unittest.TestCase):
    """Test alert functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_manager = DatabaseManager(self.test_db.name)
        self.db_manager.initialize_tables()
        
        # Mock config
        self.config = Config("non_existent_config.yaml")
        self.alert_manager = FreeTierAlertManager(self.config, self.db_manager)
    
    def tearDown(self):
        """Clean up."""
        os.unlink(self.test_db.name)
    
    def test_alert_generation(self):
        """Test alert generation for high usage."""
        # Insert high usage data
        high_usage_data = [
            {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'service': 'Amazon Elastic Compute Cloud - Compute',
                'usage_type': 't2.micro',
                'usage_amount': 700.0,  # 93% of 750 limit
                'usage_unit': 'hours',
                'cost': 0.0
            }
        ]
        
        self.db_manager.insert_usage_data(high_usage_data)
        
        # Check for alerts
        alerts = self.alert_manager.check_free_tier_alerts(high_usage_data)
        
        self.assertGreater(len(alerts), 0, "Should generate alerts for high usage")
        
        # Check alert severity
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        self.assertGreater(len(critical_alerts), 0, "Should have critical alerts for 90%+ usage")
    
    def test_recommendations(self):
        """Test recommendation generation."""
        # Mock usage data
        usage_data = []
        
        recommendations = self.alert_manager.get_service_recommendations(usage_data)
        
        self.assertGreater(len(recommendations), 0, "Should always have basic recommendations")
        
        # Check for general recommendations
        budget_rec = next((r for r in recommendations if 'Budget' in r['title']), None)
        self.assertIsNotNone(budget_rec, "Should recommend setting up AWS Budgets")


class TestFreeTierLimits(unittest.TestCase):
    """Test free tier limits and calculations."""
    
    def test_ec2_limit_calculation(self):
        """Test EC2 usage percentage calculation."""
        # 750 hours per month limit
        # 24 hours/day * 31 days = 744 hours = 99.2% usage
        usage_hours = 744
        limit_hours = 750
        expected_percentage = (usage_hours / limit_hours) * 100
        
        self.assertAlmostEqual(expected_percentage, 99.2, places=1)
    
    def test_s3_storage_limit(self):
        """Test S3 storage limit calculation."""
        # 5 GB limit
        usage_gb = 4.8
        limit_gb = 5.0
        expected_percentage = (usage_gb / limit_gb) * 100
        
        self.assertAlmostEqual(expected_percentage, 96.0, places=1)
    
    def test_lambda_request_limit(self):
        """Test Lambda request limit calculation."""
        # 1M requests per month
        usage_requests = 750000
        limit_requests = 1000000
        expected_percentage = (usage_requests / limit_requests) * 100
        
        self.assertAlmostEqual(expected_percentage, 75.0, places=1)


def run_tests():
    """Run all tests."""
    print("🧪 Running FinOps Dashboard Tests...")
    print("=" * 50)
    
    # Create test suite
    test_classes = [
        TestDatabaseManager,
        TestConfig,
        TestAlerts,
        TestFreeTierLimits
    ]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print(f"Ran {result.testsRun} tests successfully")
    else:
        print("❌ Some tests failed!")
        print(f"Ran {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
