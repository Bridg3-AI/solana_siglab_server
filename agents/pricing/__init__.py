"""
LLM-Lite Parametric Pricing Module

이 모듈은 실측 데이터 없는 이벤트들에 대해 LLM 전문지식만으로 
파라메트릭 보험 상품을 자동 설계하는 시스템을 제공합니다.

구성 요소:
- peril_canvas: 보험 위험 정의 및 지급 구조 설계
- prior_extraction: LLM 기반 확률 분포 모수 추출
- scenario_generator: Monte Carlo 시나리오 생성
- monte_carlo_pricer: 기댓값 손실 및 보험료 계산
- pricing_reporter: 가격책정 결과 리포팅
"""

from .models.base import (
    PerilCanvas,
    PayoutCurve,
    FrequencyPrior,
    SeverityPrior,
    PricingResult
)

__all__ = [
    "PerilCanvas",
    "PayoutCurve", 
    "FrequencyPrior",
    "SeverityPrior",
    "PricingResult"
]

__version__ = "0.1.0"