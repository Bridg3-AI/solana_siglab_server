# Solana SigLab Agents V0.1 Implementation Plan

본 문서는 Solana SigLab 보험 에이전트의 **매우 단순화된 초기 버전(V0.1)** 을 구현하기 위한 구체적인 계획을 제시합니다. V0.1은 LangGraph 기반 에이전트의 핵심 개념을 검증하는 최소 실행 가능 제품(MVP) 수준으로 정의됩니다.

---

## 1. 목표(Scope)

V0.1에서 달성하고자 하는 최소 기능은 아래와 같습니다.

1. **사용자 요청 수신**: "항공편 지연 관련 보험을 만들어줘" 와 같은 자연어 입력을 수신.
2. **플래너 노드**: LLM(GPT-4o) 를 이용해 입력을 구체화(명세화)하고 단계형 Plan을 생성. 예) "특정일에 태풍으로 항공편이 2시간 이상 지연되거나 취소되면 보상"과 같은 보험 이벤트·조건·보상 명세를 도출.
3. **Tool Router 노드**: Plan 을 기반으로 두 개의 핵심 Tool 호출 파라미터 구성.
4. **Executor 노드**: Tool 스텁(stub) 함수 실행 후 결과 반환.
5. **출력**: 손해율(loss ratio) 계산 결과를 사용자에게 JSON 형태로 응답.

> 🛠️ **Out-of-Scope**: 보험료 계산, 스마트 컨트랙트 배포, 검증 가드, 메모리, 벡터 DB, 리포팅 등은 V0.1 범위에 포함되지 않습니다.

---

## 2. LangGraph 설계 (Minimal)

### 2.1 AgentState 타입
```python
class AgentState(TypedDict):
    messages: list[dict]   # 대화 내역
    plan: str             # Planner 생성 Plan
    result: dict | None   # Tool 실행 결과
```

### 2.2 그래프 노드
| 노드 ID | 역할 | 파일 |
|---------|------|------|
| `planner` | 사용자 메시지를 단계형 Plan 으로 변환 | `agents/core/planner.py` |
| `tool_router` | Plan 해석 → Tool 이름·파라미터 추출 | `agents/core/router.py` |
| `executor` | 파라미터에 맞춰 Tool 실행 후 결과 저장 | `agents/core/executor.py` |
| `END` | 그래프 종료 | (LangGraph 내장) |

### 2.3 그래프 정의 예시
```python
from langgraph.graph import StateGraph, END
from .planner import planner_chain
from .router import tool_router
from .executor import executor_layer
from .state import AgentState

graph = StateGraph(AgentState)

graph.add_node("planner", planner_chain)
graph.add_node("tool_router", tool_router)
graph.add_node("executor", executor_layer)

graph.add_edge("planner", "tool_router")
graph.add_edge("tool_router", "executor")

graph.add_edge("executor", END)

agent = graph.compile()
```

---

## 3. Tool 스펙 (V0.1)

| Tool ID | 입력 | 출력 | 설명 |
|---------|------|------|------|
| `insurance.collect_event_data` | `event_type: str` | `event_data: dict` | 이벤트(예: typhoon) 관련 API 호출(모의) |
| `insurance.calculate_loss_ratio` | `event_data: dict` | `loss_ratio: float` | 손해율 산정(모의 계산) |

* **Stub 구현**: 실제 외부 API 대신 고정 값 또는 난수 반환하여 흐름 검증.
* **Function Schema**: LangGraph `add_function` 사용, JSON Schema 로 입력/출력 선언.

---

## 4. 파일/디렉터리 구조 (신규 및 수정)
```
agents/
└── core/
    ├── planner.py      # LLM 호출 체인
    ├── router.py       # 툴 라우팅 로직
    ├── executor.py     # Tool 실행 래퍼
    └── state.py        # AgentState 정의
agents/tools/
    └── insurance.py    # 두 개의 Tool stub
run_agent.py            # CLI 진입점 (예: python run_agent.py "...")
```

---

## 5. 일정(Roadmap)

| 주차 | 작업 항목 | 산출물 |
|------|-----------|--------|
| Week 1 | 프로젝트 스캐폴딩 & 의존성( `langgraph`, `openai`, `pydantic`) 설정 | Poetry/requirements.txt, 디렉터리 구조 |
| Week 1 | Tool stub 2종 구현 (`insurance.py`) | collect_event_data, calculate_loss_ratio |
| Week 2 | Core 노드( planner / router / executor ) 개발 | 각 Python 모듈 |
| Week 2 | LangGraph 그래프 정의 및 컴파일 | `state.py`, 그래프 코드 |
| Week 2 | CLI 스크립트 작성 & 데모 실행 | `run_agent.py`, README 업데이트 |

---

## 6. 수용 기준(Acceptance Criteria)

- `python run_agent.py "태풍 손해율 계산"` 명령 실행 시 JSON 응답 `{ "loss_ratio": <float> }` 출력.
- 모든 유닛 테스트 통과 (`pytest`).
- 실행 시간 10초 이하(LLM 호출 mock).

---

## 7. 향후 확장 포인트

1. Validator 노드 추가하여 Schema/Pydantic 검증.
2. Premium 계산, Product 생성 Tool 통합.
3. 블록체인 배포/지급 기능 연동.
4. 실시간 데이터 API 연결 및 모델 정확도 향상.

---

> V0.1은 **LangGraph 에이전트 아키텍처 학습 및 파이프라인 검증**을 목적으로 하며, 이후 버전에서 점진적으로 기능을 확장합니다.
