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
        """빈도 분포에서 샘플링"""
        
        dist_type = frequency_prior.distribution
        params = frequency_prior.parameters
        
        if dist_type == DistributionType.NEGATIVE_BINOMIAL:
            r = params["r"]
            p = params["p"]
            return np.random.negative_binomial(r, p)
        
        elif dist_type == DistributionType.POISSON:
            lam = params["lambda"]
            return np.random.poisson(lam)
        
        else:
            # 기본값: Poisson(1)
            return np.random.poisson(1)
    
    def _sample_severity(self, severity_prior: SeverityPrior) -> float:
        """심도 분포에서 샘플링"""
        
        dist_type = severity_prior.distribution
        params = severity_prior.parameters
        
        if dist_type == DistributionType.LOGNORMAL:
            mu = params["mu"]
            sigma = params["sigma"]
            return np.random.lognormal(mu, sigma)
        
        elif dist_type == DistributionType.GAMMA:
            if "alpha" in params and "beta" in params:
                alpha = params["alpha"]
                beta = params["beta"]
                return np.random.gamma(alpha, 1/beta)
            elif "shape" in params and "scale" in params:
                shape = params["shape"]
                scale = params["scale"]
                return np.random.gamma(shape, scale)
        
        elif dist_type == DistributionType.EXPONENTIAL:
            if "lambda" in params:
                lam = params["lambda"]
                return np.random.exponential(1/lam)
            elif "scale" in params:
                scale = params["scale"]
                return np.random.exponential(scale)
        
        elif dist_type == DistributionType.NORMAL:
            mu = params.get("mu", 0)
            sigma = params.get("sigma", 1)
            return max(0, np.random.normal(mu, sigma))  # 음수 방지
        
        else:
            # 기본값: LogNormal(1, 0.5)
            return np.random.lognormal(1, 0.5)
    
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
        """트리거 조건 확인"""
        
        threshold = trigger_condition.threshold
        operator = trigger_condition.operator
        
        if operator == ">=":
            return severity >= threshold
        elif operator == "<=":
            return severity <= threshold
        elif operator == ">":
            return severity > threshold
        elif operator == "<":
            return severity < threshold
        elif operator == "==":
            return abs(severity - threshold) < 0.001  # 부동소수점 비교
        else:
            return severity >= threshold  # 기본값
    
    def _calculate_event_payout(self, severity: float, trigger_condition, payout_curve) -> float:
        """개별 이벤트의 지급액 계산"""
        
        threshold = trigger_condition.threshold
        curve_type = payout_curve.curve_type
        base_amount = payout_curve.base_amount
        max_payout = payout_curve.max_payout
        multiplier = payout_curve.multiplier
        
        # 트리거 초과 정도 계산
        if trigger_condition.operator in [">=", ">"]:
            excess = max(0, severity - threshold)
        elif trigger_condition.operator in ["<=", "<"]:
            excess = max(0, threshold - severity)
        else:
            excess = abs(severity - threshold)
        
        # 지급 곡선에 따른 계산
        if curve_type == CurveType.LINEAR:
            payout = base_amount + (excess * multiplier)
        
        elif curve_type == CurveType.STEP:
            # 단계별 지급 (excess를 기준으로)
            steps = int(excess)
            payout = base_amount + (steps * multiplier)
        
        elif curve_type == CurveType.EXPONENTIAL:
            # 지수적 증가
            payout = base_amount * (1 + excess) ** (multiplier / 1000)
        
        elif curve_type == CurveType.LOGARITHMIC:
            # 로그적 증가
            payout = base_amount + multiplier * np.log(1 + excess)
        
        else:
            # 기본값: 선형
            payout = base_amount + (excess * multiplier)
        
        # 최대 지급액 제한
        return min(payout, max_payout)
    
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