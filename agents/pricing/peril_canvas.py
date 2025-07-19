"""
Peril Canvas Generator (STEP 0)

보험 위험 정의 캔버스를 LLM 기반으로 자동 생성하는 모듈입니다.
사용자 입력을 분석하여 구체적인 보험 상품 스펙을 설계합니다.
"""

import json
from typing import Dict, List, Optional, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models.base import (
    PerilCanvas, PayoutCurve, LimitStructure, TriggerCondition,
    CurveType, DistributionType
)
from ..core.config import get_config


class PerilCanvasGenerator:
    """LLM 기반 Peril Canvas 자동 생성기"""
    
    def __init__(self):
        self.config = get_config()
        self._llm = None
    
    @property
    def llm(self) -> ChatOpenAI:
        """지연 초기화된 LLM 인스턴스"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.config.model_name,
                temperature=0.2,  # 일관성을 위해 낮은 temperature
                max_tokens=2000,
                api_key=self.config.openai_api_key
            )
        return self._llm
    
    async def generate_canvas_from_input(self, user_input: str) -> PerilCanvas:
        """
        사용자 입력으로부터 Peril Canvas 생성
        
        Args:
            user_input: 사용자의 자연어 입력
            
        Returns:
            생성된 PerilCanvas 객체
        """
        # 1단계: 위험 타입 및 기본 정보 추출
        peril_info = await self._extract_peril_info(user_input)
        
        # 2단계: 트리거 지표 추천
        trigger_metrics = await self._suggest_trigger_metrics(
            peril_info["peril"], peril_info["description"]
        )
        
        # 3단계: 지급 구조 설계
        payout_structure = await self._design_payout_structure(
            peril_info["peril"], trigger_metrics["primary_metric"]
        )
        
        # 4단계: PerilCanvas 객체 구성
        return self._build_peril_canvas(peril_info, trigger_metrics, payout_structure)
    
    async def _extract_peril_info(self, user_input: str) -> Dict[str, str]:
        """사용자 입력에서 위험 타입 및 기본 정보 추출"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
당신은 보험 상품 설계 전문가입니다. 사용자 입력을 분석하여 파라메트릭 보험 위험을 정의해주세요.

다음 JSON 형식으로 응답하세요:
{
    "peril": "위험 타입 (영문, 소문자, 언더스코어 사용)",
    "description": "위험에 대한 상세 설명 (한국어)",
    "region": "적용 지역",
    "coverage_period": "커버리지 기간",
    "industry": "관련 산업 분야"
}

예시:
- "태풍 보험" → peril: "typhoon"
- "항공편 지연" → peril: "flight_delay"  
- "게임 서버 다운" → peril: "server_downtime"
- "스포츠 경기 취소" → peril: "sports_cancellation"
"""),
            ("human", "사용자 입력: {user_input}")
        ])
        
        try:
            messages = prompt.format_messages(user_input=user_input)
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: 키워드 기반 매핑
            return self._fallback_peril_extraction(user_input)
    
    def _fallback_peril_extraction(self, user_input: str) -> Dict[str, str]:
        """LLM 실패 시 키워드 기반 위험 타입 추출"""
        
        user_lower = user_input.lower()
        
        peril_mappings = {
            "typhoon": {
                "keywords": ["태풍", "허리케인", "cyclone", "typhoon"],
                "description": "태풍으로 인한 재산 피해 및 사업 중단",
                "region": "Korea"
            },
            "flight_delay": {
                "keywords": ["항공", "비행기", "항공편", "지연", "취소", "flight"],
                "description": "항공편 지연 및 취소로 인한 손실",
                "region": "Global"
            },
            "earthquake": {
                "keywords": ["지진", "earthquake", "진도", "흔들림"],
                "description": "지진으로 인한 구조물 피해",
                "region": "Korea"
            },
            "server_downtime": {
                "keywords": ["서버", "다운", "장애", "outage", "downtime"],
                "description": "서버 다운타임으로 인한 비즈니스 손실",
                "region": "Global"
            },
            "weather": {
                "keywords": ["날씨", "기상", "weather", "악천후"],
                "description": "악천후로 인한 이벤트 취소 및 손실",
                "region": "Korea"
            }
        }
        
        for peril, info in peril_mappings.items():
            if any(keyword in user_lower for keyword in info["keywords"]):
                return {
                    "peril": peril,
                    "description": info["description"],
                    "region": info["region"],
                    "coverage_period": "annual",
                    "industry": "general"
                }
        
        # 기본값
        return {
            "peril": "general",
            "description": f"'{user_input}'에 대한 파라메트릭 보험",
            "region": "Global",
            "coverage_period": "annual",
            "industry": "general"
        }
    
    async def _suggest_trigger_metrics(self, peril: str, description: str) -> Dict[str, str]:
        """위험 타입에 따른 트리거 지표 추천"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
당신은 보험 계리사입니다. 주어진 위험에 대해 객관적이고 측정 가능한 트리거 지표를 추천해주세요.

다음 JSON 형식으로 응답하세요:
{
    "primary_metric": "주요 트리거 지표 (영문)",
    "metric_description": "지표 설명 (한국어)",
    "unit": "측정 단위",
    "data_sources": ["데이터 소스1", "데이터 소스2"],
    "threshold_guidance": "임계값 설정 가이드"
}

예시:
- 태풍: primary_metric: "central_pressure", unit: "hPa"
- 항공 지연: primary_metric: "delay_minutes", unit: "minutes"
- 서버 다운: primary_metric: "downtime_minutes", unit: "minutes"
"""),
            ("human", "위험: {peril}\n설명: {description}")
        ])
        
        try:
            messages = prompt.format_messages(peril=peril, description=description)
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            # Fallback: 기본 지표 매핑
            return self._get_default_trigger_metric(peril)
    
    def _get_default_trigger_metric(self, peril: str) -> Dict[str, str]:
        """기본 트리거 지표 매핑"""
        
        default_metrics = {
            "typhoon": {
                "primary_metric": "central_pressure",
                "metric_description": "태풍 중심기압",
                "unit": "hPa",
                "data_sources": ["JMA", "KMA", "NOAA"],
                "threshold_guidance": "950 hPa 이하에서 지급 시작"
            },
            "flight_delay": {
                "primary_metric": "delay_minutes",
                "metric_description": "평균 출발 지연 시간",
                "unit": "minutes",
                "data_sources": ["FlightAware", "OAG", "Airport APIs"],
                "threshold_guidance": "60분 이상 지연 시 지급"
            },
            "earthquake": {
                "primary_metric": "magnitude",
                "metric_description": "지진 규모",
                "unit": "Richter",
                "data_sources": ["USGS", "KMA", "JMA"],
                "threshold_guidance": "규모 6.0 이상에서 지급 시작"
            },
            "server_downtime": {
                "primary_metric": "downtime_minutes",
                "metric_description": "서버 다운타임",
                "unit": "minutes",
                "data_sources": ["Monitoring APIs", "Internal Systems"],
                "threshold_guidance": "10분 이상 다운 시 지급"
            }
        }
        
        return default_metrics.get(peril, {
            "primary_metric": "event_intensity",
            "metric_description": "이벤트 강도",
            "unit": "scale",
            "data_sources": ["Public APIs"],
            "threshold_guidance": "중간 강도 이상에서 지급"
        })
    
    async def _design_payout_structure(self, peril: str, metric: str) -> Dict:
        """지급 구조 설계"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
당신은 보험 상품 설계자입니다. 주어진 위험과 트리거 지표에 대해 합리적인 지급 구조를 설계해주세요.

다음 JSON 형식으로 응답하세요:
{
    "curve_type": "linear|step|exponential",
    "threshold": 임계값(숫자),
    "operator": "<=|>=|>|<",
    "base_amount": 기본지급액,
    "max_payout": 최대지급액,
    "multiplier": 지급배수,
    "deductible": 공제액,
    "rationale": "설계 근거"
}

보험 상품 설계 원칙:
1. 지급 임계값은 이벤트 심도와 비례해야 함
2. 최대 지급액은 시장에서 수용 가능한 수준
3. 지급 곡선은 위험의 특성을 반영해야 함
"""),
            ("human", "위험: {peril}\n트리거 지표: {metric}")
        ])
        
        try:
            messages = prompt.format_messages(peril=peril, metric=metric)
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            # Fallback: 기본 지급 구조
            return self._get_default_payout_structure(peril)
    
    def _get_default_payout_structure(self, peril: str) -> Dict:
        """기본 지급 구조 매핑"""
        
        default_structures = {
            "typhoon": {
                "curve_type": "linear",
                "threshold": 950.0,
                "operator": "<=",
                "base_amount": 10000.0,
                "max_payout": 2000000.0,
                "multiplier": 10000.0,
                "deductible": 0.0,
                "rationale": "중심기압이 낮을수록 피해가 커지는 선형 관계"
            },
            "flight_delay": {
                "curve_type": "step",
                "threshold": 60.0,
                "operator": ">=",
                "base_amount": 200.0,
                "max_payout": 1000000.0,
                "multiplier": 200.0,
                "deductible": 0.0,
                "rationale": "60분 단위로 단계적 지급"
            },
            "server_downtime": {
                "curve_type": "linear",
                "threshold": 10.0,
                "operator": ">=",
                "base_amount": 500.0,
                "max_payout": 750000.0,
                "multiplier": 500.0,
                "deductible": 0.0,
                "rationale": "다운타임에 비례한 비즈니스 손실 보상"
            }
        }
        
        return default_structures.get(peril, {
            "curve_type": "linear",
            "threshold": 1.0,
            "operator": ">=",
            "base_amount": 1000.0,
            "max_payout": 100000.0,
            "multiplier": 1000.0,
            "deductible": 0.0,
            "rationale": "일반적인 선형 지급 구조"
        })
    
    def _build_peril_canvas(
        self, 
        peril_info: Dict[str, str], 
        trigger_metrics: Dict[str, str], 
        payout_structure: Dict
    ) -> PerilCanvas:
        """최종 PerilCanvas 객체 구성"""
        
        # TriggerCondition 생성
        trigger_condition = TriggerCondition(
            metric=trigger_metrics["primary_metric"],
            threshold=payout_structure["threshold"],
            operator=payout_structure["operator"],
            unit=trigger_metrics["unit"]
        )
        
        # PayoutCurve 생성
        payout_curve = PayoutCurve(
            curve_type=CurveType(payout_structure["curve_type"]),
            base_amount=payout_structure["base_amount"],
            max_payout=payout_structure["max_payout"],
            multiplier=payout_structure["multiplier"]
        )
        
        # LimitStructure 생성
        limit_structure = LimitStructure(
            trigger_condition=trigger_condition,
            payout_curve=payout_curve,
            deductible=payout_structure["deductible"]
        )
        
        # PerilCanvas 생성
        return PerilCanvas(
            peril=peril_info["peril"],
            description=peril_info["description"],
            trigger_metric=trigger_metrics["primary_metric"],
            data_sources=trigger_metrics["data_sources"],
            limit_structure=limit_structure,
            region=peril_info["region"],
            coverage_period=peril_info["coverage_period"]
        )
    
    async def validate_canvas(self, canvas: PerilCanvas) -> Tuple[bool, List[str]]:
        """생성된 Canvas의 유효성 검증"""
        
        errors = []
        
        # 기본 검증
        if not canvas.peril:
            errors.append("위험 타입이 정의되지 않았습니다")
        
        if not canvas.trigger_metric:
            errors.append("트리거 지표가 정의되지 않았습니다")
        
        # 지급 구조 검증
        limit_struct = canvas.limit_structure
        if limit_struct.payout_curve.base_amount <= 0:
            errors.append("기본 지급액이 0보다 커야 합니다")
        
        if limit_struct.payout_curve.max_payout < limit_struct.payout_curve.base_amount:
            errors.append("최대 지급액이 기본 지급액보다 커야 합니다")
        
        # LLM 기반 논리적 검증
        if not errors:
            llm_validation = await self._llm_validate_canvas(canvas)
            if not llm_validation["valid"]:
                errors.extend(llm_validation["issues"])
        
        return len(errors) == 0, errors
    
    async def _llm_validate_canvas(self, canvas: PerilCanvas) -> Dict:
        """LLM을 사용한 Canvas 논리적 검증"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
당신은 보험 전문가입니다. 주어진 보험 상품 설계의 논리적 일관성을 검토해주세요.

다음 JSON 형식으로 응답하세요:
{
    "valid": true/false,
    "issues": ["문제점1", "문제점2"],
    "suggestions": ["개선사항1", "개선사항2"]
}

검토 기준:
1. 트리거 지표와 위험 타입의 적합성
2. 지급 구조의 합리성
3. 시장에서의 수용 가능성
4. 도덕적 해이 방지
"""),
            ("human", """
위험 타입: {peril}
트리거 지표: {trigger_metric}
임계값: {threshold} {unit}
최대 지급액: ${max_payout:,.0f}
지급 곡선: {curve_type}
""".format(
                peril=canvas.peril,
                trigger_metric=canvas.trigger_metric,
                threshold=canvas.limit_structure.trigger_condition.threshold,
                unit=canvas.limit_structure.trigger_condition.unit,
                max_payout=canvas.limit_structure.payout_curve.max_payout,
                curve_type=canvas.limit_structure.payout_curve.curve_type
            ))
        ])
        
        try:
            messages = prompt.format_messages()
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            # Fallback: 기본 검증 통과
            return {"valid": True, "issues": [], "suggestions": []}


# 편의 함수들
async def generate_canvas(user_input: str) -> PerilCanvas:
    """간편한 Canvas 생성 함수"""
    generator = PerilCanvasGenerator()
    return await generator.generate_canvas_from_input(user_input)


async def validate_canvas(canvas: PerilCanvas) -> Tuple[bool, List[str]]:
    """간편한 Canvas 검증 함수"""
    generator = PerilCanvasGenerator()
    return await generator.validate_canvas(canvas)