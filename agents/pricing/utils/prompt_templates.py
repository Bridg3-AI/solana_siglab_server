"""
LangChain 프롬프트 템플릿 유틸리티

안전하고 재사용 가능한 프롬프트 템플릿 관리를 위한 모듈입니다.
JSON 예시와 템플릿 변수 간의 충돌을 방지하고, 
일관된 프롬프트 구조를 제공합니다.
"""

import json
import re
from typing import Dict, List, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


class SafePromptBuilder:
    """안전한 프롬프트 템플릿 빌더"""
    
    @staticmethod
    def escape_json_in_template(template_text: str) -> str:
        """
        템플릿 텍스트에서 JSON 예시의 중괄호를 안전하게 이스케이프
        
        Args:
            template_text: 이스케이프할 템플릿 텍스트
            
        Returns:
            이스케이프된 템플릿 텍스트
        """
        # 더 정교한 JSON 이스케이프 방식
        lines = template_text.split('\n')
        escaped_lines = []
        in_json_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # JSON 블록 시작 감지 - "{{{{" 패턴을 찾음
            if '{{{{' in line:
                in_json_block = True
                escaped_lines.append(line)
                continue
            
            # JSON 블록 끝 감지 - "}}}}" 패턴을 찾음  
            if '}}}}' in line and in_json_block:
                in_json_block = False
                escaped_lines.append(line)
                continue
            
            # JSON 블록 내부가 아니고 JSON 형태로 보이는 라인인지 확인
            if not in_json_block:
                # JSON 라인 감지: 키-값 쌍이 있는 라인
                is_json_line = (
                    ('"' in stripped and ':' in stripped) or
                    (stripped.startswith('{') and ':' in stripped) or
                    (stripped.endswith('}') and ':' in line) or
                    (stripped.startswith('"') and stripped.endswith('",') and ':' in stripped)
                )
                
                # 템플릿 변수 패턴 감지: {variable_name} 형태
                # 단일 템플릿 변수이거나 템플릿 변수가 포함된 텍스트 라인
                import re
                template_var_pattern = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
                has_template_vars = bool(re.search(template_var_pattern, stripped))
                is_pure_json = (
                    ('"' in stripped and ',' in stripped) or
                    (stripped.startswith('{') and stripped.endswith('}') and ':' in stripped)
                )
                is_template_variable = has_template_vars and not is_pure_json
                
                # JSON과 템플릿 변수가 혼재한 경우 선택적 이스케이프
                if is_json_line and not is_template_variable:
                    # 순수 JSON 라인 - 전체 이스케이프
                    escaped_line = line.replace('{', '{{').replace('}', '}}')
                    escaped_lines.append(escaped_line)
                elif has_template_vars and is_json_line:
                    # 혼재 라인 - 템플릿 변수 보호하면서 JSON만 이스케이프
                    import re
                    
                    # 모든 템플릿 변수를 임시 마커로 교체
                    template_var_pattern = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
                    vars_found = re.findall(template_var_pattern, line)
                    temp_line = line
                    temp_markers = {}
                    
                    for i, var in enumerate(vars_found):
                        marker = f"__TEMPLATE_VAR_{i}__"
                        temp_markers[marker] = var
                        temp_line = temp_line.replace(var, marker, 1)  # 첫 번째 발견만 교체
                    
                    # 남은 모든 중괄호를 JSON으로 간주하고 이스케이프
                    escaped_line = temp_line.replace('{', '{{').replace('}', '}}')
                    
                    # 템플릿 변수 복원
                    for marker, var in temp_markers.items():
                        escaped_line = escaped_line.replace(marker, var)
                    
                    escaped_lines.append(escaped_line)
                else:
                    escaped_lines.append(line)
            else:
                # JSON 블록 내부라면 그대로 유지
                escaped_lines.append(line)
        
        return '\n'.join(escaped_lines)
    
    @staticmethod
    def validate_template_variables(template_text: str, variables: List[str]) -> Dict[str, Any]:
        """
        템플릿 변수의 안전성 검증
        
        Args:
            template_text: 검증할 템플릿 텍스트
            variables: 사용될 변수 목록
            
        Returns:
            검증 결과 딕셔너리
        """
        result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # 이미 이스케이프된 JSON 구조 제거하여 실제 템플릿 변수만 추출
        cleaned_text = template_text
        
        # 이중 중괄호로 이스케이프된 JSON 블록 제거
        cleaned_text = re.sub(r'\{\{[^{}]*\}\}', '', cleaned_text)
        
        # 남은 단일 중괄호에서 템플릿 변수 추출
        template_vars = re.findall(r'\{([^{}]+)\}', cleaned_text)
        
        # JSON 키 형태가 아닌 실제 변수명만 필터링
        actual_vars = []
        for var in template_vars:
            # JSON 키 패턴이 아닌 경우만 실제 템플릿 변수로 간주
            if ':' not in var and '"' not in var and not var.strip().startswith('"'):
                actual_vars.append(var.strip())
        
        # 미정의 변수 확인
        undefined_vars = set(actual_vars) - set(variables)
        if undefined_vars:
            result["errors"].append(f"미정의 변수 발견: {list(undefined_vars)}")
            result["is_valid"] = False
        
        # 미사용 변수 확인 - 실제 사용된 변수만 체크
        unused_vars = set(variables) - set(actual_vars)
        if unused_vars:
            result["warnings"].append(f"미사용 변수: {list(unused_vars)}")
        
        return result
    
    @classmethod
    def create_safe_chat_template(
        cls, 
        system_template: str, 
        human_template: str, 
        variables: Optional[List[str]] = None,
        validate_variables: bool = False
    ) -> ChatPromptTemplate:
        """
        안전한 ChatPromptTemplate 생성
        
        Args:
            system_template: 시스템 메시지 템플릿
            human_template: 휴먼 메시지 템플릿
            variables: 사용될 변수 목록 (검증용)
            validate_variables: 변수 검증 활성화 여부
            
        Returns:
            안전하게 구성된 ChatPromptTemplate
        """
        # JSON 이스케이프 적용
        safe_system = cls.escape_json_in_template(system_template)
        safe_human = cls.escape_json_in_template(human_template)
        
        # 변수 검증 (선택사항)
        if variables and validate_variables:
            system_validation = cls.validate_template_variables(safe_system, variables)
            human_validation = cls.validate_template_variables(safe_human, variables)
            
            # 검증 결과 로깅 (오류만 출력, 경고는 생략)
            if not system_validation["is_valid"]:
                print(f"⚠️ [TEMPLATE] 시스템 템플릿 검증 실패: {system_validation['errors']}")
            if not human_validation["is_valid"]:
                print(f"⚠️ [TEMPLATE] 휴먼 템플릿 검증 실패: {human_validation['errors']}")
        
        return ChatPromptTemplate.from_messages([
            ("system", safe_system),
            ("human", safe_human)
        ])


class PriorExtractionPrompts:
    """Prior 추출용 표준화된 프롬프트 모음"""
    
    # 공통 JSON 응답 형식 안내
    JSON_RESPONSE_INSTRUCTION = """
CRITICAL: Respond with pure JSON format only. No code blocks, no markdown, no additional explanations. 
Output must be a single, complete, valid JSON object that can be parsed directly.
"""
    
    # 빈도 Prior 프롬프트
    FREQUENCY_SYSTEM_TEMPLATE = """You are an actuarial risk modeling expert with deep knowledge of catastrophe modeling and historical event patterns.

{json_instruction}

Response format:
{{{{
    "distribution": "negative_binomial",
    "parameters": {{{{
        "r": 2.5,
        "p": 0.75
    }}}},
    "percentiles": {{{{
        "5th": 0.0,
        "50th": 1.0,
        "95th": 4.0
    }}}},
    "sources": ["Source1", "Source2"],
    "confidence": 0.85,
    "rationale": "Brief explanation of parameter selection"
}}}}

Key requirements:
1. Use Negative-Binomial(r, p) for overdispersed count data
2. Provide 5th, 50th, 95th percentiles for uncertainty quantification
3. Name at least 2 authoritative meteorological/industry sources
4. Confidence level based on data quality and historical precedent"""
    
    FREQUENCY_HUMAN_TEMPLATE = """Event type: {peril}
Region: {region}
Context: Annual frequency modeling for parametric insurance
Data sources mentioned: {data_sources}

Provide the Negative-Binomial parameters for annual event count, considering:
- Historical frequency patterns in the specified region
- Climate change trends and evolving risk patterns
- Seasonal clustering and return periods
- Regional vulnerability and exposure characteristics"""
    
    # 심도 Prior 프롬프트
    SEVERITY_SYSTEM_TEMPLATE = """You are an expert in catastrophe modeling and extreme value statistics.

{json_instruction}

Response format:
{{{{
    "distribution": "{distribution}",
    "parameters": {{{{
        "mu": 2.1,
        "sigma": 0.6
    }}}},
    "percentiles": {{{{
        "5th": 3.2,
        "50th": 8.1,
        "95th": 25.4
    }}}},
    "metric_unit": "{unit}",
    "sources": ["Source1", "Source2"],
    "confidence": 0.82,
    "rationale": "Brief explanation of distribution choice and parameters"
}}}}

Distribution guidance:
- LogNormal: For multiplicative processes, positive skewness
- Gamma: For positive continuous values with flexible shape
- Exponential: For memory-less waiting times
- Normal: For symmetric, bell-shaped distributions"""
    
    SEVERITY_HUMAN_TEMPLATE = """Event type: {peril}
Trigger metric: {metric}
Unit: {unit}
Recommended distribution: {distribution}

Provide the {distribution} distribution parameters for the severity of {metric} when {peril} events occur.

Consider:
- Physical constraints and realistic ranges for {metric}
- Historical extreme values and return periods
- Fat-tail characteristics for catastrophic events
- Measurement precision and data quality factors"""
    
    # 티켓 기반 지표 특화 프롬프트
    SEVERITY_TICKETS_HUMAN_TEMPLATE = """Event type: {peril}
Trigger metric: {metric}
Unit: {unit}
Recommended distribution: {distribution}

CRITICAL: For ticket-based metrics, ensure realistic venue capacity constraints.
{ticket_guidance}

Provide the {distribution} distribution parameters for {metric} severity in {peril} scenarios.

Requirements:
{requirements}"""
    
    @classmethod
    def get_frequency_prompt(cls) -> ChatPromptTemplate:
        """빈도 Prior 추출용 안전한 프롬프트 템플릿"""
        return SafePromptBuilder.create_safe_chat_template(
            system_template=cls.FREQUENCY_SYSTEM_TEMPLATE.format(
                json_instruction=cls.JSON_RESPONSE_INSTRUCTION
            ),
            human_template=cls.FREQUENCY_HUMAN_TEMPLATE,
            variables=["peril", "region", "data_sources"],
            validate_variables=False  # 검증 비활성화
        )
    
    @classmethod
    def get_severity_prompt(cls, distribution: str, unit: str) -> ChatPromptTemplate:
        """심도 Prior 추출용 안전한 프롬프트 템플릿"""
        return SafePromptBuilder.create_safe_chat_template(
            system_template=cls.SEVERITY_SYSTEM_TEMPLATE.format(
                json_instruction=cls.JSON_RESPONSE_INSTRUCTION,
                distribution=distribution,
                unit=unit
            ),
            human_template=cls.SEVERITY_HUMAN_TEMPLATE,
            variables=["peril", "metric", "unit", "distribution"],
            validate_variables=False  # 검증 비활성화
        )
    
    @classmethod
    def get_severity_tickets_prompt(cls, distribution: str, unit: str, metric: str) -> ChatPromptTemplate:
        """티켓 기반 지표용 특화 심도 Prior 프롬프트"""
        
        # 티켓 지표별 특화 안내
        if "percentage" in metric or "percent" in unit:
            ticket_guidance = """Typical ranges: Low sales (20-40%), Medium sales (50-70%), High sales (80-95%).
Concert cancellations often occur when sales are high (70%+), so ensure distribution reflects this."""
            requirements = """- Values must be in percentage range (0-100)
- 50th percentile should be around 60-80% for realistic cancellation scenarios
- 95th percentile should approach 90-95% to capture high-ticket-sales cancellations
- Parameters should generate values that can trigger the insurance payout
- Consider seasonal patterns and market dynamics"""
        else:
            ticket_guidance = """Typical venue sizes: Small venues (500-2000), Medium venues (2000-10000), Large venues (10000-50000).
Concert cancellations are insured when significant ticket sales occur (1000+ tickets)."""
            requirements = """- Values should represent realistic ticket sales numbers
- 50th percentile should be around 2000-5000 tickets for medium venues
- 95th percentile should reach 10000-20000 for large venue scenarios
- Parameters should generate values that can trigger insurance payouts (>1000 tickets)
- Consider venue capacity constraints and market demand patterns"""
        
        return SafePromptBuilder.create_safe_chat_template(
            system_template=cls.SEVERITY_SYSTEM_TEMPLATE.format(
                json_instruction=cls.JSON_RESPONSE_INSTRUCTION,
                distribution=distribution,
                unit=unit
            ),
            human_template=cls.SEVERITY_TICKETS_HUMAN_TEMPLATE.format(
                peril="{peril}",
                metric="{metric}",
                unit="{unit}",
                distribution="{distribution}",
                ticket_guidance=ticket_guidance,
                requirements=requirements
            ),
            variables=["peril", "metric", "unit", "distribution"],
            validate_variables=False  # 검증 비활성화
        )


class PerilCanvasPrompts:
    """Peril Canvas 생성용 표준화된 프롬프트 모음"""
    
    # Peril 정보 추출 프롬프트
    PERIL_EXTRACTION_SYSTEM = """You are an insurance risk analyzer. Extract information from user input and respond with valid JSON only.

CRITICAL: Your response must be a single, complete, valid JSON object. Do not include any text before or after the JSON.

STRICT KEYWORD MATCHING RULES:
1. If input contains "콘서트" OR "공연" OR "연주회" → MUST use "concert_cancellation"
2. If input contains "취소" AND ("콘서트" OR "공연") → MUST use "concert_cancellation"  
3. If input contains "게임" OR "서버" → use "game_server_downtime"
4. If input contains "태풍" → use "typhoon"
5. If input contains "지진" → use "earthquake"
6. If input contains "항공" OR "비행기" → use "flight_delay"

CRITICAL: The word "콘서트" (concert) ALWAYS maps to "concert_cancellation", never "unknown".

Required format:
{{{{
    "peril": "risk_type_in_lowercase_english",
    "description": "Brief Korean description",
    "region": "Global",
    "coverage_period": "annual", 
    "industry": "general"
}}}}

MANDATORY EXAMPLES:
- "콘서트 취소 보험" → {{{{"peril": "concert_cancellation", "description": "콘서트 취소 보험", "region": "Global", "coverage_period": "annual", "industry": "general"}}}}
- "콘서트 보험" → {{{{"peril": "concert_cancellation", "description": "콘서트 관련 보험", "region": "Global", "coverage_period": "annual", "industry": "general"}}}}
- "태풍 보험" → {{{{"peril": "typhoon", "description": "태풍 피해 보험", "region": "Korea", "coverage_period": "annual", "industry": "general"}}}}"""
    
    PERIL_EXTRACTION_HUMAN = "Input: {user_input}"
    
    @classmethod
    def get_peril_extraction_prompt(cls) -> ChatPromptTemplate:
        """Peril 정보 추출용 안전한 프롬프트"""
        return SafePromptBuilder.create_safe_chat_template(
            system_template=cls.PERIL_EXTRACTION_SYSTEM,
            human_template=cls.PERIL_EXTRACTION_HUMAN,
            variables=["user_input"],
            validate_variables=False  # 검증 비활성화
        )