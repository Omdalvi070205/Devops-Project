"""
Free Tier Dashboard using Dash (alternative to Grafana)
Simple web dashboard for AWS free tier usage monitoring.
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Any
import logging

from database import DatabaseManager
from config import Config


class FreeTierDashboard:
    """Free tier usage dashboard using Dash."""
    
    def __init__(self, config: Config):
        """Initialize dashboard."""
        self.config = config
        self.db_manager = DatabaseManager(config.database_path)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Dash app
        self.app = dash.Dash(__name__, external_stylesheets=[
            'https://codepen.io/chriddyp/pen/bWLwgP.css'
        ])
        self.app.title = config.get('dashboard.title', 'AWS Free Tier Monitor')
        
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Setup dashboard layout."""
        self.app.layout = html.Div([
            html.H1("AWS Free Tier Usage Monitor", 
                   style={'textAlign': 'center', 'color': '#2c3e50'}),
            
            html.Div([
                html.H3("📊 Current Month Overview"),
                dcc.Graph(id='usage-overview-chart'),
                html.Hr(),
                
                html.H3("⚠️ Active Alerts"),
                html.Div(id='alerts-section'),
                html.Hr(),
                
                html.H3("📈 Cost Trend (Last 30 Days)"),
                dcc.Graph(id='cost-trend-chart'),
                html.Hr(),
                
                html.H3("🔧 Service Recommendations"),
                html.Div(id='recommendations-section'),
                html.Hr(),
                
                html.H3("📋 Detailed Usage Table"),
                html.Div(id='usage-table')
            ], style={'margin': '20px'}),
            
            # Auto-refresh component
            dcc.Interval(
                id='interval-component',
                interval=5*60*1000,  # Update every 5 minutes
                n_intervals=0
            ),
            
            # Footer
            html.Div([
                html.Hr(),
                html.P([
                    "💡 ",
                    html.Strong("Free Tier Dashboard"),
                    " - Last updated: ",
                    html.Span(id='last-updated')
                ], style={'textAlign': 'center', 'color': '#7f8c8d'})
            ])
        ])
    
    def setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        @self.app.callback(
            [Output('usage-overview-chart', 'figure'),
             Output('alerts-section', 'children'),
             Output('cost-trend-chart', 'figure'),
             Output('recommendations-section', 'children'),
             Output('usage-table', 'children'),
             Output('last-updated', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            """Update all dashboard components."""
            
            # Get current usage data
            current_month = datetime.now().strftime('%Y-%m')
            usage_status = self.db_manager.check_free_tier_usage(current_month)
            
            # 1. Usage Overview Chart
            overview_fig = self.create_usage_overview_chart(usage_status)
            
            # 2. Alerts Section
            alerts_section = self.create_alerts_section(usage_status)
            
            # 3. Cost Trend Chart
            cost_trend_fig = self.create_cost_trend_chart()
            
            # 4. Recommendations
            recommendations = self.create_recommendations_section(usage_status)
            
            # 5. Usage Table
            usage_table = self.create_usage_table(usage_status)
            
            # 6. Last updated time
            last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return (overview_fig, alerts_section, cost_trend_fig, 
                   recommendations, usage_table, last_updated)
    
    def create_usage_overview_chart(self, usage_status: List[Dict]) -> go.Figure:
        """Create usage overview donut chart."""
        if not usage_status:
            return go.Figure().add_annotation(text="No data available", 
                                            xref="paper", yref="paper",
                                            x=0.5, y=0.5, showarrow=False)
        
        # Categorize services by usage level
        categories = {'Safe (0-50%)': 0, 'Moderate (50-75%)': 0, 
                     'Warning (75-90%)': 0, 'Critical (90%+)': 0}
        
        for service in usage_status:
            usage_pct = service.get('usage_percentage', 0)
            if usage_pct >= 90:
                categories['Critical (90%+)'] += 1
            elif usage_pct >= 75:
                categories['Warning (75-90%)'] += 1
            elif usage_pct >= 50:
                categories['Moderate (50-75%)'] += 1
            else:
                categories['Safe (0-50%)'] += 1
        
        colors = ['#27ae60', '#f39c12', '#e67e22', '#e74c3c']
        
        fig = go.Figure(data=[go.Pie(
            labels=list(categories.keys()),
            values=list(categories.values()),
            hole=0.4,
            marker_colors=colors
        )])
        
        fig.update_layout(
            title="Services by Usage Level",
            font={'size': 12}
        )
        
        return fig
    
    def create_alerts_section(self, usage_status: List[Dict]) -> html.Div:
        """Create alerts section."""
        alerts = []
        
        for service in usage_status:
            usage_pct = service.get('usage_percentage', 0)
            if usage_pct >= 75:  # Warning or critical
                alert_color = '#e74c3c' if usage_pct >= 90 else '#e67e22'
                icon = '🚨' if usage_pct >= 90 else '⚠️'
                
                alerts.append(html.Div([
                    html.Span(icon, style={'marginRight': '10px'}),
                    html.Strong(f"{service['service']}: "),
                    f"{usage_pct:.1f}% of free tier used",
                    html.Br(),
                    html.Small(f"({service['total_usage']:.1f} / {service['free_tier_limit']:.1f} {service['usage_unit']})")
                ], style={
                    'padding': '10px',
                    'margin': '5px 0',
                    'backgroundColor': '#fff5f5',
                    'border': f'1px solid {alert_color}',
                    'borderRadius': '5px'
                }))
        
        if not alerts:
            return html.Div([
                html.Span("✅", style={'marginRight': '10px'}),
                "All services are within safe usage limits!"
            ], style={
                'padding': '10px',
                'backgroundColor': '#f0fff4',
                'border': '1px solid #27ae60',
                'borderRadius': '5px',
                'color': '#27ae60'
            })
        
        return html.Div(alerts)
    
    def create_cost_trend_chart(self) -> go.Figure:
        """Create cost trend chart."""
        cost_data = self.db_manager.get_cost_trend(30)
        
        if not cost_data:
            return go.Figure().add_annotation(text="No cost data available", 
                                            xref="paper", yref="paper",
                                            x=0.5, y=0.5, showarrow=False)
        
        df = pd.DataFrame(cost_data)
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        
        # Daily cost line
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['daily_cost'],
            mode='lines+markers',
            name='Daily Cost',
            line={'color': '#3498db', 'width': 2}
        ))
        
        # Add threshold line at $1/month (approximately $0.033/day)
        daily_threshold = 1.0 / 30
        fig.add_hline(y=daily_threshold, line_dash="dash", 
                     line_color="red", 
                     annotation_text=f"${daily_threshold:.3f}/day threshold")
        
        fig.update_layout(
            title="Daily Cost Trend",
            xaxis_title="Date",
            yaxis_title="Cost (USD)",
            hovermode='x unified'
        )
        
        return fig
    
    def create_recommendations_section(self, usage_status: List[Dict]) -> html.Div:
        """Create recommendations section."""
        recommendations = []
        
        for service in usage_status:
            usage_pct = service.get('usage_percentage', 0)
            service_name = service['service']
            
            if usage_pct >= 80:
                if 'Compute Cloud' in service_name:
                    recommendations.append({
                        'icon': '🖥️',
                        'title': 'EC2 Optimization',
                        'desc': 'Stop instances when not needed to stay within 750 hours/month',
                        'priority': 'High'
                    })
                elif 'Storage Service' in service_name:
                    recommendations.append({
                        'icon': '💾',
                        'title': 'S3 Storage Review',
                        'desc': 'Consider lifecycle policies or delete unused files',
                        'priority': 'Medium'
                    })
                elif 'Lambda' in service_name:
                    recommendations.append({
                        'icon': '⚡',
                        'title': 'Lambda Optimization',
                        'desc': 'Optimize memory allocation and execution time',
                        'priority': 'Medium'
                    })
        
        # Add general recommendations
        if not recommendations:
            recommendations = [
                {
                    'icon': '💰',
                    'title': 'Set up AWS Budgets',
                    'desc': 'Create a $0.01 budget with email alerts',
                    'priority': 'High'
                },
                {
                    'icon': '📊',
                    'title': 'Enable Cost Anomaly Detection',
                    'desc': 'Free AWS service to detect unusual spending',
                    'priority': 'Medium'
                }
            ]
        
        rec_elements = []
        for rec in recommendations:
            color = '#e74c3c' if rec['priority'] == 'High' else '#f39c12'
            rec_elements.append(html.Div([
                html.Span(rec['icon'], style={'marginRight': '10px'}),
                html.Strong(rec['title']),
                html.Br(),
                rec['desc'],
                html.Span(f" [{rec['priority']} Priority]", 
                         style={'color': color, 'fontWeight': 'bold'})
            ], style={
                'padding': '10px',
                'margin': '5px 0',
                'backgroundColor': '#f8f9fa',
                'border': '1px solid #dee2e6',
                'borderRadius': '5px'
            }))
        
        return html.Div(rec_elements)
    
    def create_usage_table(self, usage_status: List[Dict]) -> dash_table.DataTable:
        """Create detailed usage table."""
        if not usage_status:
            return html.Div("No usage data available")
        
        # Prepare table data
        table_data = []
        for service in usage_status:
            table_data.append({
                'Service': service['service'],
                'Usage Type': service['usage_type'],
                'Current Usage': f"{service['total_usage']:.2f} {service['usage_unit']}",
                'Free Tier Limit': f"{service['free_tier_limit']:.2f} {service['limit_unit']}",
                'Usage %': f"{service['usage_percentage']:.1f}%",
                'Remaining': f"{service['remaining']:.2f} {service['usage_unit']}",
                'Status': service['alert_level'].title()
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": i, "id": i} for i in table_data[0].keys() if table_data],
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Status} = Critical'},
                    'backgroundColor': '#fee',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{Status} = Warning'},
                    'backgroundColor': '#fff3cd',
                    'color': 'black',
                }
            ],
            style_header={
                'backgroundColor': '#3498db',
                'color': 'white',
                'fontWeight': 'bold'
            },
            sort_action="native"
        )
    
    def run(self, debug=False):
        """Run the dashboard server."""
        host = self.config.get('dashboard.host', 'localhost')
        port = self.config.get('dashboard.port', 8050)
        
        self.logger.info(f"Starting dashboard server at http://{host}:{port}")
        self.app.run_server(debug=debug, host=host, port=port)


if __name__ == "__main__":
    # Run dashboard standalone
    config = Config()
    dashboard = FreeTierDashboard(config)
    dashboard.run(debug=True)
