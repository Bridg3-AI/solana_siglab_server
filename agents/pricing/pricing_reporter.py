"""
Pricing Reporter (STEP 4)

가격책정 결과를 리포팅하고 감사 추적을 관리하는 모듈입니다.
"""

import json
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from .models.base import (
    PerilCanvas, FrequencyPrior, SeverityPrior, PricingResult, 
    AuditTrail, ScenarioData
)


class PricingReporter:
    """가격책정 결과 리포트 생성기"""
    
    def __init__(self):
        pass
    
    def generate_pricing_table(self, results: List[PricingResult]) -> pd.DataFrame:
        """
        표준화된 가격책정 테이블 생성 (STEP 4 표 형식)
        
        Args:
            results: PricingResult 객체 리스트
            
        Returns:
            가격책정 테이블 DataFrame
        """
        
        table_data = []
        
        for result in results:
            # modify_plan.md의 표 형식에 맞춰 구성
            row = {
                "Peril": result.peril,
                "EL (USD)": f"${result.expected_loss:,.0f}",
                "CoV": f"{result.coefficient_of_variation:.2f}",
                "Risk Load": f"{result.risk_load:.3f}",
                "Net Premium (USD)": f"${result.net_premium:,.0f}",
                "Gross Premium (USD)": f"${result.gross_premium:,.0f}",
                "VaR 99% (USD)": f"${result.var_99:,.0f}",
                "TVaR 99% (USD)": f"${result.tvar_99:,.0f}",
                "Risk Level": result.risk_level.value,
                "Recommendation": result.recommendation,
                "PML Ratio": f"{result.get_pml_ratio():.1f}x",
                "Tail Ratio": f"{result.get_tail_ratio():.2f}",
                "Simulation Years": result.simulation_years,
                "Timestamp": result.timestamp
            }
            
            table_data.append(row)
        
        return pd.DataFrame(table_data)
    
    def generate_sanity_dashboard(self, result: PricingResult) -> Dict[str, any]:
        """
        EL/VaR/TVaR 비율 체크를 위한 Sanity Dashboard
        
        Args:
            result: PricingResult 객체
            
        Returns:
            대시보드 정보 딕셔너리
        """
        
        dashboard = {
            "basic_metrics": {
                "expected_loss": result.expected_loss,
                "gross_premium": result.gross_premium,
                "premium_to_el_ratio": result.gross_premium / result.expected_loss if result.expected_loss > 0 else 0
            },
            "risk_metrics": {
                "var_99": result.var_99,
                "tvar_99": result.tvar_99,
                "pml_ratio": result.get_pml_ratio(),
                "tail_ratio": result.get_tail_ratio()
            },
            "validation_checks": self.validate_sanity_checks(result),
            "risk_assessment": {
                "risk_level": result.risk_level.value,
                "coefficient_of_variation": result.coefficient_of_variation,
                "risk_load": result.risk_load
            },
            "benchmarks": self._generate_industry_benchmarks(result.peril),
            "alerts": self._generate_alerts(result)
        }
        
        return dashboard
    
    def validate_sanity_checks(self, result: PricingResult) -> Dict[str, bool]:
        """
        가격책정 결과의 건전성 검증
        
        Args:
            result: PricingResult 객체
            
        Returns:
            검증 결과 딕셔너리
        """
        
        checks = {}
        
        # 1. Tail Padding 검증 (Risk Load ≥ 20% 또는 EL×20%)
        checks["tail_padding"] = self.validate_tail_padding(result)
        
        # 2. 보험료 합리성 (총 보험료 > 순 보험료)
        checks["premium_consistency"] = result.gross_premium >= result.net_premium
        
        # 3. VaR/TVaR 관계 (TVaR ≥ VaR)
        checks["var_tvar_consistency"] = result.tvar_99 >= result.var_99
        
        # 4. PML 비율 합리성 (< 100x)
        checks["pml_ratio_reasonable"] = result.get_pml_ratio() < 100
        
        # 5. 변동계수 합리성 (< 5.0)
        checks["cov_reasonable"] = result.coefficient_of_variation < 5.0
        
        # 6. 기댓값 손실 양수 확인
        checks["positive_el"] = result.expected_loss >= 0
        
        # 7. Risk Load 범위 확인 (0% ~ 200%)
        checks["risk_load_range"] = 0 <= result.risk_load <= 2.0
        
        return checks
    
    def validate_tail_padding(self, result: PricingResult) -> bool:
        """
        Tail Padding 검증 (Risk Load ≥ 20% 또는 EL×20% 추가)
        
        Args:
            result: PricingResult 객체
            
        Returns:
            Tail padding 조건 만족 여부
        """
        # modify_plan.md 요구사항: RiskLoad ≥ 20% 또는 EL×20% 추가
        min_risk_load = 0.20
        el_based_padding = result.expected_loss * 0.20
        
        return (result.risk_load >= min_risk_load) or \
               (result.gross_premium - result.net_premium >= el_based_padding)
    
    def _generate_industry_benchmarks(self, peril: str) -> Dict[str, float]:
        """위험 타입별 산업 벤치마크"""
        
        benchmarks = {
            "typhoon": {
                "typical_el_range": [50000, 200000],
                "typical_cov_range": [0.4, 0.8],
                "typical_risk_load": 0.35,
                "market_premium_range": [0.15, 0.25]
            },
            "flight_delay": {
                "typical_el_range": [10000, 50000],
                "typical_cov_range": [0.3, 0.6],
                "typical_risk_load": 0.25,
                "market_premium_range": [0.10, 0.20]
            },
            "server_downtime": {
                "typical_el_range": [5000, 100000],
                "typical_cov_range": [0.5, 1.0],
                "typical_risk_load": 0.40,
                "market_premium_range": [0.20, 0.30]
            },
            "earthquake": {
                "typical_el_range": [20000, 500000],
                "typical_cov_range": [0.6, 1.2],
                "typical_risk_load": 0.50,
                "market_premium_range": [0.25, 0.40]
            }
        }
        
        return benchmarks.get(peril, {
            "typical_el_range": [10000, 100000],
            "typical_cov_range": [0.3, 0.8],
            "typical_risk_load": 0.30,
            "market_premium_range": [0.15, 0.25]
        })
    
    def _generate_alerts(self, result: PricingResult) -> List[str]:
        """가격책정 결과 기반 알림 생성"""
        
        alerts = []
        
        # 높은 변동성 경고
        if result.coefficient_of_variation > 1.0:
            alerts.append(f"⚠️ 높은 변동성 (CoV: {result.coefficient_of_variation:.2f}) - 포트폴리오 분산 필요")
        
        # 높은 PML 비율 경고
        pml_ratio = result.get_pml_ratio()
        if pml_ratio > 20:
            alerts.append(f"⚠️ 높은 PML 비율 ({pml_ratio:.1f}x) - 재보험 고려 필요")
        
        # 낮은 Risk Load 경고
        if result.risk_load < 0.15:
            alerts.append(f"⚠️ 낮은 Risk Load ({result.risk_load:.2f}) - Tail 리스크 과소평가 가능성")
        
        # 매우 높은 리스크 레벨 경고
        if result.risk_level.value == "very_high":
            alerts.append("🚨 매우 높은 리스크 - 상품 출시 재검토 필요")
        
        # 비정상적인 지표 경고
        if result.expected_loss <= 0:
            alerts.append("❌ 기댓값 손실이 0 또는 음수 - 모델 검토 필요")
        
        return alerts
    
    def create_audit_trail(
        self,
        process_id: str,
        user_input: str,
        canvas: PerilCanvas,
        frequency_prior: FrequencyPrior,
        severity_prior: SeverityPrior,
        scenarios: pd.DataFrame,
        pricing_result: PricingResult,
        llm_conversations: List[Dict[str, str]] = None
    ) -> AuditTrail:
        """
        규제 대응용 감사 추적 정보 생성
        
        Args:
            process_id: 프로세스 고유 ID
            user_input: 원본 사용자 입력
            canvas: 생성된 PerilCanvas
            frequency_prior: 빈도 Prior
            severity_prior: 심도 Prior
            scenarios: 시나리오 데이터
            pricing_result: 최종 가격책정 결과
            llm_conversations: LLM 대화 기록
            
        Returns:
            AuditTrail 객체
        """
        
        # 시나리오 요약 통계
        scenario_summary = {
            "total_scenarios": len(scenarios),
            "mean_annual_loss": float(scenarios["annual_loss"].mean()),
            "std_annual_loss": float(scenarios["annual_loss"].std()),
            "zero_loss_years": int((scenarios["annual_loss"] == 0).sum()),
            "max_annual_loss": float(scenarios["annual_loss"].max()),
            "total_events": int(scenarios["event_count"].sum()),
            "tail_scenarios": int(scenarios.get("tail_scenario", pd.Series()).notna().sum())
        }
        
        # 검증 체크 실행
        validation_checks = self.validate_sanity_checks(pricing_result)
        
        return AuditTrail(
            process_id=process_id,
            user_input=user_input,
            peril_canvas=canvas,
            frequency_prior=frequency_prior,
            severity_prior=severity_prior,
            llm_conversations=llm_conversations or [],
            scenario_summary=scenario_summary,
            pricing_result=pricing_result,
            validation_checks=validation_checks,
            created_at=datetime.now().isoformat()
        )
    
    def export_audit_trail(self, audit_trail: AuditTrail, filepath: str) -> str:
        """
        감사 추적 정보를 파일로 저장
        
        Args:
            audit_trail: AuditTrail 객체
            filepath: 저장할 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        
        # Pydantic 모델을 JSON으로 직렬화
        audit_data = audit_trail.dict()
        
        # JSON 파일로 저장 (가독성을 위해 들여쓰기 적용)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
    
    def generate_executive_summary(
        self, 
        pricing_result: PricingResult,
        canvas: PerilCanvas,
        dashboard: Dict[str, any]
    ) -> str:
        """
        경영진 요약 보고서 생성
        
        Args:
            pricing_result: 가격책정 결과
            canvas: PerilCanvas
            dashboard: Sanity Dashboard
            
        Returns:
            요약 보고서 텍스트
        """
        
        summary = f"""
# {canvas.peril.upper()} 파라메트릭 보험 가격책정 요약

## 📊 핵심 지표
- **기댓값 손실**: ${pricing_result.expected_loss:,.0f}
- **권장 보험료**: ${pricing_result.gross_premium:,.0f}
- **리스크 레벨**: {pricing_result.risk_level.value.upper()}
- **변동계수**: {pricing_result.coefficient_of_variation:.2f}

## 💡 추천사항
{pricing_result.recommendation}

## 🎯 위험 구조
- **트리거 조건**: {canvas.limit_structure.trigger_condition.metric} {canvas.limit_structure.trigger_condition.operator} {canvas.limit_structure.trigger_condition.threshold} {canvas.limit_structure.trigger_condition.unit}
- **최대 지급액**: ${canvas.limit_structure.payout_curve.max_payout:,.0f}
- **지급 곡선**: {canvas.limit_structure.payout_curve.curve_type.value}

## 📈 리스크 분석
- **99% VaR**: ${pricing_result.var_99:,.0f}
- **99% TVaR**: ${pricing_result.tvar_99:,.0f}
- **PML 비율**: {pricing_result.get_pml_ratio():.1f}x

## ✅ 검증 상태
"""
        
        # 검증 결과 추가
        validation = dashboard["validation_checks"]
        passed_checks = sum(validation.values())
        total_checks = len(validation)
        
        summary += f"- **검증 통과율**: {passed_checks}/{total_checks} ({passed_checks/total_checks*100:.0f}%)\n"
        
        if not all(validation.values()):
            summary += "\n## ⚠️ 검증 실패 항목\n"
            for check, passed in validation.items():
                if not passed:
                    summary += f"- {check}: 실패\n"
        
        # 알림 추가
        alerts = dashboard["alerts"]
        if alerts:
            summary += "\n## 🚨 주의사항\n"
            for alert in alerts:
                summary += f"- {alert}\n"
        
        summary += f"\n---\n생성일시: {pricing_result.timestamp}\n시뮬레이션: {pricing_result.simulation_years:,}년"
        
        return summary
    
    def export_pricing_report(
        self,
        pricing_result: PricingResult,
        canvas: PerilCanvas,
        scenarios: pd.DataFrame,
        output_dir: str
    ) -> Dict[str, str]:
        """
        완전한 가격책정 리포트 패키지 생성
        
        Args:
            pricing_result: 가격책정 결과
            canvas: PerilCanvas
            scenarios: 시나리오 데이터
            output_dir: 출력 디렉토리
            
        Returns:
            생성된 파일들의 경로 딕셔너리
        """
        
        import os
        from datetime import datetime
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{canvas.peril}_{timestamp}"
        
        files_created = {}
        
        # 1. 가격책정 테이블 (CSV)
        pricing_table = self.generate_pricing_table([pricing_result])
        table_path = os.path.join(output_dir, f"{base_filename}_pricing_table.csv")
        pricing_table.to_csv(table_path, index=False)
        files_created["pricing_table"] = table_path
        
        # 2. 시나리오 데이터 (CSV)
        scenario_path = os.path.join(output_dir, f"{base_filename}_scenarios.csv")
        # 시나리오 평면화 저장
        self._export_flattened_scenarios(scenarios, scenario_path)
        files_created["scenarios"] = scenario_path
        
        # 3. Sanity Dashboard (JSON)
        dashboard = self.generate_sanity_dashboard(pricing_result)
        dashboard_path = os.path.join(output_dir, f"{base_filename}_dashboard.json")
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2, ensure_ascii=False, default=str)
        files_created["dashboard"] = dashboard_path
        
        # 4. 경영진 요약 (Markdown)
        executive_summary = self.generate_executive_summary(pricing_result, canvas, dashboard)
        summary_path = os.path.join(output_dir, f"{base_filename}_executive_summary.md")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(executive_summary)
        files_created["executive_summary"] = summary_path
        
        return files_created
    
    def _export_flattened_scenarios(self, scenarios: pd.DataFrame, filepath: str) -> None:
        """시나리오 데이터를 평면화하여 CSV로 저장"""
        
        flattened_data = []
        
        for _, row in scenarios.iterrows():
            year = row["year"]
            event_count = row["event_count"]
            annual_loss = row["annual_loss"]
            events = row.get("events_with_payouts", [])
            tail_scenario = row.get("tail_scenario", None)
            
            if not events:
                # 이벤트가 없는 연도
                flattened_data.append({
                    "year": year,
                    "event_count": 0,
                    "annual_loss": 0.0,
                    "event_id": None,
                    "severity": None,
                    "payout": 0.0,
                    "triggered": False,
                    "tail_scenario": tail_scenario
                })
            else:
                # 각 이벤트별로 행 생성
                for event in events:
                    flattened_data.append({
                        "year": year,
                        "event_count": event_count,
                        "annual_loss": annual_loss,
                        "event_id": event.get("event_id"),
                        "severity": event.get("severity"),
                        "payout": event.get("payout", 0.0),
                        "triggered": event.get("triggered", False),
                        "tail_scenario": tail_scenario
                    })
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(filepath, index=False)


# 편의 함수들
def generate_pricing_report(
    pricing_result: PricingResult,
    canvas: PerilCanvas,
    scenarios: pd.DataFrame
) -> Dict[str, any]:
    """간편한 가격책정 리포트 생성"""
    reporter = PricingReporter()
    
    dashboard = reporter.generate_sanity_dashboard(pricing_result)
    pricing_table = reporter.generate_pricing_table([pricing_result])
    executive_summary = reporter.generate_executive_summary(pricing_result, canvas, dashboard)
    
    return {
        "dashboard": dashboard,
        "pricing_table": pricing_table,
        "executive_summary": executive_summary,
        "validation_passed": all(dashboard["validation_checks"].values())
    }


def create_process_audit_trail(
    user_input: str,
    canvas: PerilCanvas,
    frequency_prior: FrequencyPrior,
    severity_prior: SeverityPrior,
    scenarios: pd.DataFrame,
    pricing_result: PricingResult
) -> AuditTrail:
    """간편한 감사 추적 생성"""
    reporter = PricingReporter()
    process_id = f"pricing_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    return reporter.create_audit_trail(
        process_id, user_input, canvas, frequency_prior, severity_prior,
        scenarios, pricing_result
    )