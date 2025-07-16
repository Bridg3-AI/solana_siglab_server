# Solana SigLab Agents 구현 계획

## 개요

Solana SigLab Server의 `agents` 모듈은 LangGraph 프레임워크를 활용한 LMM(Large Multimodal Model) 기반 에이전트로, 파라메트릭 보험 상품 개발 및 자동 보험금 지급을 위한 지능형 에이전트 시스템입니다.

### 파라메트릭 보험 워크플로우
1. **요청 단계**: 유저가 파라메트릭 보험 대상 이벤트에 대하여 요청
2. **분석 및 상품 개발**: AI 에이전트가 대상 이벤트에 대해 손해율을 산정하고 수익성 있는 파라메트릭 보험 상품을 개발 후 판매
3. **자동 지급**: 사전 지정된 조건 충족 시 스마트 컨트랙트로 토큰을 보험금으로 유저에게 지급

## 목표

파라메트릭 보험 상품 개발 및 자동 지급을 위한 지능형 에이전트 시스템 구축:
- 보험 이벤트 데이터를 수집·정제·해석하여 손해율 산정
- 위험 평가 및 보험료 산정 도구를 활용한 수익성 분석
- 스마트 컨트랙트 조건 검증 및 자동 보험금 지급 트리거
- 완전 자동화된 파라메트릭 보험 운영 파이프라인 구현

## 1. 에이전트 전반 구조

### 계층별 구성요소

| 계층 | 구성요소 | 주요 책임 |
|------|----------|-----------|
| ① Planner (LMM) | GPT-4.1 / Gemini 2.5 class LMM | 사용자의 보험 요청 → "손해율 산정 및 상품 개발 계획" 생성 |
| ② Tool Router | LangGraph function-calling 라우터 | Planner가 호출한 함수를 보험 분석 및 블록체인 도구로 매핑 |
| ③ Execution Layer | Python + FastAPI 마이크로서비스 | - 보험 이벤트 데이터 수집 API<br>- 손해율 산정 모델<br>- 보험료 계산 엔진<br>- 스마트 컨트랙트 인터페이스 |
| ④ Memory / KB | Vector DB + Conversation Memory | 과거 보험 이벤트 유사도 검색, 손해율 히스토리 조회 |
| Ⅴ Validation Guard | 검증 체인 + 정책엔진 | 결과 정합성(주소 형식·네트워크 검증) 체크 & 에이전트 재시도 |
| Ⅵ Audit Trail | Prompt/Action/Result 로그 | 모델 거버넌스·블록체인 분석 보고서 자동 생성 |

### 프레임워크 선택 근거
LangGraph는 2025년형 오픈소스 프레임워크로 계획→행동→관찰 루프와 도구 타입 세이프티가 성숙해 파라메트릭 보험 워크플로우 자동화에 최적화됨

## 2. Tool 카탈로그 (파라메트릭 보험 도구)

| Tool ID | 엔드포인트 | I/O 예시 | 설명 |
|---------|------------|----------|------|
| `insurance.collect_event_data` | `/events/collect` | (event_type, params) → 이벤트 데이터 | 보험 이벤트 데이터 수집 |
| `insurance.calculate_loss_ratio` | `/analysis/loss_ratio` | (event_data) → 손해율 | 손해율 산정 |
| `insurance.assess_risk` | `/analysis/risk` | (event_params) → 위험도 | 위험 평가 |
| `insurance.calculate_premium` | `/pricing/premium` | (risk_data) → 보험료 | 보험료 계산 |
| `insurance.create_product` | `/products/create` | (product_specs) → 상품 정보 | 보험 상품 생성 |
| `insurance.validate_conditions` | `/contracts/validate` | (conditions) → 검증 결과 | 보험금 지급 조건 검증 |
| `blockchain.deploy_contract` | `/contracts/deploy` | (contract_data) → 컨트랙트 주소 | 스마트 컨트랙트 배포 |
| `blockchain.trigger_payout` | `/contracts/payout` | (contract_addr, amount) → 거래 해시 | 보험금 자동 지급 |
| `report.gen_insurance` | `/report/insurance` | (product_data) → PDF | 보험 상품 보고서 생성 |

각 Tool 함수 시그니처는 LMM 시스템 프롬프트에 function schema로 주입해 자연어 보험 요청 → 함수 호출로 작동

## 3. 에이전트 Reasoning Loop (pseudo-prompt)

```
System:
You are Solana SigLab Insurance Agent. Available tools: insurance.collect_event_data, insurance.calculate_loss_ratio, insurance.create_product, ...

User:
"태풍으로 인한 농작물 피해 보험 상품을 개발해주세요."

--- Planner 체인 출력 예 ---
1. Collect typhoon event data (insurance.collect_event_data)
2. Calculate historical loss ratio for typhoon events
3. Assess risk factors for agricultural damage
4. Calculate appropriate premium (insurance.calculate_premium)
5. Create insurance product (insurance.create_product)
6. Deploy smart contract (blockchain.deploy_contract)
7. Generate product report (report.gen_insurance)
```

## 4. 모델·데이터 파이프라인 세부

| 단계 | 구현 포인트 |
|------|-------------|
| 데이터 인제스트 | 외부 API → 보험 이벤트 실시간 데이터 수집 |
| 피처링 Tool | Execution Layer에서 이벤트 데이터 → 위험 평가 피처 |
| 분석 모델 | ML 기반 손해율 예측 및 위험도 분석 |
| 온라인 러닝 | 실시간 보험 청구 데이터로 모델 업데이트 |
| 안전장치 | 보험 조건 검증, 지급 한도 체크 |

## 5. 품질·거버넌스

| 항목 | 메트릭 | SLO |
|------|--------|-----|
| 손해율 예측 정확도 | > 85% (과거 데이터 기준) |
| 보험료 산정 정확도 | > 90% (수익성 기준) |
| Tool 호출 실패율 | < 1% |
| 자동 재시도 한계 | 3회 |
| 설명 가능성 | 95% "Why?" 쿼리 응답 성공 |
| 보험금 지급 정확도 | > 99% (조건 충족 시) |

### A/B 안전 가드
신규 모델은 트래픽 10%→25%→50% 단계별 확대, 오류 발생 시 즉시 롤백

## 6. DevOps·MLOps 파이프라인

- **코드**: monorepo (Firebase Functions + LangGraph)
- **CI/CD**: GitHub Actions → Firebase Deploy
- **Observability**: Firebase Logging + 구조화된 로깅
- **Security**: Firebase Auth + Input Validation

## 7. 실행 로드맵

| Sprint | 목표 | 산출물 |
|--------|------|--------|
| S1 | 보험 Tool API 3종 PoC | collect_event_data, calculate_loss_ratio, assess_risk |
| S2 | Planner-Router 체인 통합 | 보험 전용 LMM Prompt template, function schema |
| S3 | 보험 Guard rails & Audit Trail | 보험 정책엔진, 전량 보험 거래 로그 |
| S4 | 스마트 컨트랙트 연동 | deploy_contract, trigger_payout, validate_conditions |

## 8. 현재 구현 상태

### 기존 구조 (v1.0)
```
agents/
├── __init__.py          # 기본 에이전트 exports
├── agent.py            # 메인 에이전트 구현
├── langgraph.json      # LangGraph 설정
├── memory.py           # 대화 메모리 관리
└── utils/              # 유틸리티
    ├── state.py        # 상태 정의
    ├── tools.py        # Solana 도구들
    └── nodes.py        # 그래프 노드 함수들
```

### 목표 구조 (LMM Agent)
```
agents/
├── core/               # 핵심 에이전트 로직
│   ├── planner.py     # LMM 기반 계획 수립
│   ├── router.py      # 도구 라우팅
│   └── executor.py    # 실행 레이어
├── tools/             # 보험 도구 확장
│   ├── insurance.py   # 보험 분석 도구
│   ├── blockchain.py  # 블록체인 인터페이스
│   ├── analytics.py   # 손해율 분석 도구
│   └── reporting.py   # 보험 보고서 생성
├── memory/            # 메모리 시스템
│   ├── vector_store.py # 벡터 검색
│   └── conversation.py # 대화 메모리
├── validation/        # 검증 시스템
│   ├── guards.py      # 안전 가드
│   └── policies.py    # 정책 엔진
└── monitoring/        # 모니터링
    ├── audit.py       # 감사 로그
    └── metrics.py     # 성능 메트릭
```
