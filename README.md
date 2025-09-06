# 💰 AWS Free Tier FinOps Dashboard

A **completely free** cloud cost monitoring dashboard specifically designed for AWS Free Tier users. Monitor your usage, get alerts before incurring charges, and maintain visibility over your cloud resources without spending a dime!

## 🎯 Features

- **100% Free Tier Focus**: Tracks all AWS 12-month free tier services
- **Real-time Alerts**: Get warnings before hitting free tier limits
- **Cost Monitoring**: Track any unexpected charges with $0.01+ alerts  
- **Interactive Dashboard**: Beautiful web interface using Dash (free alternative to Grafana)
- **Zero Infrastructure Costs**: Uses only SQLite database and local hosting
- **Smart Recommendations**: Get actionable advice to optimize your usage
- **Weekly Reports**: Automated usage summaries

## 📋 Supported AWS Services

### 12-Month Free Tier Services Monitored:
- **EC2**: 750 hours of t2.micro instances
- **S3**: 5 GB storage + 20K GET + 2K PUT requests  
- **Lambda**: 1M requests + 400K GB-seconds compute time
- **RDS**: 750 hours of db.t2.micro + 20 GB storage
- **DynamoDB**: 25 GB storage + 25 RCU + 25 WCU
- **CloudWatch**: 10 custom metrics + 10 alarms
- **SNS**: 1M published notifications
- **SQS**: 1M requests

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- AWS Account with configured credentials
- AWS CLI installed (optional but recommended)

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd finops-cloud-cost-dashboard

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure AWS Credentials
```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### 3. Configuration
```bash
# Copy environment template
cp .env.template .env

# Edit .env file with your settings
nano .env  # or use your favorite editor
```

### 4. Initialize Database
```bash
cd src
python database.py  # This will create the SQLite database and tables
```

### 5. First Run
```bash
# Collect initial data
python main.py --days 7

# Start the dashboard
python dashboard.py
```

Visit `http://localhost:8050` to see your dashboard!

## 📊 Dashboard Overview

### Main Sections:
1. **Usage Overview**: Pie chart showing services by risk level
2. **Active Alerts**: Real-time warnings for high usage
3. **Cost Trend**: Daily cost tracking with threshold alerts
4. **Recommendations**: Smart suggestions to optimize usage
5. **Detailed Table**: Complete breakdown of all services

### Alert Levels:
- 🟢 **Safe (0-50%)**: Normal usage, no concerns
- 🟡 **Moderate (50-75%)**: Monitor closely
- 🟠 **Warning (75-90%)**: Approaching limit, take action
- 🔴 **Critical (90%+)**: Immediate action required!

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# AWS Configuration  
AWS_REGION=us-east-1
AWS_PROFILE=default

# Monitoring
REPORT_EMAIL=your-email@example.com
MAX_MONTHLY_COST=1.00

# Dashboard
DASHBOARD_HOST=localhost
DASHBOARD_PORT=8050

# Alert Thresholds
WARNING_THRESHOLD=75.0
CRITICAL_THRESHOLD=90.0
```

### Main Configuration (config/config.yaml)
```yaml
# Free Tier Focus
free_tier_focus: true
max_monthly_cost_alert: 1.0

# Alert Thresholds
alert_thresholds:
  warning: 75.0
  critical: 90.0

# Monitoring
monitoring:
  check_interval_hours: 6
  report_email: null
  enable_cost_alerts: true
```

## 🔄 Automation

### Scheduled Monitoring
```bash
# Add to crontab for automatic monitoring
0 */6 * * * cd /path/to/project/src && python main.py --days 1

# Weekly report
0 9 * * 1 cd /path/to/project/src && python -c "
from database import DatabaseManager
from datetime import datetime
db = DatabaseManager()
report = db.export_free_tier_report()
print('Weekly Report Generated:', datetime.now())
"
```

### Windows Task Scheduler
Create a batch file for Windows automation:
```batch
@echo off
cd /d "C:\path\to\finops-cloud-cost-dashboard\src"
python main.py --days 1
```

## 📈 Usage Examples

### Command Line Usage
```bash
# Check last 30 days
python main.py --days 30

# AWS only
python main.py --provider aws --days 7

# Custom config
python main.py --config ../config/production.yaml

# Debug mode
python main.py --log-level DEBUG
```

### Programmatic Usage
```python
from src.database import DatabaseManager
from src.config import Config
from src.aws_client import AWSCostClient

# Get current usage
config = Config()
db = DatabaseManager(config.database_path)
usage_status = db.check_free_tier_usage()

# Check for alerts
for service in usage_status:
    if service['usage_percentage'] > 75:
        print(f"Alert: {service['service']} at {service['usage_percentage']:.1f}%")
```

## 🏗️ Architecture

```
finops-cloud-cost-dashboard/
├── src/
│   ├── main.py              # Main application entry point
│   ├── aws_client.py        # AWS Cost Explorer API client
│   ├── database.py          # SQLite database manager
│   ├── alerts.py            # Alert and notification system
│   ├── config.py            # Configuration management
│   └── dashboard.py         # Web dashboard (Dash)
├── config/
│   └── config.yaml          # Main configuration file
├── data/
│   └── finops_dashboard.db  # SQLite database (auto-created)
├── docs/
│   └── *.md                 # Additional documentation
└── scripts/
    └── *.py                 # Utility scripts
```

## 💡 Cost Optimization Tips

### EC2 (750 hours/month limit)
- **Stop instances when not in use**: 24/7 = 720 hours (safe)
- **Use scheduling**: Stop at night, weekends
- **Monitor closely**: 750 hours = ~25 hours/day max

### S3 (5 GB storage limit)
- **Lifecycle policies**: Auto-delete old files
- **Compress data**: Reduce storage usage
- **Monitor requests**: 20K GET, 2K PUT monthly limits

### Lambda (1M requests, 400K GB-seconds)
- **Optimize memory**: Lower memory = lower GB-seconds
- **Efficient code**: Reduce execution time
- **Cold starts**: Consider provisioned concurrency for high-traffic

### General Tips
1. **Set up AWS Budgets** (free service) with $0.01 alert
2. **Enable AWS Cost Anomaly Detection** (free)  
3. **Review monthly**: Check usage patterns
4. **Use CloudWatch Alarms**: Free monitoring
5. **Consider AWS Free Tier Expiration** (12 months)

## 🆘 Troubleshooting

### Common Issues

**1. "AWS credentials not found"**
```bash
# Check credentials
aws sts get-caller-identity

# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**2. "No data in dashboard"**
```bash
# Run data collection first
python main.py --days 7

# Check database
python -c "from database import DatabaseManager; db=DatabaseManager(); print(len(db.check_free_tier_usage()))"
```

**3. "Dashboard won't start"**
```bash
# Check if port is in use
netstat -an | grep 8050

# Use different port
python dashboard.py  # Edit config.yaml to change port
```

**4. "Permission denied" errors**
```bash
# Check IAM permissions - need ces:GetCostAndUsage
# Attach AWS Cost Explorer read permissions to your user
```

### Required AWS Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetUsageReport",
                "ce:GetReservationCoverage",
                "ce:ListCostCategoryDefinitions",
                "ce:GetRightsizingRecommendation"
            ],
            "Resource": "*"
        }
    ]
}
```

## 📚 Additional Documentation

- [API Documentation](docs/api.md)
- [Alert Logic Details](docs/alerts.md)
- [Database Schema](docs/database.md)
- [Contributing Guide](docs/contributing.md)

## 🔒 Security Notes

- **Never commit credentials**: Use `.env` files (gitignored)
- **Least privilege**: Use minimal IAM permissions
- **Local only**: Database contains usage data, keep it secure
- **HTTPS**: Consider reverse proxy for production dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **AWS Free Tier** for providing free cloud resources
- **Dash/Plotly** for the free dashboard framework
- **SQLite** for the lightweight, free database
- **Python ecosystem** for excellent free libraries

## 📞 Support

- Create an [Issue](issues) for bugs or feature requests
- Check [Discussions](discussions) for questions
- Email: [your-email] for security concerns

---

**🎉 Happy Free Tier Monitoring! Keep those cloud costs at $0.00!** 🎉
