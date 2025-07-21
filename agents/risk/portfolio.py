"""
Portfolio Management System

This module implements portfolio management and risk diversification
for parametric insurance products.
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
from collections import defaultdict
import statistics

from .models import RiskLevel, RiskPrediction
from .calculator import RiskCalculationResult, RealTimeRiskCalculator

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Asset classes for portfolio diversification"""
    WEATHER = "weather"
    FLIGHT = "flight"
    CRYPTO = "crypto"
    AGRICULTURE = "agriculture"
    MARINE = "marine"
    CYBER = "cyber"


class PolicyStatus(Enum):
    """Policy status"""
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    CLAIMED = "claimed"
    CANCELLED = "cancelled"


@dataclass
class InsurancePolicy:
    """Insurance policy data structure"""
    policy_id: str
    contract_id: str
    policy_holder: str
    asset_class: AssetClass
    coverage_amount: float
    premium_amount: float
    premium_rate: float
    risk_score: float
    risk_level: RiskLevel
    trigger_conditions: Dict[str, Any]
    start_date: datetime
    end_date: datetime
    status: PolicyStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_coverage: float
    total_premium: float
    total_policies: int
    average_risk_score: float
    risk_distribution: Dict[str, int]
    asset_allocation: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]
    diversification_ratio: float
    sharpe_ratio: float
    var_95: float  # Value at Risk 95%
    expected_shortfall: float
    timestamp: datetime


@dataclass
class RiskExposure:
    """Risk exposure analysis"""
    asset_class: AssetClass
    total_exposure: float
    policy_count: int
    average_risk_score: float
    concentration_risk: float
    geographic_concentration: Dict[str, float]
    temporal_concentration: Dict[str, float]


@dataclass
class RebalanceRecommendation:
    """Portfolio rebalancing recommendation"""
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    rebalance_actions: List[Dict[str, Any]]
    expected_improvement: Dict[str, float]
    risk_reduction: float
    timestamp: datetime


class PortfolioManager:
    """Portfolio management system for parametric insurance"""
    
    def __init__(self, risk_calculator: RealTimeRiskCalculator):
        self.risk_calculator = risk_calculator
        self.policies: Dict[str, InsurancePolicy] = {}
        self.portfolio_history: List[PortfolioMetrics] = []
        self.rebalance_threshold = 0.05  # 5% deviation trigger
        self.max_concentration = 0.3  # 30% maximum concentration per asset class
        self.target_diversification = 0.8  # Target diversification ratio
        
    async def add_policy(self, policy: InsurancePolicy) -> bool:
        """Add a new policy to the portfolio"""
        try:
            # Validate policy
            if not await self._validate_policy(policy):
                logger.error(f"Policy validation failed: {policy.policy_id}")
                return False
            
            # Check portfolio constraints
            if not await self._check_portfolio_constraints(policy):
                logger.warning(f"Portfolio constraints violated: {policy.policy_id}")
                return False
            
            # Add policy to portfolio
            self.policies[policy.policy_id] = policy
            
            # Update portfolio metrics
            await self._update_portfolio_metrics()
            
            logger.info(f"Policy added to portfolio: {policy.policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add policy {policy.policy_id}: {e}")
            return False
    
    async def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy from the portfolio"""
        try:
            if policy_id not in self.policies:
                logger.warning(f"Policy not found: {policy_id}")
                return False
            
            # Remove policy
            del self.policies[policy_id]
            
            # Update portfolio metrics
            await self._update_portfolio_metrics()
            
            logger.info(f"Policy removed from portfolio: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove policy {policy_id}: {e}")
            return False
    
    async def update_policy(self, policy_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing policy"""
        try:
            if policy_id not in self.policies:
                logger.warning(f"Policy not found: {policy_id}")
                return False
            
            policy = self.policies[policy_id]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            policy.updated_at = datetime.now()
            
            # Update portfolio metrics
            await self._update_portfolio_metrics()
            
            logger.info(f"Policy updated: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update policy {policy_id}: {e}")
            return False
    
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics"""
        if not self.portfolio_history:
            await self._update_portfolio_metrics()
        
        return self.portfolio_history[-1] if self.portfolio_history else None
    
    async def get_risk_exposure(self, asset_class: Optional[AssetClass] = None) -> Union[RiskExposure, Dict[str, RiskExposure]]:
        """Get risk exposure analysis"""
        if asset_class:
            return await self._calculate_risk_exposure(asset_class)
        else:
            exposures = {}
            for ac in AssetClass:
                exposure = await self._calculate_risk_exposure(ac)
                if exposure.policy_count > 0:
                    exposures[ac.value] = exposure
            return exposures
    
    async def analyze_concentration_risk(self) -> Dict[str, Any]:
        """Analyze concentration risk in the portfolio"""
        try:
            # Asset class concentration
            asset_concentration = await self._calculate_asset_concentration()
            
            # Geographic concentration
            geographic_concentration = await self._calculate_geographic_concentration()
            
            # Temporal concentration
            temporal_concentration = await self._calculate_temporal_concentration()
            
            # Risk score concentration
            risk_concentration = await self._calculate_risk_concentration()
            
            return {
                'asset_concentration': asset_concentration,
                'geographic_concentration': geographic_concentration,
                'temporal_concentration': temporal_concentration,
                'risk_concentration': risk_concentration,
                'overall_concentration_score': await self._calculate_overall_concentration(),
                'concentration_warnings': await self._get_concentration_warnings(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Concentration risk analysis failed: {e}")
            return {}
    
    async def generate_rebalance_recommendations(self) -> RebalanceRecommendation:
        """Generate portfolio rebalancing recommendations"""
        try:
            # Calculate current allocation
            current_allocation = await self._calculate_current_allocation()
            
            # Calculate target allocation
            target_allocation = await self._calculate_target_allocation()
            
            # Generate rebalance actions
            rebalance_actions = await self._generate_rebalance_actions(
                current_allocation, target_allocation
            )
            
            # Calculate expected improvement
            expected_improvement = await self._calculate_expected_improvement(
                current_allocation, target_allocation
            )
            
            # Calculate risk reduction
            risk_reduction = await self._calculate_risk_reduction(
                current_allocation, target_allocation
            )
            
            return RebalanceRecommendation(
                current_allocation=current_allocation,
                target_allocation=target_allocation,
                rebalance_actions=rebalance_actions,
                expected_improvement=expected_improvement,
                risk_reduction=risk_reduction,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Rebalance recommendation generation failed: {e}")
            return RebalanceRecommendation(
                current_allocation={},
                target_allocation={},
                rebalance_actions=[],
                expected_improvement={},
                risk_reduction=0.0,
                timestamp=datetime.now()
            )
    
    async def optimize_portfolio(self, optimization_objective: str = "risk_adjusted_return") -> Dict[str, Any]:
        """Optimize portfolio allocation"""
        try:
            if optimization_objective == "risk_adjusted_return":
                return await self._optimize_risk_adjusted_return()
            elif optimization_objective == "minimum_variance":
                return await self._optimize_minimum_variance()
            elif optimization_objective == "maximum_diversification":
                return await self._optimize_maximum_diversification()
            else:
                raise ValueError(f"Unknown optimization objective: {optimization_objective}")
                
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}")
            return {}
    
    async def stress_test_portfolio(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform stress testing on the portfolio"""
        try:
            stress_results = {}
            
            for i, scenario in enumerate(scenarios):
                scenario_name = scenario.get('name', f'scenario_{i}')
                
                # Apply scenario to portfolio
                stressed_metrics = await self._apply_stress_scenario(scenario)
                
                stress_results[scenario_name] = {
                    'scenario': scenario,
                    'stressed_metrics': stressed_metrics,
                    'impact_analysis': await self._analyze_stress_impact(stressed_metrics),
                    'recovery_time': await self._estimate_recovery_time(scenario),
                    'mitigation_suggestions': await self._suggest_mitigations(scenario)
                }
            
            return {
                'stress_test_results': stress_results,
                'overall_resilience_score': await self._calculate_resilience_score(stress_results),
                'recommendations': await self._generate_stress_recommendations(stress_results),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Stress testing failed: {e}")
            return {}
    
    async def _validate_policy(self, policy: InsurancePolicy) -> bool:
        """Validate policy parameters"""
        if not policy.policy_id or not policy.contract_id:
            return False
        
        if policy.coverage_amount <= 0 or policy.premium_amount <= 0:
            return False
        
        if policy.start_date >= policy.end_date:
            return False
        
        if policy.risk_score < 0 or policy.risk_score > 1:
            return False
        
        return True
    
    async def _check_portfolio_constraints(self, policy: InsurancePolicy) -> bool:
        """Check if adding policy violates portfolio constraints"""
        # Check asset class concentration
        asset_exposure = await self._calculate_asset_exposure_after_addition(policy)
        if asset_exposure > self.max_concentration:
            return False
        
        # Check total portfolio size constraints
        total_coverage = sum(p.coverage_amount for p in self.policies.values())
        if total_coverage + policy.coverage_amount > 100_000_000:  # 100M limit
            return False
        
        # Check correlation constraints
        correlation_risk = await self._calculate_correlation_risk_after_addition(policy)
        if correlation_risk > 0.8:  # High correlation threshold
            return False
        
        return True
    
    async def _update_portfolio_metrics(self):
        """Update portfolio metrics"""
        if not self.policies:
            return
        
        active_policies = [p for p in self.policies.values() if p.status == PolicyStatus.ACTIVE]
        
        if not active_policies:
            return
        
        # Calculate basic metrics
        total_coverage = sum(p.coverage_amount for p in active_policies)
        total_premium = sum(p.premium_amount for p in active_policies)
        total_policies = len(active_policies)
        average_risk_score = sum(p.risk_score for p in active_policies) / total_policies
        
        # Risk distribution
        risk_distribution = defaultdict(int)
        for policy in active_policies:
            risk_distribution[policy.risk_level.value] += 1
        
        # Asset allocation
        asset_allocation = defaultdict(float)
        for policy in active_policies:
            asset_allocation[policy.asset_class.value] += policy.coverage_amount
        
        # Normalize asset allocation
        for asset_class in asset_allocation:
            asset_allocation[asset_class] /= total_coverage
        
        # Correlation matrix
        correlation_matrix = await self._calculate_correlation_matrix(active_policies)
        
        # Diversification ratio
        diversification_ratio = await self._calculate_diversification_ratio(active_policies)
        
        # Sharpe ratio
        sharpe_ratio = await self._calculate_sharpe_ratio(active_policies)
        
        # VaR and Expected Shortfall
        var_95 = await self._calculate_var_95(active_policies)
        expected_shortfall = await self._calculate_expected_shortfall(active_policies)
        
        metrics = PortfolioMetrics(
            total_coverage=total_coverage,
            total_premium=total_premium,
            total_policies=total_policies,
            average_risk_score=average_risk_score,
            risk_distribution=dict(risk_distribution),
            asset_allocation=dict(asset_allocation),
            correlation_matrix=correlation_matrix,
            diversification_ratio=diversification_ratio,
            sharpe_ratio=sharpe_ratio,
            var_95=var_95,
            expected_shortfall=expected_shortfall,
            timestamp=datetime.now()
        )
        
        self.portfolio_history.append(metrics)
        
        # Keep only last 100 metrics
        if len(self.portfolio_history) > 100:
            self.portfolio_history = self.portfolio_history[-100:]
    
    async def _calculate_risk_exposure(self, asset_class: AssetClass) -> RiskExposure:
        """Calculate risk exposure for an asset class"""
        asset_policies = [p for p in self.policies.values() 
                         if p.asset_class == asset_class and p.status == PolicyStatus.ACTIVE]
        
        if not asset_policies:
            return RiskExposure(
                asset_class=asset_class,
                total_exposure=0.0,
                policy_count=0,
                average_risk_score=0.0,
                concentration_risk=0.0,
                geographic_concentration={},
                temporal_concentration={}
            )
        
        total_exposure = sum(p.coverage_amount for p in asset_policies)
        policy_count = len(asset_policies)
        average_risk_score = sum(p.risk_score for p in asset_policies) / policy_count
        
        # Concentration risk (simplified)
        total_portfolio_exposure = sum(p.coverage_amount for p in self.policies.values())
        concentration_risk = total_exposure / total_portfolio_exposure if total_portfolio_exposure > 0 else 0
        
        # Geographic concentration
        geographic_concentration = defaultdict(float)
        for policy in asset_policies:
            location = policy.metadata.get('location', 'unknown')
            geographic_concentration[location] += policy.coverage_amount / total_exposure
        
        # Temporal concentration
        temporal_concentration = defaultdict(float)
        for policy in asset_policies:
            month = policy.start_date.strftime('%Y-%m')
            temporal_concentration[month] += policy.coverage_amount / total_exposure
        
        return RiskExposure(
            asset_class=asset_class,
            total_exposure=total_exposure,
            policy_count=policy_count,
            average_risk_score=average_risk_score,
            concentration_risk=concentration_risk,
            geographic_concentration=dict(geographic_concentration),
            temporal_concentration=dict(temporal_concentration)
        )
    
    async def _calculate_asset_concentration(self) -> Dict[str, float]:
        """Calculate asset class concentration"""
        asset_exposure = defaultdict(float)
        total_exposure = 0.0
        
        for policy in self.policies.values():
            if policy.status == PolicyStatus.ACTIVE:
                asset_exposure[policy.asset_class.value] += policy.coverage_amount
                total_exposure += policy.coverage_amount
        
        # Normalize to percentages
        if total_exposure > 0:
            for asset_class in asset_exposure:
                asset_exposure[asset_class] /= total_exposure
        
        return dict(asset_exposure)
    
    async def _calculate_geographic_concentration(self) -> Dict[str, float]:
        """Calculate geographic concentration"""
        geographic_exposure = defaultdict(float)
        total_exposure = 0.0
        
        for policy in self.policies.values():
            if policy.status == PolicyStatus.ACTIVE:
                location = policy.metadata.get('location', 'unknown')
                geographic_exposure[location] += policy.coverage_amount
                total_exposure += policy.coverage_amount
        
        # Normalize to percentages
        if total_exposure > 0:
            for location in geographic_exposure:
                geographic_exposure[location] /= total_exposure
        
        return dict(geographic_exposure)
    
    async def _calculate_temporal_concentration(self) -> Dict[str, float]:
        """Calculate temporal concentration"""
        temporal_exposure = defaultdict(float)
        total_exposure = 0.0
        
        for policy in self.policies.values():
            if policy.status == PolicyStatus.ACTIVE:
                month = policy.start_date.strftime('%Y-%m')
                temporal_exposure[month] += policy.coverage_amount
                total_exposure += policy.coverage_amount
        
        # Normalize to percentages
        if total_exposure > 0:
            for month in temporal_exposure:
                temporal_exposure[month] /= total_exposure
        
        return dict(temporal_exposure)
    
    async def _calculate_risk_concentration(self) -> Dict[str, float]:
        """Calculate risk level concentration"""
        risk_exposure = defaultdict(float)
        total_exposure = 0.0
        
        for policy in self.policies.values():
            if policy.status == PolicyStatus.ACTIVE:
                risk_exposure[policy.risk_level.value] += policy.coverage_amount
                total_exposure += policy.coverage_amount
        
        # Normalize to percentages
        if total_exposure > 0:
            for risk_level in risk_exposure:
                risk_exposure[risk_level] /= total_exposure
        
        return dict(risk_exposure)
    
    async def _calculate_overall_concentration(self) -> float:
        """Calculate overall concentration score"""
        # Herfindahl-Hirschman Index for concentration
        asset_concentration = await self._calculate_asset_concentration()
        
        hhi = sum(share ** 2 for share in asset_concentration.values())
        
        # Normalize to 0-1 scale (1 = high concentration, 0 = low concentration)
        return hhi
    
    async def _get_concentration_warnings(self) -> List[str]:
        """Get concentration warnings"""
        warnings = []
        
        asset_concentration = await self._calculate_asset_concentration()
        
        for asset_class, concentration in asset_concentration.items():
            if concentration > self.max_concentration:
                warnings.append(f"High concentration in {asset_class}: {concentration:.2%}")
        
        return warnings
    
    async def _calculate_current_allocation(self) -> Dict[str, float]:
        """Calculate current portfolio allocation"""
        return await self._calculate_asset_concentration()
    
    async def _calculate_target_allocation(self) -> Dict[str, float]:
        """Calculate target portfolio allocation"""
        # Simple equal weight allocation as baseline
        # In practice, this would use optimization algorithms
        
        active_asset_classes = set(p.asset_class.value for p in self.policies.values() 
                                 if p.status == PolicyStatus.ACTIVE)
        
        if not active_asset_classes:
            return {}
        
        target_weight = 1.0 / len(active_asset_classes)
        
        return {asset_class: target_weight for asset_class in active_asset_classes}
    
    async def _generate_rebalance_actions(self, 
                                        current_allocation: Dict[str, float],
                                        target_allocation: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate rebalancing actions"""
        actions = []
        
        for asset_class in target_allocation:
            current_weight = current_allocation.get(asset_class, 0.0)
            target_weight = target_allocation[asset_class]
            
            difference = target_weight - current_weight
            
            if abs(difference) > self.rebalance_threshold:
                action = {
                    'asset_class': asset_class,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'difference': difference,
                    'action': 'increase' if difference > 0 else 'decrease',
                    'priority': 'high' if abs(difference) > 0.1 else 'medium'
                }
                actions.append(action)
        
        return actions
    
    async def _calculate_expected_improvement(self,
                                           current_allocation: Dict[str, float],
                                           target_allocation: Dict[str, float]) -> Dict[str, float]:
        """Calculate expected improvement from rebalancing"""
        return {
            'diversification_improvement': 0.05,  # Simplified
            'risk_reduction': 0.03,
            'expected_return_improvement': 0.02
        }
    
    async def _calculate_risk_reduction(self,
                                      current_allocation: Dict[str, float],
                                      target_allocation: Dict[str, float]) -> float:
        """Calculate expected risk reduction"""
        # Simplified risk reduction calculation
        current_concentration = sum(weight ** 2 for weight in current_allocation.values())
        target_concentration = sum(weight ** 2 for weight in target_allocation.values())
        
        return max(0.0, current_concentration - target_concentration)
    
    async def _calculate_correlation_matrix(self, policies: List[InsurancePolicy]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between asset classes"""
        # This would typically use historical data
        # For now, returning a simplified correlation matrix
        
        asset_classes = list(set(p.asset_class.value for p in policies))
        correlation_matrix = {}
        
        for asset1 in asset_classes:
            correlation_matrix[asset1] = {}
            for asset2 in asset_classes:
                if asset1 == asset2:
                    correlation_matrix[asset1][asset2] = 1.0
                elif (asset1 == 'weather' and asset2 == 'agriculture') or \
                     (asset1 == 'agriculture' and asset2 == 'weather'):
                    correlation_matrix[asset1][asset2] = 0.7  # High correlation
                elif (asset1 == 'crypto' and asset2 == 'flight') or \
                     (asset1 == 'flight' and asset2 == 'crypto'):
                    correlation_matrix[asset1][asset2] = 0.2  # Low correlation
                else:
                    correlation_matrix[asset1][asset2] = 0.3  # Medium correlation
        
        return correlation_matrix
    
    async def _calculate_diversification_ratio(self, policies: List[InsurancePolicy]) -> float:
        """Calculate diversification ratio"""
        if len(policies) <= 1:
            return 0.0
        
        # Simplified diversification ratio
        asset_classes = set(p.asset_class for p in policies)
        return len(asset_classes) / len(AssetClass)
    
    async def _calculate_sharpe_ratio(self, policies: List[InsurancePolicy]) -> float:
        """Calculate Sharpe ratio"""
        if not policies:
            return 0.0
        
        # Simplified Sharpe ratio calculation
        returns = [p.premium_amount / p.coverage_amount for p in policies]
        
        if len(returns) <= 1:
            return 0.0
        
        avg_return = statistics.mean(returns)
        return_std = statistics.stdev(returns)
        
        return avg_return / return_std if return_std > 0 else 0.0
    
    async def _calculate_var_95(self, policies: List[InsurancePolicy]) -> float:
        """Calculate Value at Risk (95% confidence)"""
        if not policies:
            return 0.0
        
        # Simplified VaR calculation
        losses = [p.coverage_amount * p.risk_score for p in policies]
        
        if len(losses) <= 1:
            return sum(losses)
        
        return np.percentile(losses, 95)
    
    async def _calculate_expected_shortfall(self, policies: List[InsurancePolicy]) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if not policies:
            return 0.0
        
        # Simplified ES calculation
        losses = [p.coverage_amount * p.risk_score for p in policies]
        
        if len(losses) <= 1:
            return sum(losses)
        
        var_95 = np.percentile(losses, 95)
        tail_losses = [loss for loss in losses if loss >= var_95]
        
        return statistics.mean(tail_losses) if tail_losses else 0.0
    
    async def _calculate_asset_exposure_after_addition(self, policy: InsurancePolicy) -> float:
        """Calculate asset exposure after adding a policy"""
        current_asset_exposure = sum(
            p.coverage_amount for p in self.policies.values()
            if p.asset_class == policy.asset_class and p.status == PolicyStatus.ACTIVE
        )
        
        total_exposure = sum(
            p.coverage_amount for p in self.policies.values()
            if p.status == PolicyStatus.ACTIVE
        )
        
        new_asset_exposure = current_asset_exposure + policy.coverage_amount
        new_total_exposure = total_exposure + policy.coverage_amount
        
        return new_asset_exposure / new_total_exposure if new_total_exposure > 0 else 0.0
    
    async def _calculate_correlation_risk_after_addition(self, policy: InsurancePolicy) -> float:
        """Calculate correlation risk after adding a policy"""
        # Simplified correlation risk calculation
        same_asset_policies = [
            p for p in self.policies.values()
            if p.asset_class == policy.asset_class and p.status == PolicyStatus.ACTIVE
        ]
        
        if not same_asset_policies:
            return 0.0
        
        # Calculate average correlation with existing policies
        correlations = []
        for existing_policy in same_asset_policies:
            # This would use actual correlation calculation
            # For now, using asset class correlation
            correlation = 0.8 if existing_policy.asset_class == policy.asset_class else 0.3
            correlations.append(correlation)
        
        return statistics.mean(correlations) if correlations else 0.0
    
    # Additional methods for stress testing and optimization would be implemented here
    async def _optimize_risk_adjusted_return(self) -> Dict[str, Any]:
        """Optimize for risk-adjusted return"""
        # This would implement portfolio optimization algorithms
        # For now, returning a simplified result
        return {
            'optimization_objective': 'risk_adjusted_return',
            'optimal_allocation': await self._calculate_target_allocation(),
            'expected_return': 0.08,
            'expected_risk': 0.12,
            'sharpe_ratio': 0.67
        }
    
    async def _optimize_minimum_variance(self) -> Dict[str, Any]:
        """Optimize for minimum variance"""
        return {
            'optimization_objective': 'minimum_variance',
            'optimal_allocation': await self._calculate_target_allocation(),
            'expected_variance': 0.05,
            'risk_reduction': 0.03
        }
    
    async def _optimize_maximum_diversification(self) -> Dict[str, Any]:
        """Optimize for maximum diversification"""
        return {
            'optimization_objective': 'maximum_diversification',
            'optimal_allocation': await self._calculate_target_allocation(),
            'diversification_ratio': 0.85,
            'concentration_reduction': 0.1
        }
    
    async def _apply_stress_scenario(self, scenario: Dict[str, Any]) -> PortfolioMetrics:
        """Apply stress scenario to portfolio"""
        # This would simulate the impact of stress scenarios
        # For now, returning modified metrics
        current_metrics = await self.get_portfolio_metrics()
        
        if not current_metrics:
            return current_metrics
        
        # Apply stress multipliers
        stress_multiplier = scenario.get('stress_multiplier', 1.5)
        
        stressed_metrics = PortfolioMetrics(
            total_coverage=current_metrics.total_coverage,
            total_premium=current_metrics.total_premium,
            total_policies=current_metrics.total_policies,
            average_risk_score=min(1.0, current_metrics.average_risk_score * stress_multiplier),
            risk_distribution=current_metrics.risk_distribution,
            asset_allocation=current_metrics.asset_allocation,
            correlation_matrix=current_metrics.correlation_matrix,
            diversification_ratio=current_metrics.diversification_ratio * 0.8,
            sharpe_ratio=current_metrics.sharpe_ratio * 0.7,
            var_95=current_metrics.var_95 * stress_multiplier,
            expected_shortfall=current_metrics.expected_shortfall * stress_multiplier,
            timestamp=datetime.now()
        )
        
        return stressed_metrics
    
    async def _analyze_stress_impact(self, stressed_metrics: PortfolioMetrics) -> Dict[str, Any]:
        """Analyze impact of stress scenario"""
        current_metrics = await self.get_portfolio_metrics()
        
        if not current_metrics:
            return {}
        
        return {
            'var_impact': (stressed_metrics.var_95 - current_metrics.var_95) / current_metrics.var_95,
            'expected_shortfall_impact': (stressed_metrics.expected_shortfall - current_metrics.expected_shortfall) / current_metrics.expected_shortfall,
            'diversification_impact': (stressed_metrics.diversification_ratio - current_metrics.diversification_ratio) / current_metrics.diversification_ratio,
            'overall_impact_score': 0.3  # Simplified
        }
    
    async def _estimate_recovery_time(self, scenario: Dict[str, Any]) -> int:
        """Estimate recovery time in days"""
        # This would use historical data and simulation
        # For now, returning a simplified estimate
        severity = scenario.get('severity', 'medium')
        
        recovery_times = {
            'low': 30,
            'medium': 90,
            'high': 180,
            'extreme': 365
        }
        
        return recovery_times.get(severity, 90)
    
    async def _suggest_mitigations(self, scenario: Dict[str, Any]) -> List[str]:
        """Suggest mitigation strategies"""
        return [
            "Increase diversification across asset classes",
            "Implement dynamic hedging strategies",
            "Reduce concentration in high-risk assets",
            "Increase reinsurance coverage",
            "Implement early warning systems"
        ]
    
    async def _calculate_resilience_score(self, stress_results: Dict[str, Any]) -> float:
        """Calculate overall portfolio resilience score"""
        # Simplified resilience score
        return 0.75  # Would be based on stress test results
    
    async def _generate_stress_recommendations(self, stress_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on stress test results"""
        return [
            "Reduce concentration in crypto assets",
            "Increase weather insurance allocation",
            "Implement correlation-based hedging",
            "Review risk limits and constraints"
        ]


class RiskDiversificationSystem:
    """System for managing risk diversification"""
    
    def __init__(self, portfolio_manager: PortfolioManager):
        self.portfolio_manager = portfolio_manager
        self.diversification_rules = []
        self.monitoring_alerts = []
        
    async def add_diversification_rule(self, rule: Dict[str, Any]):
        """Add a diversification rule"""
        self.diversification_rules.append(rule)
        logger.info(f"Diversification rule added: {rule}")
    
    async def check_diversification_rules(self) -> List[Dict[str, Any]]:
        """Check all diversification rules"""
        violations = []
        
        for rule in self.diversification_rules:
            violation = await self._check_rule(rule)
            if violation:
                violations.append(violation)
        
        return violations
    
    async def _check_rule(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check a specific diversification rule"""
        rule_type = rule.get('type')
        
        if rule_type == 'asset_concentration':
            return await self._check_asset_concentration_rule(rule)
        elif rule_type == 'correlation_limit':
            return await self._check_correlation_limit_rule(rule)
        elif rule_type == 'geographic_diversification':
            return await self._check_geographic_diversification_rule(rule)
        
        return None
    
    async def _check_asset_concentration_rule(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check asset concentration rule"""
        max_concentration = rule.get('max_concentration', 0.3)
        asset_concentration = await self.portfolio_manager._calculate_asset_concentration()
        
        for asset_class, concentration in asset_concentration.items():
            if concentration > max_concentration:
                return {
                    'rule_type': 'asset_concentration',
                    'asset_class': asset_class,
                    'current_concentration': concentration,
                    'max_allowed': max_concentration,
                    'violation_severity': 'high' if concentration > max_concentration * 1.5 else 'medium'
                }
        
        return None
    
    async def _check_correlation_limit_rule(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check correlation limit rule"""
        # Simplified correlation check
        return None
    
    async def _check_geographic_diversification_rule(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check geographic diversification rule"""
        # Simplified geographic diversification check
        return None
    
    async def generate_diversification_report(self) -> Dict[str, Any]:
        """Generate diversification report"""
        violations = await self.check_diversification_rules()
        metrics = await self.portfolio_manager.get_portfolio_metrics()
        
        return {
            'diversification_score': metrics.diversification_ratio if metrics else 0.0,
            'rule_violations': violations,
            'recommendations': await self._generate_diversification_recommendations(),
            'monitoring_alerts': self.monitoring_alerts,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _generate_diversification_recommendations(self) -> List[str]:
        """Generate diversification recommendations"""
        return [
            "Consider adding more asset classes to the portfolio",
            "Reduce correlation between existing positions",
            "Implement geographic diversification strategies",
            "Review and update diversification rules regularly"
        ]


# Utility functions
async def create_portfolio_manager(risk_calculator: RealTimeRiskCalculator) -> PortfolioManager:
    """Create a portfolio manager instance"""
    return PortfolioManager(risk_calculator)


async def create_diversification_system(portfolio_manager: PortfolioManager) -> RiskDiversificationSystem:
    """Create a risk diversification system"""
    return RiskDiversificationSystem(portfolio_manager)


async def create_sample_portfolio() -> List[InsurancePolicy]:
    """Create sample policies for testing"""
    policies = []
    
    # Weather insurance policies
    for i in range(5):
        policy = InsurancePolicy(
            policy_id=f"weather_{i}",
            contract_id=f"contract_weather_{i}",
            policy_holder=f"holder_{i}",
            asset_class=AssetClass.WEATHER,
            coverage_amount=10000.0 * (i + 1),
            premium_amount=500.0 * (i + 1),
            premium_rate=0.05,
            risk_score=0.3 + i * 0.1,
            risk_level=RiskLevel.MEDIUM,
            trigger_conditions={"weather_event": "typhoon"},
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status=PolicyStatus.ACTIVE,
            metadata={"location": "Tokyo"}
        )
        policies.append(policy)
    
    # Crypto insurance policies
    for i in range(3):
        policy = InsurancePolicy(
            policy_id=f"crypto_{i}",
            contract_id=f"contract_crypto_{i}",
            policy_holder=f"holder_{i+5}",
            asset_class=AssetClass.CRYPTO,
            coverage_amount=5000.0 * (i + 1),
            premium_amount=250.0 * (i + 1),
            premium_rate=0.05,
            risk_score=0.4 + i * 0.1,
            risk_level=RiskLevel.HIGH,
            trigger_conditions={"crypto_symbol": "BTC"},
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status=PolicyStatus.ACTIVE,
            metadata={"symbol": "BTC"}
        )
        policies.append(policy)
    
    return policies