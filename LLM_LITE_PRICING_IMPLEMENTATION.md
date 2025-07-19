# LLM-Lite Parametric Pricing 구현 계획

## 📋 프로젝트 개요

**목표**: 실측 데이터 없는 이벤트들에 대해 LLM만으로 파라메트릭 보험 상품을 자동 설계하는 시스템 구현

**기반**: modify_plan.md의 "LLM-Lite Parametric Pricing" 방법론을 현재 LangGraph 기반 코드베이스에 통합

## 🏗️ 전체 아키텍처

```
user_input → peril_canvas → prior_extraction → scenario_generation → monte_carlo_pricing → pricing_report
```

---

## 📅 Phase 1: Core Infrastructure (Peril Canvas + Prior Extraction)

### 1.1 디렉토리 구조 생성
- [ ] `agents/pricing/` 디렉토리 생성
- [ ] `agents/pricing/__init__.py` 생성
- [ ] `agents/pricing/models/` 서브디렉토리 생성

### 1.2 Peril Canvas 시스템 구현
- [ ] `agents/pricing/peril_canvas.py` 생성
  - [ ] `PerilCanvas` 데이터 모델 정의
  - [ ] `PayoutCurve` 데이터 모델 정의
  - [ ] `PerilCanvasGenerator` 클래스 구현
  - [ ] LLM 기반 canvas 자동 생성 로직
  - [ ] 트리거 지표 추천 시스템
  - [ ] 지급 구조 설계 로직

### 1.3 Prior Extraction 시스템 구현
- [ ] `agents/pricing/prior_extraction.py` 생성
  - [ ] `PriorExtractor` 클래스 구현
  - [ ] `FrequencyPrior` 데이터 모델 정의
  - [ ] `SeverityPrior` 데이터 모델 정의
  - [ ] 확률-주도 프롬프팅 템플릿 작성
  - [ ] LLM 기반 분포 모수 추출 로직
  - [ ] Self-Critique Loop 구현

### 1.4 공통 모델 정의
- [ ] `agents/pricing/models/__init__.py` 생성
- [ ] `agents/pricing/models/base.py` 생성
  - [ ] 기본 Pydantic 모델들 정의
  - [ ] 공통 검증 로직
  - [ ] 타입 정의

---

## 📅 Phase 2: Pricing Engine (Scenario Generator + Monte Carlo Pricer)

### 2.1 Synthetic Scenario Generator 구현
- [ ] `agents/pricing/scenario_generator.py` 생성
  - [ ] `SyntheticScenarioGenerator` 클래스 구현
  - [ ] NumPy 기반 확률 분포 시뮬레이션
  - [ ] 1000년 시나리오 생성 로직
  - [ ] Peril Canvas 지급 공식 적용
  - [ ] LLM 기반 Tail Risk 시나리오 생성
  - [ ] 시나리오 데이터 저장/로드 기능

### 2.2 Monte Carlo Pricing Engine 구현
- [ ] `agents/pricing/monte_carlo_pricer.py` 생성
  - [ ] `MonteCarloPricer` 클래스 구현
  - [ ] Expected Loss (EL) 계산 로직
  - [ ] Coefficient of Variation (CoV) 계산
  - [ ] Risk Load 계산 (0.15 + 0.5 × CoV)
  - [ ] Gross Premium 계산
  - [ ] VaR 99% / TVaR 99% 계산
  - [ ] `PricingResult` 데이터 모델 정의

### 2.3 의존성 패키지 추가
- [ ] `src/requirements.txt` 업데이트
  - [ ] `numpy>=1.24.0` 추가
  - [ ] `pandas>=2.0.0` 추가
  - [ ] `scipy>=1.10.0` 추가

---

## 📅 Phase 3: Integration & Reporting

### 3.1 Pricing Reporter 구현
- [ ] `agents/pricing/pricing_reporter.py` 생성
  - [ ] `PricingReporter` 클래스 구현
  - [ ] 가격책정 테이블 생성 로직
  - [ ] Sanity Dashboard 구현
  - [ ] Tail Padding 검증 로직
  - [ ] 감사 추적 파일 생성 기능

### 3.2 LangGraph 노드 구현
- [ ] `agents/pricing/nodes.py` 생성
  - [ ] `peril_canvas_node` 함수 구현
  - [ ] `prior_extraction_node` 함수 구현
  - [ ] `scenario_generation_node` 함수 구현
  - [ ] `pricing_calculation_node` 함수 구현
  - [ ] `pricing_report_node` 함수 구현

### 3.3 상태 모델 확장
- [ ] `agents/core/state.py` 수정
  - [ ] `LLMPricingState` 클래스 추가
  - [ ] Pricing 관련 필드들 추가
  - [ ] 기존 `AgentState`와의 호환성 유지

### 3.4 새로운 Insurance Agent 구현
- [ ] `agents/pricing_insurance_agent.py` 생성
  - [ ] `PricingInsuranceAgent` 클래스 구현
  - [ ] 새로운 LangGraph 워크플로 정의
  - [ ] 6단계 노드 연결 (canvas → prior → scenario → pricing → report)
  - [ ] 기존 `InsuranceAgent`와의 호환성 유지

---

## 📅 Phase 4: Testing & Validation

### 4.1 단위 테스트 작성
- [ ] `agents/pricing/tests/` 디렉토리 생성
- [ ] `agents/pricing/tests/test_peril_canvas.py` 생성
- [ ] `agents/pricing/tests/test_prior_extraction.py` 생성
- [ ] `agents/pricing/tests/test_scenario_generator.py` 생성
- [ ] `agents/pricing/tests/test_monte_carlo_pricer.py` 생성
- [ ] `agents/pricing/tests/test_pricing_reporter.py` 생성

### 4.2 통합 테스트 작성
- [ ] `agents/pricing/tests/test_integration.py` 생성
  - [ ] 전체 워크플로 테스트
  - [ ] 다양한 이벤트 타입 테스트
  - [ ] 성능 테스트

### 4.3 CLI 업데이트
- [ ] `run_pricing_agent.py` 생성
  - [ ] 새로운 Pricing Agent CLI 인터페이스
  - [ ] 기존 `run_agent.py`와 동일한 사용법
  - [ ] 추가 옵션: `--enable-pricing`, `--years`, `--audit-trail`

---

## 📅 Phase 5: Documentation & Examples

### 5.1 문서화
- [ ] `docs/llm-lite-pricing.md` 생성
  - [ ] 사용법 가이드
  - [ ] API 레퍼런스
  - [ ] 예제 코드

### 5.2 예제 시나리오
- [ ] `examples/pricing_examples.py` 생성
  - [ ] 태풍 보험 예제
  - [ ] 게임 서버 다운 보험 예제
  - [ ] 스포츠 이벤트 보험 예제

---

## 🔧 구현 체크포인트

### Checkpoint 1: Core Infrastructure 완료 후
- [ ] 간단한 태풍 시나리오로 Peril Canvas 생성 테스트
- [ ] LLM으로 Prior 추출 테스트
- [ ] 기본 워크플로 동작 확인

### Checkpoint 2: Pricing Engine 완료 후
- [ ] 1000년 시뮬레이션 실행 테스트
- [ ] EL/CoV/Risk Load 계산 검증
- [ ] 다양한 이벤트 타입 처리 확인

### Checkpoint 3: Integration 완료 후
- [ ] 전체 파이프라인 End-to-End 테스트
- [ ] 기존 시스템과의 호환성 확인
- [ ] 성능 벤치마크 수행

### Checkpoint 4: Testing & Validation 완료 후
- [ ] 테스트 커버리지 ≥ 90% 달성
- [ ] 에러 핸들링 검증
- [ ] 규제 요구사항 준수 확인

---

## 🎯 성공 기준

### 기능적 요구사항
- [ ] 임의의 이벤트 입력으로 보험 상품 설계 가능
- [ ] LLM만으로 Prior 분포 추출
- [ ] Monte Carlo 시뮬레이션으로 가격 계산
- [ ] 감사 추적 가능한 전체 프로세스

### 비기능적 요구사항
- [ ] 전체 처리 시간 < 5분 (1000년 시뮬레이션 포함)
- [ ] 메모리 사용량 < 1GB
- [ ] API 응답 시간 < 30초
- [ ] 테스트 커버리지 ≥ 90%

### 품질 요구사항
- [ ] PEP 8 스타일 가이드 준수
- [ ] Type hints 100% 적용
- [ ] Docstring 모든 공개 함수에 적용
- [ ] 에러 처리 모든 외부 API 호출에 적용

---

## ⚠️ 위험 요소 및 대응 방안

### 기술적 위험
- **LLM API 실패**: Fallback 로직 및 Mock 데이터 준비
- **메모리 부족**: 청크 단위 처리 및 스트리밍 구현
- **계산 속도**: 병렬 처리 및 캐싱 적용

### 비즈니스 위험
- **Prior 정확도**: Self-Critique Loop 및 검증 로직 강화
- **규제 준수**: 완전한 Audit Trail 및 문서화
- **신뢰성**: 충분한 테스트 및 검증

---

## 📊 진행 상황 추적

- **Phase 1**: ⏳ 진행 예정
- **Phase 2**: ⏳ 대기 중
- **Phase 3**: ⏳ 대기 중
- **Phase 4**: ⏳ 대기 중
- **Phase 5**: ⏳ 대기 중

**전체 진행률**: 0% (0/100 작업 완료)

---

## 🚀 다음 단계

1. **Phase 1 시작**: 디렉토리 구조 생성부터 시작
2. **의존성 확인**: 필요한 패키지 설치 및 환경 설정
3. **기본 모델 정의**: Pydantic 모델들부터 구현
4. **점진적 개발**: 각 컴포넌트별로 단위 테스트와 함께 개발

**예상 완료 시간**: 2-3일 (집중 개발 시)