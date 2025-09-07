#!/usr/bin/env python3
"""
Quick Start script for FinOps Dashboard.
Sets up the project with sample data for immediate testing.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_banner():
    """Print welcome banner."""
    print("=" * 60)
    print("🚀 FinOps Dashboard Quick Start")
    print("💰 AWS Free Tier Cost Monitoring")
    print("=" * 60)
    print()

def check_requirements():
    """Check if requirements are installed."""
    try:
        import boto3
        import dash
        import plotly
        import yaml
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Installing requirements...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          check=True, capture_output=True)
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements")
            return False

def setup_environment():
    """Set up environment file."""
    env_template = ".env.template"
    env_file = ".env"
    
    if not os.path.exists(env_file):
        if os.path.exists(env_template):
            shutil.copy(env_template, env_file)
            print(f"✅ Created {env_file} from template")
            print(f"📝 Please edit {env_file} with your AWS credentials")
        else:
            print(f"⚠️  {env_template} not found, creating basic .env file")
            with open(env_file, 'w') as f:
                f.write("""# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Database
DATABASE_PATH=data/finops_dashboard.db

# Dashboard
DASHBOARD_HOST=localhost
DASHBOARD_PORT=8050

# Alerts
MAX_MONTHLY_COST=1.00
WARNING_THRESHOLD=75.0
CRITICAL_THRESHOLD=90.0
""")
            print(f"✅ Created basic {env_file}")
    else:
        print(f"✅ {env_file} already exists")

def check_aws_credentials():
    """Check AWS credentials."""
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        
        try:
            session = boto3.Session()
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            print(f"✅ AWS credentials configured for account: {identity.get('Account', 'Unknown')}")
            return True
        except NoCredentialsError:
            print("⚠️  AWS credentials not configured")
            print("📝 Configure using: aws configure")
            print("📝 Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
            return False
        except ClientError as e:
            print(f"⚠️  AWS credential error: {e}")
            return False
            
    except ImportError:
        print("⚠️  boto3 not installed")
        return False

def create_directories():
    """Create necessary directories."""
    directories = ['data', 'logs', 'exports']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def initialize_database():
    """Initialize the database."""
    try:
        sys.path.insert(0, 'src')
        from database import DatabaseManager
        
        db_manager = DatabaseManager()
        db_manager.initialize_tables()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def generate_sample_data():
    """Generate sample data for testing."""
    choice = input("\n📊 Generate sample data for testing? (y/N): ").strip().lower()
    
    if choice in ['y', 'yes']:
        try:
            sys.path.insert(0, 'scripts')
            from generate_sample_data import populate_sample_data
            
            print("Generating 30 days of sample data...")
            populate_sample_data(days=30)
            print("✅ Sample data generated successfully")
            return True
        except Exception as e:
            print(f"❌ Sample data generation failed: {e}")
            return False
    else:
        print("⏭️  Skipping sample data generation")
        return True

def run_tests():
    """Run basic tests."""
    choice = input("\n🧪 Run basic tests? (y/N): ").strip().lower()
    
    if choice in ['y', 'yes']:
        try:
            sys.path.insert(0, 'tests')
            from test_basic import run_tests
            
            success = run_tests()
            if success:
                print("✅ All tests passed!")
            else:
                print("⚠️  Some tests failed, but you can still continue")
            return True
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return False
    else:
        print("⏭️  Skipping tests")
        return True

def start_dashboard():
    """Ask if user wants to start the dashboard."""
    choice = input("\n🌐 Start the dashboard now? (y/N): ").strip().lower()
    
    if choice in ['y', 'yes']:
        try:
            print("\n🚀 Starting dashboard...")
            print("📱 Dashboard will be available at: http://localhost:8050")
            print("⌨️  Press Ctrl+C to stop the dashboard")
            print()
            
            # Change to src directory and run dashboard
            os.chdir('src')
            subprocess.run([sys.executable, "dashboard.py"])
            
        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped by user")
        except Exception as e:
            print(f"❌ Failed to start dashboard: {e}")
    else:
        print("📝 To start the dashboard later, run:")
        print("   cd src && python dashboard.py")

def print_next_steps():
    """Print next steps."""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete! Next Steps:")
    print("=" * 60)
    print()
    print("1. 🔧 Configure AWS credentials:")
    print("   aws configure")
    print()
    print("2. 📊 Collect real usage data:")
    print("   cd src && python main.py --days 7")
    print()
    print("3. 🌐 Start the dashboard:")
    print("   cd src && python dashboard.py")
    print("   Then visit: http://localhost:8050")
    print()
    print("4. ⏰ Set up automation (optional):")
    print("   Add to crontab: 0 */6 * * * cd /path/to/project/src && python main.py --days 1")
    print()
    print("📚 Documentation: README.md")
    print("🆘 Issues: Check troubleshooting section in README.md")
    print()
    print("💡 Remember: This tool helps you stay within AWS Free Tier limits!")
    print("=" * 60)

def main():
    """Main setup process."""
    print_banner()
    
    # Check current directory
    if not os.path.exists("requirements.txt"):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Step-by-step setup
    steps = [
        ("Checking requirements", check_requirements),
        ("Setting up environment", setup_environment),
        ("Checking AWS credentials", check_aws_credentials),
        ("Creating directories", create_directories),
        ("Initializing database", initialize_database),
        ("Generating sample data", generate_sample_data),
        ("Running tests", run_tests),
    ]
    
    for step_name, step_func in steps:
        print(f"\n🔄 {step_name}...")
        try:
            if not step_func():
                print(f"⚠️  {step_name} completed with warnings")
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
            if input("Continue anyway? (y/N): ").strip().lower() not in ['y', 'yes']:
                print("Setup aborted")
                sys.exit(1)
    
    # Optional dashboard start
    start_dashboard()
    
    # Print final instructions
    print_next_steps()

if __name__ == "__main__":
    main()
