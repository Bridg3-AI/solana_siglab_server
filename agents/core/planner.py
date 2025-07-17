"""Planner node for converting user messages to structured plans"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .state import AgentState
from .config import get_config


# LLM 인스턴스 (지연 초기화)
_llm = None

def get_llm_instance():
    """Get LLM instance with lazy initialization"""
    global _llm
    if _llm is None:
        config = get_config()
        _llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=config.openai_api_key
        )
    return _llm

# 프롬프트 템플릿 정의
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
당신은 파라메트릭 보험 상품 설계를 위한 계획 수립 전문가입니다.
사용자의 자연어 요청을 분석하여 구체적인 보험 상품 계획을 생성해야 합니다.

다음 형식으로 응답해주세요:
1. 이벤트 타입: (예: typhoon, flight_delay, earthquake)
2. 보험 조건: (구체적인 트리거 조건)
3. 보상 내용: (지급 조건 및 금액)
4. 데이터 소스: (필요한 데이터 출처)
5. 위험 평가: (예상 손해율 계산을 위한 요소)

반드시 한국어로 응답하고, 실제 구현 가능한 수준의 구체적인 계획을 제시하세요.
"""),
    ("human", "{user_input}")
])

# 체인 구성 함수
def get_planner_chain():
    """Get planner chain with LLM"""
    return PLANNER_PROMPT | get_llm_instance()


async def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Planner node: Convert user messages to structured plan
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with generated plan
    """
    # 최신 사용자 메시지 추출
    if not state.get("messages"):
        return {"plan": "사용자 메시지가 없습니다."}
    
    # 마지막 메시지에서 사용자 입력 추출
    last_message = state["messages"][-1]
    user_input = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
    
    # 이벤트 타입 추출 (간단한 키워드 매칭)
    event_type = extract_event_type(user_input)
    
    try:
        # LLM 호출하여 계획 생성
        llm = get_llm_instance()
        messages = PLANNER_PROMPT.format_messages(user_input=user_input)
        response = await llm.ainvoke(messages)
        plan = response.content
        
        # 기존 상태 유지하면서 업데이트
        updated_state = dict(state)
        updated_state.update({
            "plan": plan,
            "event_type": event_type,
            "messages": state["messages"] + [{"role": "assistant", "content": f"계획 생성됨: {plan[:100]}..."}]
        })
        return updated_state
        
    except Exception as e:
        # Mock plan for testing when LLM fails
        mock_plan = f"""
1. 이벤트 타입: {event_type}
2. 보험 조건: {user_input}에 대한 구체적인 트리거 조건 설정
3. 보상 내용: 이벤트 발생 시 보상금 지급
4. 데이터 소스: 관련 기상청 및 외부 API 데이터
5. 위험 평가: 과거 통계 데이터 기반 손해율 계산
"""
        
        # 기존 상태 유지하면서 업데이트
        updated_state = dict(state)
        updated_state.update({
            "plan": mock_plan,
            "event_type": event_type,
            "messages": state["messages"] + [{"role": "assistant", "content": f"Mock 계획 생성됨 (LLM 오류로 인한 대체)"}]
        })
        return updated_state


def extract_event_type(user_input: str) -> str:
    """
    Extract event type from user input using simple keyword matching
    
    Args:
        user_input: User's natural language input
        
    Returns:
        Detected event type
    """
    user_input_lower = user_input.lower()
    
    # 키워드 매핑
    event_keywords = {
        "typhoon": ["태풍", "태풍우", "허리케인", "cyclone"],
        "flight_delay": ["항공", "비행기", "항공편", "지연", "취소", "flight"],
        "earthquake": ["지진", "earthquake", "진도", "흔들림"],
        "flood": ["홍수", "침수", "물난리", "범람"],
        "drought": ["가뭄", "drought", "메마름", "물부족"],
        "fire": ["화재", "fire", "불", "산불"],
        "weather": ["날씨", "기상", "weather", "악천후"]
    }
    
    # 키워드 매칭
    for event_type, keywords in event_keywords.items():
        if any(keyword in user_input_lower for keyword in keywords):
            return event_type
    
    # 기본값
    return "general"