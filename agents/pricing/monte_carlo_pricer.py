"""
Monte Carlo Pricing Engine (STEP 3)

시나리오 데이터를 기반으로 Expected Loss, Risk Load, 보험료를 계산하는 모듈입니다.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats

from .models.base import PricingResult, RiskLevel


class MonteCarloPricer:
    """경량 Monte Carlo 가격 계산기"""
    
    def __init__(self):
        pass
    
    def calculate_pricing(
        self,
        scenarios: pd.DataFrame,
        peril: str,
        market_risk_premium: float = 0.15,
        enable_tail_padding: bool = True,
        confidence_level: float = 0.99
    ) -> PricingResult:
        """
        시나리오 데이터로부터 완전한 가격책정 계산
        
        Args:
            scenarios: 시나리오 데이터프레임
            peril: 위험 타입
            market_risk_premium: 시장 리스크 프리미엄 (기본 15%)
            enable_tail_padding: Tail 패딩 적용 여부
            confidence_level: VaR/TVaR 신뢰수준
            
        Returns:
            PricingResult 객체
        """
        
        # 1단계: 기본 통계량 계산
        expected_loss = self.calculate_expected_loss(scenarios)
        coefficient_of_variation = self.calculate_coefficient_of_variation(scenarios)
        
        # 2단계: Risk Load 계산
        risk_load = self.calculate_risk_load(
            coefficient_of_variation, market_risk_premium, enable_tail_padding
        )
        
        # 3단계: 보험료 계산
        net_premium = expected_loss
        gross_premium = self.calculate_gross_premium(expected_loss, risk_load)
        
        # 4단계: 리스크 지표 계산
        var_99, tvar_99 = self.calculate_var_tvar(scenarios, confidence_level)
        
        # 5단계: 리스크 레벨 분류
        risk_level = self.classify_risk_level(coefficient_of_variation, expected_loss, var_99)
        
        # 6단계: 추천사항 생성
        recommendation = self.generate_recommendation(risk_level, coefficient_of_variation, expected_loss)
        
        return PricingResult(
            peril=peril,
            expected_loss=expected_loss,
            coefficient_of_variation=coefficient_of_variation,
            risk_load=risk_load,
            net_premium=net_premium,
            gross_premium=gross_premium,
            var_99=var_99,
            tvar_99=tvar_99,
            risk_level=risk_level,
            recommendation=recommendation,
            simulation_years=len(scenarios),
            timestamp=datetime.now().isoformat()
        )
    
    def calculate_expected_loss(self, scenarios: pd.DataFrame) -> float:
        """
        연간 기댓값 손실 (EL) 계산
        
        Args:
            scenarios: 시나리오 데이터프레임
            
        Returns:
            연간 기댓값 손실 (USD)
        """
        annual_losses = scenarios["annual_loss"]
        return float(annual_losses.mean())
    
    def calculate_coefficient_of_variation(self, scenarios: pd.DataFrame) -> float:
        """
        변동계수 (CoV) 계산
        
        Args:
            scenarios: 시나리오 데이터프레임
            
        Returns:
            변동계수 (표준편차 / 평균)
        """
        annual_losses = scenarios["annual_loss"]
        mean_loss = annual_losses.mean()
        std_loss = annual_losses.std()
        
        if mean_loss == 0:
            return 0.0
        
        return float(std_loss / mean_loss)
    
    def calculate_risk_load(
        self, 
        cov: float, 
        market_premium: float = 0.15,
        enable_tail_padding: bool = True
    ) -> float:
        """
        Risk Load 계산 (modify_plan.md 공식: 0.15 + 0.5 × CoV)
        
        Args:
            cov: 변동계수
            market_premium: 시장 리스크 프리미엄
            enable_tail_padding: Tail 패딩 적용 여부
            
        Returns:
            Risk Load (비율)
        """
        # 기본 공식: 시장 프리미엄 + 변동성 가산
        base_risk_load = market_premium + (0.5 * cov)
        
        # Tail Padding 적용 (최소 20% 보장)
        if enable_tail_padding:
            min_risk_load = 0.20
            base_risk_load = max(base_risk_load, min_risk_load)
        
        return float(base_risk_load)
    
    def calculate_gross_premium(self, expected_loss: float, risk_load: float) -> float:
        """
        총 보험료 계산
        
        Args:
            expected_loss: 기댓값 손실
            risk_load: Risk Load
            
        Returns:
            총 보험료 (USD)
        """
        return expected_loss * (1 + risk_load)
    
    def calculate_var_tvar(
        self, 
        scenarios: pd.DataFrame, 
        confidence_level: float = 0.99
    ) -> Tuple[float, float]:
        """
        VaR (Value at Risk) 및 TVaR (Tail Value at Risk) 계산
        
        Args:
            scenarios: 시나리오 데이터프레임
            confidence_level: 신뢰수준 (기본 99%)
            
        Returns:
            Tuple of (VaR, TVaR)
        """
        annual_losses = scenarios["annual_loss"].values
        annual_losses_sorted = np.sort(annual_losses)
        
        # VaR 계산 (99%ile)
        var_index = int(np.ceil(confidence_level * len(annual_losses_sorted))) - 1
        var_99 = float(annual_losses_sorted[var_index])
        
        # TVaR 계산 (VaR 초과 손실의 평균)
        tail_losses = annual_losses_sorted[var_index:]
        tvar_99 = float(tail_losses.mean()) if len(tail_losses) > 0 else var_99
        
        return var_99, tvar_99
    
    def classify_risk_level(
        self, 
        cov: float, 
        expected_loss: float, 
        var_99: float
    ) -> RiskLevel:
        """
        리스크 레벨 분류
        
        Args:
            cov: 변동계수
            expected_loss: 기댓값 손실
            var_99: VaR 99%
            
        Returns:
            RiskLevel 열거형
        """
        # PML (Probable Maximum Loss) 비율 계산
        pml_ratio = var_99 / expected_loss if expected_loss > 0 else 0
        
        # 다중 기준 분류
        if cov < 0.3 and pml_ratio < 5:
            return RiskLevel.LOW
        elif cov < 0.6 and pml_ratio < 10:
            return RiskLevel.MEDIUM
        elif cov < 1.0 and pml_ratio < 20:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def generate_recommendation(
        self, 
        risk_level: RiskLevel, 
        cov: float, 
        expected_loss: float
    ) -> str:
        """
        리스크 레벨에 따른 추천사항 생성
        
        Args:
            risk_level: 분류된 리스크 레벨
            cov: 변동계수
            expected_loss: 기댓값 손실
            
        Returns:
            추천사항 텍스트
        """
        
        if risk_level == RiskLevel.LOW:
            return f"낮은 위험도 (CoV: {cov:.2f}): 보험 상품 출시 권장. 예상 손실 ${expected_loss:,.0f}는 안정적인 수준입니다."
        
        elif risk_level == RiskLevel.MEDIUM:
            return f"중간 위험도 (CoV: {cov:.2f}): 추가 분석 후 신중한 출시 권장. 포트폴리오 분산을 통한 리스크 완화 필요."
        
        elif risk_level == RiskLevel.HIGH:
            return f"높은 위험도 (CoV: {cov:.2f}): 보험료 조정 또는 한도 제한 필요. 재보험 옵션 고려 권장."
        
        else:  # VERY_HIGH
            return f"매우 높은 위험도 (CoV: {cov:.2f}): 현재 조건으로는 보험 상품 출시 비권장. 트리거 조건 재검토 필요."
    
    def calculate_additional_metrics(self, scenarios: pd.DataFrame) -> Dict[str, float]:
        """
        추가 리스크 지표 계산
        
        Args:
            scenarios: 시나리오 데이터프레임
            
        Returns:
            추가 지표 딕셔너리
        """
        annual_losses = scenarios["annual_loss"]
        
        # 기본 통계량
        metrics = {
            "skewness": float(stats.skew(annual_losses)),
            "kurtosis": float(stats.kurtosis(annual_losses)),
            "zero_loss_probability": float((annual_losses == 0).mean()),
            "extreme_loss_probability": float((annual_losses > annual_losses.quantile(0.95)).mean())
        }
        
        # 백분위수
        percentiles = [5, 10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            metrics[f"percentile_{p}"] = float(annual_losses.quantile(p/100))
        
        # 연간 이벤트 통계
        if "event_count" in scenarios.columns:
            event_counts = scenarios["event_count"]
            metrics.update({
                "avg_events_per_year": float(event_counts.mean()),
                "max_events_per_year": float(event_counts.max()),
                "zero_event_probability": float((event_counts == 0).mean())
            })
        
        return metrics
    
    def stress_test_scenarios(
        self, 
        scenarios: pd.DataFrame, 
        stress_factors: Dict[str, float]
    ) -> Dict[str, PricingResult]:
        """
        스트레스 테스트 시나리오 실행
        
        Args:
            scenarios: 기본 시나리오 데이터프레임
            stress_factors: 스트레스 요인 딕셔너리
                - "severity_shock": 심도 증가 배수 (예: 1.5)
                - "frequency_shock": 빈도 증가 배수 (예: 2.0)
                - "correlation_shock": 상관관계 증가 (예: 0.3)
                
        Returns:
            스트레스 시나리오별 PricingResult
        """
        
        stress_results = {}
        
        for scenario_name, factor in stress_factors.items():
            # 시나리오별 스트레스 적용
            stressed_scenarios = self._apply_stress_factor(scenarios, scenario_name, factor)
            
            # 스트레스된 시나리오로 가격 재계산
            stressed_result = self.calculate_pricing(
                stressed_scenarios, 
                peril=f"stressed_{scenario_name}"
            )
            
            stress_results[scenario_name] = stressed_result
        
        return stress_results
    
    def _apply_stress_factor(
        self, 
        scenarios: pd.DataFrame, 
        stress_type: str, 
        factor: float
    ) -> pd.DataFrame:
        """스트레스 요인을 시나리오에 적용"""
        
        stressed_scenarios = scenarios.copy()
        
        if stress_type == "severity_shock":
            # 모든 이벤트의 심도를 factor배 증가
            for idx, row in stressed_scenarios.iterrows():
                if row["events_with_payouts"]:
                    updated_events = []
                    for event in row["events_with_payouts"]:
                        stressed_event = event.copy()
                        stressed_event["severity"] *= factor
                        # 지급액은 별도 재계산 필요 (현재는 단순 증가)
                        if stressed_event.get("payout", 0) > 0:
                            stressed_event["payout"] *= factor
                        updated_events.append(stressed_event)
                    
                    stressed_scenarios.at[idx, "events_with_payouts"] = updated_events
                    stressed_scenarios.at[idx, "annual_loss"] = sum(
                        e.get("payout", 0) for e in updated_events
                    )
        
        elif stress_type == "frequency_shock":
            # 이벤트 발생 횟수를 factor배 증가 (확률적으로)
            for idx, row in stressed_scenarios.iterrows():
                if np.random.random() < (factor - 1.0):  # 추가 이벤트 발생 확률
                    if row["events_with_payouts"]:
                        # 기존 이벤트 중 하나를 복제
                        original_events = row["events_with_payouts"]
                        additional_event = original_events[0].copy()
                        additional_event["event_id"] = f"stress_{idx}"
                        
                        updated_events = original_events + [additional_event]
                        stressed_scenarios.at[idx, "events_with_payouts"] = updated_events
                        stressed_scenarios.at[idx, "event_count"] += 1
                        stressed_scenarios.at[idx, "annual_loss"] += additional_event.get("payout", 0)
        
        return stressed_scenarios
    
    def generate_pricing_sensitivity(
        self, 
        scenarios: pd.DataFrame, 
        peril: str,
        parameter_ranges: Dict[str, List[float]]
    ) -> pd.DataFrame:
        """
        파라미터 민감도 분석
        
        Args:
            scenarios: 시나리오 데이터프레임
            peril: 위험 타입
            parameter_ranges: 파라미터 범위 딕셔너리
                - "market_risk_premium": [0.10, 0.15, 0.20, 0.25]
                - "confidence_level": [0.95, 0.99, 0.995]
                
        Returns:
            민감도 분석 결과 데이터프레임
        """
        
        sensitivity_results = []
        
        # 기본값으로 조합 생성
        from itertools import product
        
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            # 해당 파라미터로 가격 계산
            result = self.calculate_pricing(
                scenarios,
                peril,
                market_risk_premium=params.get("market_risk_premium", 0.15),
                confidence_level=params.get("confidence_level", 0.99)
            )
            
            # 결과 저장
            sensitivity_row = {
                **params,
                "expected_loss": result.expected_loss,
                "risk_load": result.risk_load,
                "gross_premium": result.gross_premium,
                "var_99": result.var_99,
                "tvar_99": result.tvar_99,
                "risk_level": result.risk_level.value
            }
            
            sensitivity_results.append(sensitivity_row)
        
        return pd.DataFrame(sensitivity_results)


# 편의 함수들
def price_scenarios(
    scenarios: pd.DataFrame,
    peril: str,
    market_risk_premium: float = 0.15
) -> PricingResult:
    """간편한 가격책정 함수"""
    pricer = MonteCarloPricer()
    return pricer.calculate_pricing(scenarios, peril, market_risk_premium)


def calculate_el_cov(scenarios: pd.DataFrame) -> Tuple[float, float]:
    """간편한 EL/CoV 계산 함수"""
    pricer = MonteCarloPricer()
    el = pricer.calculate_expected_loss(scenarios)
    cov = pricer.calculate_coefficient_of_variation(scenarios)
    return el, cov