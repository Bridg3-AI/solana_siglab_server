"""
Synthetic Scenario Generator (STEP 2)

Prior 분포를 기반으로 Monte Carlo 시뮬레이션을 통해 
1000년 가상 시나리오를 생성하는 모듈입니다.
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models.base import (
    PerilCanvas, FrequencyPrior, SeverityPrior, ScenarioData,
    DistributionType, CurveType
)
from ..core.config import get_config


class SyntheticScenarioGenerator:
    """Monte Carlo 시나리오 생성기"""
    
    def __init__(self, random_seed: Optional[int] = None):
        self.config = get_config()
        self._llm = None
        
        # 재현가능한 결과를 위한 시드 설정
        if random_seed is not None:
            np.random.seed(random_seed)
    
    @property
    def llm(self) -> ChatOpenAI:
        """지연 초기화된 LLM 인스턴스"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.config.model_name,
                temperature=0.3,
                max_tokens=1000,
                api_key=self.config.openai_api_key
            )
        return self._llm
    
    async def generate_scenarios(
        self,
        canvas: PerilCanvas,
        frequency_prior: FrequencyPrior,
        severity_prior: SeverityPrior,
        years: int = 1000,
        include_tail_scenarios: bool = True
    ) -> pd.DataFrame:
        """
        Prior 분포를 기반으로 Monte Carlo 시나리오 생성
        
        Args:
            canvas: PerilCanvas 객체
            frequency_prior: 빈도 Prior 분포
            severity_prior: 심도 Prior 분포
            years: 시뮬레이션 연수
            include_tail_scenarios: Tail Risk 시나리오 포함 여부
            
        Returns:
            시나리오 데이터프레임
        """
        
        # 1단계: 기본 Monte Carlo 시뮬레이션
        base_scenarios = self._generate_base_scenarios(
            frequency_prior, severity_prior, years
        )
        
        # 2단계: Peril Canvas 지급 공식 적용
        scenarios_with_payouts = self._apply_payout_formula(base_scenarios, canvas)
        
        # 3단계: Tail Risk 시나리오 추가 (옵션)
        if include_tail_scenarios:
            tail_scenarios = await self._generate_tail_scenarios(
                canvas.peril, canvas.region, count=max(10, years // 100)
            )
            scenarios_with_payouts = self._merge_tail_scenarios(
                scenarios_with_payouts, tail_scenarios, canvas
            )
        
        return scenarios_with_payouts
    
    def _generate_base_scenarios(
        self,
        frequency_prior: FrequencyPrior,
        severity_prior: SeverityPrior,
        years: int
    ) -> pd.DataFrame:
        """기본 Monte Carlo 시뮬레이션 실행"""
        
        scenarios = []
        
        for year in range(years):
            # 연간 이벤트 발생 횟수 생성
            event_count = self._sample_frequency(frequency_prior)
            
            # 각 이벤트의 심도 생성
            events = []
            for event_idx in range(event_count):
                severity = self._sample_severity(severity_prior)
                events.append({
                    "event_id": f"{year}_{event_idx}",
                    "severity": severity,
                    "event_index": event_idx
                })
            
            scenarios.append({
                "year": year,
                "event_count": event_count,
                "events": events
            })
        
        return pd.DataFrame(scenarios)
    
    def _sample_frequency(self, frequency_prior: FrequencyPrior) -> int:
        """빈도 분포에서 샘플링 (강화된 엣지 케이스 처리)"""
        
        # None 값 방어 처리
        if frequency_prior is None or frequency_prior.parameters is None:
            print("⚠️ [SCENARIO] FrequencyPrior 또는 parameters가 None - 기본값 사용")
            return np.random.poisson(1)
        
        dist_type = frequency_prior.distribution
        params = frequency_prior.parameters
        
        try:
            if dist_type == DistributionType.NEGATIVE_BINOMIAL:
                return self._sample_negative_binomial(params)
            elif dist_type == DistributionType.POISSON:
                return self._sample_poisson(params)
            else:
                print(f"⚠️ [SCENARIO] 알 수 없는 빈도 분포: {dist_type} - 기본값 사용")
                return np.random.poisson(1)
                
        except Exception as e:
            print(f"⚠️ [SCENARIO] 빈도 샘플링 중 오류: {e} - 기본값 사용")
            return np.random.poisson(1)
    
    def _sample_negative_binomial(self, params: dict) -> int:
        """Negative Binomial 분포 샘플링 (다양한 파라미터 형태 지원)"""
        
        # r, p 형태
        if "r" in params and "p" in params:
            r = self._safe_float_conversion(params["r"], "r", 1.0)
            p = self._safe_float_conversion(params["p"], "p", 0.5)
            
            # 파라미터 유효성 검증
            if r <= 0:
                print(f"⚠️ [SCENARIO] 유효하지 않은 r 값: {r} - 기본값 1.0 사용")
                r = 1.0
            if p <= 0 or p >= 1:
                print(f"⚠️ [SCENARIO] 유효하지 않은 p 값: {p} - 기본값 0.5 사용")
                p = 0.5
                
            return np.random.negative_binomial(r, p)
        
        # n, p 형태 (alternative parameterization)
        elif "n" in params and "p" in params:
            n = self._safe_float_conversion(params["n"], "n", 1.0)
            p = self._safe_float_conversion(params["p"], "p", 0.5)
            
            if n <= 0: n = 1.0
            if p <= 0 or p >= 1: p = 0.5
                
            return np.random.negative_binomial(n, p)
        
        # size, prob 형태
        elif "size" in params and "prob" in params:
            size = self._safe_float_conversion(params["size"], "size", 1.0)
            prob = self._safe_float_conversion(params["prob"], "prob", 0.5)
            
            if size <= 0: size = 1.0
            if prob <= 0 or prob >= 1: prob = 0.5
                
            return np.random.negative_binomial(size, prob)
        
        # mu, phi 형태 (mean, overdispersion)
        elif "mu" in params and "phi" in params:
            mu = self._safe_float_conversion(params["mu"], "mu", 1.0)
            phi = self._safe_float_conversion(params["phi"], "phi", 1.0)
            
            if mu <= 0: mu = 1.0
            if phi <= 0: phi = 1.0
            
            # mu = r * (1-p) / p, var = mu + phi * mu^2
            # Convert to r, p parameterization
            p = mu / (mu + phi * mu * mu)
            r = mu * p / (1 - p)
            
            if p <= 0 or p >= 1: p = 0.5
            if r <= 0: r = 1.0
                
            return np.random.negative_binomial(r, p)
        
        else:
            print(f"⚠️ [SCENARIO] 알 수 없는 Negative Binomial 파라미터: {params} - 기본값 사용")
            return np.random.negative_binomial(1, 0.5)
    
    def _sample_poisson(self, params: dict) -> int:
        """Poisson 분포 샘플링 (다양한 파라미터 형태 지원)"""
        
        # lambda 형태
        if "lambda" in params:
            lam = self._safe_float_conversion(params["lambda"], "lambda", 1.0)
        elif "lam" in params:
            lam = self._safe_float_conversion(params["lam"], "lam", 1.0)
        elif "rate" in params:
            lam = self._safe_float_conversion(params["rate"], "rate", 1.0)
        elif "mu" in params:
            lam = self._safe_float_conversion(params["mu"], "mu", 1.0)
        else:
            print(f"⚠️ [SCENARIO] 알 수 없는 Poisson 파라미터: {params} - 기본값 사용")
            lam = 1.0
        
        # 파라미터 유효성 검증
        if lam <= 0:
            print(f"⚠️ [SCENARIO] 유효하지 않은 lambda 값: {lam} - 기본값 1.0 사용")
            lam = 1.0
        
        return np.random.poisson(lam)
    
    def _safe_float_conversion(self, value, param_name: str, default_value: float) -> float:
        """안전한 float 변환 (None, string 등 처리)"""
        
        if value is None:
            print(f"⚠️ [SCENARIO] {param_name} 값이 None - 기본값 {default_value} 사용")
            return default_value
        
        try:
            return float(value)
        except (TypeError, ValueError):
            print(f"⚠️ [SCENARIO] {param_name} 값 변환 실패 ({value}) - 기본값 {default_value} 사용")
            return default_value
    
    def _sample_severity(self, severity_prior: SeverityPrior) -> float:
        """심도 분포에서 샘플링 (강화된 엣지 케이스 처리)"""
        
        # None 값 방어 처리
        if severity_prior is None or severity_prior.parameters is None:
            print("⚠️ [SCENARIO] SeverityPrior 또는 parameters가 None - 기본값 사용")
            return np.random.lognormal(1, 0.5)
        
        dist_type = severity_prior.distribution
        params = severity_prior.parameters
        
        try:
            if dist_type == DistributionType.LOGNORMAL:
                return self._sample_lognormal(params)
            elif dist_type == DistributionType.GAMMA:
                return self._sample_gamma(params)
            elif dist_type == DistributionType.EXPONENTIAL:
                return self._sample_exponential(params)
            elif dist_type == DistributionType.NORMAL:
                return self._sample_normal(params)
            else:
                print(f"⚠️ [SCENARIO] 알 수 없는 심도 분포: {dist_type} - 기본값 사용")
                return np.random.lognormal(1, 0.5)
                
        except Exception as e:
            print(f"⚠️ [SCENARIO] 심도 샘플링 중 오류: {e} - 기본값 사용")
            return np.random.lognormal(1, 0.5)
    
    def _sample_lognormal(self, params: dict) -> float:
        """LogNormal 분포 샘플링 (다양한 파라미터 형태 지원)"""
        
        # mu, sigma 형태 (표준)
        if "mu" in params and "sigma" in params:
            mu = self._safe_float_conversion(params["mu"], "mu", 1.0)
            sigma = self._safe_float_conversion(params["sigma"], "sigma", 0.5)
        # mean, std 형태
        elif "mean" in params and "std" in params:
            mu = self._safe_float_conversion(params["mean"], "mean", 1.0)
            sigma = self._safe_float_conversion(params["std"], "std", 0.5)
        # location, scale 형태
        elif "location" in params and "scale" in params:
            mu = self._safe_float_conversion(params["location"], "location", 1.0)
            sigma = self._safe_float_conversion(params["scale"], "scale", 0.5)
        # m, s 형태
        elif "m" in params and "s" in params:
            mu = self._safe_float_conversion(params["m"], "m", 1.0)
            sigma = self._safe_float_conversion(params["s"], "s", 0.5)
        else:
            print(f"⚠️ [SCENARIO] 알 수 없는 LogNormal 파라미터: {params} - 기본값 사용")
            mu, sigma = 1.0, 0.5
        
        # 파라미터 유효성 검증
        if sigma <= 0:
            print(f"⚠️ [SCENARIO] 유효하지 않은 sigma 값: {sigma} - 기본값 0.5 사용")
            sigma = 0.5
        
        return np.random.lognormal(mu, sigma)
    
    def _sample_gamma(self, params: dict) -> float:
        """Gamma 분포 샘플링 (다양한 파라미터 형태 지원)"""
        
        # alpha, beta 형태 (shape, rate)
        if "alpha" in params and "beta" in params:
            alpha = self._safe_float_conversion(params["alpha"], "alpha", 2.0)
            beta = self._safe_float_conversion(params["beta"], "beta", 1.0)
            
            if alpha <= 0: alpha = 2.0
            if beta <= 0: beta = 1.0
            
            return np.random.gamma(alpha, 1/beta)
        
        # shape, scale 형태
        elif "shape" in params and "scale" in params:
            shape = self._safe_float_conversion(params["shape"], "shape", 2.0)
            scale = self._safe_float_conversion(params["scale"], "scale", 1.0)
            
            if shape <= 0: shape = 2.0
            if scale <= 0: scale = 1.0
            
            return np.random.gamma(shape, scale)
        
        # shape, rate 형태
        elif "shape" in params and "rate" in params:
            shape = self._safe_float_conversion(params["shape"], "shape", 2.0)
            rate = self._safe_float_conversion(params["rate"], "rate", 1.0)
            
            if shape <= 0: shape = 2.0
            if rate <= 0: rate = 1.0
            
            return np.random.gamma(shape, 1/rate)
        
        # k, theta 형태 (alternative naming)
        elif "k" in params and "theta" in params:
            k = self._safe_float_conversion(params["k"], "k", 2.0)
            theta = self._safe_float_conversion(params["theta"], "theta", 1.0)
            
            if k <= 0: k = 2.0
            if theta <= 0: theta = 1.0
            
            return np.random.gamma(k, theta)
        
        # mu, sigma 형태 (LLM이 잘못 응답한 경우)
        elif "mu" in params and "sigma" in params:
            mu = self._safe_float_conversion(params["mu"], "mu", 2.0)
            sigma = self._safe_float_conversion(params["sigma"], "sigma", 1.0)
            
            if mu <= 0: mu = 2.0
            if sigma <= 0: sigma = 1.0
            
            # Method of moments: alpha = (mu/sigma)^2, beta = sigma^2/mu
            var = sigma ** 2
            alpha = (mu ** 2) / var
            beta = var / mu
            
            if alpha <= 0: alpha = 2.0
            if beta <= 0: beta = 1.0
            
            return np.random.gamma(alpha, beta)
        
        # mean, var 형태
        elif "mean" in params and ("var" in params or "variance" in params):
            mean = self._safe_float_conversion(params["mean"], "mean", 2.0)
            var = self._safe_float_conversion(params.get("var", params.get("variance", 1.0)), "variance", 1.0)
            
            if mean <= 0: mean = 2.0
            if var <= 0: var = 1.0
            
            # Method of moments
            alpha = (mean ** 2) / var
            beta = var / mean
            
            if alpha <= 0: alpha = 2.0
            if beta <= 0: beta = 1.0
            
            return np.random.gamma(alpha, beta)
        
        else:
            print(f"⚠️ [SCENARIO] 알 수 없는 Gamma 파라미터: {params} - 기본값 사용")
            return np.random.gamma(2.0, 1.0)
    
    def _sample_exponential(self, params: dict) -> float:
        """Exponential 분포 샘플링 (다양한 파라미터 형태 지원)"""
        
        # lambda 형태 (rate parameter)
        if "lambda" in params:
            lam = self._safe_float_conversion(params["lambda"], "lambda", 1.0)
            if lam <= 0: lam = 1.0
            return np.random.exponential(1/lam)
        
        # rate 형태
        elif "rate" in params:
            rate = self._safe_float_conversion(params["rate"], "rate", 1.0)
            if rate <= 0: rate = 1.0
            return np.random.exponential(1/rate)
        
        # scale 형태
        elif "scale" in params:
            scale = self._safe_float_conversion(params["scale"], "scale", 1.0)
            if scale <= 0: scale = 1.0
            return np.random.exponential(scale)
        
        # beta 형태 (alternative naming)
        elif "beta" in params:
            beta = self._safe_float_conversion(params["beta"], "beta", 1.0)
            if beta <= 0: beta = 1.0
            return np.random.exponential(1/beta)
        
        # mean 형태
        elif "mean" in params:
            mean = self._safe_float_conversion(params["mean"], "mean", 1.0)
            if mean <= 0: mean = 1.0
            return np.random.exponential(mean)
        
        else:
            print(f"⚠️ [SCENARIO] 알 수 없는 Exponential 파라미터: {params} - 기본값 사용")
            return np.random.exponential(1.0)
    
    def _sample_normal(self, params: dict) -> float:
        """Normal 분포 샘플링 (음수 방지, 다양한 파라미터 형태 지원)"""
        
        # mu, sigma 형태
        if "mu" in params and "sigma" in params:
            mu = self._safe_float_conversion(params["mu"], "mu", 1.0)
            sigma = self._safe_float_conversion(params["sigma"], "sigma", 1.0)
        # mean, std 형태
        elif "mean" in params and ("std" in params or "stddev" in params):
            mu = self._safe_float_conversion(params["mean"], "mean", 1.0)
            sigma = self._safe_float_conversion(params.get("std", params.get("stddev", 1.0)), "std", 1.0)
        # location, scale 형태
        elif "location" in params and "scale" in params:
            mu = self._safe_float_conversion(params["location"], "location", 1.0)
            sigma = self._safe_float_conversion(params["scale"], "scale", 1.0)
        else:
            print(f"⚠️ [SCENARIO] 알 수 없는 Normal 파라미터: {params} - 기본값 사용")
            mu, sigma = 1.0, 1.0
        
        # 파라미터 유효성 검증
        if sigma <= 0:
            print(f"⚠️ [SCENARIO] 유효하지 않은 sigma 값: {sigma} - 기본값 1.0 사용")
            sigma = 1.0
        
        # 음수 방지를 위한 Truncated Normal 근사
        sample = np.random.normal(mu, sigma)
        return max(0.001, sample)  # 매우 작은 양수로 제한
    
    def _apply_payout_formula(self, scenarios: pd.DataFrame, canvas: PerilCanvas) -> pd.DataFrame:
        """Peril Canvas의 지급 공식을 시나리오에 적용"""
        
        limit_structure = canvas.limit_structure
        trigger_condition = limit_structure.trigger_condition
        payout_curve = limit_structure.payout_curve
        
        def calculate_payout(events_list: List[Dict]) -> Tuple[List[Dict], float]:
            """이벤트 리스트에서 연간 총 지급액 계산"""
            
            updated_events = []
            annual_payout = 0.0
            
            for event in events_list:
                severity = event["severity"]
                
                # 트리거 조건 확인
                triggered = self._check_trigger_condition(severity, trigger_condition)
                
                if triggered:
                    # 지급액 계산
                    payout = self._calculate_event_payout(severity, trigger_condition, payout_curve)
                    annual_payout += payout
                    
                    event_with_payout = {**event, "payout": payout, "triggered": True}
                else:
                    event_with_payout = {**event, "payout": 0.0, "triggered": False}
                
                updated_events.append(event_with_payout)
            
            return updated_events, annual_payout
        
        # 각 연도별로 지급액 계산
        scenarios["events_with_payouts"] = None
        scenarios["annual_loss"] = 0.0
        
        for idx, row in scenarios.iterrows():
            events_with_payouts, annual_loss = calculate_payout(row["events"])
            scenarios.at[idx, "events_with_payouts"] = events_with_payouts
            scenarios.at[idx, "annual_loss"] = annual_loss
        
        return scenarios
    
    def _check_trigger_condition(self, severity: float, trigger_condition) -> bool:
        """트리거 조건 확인 (강화된 엣지 케이스 처리)"""
        
        # None 값 및 기본 유효성 검증
        if severity is None or trigger_condition is None:
            return False
        
        # Severity 값 유효성 검증
        severity = self._safe_float_conversion(severity, "severity", 0.0)
        if severity is None or not isinstance(severity, (int, float)):
            return False
        
        # Trigger condition 속성 확인
        try:
            threshold = getattr(trigger_condition, 'threshold', None)
            operator = getattr(trigger_condition, 'operator', None)
        except AttributeError:
            print("⚠️ [SCENARIO] trigger_condition 속성 접근 실패")
            return False
        
        # Threshold 값 유효성 검증
        threshold = self._safe_float_conversion(threshold, "threshold", 0.0)
        if threshold is None:
            return False
        
        # Operator 유효성 검증
        if operator is None or not isinstance(operator, str):
            print(f"⚠️ [SCENARIO] 유효하지 않은 operator: {operator} - 기본값 '>=' 사용")
            operator = ">="
        
        # 연산 수행
        try:
            if operator == ">=":
                return float(severity) >= float(threshold)
            elif operator == "<=":
                return float(severity) <= float(threshold)
            elif operator == ">":
                return float(severity) > float(threshold)
            elif operator == "<":
                return float(severity) < float(threshold)
            elif operator == "==":
                return abs(float(severity) - float(threshold)) < 0.001  # 부동소수점 비교
            elif operator == "!=":
                return abs(float(severity) - float(threshold)) >= 0.001
            else:
                print(f"⚠️ [SCENARIO] 알 수 없는 operator: {operator} - 기본값 '>=' 사용")
                return float(severity) >= float(threshold)
                
        except (TypeError, ValueError, OverflowError) as e:
            print(f"⚠️ [SCENARIO] 트리거 조건 비교 중 오류: {e}, severity={severity}, threshold={threshold}, operator={operator}")
            return False
    
    def _calculate_event_payout(self, severity: float, trigger_condition, payout_curve) -> float:
        """개별 이벤트의 지급액 계산 (강화된 엣지 케이스 처리)"""
        
        # 기본 유효성 검증
        if severity is None or trigger_condition is None or payout_curve is None:
            return 0.0
        
        # Severity 값 변환
        severity = self._safe_float_conversion(severity, "severity", 0.0)
        if severity is None:
            return 0.0
        
        # Trigger condition 속성 추출
        try:
            threshold = self._safe_float_conversion(getattr(trigger_condition, 'threshold', 0.0), "threshold", 0.0)
            operator = getattr(trigger_condition, 'operator', ">=")
        except (AttributeError, TypeError):
            print("⚠️ [SCENARIO] trigger_condition 속성 추출 실패")
            return 0.0
        
        # Payout curve 속성 추출
        try:
            curve_type = getattr(payout_curve, 'curve_type', CurveType.LINEAR)
            base_amount = self._safe_float_conversion(getattr(payout_curve, 'base_amount', 0.0), "base_amount", 0.0)
            max_payout = self._safe_float_conversion(getattr(payout_curve, 'max_payout', 1000000.0), "max_payout", 1000000.0)
            multiplier = self._safe_float_conversion(getattr(payout_curve, 'multiplier', 1.0), "multiplier", 1.0)
        except (AttributeError, TypeError) as e:
            print(f"⚠️ [SCENARIO] payout_curve 속성 추출 실패: {e}")
            return 0.0
        
        # 파라미터 유효성 검증
        if base_amount < 0:
            base_amount = 0.0
        if max_payout <= 0:
            max_payout = 1000000.0
        if multiplier < 0:
            multiplier = 1.0
        
        try:
            # 트리거 초과 정도 계산
            if operator in [">=", ">"]:
                excess = max(0.0, float(severity) - float(threshold))
            elif operator in ["<=", "<"]:
                excess = max(0.0, float(threshold) - float(severity))
            elif operator == "==":
                # 정확히 일치하는 경우만 지급
                excess = 1.0 if abs(float(severity) - float(threshold)) < 0.001 else 0.0
            else:
                excess = abs(float(severity) - float(threshold))
            
            # 지급 곡선에 따른 계산
            if curve_type == CurveType.LINEAR:
                payout = base_amount + (excess * multiplier)
            elif curve_type == CurveType.STEP:
                steps = max(0, int(excess))
                payout = base_amount + (steps * multiplier)
            elif curve_type == CurveType.EXPONENTIAL:
                # 지수 곡선: 안전한 지수 계산
                if excess > 0 and multiplier > 0:
                    try:
                        exp_factor = min(10.0, multiplier / 1000.0)  # 지수 폭발 방지
                        payout = base_amount * ((1.0 + excess) ** exp_factor)
                    except (OverflowError, ValueError):
                        payout = max_payout  # 오버플로우 시 최대값
                else:
                    payout = base_amount
            elif hasattr(CurveType, 'LOGARITHMIC') and curve_type == CurveType.LOGARITHMIC:
                # 로그 곡선: 안전한 로그 계산
                if excess > 0:
                    try:
                        payout = base_amount + multiplier * np.log(1.0 + excess)
                    except (ValueError, OverflowError):
                        payout = base_amount + multiplier * 1.0  # 로그 오류 시 기본값
                else:
                    payout = base_amount
            else:
                # 기본: Linear
                payout = base_amount + (excess * multiplier)
            
            # 최대 지급액 제한 및 음수 방지
            payout = max(0.0, min(float(payout), float(max_payout)))
            
            # 무한대 및 NaN 방지
            if not np.isfinite(payout):
                print(f"⚠️ [SCENARIO] 무한대 또는 NaN 지급액 - 기본값 사용: {payout}")
                payout = base_amount
            
            return payout
            
        except (TypeError, ValueError, OverflowError) as e:
            print(f"⚠️ [SCENARIO] 지급액 계산 중 오류: {e} - 기본값 사용")
            return base_amount
    
    async def _generate_tail_scenarios(self, peril: str, region: str, count: int = 10) -> List[Dict]:
        """LLM을 사용한 Tail Risk 시나리오 생성"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are an expert in extreme event modeling and tail risk analysis.

Generate extreme tail-risk scenarios for parametric insurance stress testing.

Response format (JSON only):
{
    "scenarios": [
        {
            "name": "Scenario name",
            "severity_multiplier": 2.5,
            "frequency_multiplier": 1.2,
            "description": "Brief description",
            "probability": 0.001
        }
    ]
}

Guidelines:
1. Focus on genuinely extreme but plausible scenarios
2. Severity multiplier: How much more severe than typical events
3. Frequency multiplier: How much more frequent than normal years
4. Probability: Annual probability of this scenario type
5. Consider climate change, systemic risks, and correlations
"""),
            ("human", """
Event type: {peril}
Region: {region}
Count needed: {count}

Generate {count} extreme tail-risk scenarios that could stress-test a parametric insurance model.

Consider:
- Historical precedents and "near-miss" events
- Climate change amplification effects
- Correlation and clustering of events
- Secondary and cascading effects
- Model uncertainty and parameter extremes
""")
        ])
        
        try:
            messages = prompt.format_messages(peril=peril, region=region, count=count)
            response = await self.llm.ainvoke(messages)
            
            result = json.loads(response.content)
            return result.get("scenarios", [])
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: 기본 tail 시나리오
            return self._get_default_tail_scenarios(peril, count)
    
    def _get_default_tail_scenarios(self, peril: str, count: int) -> List[Dict]:
        """기본 Tail Risk 시나리오"""
        
        default_scenarios = {
            "typhoon": [
                {"name": "Super Typhoon", "severity_multiplier": 3.0, "frequency_multiplier": 1.0, "probability": 0.01},
                {"name": "Multiple Typhoons", "severity_multiplier": 1.5, "frequency_multiplier": 3.0, "probability": 0.005},
                {"name": "Unprecedented Track", "severity_multiplier": 2.5, "frequency_multiplier": 1.0, "probability": 0.002}
            ],
            "flight_delay": [
                {"name": "System-wide Outage", "severity_multiplier": 5.0, "frequency_multiplier": 1.0, "probability": 0.001},
                {"name": "Weather Mega-Event", "severity_multiplier": 3.0, "frequency_multiplier": 2.0, "probability": 0.005},
                {"name": "Cyber Attack", "severity_multiplier": 4.0, "frequency_multiplier": 1.0, "probability": 0.002}
            ],
            "server_downtime": [
                {"name": "Data Center Failure", "severity_multiplier": 10.0, "frequency_multiplier": 1.0, "probability": 0.001},
                {"name": "DDoS Attack", "severity_multiplier": 3.0, "frequency_multiplier": 5.0, "probability": 0.01},
                {"name": "Hardware Cascade", "severity_multiplier": 5.0, "frequency_multiplier": 2.0, "probability": 0.005}
            ]
        }
        
        scenarios = default_scenarios.get(peril, [
            {"name": "Extreme Event", "severity_multiplier": 3.0, "frequency_multiplier": 1.0, "probability": 0.01}
        ])
        
        return scenarios[:count]
    
    def _merge_tail_scenarios(
        self, 
        base_scenarios: pd.DataFrame, 
        tail_scenarios: List[Dict], 
        canvas: PerilCanvas
    ) -> pd.DataFrame:
        """Tail 시나리오를 기본 시나리오에 통합"""
        
        scenarios_copy = base_scenarios.copy()
        total_years = len(scenarios_copy)
        
        for tail_scenario in tail_scenarios:
            # 시나리오 발생 확률에 따라 적용할 연도 선택
            probability = tail_scenario.get("probability", 0.01)
            n_years = max(1, int(total_years * probability))
            
            # 랜덤하게 연도 선택
            selected_years = np.random.choice(total_years, size=n_years, replace=False)
            
            for year_idx in selected_years:
                # 기존 이벤트들을 tail 시나리오로 증폭
                severity_mult = tail_scenario.get("severity_multiplier", 2.0)
                frequency_mult = tail_scenario.get("frequency_multiplier", 1.0)
                
                original_events = scenarios_copy.at[year_idx, "events_with_payouts"]
                if not original_events:
                    continue
                
                # 심도 증폭
                amplified_events = []
                for event in original_events:
                    amplified_event = event.copy()
                    amplified_event["severity"] *= severity_mult
                    amplified_event["tail_scenario"] = tail_scenario["name"]
                    amplified_events.append(amplified_event)
                
                # 빈도 증폭 (추가 이벤트 생성)
                if frequency_mult > 1.0:
                    additional_events = int((frequency_mult - 1.0) * len(original_events))
                    for i in range(additional_events):
                        # 기존 이벤트 중 하나를 복제하고 변형
                        base_event = np.random.choice(original_events)
                        new_event = base_event.copy()
                        new_event["event_id"] = f"{year_idx}_tail_{i}"
                        new_event["severity"] *= severity_mult * np.random.uniform(0.8, 1.2)
                        new_event["tail_scenario"] = tail_scenario["name"]
                        amplified_events.append(new_event)
                
                # 지급액 재계산
                updated_events, annual_loss = self._recalculate_payouts(amplified_events, canvas)
                scenarios_copy.at[year_idx, "events_with_payouts"] = updated_events
                scenarios_copy.at[year_idx, "annual_loss"] = annual_loss
                scenarios_copy.at[year_idx, "tail_scenario"] = tail_scenario["name"]
        
        return scenarios_copy
    
    def _recalculate_payouts(self, events: List[Dict], canvas: PerilCanvas) -> Tuple[List[Dict], float]:
        """이벤트 리스트의 지급액 재계산"""
        
        trigger_condition = canvas.limit_structure.trigger_condition
        payout_curve = canvas.limit_structure.payout_curve
        
        updated_events = []
        annual_loss = 0.0
        
        for event in events:
            severity = event["severity"]
            triggered = self._check_trigger_condition(severity, trigger_condition)
            
            if triggered:
                payout = self._calculate_event_payout(severity, trigger_condition, payout_curve)
                annual_loss += payout
                event_updated = {**event, "payout": payout, "triggered": True}
            else:
                event_updated = {**event, "payout": 0.0, "triggered": False}
            
            updated_events.append(event_updated)
        
        return updated_events, annual_loss
    
    def export_scenarios(self, scenarios: pd.DataFrame, filepath: str) -> None:
        """시나리오 데이터를 CSV로 저장"""
        
        # 이벤트 세부사항을 평면화
        flattened_data = []
        
        for _, row in scenarios.iterrows():
            year = row["year"]
            event_count = row["event_count"]
            annual_loss = row["annual_loss"]
            events = row.get("events_with_payouts", [])
            tail_scenario = row.get("tail_scenario", None)
            
            if not events:
                # 이벤트가 없는 연도
                flattened_data.append({
                    "year": year,
                    "event_count": 0,
                    "annual_loss": 0.0,
                    "event_id": None,
                    "severity": None,
                    "payout": 0.0,
                    "triggered": False,
                    "tail_scenario": tail_scenario
                })
            else:
                # 각 이벤트별로 행 생성
                for event in events:
                    flattened_data.append({
                        "year": year,
                        "event_count": event_count,
                        "annual_loss": annual_loss,
                        "event_id": event.get("event_id"),
                        "severity": event.get("severity"),
                        "payout": event.get("payout", 0.0),
                        "triggered": event.get("triggered", False),
                        "tail_scenario": tail_scenario
                    })
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(filepath, index=False)
    
    def get_scenario_summary(self, scenarios: pd.DataFrame) -> Dict[str, float]:
        """시나리오 요약 통계"""
        
        annual_losses = scenarios["annual_loss"]
        
        return {
            "total_scenarios": len(scenarios),
            "mean_annual_loss": annual_losses.mean(),
            "std_annual_loss": annual_losses.std(),
            "min_annual_loss": annual_losses.min(),
            "max_annual_loss": annual_losses.max(),
            "median_annual_loss": annual_losses.median(),
            "zero_loss_years": (annual_losses == 0).sum(),
            "extreme_loss_years": (annual_losses > annual_losses.quantile(0.95)).sum(),
            "total_events": scenarios["event_count"].sum(),
            "avg_events_per_year": scenarios["event_count"].mean()
        }


# 편의 함수들
async def generate_scenarios_from_priors(
    canvas: PerilCanvas,
    frequency_prior: FrequencyPrior,
    severity_prior: SeverityPrior,
    years: int = 1000,
    random_seed: Optional[int] = None
) -> pd.DataFrame:
    """간편한 시나리오 생성 함수"""
    generator = SyntheticScenarioGenerator(random_seed=random_seed)
    return await generator.generate_scenarios(canvas, frequency_prior, severity_prior, years)


def export_scenarios_csv(scenarios: pd.DataFrame, filepath: str) -> None:
    """간편한 CSV 저장 함수"""
    generator = SyntheticScenarioGenerator()
    generator.export_scenarios(scenarios, filepath)