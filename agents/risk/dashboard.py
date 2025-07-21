"""
Risk Dashboard and Alert System

This module implements a comprehensive risk dashboard and alert system
for monitoring and visualizing risk metrics in real-time.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict, deque

from .models import RiskLevel, RiskPrediction
from .calculator import RiskCalculationResult, RealTimeRiskCalculator
from .portfolio import PortfolioManager, PortfolioMetrics, InsurancePolicy
from .metrics import RiskMetrics, PerformanceAnalyzer, MetricResult

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    RISK_THRESHOLD = "risk_threshold"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONCENTRATION_RISK = "concentration_risk"
    CORRELATION_SPIKE = "correlation_spike"
    VOLATILITY_SPIKE = "volatility_spike"
    SYSTEM_ERROR = "system_error"
    MODEL_DRIFT = "model_drift"
    DATA_QUALITY = "data_quality"


@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    threshold_value: Optional[float]
    current_value: Optional[float]
    policy_ids: List[str]
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    created_by: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    widget_id: str
    widget_type: str
    title: str
    description: str
    config: Dict[str, Any]
    position: Tuple[int, int]
    size: Tuple[int, int]
    refresh_interval: int  # seconds
    last_updated: datetime
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardSnapshot:
    """Dashboard snapshot data"""
    snapshot_id: str
    timestamp: datetime
    portfolio_summary: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    alerts: List[Alert]
    active_policies: int
    total_coverage: float
    total_premium: float
    overall_risk_score: float


class RiskDashboard:
    """Risk dashboard for monitoring and visualization"""
    
    def __init__(self, 
                 portfolio_manager: PortfolioManager,
                 risk_calculator: RealTimeRiskCalculator,
                 risk_metrics: RiskMetrics,
                 performance_analyzer: PerformanceAnalyzer):
        self.portfolio_manager = portfolio_manager
        self.risk_calculator = risk_calculator
        self.risk_metrics = risk_metrics
        self.performance_analyzer = performance_analyzer
        
        self.widgets: Dict[str, DashboardWidget] = {}
        self.snapshots: deque = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.update_interval = 30  # seconds
        self.is_running = False
        self.last_update = datetime.now()
        
        # Initialize default widgets
        asyncio.create_task(self._initialize_default_widgets())
    
    async def _initialize_default_widgets(self):
        """Initialize default dashboard widgets"""
        default_widgets = [
            {
                'widget_id': 'portfolio_summary',
                'widget_type': 'summary_card',
                'title': 'Portfolio Summary',
                'description': 'Overview of portfolio metrics',
                'config': {'metrics': ['total_coverage', 'total_premium', 'active_policies']},
                'position': (0, 0),
                'size': (4, 2),
                'refresh_interval': 30
            },
            {
                'widget_id': 'risk_score_gauge',
                'widget_type': 'gauge',
                'title': 'Overall Risk Score',
                'description': 'Current portfolio risk level',
                'config': {'min': 0, 'max': 1, 'thresholds': [0.3, 0.6, 0.8]},
                'position': (4, 0),
                'size': (2, 2),
                'refresh_interval': 15
            },
            {
                'widget_id': 'asset_allocation',
                'widget_type': 'pie_chart',
                'title': 'Asset Allocation',
                'description': 'Portfolio allocation by asset class',
                'config': {'show_percentages': True},
                'position': (6, 0),
                'size': (3, 3),
                'refresh_interval': 60
            },
            {
                'widget_id': 'risk_metrics_table',
                'widget_type': 'table',
                'title': 'Key Risk Metrics',
                'description': 'Important risk indicators',
                'config': {'columns': ['metric', 'value', 'trend', 'threshold']},
                'position': (0, 2),
                'size': (6, 3),
                'refresh_interval': 30
            },
            {
                'widget_id': 'performance_chart',
                'widget_type': 'line_chart',
                'title': 'Performance Trend',
                'description': 'Portfolio performance over time',
                'config': {'timeframe': '30d', 'metrics': ['total_return', 'sharpe_ratio']},
                'position': (0, 5),
                'size': (9, 3),
                'refresh_interval': 60
            },
            {
                'widget_id': 'alerts_panel',
                'widget_type': 'alerts_list',
                'title': 'Active Alerts',
                'description': 'Current system alerts',
                'config': {'max_alerts': 10, 'show_acknowledged': False},
                'position': (9, 0),
                'size': (3, 5),
                'refresh_interval': 10
            }
        ]
        
        for widget_config in default_widgets:
            widget = DashboardWidget(
                widget_id=widget_config['widget_id'],
                widget_type=widget_config['widget_type'],
                title=widget_config['title'],
                description=widget_config['description'],
                config=widget_config['config'],
                position=widget_config['position'],
                size=widget_config['size'],
                refresh_interval=widget_config['refresh_interval'],
                last_updated=datetime.now()
            )
            self.widgets[widget.widget_id] = widget
    
    async def start_dashboard(self):
        """Start the dashboard update loop"""
        self.is_running = True
        logger.info("Risk dashboard started")
        
        while self.is_running:
            try:
                await self._update_dashboard()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Dashboard update failed: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def stop_dashboard(self):
        """Stop the dashboard update loop"""
        self.is_running = False
        logger.info("Risk dashboard stopped")
    
    async def _update_dashboard(self):
        """Update all dashboard widgets"""
        update_tasks = []
        
        for widget_id, widget in self.widgets.items():
            # Check if widget needs updating
            time_since_update = (datetime.now() - widget.last_updated).total_seconds()
            if time_since_update >= widget.refresh_interval:
                task = self._update_widget(widget)
                update_tasks.append(task)
        
        # Update widgets concurrently
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # Create dashboard snapshot
        await self._create_snapshot()
        
        self.last_update = datetime.now()
    
    async def _update_widget(self, widget: DashboardWidget):
        """Update a specific widget"""
        try:
            if widget.widget_type == 'summary_card':
                widget.data = await self._get_summary_card_data(widget)
            elif widget.widget_type == 'gauge':
                widget.data = await self._get_gauge_data(widget)
            elif widget.widget_type == 'pie_chart':
                widget.data = await self._get_pie_chart_data(widget)
            elif widget.widget_type == 'table':
                widget.data = await self._get_table_data(widget)
            elif widget.widget_type == 'line_chart':
                widget.data = await self._get_line_chart_data(widget)
            elif widget.widget_type == 'alerts_list':
                widget.data = await self._get_alerts_data(widget)
            
            widget.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Widget update failed for {widget.widget_id}: {e}")
            widget.data = {'error': str(e)}
    
    async def _get_summary_card_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for summary card widget"""
        try:
            portfolio_metrics = await self.portfolio_manager.get_portfolio_metrics()
            
            if not portfolio_metrics:
                return {'error': 'No portfolio data available'}
            
            data = {
                'total_coverage': {
                    'value': portfolio_metrics.total_coverage,
                    'formatted': f"${portfolio_metrics.total_coverage:,.2f}",
                    'change': 0.0,  # Would calculate change from previous
                    'trend': 'stable'
                },
                'total_premium': {
                    'value': portfolio_metrics.total_premium,
                    'formatted': f"${portfolio_metrics.total_premium:,.2f}",
                    'change': 0.0,
                    'trend': 'stable'
                },
                'active_policies': {
                    'value': portfolio_metrics.total_policies,
                    'formatted': str(portfolio_metrics.total_policies),
                    'change': 0,
                    'trend': 'stable'
                },
                'average_risk_score': {
                    'value': portfolio_metrics.average_risk_score,
                    'formatted': f"{portfolio_metrics.average_risk_score:.3f}",
                    'change': 0.0,
                    'trend': 'stable'
                }
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Summary card data error: {e}")
            return {'error': str(e)}
    
    async def _get_gauge_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for gauge widget"""
        try:
            portfolio_metrics = await self.portfolio_manager.get_portfolio_metrics()
            
            if not portfolio_metrics:
                return {'error': 'No portfolio data available'}
            
            risk_score = portfolio_metrics.average_risk_score
            config = widget.config
            
            # Determine color based on thresholds
            thresholds = config.get('thresholds', [0.3, 0.6, 0.8])
            if risk_score < thresholds[0]:
                color = 'green'
                status = 'Low Risk'
            elif risk_score < thresholds[1]:
                color = 'yellow'
                status = 'Medium Risk'
            elif risk_score < thresholds[2]:
                color = 'orange'
                status = 'High Risk'
            else:
                color = 'red'
                status = 'Critical Risk'
            
            return {
                'value': risk_score,
                'min': config.get('min', 0),
                'max': config.get('max', 1),
                'color': color,
                'status': status,
                'thresholds': thresholds,
                'formatted': f"{risk_score:.1%}"
            }
            
        except Exception as e:
            logger.error(f"Gauge data error: {e}")
            return {'error': str(e)}
    
    async def _get_pie_chart_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for pie chart widget"""
        try:
            portfolio_metrics = await self.portfolio_manager.get_portfolio_metrics()
            
            if not portfolio_metrics:
                return {'error': 'No portfolio data available'}
            
            allocation = portfolio_metrics.asset_allocation
            
            # Convert to chart data format
            chart_data = []
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
            
            for i, (asset_class, percentage) in enumerate(allocation.items()):
                chart_data.append({
                    'name': asset_class.replace('_', ' ').title(),
                    'value': percentage,
                    'percentage': f"{percentage:.1%}",
                    'color': colors[i % len(colors)]
                })
            
            return {
                'data': chart_data,
                'total': sum(allocation.values()),
                'show_percentages': widget.config.get('show_percentages', True)
            }
            
        except Exception as e:
            logger.error(f"Pie chart data error: {e}")
            return {'error': str(e)}
    
    async def _get_table_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for table widget"""
        try:
            portfolio_metrics = await self.portfolio_manager.get_portfolio_metrics()
            
            if not portfolio_metrics:
                return {'error': 'No portfolio data available'}
            
            # Create table rows with key metrics
            rows = [
                {
                    'metric': 'Total Coverage',
                    'value': f"${portfolio_metrics.total_coverage:,.2f}",
                    'trend': '↑',
                    'threshold': 'N/A'
                },
                {
                    'metric': 'Average Risk Score',
                    'value': f"{portfolio_metrics.average_risk_score:.3f}",
                    'trend': '→',
                    'threshold': '< 0.6'
                },
                {
                    'metric': 'Diversification Ratio',
                    'value': f"{portfolio_metrics.diversification_ratio:.2f}",
                    'trend': '↑',
                    'threshold': '> 0.8'
                },
                {
                    'metric': 'Sharpe Ratio',
                    'value': f"{portfolio_metrics.sharpe_ratio:.2f}",
                    'trend': '↑',
                    'threshold': '> 1.0'
                },
                {
                    'metric': 'VaR (95%)',
                    'value': f"${portfolio_metrics.var_95:,.2f}",
                    'trend': '↓',
                    'threshold': 'Monitor'
                }
            ]
            
            return {
                'columns': widget.config.get('columns', ['metric', 'value', 'trend', 'threshold']),
                'rows': rows
            }
            
        except Exception as e:
            logger.error(f"Table data error: {e}")
            return {'error': str(e)}
    
    async def _get_line_chart_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for line chart widget"""
        try:
            # Get historical portfolio metrics
            # For now, using sample data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Generate sample time series data
            dates = []
            total_returns = []
            sharpe_ratios = []
            
            current_date = start_date
            while current_date <= end_date:
                dates.append(current_date.isoformat())
                total_returns.append(0.05 + 0.01 * (current_date.day % 7))  # Sample data
                sharpe_ratios.append(0.8 + 0.2 * (current_date.day % 5))  # Sample data
                current_date += timedelta(days=1)
            
            return {
                'dates': dates,
                'series': [
                    {
                        'name': 'Total Return',
                        'data': total_returns,
                        'color': '#45B7D1'
                    },
                    {
                        'name': 'Sharpe Ratio',
                        'data': sharpe_ratios,
                        'color': '#96CEB4'
                    }
                ],
                'timeframe': widget.config.get('timeframe', '30d')
            }
            
        except Exception as e:
            logger.error(f"Line chart data error: {e}")
            return {'error': str(e)}
    
    async def _get_alerts_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for alerts widget"""
        try:
            # Get active alerts from alert system
            # For now, returning sample alerts
            sample_alerts = [
                {
                    'id': 'alert_1',
                    'type': 'risk_threshold',
                    'severity': 'warning',
                    'title': 'High Risk Score',
                    'message': 'Portfolio risk score exceeds threshold',
                    'timestamp': datetime.now().isoformat(),
                    'acknowledged': False
                },
                {
                    'id': 'alert_2',
                    'type': 'concentration_risk',
                    'severity': 'info',
                    'title': 'Asset Concentration',
                    'message': 'High concentration in crypto assets',
                    'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
                    'acknowledged': False
                }
            ]
            
            return {
                'alerts': sample_alerts,
                'total_count': len(sample_alerts),
                'unacknowledged_count': sum(1 for a in sample_alerts if not a['acknowledged']),
                'max_alerts': widget.config.get('max_alerts', 10)
            }
            
        except Exception as e:
            logger.error(f"Alerts data error: {e}")
            return {'error': str(e)}
    
    async def _create_snapshot(self):
        """Create a dashboard snapshot"""
        try:
            portfolio_metrics = await self.portfolio_manager.get_portfolio_metrics()
            
            if not portfolio_metrics:
                return
            
            # Create snapshot
            snapshot = DashboardSnapshot(
                snapshot_id=f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(),
                portfolio_summary={
                    'total_coverage': portfolio_metrics.total_coverage,
                    'total_premium': portfolio_metrics.total_premium,
                    'total_policies': portfolio_metrics.total_policies,
                    'average_risk_score': portfolio_metrics.average_risk_score
                },
                risk_metrics={
                    'diversification_ratio': portfolio_metrics.diversification_ratio,
                    'var_95': portfolio_metrics.var_95,
                    'expected_shortfall': portfolio_metrics.expected_shortfall
                },
                performance_metrics={
                    'sharpe_ratio': portfolio_metrics.sharpe_ratio
                },
                alerts=[],  # Would include actual alerts
                active_policies=portfolio_metrics.total_policies,
                total_coverage=portfolio_metrics.total_coverage,
                total_premium=portfolio_metrics.total_premium,
                overall_risk_score=portfolio_metrics.average_risk_score
            )
            
            self.snapshots.append(snapshot)
            
        except Exception as e:
            logger.error(f"Snapshot creation failed: {e}")
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return {
            'widgets': {
                widget_id: {
                    'config': widget.__dict__,
                    'data': widget.data
                }
                for widget_id, widget in self.widgets.items()
            },
            'last_update': self.last_update.isoformat(),
            'is_running': self.is_running,
            'update_interval': self.update_interval
        }
    
    async def add_widget(self, widget: DashboardWidget):
        """Add a new widget to the dashboard"""
        self.widgets[widget.widget_id] = widget
        logger.info(f"Widget added: {widget.widget_id}")
    
    async def remove_widget(self, widget_id: str):
        """Remove a widget from the dashboard"""
        if widget_id in self.widgets:
            del self.widgets[widget_id]
            logger.info(f"Widget removed: {widget_id}")
    
    async def update_widget_config(self, widget_id: str, config: Dict[str, Any]):
        """Update widget configuration"""
        if widget_id in self.widgets:
            self.widgets[widget_id].config.update(config)
            logger.info(f"Widget config updated: {widget_id}")
    
    async def get_historical_snapshots(self, 
                                     start_date: datetime,
                                     end_date: datetime) -> List[DashboardSnapshot]:
        """Get historical dashboard snapshots"""
        filtered_snapshots = []
        
        for snapshot in self.snapshots:
            if start_date <= snapshot.timestamp <= end_date:
                filtered_snapshots.append(snapshot)
        
        return filtered_snapshots
    
    async def export_dashboard_data(self, format: str = 'json') -> str:
        """Export dashboard data"""
        data = await self.get_dashboard_data()
        
        if format == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


class AlertSystem:
    """Alert system for risk monitoring"""
    
    def __init__(self, 
                 portfolio_manager: PortfolioManager,
                 risk_calculator: RealTimeRiskCalculator):
        self.portfolio_manager = portfolio_manager
        self.risk_calculator = risk_calculator
        
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.notification_handlers: List[callable] = []
        
        self.is_monitoring = False
        self.check_interval = 60  # seconds
        
        # Initialize default alert rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        self.alert_rules = [
            {
                'rule_id': 'risk_threshold',
                'name': 'High Risk Score',
                'description': 'Alert when portfolio risk score exceeds threshold',
                'condition': lambda metrics: metrics.average_risk_score > 0.8,
                'severity': AlertSeverity.WARNING,
                'alert_type': AlertType.RISK_THRESHOLD,
                'threshold': 0.8,
                'cooldown': 300  # 5 minutes
            },
            {
                'rule_id': 'concentration_risk',
                'name': 'Asset Concentration',
                'description': 'Alert when asset concentration is too high',
                'condition': lambda metrics: max(metrics.asset_allocation.values()) > 0.5,
                'severity': AlertSeverity.WARNING,
                'alert_type': AlertType.CONCENTRATION_RISK,
                'threshold': 0.5,
                'cooldown': 600  # 10 minutes
            },
            {
                'rule_id': 'var_threshold',
                'name': 'Value at Risk',
                'description': 'Alert when VaR exceeds threshold',
                'condition': lambda metrics: metrics.var_95 > 10000,
                'severity': AlertSeverity.ERROR,
                'alert_type': AlertType.RISK_THRESHOLD,
                'threshold': 10000,
                'cooldown': 300
            }
        ]
    
    async def start_monitoring(self):
        """Start alert monitoring"""
        self.is_monitoring = True
        logger.info("Alert monitoring started")
        
        while self.is_monitoring:
            try:
                await self._check_alerts()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Alert monitoring error: {e}")
                await asyncio.sleep(30)  # Brief pause before retrying
    
    async def stop_monitoring(self):
        """Stop alert monitoring"""
        self.is_monitoring = False
        logger.info("Alert monitoring stopped")
    
    async def _check_alerts(self):
        """Check all alert rules"""
        portfolio_metrics = await self.portfolio_manager.get_portfolio_metrics()
        
        if not portfolio_metrics:
            return
        
        for rule in self.alert_rules:
            try:
                # Check if rule condition is met
                if rule['condition'](portfolio_metrics):
                    await self._trigger_alert(rule, portfolio_metrics)
                    
            except Exception as e:
                logger.error(f"Alert rule check failed for {rule['rule_id']}: {e}")
    
    async def _trigger_alert(self, rule: Dict[str, Any], metrics: PortfolioMetrics):
        """Trigger an alert"""
        alert_id = f"{rule['rule_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Check cooldown
        if await self._is_in_cooldown(rule['rule_id'], rule['cooldown']):
            return
        
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            alert_type=rule['alert_type'],
            severity=rule['severity'],
            title=rule['name'],
            message=rule['description'],
            details={
                'rule_id': rule['rule_id'],
                'threshold': rule['threshold'],
                'current_value': await self._get_current_value(rule, metrics),
                'portfolio_metrics': metrics.__dict__
            },
            threshold_value=rule['threshold'],
            current_value=await self._get_current_value(rule, metrics),
            policy_ids=[],  # Would include relevant policy IDs
            timestamp=datetime.now()
        )
        
        self.alerts[alert_id] = alert
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.warning(f"Alert triggered: {alert.title} ({alert.severity.value})")
    
    async def _is_in_cooldown(self, rule_id: str, cooldown_seconds: int) -> bool:
        """Check if alert rule is in cooldown period"""
        cutoff_time = datetime.now() - timedelta(seconds=cooldown_seconds)
        
        for alert in self.alerts.values():
            if (alert.details.get('rule_id') == rule_id and 
                alert.timestamp > cutoff_time):
                return True
        
        return False
    
    async def _get_current_value(self, rule: Dict[str, Any], metrics: PortfolioMetrics) -> float:
        """Get current value for alert rule"""
        if rule['rule_id'] == 'risk_threshold':
            return metrics.average_risk_score
        elif rule['rule_id'] == 'concentration_risk':
            return max(metrics.asset_allocation.values())
        elif rule['rule_id'] == 'var_threshold':
            return metrics.var_95
        else:
            return 0.0
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
    
    async def add_notification_handler(self, handler: callable):
        """Add a notification handler"""
        self.notification_handlers.append(handler)
        logger.info("Notification handler added")
    
    async def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            self.alerts[alert_id].metadata['acknowledged_by'] = user
            self.alerts[alert_id].metadata['acknowledged_at'] = datetime.now().isoformat()
            logger.info(f"Alert acknowledged: {alert_id} by {user}")
    
    async def resolve_alert(self, alert_id: str, user: str = "system"):
        """Resolve an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].metadata['resolved_by'] = user
            self.alerts[alert_id].metadata['resolved_at'] = datetime.now().isoformat()
            logger.info(f"Alert resolved: {alert_id} by {user}")
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get active (unresolved) alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    async def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity level"""
        return [alert for alert in self.alerts.values() if alert.severity == severity]
    
    async def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Get alerts by type"""
        return [alert for alert in self.alerts.values() if alert.alert_type == alert_type]
    
    async def add_alert_rule(self, rule: Dict[str, Any]):
        """Add a new alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Alert rule added: {rule['rule_id']}")
    
    async def remove_alert_rule(self, rule_id: str):
        """Remove an alert rule"""
        self.alert_rules = [rule for rule in self.alert_rules if rule['rule_id'] != rule_id]
        logger.info(f"Alert rule removed: {rule_id}")
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alerts)
        active_alerts = len(await self.get_active_alerts())
        
        severity_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for alert in self.alerts.values():
            severity_counts[alert.severity.value] += 1
            type_counts[alert.alert_type.value] += 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': total_alerts - active_alerts,
            'severity_distribution': dict(severity_counts),
            'type_distribution': dict(type_counts),
            'alert_rules_count': len(self.alert_rules),
            'monitoring_status': self.is_monitoring
        }


# Sample notification handlers
async def email_notification_handler(alert: Alert):
    """Sample email notification handler"""
    logger.info(f"Email notification: {alert.title} ({alert.severity.value})")
    # In practice, this would send an actual email


async def slack_notification_handler(alert: Alert):
    """Sample Slack notification handler"""
    logger.info(f"Slack notification: {alert.title} ({alert.severity.value})")
    # In practice, this would send a Slack message


async def sms_notification_handler(alert: Alert):
    """Sample SMS notification handler"""
    if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
        logger.info(f"SMS notification: {alert.title} ({alert.severity.value})")
        # In practice, this would send an SMS


# Utility functions
async def create_risk_dashboard(portfolio_manager: PortfolioManager,
                               risk_calculator: RealTimeRiskCalculator,
                               risk_metrics: RiskMetrics,
                               performance_analyzer: PerformanceAnalyzer) -> RiskDashboard:
    """Create a risk dashboard instance"""
    return RiskDashboard(portfolio_manager, risk_calculator, risk_metrics, performance_analyzer)


async def create_alert_system(portfolio_manager: PortfolioManager,
                            risk_calculator: RealTimeRiskCalculator) -> AlertSystem:
    """Create an alert system instance"""
    return AlertSystem(portfolio_manager, risk_calculator)


async def setup_default_notifications(alert_system: AlertSystem):
    """Set up default notification handlers"""
    await alert_system.add_notification_handler(email_notification_handler)
    await alert_system.add_notification_handler(slack_notification_handler)
    await alert_system.add_notification_handler(sms_notification_handler)


async def create_custom_widget(widget_id: str,
                             widget_type: str,
                             title: str,
                             config: Dict[str, Any],
                             position: Tuple[int, int] = (0, 0),
                             size: Tuple[int, int] = (4, 3)) -> DashboardWidget:
    """Create a custom dashboard widget"""
    return DashboardWidget(
        widget_id=widget_id,
        widget_type=widget_type,
        title=title,
        description=f"Custom {widget_type} widget",
        config=config,
        position=position,
        size=size,
        refresh_interval=60,
        last_updated=datetime.now()
    )