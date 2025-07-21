"""
Real-time Risk Calculator and Dynamic Pricing Engine

This module implements real-time risk calculation and dynamic pricing
for parametric insurance products.
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import time

from .models import RiskLevel, RiskPrediction, ModelEnsemble
from ..data.weather import WeatherDataCollector
from ..data.flight import FlightDataCollector
from ..data.crypto import CryptoDataCollector

logger = logging.getLogger(__name__)


class PricingModel(Enum):
    """Dynamic pricing models"""
    STATIC = "static"
    DEMAND_BASED = "demand_based"
    RISK_BASED = "risk_based"
    MARKET_BASED = "market_based"
    ML_BASED = "ml_based"


@dataclass
class RiskFactors:
    """Risk factors for calculation"""
    base_risk: float
    historical_risk: float
    market_risk: float
    volatility_risk: float
    correlation_risk: float
    liquidity_risk: float
    timestamp: datetime


@dataclass
class PricingParameters:
    """Pricing parameters"""
    base_premium_rate: float
    risk_multiplier: float
    demand_multiplier: float
    market_multiplier: float
    minimum_premium: float
    maximum_premium: float
    currency: str = "USD"


@dataclass
class RiskCalculationResult:
    """Risk calculation result"""
    risk_score: float
    risk_level: RiskLevel
    risk_factors: RiskFactors
    premium_rate: float
    suggested_price: float
    confidence: float
    calculation_time: float
    timestamp: datetime


class RealTimeRiskCalculator:
    """Real-time risk calculator for parametric insurance"""
    
    def __init__(self, model_ensemble: Optional[ModelEnsemble] = None):
        self.model_ensemble = model_ensemble
        self.data_collectors = {
            'weather': WeatherDataCollector(),
            'flight': FlightDataCollector(),
            'crypto': CryptoDataCollector()
        }
        self.calculation_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def calculate_risk(self, 
                           insurance_type: str,
                           parameters: Dict[str, Any],
                           real_time_data: Optional[Dict[str, Any]] = None) -> RiskCalculationResult:
        """Calculate real-time risk for insurance product"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(insurance_type, parameters)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Using cached risk calculation for {insurance_type}")
                return cached_result
            
            # Collect real-time data if not provided
            if real_time_data is None:
                real_time_data = await self._collect_real_time_data(insurance_type, parameters)
            
            # Calculate risk factors
            risk_factors = await self._calculate_risk_factors(
                insurance_type, parameters, real_time_data
            )
            
            # Calculate overall risk score
            risk_score = await self._calculate_risk_score(risk_factors, parameters)
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Calculate premium rate
            premium_rate = await self._calculate_premium_rate(
                risk_score, risk_level, parameters
            )
            
            # Calculate suggested price
            coverage_amount = parameters.get('coverage_amount', 1000.0)
            suggested_price = coverage_amount * premium_rate
            
            # Use ML model if available
            confidence = 0.8  # Base confidence
            if self.model_ensemble:
                try:
                    features = self._extract_features(risk_factors, parameters, real_time_data)
                    ml_prediction = await self.model_ensemble.predict_ensemble(features)
                    
                    # Adjust risk score based on ML prediction
                    ml_risk_score = self._risk_level_to_score(ml_prediction.risk_level)
                    risk_score = (risk_score + ml_risk_score) / 2
                    risk_level = self._determine_risk_level(risk_score)
                    confidence = ml_prediction.confidence
                    
                except Exception as e:
                    logger.warning(f"ML prediction failed: {e}")
            
            calculation_time = time.time() - start_time
            
            result = RiskCalculationResult(
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                premium_rate=premium_rate,
                suggested_price=suggested_price,
                confidence=confidence,
                calculation_time=calculation_time,
                timestamp=datetime.now()
            )
            
            # Cache result
            self._cache_result(cache_key, result)
            
            logger.info(f"Risk calculation completed for {insurance_type}: "
                       f"score={risk_score:.3f}, level={risk_level.value}, "
                       f"premium={premium_rate:.4f}, time={calculation_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Risk calculation failed for {insurance_type}: {e}")
            
            # Return fallback calculation
            return RiskCalculationResult(
                risk_score=0.5,
                risk_level=RiskLevel.MEDIUM,
                risk_factors=RiskFactors(
                    base_risk=0.5,
                    historical_risk=0.5,
                    market_risk=0.5,
                    volatility_risk=0.5,
                    correlation_risk=0.5,
                    liquidity_risk=0.5,
                    timestamp=datetime.now()
                ),
                premium_rate=0.05,
                suggested_price=parameters.get('coverage_amount', 1000.0) * 0.05,
                confidence=0.0,
                calculation_time=time.time() - start_time,
                timestamp=datetime.now()
            )
    
    async def _collect_real_time_data(self, insurance_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Collect real-time data for risk calculation"""
        data = {}
        
        try:
            if insurance_type == "weather_insurance":
                location = parameters.get('location', 'Tokyo')
                weather_data = await self.data_collectors['weather'].get_current_weather(location)
                data['weather'] = weather_data
                
            elif insurance_type == "flight_insurance":
                flight_number = parameters.get('flight_number', 'AA123')
                flight_data = await self.data_collectors['flight'].get_flight_status(flight_number)
                data['flight'] = flight_data
                
            elif insurance_type == "crypto_insurance":
                symbol = parameters.get('crypto_symbol', 'BTC')
                crypto_data = await self.data_collectors['crypto'].get_current_price(symbol)
                data['crypto'] = crypto_data
                
        except Exception as e:
            logger.warning(f"Failed to collect real-time data for {insurance_type}: {e}")
            
        return data
    
    async def _calculate_risk_factors(self, 
                                    insurance_type: str,
                                    parameters: Dict[str, Any],
                                    real_time_data: Dict[str, Any]) -> RiskFactors:
        """Calculate individual risk factors"""
        
        # Base risk calculation
        base_risk = await self._calculate_base_risk(insurance_type, parameters)
        
        # Historical risk calculation
        historical_risk = await self._calculate_historical_risk(insurance_type, parameters)
        
        # Market risk calculation
        market_risk = await self._calculate_market_risk(insurance_type, real_time_data)
        
        # Volatility risk calculation
        volatility_risk = await self._calculate_volatility_risk(insurance_type, real_time_data)
        
        # Correlation risk calculation
        correlation_risk = await self._calculate_correlation_risk(insurance_type, parameters)
        
        # Liquidity risk calculation
        liquidity_risk = await self._calculate_liquidity_risk(insurance_type, parameters)
        
        return RiskFactors(
            base_risk=base_risk,
            historical_risk=historical_risk,
            market_risk=market_risk,
            volatility_risk=volatility_risk,
            correlation_risk=correlation_risk,
            liquidity_risk=liquidity_risk,
            timestamp=datetime.now()
        )
    
    async def _calculate_base_risk(self, insurance_type: str, parameters: Dict[str, Any]) -> float:
        """Calculate base risk based on insurance type and parameters"""
        if insurance_type == "weather_insurance":
            event_type = parameters.get('weather_event', 'typhoon')
            location = parameters.get('location', 'Tokyo')
            
            # Risk mapping for different weather events
            weather_risk_map = {
                'typhoon': 0.3,
                'hurricane': 0.35,
                'earthquake': 0.4,
                'flood': 0.25,
                'drought': 0.2,
                'wildfire': 0.3,
                'hail': 0.15,
                'freeze': 0.2
            }
            
            base_risk = weather_risk_map.get(event_type, 0.25)
            
            # Adjust for location (simplified)
            if 'Japan' in location or 'Tokyo' in location:
                base_risk *= 1.2  # Higher risk in earthquake-prone areas
            
        elif insurance_type == "flight_insurance":
            airline = parameters.get('airline', 'AA')
            route_distance = parameters.get('route_distance', 1000)
            
            # Risk based on airline reliability (simplified)
            airline_risk_map = {
                'AA': 0.15,  # American Airlines
                'DL': 0.12,  # Delta
                'UA': 0.18,  # United
                'SW': 0.10,  # Southwest
                'B6': 0.14   # JetBlue
            }
            
            base_risk = airline_risk_map.get(airline, 0.15)
            
            # Adjust for route distance
            if route_distance > 5000:
                base_risk *= 1.3  # Long-haul flights have higher risk
            
        elif insurance_type == "crypto_insurance":
            symbol = parameters.get('crypto_symbol', 'BTC')
            insurance_type_crypto = parameters.get('insurance_type', 'price_drop')
            
            # Risk based on crypto type
            crypto_risk_map = {
                'BTC': 0.2,
                'ETH': 0.25,
                'SOL': 0.3,
                'ADA': 0.35,
                'DOT': 0.35,
                'AVAX': 0.4
            }
            
            base_risk = crypto_risk_map.get(symbol, 0.3)
            
            # Adjust for insurance type
            if insurance_type_crypto == 'volatility_spike':
                base_risk *= 1.5
            elif insurance_type_crypto == 'de_pegging':
                base_risk *= 0.8
            
        else:
            base_risk = 0.25  # Default base risk
            
        return np.clip(base_risk, 0.0, 1.0)
    
    async def _calculate_historical_risk(self, insurance_type: str, parameters: Dict[str, Any]) -> float:
        """Calculate historical risk based on past events"""
        # This would typically analyze historical data
        # For now, returning a simplified calculation
        
        if insurance_type == "weather_insurance":
            # Check historical weather patterns
            location = parameters.get('location', 'Tokyo')
            event_type = parameters.get('weather_event', 'typhoon')
            
            # Simplified historical risk (would be based on actual historical data)
            historical_frequency = {
                'typhoon': 0.3,
                'hurricane': 0.25,
                'earthquake': 0.4,
                'flood': 0.2,
                'drought': 0.15
            }
            
            return historical_frequency.get(event_type, 0.2)
            
        elif insurance_type == "flight_insurance":
            # Historical flight delay patterns
            airline = parameters.get('airline', 'AA')
            
            # Simplified historical delay rates
            delay_rates = {
                'AA': 0.18,
                'DL': 0.15,
                'UA': 0.22,
                'SW': 0.12,
                'B6': 0.16
            }
            
            return delay_rates.get(airline, 0.18)
            
        elif insurance_type == "crypto_insurance":
            # Historical crypto volatility
            symbol = parameters.get('crypto_symbol', 'BTC')
            
            # Simplified historical volatility
            volatility_rates = {
                'BTC': 0.25,
                'ETH': 0.35,
                'SOL': 0.45,
                'ADA': 0.4,
                'DOT': 0.4
            }
            
            return volatility_rates.get(symbol, 0.35)
            
        return 0.2  # Default historical risk
    
    async def _calculate_market_risk(self, insurance_type: str, real_time_data: Dict[str, Any]) -> float:
        """Calculate market risk based on current market conditions"""
        
        if insurance_type == "crypto_insurance" and 'crypto' in real_time_data:
            crypto_data = real_time_data['crypto']
            
            # Calculate market risk based on price changes
            price_change_24h = crypto_data.get('price_change_24h', 0.0)
            market_cap = crypto_data.get('market_cap', 0)
            volume_24h = crypto_data.get('volume_24h', 0)
            
            # Higher volatility = higher risk
            volatility_risk = abs(price_change_24h) / 100.0
            
            # Lower market cap = higher risk
            market_cap_risk = max(0.0, 1.0 - (market_cap / 1e12))  # Normalize to 1T
            
            # Lower volume = higher risk
            volume_risk = max(0.0, 1.0 - (volume_24h / 1e10))  # Normalize to 10B
            
            market_risk = (volatility_risk + market_cap_risk + volume_risk) / 3.0
            
        elif insurance_type == "weather_insurance" and 'weather' in real_time_data:
            weather_data = real_time_data['weather']
            
            # Calculate risk based on current weather conditions
            temperature = weather_data.get('temperature', 20.0)
            humidity = weather_data.get('humidity', 50.0)
            wind_speed = weather_data.get('wind_speed', 10.0)
            pressure = weather_data.get('pressure', 1013.25)
            
            # Extreme conditions = higher risk
            temp_risk = max(0.0, (abs(temperature - 20.0) - 10.0) / 30.0)
            humidity_risk = max(0.0, (abs(humidity - 50.0) - 30.0) / 40.0)
            wind_risk = max(0.0, (wind_speed - 20.0) / 80.0)
            pressure_risk = max(0.0, (abs(pressure - 1013.25) - 20.0) / 50.0)
            
            market_risk = (temp_risk + humidity_risk + wind_risk + pressure_risk) / 4.0
            
        else:
            market_risk = 0.2  # Default market risk
            
        return np.clip(market_risk, 0.0, 1.0)
    
    async def _calculate_volatility_risk(self, insurance_type: str, real_time_data: Dict[str, Any]) -> float:
        """Calculate volatility risk"""
        
        if insurance_type == "crypto_insurance" and 'crypto' in real_time_data:
            crypto_data = real_time_data['crypto']
            
            # Calculate volatility based on price changes
            price_change_1h = crypto_data.get('price_change_1h', 0.0)
            price_change_24h = crypto_data.get('price_change_24h', 0.0)
            price_change_7d = crypto_data.get('price_change_7d', 0.0)
            
            # Calculate volatility as standard deviation of returns
            returns = [price_change_1h, price_change_24h, price_change_7d]
            volatility = np.std(returns) / 100.0
            
        elif insurance_type == "flight_insurance" and 'flight' in real_time_data:
            flight_data = real_time_data['flight']
            
            # Calculate volatility based on schedule changes
            scheduled_departure = flight_data.get('scheduled_departure')
            actual_departure = flight_data.get('actual_departure')
            
            if scheduled_departure and actual_departure:
                # Calculate delay variance (simplified)
                delay_minutes = (actual_departure - scheduled_departure).total_seconds() / 60
                volatility = min(abs(delay_minutes) / 300.0, 1.0)  # Normalize to 5 hours
            else:
                volatility = 0.2
                
        else:
            volatility = 0.2  # Default volatility
            
        return np.clip(volatility, 0.0, 1.0)
    
    async def _calculate_correlation_risk(self, insurance_type: str, parameters: Dict[str, Any]) -> float:
        """Calculate correlation risk with other assets/events"""
        
        # This would typically analyze correlations with other risks
        # For now, returning a simplified calculation
        
        if insurance_type == "crypto_insurance":
            symbol = parameters.get('crypto_symbol', 'BTC')
            
            # Bitcoin correlation risk (simplified)
            btc_correlation = {
                'BTC': 0.0,   # No self-correlation
                'ETH': 0.3,   # High correlation with BTC
                'SOL': 0.25,  # Medium correlation
                'ADA': 0.2,   # Lower correlation
                'DOT': 0.2
            }
            
            return btc_correlation.get(symbol, 0.25)
            
        elif insurance_type == "weather_insurance":
            # Weather events correlation
            event_type = parameters.get('weather_event', 'typhoon')
            
            # Correlation with seasonal patterns
            seasonal_correlation = {
                'typhoon': 0.4,    # Seasonal pattern
                'hurricane': 0.4,  # Seasonal pattern
                'earthquake': 0.1, # Not seasonal
                'flood': 0.3,      # Somewhat seasonal
                'drought': 0.5     # Highly seasonal
            }
            
            return seasonal_correlation.get(event_type, 0.3)
            
        return 0.2  # Default correlation risk
    
    async def _calculate_liquidity_risk(self, insurance_type: str, parameters: Dict[str, Any]) -> float:
        """Calculate liquidity risk"""
        
        coverage_amount = parameters.get('coverage_amount', 1000.0)
        
        # Higher coverage amounts have higher liquidity risk
        if coverage_amount > 100000:
            liquidity_risk = 0.4
        elif coverage_amount > 50000:
            liquidity_risk = 0.3
        elif coverage_amount > 10000:
            liquidity_risk = 0.2
        else:
            liquidity_risk = 0.1
            
        return liquidity_risk
    
    async def _calculate_risk_score(self, risk_factors: RiskFactors, parameters: Dict[str, Any]) -> float:
        """Calculate overall risk score from individual factors"""
        
        # Weighted combination of risk factors
        weights = {
            'base_risk': 0.25,
            'historical_risk': 0.20,
            'market_risk': 0.20,
            'volatility_risk': 0.15,
            'correlation_risk': 0.10,
            'liquidity_risk': 0.10
        }
        
        risk_score = (
            risk_factors.base_risk * weights['base_risk'] +
            risk_factors.historical_risk * weights['historical_risk'] +
            risk_factors.market_risk * weights['market_risk'] +
            risk_factors.volatility_risk * weights['volatility_risk'] +
            risk_factors.correlation_risk * weights['correlation_risk'] +
            risk_factors.liquidity_risk * weights['liquidity_risk']
        )
        
        return np.clip(risk_score, 0.0, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from risk score"""
        if risk_score < 0.25:
            return RiskLevel.LOW
        elif risk_score < 0.5:
            return RiskLevel.MEDIUM
        elif risk_score < 0.75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    async def _calculate_premium_rate(self, 
                                    risk_score: float,
                                    risk_level: RiskLevel,
                                    parameters: Dict[str, Any]) -> float:
        """Calculate premium rate based on risk"""
        
        # Base premium rates by risk level
        base_rates = {
            RiskLevel.LOW: 0.02,
            RiskLevel.MEDIUM: 0.05,
            RiskLevel.HIGH: 0.10,
            RiskLevel.CRITICAL: 0.20
        }
        
        base_rate = base_rates[risk_level]
        
        # Adjust based on exact risk score
        risk_adjustment = risk_score * 0.15  # Max 15% adjustment
        
        # Apply duration multiplier
        duration_days = parameters.get('duration_days', 30)
        duration_multiplier = 1.0 + (duration_days - 30) / 365.0
        
        # Apply coverage multiplier
        coverage_amount = parameters.get('coverage_amount', 1000.0)
        coverage_multiplier = 1.0 + max(0.0, (coverage_amount - 10000) / 100000)
        
        premium_rate = base_rate * (1 + risk_adjustment) * duration_multiplier * coverage_multiplier
        
        # Apply minimum and maximum limits
        min_rate = parameters.get('min_premium_rate', 0.01)
        max_rate = parameters.get('max_premium_rate', 0.50)
        
        return np.clip(premium_rate, min_rate, max_rate)
    
    def _extract_features(self, 
                         risk_factors: RiskFactors,
                         parameters: Dict[str, Any],
                         real_time_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract features for ML model"""
        features = {
            'base_risk': risk_factors.base_risk,
            'historical_risk': risk_factors.historical_risk,
            'market_risk': risk_factors.market_risk,
            'volatility_risk': risk_factors.volatility_risk,
            'correlation_risk': risk_factors.correlation_risk,
            'liquidity_risk': risk_factors.liquidity_risk,
            'coverage_amount': parameters.get('coverage_amount', 1000.0),
            'duration_days': parameters.get('duration_days', 30),
            'trigger_threshold': parameters.get('trigger_threshold', 0.1)
        }
        
        return features
    
    def _risk_level_to_score(self, risk_level: RiskLevel) -> float:
        """Convert risk level to numerical score"""
        score_map = {
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.75,
            RiskLevel.CRITICAL: 0.9
        }
        return score_map.get(risk_level, 0.5)
    
    def _generate_cache_key(self, insurance_type: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for risk calculation"""
        import hashlib
        
        # Create a normalized parameter string
        param_str = json.dumps(parameters, sort_keys=True)
        cache_key = f"{insurance_type}:{hashlib.md5(param_str.encode()).hexdigest()}"
        
        return cache_key
    
    def _get_cached_result(self, cache_key: str) -> Optional[RiskCalculationResult]:
        """Get cached result if still valid"""
        if cache_key in self.calculation_cache:
            cached_result, timestamp = self.calculation_cache[cache_key]
            
            # Check if cache is still valid
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return cached_result
            else:
                # Remove expired cache
                del self.calculation_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: RiskCalculationResult):
        """Cache calculation result"""
        self.calculation_cache[cache_key] = (result, datetime.now())
        
        # Clean up old cache entries
        current_time = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.calculation_cache.items()
            if (current_time - timestamp).total_seconds() > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.calculation_cache[key]


class DynamicPricingEngine:
    """Dynamic pricing engine for parametric insurance"""
    
    def __init__(self, risk_calculator: RealTimeRiskCalculator):
        self.risk_calculator = risk_calculator
        self.pricing_models = {}
        self.market_data = {}
        self.demand_data = {}
        
    async def calculate_dynamic_price(self,
                                    insurance_type: str,
                                    parameters: Dict[str, Any],
                                    pricing_model: PricingModel = PricingModel.RISK_BASED) -> Dict[str, Any]:
        """Calculate dynamic price based on selected pricing model"""
        
        try:
            # Get base risk calculation
            risk_result = await self.risk_calculator.calculate_risk(insurance_type, parameters)
            
            # Apply pricing model
            if pricing_model == PricingModel.STATIC:
                final_price = await self._static_pricing(risk_result, parameters)
            elif pricing_model == PricingModel.DEMAND_BASED:
                final_price = await self._demand_based_pricing(risk_result, parameters)
            elif pricing_model == PricingModel.RISK_BASED:
                final_price = await self._risk_based_pricing(risk_result, parameters)
            elif pricing_model == PricingModel.MARKET_BASED:
                final_price = await self._market_based_pricing(risk_result, parameters)
            elif pricing_model == PricingModel.ML_BASED:
                final_price = await self._ml_based_pricing(risk_result, parameters)
            else:
                final_price = risk_result.suggested_price
            
            return {
                'final_price': final_price,
                'base_price': risk_result.suggested_price,
                'risk_score': risk_result.risk_score,
                'risk_level': risk_result.risk_level.value,
                'premium_rate': risk_result.premium_rate,
                'pricing_model': pricing_model.value,
                'confidence': risk_result.confidence,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Dynamic pricing failed: {e}")
            
            # Return fallback pricing
            coverage_amount = parameters.get('coverage_amount', 1000.0)
            return {
                'final_price': coverage_amount * 0.05,
                'base_price': coverage_amount * 0.05,
                'risk_score': 0.5,
                'risk_level': 'medium',
                'premium_rate': 0.05,
                'pricing_model': pricing_model.value,
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def _static_pricing(self, risk_result: RiskCalculationResult, parameters: Dict[str, Any]) -> float:
        """Static pricing based on predefined rates"""
        return risk_result.suggested_price
    
    async def _demand_based_pricing(self, risk_result: RiskCalculationResult, parameters: Dict[str, Any]) -> float:
        """Demand-based pricing"""
        base_price = risk_result.suggested_price
        
        # Get demand data (simplified)
        demand_multiplier = await self._get_demand_multiplier(parameters)
        
        return base_price * demand_multiplier
    
    async def _risk_based_pricing(self, risk_result: RiskCalculationResult, parameters: Dict[str, Any]) -> float:
        """Risk-based pricing with additional risk adjustments"""
        base_price = risk_result.suggested_price
        
        # Additional risk adjustments
        risk_adjustment = 1.0 + (risk_result.risk_score - 0.5) * 0.3
        
        return base_price * risk_adjustment
    
    async def _market_based_pricing(self, risk_result: RiskCalculationResult, parameters: Dict[str, Any]) -> float:
        """Market-based pricing considering competitor prices"""
        base_price = risk_result.suggested_price
        
        # Get market data (simplified)
        market_multiplier = await self._get_market_multiplier(parameters)
        
        return base_price * market_multiplier
    
    async def _ml_based_pricing(self, risk_result: RiskCalculationResult, parameters: Dict[str, Any]) -> float:
        """ML-based pricing using trained models"""
        # This would use a separate ML model for pricing
        # For now, use risk-based pricing with ML confidence adjustment
        
        base_price = risk_result.suggested_price
        confidence_adjustment = 1.0 + (1.0 - risk_result.confidence) * 0.2
        
        return base_price * confidence_adjustment
    
    async def _get_demand_multiplier(self, parameters: Dict[str, Any]) -> float:
        """Get demand multiplier based on current demand"""
        # This would analyze current demand patterns
        # For now, return a simplified multiplier
        
        coverage_amount = parameters.get('coverage_amount', 1000.0)
        
        # Higher demand for smaller coverage amounts
        if coverage_amount < 1000:
            return 1.2
        elif coverage_amount < 5000:
            return 1.1
        elif coverage_amount < 10000:
            return 1.0
        else:
            return 0.95
    
    async def _get_market_multiplier(self, parameters: Dict[str, Any]) -> float:
        """Get market multiplier based on competitor analysis"""
        # This would analyze competitor prices
        # For now, return a simplified multiplier
        
        insurance_type = parameters.get('insurance_type', 'weather_insurance')
        
        # Market multipliers by insurance type
        market_multipliers = {
            'weather_insurance': 1.05,
            'flight_insurance': 0.95,
            'crypto_insurance': 1.15
        }
        
        return market_multipliers.get(insurance_type, 1.0)
    
    async def update_market_data(self, market_data: Dict[str, Any]):
        """Update market data for pricing calculations"""
        self.market_data.update(market_data)
        logger.info("Market data updated for dynamic pricing")
    
    async def update_demand_data(self, demand_data: Dict[str, Any]):
        """Update demand data for pricing calculations"""
        self.demand_data.update(demand_data)
        logger.info("Demand data updated for dynamic pricing")
    
    async def get_pricing_analytics(self) -> Dict[str, Any]:
        """Get pricing analytics and statistics"""
        return {
            'market_data': self.market_data,
            'demand_data': self.demand_data,
            'cache_size': len(self.risk_calculator.calculation_cache),
            'available_models': [model.value for model in PricingModel],
            'last_updated': datetime.now().isoformat()
        }


# Utility functions
async def create_risk_calculator(model_ensemble: Optional[ModelEnsemble] = None) -> RealTimeRiskCalculator:
    """Create a risk calculator instance"""
    return RealTimeRiskCalculator(model_ensemble)


async def create_pricing_engine(risk_calculator: RealTimeRiskCalculator) -> DynamicPricingEngine:
    """Create a pricing engine instance"""
    return DynamicPricingEngine(risk_calculator)


async def batch_risk_calculation(risk_calculator: RealTimeRiskCalculator,
                               requests: List[Dict[str, Any]]) -> List[RiskCalculationResult]:
    """Perform batch risk calculations"""
    results = []
    
    # Process requests concurrently
    tasks = []
    for request in requests:
        task = risk_calculator.calculate_risk(
            request['insurance_type'],
            request['parameters'],
            request.get('real_time_data')
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Batch calculation failed for request {i}: {result}")
            # Create fallback result
            processed_results.append(RiskCalculationResult(
                risk_score=0.5,
                risk_level=RiskLevel.MEDIUM,
                risk_factors=RiskFactors(
                    base_risk=0.5,
                    historical_risk=0.5,
                    market_risk=0.5,
                    volatility_risk=0.5,
                    correlation_risk=0.5,
                    liquidity_risk=0.5,
                    timestamp=datetime.now()
                ),
                premium_rate=0.05,
                suggested_price=requests[i]['parameters'].get('coverage_amount', 1000.0) * 0.05,
                confidence=0.0,
                calculation_time=0.0,
                timestamp=datetime.now()
            ))
        else:
            processed_results.append(result)
    
    return processed_results