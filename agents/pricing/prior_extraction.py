"""
Prior Extraction System (STEP 1)

확률-주도 프롬프팅을 통해 LLM에서 확률 분포 모수를 추출하는 모듈입니다.
실측 데이터가 없는 상황에서 LLM의 전문지식을 활용하여 Prior 분포를 생성합니다.
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models.base import (
    PerilCanvas, FrequencyPrior, SeverityPrior, DistributionType
)
from ..core.config import get_config


class PriorExtractor:
    """LLM 기반 확률 분포 모수 추출기"""
    
    def __init__(self):
        self.config = get_config()
        self._llm = None
    
    @property
    def llm(self) -> ChatOpenAI:
        """지연 초기화된 LLM 인스턴스"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.config.model_name,
                temperature=0.1,  # 일관성을 위해 매우 낮은 temperature
                max_tokens=1500,
                api_key=self.config.openai_api_key
            )
        return self._llm
    
    async def extract_priors(self, canvas: PerilCanvas) -> Tuple[FrequencyPrior, SeverityPrior]:
        """
        Peril Canvas로부터 빈도 및 심도 Prior 추출
        
        Args:
            canvas: 생성된 PerilCanvas 객체
            
        Returns:
            Tuple of (FrequencyPrior, SeverityPrior)
        """
        # 동시에 빈도와 심도 Prior 추출
        frequency_task = self.extract_frequency_prior(
            canvas.peril, canvas.region, canvas.data_sources
        )
        severity_task = self.extract_severity_prior(
            canvas.peril, canvas.trigger_metric, 
            canvas.limit_structure.trigger_condition.unit
        )
        
        frequency_prior, severity_prior = await asyncio.gather(
            frequency_task, severity_task
        )
        
        # Self-Critique Loop으로 일관성 검증
        validated_priors = await self.self_critique_loop(
            canvas, frequency_prior, severity_prior
        )
        
        return validated_priors["frequency"], validated_priors["severity"]
    
    async def extract_frequency_prior(
        self, peril: str, region: str, data_sources: List[str]
    ) -> FrequencyPrior:
        """
        연간 발생 빈도 Prior 추출 (Negative-Binomial)
        
        Args:
            peril: 위험 타입
            region: 적용 지역
            data_sources: 데이터 소스 목록
            
        Returns:
            FrequencyPrior 객체
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are an actuarial risk modeling expert with deep knowledge of catastrophe modeling and historical event patterns.

Provide annual event frequency parameters as independent random variables for parametric insurance modeling.

Response format (JSON only):
{
    "distribution": "negative_binomial",
    "parameters": {
        "r": 2.5,
        "p": 0.75
    },
    "percentiles": {
        "5th": 0.0,
        "50th": 1.0,
        "95th": 4.0
    },
    "sources": ["Source1", "Source2"],
    "confidence": 0.85,
    "rationale": "Brief explanation of parameter selection"
}

Key requirements:
1. Use Negative-Binomial(r, p) for overdispersed count data
2. Provide 5th, 50th, 95th percentiles for uncertainty quantification
3. Name at least 2 authoritative meteorological/industry sources
4. Confidence level based on data quality and historical precedent
"""),
            ("human", """
Event type: {peril}
Region: {region}
Context: Annual frequency modeling for parametric insurance
Data sources mentioned: {data_sources}

Provide the Negative-Binomial parameters for annual event count, considering:
- Historical frequency patterns in the specified region
- Climate change trends and evolving risk patterns
- Seasonal clustering and return periods
- Regional vulnerability and exposure characteristics
""")
        ])
        
        try:
            messages = prompt.format_messages(
                peril=peril, 
                region=region, 
                data_sources=", ".join(data_sources) if data_sources else "Standard meteorological databases"
            )
            response = await self.llm.ainvoke(messages)
            
            # JSON 파싱 및 검증
            prior_data = json.loads(response.content)
            return FrequencyPrior(**prior_data)
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: 기본 Prior 반환
            return self._get_default_frequency_prior(peril, region)
    
    async def extract_severity_prior(
        self, peril: str, metric: str, unit: str
    ) -> SeverityPrior:
        """
        이벤트 심도 Prior 추출 (LogNormal, Gamma 등)
        
        Args:
            peril: 위험 타입
            metric: 트리거 지표
            unit: 측정 단위
            
        Returns:
            SeverityPrior 객체
        """
        
        # 위험 타입별 적절한 분포 선택
        recommended_distribution = self._get_recommended_severity_distribution(peril, metric)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""
You are an expert in catastrophe modeling and extreme value statistics.

Provide severity distribution parameters for the trigger metric when events occur.

Response format (JSON only):
{{
    "distribution": "{recommended_distribution}",
    "parameters": {{
        "mu": 2.1,
        "sigma": 0.6
    }},
    "percentiles": {{
        "5th": 3.2,
        "50th": 8.1,
        "95th": 25.4
    }},
    "metric_unit": "{unit}",
    "sources": ["Source1", "Source2"],
    "confidence": 0.82,
    "rationale": "Brief explanation of distribution choice and parameters"
}}

Distribution guidance:
- LogNormal: For multiplicative processes, positive skewness
- Gamma: For positive continuous values with flexible shape
- Exponential: For memory-less waiting times
- Normal: For symmetric, bell-shaped distributions
"""),
            ("human", """
Event type: {peril}
Trigger metric: {metric}
Unit: {unit}
Recommended distribution: {recommended_distribution}

Provide the {recommended_distribution} distribution parameters for the severity of {metric} when {peril} events occur.

Consider:
- Physical constraints and realistic ranges for {metric}
- Historical extreme values and return periods
- Fat-tail characteristics for catastrophic events
- Measurement precision and data quality factors
""")
        ])
        
        try:
            messages = prompt.format_messages(
                peril=peril,
                metric=metric,
                unit=unit,
                recommended_distribution=recommended_distribution
            )
            response = await self.llm.ainvoke(messages)
            
            # JSON 파싱 및 검증
            prior_data = json.loads(response.content)
            return SeverityPrior(**prior_data)
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: 기본 Prior 반환
            return self._get_default_severity_prior(peril, metric, unit)
    
    def _get_recommended_severity_distribution(self, peril: str, metric: str) -> str:
        """위험 타입과 지표에 따른 권장 분포"""
        
        distribution_mapping = {
            ("typhoon", "central_pressure"): "lognormal",
            ("typhoon", "wind_speed"): "gamma",
            ("flight_delay", "delay_minutes"): "gamma",
            ("earthquake", "magnitude"): "gamma",
            ("server_downtime", "downtime_minutes"): "exponential",
            ("flood", "water_level"): "lognormal",
            ("drought", "precipitation_deficit"): "gamma"
        }
        
        return distribution_mapping.get((peril, metric), "lognormal")
    
    async def self_critique_loop(
        self, canvas: PerilCanvas, frequency_prior: FrequencyPrior, severity_prior: SeverityPrior
    ) -> Dict[str, any]:
        """
        LLM Self-Critique Loop으로 모수 일관성 검증 및 수정
        
        Args:
            canvas: PerilCanvas 객체
            frequency_prior: 추출된 빈도 Prior
            severity_prior: 추출된 심도 Prior
            
        Returns:
            검증 및 수정된 Prior 딕셔너리
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a senior actuarial reviewer. Examine the consistency and reasonableness of these parametric insurance model parameters.

Response format (JSON only):
{
    "consistent": true/false,
    "issues": ["Issue 1", "Issue 2"],
    "corrections": {
        "frequency": {
            "parameters": {"r": 2.8, "p": 0.8},
            "rationale": "Adjustment reason"
        },
        "severity": {
            "parameters": {"mu": 2.0, "sigma": 0.5},
            "rationale": "Adjustment reason"
        }
    },
    "overall_assessment": "Brief assessment of model credibility"
}

Consistency checks:
1. Parameter ranges within realistic bounds
2. Frequency-severity relationship makes sense
3. Regional applicability of parameters
4. Historical precedent alignment
5. Extreme scenario plausibility
"""),
            ("human", """
Event: {peril} in {region}
Trigger: {metric} {unit}

Frequency Prior (Negative-Binomial):
- r = {freq_r}, p = {freq_p}
- 50th percentile: {freq_50th} events/year

Severity Prior ({severity_dist}):
- μ = {sev_mu}, σ = {sev_sigma}
- 50th percentile: {sev_50th} {unit}

Are these parameters self-consistent and realistic? If not, provide corrections.
""")
        ])
        
        try:
            messages = prompt.format_messages(
                peril=canvas.peril,
                region=canvas.region,
                metric=canvas.trigger_metric,
                unit=canvas.limit_structure.trigger_condition.unit,
                freq_r=frequency_prior.parameters.get("r"),
                freq_p=frequency_prior.parameters.get("p"),
                freq_50th=frequency_prior.percentiles.get("50th"),
                severity_dist=severity_prior.distribution,
                sev_mu=severity_prior.parameters.get("mu", "N/A"),
                sev_sigma=severity_prior.parameters.get("sigma", "N/A"),
                sev_50th=severity_prior.percentiles.get("50th")
            )
            response = await self.llm.ainvoke(messages)
            
            critique_result = json.loads(response.content)
            
            # 수정사항이 있다면 적용
            if not critique_result["consistent"] and "corrections" in critique_result:
                corrected_frequency = self._apply_frequency_corrections(
                    frequency_prior, critique_result["corrections"].get("frequency")
                )
                corrected_severity = self._apply_severity_corrections(
                    severity_prior, critique_result["corrections"].get("severity")
                )
                
                return {
                    "frequency": corrected_frequency,
                    "severity": corrected_severity,
                    "critique": critique_result
                }
            
            return {
                "frequency": frequency_prior,
                "severity": severity_prior,
                "critique": critique_result
            }
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: 원본 Prior 반환
            return {
                "frequency": frequency_prior,
                "severity": severity_prior,
                "critique": {"consistent": True, "issues": [], "overall_assessment": "Default validation"}
            }
    
    def _apply_frequency_corrections(self, original: FrequencyPrior, corrections: Optional[Dict]) -> FrequencyPrior:
        """빈도 Prior 수정사항 적용"""
        if not corrections or "parameters" not in corrections:
            return original
        
        # 새로운 파라미터로 업데이트
        updated_params = {**original.parameters, **corrections["parameters"]}
        
        return FrequencyPrior(
            distribution=original.distribution,
            parameters=updated_params,
            percentiles=original.percentiles,  # 백분위수는 재계산 필요하지만 일단 유지
            sources=original.sources,
            confidence=original.confidence * 0.9  # 수정으로 인한 신뢰도 약간 감소
        )
    
    def _apply_severity_corrections(self, original: SeverityPrior, corrections: Optional[Dict]) -> SeverityPrior:
        """심도 Prior 수정사항 적용"""
        if not corrections or "parameters" not in corrections:
            return original
        
        # 새로운 파라미터로 업데이트
        updated_params = {**original.parameters, **corrections["parameters"]}
        
        return SeverityPrior(
            distribution=original.distribution,
            parameters=updated_params,
            percentiles=original.percentiles,
            metric_unit=original.metric_unit,
            sources=original.sources,
            confidence=original.confidence * 0.9
        )
    
    def _get_default_frequency_prior(self, peril: str, region: str) -> FrequencyPrior:
        """기본 빈도 Prior (LLM 실패 시)"""
        
        default_priors = {
            "typhoon": {
                "parameters": {"r": 2.5, "p": 0.8},
                "percentiles": {"5th": 0.0, "50th": 1.0, "95th": 4.0},
                "sources": ["JMA Historical Database", "NOAA Storm Database"]
            },
            "flight_delay": {
                "parameters": {"r": 5.0, "p": 0.7},
                "percentiles": {"5th": 1.0, "50th": 3.0, "95th": 8.0},
                "sources": ["FlightAware Statistics", "OAG Performance Data"]
            },
            "earthquake": {
                "parameters": {"r": 1.5, "p": 0.9},
                "percentiles": {"5th": 0.0, "50th": 0.0, "95th": 2.0},
                "sources": ["USGS Earthquake Database", "Regional Seismic Networks"]
            },
            "server_downtime": {
                "parameters": {"r": 8.0, "p": 0.6},
                "percentiles": {"5th": 2.0, "50th": 5.0, "95th": 12.0},
                "sources": ["Industry Uptime Statistics", "Cloud Provider SLAs"]
            }
        }
        
        default = default_priors.get(peril, {
            "parameters": {"r": 3.0, "p": 0.75},
            "percentiles": {"5th": 0.0, "50th": 1.0, "95th": 5.0},
            "sources": ["Industry Statistics", "Expert Judgment"]
        })
        
        return FrequencyPrior(
            distribution=DistributionType.NEGATIVE_BINOMIAL,
            parameters=default["parameters"],
            percentiles=default["percentiles"],
            sources=default["sources"],
            confidence=0.7  # 기본값은 낮은 신뢰도
        )
    
    def _get_default_severity_prior(self, peril: str, metric: str, unit: str) -> SeverityPrior:
        """기본 심도 Prior (LLM 실패 시)"""
        
        default_priors = {
            ("typhoon", "central_pressure"): {
                "distribution": DistributionType.LOGNORMAL,
                "parameters": {"mu": 2.1, "sigma": 0.6},
                "percentiles": {"5th": 3.2, "50th": 8.1, "95th": 25.4},
                "sources": ["JMA Storm Database"]
            },
            ("flight_delay", "delay_minutes"): {
                "distribution": DistributionType.GAMMA,
                "parameters": {"alpha": 2.0, "beta": 0.03},
                "percentiles": {"5th": 15.0, "50th": 67.0, "95th": 180.0},
                "sources": ["Aviation Statistics"]
            },
            ("server_downtime", "downtime_minutes"): {
                "distribution": DistributionType.EXPONENTIAL,
                "parameters": {"lambda": 0.1},
                "percentiles": {"5th": 0.5, "50th": 6.9, "95th": 30.0},
                "sources": ["IT Industry Reports"]
            }
        }
        
        key = (peril, metric)
        default = default_priors.get(key, {
            "distribution": DistributionType.LOGNORMAL,
            "parameters": {"mu": 1.0, "sigma": 0.5},
            "percentiles": {"5th": 1.2, "50th": 2.7, "95th": 7.4},
            "sources": ["Expert Judgment"]
        })
        
        return SeverityPrior(
            distribution=default["distribution"],
            parameters=default["parameters"],
            percentiles=default["percentiles"],
            metric_unit=unit,
            sources=default["sources"],
            confidence=0.7
        )


# 편의 함수들
async def extract_priors_from_canvas(canvas: PerilCanvas) -> Tuple[FrequencyPrior, SeverityPrior]:
    """간편한 Prior 추출 함수"""
    extractor = PriorExtractor()
    return await extractor.extract_priors(canvas)


async def validate_prior_consistency(
    frequency_prior: FrequencyPrior, 
    severity_prior: SeverityPrior,
    canvas: PerilCanvas
) -> Dict[str, any]:
    """간편한 Prior 일관성 검증 함수"""
    extractor = PriorExtractor()
    result = await extractor.self_critique_loop(canvas, frequency_prior, severity_prior)
    return result["critique"]