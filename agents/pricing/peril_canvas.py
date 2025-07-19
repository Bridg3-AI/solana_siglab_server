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
from .utils.prompt_templates import PerilCanvasPrompts


class PerilCanvasGenerator:
    """LLM 기반 Peril Canvas 자동 생성기"""
    
    def __init__(self):
        self.config = get_config()
        self._llm = None
    
    @property
    def llm(self) -> ChatOpenAI:
        """지연 초기화된 LLM 인스턴스"""
        if self._llm is None:
            print(f"🔧 [CONFIG] LLM 초기화:")
            print(f"   모델: {self.config.model_name}")
            print(f"   API 키 존재: {bool(self.config.openai_api_key)}")
            print(f"   API 키 첫 10자: {self.config.openai_api_key[:10] if self.config.openai_api_key else 'None'}")
            
            self._llm = ChatOpenAI(
                model=self.config.model_name,
                temperature=0.1,  # 더 낮은 temperature로 일관성 향상
                max_tokens=6000,  # 토큰 수 줄여서 완전한 응답 보장
                api_key=self.config.openai_api_key,
                request_timeout=30,  # 타임아웃 설정
                max_retries=2  # 재시도 설정
            )
            print(f"✅ [CONFIG] LLM 초기화 완료")
        return self._llm
    
    async def generate_canvas_from_input(self, user_input: str) -> PerilCanvas:
        """
        사용자 입력으로부터 Peril Canvas 생성
        
        Args:
            user_input: 사용자의 자연어 입력
            
        Returns:
            생성된 PerilCanvas 객체
        """
        try:
            print(f"📋 [CANVAS] 1단계: 위험 타입 정보 추출 시작...")
            # 1단계: 위험 타입 및 기본 정보 추출
            peril_info = await self._extract_peril_info(user_input)
            print(f"📋 [CANVAS] 1단계 완료: {peril_info}")
            
            print(f"📋 [CANVAS] 2단계: 트리거 지표 추천 시작...")
            # 2단계: 트리거 지표 추천
            trigger_metrics = await self._suggest_trigger_metrics(
                peril_info["peril"], peril_info["description"]
            )
            print(f"📋 [CANVAS] 2단계 완료: {trigger_metrics}")
            
            print(f"📋 [CANVAS] 3단계: 지급 구조 설계 시작...")
            # 3단계: 지급 구조 설계
            payout_structure = await self._design_payout_structure(
                peril_info["peril"], trigger_metrics["primary_metric"]
            )
            print(f"📋 [CANVAS] 3단계 완료: {payout_structure}")
            
            print(f"📋 [CANVAS] 4단계: PerilCanvas 객체 구성 시작...")
            # 4단계: PerilCanvas 객체 구성
            canvas = self._build_peril_canvas(peril_info, trigger_metrics, payout_structure)
            print(f"📋 [CANVAS] 4단계 완료: {type(canvas)}")
            return canvas
            
        except Exception as e:
            print(f"❌ [CANVAS] Canvas 생성 중 오류: {str(e)}")
            print(f"❌ [CANVAS] 오류 타입: {type(e)}")
            import traceback
            traceback.print_exc()
            raise e
    
    async def _extract_peril_info(self, user_input: str) -> Dict[str, str]:
        """사용자 입력에서 위험 타입 및 기본 정보 추출"""
        
        # 새로운 안전한 템플릿 시스템 사용
        prompt = PerilCanvasPrompts.get_peril_extraction_prompt()
        
        try:
            print(f"🔍 [API] Peril extraction LLM 호출 중... (입력: {user_input})")
            print(f"🔧 [TEMPLATE] 안전한 ChatPromptTemplate 사용")
            
            messages = prompt.format_messages(user_input=user_input)
            response = await self.llm.ainvoke(messages)
            print(f"✅ [API] LLM 응답 성공")
            
            # 강화된 JSON 파싱 로직 사용
            result = self._parse_llm_json_response(response.content, "Peril extraction")
            if result:
                # 필수 필드 검증
                required_fields = ["peril", "description", "region", "coverage_period", "industry"]
                missing_fields = [field for field in required_fields if not result.get(field)]
                
                if missing_fields:
                    print(f"⚠️ [API] 필수 필드 누락: {missing_fields}, fallback 사용")
                    return self._fallback_peril_extraction(user_input)
                
                # 데이터 타입 검증
                if not isinstance(result["peril"], str) or not result["peril"].strip():
                    print(f"⚠️ [API] peril 필드가 유효하지 않음, fallback 사용")
                    return self._fallback_peril_extraction(user_input)
                
                print(f"🎉 [API] 완전한 결과 반환: {result}")
                return result
            else:
                print(f"🔄 [API] JSON 파싱 실패 - Fallback 사용: {user_input}")
                return self._fallback_peril_extraction(user_input)
                
        except Exception as e:
            print(f"❌ [API] LLM 호출 실패: {str(e)}")
            # Fallback: 키워드 기반 매핑
            print(f"🔄 [API] Fallback 사용: {user_input}")
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
            "concert_cancellation": {
                "keywords": ["콘서트", "공연", "연주회", "뮤지컬", "오페라", "concert", "performance", "show"],
                "description": "콘서트 및 공연 취소로 인한 손실",
                "region": "Global"
            },
            "event_cancellation": {
                "keywords": ["이벤트 취소", "행사 취소", "축제 취소", "스포츠 취소", "경기 취소"],
                "description": "각종 이벤트 및 행사 취소로 인한 손실",
                "region": "Global"
            },
            "flight_delay": {
                "keywords": ["항공편 지연", "항공편 취소", "비행기 지연", "flight delay", "flight cancellation"],
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
            ("system", """You are an insurance actuary. Recommend objective and measurable trigger metrics for the given risk.

CRITICAL: Respond with valid JSON only. No markdown, no explanations, just JSON.

Required format:
{{
    "primary_metric": "trigger_metric_in_english",
    "metric_description": "Korean description",
    "unit": "measurement_unit",
    "data_sources": ["source1", "source2"],
    "threshold_guidance": "Korean threshold guidance"
}}

Examples:
- Typhoon: {{"primary_metric": "central_pressure", "unit": "hPa"}}
- Flight delay: {{"primary_metric": "delay_minutes", "unit": "minutes"}}
- Server down: {{"primary_metric": "downtime_minutes", "unit": "minutes"}}"""),
            ("human", "Risk: {peril}\nDescription: {description}")
        ])
        
        try:
            print(f"🔍 [API] 트리거 지표 LLM 호출 중... (위험: {peril})")
            messages = prompt.format_messages(peril=peril, description=description)
            response = await self.llm.ainvoke(messages)
            print(f"✅ [API] 트리거 지표 LLM 응답 성공")
            print(f"🔍 [API] 응답 내용: {response.content}")
            
            # JSON 파싱 (1단계와 동일한 방식)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx+1]
                result = json.loads(json_content)
                print(f"✅ [API] 트리거 지표 JSON 파싱 성공: {result}")
                return result
            else:
                print(f"❌ [API] 트리거 지표 JSON 구조 없음, fallback 사용")
                return self._get_default_trigger_metric(peril)
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"❌ [API] 트리거 지표 LLM 호출 실패: {str(e)}")
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
            "concert_cancellation": {
                "primary_metric": "event_intensity",
                "metric_description": "콘서트 취소 심각도",
                "unit": "scale",
                "data_sources": ["Event Management APIs", "Entertainment Industry Data"],
                "threshold_guidance": "레벨 3 이상에서 지급 시작"
            },
            "event_cancellation": {
                "primary_metric": "event_intensity",
                "metric_description": "이벤트 취소 심각도",
                "unit": "scale", 
                "data_sources": ["Event Management APIs", "Industry Statistics"],
                "threshold_guidance": "레벨 2 이상에서 지급 시작"
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
            ("system", """You are an insurance product designer. Design a reasonable payout structure for the given risk and trigger metric.

CRITICAL: Respond with valid JSON only. No markdown, no explanations, just JSON.

Required format:
{{
    "curve_type": "linear",
    "threshold": 3.0,
    "operator": ">=",
    "base_amount": 5000.0,
    "max_payout": 500000.0,
    "multiplier": 5000.0,
    "deductible": 0.0,
    "rationale": "Korean explanation"
}}

Design principles:
1. Threshold should be proportional to event severity
2. Maximum payout should be market-acceptable
3. Payout curve should reflect risk characteristics"""),
            ("human", "Risk: {peril}\nTrigger metric: {metric}")
        ])
        
        try:
            print(f"🔍 [API] 지급 구조 LLM 호출 중... (위험: {peril}, 지표: {metric})")
            messages = prompt.format_messages(peril=peril, metric=metric)
            response = await self.llm.ainvoke(messages)
            print(f"✅ [API] 지급 구조 LLM 응답 성공")
            print(f"🔍 [API] 응답 내용: {response.content}")
            
            # JSON 파싱 (1단계와 동일한 방식)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx+1]
                result = json.loads(json_content)
                print(f"✅ [API] 지급 구조 JSON 파싱 성공: {result}")
                return result
            else:
                print(f"❌ [API] 지급 구조 JSON 구조 없음, fallback 사용")
                return self._get_default_payout_structure(peril)
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"❌ [API] 지급 구조 LLM 호출 실패: {str(e)}")
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
            "concert_cancellation": {
                "curve_type": "step",
                "threshold": 3.0,
                "operator": ">=",
                "base_amount": 5000.0,
                "max_payout": 500000.0,
                "multiplier": 5000.0,
                "deductible": 0.0,
                "rationale": "콘서트 취소 심각도에 따른 단계적 지급"
            },
            "event_cancellation": {
                "curve_type": "step",
                "threshold": 2.0,
                "operator": ">=",
                "base_amount": 3000.0,
                "max_payout": 300000.0,
                "multiplier": 3000.0,
                "deductible": 0.0,
                "rationale": "이벤트 취소 심각도에 따른 단계적 지급"
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
    
    def _parse_llm_json_response(self, content: str, context: str) -> Optional[Dict]:
        """
        LLM 응답에서 JSON을 안전하게 파싱
        
        Args:
            content: LLM 응답 내용
            context: 로깅을 위한 컨텍스트 (예: "Peril extraction", "Trigger metrics")
            
        Returns:
            파싱된 JSON 딕셔너리 또는 None
        """
        try:
            # 기본 정리
            content = content.strip()
            
            # 코드 블록 제거
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # 이중 중괄호 처리 - LangChain 템플릿에서 이스케이프된 것을 원래대로
            content = content.replace('{{', '{').replace('}}', '}')
            
            # JSON 추출 - 첫 번째 { 부터 마지막 } 까지
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx+1]
                print(f"🔍 [API] {context} JSON 추출: {json_content}")
                
                # JSON 파싱 시도
                result = json.loads(json_content)
                print(f"✅ [API] {context} JSON 파싱 성공: {result}")
                return result
            else:
                print(f"❌ [API] {context} JSON 구조를 찾을 수 없음")
                return None
                
        except json.JSONDecodeError as e:
            print(f"❌ [API] {context} JSON 파싱 실패: {str(e)}")
            print(f"🔍 [API] 파싱 실패 내용: {content[:500]}...")
            return None
        except Exception as e:
            print(f"❌ [API] {context} 예상치 못한 오류: {str(e)}")
            return None


# 편의 함수들
async def generate_canvas(user_input: str) -> PerilCanvas:
    """간편한 Canvas 생성 함수"""
    generator = PerilCanvasGenerator()
    return await generator.generate_canvas_from_input(user_input)


async def validate_canvas(canvas: PerilCanvas) -> Tuple[bool, List[str]]:
    """간편한 Canvas 검증 함수"""
    generator = PerilCanvasGenerator()
    return await generator.validate_canvas(canvas)