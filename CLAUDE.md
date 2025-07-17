<guide>
<system_prompt_directives><![CDATA[
당신은 코드 생성 AI 에이전트입니다.
KISS(Keep It Simple, Stupid) 원칙을 준수하여 가능한 한 단순하고 명확하게 작성하십시오.
기존 아키텍처·디자인 패턴·프로젝트 목적을 항상 최우선으로 고려하십시오.
불필요한 파일이나 코드를 절대 생성하지 마십시오.
모든 작업 전에 구체적인 구현 계획을 작성하고, 그 계획에 대해 승인 및 피드백을 반드시 받으십시오.
계획이 승인될 때까지 실제 코드를 출력하지 마십시오.
]]></system_prompt_directives>

<architecture_description><![CDATA[
프로젝트는 크게 두 부분으로 구성됩니다:
(1) /firebase  : Node 18 기반 Firebase Functions (TypeScript/JavaScript)
(2) /src       : Python 3.11 기반 LangChain·LangGraph 서비스 레이어
Python 영역 디렉터리: api/, config/, models/, services/, utils/, tests/
Node(Firebase) 영역은 functions/** 내부에서 트리거별(HTTP, Auth, Schedule) 파일로 분리합니다.
]]></architecture_description>

<python_standards><![CDATA[
- PEP 8 준수. 타입 힌트 필수.
- 비동기 함수 우선(async/await).
- 의존성은 src/requirements.txt에 명시. 새 패키지 추가 시 버전 고정.
- 예외는 custom Error 클래스로 래핑하여 api 층에서 JSON 형태로 반환.
]]></python_standards>

<typescript_standards><![CDATA[
- ESLint airbnb-base 스타일 가이드 준수.
- Cloud Function 1개당 파일 1개. 공용 로직은 /firebase/lib/* 로 분리.
- await/async 사용, 콜백 금지.
]]></typescript_standards>

<testing_docs>새 기능 추가 시 pytest·Firebase emulator 테스트 필수, 공개 함수·클래스에 한·영 docstring/JSDoc 작성</testing_docs>
<git_convention>Conventional Commits 형식(feat:, fix:, chore: 등)을 사용</git_convention>

<project_overview><![CDATA[
이 프로젝트는 Solana 메인넷/테스트넷에 배포된 스마트 컨트랙트를 통해 파라메트릭 보험 상품을 자동화합니다.
Solana의 고성능 TPS와 저비용 수수료는 실시간 보험금 지급 트리거에 적합합니다.
]]></project_overview>

<parametric_insurance_workflow><![CDATA[
1. 사용자 이벤트 요청 수신 → 에이전트가 보험 상품 설계
2. Anchor 기반 스마트 컨트랙트 배포(`deploy_contract` Tool)
3. 오라클/데이터 피드로 조건 충족 여부 모니터링
4. 조건 만족 시 `trigger_payout` Tool 호출로 토큰 전송
]]></parametric_insurance_workflow>

<agent_tools><![CDATA[
- anchorpy: Solana Anchor 컨트랙트 인터페이스
- solana-py: RPC 호출·트랜잭션 서명
- aiosol: Async Solana API 래퍼
- spl.token: 토큰 발행·전송 관리
]]></agent_tools>

<security_considerations><![CDATA[
• 컨트랙트 업그레이드 권한 제한(Upgradeable = false 또는 multisig)
• Oracle 조작 방지를 위해 체인링크·Pyth 분산 피드 사용
• 보험금 지급 한도·재시도 횟수에 대한 on-chain Guard 레이어 적용
]]></security_considerations>

<compliance_notes><![CDATA[
본 파라메트릭 보험 모델은 현지 규제(FinTech Sandbox 등)를 고려하여 설계되어야 하며, 모든 스마트 컨트랙트 코드는 오픈소스로 감사 가능합니다.
]]></compliance_notes>

<langgraph_overview><![CDATA[
LangGraph는 Graph-of-Thought(Plan→Act→Observe) 패러다임을 지원하는 프레임워크로, 순수 비동기 노드·불변 상태·타입 안전 도구 호출을 특징으로 합니다.
]]></langgraph_overview>

<langgraph_core_concepts>Graph-of-Thought, Node=pure async funcs, Immutable State, Typed Tools</langgraph_core_concepts>

<langgraph_principles><![CDATA[
P1 단일 책임 | 노드는 하나의 도메인 책임만 수행
P2 Immutable State | state 변형 금지, 새 객체 리턴
P3 타입 안전 | I/O를 pydantic 모델로 정의
P4 장애 허용 | 재시도/타임아웃 설정
P5 도구 스키마 | @tool 데코레이터로 JSON schema 명시
P6 관찰 가능성 | structlog 기반 노드별 logging
P7 테스트 우선 | pytest 커버리지 ≥ 90%
]]></langgraph_principles>

<directory_template><![CDATA[
agents/
├── core/            # planner.py, router.py, executor.py
├── tools/           # insurance.py, blockchain.py, reporting.py
├── memory/          # vector_store.py, conversation.py
├── validation/      # guards.py, policies.py
└── tests/           # test_nodes.py, test_graph.py
]]></directory_template>

<state_py><![CDATA[
from pydantic import BaseModel
class InsuranceState(BaseModel):
    request: str
    event_data: dict | None = None
    loss_ratio: float | None = None
]]></state_py>

<tools_insurance_py><![CDATA[
from langchain_core.tools import tool

@tool
async def collect_event_data(event_type: str) -> dict:
    """Collect historical event data for the given event type."""
    ...
]]></tools_insurance_py>

<executor_py><![CDATA[
from langgraph.graph import StateGraph
from .state import InsuranceState
from .tools.insurance import collect_event_data

graph = StateGraph(InsuranceState)
graph.add_node("collect", collect_event_data)
graph.set_entry_point("collect")
app = graph.compile()
]]></executor_py>

<ci_cd>pytest · ruff · mypy --strict 통과 및 LangGraph 스냅샷 회귀 테스트를 GitHub Actions로 검증</ci_cd>
</guide>
