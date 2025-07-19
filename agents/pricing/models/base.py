"""
Base Models for LLM-Lite Parametric Pricing

Pydantic 기반 데이터 모델들을 정의합니다.
모든 I/O는 타입 안전성을 보장하기 위해 이 모델들을 사용합니다.
"""

from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum
import pandas as pd


class CurveType(str, Enum):
    """지급 곡선 타입"""
    LINEAR = "linear"
    STEP = "step"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"


class DistributionType(str, Enum):
    """확률 분포 타입"""
    NEGATIVE_BINOMIAL = "negative_binomial"
    POISSON = "poisson"
    LOGNORMAL = "lognormal"
    GAMMA = "gamma"
    EXPONENTIAL = "exponential"
    NORMAL = "normal"


class RiskLevel(str, Enum):
    """리스크 레벨 분류"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class TriggerCondition(BaseModel):
    """트리거 조건 정의"""
    metric: str = Field(..., description="트리거 지표 (예: 중심기압, 지연시간)")
    threshold: float = Field(..., description="임계값")
    operator: Literal[">=", "<=", ">", "<", "=="] = Field(default=">=", description="비교 연산자")
    unit: str = Field(..., description="단위 (예: hPa, minutes, USD)")
    
    class Config:
        schema_extra = {
            "example": {
                "metric": "central_pressure",
                "threshold": 950.0,
                "operator": "<=",
                "unit": "hPa"
            }
        }


class PayoutCurve(BaseModel):
    """지급 곡선 정의"""
    curve_type: CurveType = Field(default=CurveType.LINEAR, description="곡선 타입")
    base_amount: float = Field(..., ge=0, description="기본 지급액 (USD)")
    max_payout: float = Field(..., ge=0, description="최대 지급액 (USD)")
    multiplier: float = Field(default=1.0, gt=0, description="지급 배수")
    parameters: Dict[str, float] = Field(default_factory=dict, description="곡선별 추가 파라미터")
    
    @validator("max_payout")
    def max_payout_must_be_greater_than_base(cls, v, values):
        if "base_amount" in values and v < values["base_amount"]:
            raise ValueError("max_payout must be greater than or equal to base_amount")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "curve_type": "linear",
                "base_amount": 10000.0,
                "max_payout": 2000000.0,
                "multiplier": 10000.0,
                "parameters": {"slope": 1.0}
            }
        }


class LimitStructure(BaseModel):
    """한도 구조 정의"""
    trigger_condition: TriggerCondition
    payout_curve: PayoutCurve
    deductible: float = Field(default=0.0, ge=0, description="공제액 (USD)")
    waiting_period: int = Field(default=0, ge=0, description="대기 기간 (일)")
    policy_period: int = Field(default=365, gt=0, description="보험 기간 (일)")
    
    class Config:
        schema_extra = {
            "example": {
                "trigger_condition": {
                    "metric": "central_pressure",
                    "threshold": 950.0,
                    "operator": "<=",
                    "unit": "hPa"
                },
                "payout_curve": {
                    "curve_type": "linear",
                    "base_amount": 10000.0,
                    "max_payout": 2000000.0
                },
                "deductible": 0.0,
                "waiting_period": 0,
                "policy_period": 365
            }
        }


class PerilCanvas(BaseModel):
    """보험 위험 정의 캔버스 (STEP 0)"""
    peril: str = Field(..., description="위험 타입 (예: typhoon, flight_delay)")
    description: str = Field(..., description="위험에 대한 상세 설명")
    trigger_metric: str = Field(..., description="트리거 지표")
    data_sources: List[str] = Field(default_factory=list, description="데이터 소스 목록")
    limit_structure: LimitStructure = Field(..., description="한도 구조")
    region: str = Field(default="global", description="적용 지역")
    coverage_period: str = Field(default="annual", description="커버리지 기간")
    
    class Config:
        schema_extra = {
            "example": {
                "peril": "typhoon",
                "description": "태평양 태풍으로 인한 재산 피해",
                "trigger_metric": "central_pressure",
                "data_sources": ["JMA", "NOAA", "KMA"],
                "region": "Korea",
                "coverage_period": "annual"
            }
        }


class FrequencyPrior(BaseModel):
    """빈도 분포 Prior (STEP 1)"""
    distribution: DistributionType = Field(..., description="분포 타입")
    parameters: Dict[str, float] = Field(..., description="분포 모수")
    percentiles: Dict[str, float] = Field(..., description="5th-95th 백분위수")
    sources: List[str] = Field(default_factory=list, description="정보 출처")
    confidence: float = Field(default=0.8, ge=0, le=1, description="신뢰도")
    
    @validator("percentiles")
    def validate_percentiles(cls, v):
        required_keys = ["5th", "50th", "95th"]
        if not all(key in v for key in required_keys):
            raise ValueError(f"percentiles must contain {required_keys}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "distribution": "negative_binomial",
                "parameters": {"r": 2.5, "p": 0.8},
                "percentiles": {"5th": 0.0, "50th": 1.0, "95th": 4.0},
                "sources": ["JMA Historical Data", "NOAA Storm Database"],
                "confidence": 0.85
            }
        }


class SeverityPrior(BaseModel):
    """심도 분포 Prior (STEP 1)"""
    distribution: DistributionType = Field(..., description="분포 타입")
    parameters: Dict[str, float] = Field(..., description="분포 모수")
    percentiles: Dict[str, float] = Field(..., description="5th-95th 백분위수")
    metric_unit: str = Field(..., description="지표 단위")
    sources: List[str] = Field(default_factory=list, description="정보 출처")
    confidence: float = Field(default=0.8, ge=0, le=1, description="신뢰도")
    
    @validator("percentiles")
    def validate_percentiles(cls, v):
        required_keys = ["5th", "50th", "95th"]
        if not all(key in v for key in required_keys):
            raise ValueError(f"percentiles must contain {required_keys}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "distribution": "lognormal",
                "parameters": {"mu": 2.1, "sigma": 0.6},
                "percentiles": {"5th": 3.2, "50th": 8.1, "95th": 25.4},
                "metric_unit": "hPa_below_950",
                "sources": ["JMA Storm Intensity Database"],
                "confidence": 0.82
            }
        }


class ScenarioData(BaseModel):
    """시나리오 데이터 (STEP 2)"""
    year: int = Field(..., description="시뮬레이션 연도")
    event_count: int = Field(..., ge=0, description="연간 이벤트 발생 횟수")
    events: List[Dict[str, float]] = Field(default_factory=list, description="개별 이벤트 데이터")
    annual_loss: float = Field(default=0.0, ge=0, description="연간 총 손실")
    
    class Config:
        schema_extra = {
            "example": {
                "year": 1,
                "event_count": 2,
                "events": [
                    {"severity": 15.2, "payout": 152000.0},
                    {"severity": 8.7, "payout": 87000.0}
                ],
                "annual_loss": 239000.0
            }
        }


class PricingResult(BaseModel):
    """가격책정 결과 (STEP 3-4)"""
    peril: str = Field(..., description="위험 타입")
    expected_loss: float = Field(..., ge=0, description="기댓값 손실 (EL)")
    coefficient_of_variation: float = Field(..., ge=0, description="변동계수 (CoV)")
    risk_load: float = Field(..., ge=0, description="위험 할증")
    net_premium: float = Field(..., ge=0, description="순 보험료")
    gross_premium: float = Field(..., ge=0, description="총 보험료")
    var_99: float = Field(..., ge=0, description="VaR 99%")
    tvar_99: float = Field(..., ge=0, description="TVaR 99%")
    risk_level: RiskLevel = Field(..., description="리스크 레벨")
    recommendation: str = Field(..., description="추천사항")
    simulation_years: int = Field(default=1000, description="시뮬레이션 연수")
    timestamp: str = Field(..., description="계산 일시")
    
    @validator("gross_premium")
    def gross_premium_validation(cls, v, values):
        if "net_premium" in values and v < values["net_premium"]:
            raise ValueError("gross_premium must be greater than or equal to net_premium")
        return v
    
    def get_pml_ratio(self) -> float:
        """Probable Maximum Loss 비율 계산"""
        return self.var_99 / self.expected_loss if self.expected_loss > 0 else 0.0
    
    def get_tail_ratio(self) -> float:
        """Tail Risk 비율 계산"""
        return self.tvar_99 / self.var_99 if self.var_99 > 0 else 0.0
    
    class Config:
        schema_extra = {
            "example": {
                "peril": "typhoon",
                "expected_loss": 94000.0,
                "coefficient_of_variation": 0.55,
                "risk_load": 0.425,
                "net_premium": 94000.0,
                "gross_premium": 134000.0,
                "var_99": 450000.0,
                "tvar_99": 620000.0,
                "risk_level": "medium",
                "recommendation": "추가 분석 후 신중한 출시",
                "simulation_years": 1000,
                "timestamp": "2024-07-19T10:30:00Z"
            }
        }


class AuditTrail(BaseModel):
    """감사 추적 정보"""
    process_id: str = Field(..., description="프로세스 ID")
    user_input: str = Field(..., description="사용자 입력")
    peril_canvas: PerilCanvas = Field(..., description="생성된 Peril Canvas")
    frequency_prior: FrequencyPrior = Field(..., description="빈도 Prior")
    severity_prior: SeverityPrior = Field(..., description="심도 Prior")
    llm_conversations: List[Dict[str, str]] = Field(default_factory=list, description="LLM 대화 기록")
    scenario_summary: Dict[str, float] = Field(..., description="시나리오 요약 통계")
    pricing_result: PricingResult = Field(..., description="최종 가격책정 결과")
    validation_checks: Dict[str, bool] = Field(default_factory=dict, description="검증 체크 결과")
    created_at: str = Field(..., description="생성 일시")
    
    class Config:
        schema_extra = {
            "example": {
                "process_id": "pricing_20240719_103045",
                "user_input": "태풍 손해율 계산",
                "scenario_summary": {
                    "total_scenarios": 15000,
                    "mean_annual_loss": 94000.0,
                    "std_annual_loss": 51700.0
                },
                "validation_checks": {
                    "tail_padding": True,
                    "sanity_check": True,
                    "parameter_consistency": True
                },
                "created_at": "2024-07-19T10:30:45Z"
            }
        }