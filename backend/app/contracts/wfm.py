from datetime import date as dt_date, time as dt_time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SolverWeightsDTO(BaseModel):
    """Parametry i wagi funkcji celu dla bezstanowego silnika OR-Tools CP-SAT."""

    w_dev_1: int = 6                  # do 4h (0 - 240 min)
    w_dev_2: int = 18                 # > 4h do 10h (240 - 600 min)
    w_dev_3: int = 48                 # > 10h (> 600 min)
    urgency_scale: int = 1200         # premia za rzadkość dyspozycyjności (scarcity_ratio * urgency_scale)
    slot_fill_reward: int = 50000
    preferred_bonus: int = 2000
    available_bonus: int = 500
    clopening_penalty: int = 25000
    excess_shifts_penalty: int = 2000
    excess_monthly_minutes_penalty: int = 1000
    split_shift_penalty: int = 50
    max_solve_time_sec: float = 10.0


class SolverShiftItem(BaseModel):
    id: int
    name: str
    start_time: str  # "HH:MM" lub "HH:MM:SS"
    end_time: str    # "HH:MM" lub "HH:MM:SS"
    applicable_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


class SolverRoleItem(BaseModel):
    id: int
    name: str


class SolverEmployeeItem(BaseModel):
    id: str
    full_name: str
    role_ids: List[int] = Field(default_factory=list)
    target_hours_per_month: Optional[float] = None
    target_shifts_per_month: Optional[int] = None
    worked_or_scheduled_hours: float = 0.0
    remaining_monthly_target: float = 0.0
    effective_weekly_target_hours: float = 0.0
    effective_weekly_target_minutes: int = 0
    scarcity_ratio: float = 0.0


class SolverRequirementItem(BaseModel):
    date: str  # ISO "YYYY-MM-DD"
    shift_def_id: int
    role_id: int
    min_count: int


class SolverAvailabilityItem(BaseModel):
    user_id: str
    date: str  # ISO "YYYY-MM-DD"
    shift_def_id: int
    status: str  # "AVAILABLE", "PREFERRED", "UNAVAILABLE", "UNKNOWN"


class SolverLeaveDayItem(BaseModel):
    user_id: str
    date: str  # ISO "YYYY-MM-DD"


class SolverInputDTO(BaseModel):
    """
    Samowystarczalny kontrakt Pure-Compute (JSON-In -> OR-Tools CP-SAT -> JSON-Out)
    dla bezstanowego silnika solvera (zero połączeń z bazą PostgreSQL).
    """

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[int] = None
    start_date: str  # ISO "YYYY-MM-DD"
    end_date: str    # ISO "YYYY-MM-DD"
    save: bool = False
    shifts: List[SolverShiftItem] = Field(default_factory=list)
    roles: List[SolverRoleItem] = Field(default_factory=list)
    employees: List[SolverEmployeeItem] = Field(default_factory=list)
    requirements: List[SolverRequirementItem] = Field(default_factory=list)
    availabilities: List[SolverAvailabilityItem] = Field(default_factory=list)
    leave_days: List[SolverLeaveDayItem] = Field(default_factory=list)
    weekly_targets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    weights: SolverWeightsDTO = Field(default_factory=SolverWeightsDTO)


# Alias kompatybilności wstecznej
SolverJobPayload = SolverInputDTO


class SolverAssignmentDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    date: str  # ISO "YYYY-MM-DD"
    shift_def_id: int
    user_id: str
    role_id: int
    is_published: bool = False
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    shift_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class DecisionExplanationDTO(BaseModel):
    """Szczegółowe uzasadnienie decyzji solvera dla pojedynczego slotu lub pracownika."""

    category: str  # "ASSIGNED", "DEFICIT", "REST_VIOLATION", "EMPLOYEE_SUMMARY", "INFEASIBLE"
    date: Optional[str] = None
    shift_def_id: Optional[int] = None
    shift_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SolverExplanationDTO(BaseModel):
    solver_status: str
    solve_duration_sec: float
    variables_count: int
    objective_terms_count: int
    wall_time_sec: float = 0.0
    user_time_sec: float = 0.0
    objective_value: float
    best_objective_bound: float = 0.0
    total_required_slots: int
    total_assigned_slots: int
    coverage_pct: float
    deficit_explanations: List[Dict[str, Any]] = Field(default_factory=list)
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    deficit_details: Dict[str, Any] = Field(default_factory=dict)
    employee_summary_log: Dict[str, Any] = Field(default_factory=dict)
    employee_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    rest_violations: List[Dict[str, Any]] = Field(default_factory=list)
    domain_logs: List[str] = Field(default_factory=list)
    decisions: List[DecisionExplanationDTO] = Field(default_factory=list)


class SolverResultDTO(BaseModel):
    """Ścisły kontrakt wyjściowy bezstanowego silnika optymalizacji grafiku."""

    job_id: str
    status: str  # "success" | "infeasible"
    count: int
    schedules: List[SolverAssignmentDTO] = Field(default_factory=list)
    warnings: List[Union[Dict[str, Any], str]] = Field(default_factory=list)
    weekly_targets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    decisions: List[DecisionExplanationDTO] = Field(default_factory=list)
    solver_explanation: SolverExplanationDTO


# ═══════════════════════════════════════════════════════════════════════════════
#  WFM Prediction & Labor Cost Simulation Contracts
# ═══════════════════════════════════════════════════════════════════════════════


class WfmShiftDTO(BaseModel):
    id: int
    name: str
    start_time: dt_time
    end_time: dt_time
    applicable_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


class WfmRoleDTO(BaseModel):
    id: int
    name: str
    color_hex: str = "#607D8B"
    hourly_rate: Optional[float] = None


class WfmEmployeeDTO(BaseModel):
    id: UUID
    full_name: str
    is_active: bool = True
    role_system: str = "EMPLOYEE"
    target_hours_per_month: Optional[float] = None
    hourly_rate: Optional[float] = None
    role_ids: List[int] = Field(default_factory=list)
    role_hourly_rates: List[float] = Field(default_factory=list)


class WfmScheduleItemDTO(BaseModel):
    id: Optional[UUID] = None
    date: dt_date
    shift_def_id: int
    user_id: UUID
    role_id: int


class WfmAvailabilityItemDTO(BaseModel):
    user_id: UUID
    date: dt_date
    shift_def_id: int
    status: str


class WfmLeaveRequestItemDTO(BaseModel):
    user_id: UUID
    start_date: dt_date
    end_date: dt_date
    status: str = "APPROVED"


class WfmRequirementItemDTO(BaseModel):
    date: Optional[dt_date] = None
    day_of_week: Optional[int] = None
    shift_def_id: int
    role_id: int
    min_count: int


class WfmAttendanceItemDTO(BaseModel):
    user_id: UUID
    date: dt_date
    schedule_id: Optional[UUID] = None
    check_in: dt_time
    check_out: dt_time
    status: str = "CONFIRMED"
    is_absent: bool = False


class WfmGiveawayItemDTO(BaseModel):
    schedule_id: UUID
    offered_by: UUID


class WfmPredictionInputDTO(BaseModel):
    """Samowystarczalny kontrakt wejściowy dla bezstanowego silnika predykcji WFM."""

    tenant_id: Optional[int] = None
    start_date: dt_date
    end_date: Optional[dt_date] = None
    reference_date: Optional[dt_date] = None
    lookback_weeks_drift: int = 6
    lookback_weeks_stability: int = 8
    include_rest_of_month: bool = True
    employees: List[WfmEmployeeDTO] = Field(default_factory=list)
    shifts: List[WfmShiftDTO] = Field(default_factory=list)
    roles: List[WfmRoleDTO] = Field(default_factory=list)
    schedules: List[WfmScheduleItemDTO] = Field(default_factory=list)
    availabilities: List[WfmAvailabilityItemDTO] = Field(default_factory=list)
    leave_requests: List[WfmLeaveRequestItemDTO] = Field(default_factory=list)
    requirements: List[WfmRequirementItemDTO] = Field(default_factory=list)
    attendances: List[WfmAttendanceItemDTO] = Field(default_factory=list)
    giveaways: List[WfmGiveawayItemDTO] = Field(default_factory=list)
    draft_entries: Optional[List[Dict[str, Any]]] = None


class WfmPredictionOutputDTO(BaseModel):
    """Ścisły kontrakt wyjściowy pełnego raportu predykcyjnego WFM."""

    start_date: str
    end_date: str
    bottleneck_forecast: Dict[str, Any]
    attendance_drift: Dict[str, Any]
    shift_stability: Dict[str, Any]
    labor_cost_simulation: Dict[str, Any]
