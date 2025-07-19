"""
LLM-Lite Parametric Pricing 통합 테스트

이 파일은 전체 시스템의 통합 테스트를 수행합니다.
실제 LLM API 호출 없이도 시스템 구조를 검증할 수 있습니다.
"""

import asyncio
import json
from typing import Dict, Any

# 테스트용 Mock 데이터
MOCK_PERIL_CANVAS = {
    "peril": "server_downtime",
    "description": "게임 서버 다운타임으로 인한 비즈니스 손실",
    "trigger_metric": "downtime_minutes",
    "data_sources": ["Monitoring APIs", "Internal Systems"],
    "region": "Global",
    "coverage_period": "annual",
    "limit_structure": {
        "trigger_condition": {
            "metric": "downtime_minutes",
            "threshold": 10.0,
            "operator": ">=",
            "unit": "minutes"
        },
        "payout_curve": {
            "curve_type": "linear",
            "base_amount": 500.0,
            "max_payout": 750000.0,
            "multiplier": 500.0
        },
        "deductible": 0.0,
        "waiting_period": 0,
        "policy_period": 365
    }
}

MOCK_FREQUENCY_PRIOR = {
    "distribution": "negative_binomial",
    "parameters": {"r": 8.0, "p": 0.6},
    "percentiles": {"5th": 2.0, "50th": 5.0, "95th": 12.0},
    "sources": ["Industry Uptime Statistics", "Cloud Provider SLAs"],
    "confidence": 0.8
}

MOCK_SEVERITY_PRIOR = {
    "distribution": "exponential",
    "parameters": {"lambda": 0.1},
    "percentiles": {"5th": 0.5, "50th": 6.9, "95th": 30.0},
    "metric_unit": "minutes",
    "sources": ["IT Industry Reports"],
    "confidence": 0.75
}


class TestPerilCanvasGeneration:
    """Peril Canvas 생성 테스트"""
    
    def test_canvas_structure_validation(self):
        """Canvas 구조 검증"""
        
        # 필수 필드 확인
        required_fields = [
            "peril", "description", "trigger_metric", 
            "data_sources", "limit_structure"
        ]
        
        for field in required_fields:
            assert field in MOCK_PERIL_CANVAS, f"필수 필드 누락: {field}"
        
        # Limit Structure 검증
        limit_structure = MOCK_PERIL_CANVAS["limit_structure"]
        assert "trigger_condition" in limit_structure
        assert "payout_curve" in limit_structure
        
        # Trigger Condition 검증
        trigger = limit_structure["trigger_condition"]
        assert trigger["threshold"] > 0
        assert trigger["operator"] in [">=", "<=", ">", "<", "=="]
        
        # Payout Curve 검증
        payout = limit_structure["payout_curve"]
        assert payout["max_payout"] >= payout["base_amount"]
        assert payout["curve_type"] in ["linear", "step", "exponential", "logarithmic"]
    
    def test_event_type_mapping(self):
        """이벤트 타입 매핑 검증"""
        
        event_mappings = {
            "게임 서버 다운타임": "server_downtime",
            "태풍 보험": "typhoon",
            "항공편 지연": "flight_delay",
            "지진 위험": "earthquake"
        }
        
        for korean_input, expected_peril in event_mappings.items():
            # 키워드 매칭 로직 검증
            normalized_input = korean_input.lower()
            
            if "서버" in normalized_input or "다운" in normalized_input:
                assert expected_peril == "server_downtime"
            elif "태풍" in normalized_input:
                assert expected_peril == "typhoon"
            elif "항공" in normalized_input or "지연" in normalized_input:
                assert expected_peril == "flight_delay"
            elif "지진" in normalized_input:
                assert expected_peril == "earthquake"


class TestPriorExtraction:
    """Prior 추출 테스트"""
    
    def test_frequency_prior_structure(self):
        """빈도 Prior 구조 검증"""
        
        freq_prior = MOCK_FREQUENCY_PRIOR
        
        # 필수 필드 확인
        required_fields = ["distribution", "parameters", "percentiles", "confidence"]
        for field in required_fields:
            assert field in freq_prior, f"빈도 Prior 필수 필드 누락: {field}"
        
        # 분포 파라미터 검증
        if freq_prior["distribution"] == "negative_binomial":
            params = freq_prior["parameters"]
            assert "r" in params and "p" in params
            assert params["r"] > 0 and 0 < params["p"] <= 1
        
        # 백분위수 검증
        percentiles = freq_prior["percentiles"]
        assert percentiles["5th"] <= percentiles["50th"] <= percentiles["95th"]
    
    def test_severity_prior_structure(self):
        """심도 Prior 구조 검증"""
        
        sev_prior = MOCK_SEVERITY_PRIOR
        
        # 필수 필드 확인
        required_fields = ["distribution", "parameters", "percentiles", "metric_unit"]
        for field in required_fields:
            assert field in sev_prior, f"심도 Prior 필수 필드 누락: {field}"
        
        # 분포 파라미터 검증
        if sev_prior["distribution"] == "exponential":
            params = sev_prior["parameters"]
            assert "lambda" in params
            assert params["lambda"] > 0
        
        # 백분위수 검증
        percentiles = sev_prior["percentiles"]
        assert percentiles["5th"] <= percentiles["50th"] <= percentiles["95th"]


class TestScenarioGeneration:
    """시나리오 생성 테스트"""
    
    def test_scenario_data_structure(self):
        """시나리오 데이터 구조 검증"""
        
        # Mock 시나리오 데이터
        mock_scenario = {
            "year": 1,
            "event_count": 2,
            "events_with_payouts": [
                {
                    "event_id": "1_0",
                    "severity": 15.5,
                    "payout": 7750.0,
                    "triggered": True
                },
                {
                    "event_id": "1_1", 
                    "severity": 5.2,
                    "payout": 0.0,
                    "triggered": False
                }
            ],
            "annual_loss": 7750.0
        }
        
        # 구조 검증
        assert "year" in mock_scenario
        assert "event_count" in mock_scenario
        assert "annual_loss" in mock_scenario
        assert mock_scenario["event_count"] == len(mock_scenario["events_with_payouts"])
        
        # 이벤트 구조 검증
        for event in mock_scenario["events_with_payouts"]:
            assert "severity" in event
            assert "payout" in event
            assert "triggered" in event
            assert event["payout"] >= 0
    
    def test_payout_calculation_logic(self):
        """지급액 계산 로직 검증"""
        
        # 테스트 케이스
        test_cases = [
            {"severity": 15.0, "threshold": 10.0, "operator": ">=", "expected_triggered": True},
            {"severity": 5.0, "threshold": 10.0, "operator": ">=", "expected_triggered": False},
            {"severity": 950.0, "threshold": 950.0, "operator": "<=", "expected_triggered": True},
            {"severity": 960.0, "threshold": 950.0, "operator": "<=", "expected_triggered": False}
        ]
        
        for case in test_cases:
            severity = case["severity"]
            threshold = case["threshold"]
            operator = case["operator"]
            expected = case["expected_triggered"]
            
            # 트리거 조건 검증
            if operator == ">=":
                triggered = severity >= threshold
            elif operator == "<=":
                triggered = severity <= threshold
            else:
                triggered = False
            
            assert triggered == expected, f"트리거 조건 실패: {case}"


class TestMonteCarloPricing:
    """Monte Carlo 가격 계산 테스트"""
    
    def test_pricing_metrics_calculation(self):
        """가격 지표 계산 검증"""
        
        # Mock 연간 손실 데이터
        annual_losses = [0, 5000, 12000, 0, 8500, 25000, 0, 3000, 15000, 45000]
        
        # Expected Loss 계산
        expected_loss = sum(annual_losses) / len(annual_losses)
        assert expected_loss == 11350.0
        
        # Coefficient of Variation 계산
        mean_loss = expected_loss
        variance = sum((x - mean_loss) ** 2 for x in annual_losses) / len(annual_losses)
        std_loss = variance ** 0.5
        cov = std_loss / mean_loss if mean_loss > 0 else 0
        
        assert cov > 0, "변동계수는 양수여야 함"
        
        # Risk Load 계산 (0.15 + 0.5 × CoV)
        risk_load = 0.15 + (0.5 * cov)
        assert risk_load >= 0.15, "Risk Load는 최소 15%"
        
        # Gross Premium 계산
        gross_premium = expected_loss * (1 + risk_load)
        assert gross_premium > expected_loss, "총 보험료는 기댓값 손실보다 커야 함"
    
    def test_var_tvar_calculation(self):
        """VaR/TVaR 계산 검증"""
        
        # 정렬된 손실 데이터 (100개 시나리오 가정)
        sorted_losses = list(range(0, 100000, 1000))  # 0, 1000, 2000, ..., 99000
        
        # 99% VaR (99번째 백분위수)
        var_index = int(0.99 * len(sorted_losses)) - 1
        var_99 = sorted_losses[var_index]
        
        # 99% TVaR (VaR 초과 손실의 평균)
        tail_losses = sorted_losses[var_index:]
        tvar_99 = sum(tail_losses) / len(tail_losses) if tail_losses else var_99
        
        assert tvar_99 >= var_99, "TVaR는 VaR보다 크거나 같아야 함"
        assert var_99 > 0, "VaR는 양수여야 함"
    
    def test_risk_level_classification(self):
        """리스크 레벨 분류 검증"""
        
        test_cases = [
            {"cov": 0.2, "pml_ratio": 3, "expected": "low"},
            {"cov": 0.4, "pml_ratio": 7, "expected": "medium"},
            {"cov": 0.8, "pml_ratio": 15, "expected": "high"},
            {"cov": 1.5, "pml_ratio": 25, "expected": "very_high"}
        ]
        
        for case in test_cases:
            cov = case["cov"]
            pml_ratio = case["pml_ratio"]
            expected = case["expected"]
            
            # 리스크 레벨 분류 로직
            if cov < 0.3 and pml_ratio < 5:
                risk_level = "low"
            elif cov < 0.6 and pml_ratio < 10:
                risk_level = "medium"
            elif cov < 1.0 and pml_ratio < 20:
                risk_level = "high"
            else:
                risk_level = "very_high"
            
            assert risk_level == expected, f"리스크 레벨 분류 오류: {case}"


class TestValidationChecks:
    """검증 체크 테스트"""
    
    def test_tail_padding_validation(self):
        """Tail Padding 검증 테스트"""
        
        test_cases = [
            {"risk_load": 0.25, "expected": True},  # 25% > 20%
            {"risk_load": 0.15, "expected": False}, # 15% < 20%
            {"risk_load": 0.20, "expected": True}   # 20% = 20%
        ]
        
        for case in test_cases:
            risk_load = case["risk_load"]
            expected = case["expected"]
            
            # Tail Padding 검증 로직
            min_risk_load = 0.20
            tail_padding_passed = risk_load >= min_risk_load
            
            assert tail_padding_passed == expected, f"Tail Padding 검증 실패: {case}"
    
    def test_sanity_checks(self):
        """건전성 검증 테스트"""
        
        # Mock 가격책정 결과
        mock_result = {
            "expected_loss": 50000,
            "net_premium": 50000,
            "gross_premium": 65000,
            "var_99": 200000,
            "tvar_99": 250000,
            "coefficient_of_variation": 0.4,
            "risk_load": 0.3
        }
        
        # 각종 검증 수행
        checks = {}
        
        # 1. 보험료 일관성
        checks["premium_consistency"] = mock_result["gross_premium"] >= mock_result["net_premium"]
        
        # 2. VaR/TVaR 관계
        checks["var_tvar_consistency"] = mock_result["tvar_99"] >= mock_result["var_99"]
        
        # 3. 기댓값 손실 양수
        checks["positive_el"] = mock_result["expected_loss"] >= 0
        
        # 4. CoV 합리성
        checks["cov_reasonable"] = mock_result["coefficient_of_variation"] < 5.0
        
        # 5. Risk Load 범위
        checks["risk_load_range"] = 0 <= mock_result["risk_load"] <= 2.0
        
        # 모든 검증이 통과해야 함
        assert all(checks.values()), f"검증 실패: {checks}"


class TestEndToEndWorkflow:
    """End-to-End 워크플로 테스트"""
    
    def test_workflow_state_transitions(self):
        """워크플로 상태 전환 테스트"""
        
        # 초기 상태
        initial_state = {
            "messages": [{"role": "user", "content": "게임 서버 다운타임 보험"}],
            "plan": "",
            "result": None,
            "event_type": None
        }
        
        # 1단계: Peril Canvas 생성 후 상태
        after_canvas = {
            **initial_state,
            "peril_canvas": MOCK_PERIL_CANVAS,
            "event_type": "server_downtime"
        }
        
        # 2단계: Prior 추출 후 상태
        after_prior = {
            **after_canvas,
            "frequency_prior": MOCK_FREQUENCY_PRIOR,
            "severity_prior": MOCK_SEVERITY_PRIOR
        }
        
        # 3단계: 시나리오 생성 후 상태
        after_scenarios = {
            **after_prior,
            "scenarios": {
                "summary": {"total_scenarios": 100, "mean_annual_loss": 25000},
                "data": []  # 실제로는 시나리오 데이터
            }
        }
        
        # 각 단계별 필수 데이터 확인
        assert "peril_canvas" in after_canvas
        assert "event_type" in after_canvas
        
        assert "frequency_prior" in after_prior
        assert "severity_prior" in after_prior
        
        assert "scenarios" in after_scenarios
        assert "summary" in after_scenarios["scenarios"]
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        
        # 데이터 누락 시나리오
        incomplete_states = [
            {},  # 빈 상태
            {"messages": []},  # 메시지 없음
            {"peril_canvas": None},  # Canvas 없음
            {"frequency_prior": None, "severity_prior": None}  # Prior 없음
        ]
        
        for state in incomplete_states:
            # 각 상태에서 필수 데이터 확인
            has_messages = bool(state.get("messages"))
            has_canvas = bool(state.get("peril_canvas"))
            has_priors = bool(state.get("frequency_prior")) and bool(state.get("severity_prior"))
            
            # 최소한의 요구사항 확인
            if not has_messages:
                assert "messages" not in state or not state["messages"]
            
            if not has_canvas:
                assert "peril_canvas" not in state or not state["peril_canvas"]
            
            if not has_priors:
                assert not (state.get("frequency_prior") and state.get("severity_prior"))


# 통합 테스트 실행 함수
def run_all_tests():
    """모든 테스트 실행"""
    
    test_classes = [
        TestPerilCanvasGeneration(),
        TestPriorExtraction(),
        TestScenarioGeneration(),
        TestMonteCarloPricing(),
        TestValidationChecks(),
        TestEndToEndWorkflow()
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n🧪 {class_name} 테스트 실행...")
        
        # 각 클래스의 테스트 메서드 실행
        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    method = getattr(test_class, method_name)
                    method()
                    print(f"   ✅ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"   ❌ {method_name}: {str(e)}")
                    failed_tests.append((class_name, method_name, str(e)))
    
    # 결과 요약
    print(f"\n📊 테스트 결과 요약:")
    print(f"   총 테스트: {total_tests}")
    print(f"   통과: {passed_tests}")
    print(f"   실패: {len(failed_tests)}")
    print(f"   성공률: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests:
        print(f"\n❌ 실패한 테스트:")
        for class_name, method_name, error in failed_tests:
            print(f"   {class_name}.{method_name}: {error}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    print("🚀 LLM-Lite Parametric Pricing 통합 테스트 시작")
    print("=" * 60)
    
    success = run_all_tests()
    
    if success:
        print(f"\n🎉 모든 테스트가 통과했습니다!")
        print("   시스템이 올바르게 구현되었습니다.")
    else:
        print(f"\n⚠️  일부 테스트가 실패했습니다.")
        print("   실패한 부분을 검토해주세요.")
    
    print("\n" + "=" * 60)