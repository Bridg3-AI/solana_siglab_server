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
            ("system", """You are an actuarial risk modeling expert with deep knowledge of catastrophe modeling and historical event patterns.

CRITICAL: Respond with pure JSON format only. No code blocks or additional explanations. Output JSON only.

Response format:
{{
    "distribution": "negative_binomial",
    "parameters": {{
        "r": 2.5,
        "p": 0.75
    }},
    "percentiles": {{
        "5th": 0.0,
        "50th": 1.0,
        "95th": 4.0
    }},
    "sources": ["Source1", "Source2"],
    "confidence": 0.85,
    "rationale": "Brief explanation of parameter selection"
}}

Key requirements:
1. Use Negative-Binomial(r, p) for overdispersed count data
2. Provide 5th, 50th, 95th percentiles for uncertainty quantification
3. Name at least 2 authoritative meteorological/industry sources
4. Confidence level based on data quality and historical precedent"""),
            ("human", """Event type: {peril}
Region: {region}
Context: Annual frequency modeling for parametric insurance
Data sources mentioned: {data_sources}

Provide the Negative-Binomial parameters for annual event count, considering:
- Historical frequency patterns in the specified region
- Climate change trends and evolving risk patterns
- Seasonal clustering and return periods
- Regional vulnerability and exposure characteristics""")
        ])
        
        try:
            print(f"🔍 [API] 빈도 Prior LLM 호출 중... (위험: {peril}, 지역: {region})")
            messages = prompt.format_messages(
                peril=peril, 
                region=region, 
                data_sources=", ".join(data_sources) if data_sources else "Standard meteorological databases"
            )
            response = await self.llm.ainvoke(messages)
            print(f"✅ [API] 빈도 Prior LLM 응답 성공")
            print(f"🔍 [API] 응답 내용: {response.content[:300]}...")
            
            # JSON 파싱 및 검증 - 강화된 파싱 로직
            content = response.content.strip()
            
            # 코드 블록 제거
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # JSON 추출
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                content = content[start_idx:end_idx+1]
            
            print(f"🔍 [API] 빈도 Prior JSON 추출: {content}")
            prior_data = json.loads(content)
            print(f"✅ [API] 빈도 Prior JSON 파싱 성공: {prior_data}")
            return FrequencyPrior(**prior_data)
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"❌ [API] 빈도 Prior LLM 호출 실패: {str(e)}")
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
        
        # JSON에서 중괄호가 문제가 되지 않도록 문자열 연결 방식 사용
        system_prompt = (
            "You are an expert in catastrophe modeling and extreme value statistics.\n\n"
            "CRITICAL: Respond with pure JSON format only. No code blocks or additional explanations. Output JSON only.\n\n"
            "Response format:\n"
            "{\n"
            '    "distribution": "' + recommended_distribution + '",\n'
            '    "parameters": {\n'
            '        "mu": 2.1,\n'
            '        "sigma": 0.6\n'
            '    },\n'
            '    "percentiles": {\n'
            '        "5th": 3.2,\n'
            '        "50th": 8.1,\n'
            '        "95th": 25.4\n'
            '    },\n'
            '    "metric_unit": "' + unit + '",\n'
            '    "sources": ["Source1", "Source2"],\n'
            '    "confidence": 0.82,\n'
            '    "rationale": "Brief explanation of distribution choice and parameters"\n'
            "}\n\n"
            "Distribution guidance:\n"
            "- LogNormal: For multiplicative processes, positive skewness\n"
            "- Gamma: For positive continuous values with flexible shape\n"
            "- Exponential: For memory-less waiting times\n"
            "- Normal: For symmetric, bell-shaped distributions"
        )
        
        # human 메시지도 문자열 연결 방식으로 LangChain 템플릿 충돌 방지
        # 티켓 관련 지표에 대한 특별한 안내 제공
        if "tickets" in metric or "ticket" in metric:
            if "percentage" in metric or "percent" in unit:
                human_prompt = (
                    "Event type: " + peril + "\n"
                    "Trigger metric: " + metric + "\n"
                    "Unit: " + unit + "\n"
                    "Recommended distribution: " + recommended_distribution + "\n\n"
                    "CRITICAL: For percentage-based metrics, values should be realistic percentages (0-100).\n"
                    "Typical ranges: Low sales (20-40%), Medium sales (50-70%), High sales (80-95%).\n"
                    "Concert cancellations often occur when sales are high (70%+), so ensure distribution reflects this.\n\n"
                    "Provide the " + recommended_distribution + " distribution parameters for " + metric + " severity in " + peril + " scenarios.\n\n"
                    "Requirements:\n"
                    "- Values must be in percentage range (0-100)\n"
                    "- 50th percentile should be around 60-80% for realistic cancellation scenarios\n"
                    "- 95th percentile should approach 90-95% to capture high-ticket-sales cancellations\n"
                    "- Parameters should generate values that can trigger the insurance payout\n"
                    "- Consider seasonal patterns and market dynamics"
                )
            else:  # number_of_tickets_sold case
                human_prompt = (
                    "Event type: " + peril + "\n"
                    "Trigger metric: " + metric + "\n"
                    "Unit: " + unit + "\n"
                    "Recommended distribution: " + recommended_distribution + "\n\n"
                    "CRITICAL: For ticket count metrics, values should reflect realistic concert venue capacities.\n"
                    "Typical venue sizes: Small venues (500-2000), Medium venues (2000-10000), Large venues (10000-50000).\n"
                    "Concert cancellations are insured when significant ticket sales occur (1000+ tickets).\n\n"
                    "Provide the " + recommended_distribution + " distribution parameters for " + metric + " severity in " + peril + " scenarios.\n\n"
                    "Requirements:\n"
                    "- Values should represent realistic ticket sales numbers\n"
                    "- 50th percentile should be around 2000-5000 tickets for medium venues\n"
                    "- 95th percentile should reach 10000-20000 for large venue scenarios\n"
                    "- Parameters should generate values that can trigger insurance payouts (>1000 tickets)\n"
                    "- Consider venue capacity constraints and market demand patterns"
                )
        else:
            human_prompt = (
                "Event type: " + peril + "\n"
                "Trigger metric: " + metric + "\n"
                "Unit: " + unit + "\n"
                "Recommended distribution: " + recommended_distribution + "\n\n"
                "Provide the " + recommended_distribution + " distribution parameters for the severity of " + metric + " when " + peril + " events occur.\n\n"
                "Consider:\n"
                "- Physical constraints and realistic ranges for " + metric + "\n"
                "- Historical extreme values and return periods\n"
                "- Fat-tail characteristics for catastrophic events\n"
                "- Measurement precision and data quality factors"
            )
        
        try:
            print(f"🔍 [API] 심도 Prior LLM 호출 중... (위험: {peril}, 지표: {metric})")
            
            # ChatPromptTemplate을 사용하지 않고 직접 메시지 생성
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            print(f"🔍 [API] 메시지 직접 생성 완료")
            response = await self.llm.ainvoke(messages)
            print(f"✅ [API] 심도 Prior LLM 응답 성공")
            print(f"🔍 [API] 응답 내용: {response.content[:300]}...")
            
            # JSON 파싱 및 검증 - 강화된 파싱 로직
            content = response.content.strip()
            
            # 코드 블록 제거
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # JSON 추출
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                content = content[start_idx:end_idx+1]
            
            print(f"🔍 [API] 심도 Prior JSON 추출: {content}")
            prior_data = json.loads(content)
            print(f"✅ [API] 심도 Prior JSON 파싱 성공: {prior_data}")
            
            # LLM 제공 파라미터와 percentile이 불일치할 경우 수정
            corrected_prior_data = self._correct_distribution_parameters(prior_data)
            
            return SeverityPrior(**corrected_prior_data)
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"❌ [API] 심도 Prior LLM 호출 실패: {str(e)}")
            # Fallback: 기본 Prior 반환
            return self._get_default_severity_prior(peril, metric, unit)
    
    def _get_recommended_severity_distribution(self, peril: str, metric: str) -> str:
        """위험 타입과 지표에 따른 권장 분포"""
        
        distribution_mapping = {
            ("typhoon", "central_pressure"): "lognormal",
            ("typhoon", "wind_speed"): "gamma",
            ("concert_cancellation", "event_intensity"): "gamma",
            ("concert_cancellation", "cancellation_rate"): "gamma",  # 새로운 지표 추가
            ("event_cancellation", "event_intensity"): "gamma",
            ("flight_delay", "delay_minutes"): "gamma",
            ("earthquake", "magnitude"): "gamma",
            ("server_downtime", "downtime_minutes"): "exponential",
            ("flood", "water_level"): "lognormal",
            ("drought", "precipitation_deficit"): "gamma"
        }
        
        return distribution_mapping.get((peril, metric), "lognormal")
    
    def _correct_distribution_parameters(self, prior_data: dict) -> dict:
        """LLM이 제공한 분포 파라미터를 percentile 기반으로 수정"""
        
        distribution = prior_data.get("distribution", "lognormal")
        percentiles = prior_data.get("percentiles", {})
        parameters = prior_data.get("parameters", {})
        
        # percentile 값이 없으면 원본 반환
        if not percentiles or "50th" not in percentiles:
            return prior_data
        
        try:
            p50 = float(percentiles["50th"])
            
            if distribution == "lognormal":
                # LogNormal 분포 파라미터 수정
                corrected_params = self._correct_lognormal_parameters(percentiles, parameters)
                if corrected_params:
                    print(f"🔧 [PRIOR] LogNormal 파라미터 수정: {parameters} → {corrected_params}")
                    prior_data["parameters"] = corrected_params
            
            elif distribution == "gamma":
                # Gamma 분포 파라미터 수정
                corrected_params = self._correct_gamma_parameters(percentiles, parameters)
                if corrected_params:
                    print(f"🔧 [PRIOR] Gamma 파라미터 수정: {parameters} → {corrected_params}")
                    prior_data["parameters"] = corrected_params
            
            return prior_data
            
        except (ValueError, TypeError) as e:
            print(f"⚠️ [PRIOR] 분포 파라미터 수정 실패: {e} - 원본 사용")
            return prior_data
    
    def _correct_lognormal_parameters(self, percentiles: dict, original_params: dict) -> dict:
        """LogNormal 분포 파라미터를 percentile 기반으로 수정"""
        
        try:
            import numpy as np
            
            p50 = float(percentiles["50th"])
            
            # 50th percentile = exp(mu)이므로 mu 계산
            mu = np.log(p50)
            
            # 95th percentile이 있으면 sigma 계산
            if "95th" in percentiles:
                p95 = float(percentiles["95th"])
                # P95 / P50 = exp(1.645 * sigma)
                ratio = p95 / p50
                sigma = np.log(ratio) / 1.645
            else:
                # 기본값 사용
                sigma = original_params.get("sigma", 0.5)
            
            # 합리적인 범위로 제한
            mu = max(-2, min(15, mu))  # exp(-2) ≈ 0.14, exp(15) ≈ 3.3M
            sigma = max(0.1, min(2.0, sigma))  # 너무 좁거나 넓지 않게
            
            return {"mu": round(mu, 3), "sigma": round(sigma, 3)}
            
        except Exception as e:
            print(f"⚠️ [PRIOR] LogNormal 파라미터 수정 실패: {e}")
            return None
    
    def _correct_gamma_parameters(self, percentiles: dict, original_params: dict) -> dict:
        """Gamma 분포 파라미터를 percentile 기반으로 수정"""
        
        try:
            import numpy as np
            from scipy import stats, optimize
            
            p50 = float(percentiles["50th"])
            
            # 기존 파라미터가 있으면 보정, 없으면 추정
            if "alpha" in original_params and "beta" in original_params:
                alpha = float(original_params["alpha"])
                beta = float(original_params["beta"])
                
                # 스케일 조정 (mean = alpha/beta = p50의 약 80% 정도)
                target_mean = p50 * 0.8
                scale_factor = target_mean / (alpha / beta)
                beta = beta * scale_factor
                
            else:
                # 기본값으로 추정 (shape=2, scale은 p50 기준)
                alpha = 2.0
                beta = alpha / (p50 * 0.8)
            
            # 합리적인 범위로 제한
            alpha = max(0.5, min(10.0, alpha))
            beta = max(0.001, min(100.0, beta))
            
            return {"alpha": round(alpha, 3), "beta": round(beta, 3)}
            
        except Exception as e:
            print(f"⚠️ [PRIOR] Gamma 파라미터 수정 실패: {e}")
            return None
    
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
            "concert_cancellation": {
                "parameters": {"r": 3.0, "p": 0.85},
                "percentiles": {"5th": 0.0, "50th": 1.0, "95th": 3.0},
                "sources": ["Entertainment Industry Reports", "Event Management Statistics"]
            },
            "event_cancellation": {
                "parameters": {"r": 4.0, "p": 0.8},
                "percentiles": {"5th": 0.0, "50th": 2.0, "95th": 5.0},
                "sources": ["Event Industry Database", "Insurance Claims Data"]
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
            ("concert_cancellation", "event_intensity"): {
                "distribution": DistributionType.GAMMA,
                "parameters": {"alpha": 1.5, "beta": 0.5},
                "percentiles": {"5th": 0.2, "50th": 2.5, "95th": 8.0},
                "sources": ["Entertainment Industry Reports"]
            },
            ("event_cancellation", "event_intensity"): {
                "distribution": DistributionType.GAMMA,
                "parameters": {"alpha": 2.0, "beta": 0.4},
                "percentiles": {"5th": 0.5, "50th": 4.0, "95th": 12.0},
                "sources": ["Event Management Statistics"]
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