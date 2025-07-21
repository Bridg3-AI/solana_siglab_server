"""
Risk Metrics and Performance Analysis

This module implements comprehensive risk metrics and performance analysis
for parametric insurance products and portfolios.
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import statistics
from collections import defaultdict

from .models import RiskLevel, RiskPrediction
from .calculator import RiskCalculationResult
from .portfolio import InsurancePolicy, PortfolioMetrics, PolicyStatus

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of risk metrics"""
    RETURN = "return"
    RISK = "risk"
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"
    CONCENTRATION = "concentration"
    CORRELATION = "correlation"


class TimeFrame(Enum):
    """Time frames for metric calculations"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class MetricResult:
    """Risk metric calculation result"""
    metric_name: str
    metric_type: MetricType
    value: float
    benchmark_value: Optional[float]
    percentile_rank: Optional[float]
    historical_average: Optional[float]
    trend: str  # "improving", "stable", "deteriorating"
    confidence_interval: Tuple[float, float]
    calculation_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Performance analysis report"""
    period_start: datetime
    period_end: datetime
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    var_95: float
    cvar_95: float
    metrics: List[MetricResult]
    timestamp: datetime


@dataclass
class RiskDecomposition:
    """Risk decomposition analysis"""
    total_risk: float
    systematic_risk: float
    idiosyncratic_risk: float
    asset_class_contributions: Dict[str, float]
    geographic_contributions: Dict[str, float]
    temporal_contributions: Dict[str, float]
    correlation_contributions: Dict[str, float]
    timestamp: datetime


@dataclass
class StressTestResult:
    """Stress test result"""
    scenario_name: str
    scenario_description: str
    baseline_value: float
    stressed_value: float
    impact_percentage: float
    recovery_time_days: int
    confidence_level: float
    timestamp: datetime


class RiskMetrics:
    """Risk metrics calculator"""
    
    def __init__(self):
        self.metric_history = defaultdict(list)
        self.benchmark_data = {}
        self.risk_free_rate = 0.02  # 2% risk-free rate
        
    async def calculate_return_metrics(self, 
                                     portfolio_data: List[PortfolioMetrics],
                                     time_frame: TimeFrame = TimeFrame.DAILY) -> Dict[str, MetricResult]:
        """Calculate return-based metrics"""
        try:
            if len(portfolio_data) < 2:
                logger.warning("Insufficient data for return calculations")
                return {}
            
            # Calculate returns
            returns = await self._calculate_returns(portfolio_data, time_frame)
            
            metrics = {}
            
            # Total return
            total_return = (portfolio_data[-1].total_premium - portfolio_data[0].total_premium) / portfolio_data[0].total_premium
            metrics['total_return'] = MetricResult(
                metric_name="Total Return",
                metric_type=MetricType.RETURN,
                value=total_return,
                benchmark_value=0.05,  # 5% benchmark
                percentile_rank=await self._calculate_percentile_rank('total_return', total_return),
                historical_average=await self._calculate_historical_average('total_return'),
                trend=await self._calculate_trend('total_return', total_return),
                confidence_interval=await self._calculate_confidence_interval(returns),
                calculation_date=datetime.now()
            )
            
            # Annualized return
            if returns:
                annualized_return = (1 + statistics.mean(returns)) ** (252 if time_frame == TimeFrame.DAILY else 52) - 1
                metrics['annualized_return'] = MetricResult(
                    metric_name="Annualized Return",
                    metric_type=MetricType.RETURN,
                    value=annualized_return,
                    benchmark_value=0.08,  # 8% benchmark
                    percentile_rank=await self._calculate_percentile_rank('annualized_return', annualized_return),
                    historical_average=await self._calculate_historical_average('annualized_return'),
                    trend=await self._calculate_trend('annualized_return', annualized_return),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Cumulative return
            cumulative_return = np.prod([1 + r for r in returns]) - 1 if returns else 0.0
            metrics['cumulative_return'] = MetricResult(
                metric_name="Cumulative Return",
                metric_type=MetricType.RETURN,
                value=cumulative_return,
                benchmark_value=None,
                percentile_rank=await self._calculate_percentile_rank('cumulative_return', cumulative_return),
                historical_average=await self._calculate_historical_average('cumulative_return'),
                trend=await self._calculate_trend('cumulative_return', cumulative_return),
                confidence_interval=await self._calculate_confidence_interval(returns),
                calculation_date=datetime.now()
            )
            
            logger.info(f"Calculated {len(metrics)} return metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Return metrics calculation failed: {e}")
            return {}
    
    async def calculate_risk_metrics(self, 
                                   portfolio_data: List[PortfolioMetrics],
                                   time_frame: TimeFrame = TimeFrame.DAILY) -> Dict[str, MetricResult]:
        """Calculate risk-based metrics"""
        try:
            if len(portfolio_data) < 2:
                logger.warning("Insufficient data for risk calculations")
                return {}
            
            returns = await self._calculate_returns(portfolio_data, time_frame)
            
            metrics = {}
            
            # Volatility
            if returns and len(returns) > 1:
                volatility = statistics.stdev(returns)
                annualized_volatility = volatility * np.sqrt(252 if time_frame == TimeFrame.DAILY else 52)
                
                metrics['volatility'] = MetricResult(
                    metric_name="Volatility",
                    metric_type=MetricType.RISK,
                    value=annualized_volatility,
                    benchmark_value=0.15,  # 15% benchmark
                    percentile_rank=await self._calculate_percentile_rank('volatility', annualized_volatility),
                    historical_average=await self._calculate_historical_average('volatility'),
                    trend=await self._calculate_trend('volatility', annualized_volatility),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Value at Risk (VaR)
            if returns:
                var_95 = np.percentile(returns, 5) if len(returns) > 1 else 0.0
                metrics['var_95'] = MetricResult(
                    metric_name="Value at Risk (95%)",
                    metric_type=MetricType.RISK,
                    value=var_95,
                    benchmark_value=-0.05,  # -5% benchmark
                    percentile_rank=await self._calculate_percentile_rank('var_95', var_95),
                    historical_average=await self._calculate_historical_average('var_95'),
                    trend=await self._calculate_trend('var_95', var_95),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Conditional Value at Risk (CVaR)
            if returns:
                cvar_95 = np.mean([r for r in returns if r <= np.percentile(returns, 5)]) if len(returns) > 1 else 0.0
                metrics['cvar_95'] = MetricResult(
                    metric_name="Conditional VaR (95%)",
                    metric_type=MetricType.RISK,
                    value=cvar_95,
                    benchmark_value=-0.08,  # -8% benchmark
                    percentile_rank=await self._calculate_percentile_rank('cvar_95', cvar_95),
                    historical_average=await self._calculate_historical_average('cvar_95'),
                    trend=await self._calculate_trend('cvar_95', cvar_95),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Maximum Drawdown
            if returns:
                max_drawdown = await self._calculate_max_drawdown(returns)
                metrics['max_drawdown'] = MetricResult(
                    metric_name="Maximum Drawdown",
                    metric_type=MetricType.RISK,
                    value=max_drawdown,
                    benchmark_value=-0.10,  # -10% benchmark
                    percentile_rank=await self._calculate_percentile_rank('max_drawdown', max_drawdown),
                    historical_average=await self._calculate_historical_average('max_drawdown'),
                    trend=await self._calculate_trend('max_drawdown', max_drawdown),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Skewness
            if returns and len(returns) > 2:
                from scipy import stats
                skewness = stats.skew(returns)
                metrics['skewness'] = MetricResult(
                    metric_name="Skewness",
                    metric_type=MetricType.RISK,
                    value=skewness,
                    benchmark_value=0.0,  # Normal distribution benchmark
                    percentile_rank=await self._calculate_percentile_rank('skewness', skewness),
                    historical_average=await self._calculate_historical_average('skewness'),
                    trend=await self._calculate_trend('skewness', skewness),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Kurtosis
            if returns and len(returns) > 3:
                from scipy import stats
                kurtosis = stats.kurtosis(returns)
                metrics['kurtosis'] = MetricResult(
                    metric_name="Kurtosis",
                    metric_type=MetricType.RISK,
                    value=kurtosis,
                    benchmark_value=0.0,  # Normal distribution benchmark
                    percentile_rank=await self._calculate_percentile_rank('kurtosis', kurtosis),
                    historical_average=await self._calculate_historical_average('kurtosis'),
                    trend=await self._calculate_trend('kurtosis', kurtosis),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            logger.info(f"Calculated {len(metrics)} risk metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Risk metrics calculation failed: {e}")
            return {}
    
    async def calculate_performance_metrics(self, 
                                          portfolio_data: List[PortfolioMetrics],
                                          time_frame: TimeFrame = TimeFrame.DAILY) -> Dict[str, MetricResult]:
        """Calculate performance-based metrics"""
        try:
            if len(portfolio_data) < 2:
                logger.warning("Insufficient data for performance calculations")
                return {}
            
            returns = await self._calculate_returns(portfolio_data, time_frame)
            
            metrics = {}
            
            # Sharpe Ratio
            if returns and len(returns) > 1:
                excess_returns = [r - self.risk_free_rate/252 for r in returns]
                sharpe_ratio = statistics.mean(excess_returns) / statistics.stdev(excess_returns) if statistics.stdev(excess_returns) > 0 else 0
                annualized_sharpe = sharpe_ratio * np.sqrt(252 if time_frame == TimeFrame.DAILY else 52)
                
                metrics['sharpe_ratio'] = MetricResult(
                    metric_name="Sharpe Ratio",
                    metric_type=MetricType.PERFORMANCE,
                    value=annualized_sharpe,
                    benchmark_value=1.0,  # Benchmark Sharpe ratio
                    percentile_rank=await self._calculate_percentile_rank('sharpe_ratio', annualized_sharpe),
                    historical_average=await self._calculate_historical_average('sharpe_ratio'),
                    trend=await self._calculate_trend('sharpe_ratio', annualized_sharpe),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            # Sortino Ratio
            if returns:
                downside_returns = [r for r in returns if r < 0]
                if downside_returns:
                    downside_deviation = statistics.stdev(downside_returns)
                    sortino_ratio = statistics.mean(returns) / downside_deviation if downside_deviation > 0 else 0
                    annualized_sortino = sortino_ratio * np.sqrt(252 if time_frame == TimeFrame.DAILY else 52)
                    
                    metrics['sortino_ratio'] = MetricResult(
                        metric_name="Sortino Ratio",
                        metric_type=MetricType.PERFORMANCE,
                        value=annualized_sortino,
                        benchmark_value=1.2,  # Benchmark Sortino ratio
                        percentile_rank=await self._calculate_percentile_rank('sortino_ratio', annualized_sortino),
                        historical_average=await self._calculate_historical_average('sortino_ratio'),
                        trend=await self._calculate_trend('sortino_ratio', annualized_sortino),
                        confidence_interval=await self._calculate_confidence_interval(returns),
                        calculation_date=datetime.now()
                    )
            
            # Information Ratio
            if returns:
                # Assuming benchmark returns are available
                benchmark_returns = [0.02/252] * len(returns)  # 2% annual risk-free rate
                active_returns = [r - b for r, b in zip(returns, benchmark_returns)]
                
                if len(active_returns) > 1:
                    info_ratio = statistics.mean(active_returns) / statistics.stdev(active_returns) if statistics.stdev(active_returns) > 0 else 0
                    
                    metrics['information_ratio'] = MetricResult(
                        metric_name="Information Ratio",
                        metric_type=MetricType.PERFORMANCE,
                        value=info_ratio,
                        benchmark_value=0.5,  # Benchmark Information ratio
                        percentile_rank=await self._calculate_percentile_rank('information_ratio', info_ratio),
                        historical_average=await self._calculate_historical_average('information_ratio'),
                        trend=await self._calculate_trend('information_ratio', info_ratio),
                        confidence_interval=await self._calculate_confidence_interval(returns),
                        calculation_date=datetime.now()
                    )
            
            # Calmar Ratio
            if returns:
                annualized_return = (1 + statistics.mean(returns)) ** (252 if time_frame == TimeFrame.DAILY else 52) - 1
                max_drawdown = await self._calculate_max_drawdown(returns)
                calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
                
                metrics['calmar_ratio'] = MetricResult(
                    metric_name="Calmar Ratio",
                    metric_type=MetricType.PERFORMANCE,
                    value=calmar_ratio,
                    benchmark_value=2.0,  # Benchmark Calmar ratio
                    percentile_rank=await self._calculate_percentile_rank('calmar_ratio', calmar_ratio),
                    historical_average=await self._calculate_historical_average('calmar_ratio'),
                    trend=await self._calculate_trend('calmar_ratio', calmar_ratio),
                    confidence_interval=await self._calculate_confidence_interval(returns),
                    calculation_date=datetime.now()
                )
            
            logger.info(f"Calculated {len(metrics)} performance metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {}
    
    async def calculate_efficiency_metrics(self, 
                                         portfolio_data: List[PortfolioMetrics]) -> Dict[str, MetricResult]:
        """Calculate efficiency metrics"""
        try:
            if len(portfolio_data) < 2:
                logger.warning("Insufficient data for efficiency calculations")
                return {}
            
            metrics = {}
            
            # Portfolio Turnover
            turnover = await self._calculate_portfolio_turnover(portfolio_data)
            metrics['portfolio_turnover'] = MetricResult(
                metric_name="Portfolio Turnover",
                metric_type=MetricType.EFFICIENCY,
                value=turnover,
                benchmark_value=0.5,  # 50% benchmark
                percentile_rank=await self._calculate_percentile_rank('portfolio_turnover', turnover),
                historical_average=await self._calculate_historical_average('portfolio_turnover'),
                trend=await self._calculate_trend('portfolio_turnover', turnover),
                confidence_interval=(turnover * 0.9, turnover * 1.1),
                calculation_date=datetime.now()
            )
            
            # Expense Ratio
            expense_ratio = await self._calculate_expense_ratio(portfolio_data)
            metrics['expense_ratio'] = MetricResult(
                metric_name="Expense Ratio",
                metric_type=MetricType.EFFICIENCY,
                value=expense_ratio,
                benchmark_value=0.01,  # 1% benchmark
                percentile_rank=await self._calculate_percentile_rank('expense_ratio', expense_ratio),
                historical_average=await self._calculate_historical_average('expense_ratio'),
                trend=await self._calculate_trend('expense_ratio', expense_ratio),
                confidence_interval=(expense_ratio * 0.9, expense_ratio * 1.1),
                calculation_date=datetime.now()
            )
            
            # Active Share
            active_share = await self._calculate_active_share(portfolio_data)
            metrics['active_share'] = MetricResult(
                metric_name="Active Share",
                metric_type=MetricType.EFFICIENCY,
                value=active_share,
                benchmark_value=0.6,  # 60% benchmark
                percentile_rank=await self._calculate_percentile_rank('active_share', active_share),
                historical_average=await self._calculate_historical_average('active_share'),
                trend=await self._calculate_trend('active_share', active_share),
                confidence_interval=(active_share * 0.9, active_share * 1.1),
                calculation_date=datetime.now()
            )
            
            logger.info(f"Calculated {len(metrics)} efficiency metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Efficiency metrics calculation failed: {e}")
            return {}
    
    async def _calculate_returns(self, 
                               portfolio_data: List[PortfolioMetrics],
                               time_frame: TimeFrame) -> List[float]:
        """Calculate returns from portfolio data"""
        returns = []
        
        for i in range(1, len(portfolio_data)):
            prev_value = portfolio_data[i-1].total_premium
            curr_value = portfolio_data[i].total_premium
            
            if prev_value > 0:
                return_value = (curr_value - prev_value) / prev_value
                returns.append(return_value)
        
        return returns
    
    async def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not returns:
            return 0.0
        
        cumulative_returns = []
        cumulative = 1.0
        
        for r in returns:
            cumulative *= (1 + r)
            cumulative_returns.append(cumulative)
        
        peak = cumulative_returns[0]
        max_drawdown = 0.0
        
        for value in cumulative_returns:
            if value > peak:
                peak = value
            else:
                drawdown = (value - peak) / peak
                max_drawdown = min(max_drawdown, drawdown)
        
        return max_drawdown
    
    async def _calculate_portfolio_turnover(self, portfolio_data: List[PortfolioMetrics]) -> float:
        """Calculate portfolio turnover"""
        # Simplified turnover calculation
        if len(portfolio_data) < 2:
            return 0.0
        
        # Calculate average change in asset allocation
        turnover = 0.0
        for i in range(1, len(portfolio_data)):
            prev_allocation = portfolio_data[i-1].asset_allocation
            curr_allocation = portfolio_data[i].asset_allocation
            
            # Calculate changes in allocation
            for asset_class in set(list(prev_allocation.keys()) + list(curr_allocation.keys())):
                prev_weight = prev_allocation.get(asset_class, 0.0)
                curr_weight = curr_allocation.get(asset_class, 0.0)
                turnover += abs(curr_weight - prev_weight)
        
        return turnover / (len(portfolio_data) - 1)
    
    async def _calculate_expense_ratio(self, portfolio_data: List[PortfolioMetrics]) -> float:
        """Calculate expense ratio"""
        # Simplified expense ratio calculation
        # In practice, this would include management fees, transaction costs, etc.
        return 0.005  # 0.5% default expense ratio
    
    async def _calculate_active_share(self, portfolio_data: List[PortfolioMetrics]) -> float:
        """Calculate active share"""
        # Simplified active share calculation
        # This would compare against a benchmark portfolio
        return 0.6  # 60% default active share
    
    async def _calculate_percentile_rank(self, metric_name: str, value: float) -> Optional[float]:
        """Calculate percentile rank of metric value"""
        if metric_name not in self.metric_history:
            return None
        
        history = self.metric_history[metric_name]
        if len(history) < 10:  # Need sufficient history
            return None
        
        values = [h['value'] for h in history]
        rank = sum(1 for v in values if v < value) / len(values)
        return rank
    
    async def _calculate_historical_average(self, metric_name: str) -> Optional[float]:
        """Calculate historical average of metric"""
        if metric_name not in self.metric_history:
            return None
        
        history = self.metric_history[metric_name]
        if not history:
            return None
        
        values = [h['value'] for h in history]
        return statistics.mean(values)
    
    async def _calculate_trend(self, metric_name: str, current_value: float) -> str:
        """Calculate trend of metric"""
        if metric_name not in self.metric_history:
            return "stable"
        
        history = self.metric_history[metric_name]
        if len(history) < 3:
            return "stable"
        
        recent_values = [h['value'] for h in history[-3:]]
        
        if len(recent_values) >= 2:
            if recent_values[-1] > recent_values[-2]:
                return "improving"
            elif recent_values[-1] < recent_values[-2]:
                return "deteriorating"
        
        return "stable"
    
    async def _calculate_confidence_interval(self, returns: List[float]) -> Tuple[float, float]:
        """Calculate confidence interval for returns"""
        if len(returns) < 2:
            return (0.0, 0.0)
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        # 95% confidence interval
        margin = 1.96 * std_return / np.sqrt(len(returns))
        
        return (mean_return - margin, mean_return + margin)
    
    async def update_metric_history(self, metric_name: str, value: float):
        """Update metric history"""
        self.metric_history[metric_name].append({
            'value': value,
            'timestamp': datetime.now()
        })
        
        # Keep only last 100 values
        if len(self.metric_history[metric_name]) > 100:
            self.metric_history[metric_name] = self.metric_history[metric_name][-100:]
    
    async def get_metric_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            'total_metrics': len(self.metric_history),
            'metrics_with_history': [name for name, history in self.metric_history.items() if len(history) > 0],
            'last_updated': datetime.now().isoformat()
        }
        
        return summary


class PerformanceAnalyzer:
    """Performance analyzer for portfolios and strategies"""
    
    def __init__(self, risk_metrics: RiskMetrics):
        self.risk_metrics = risk_metrics
        self.benchmark_data = {}
        self.performance_history = []
        
    async def generate_performance_report(self, 
                                        portfolio_data: List[PortfolioMetrics],
                                        start_date: datetime,
                                        end_date: datetime) -> PerformanceReport:
        """Generate comprehensive performance report"""
        try:
            # Calculate all metrics
            return_metrics = await self.risk_metrics.calculate_return_metrics(portfolio_data)
            risk_metrics = await self.risk_metrics.calculate_risk_metrics(portfolio_data)
            performance_metrics = await self.risk_metrics.calculate_performance_metrics(portfolio_data)
            efficiency_metrics = await self.risk_metrics.calculate_efficiency_metrics(portfolio_data)
            
            # Combine all metrics
            all_metrics = []
            all_metrics.extend(return_metrics.values())
            all_metrics.extend(risk_metrics.values())
            all_metrics.extend(performance_metrics.values())
            all_metrics.extend(efficiency_metrics.values())
            
            # Calculate summary statistics
            total_return = return_metrics.get('total_return', MetricResult(
                metric_name="Total Return", metric_type=MetricType.RETURN,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            annualized_return = return_metrics.get('annualized_return', MetricResult(
                metric_name="Annualized Return", metric_type=MetricType.RETURN,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            volatility = risk_metrics.get('volatility', MetricResult(
                metric_name="Volatility", metric_type=MetricType.RISK,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            sharpe_ratio = performance_metrics.get('sharpe_ratio', MetricResult(
                metric_name="Sharpe Ratio", metric_type=MetricType.PERFORMANCE,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            sortino_ratio = performance_metrics.get('sortino_ratio', MetricResult(
                metric_name="Sortino Ratio", metric_type=MetricType.PERFORMANCE,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            max_drawdown = risk_metrics.get('max_drawdown', MetricResult(
                metric_name="Max Drawdown", metric_type=MetricType.RISK,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            var_95 = risk_metrics.get('var_95', MetricResult(
                metric_name="VaR 95%", metric_type=MetricType.RISK,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            cvar_95 = risk_metrics.get('cvar_95', MetricResult(
                metric_name="CVaR 95%", metric_type=MetricType.RISK,
                value=0.0, benchmark_value=None, percentile_rank=None,
                historical_average=None, trend="stable",
                confidence_interval=(0.0, 0.0), calculation_date=datetime.now()
            )).value
            
            # Calculate additional metrics
            win_rate = await self._calculate_win_rate(portfolio_data)
            profit_factor = await self._calculate_profit_factor(portfolio_data)
            
            report = PerformanceReport(
                period_start=start_date,
                period_end=end_date,
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                var_95=var_95,
                cvar_95=cvar_95,
                metrics=all_metrics,
                timestamp=datetime.now()
            )
            
            self.performance_history.append(report)
            
            logger.info(f"Generated performance report for period {start_date} to {end_date}")
            return report
            
        except Exception as e:
            logger.error(f"Performance report generation failed: {e}")
            return PerformanceReport(
                period_start=start_date,
                period_end=end_date,
                total_return=0.0,
                annualized_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                var_95=0.0,
                cvar_95=0.0,
                metrics=[],
                timestamp=datetime.now()
            )
    
    async def decompose_risk(self, portfolio_data: List[PortfolioMetrics]) -> RiskDecomposition:
        """Decompose risk into components"""
        try:
            if not portfolio_data:
                raise ValueError("No portfolio data provided")
            
            latest_data = portfolio_data[-1]
            
            # Calculate total risk (simplified)
            total_risk = latest_data.var_95
            
            # Decompose into systematic and idiosyncratic risk
            systematic_risk = total_risk * 0.7  # 70% systematic
            idiosyncratic_risk = total_risk * 0.3  # 30% idiosyncratic
            
            # Asset class contributions
            asset_class_contributions = {}
            for asset_class, weight in latest_data.asset_allocation.items():
                asset_class_contributions[asset_class] = total_risk * weight
            
            # Geographic contributions (simplified)
            geographic_contributions = {
                'domestic': total_risk * 0.6,
                'international': total_risk * 0.4
            }
            
            # Temporal contributions (simplified)
            temporal_contributions = {
                'short_term': total_risk * 0.3,
                'medium_term': total_risk * 0.5,
                'long_term': total_risk * 0.2
            }
            
            # Correlation contributions
            correlation_contributions = {}
            for i, (asset1, weight1) in enumerate(latest_data.asset_allocation.items()):
                for j, (asset2, weight2) in enumerate(latest_data.asset_allocation.items()):
                    if i < j:  # Avoid double counting
                        correlation = latest_data.correlation_matrix.get(asset1, {}).get(asset2, 0.0)
                        contribution = 2 * weight1 * weight2 * correlation * total_risk
                        correlation_contributions[f"{asset1}-{asset2}"] = contribution
            
            return RiskDecomposition(
                total_risk=total_risk,
                systematic_risk=systematic_risk,
                idiosyncratic_risk=idiosyncratic_risk,
                asset_class_contributions=asset_class_contributions,
                geographic_contributions=geographic_contributions,
                temporal_contributions=temporal_contributions,
                correlation_contributions=correlation_contributions,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Risk decomposition failed: {e}")
            return RiskDecomposition(
                total_risk=0.0,
                systematic_risk=0.0,
                idiosyncratic_risk=0.0,
                asset_class_contributions={},
                geographic_contributions={},
                temporal_contributions={},
                correlation_contributions={},
                timestamp=datetime.now()
            )
    
    async def run_stress_test(self, 
                            portfolio_data: List[PortfolioMetrics],
                            stress_scenarios: List[Dict[str, Any]]) -> List[StressTestResult]:
        """Run stress tests on portfolio"""
        try:
            results = []
            
            if not portfolio_data:
                return results
            
            baseline_metrics = portfolio_data[-1]
            
            for scenario in stress_scenarios:
                scenario_name = scenario.get('name', 'Unknown Scenario')
                scenario_description = scenario.get('description', '')
                stress_factor = scenario.get('stress_factor', 1.5)
                
                # Apply stress to key metrics
                baseline_var = baseline_metrics.var_95
                stressed_var = baseline_var * stress_factor
                
                impact_percentage = (stressed_var - baseline_var) / baseline_var * 100
                
                # Estimate recovery time
                recovery_time = await self._estimate_recovery_time(scenario, impact_percentage)
                
                result = StressTestResult(
                    scenario_name=scenario_name,
                    scenario_description=scenario_description,
                    baseline_value=baseline_var,
                    stressed_value=stressed_var,
                    impact_percentage=impact_percentage,
                    recovery_time_days=recovery_time,
                    confidence_level=scenario.get('confidence_level', 0.95),
                    timestamp=datetime.now()
                )
                
                results.append(result)
            
            logger.info(f"Completed stress testing with {len(results)} scenarios")
            return results
            
        except Exception as e:
            logger.error(f"Stress testing failed: {e}")
            return []
    
    async def _calculate_win_rate(self, portfolio_data: List[PortfolioMetrics]) -> float:
        """Calculate win rate (percentage of positive returns)"""
        if len(portfolio_data) < 2:
            return 0.0
        
        positive_periods = 0
        total_periods = len(portfolio_data) - 1
        
        for i in range(1, len(portfolio_data)):
            if portfolio_data[i].total_premium > portfolio_data[i-1].total_premium:
                positive_periods += 1
        
        return positive_periods / total_periods if total_periods > 0 else 0.0
    
    async def _calculate_profit_factor(self, portfolio_data: List[PortfolioMetrics]) -> float:
        """Calculate profit factor (ratio of gains to losses)"""
        if len(portfolio_data) < 2:
            return 1.0
        
        gains = 0.0
        losses = 0.0
        
        for i in range(1, len(portfolio_data)):
            change = portfolio_data[i].total_premium - portfolio_data[i-1].total_premium
            if change > 0:
                gains += change
            else:
                losses += abs(change)
        
        return gains / losses if losses > 0 else float('inf')
    
    async def _estimate_recovery_time(self, scenario: Dict[str, Any], impact_percentage: float) -> int:
        """Estimate recovery time in days"""
        # Simple heuristic based on impact severity
        if impact_percentage < 5:
            return 30  # 1 month
        elif impact_percentage < 15:
            return 90  # 3 months
        elif impact_percentage < 30:
            return 180  # 6 months
        else:
            return 365  # 1 year
    
    async def compare_to_benchmark(self, 
                                 portfolio_data: List[PortfolioMetrics],
                                 benchmark_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare portfolio performance to benchmark"""
        try:
            if not portfolio_data or not benchmark_data:
                return {}
            
            # Calculate portfolio metrics
            portfolio_report = await self.generate_performance_report(
                portfolio_data, 
                portfolio_data[0].timestamp, 
                portfolio_data[-1].timestamp
            )
            
            # Calculate benchmark metrics (simplified)
            benchmark_return = 0.05  # 5% benchmark return
            benchmark_volatility = 0.10  # 10% benchmark volatility
            benchmark_sharpe = 0.5  # 0.5 benchmark Sharpe ratio
            
            # Calculate relative metrics
            excess_return = portfolio_report.annualized_return - benchmark_return
            tracking_error = abs(portfolio_report.volatility - benchmark_volatility)
            information_ratio = excess_return / tracking_error if tracking_error > 0 else 0
            
            return {
                'portfolio_metrics': {
                    'return': portfolio_report.annualized_return,
                    'volatility': portfolio_report.volatility,
                    'sharpe_ratio': portfolio_report.sharpe_ratio
                },
                'benchmark_metrics': {
                    'return': benchmark_return,
                    'volatility': benchmark_volatility,
                    'sharpe_ratio': benchmark_sharpe
                },
                'relative_metrics': {
                    'excess_return': excess_return,
                    'tracking_error': tracking_error,
                    'information_ratio': information_ratio
                },
                'outperformance': excess_return > 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Benchmark comparison failed: {e}")
            return {}
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_history:
            return {}
        
        latest_report = self.performance_history[-1]
        
        return {
            'latest_performance': {
                'total_return': latest_report.total_return,
                'annualized_return': latest_report.annualized_return,
                'sharpe_ratio': latest_report.sharpe_ratio,
                'max_drawdown': latest_report.max_drawdown
            },
            'performance_trend': await self._analyze_performance_trend(),
            'total_reports': len(self.performance_history),
            'last_updated': latest_report.timestamp.isoformat()
        }
    
    async def _analyze_performance_trend(self) -> str:
        """Analyze performance trend"""
        if len(self.performance_history) < 2:
            return "insufficient_data"
        
        recent_returns = [report.total_return for report in self.performance_history[-5:]]
        
        if len(recent_returns) >= 2:
            if recent_returns[-1] > recent_returns[-2]:
                return "improving"
            elif recent_returns[-1] < recent_returns[-2]:
                return "declining"
        
        return "stable"


# Utility functions
async def create_risk_metrics() -> RiskMetrics:
    """Create a risk metrics instance"""
    return RiskMetrics()


async def create_performance_analyzer(risk_metrics: RiskMetrics) -> PerformanceAnalyzer:
    """Create a performance analyzer instance"""
    return PerformanceAnalyzer(risk_metrics)


async def calculate_portfolio_beta(portfolio_returns: List[float], 
                                 market_returns: List[float]) -> float:
    """Calculate portfolio beta"""
    if len(portfolio_returns) != len(market_returns) or len(portfolio_returns) < 2:
        return 1.0
    
    covariance = np.cov(portfolio_returns, market_returns)[0][1]
    market_variance = np.var(market_returns)
    
    return covariance / market_variance if market_variance > 0 else 1.0


async def calculate_jensen_alpha(portfolio_returns: List[float],
                               market_returns: List[float],
                               risk_free_rate: float = 0.02) -> float:
    """Calculate Jensen's alpha"""
    if len(portfolio_returns) != len(market_returns) or len(portfolio_returns) < 2:
        return 0.0
    
    beta = await calculate_portfolio_beta(portfolio_returns, market_returns)
    
    portfolio_return = statistics.mean(portfolio_returns)
    market_return = statistics.mean(market_returns)
    
    expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
    alpha = portfolio_return - expected_return
    
    return alpha


async def calculate_treynor_ratio(portfolio_returns: List[float],
                                market_returns: List[float],
                                risk_free_rate: float = 0.02) -> float:
    """Calculate Treynor ratio"""
    if len(portfolio_returns) != len(market_returns) or len(portfolio_returns) < 2:
        return 0.0
    
    beta = await calculate_portfolio_beta(portfolio_returns, market_returns)
    portfolio_return = statistics.mean(portfolio_returns)
    
    return (portfolio_return - risk_free_rate) / beta if beta > 0 else 0.0