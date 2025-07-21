#!/usr/bin/env python3
"""
LLM-Lite Parametric Pricing Agent CLI

Usage: python run_pricing_agent.py "게임 서버 다운타임 보험"
"""
import sys
import asyncio
import json
import os
from typing import Dict, Any

# Add the src directory to the path so we can import from agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env file
from agents.core.config import load_env_file, get_config
load_env_file()

from agents.underwriter_agent import UnderwriterAgent


async def main():
    """Main CLI function"""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run_pricing_agent.py \"<user_input>\" [options]")
        print()
        print("Examples:")
        print("  python run_pricing_agent.py \"태풍 보험 상품 설계\"")
        print("  python run_pricing_agent.py \"게임 서버 다운타임 보험\" --years 500")
        print("  python run_pricing_agent.py \"항공편 지연 보험\" --debug")
        print()
        print("Options:")
        print("  --years N         시뮬레이션 연수 (기본: 1000)")
        print("  --debug          단계별 디버그 모드")
        print("  --no-audit       감사 추적 비활성화")
        print("  --export DIR     결과를 디렉토리에 저장")
        sys.exit(1)
    
    user_input = sys.argv[1]
    
    # Parse options
    options = parse_options(sys.argv[2:])
    
    try:
        # Create agent with options
        agent = UnderwriterAgent(
            simulation_years=options.get("years", 1000),
            enable_audit_trail=not options.get("no_audit", False)
        )
        
        print(f"🚀 LLM-Lite Parametric Underwriting 시작")
        print(f"입력: {user_input}")
        print(f"시뮬레이션: {options.get('years', 1000):,}년")
        print("=" * 60)
        
        # Run in debug mode or normal mode
        if options.get("debug", False):
            result = await run_debug_mode(agent, user_input)
        else:
            result = await run_normal_mode(agent, user_input)
        
        # Export results if requested
        if options.get("export") and result.get("status") == "success":
            export_path = await export_results(result, options["export"], user_input)
            print(f"\n📁 결과 저장: {export_path}")
            
    except KeyboardInterrupt:
        print("\n⏹️  실행이 사용자에 의해 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
        sys.exit(1)


def parse_options(args: list) -> Dict[str, Any]:
    """명령줄 옵션 파싱"""
    options = {}
    i = 0
    
    while i < len(args):
        arg = args[i]
        
        if arg == "--years" and i + 1 < len(args):
            try:
                options["years"] = int(args[i + 1])
                i += 2
            except ValueError:
                print("❌ --years 옵션에는 숫자를 입력해주세요")
                sys.exit(1)
        elif arg == "--debug":
            options["debug"] = True
            i += 1
        elif arg == "--no-audit":
            options["no_audit"] = True
            i += 1
        elif arg == "--export" and i + 1 < len(args):
            options["export"] = args[i + 1]
            i += 2
        else:
            print(f"❌ 알 수 없는 옵션: {arg}")
            sys.exit(1)
    
    return options


async def run_normal_mode(agent: UnderwriterAgent, user_input: str) -> Dict[str, Any]:
    """일반 모드 실행"""
    
    print("⏳ LLM-Lite Pricing 파이프라인 실행 중...")
    
    result = await agent.run(user_input)
    
    if result.get("status") == "success":
        print("✅ 가격책정 완료!")
        print()
        
        # 핵심 결과 표시
        display_core_results(result)
        
        # 상세 분석 표시
        display_detailed_analysis(result)
        
        # 검증 결과 표시
        display_validation_results(result)
        
        # JSON 출력
        print("\n📋 JSON 출력:")
        json_output = {
            "status": "success",
            "pricing_mode": "llm_lite",
            "expected_loss": result.get("expected_loss"),
            "gross_premium": result.get("gross_premium"),
            "risk_level": result.get("risk_level"),
            "loss_ratio": result.get("loss_ratio"),
            "validation_passed": result.get("validation_passed")
        }
        print(json.dumps(json_output, indent=2, ensure_ascii=False))
        
    else:
        print("❌ 가격책정 실패!")
        print(f"오류: {result.get('error', '알 수 없는 오류')}")
        
    return result


async def run_debug_mode(agent: UnderwriterAgent, user_input: str) -> Dict[str, Any]:
    """디버그 모드 실행 (단계별)"""
    
    print("🔍 디버그 모드: 단계별 실행")
    print()
    
    step_results = await agent.run_step_by_step(user_input)
    
    # 각 단계 결과 표시
    steps = [
        ("step1_peril_canvas", "1단계: Peril Canvas 생성"),
        ("step2_prior_extraction", "2단계: Prior 추출"),
        ("step3_scenario_generation", "3단계: 시나리오 생성"),
        ("step4_pricing_calculation", "4단계: 가격 계산"),
        ("step5_pricing_report", "5단계: 리포트 생성")
    ]
    
    for step_key, step_name in steps:
        step_result = step_results.get(step_key)
        if step_result:
            status_icon = "✅" if step_result["status"] == "success" else "❌"
            print(f"{status_icon} {step_name}: {step_result['status']}")
            
            if step_result["status"] == "error":
                print(f"   오류: {step_result.get('error', '알 수 없는 오류')}")
                break
            else:
                display_step_details(step_key, step_result)
        else:
            print(f"⏭️  {step_name}: 실행되지 않음")
    
    # 최종 결과가 있다면 표시
    final_step = step_results.get("step5_pricing_report")
    if final_step and final_step["status"] == "success":
        final_result = final_step["final_result"]
        print("\n" + "="*50)
        print("📊 최종 결과:")
        display_core_results(final_result)
        return final_result
    else:
        return {"status": "error", "error": "디버그 모드에서 최종 결과를 생성하지 못했습니다"}


def display_step_details(step_key: str, step_result: Dict[str, Any]) -> None:
    """단계별 세부 정보 표시"""
    
    if step_key == "step1_peril_canvas":
        canvas = step_result.get("canvas", {})
        if canvas:
            print(f"   위험 타입: {canvas.get('peril', 'unknown')}")
            print(f"   지역: {canvas.get('region', 'unknown')}")
            limit_structure = canvas.get('limit_structure', {})
            trigger = limit_structure.get('trigger_condition', {})
            print(f"   트리거: {trigger.get('metric', 'unknown')} {trigger.get('operator', '')} {trigger.get('threshold', '')} {trigger.get('unit', '')}")
    
    elif step_key == "step2_prior_extraction":
        freq_prior = step_result.get("frequency_prior", {})
        sev_prior = step_result.get("severity_prior", {})
        if freq_prior:
            print(f"   빈도 분포: {freq_prior.get('distribution', 'unknown')}")
            print(f"   신뢰도: {freq_prior.get('confidence', 0):.1%}")
        if sev_prior:
            print(f"   심도 분포: {sev_prior.get('distribution', 'unknown')}")
            print(f"   신뢰도: {sev_prior.get('confidence', 0):.1%}")
    
    elif step_key == "step3_scenario_generation":
        summary = step_result.get("scenario_summary", {})
        if summary:
            print(f"   시나리오 수: {summary.get('total_scenarios', 0):,}개")
            print(f"   평균 연간 손실: ${summary.get('mean_annual_loss', 0):,.0f}")
            print(f"   무손실 연도: {summary.get('zero_loss_years', 0):,}개")
    
    elif step_key == "step4_pricing_calculation":
        pricing = step_result.get("pricing_result", {})
        if pricing:
            print(f"   기댓값 손실: ${pricing.get('expected_loss', 0):,.0f}")
            print(f"   변동계수: {pricing.get('coefficient_of_variation', 0):.2f}")
            print(f"   총 보험료: ${pricing.get('gross_premium', 0):,.0f}")


def display_core_results(result: Dict[str, Any]) -> None:
    """핵심 결과 표시"""
    
    print("💰 핵심 가격책정 결과:")
    print(f"  기댓값 손실 (EL): ${result.get('expected_loss', 0):,.0f}")
    print(f"  권장 보험료: ${result.get('gross_premium', 0):,.0f}")
    print(f"  손해율: {result.get('loss_ratio', 0):.4f}")
    print(f"  리스크 레벨: {result.get('risk_level', 'unknown').upper()}")
    print()
    
    # 요약 정보
    summary = result.get("summary", {})
    if summary:
        print("📊 요약:")
        print(f"  이벤트 타입: {summary.get('event_type', 'unknown')}")
        print(f"  추천사항: {summary.get('recommendation', 'N/A')}")
        print()


def display_detailed_analysis(result: Dict[str, Any]) -> None:
    """상세 분석 표시"""
    
    print("📈 상세 리스크 분석:")
    print(f"  변동계수 (CoV): {result.get('coefficient_of_variation', 0):.3f}")
    print(f"  99% VaR: ${result.get('var_99', 0):,.0f}")
    print(f"  99% TVaR: ${result.get('tvar_99', 0):,.0f}")
    print(f"  시뮬레이션: {result.get('simulation_years', 0):,}년")
    print()


def display_validation_results(result: Dict[str, Any]) -> None:
    """검증 결과 표시"""
    
    dashboard = result.get("dashboard", {})
    validation_checks = dashboard.get("validation_checks", {})
    
    if validation_checks:
        print("✅ 검증 결과:")
        passed = sum(validation_checks.values())
        total = len(validation_checks)
        print(f"  통과율: {passed}/{total} ({passed/total*100:.0f}%)")
        
        # 실패한 검증 항목 표시
        failed_checks = [check for check, passed in validation_checks.items() if not passed]
        if failed_checks:
            print("  ⚠️  실패 항목:")
            for check in failed_checks:
                print(f"    - {check}")
        print()
    
    # 알림 표시
    alerts = dashboard.get("alerts", [])
    if alerts:
        print("🚨 주의사항:")
        for alert in alerts:
            print(f"  {alert}")
        print()


async def export_results(result: Dict[str, Any], export_dir: str, user_input: str) -> str:
    """결과를 파일로 저장"""
    
    import os
    from datetime import datetime
    
    # 출력 디렉토리 생성
    os.makedirs(export_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"llm_pricing_{timestamp}"
    
    # 1. 요약 JSON 저장
    summary_data = {
        "user_input": user_input,
        "timestamp": timestamp,
        "pricing_mode": "llm_lite",
        "core_results": {
            "expected_loss": result.get("expected_loss"),
            "gross_premium": result.get("gross_premium"),
            "risk_level": result.get("risk_level"),
            "loss_ratio": result.get("loss_ratio"),
            "coefficient_of_variation": result.get("coefficient_of_variation")
        },
        "validation": {
            "passed": result.get("validation_passed"),
            "checks": result.get("dashboard", {}).get("validation_checks", {})
        },
        "simulation_years": result.get("simulation_years")
    }
    
    summary_path = os.path.join(export_dir, f"{base_filename}_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    # 2. 경영진 요약 저장 (있는 경우)
    executive_summary = result.get("executive_summary")
    if executive_summary:
        summary_md_path = os.path.join(export_dir, f"{base_filename}_executive.md")
        with open(summary_md_path, 'w', encoding='utf-8') as f:
            f.write(executive_summary)
    
    # 3. 감사 추적 저장 (있는 경우)
    audit_trail = result.get("audit_trail")
    if audit_trail:
        audit_path = os.path.join(export_dir, f"{base_filename}_audit.json")
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(audit_trail, f, indent=2, ensure_ascii=False, default=str)
    
    return export_dir


def display_help():
    """도움말 표시"""
    help_text = """
LLM-Lite Parametric Pricing Agent
==================================

실측 데이터 없는 이벤트들에 대해 LLM 전문지식만으로 
파라메트릭 보험 상품을 자동 설계합니다.

사용법:
    python run_pricing_agent.py "<user_input>" [options]

예시:
    python run_pricing_agent.py "태풍 보험 상품 설계"
    python run_pricing_agent.py "게임 서버 다운타임 보험" --years 500
    python run_pricing_agent.py "항공편 지연 보험" --debug
    python run_pricing_agent.py "지진 위험 보험" --export ./results

옵션:
    --years N         Monte Carlo 시뮬레이션 연수 (기본: 1000)
    --debug          단계별 디버그 모드 실행
    --no-audit       감사 추적 비활성화
    --export DIR     결과를 지정된 디렉토리에 저장

출력:
    - Expected Loss (기댓값 손실)
    - Gross Premium (권장 보험료)
    - Risk Level (위험 수준 분류)
    - Coefficient of Variation (변동계수)
    - VaR/TVaR 99% (리스크 지표)
    - 검증 결과 및 추천사항

기능:
    ✅ 6단계 LLM-Lite Pricing 파이프라인
    ✅ Peril Canvas 자동 생성
    ✅ 확률-주도 Prior 추출
    ✅ Monte Carlo 시뮬레이션
    ✅ 자동 검증 및 Tail Padding
    ✅ 감사 추적 및 규제 대응

요구사항:
    - Python 3.11+
    - OpenAI API 키 (환경변수 OPENAI_API_KEY)
    - 필수 패키지: numpy, pandas, scipy, langgraph, langchain
"""
    print(help_text)


if __name__ == "__main__":
    # Handle help requests
    if len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help", "help"]:
        display_help()
        sys.exit(0)
    
    # Check configuration
    try:
        config = get_config()
        if not config.validate():
            raise ValueError("Invalid configuration")
    except ValueError as e:
        print(f"❌ 설정 오류: {e}")
        print()
        print("다음을 확인해주세요:")
        print("1. OPENAI_API_KEY 환경변수 설정:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print()
        print("2. 또는 .env 파일 생성:")
        print("   OPENAI_API_KEY=your-api-key-here")
        print()
        print("3. .env.example 파일에서 모든 설정 확인")
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main())