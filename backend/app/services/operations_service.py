from calendar import monthrange
import csv
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO, StringIO
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlmodel import Session, select

from ..models import (
    Announcement,
    AnnouncementReadReceipt,
    Attendance,
    AttendanceStatus,
    ChecklistCompletion,
    ChecklistTemplate,
    ChecklistTemplateItem,
    DailyCloseout,
    HaccpDevice,
    HaccpLog,
    HaccpLogType,
    JobRole,
    Notification,
    RestaurantConfig,
    RoleSystem,
    Schedule,
    ShiftDefinition,
    ShiftPeriodType,
    User,
)
from ..schemas import (
    AnnouncementCreate,
    ChecklistTemplateCreate,
    DailyCloseoutCreate,
    HaccpDeviceCreate,
    HaccpLogCreate,
)
from .push_service import PushService, send_push_to_tokens

logger = logging.getLogger(__name__)


class OperationsService:
    """Service handling Module A (Payroll & Daily Closeout), Module B (Checklists & HACCP), and Module C (Announcements)."""

    def __init__(self, session: Session, tenant_id: Optional[int] = None):
        self.session = session
        if tenant_id is None:
            from ..tenant_context import get_current_tenant_id

            tid = get_current_tenant_id()
            if not tid:
                first_rest = session.exec(select(RestaurantConfig)).first()
                if first_rest:
                    tid = first_rest.id
            self.tenant_id = tid
        else:
            self.tenant_id = tenant_id

    # ═══════════════════════════════════════════════════════════════════════════
    #  Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _calc_duration_hours(start_t: time, end_t: time, ref_date: Optional[date] = None) -> float:
        d = ref_date or date.today()
        start_dt = datetime.combine(d, start_t)
        end_dt = datetime.combine(d, end_t)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return (end_dt - start_dt).total_seconds() / 3600.0

    def resolve_hourly_rate(self, user: User, role_id: Optional[int] = None) -> float:
        """
        Resolve effective hourly rate for a user/shift:
        1. If role_id is provided and that JobRole has hourly_rate > 0, and user has no personal override, use role rate.
        2. User's personal hourly_rate takes precedence if set.
        3. Otherwise fall back to role_id's hourly_rate or user's first job_role with an hourly_rate, or 0.0.
        """
        if user.hourly_rate is not None and user.hourly_rate > 0:
            return float(user.hourly_rate)
        if role_id:
            role = self.session.get(JobRole, role_id)
            if role and role.hourly_rate is not None and role.hourly_rate > 0:
                return float(role.hourly_rate)
        if user.hourly_rate is not None:
            return float(user.hourly_rate)
        for r in getattr(user, "job_roles", []) or []:
            if r.hourly_rate is not None and r.hourly_rate > 0:
                return float(r.hourly_rate)
        return 0.0

    # ═══════════════════════════════════════════════════════════════════════════
    #  Module A: Payroll, Daily Closeout & Tip Pooling
    # ═══════════════════════════════════════════════════════════════════════════

    def get_daily_closeout_summary(self, target_date: date) -> dict:
        closeout = self.session.exec(
            select(DailyCloseout).where(
                DailyCloseout.tenant_id == self.tenant_id,
                DailyCloseout.date == target_date,
            )
        ).first()

        daily_revenue = float(closeout.daily_revenue) if closeout else 0.0
        tip_pool = float(closeout.tip_pool) if closeout else 0.0

        # Confirmed attendances on target_date
        attendances = self.session.exec(
            select(Attendance)
            .join(User, Attendance.user_id == User.id)
            .where(
                Attendance.date == target_date,
                Attendance.status == AttendanceStatus.CONFIRMED,
                User.tenant_id == self.tenant_id,
            )
        ).all()

        # Scheduled shifts on target_date
        schedules = self.session.exec(
            select(Schedule)
            .join(User, Schedule.user_id == User.id)
            .where(
                Schedule.date == target_date,
                User.tenant_id == self.tenant_id,
            )
        ).all()

        scheduled_hours = 0.0
        scheduled_labor_cost = 0.0
        schedule_by_id = {}
        for sch in schedules:
            schedule_by_id[sch.id] = sch
            shift_def = self.session.get(ShiftDefinition, sch.shift_def_id)
            if shift_def and sch.user:
                hrs = self._calc_duration_hours(shift_def.start_time, shift_def.end_time, target_date)
                scheduled_hours += hrs
                rate = self.resolve_hourly_rate(sch.user, sch.role_id)
                scheduled_labor_cost += hrs * rate

        confirmed_hours_by_user: dict[UUID, float] = {}
        user_by_id: dict[UUID, User] = {}
        confirmed_labor_cost = 0.0
        total_confirmed_hours = 0.0

        for att in attendances:
            hrs = self._calc_duration_hours(att.check_in, att.check_out, target_date)
            total_confirmed_hours += hrs
            confirmed_hours_by_user[att.user_id] = confirmed_hours_by_user.get(att.user_id, 0.0) + hrs
            if att.user:
                user_by_id[att.user_id] = att.user
                role_id = None
                if att.schedule_id and att.schedule_id in schedule_by_id:
                    role_id = schedule_by_id[att.schedule_id].role_id
                rate = self.resolve_hourly_rate(att.user, role_id)
                confirmed_labor_cost += hrs * rate

        # Effective labor cost for the day: use confirmed attendance cost if any confirmed attendance exists,
        # otherwise use scheduled labor cost so manager sees live Labor Cost % during the day too.
        effective_labor_cost = confirmed_labor_cost if total_confirmed_hours > 0 else scheduled_labor_cost
        labor_cost_pct = round((effective_labor_cost / daily_revenue) * 100.0, 2) if daily_revenue > 0 else 0.0

        # Tip pooling proportional to confirmed hours
        tip_allocations = []
        for uid, u_hours in confirmed_hours_by_user.items():
            u = user_by_id.get(uid) or self.session.get(User, uid)
            share = (tip_pool * (u_hours / total_confirmed_hours)) if (tip_pool > 0 and total_confirmed_hours > 0) else 0.0
            tip_allocations.append({
                "user_id": uid,
                "user_name": u.full_name if u else "Nieznany",
                "confirmed_hours": round(u_hours, 2),
                "allocated_tip": round(share, 2),
            })

        tip_allocations.sort(key=lambda x: x["confirmed_hours"], reverse=True)

        return {
            "id": closeout.id if closeout else None,
            "date": target_date,
            "daily_revenue": round(daily_revenue, 2),
            "tip_pool": round(tip_pool, 2),
            "notes": closeout.notes if closeout else None,
            "confirmed_hours": round(total_confirmed_hours, 2),
            "scheduled_hours": round(scheduled_hours, 2),
            "labor_cost": round(effective_labor_cost, 2),
            "labor_cost_pct": labor_cost_pct,
            "is_closed_out": closeout is not None,
            "tip_allocations": tip_allocations,
        }

    def upsert_daily_closeout(self, data: DailyCloseoutCreate, manager_id: UUID) -> dict:
        closeout = self.session.exec(
            select(DailyCloseout).where(
                DailyCloseout.tenant_id == self.tenant_id,
                DailyCloseout.date == data.date,
            )
        ).first()

        if closeout:
            closeout.daily_revenue = data.daily_revenue
            closeout.tip_pool = data.tip_pool
            closeout.notes = data.notes
            closeout.updated_at = datetime.now(timezone.utc)
        else:
            closeout = DailyCloseout(
                tenant_id=self.tenant_id,
                date=data.date,
                daily_revenue=data.daily_revenue,
                tip_pool=data.tip_pool,
                notes=data.notes,
                created_by=manager_id,
            )

        self.session.add(closeout)
        self.session.commit()
        self.session.refresh(closeout)
        return self.get_daily_closeout_summary(data.date)

    def get_closeouts_range(self, start_date: date, end_date: date) -> List[dict]:
        closeouts = self.session.exec(
            select(DailyCloseout)
            .where(
                DailyCloseout.tenant_id == self.tenant_id,
                DailyCloseout.date >= start_date,
                DailyCloseout.date <= end_date,
            )
            .order_by(DailyCloseout.date.desc())
        ).all()
        return [self.get_daily_closeout_summary(c.date) for c in closeouts]

    def get_monthly_payroll(self, year: int, month: int) -> dict:
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        employees = self.session.exec(
            select(User).where(
                User.tenant_id == self.tenant_id,
                User.role_system == RoleSystem.EMPLOYEE,
            )
        ).all()

        attendances = self.session.exec(
            select(Attendance)
            .join(User, Attendance.user_id == User.id)
            .where(
                Attendance.date >= first_day,
                Attendance.date <= last_day,
                User.tenant_id == self.tenant_id,
            )
        ).all()

        schedules = self.session.exec(
            select(Schedule)
            .join(User, Schedule.user_id == User.id)
            .where(
                Schedule.date >= first_day,
                Schedule.date <= last_day,
                User.tenant_id == self.tenant_id,
            )
        ).all()
        schedule_by_id = {s.id: s for s in schedules}

        closeouts = self.session.exec(
            select(DailyCloseout).where(
                DailyCloseout.tenant_id == self.tenant_id,
                DailyCloseout.date >= first_day,
                DailyCloseout.date <= last_day,
            )
        ).all()
        closeout_by_date = {c.date: c for c in closeouts}
        total_monthly_revenue = sum(float(c.daily_revenue) for c in closeouts)

        # Group confirmed hours by date to compute daily tip pool distribution
        daily_confirmed_by_user: dict[date, dict[UUID, float]] = {}
        daily_total_confirmed: dict[date, float] = {}

        emp_stats: dict[UUID, dict] = {}
        for emp in employees:
            emp_stats[emp.id] = {
                "user": emp,
                "confirmed_hours": 0.0,
                "pending_hours": 0.0,
                "shifts_count": 0,
                "base_pay": 0.0,
                "allocated_tips": 0.0,
            }

        for att in attendances:
            if att.user_id not in emp_stats and att.user:
                emp_stats[att.user_id] = {
                    "user": att.user,
                    "confirmed_hours": 0.0,
                    "pending_hours": 0.0,
                    "shifts_count": 0,
                    "base_pay": 0.0,
                    "allocated_tips": 0.0,
                }
            if att.user_id not in emp_stats:
                continue

            hrs = self._calc_duration_hours(att.check_in, att.check_out, att.date)
            role_id = None
            if att.schedule_id and att.schedule_id in schedule_by_id:
                role_id = schedule_by_id[att.schedule_id].role_id
            rate = self.resolve_hourly_rate(emp_stats[att.user_id]["user"], role_id)

            if att.status == AttendanceStatus.CONFIRMED:
                emp_stats[att.user_id]["confirmed_hours"] += hrs
                emp_stats[att.user_id]["shifts_count"] += 1
                emp_stats[att.user_id]["base_pay"] += hrs * rate

                daily_confirmed_by_user.setdefault(att.date, {})
                daily_confirmed_by_user[att.date][att.user_id] = (
                    daily_confirmed_by_user[att.date].get(att.user_id, 0.0) + hrs
                )
                daily_total_confirmed[att.date] = daily_total_confirmed.get(att.date, 0.0) + hrs
            elif att.status == AttendanceStatus.PENDING:
                emp_stats[att.user_id]["pending_hours"] += hrs

        # Allocate tips per day
        for d, closeout in closeout_by_date.items():
            if closeout.tip_pool > 0 and daily_total_confirmed.get(d, 0.0) > 0:
                day_tot = daily_total_confirmed[d]
                for uid, u_hrs in daily_confirmed_by_user.get(d, {}).items():
                    if uid in emp_stats:
                        emp_stats[uid]["allocated_tips"] += float(closeout.tip_pool) * (u_hrs / day_tot)

        items = []
        total_confirmed_hours = 0.0
        total_pending_hours = 0.0
        total_base_pay = 0.0
        total_tips = 0.0

        for uid, st in emp_stats.items():
            user_obj = st["user"]
            eff_rate = self.resolve_hourly_rate(user_obj)
            c_hrs = round(st["confirmed_hours"], 2)
            p_hrs = round(st["pending_hours"], 2)
            b_pay = round(st["base_pay"], 2)
            tips = round(st["allocated_tips"], 2)
            tot = round(b_pay + tips, 2)

            total_confirmed_hours += c_hrs
            total_pending_hours += p_hrs
            total_base_pay += b_pay
            total_tips += tips

            items.append({
                "user_id": uid,
                "user_name": user_obj.full_name,
                "hourly_rate": round(eff_rate, 2),
                "confirmed_hours": c_hrs,
                "pending_hours": p_hrs,
                "shifts_count": st["shifts_count"],
                "base_pay": b_pay,
                "allocated_tips": tips,
                "total_pay": tot,
            })

        items.sort(key=lambda x: x["total_pay"], reverse=True)
        total_payroll = round(total_base_pay + total_tips, 2)
        monthly_labor_cost_pct = (
            round((total_base_pay / total_monthly_revenue) * 100.0, 2)
            if total_monthly_revenue > 0
            else 0.0
        )

        return {
            "year": year,
            "month": month,
            "items": items,
            "total_confirmed_hours": round(total_confirmed_hours, 2),
            "total_pending_hours": round(total_pending_hours, 2),
            "total_base_pay": round(total_base_pay, 2),
            "total_tips": round(total_tips, 2),
            "total_payroll": total_payroll,
            "total_monthly_revenue": round(total_monthly_revenue, 2),
            "monthly_labor_cost_pct": monthly_labor_cost_pct,
        }

    def get_employee_monthly_earnings(self, user: User, year: int, month: int) -> dict:
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # Compute full monthly context to get accurate tip pool shares per day
        attendances_all = self.session.exec(
            select(Attendance)
            .join(User, Attendance.user_id == User.id)
            .where(
                Attendance.date >= first_day,
                Attendance.date <= last_day,
                Attendance.status == AttendanceStatus.CONFIRMED,
                User.tenant_id == self.tenant_id,
            )
        ).all()

        daily_total_confirmed: dict[date, float] = {}
        for att in attendances_all:
            hrs = self._calc_duration_hours(att.check_in, att.check_out, att.date)
            daily_total_confirmed[att.date] = daily_total_confirmed.get(att.date, 0.0) + hrs

        closeouts = self.session.exec(
            select(DailyCloseout).where(
                DailyCloseout.tenant_id == self.tenant_id,
                DailyCloseout.date >= first_day,
                DailyCloseout.date <= last_day,
            )
        ).all()
        closeout_by_date = {c.date: c for c in closeouts}

        my_attendances = self.session.exec(
            select(Attendance)
            .where(
                Attendance.user_id == user.id,
                Attendance.date >= first_day,
                Attendance.date <= last_day,
            )
            .order_by(Attendance.date.desc())
        ).all()

        confirmed_hours = 0.0
        pending_hours = 0.0
        base_pay = 0.0
        allocated_tips = 0.0
        daily_breakdown = []

        for att in my_attendances:
            hrs = self._calc_duration_hours(att.check_in, att.check_out, att.date)
            role_id = None
            if att.schedule_id:
                sch = self.session.get(Schedule, att.schedule_id)
                if sch:
                    role_id = sch.role_id
            rate = self.resolve_hourly_rate(user, role_id)

            day_base = 0.0
            day_tip = 0.0
            if att.status == AttendanceStatus.CONFIRMED:
                confirmed_hours += hrs
                day_base = hrs * rate
                base_pay += day_base
                c = closeout_by_date.get(att.date)
                tot_day_hrs = daily_total_confirmed.get(att.date, 0.0)
                if c and c.tip_pool > 0 and tot_day_hrs > 0:
                    day_tip = float(c.tip_pool) * (hrs / tot_day_hrs)
                    allocated_tips += day_tip
            elif att.status == AttendanceStatus.PENDING:
                pending_hours += hrs

            daily_breakdown.append({
                "date": att.date,
                "status": att.status.value,
                "hours": round(hrs, 2),
                "hourly_rate": round(rate, 2),
                "base_pay": round(day_base, 2),
                "allocated_tip": round(day_tip, 2),
                "total_pay": round(day_base + day_tip, 2),
            })

        return {
            "year": year,
            "month": month,
            "user_id": user.id,
            "user_name": user.full_name,
            "hourly_rate": round(self.resolve_hourly_rate(user), 2),
            "confirmed_hours": round(confirmed_hours, 2),
            "pending_hours": round(pending_hours, 2),
            "base_pay": round(base_pay, 2),
            "allocated_tips": round(allocated_tips, 2),
            "total_pay": round(base_pay + allocated_tips, 2),
            "daily_breakdown": daily_breakdown,
        }

    def export_monthly_payroll_csv(self, year: int, month: int) -> BytesIO:
        summary = self.get_monthly_payroll(year, month)
        str_io = StringIO()
        writer = csv.writer(str_io, delimiter=";")
        writer.writerow([
            "Pracownik",
            "Stawka godzinowa (PLN)",
            "Godziny zatwierdzone",
            "Godziny oczekujace",
            "Liczba zmian",
            "Wynagrodzenie bazowe (PLN)",
            "Napiwki z puli (PLN)",
            "Suma do wyplaty (PLN)",
        ])
        for item in summary["items"]:
            writer.writerow([
                item["user_name"],
                f"{item['hourly_rate']:.2f}",
                f"{item['confirmed_hours']:.2f}",
                f"{item['pending_hours']:.2f}",
                item["shifts_count"],
                f"{item['base_pay']:.2f}",
                f"{item['allocated_tips']:.2f}",
                f"{item['total_pay']:.2f}",
            ])
        writer.writerow([])
        writer.writerow([
            "RAZEM",
            "",
            f"{summary['total_confirmed_hours']:.2f}",
            f"{summary['total_pending_hours']:.2f}",
            "",
            f"{summary['total_base_pay']:.2f}",
            f"{summary['total_tips']:.2f}",
            f"{summary['total_payroll']:.2f}",
        ])
        buffer = BytesIO(str_io.getvalue().encode("utf-8-sig"))
        buffer.seek(0)
        return buffer

    def export_monthly_payroll_pdf(self, year: int, month: int) -> BytesIO:
        summary = self.get_monthly_payroll(year, month)
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50

        p.setFont("Helvetica-Bold", 16)
        p.drawString(40, y, f"Payroll Report / Lista Plac: {year}-{month:02d}")
        y -= 25

        p.setFont("Helvetica", 10)
        p.drawString(
            40,
            y,
            f"Utarg miesieczny: {summary['total_monthly_revenue']:.2f} PLN | "
            f"Koszt pracy (baza): {summary['total_base_pay']:.2f} PLN | "
            f"Labor Cost: {summary['monthly_labor_cost_pct']:.1f}%",
        )
        y -= 25

        # Table header
        p.setFont("Helvetica-Bold", 9)
        p.drawString(40, y, "Pracownik")
        p.drawString(180, y, "Stawka")
        p.drawString(235, y, "Godz. zatw.")
        p.drawString(300, y, "Godz. oczek.")
        p.drawString(370, y, "Podstawa")
        p.drawString(440, y, "Napiwki")
        p.drawString(500, y, "Suma PLN")
        p.line(40, y - 5, 555, y - 5)
        y -= 20

        p.setFont("Helvetica", 9)
        for item in summary["items"]:
            if y < 60:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 9)
            p.drawString(40, y, str(item["user_name"])[:25])
            p.drawString(180, y, f"{item['hourly_rate']:.2f}")
            p.drawString(235, y, f"{item['confirmed_hours']:.1f}h")
            p.drawString(300, y, f"{item['pending_hours']:.1f}h")
            p.drawString(370, y, f"{item['base_pay']:.2f}")
            p.drawString(440, y, f"{item['allocated_tips']:.2f}")
            p.drawString(500, y, f"{item['total_pay']:.2f}")
            y -= 16

        y -= 10
        p.line(40, y + 8, 555, y + 8)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(40, y - 5, "RAZEM:")
        p.drawString(235, y - 5, f"{summary['total_confirmed_hours']:.1f}h")
        p.drawString(300, y - 5, f"{summary['total_pending_hours']:.1f}h")
        p.drawString(370, y - 5, f"{summary['total_base_pay']:.2f}")
        p.drawString(440, y - 5, f"{summary['total_tips']:.2f}")
        p.drawString(500, y - 5, f"{summary['total_payroll']:.2f}")

        p.save()
        buffer.seek(0)
        return buffer

    # ═══════════════════════════════════════════════════════════════════════════
    #  Module B.1: Operational Checklists
    # ═══════════════════════════════════════════════════════════════════════════

    def _serialize_checklist_template(self, tpl: ChecklistTemplate) -> dict:
        role = self.session.get(JobRole, tpl.role_id) if tpl.role_id else None
        items = self.session.exec(
            select(ChecklistTemplateItem)
            .where(ChecklistTemplateItem.template_id == tpl.id)
            .order_by(ChecklistTemplateItem.sort_order)
        ).all()
        return {
            "id": tpl.id,
            "title": tpl.title,
            "description": tpl.description,
            "role_id": tpl.role_id,
            "role_name": role.name if role else None,
            "shift_period": tpl.shift_period,
            "is_mandatory": tpl.is_mandatory,
            "is_active": tpl.is_active,
            "created_at": tpl.created_at,
            "items": [
                {
                    "id": it.id,
                    "template_id": it.template_id,
                    "title": it.title,
                    "is_mandatory": it.is_mandatory,
                    "sort_order": it.sort_order,
                }
                for it in items
            ],
        }

    def create_checklist_template(self, data: ChecklistTemplateCreate) -> dict:
        if data.role_id is not None:
            role = self.session.get(JobRole, data.role_id)
            if not role or role.tenant_id != self.tenant_id:
                raise HTTPException(status_code=404, detail="Role not found")

        tpl = ChecklistTemplate(
            tenant_id=self.tenant_id,
            title=data.title,
            description=data.description,
            role_id=data.role_id,
            shift_period=data.shift_period,
            is_mandatory=data.is_mandatory,
            is_active=data.is_active,
        )
        self.session.add(tpl)
        self.session.commit()
        self.session.refresh(tpl)

        for idx, item_in in enumerate(data.items):
            item = ChecklistTemplateItem(
                template_id=tpl.id,
                title=item_in.title,
                is_mandatory=item_in.is_mandatory,
                sort_order=item_in.sort_order if item_in.sort_order else idx,
            )
            self.session.add(item)
        self.session.commit()
        self.session.refresh(tpl)
        return self._serialize_checklist_template(tpl)

    def get_checklist_templates(self, include_inactive: bool = False) -> List[dict]:
        query = select(ChecklistTemplate).where(ChecklistTemplate.tenant_id == self.tenant_id)
        if not include_inactive:
            query = query.where(ChecklistTemplate.is_active == True)
        templates = self.session.exec(query.order_by(ChecklistTemplate.created_at.desc())).all()
        return [self._serialize_checklist_template(t) for t in templates]

    def update_checklist_template(self, template_id: UUID, data: ChecklistTemplateCreate) -> dict:
        tpl = self.session.get(ChecklistTemplate, template_id)
        if not tpl or tpl.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Checklist template not found")

        if data.role_id is not None:
            role = self.session.get(JobRole, data.role_id)
            if not role or role.tenant_id != self.tenant_id:
                raise HTTPException(status_code=404, detail="Role not found")

        tpl.title = data.title
        tpl.description = data.description
        tpl.role_id = data.role_id
        tpl.shift_period = data.shift_period
        tpl.is_mandatory = data.is_mandatory
        tpl.is_active = data.is_active
        self.session.add(tpl)

        if data.items is not None:
            old_items = self.session.exec(
                select(ChecklistTemplateItem).where(ChecklistTemplateItem.template_id == tpl.id)
            ).all()
            for old in old_items:
                self.session.delete(old)
            for idx, item_in in enumerate(data.items):
                self.session.add(
                    ChecklistTemplateItem(
                        template_id=tpl.id,
                        title=item_in.title,
                        is_mandatory=item_in.is_mandatory,
                        sort_order=item_in.sort_order if item_in.sort_order else idx,
                    )
                )

        self.session.commit()
        self.session.refresh(tpl)
        return self._serialize_checklist_template(tpl)

    def delete_checklist_template(self, template_id: UUID) -> None:
        tpl = self.session.get(ChecklistTemplate, template_id)
        if not tpl or tpl.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Checklist template not found")
        completions = self.session.exec(
            select(ChecklistCompletion).where(ChecklistCompletion.template_id == tpl.id)
        ).all()
        for c in completions:
            self.session.delete(c)
        items = self.session.exec(
            select(ChecklistTemplateItem).where(ChecklistTemplateItem.template_id == tpl.id)
        ).all()
        for it in items:
            self.session.delete(it)
        self.session.delete(tpl)
        self.session.commit()

    def _get_applicable_templates_for_user(self, user: User, target_date: date) -> List[ChecklistTemplate]:
        templates = self.session.exec(
            select(ChecklistTemplate).where(
                ChecklistTemplate.tenant_id == self.tenant_id,
                ChecklistTemplate.is_active == True,
            )
        ).all()
        if user.role_system in (RoleSystem.MANAGER, RoleSystem.ADMIN):
            return list(templates)

        # Roles from employee's scheduled shift on target_date OR employee's assigned job_roles
        scheduled = self.session.exec(
            select(Schedule).where(
                Schedule.user_id == user.id,
                Schedule.date == target_date,
            )
        ).all()
        active_role_ids = {s.role_id for s in scheduled if s.role_id is not None}
        if not active_role_ids:
            active_role_ids = {r.id for r in (user.job_roles or []) if r.id is not None}

        applicable = []
        for tpl in templates:
            if tpl.role_id is None or tpl.role_id in active_role_ids or not active_role_ids:
                applicable.append(tpl)
        return applicable

    def get_employee_checklists(self, user: User, target_date: date) -> List[dict]:
        templates = self._get_applicable_templates_for_user(user, target_date)
        completions = self.session.exec(
            select(ChecklistCompletion).where(
                ChecklistCompletion.tenant_id == self.tenant_id,
                ChecklistCompletion.date == target_date,
                ChecklistCompletion.is_completed == True,
            )
        ).all()
        comp_by_item = {c.item_id: c for c in completions}

        result = []
        for tpl in templates:
            role = self.session.get(JobRole, tpl.role_id) if tpl.role_id else None
            items = self.session.exec(
                select(ChecklistTemplateItem)
                .where(ChecklistTemplateItem.template_id == tpl.id)
                .order_by(ChecklistTemplateItem.sort_order)
            ).all()
            item_views = []
            completed_cnt = 0
            for it in items:
                comp = comp_by_item.get(it.id)
                comp_user = self.session.get(User, comp.user_id) if comp else None
                if comp and comp.is_completed:
                    completed_cnt += 1
                item_views.append({
                    "id": it.id,
                    "template_id": tpl.id,
                    "title": it.title,
                    "is_mandatory": it.is_mandatory,
                    "sort_order": it.sort_order,
                    "is_completed": bool(comp and comp.is_completed),
                    "completed_at": comp.completed_at if comp else None,
                    "completed_by_user_id": comp.user_id if comp else None,
                    "completed_by_user_name": comp_user.full_name if comp_user else None,
                })
            result.append({
                "id": tpl.id,
                "title": tpl.title,
                "description": tpl.description,
                "role_id": tpl.role_id,
                "role_name": role.name if role else None,
                "shift_period": tpl.shift_period,
                "is_mandatory": tpl.is_mandatory,
                "date": target_date,
                "items": item_views,
                "completed_count": completed_cnt,
                "total_count": len(item_views),
            })
        return result

    def toggle_checklist_item(
        self,
        user: User,
        item_id: UUID,
        target_date: date,
        is_completed: Optional[bool] = None,
    ) -> dict:
        item = self.session.get(ChecklistTemplateItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        tpl = self.session.get(ChecklistTemplate, item.template_id)
        if not tpl or tpl.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Checklist template not found")

        existing = self.session.exec(
            select(ChecklistCompletion).where(
                ChecklistCompletion.tenant_id == self.tenant_id,
                ChecklistCompletion.item_id == item.id,
                ChecklistCompletion.date == target_date,
            )
        ).first()

        new_state = (not existing.is_completed) if (existing and is_completed is None) else (True if is_completed is None else is_completed)

        if existing:
            existing.is_completed = new_state
            existing.user_id = user.id
            existing.completed_at = datetime.now(timezone.utc)
            self.session.add(existing)
            comp = existing
        else:
            comp = ChecklistCompletion(
                tenant_id=self.tenant_id,
                template_id=tpl.id,
                item_id=item.id,
                date=target_date,
                user_id=user.id,
                is_completed=new_state,
                completed_at=datetime.now(timezone.utc),
            )
            self.session.add(comp)

        self.session.commit()
        self.session.refresh(comp)
        return {
            "id": item.id,
            "template_id": tpl.id,
            "title": item.title,
            "is_mandatory": item.is_mandatory,
            "sort_order": item.sort_order,
            "is_completed": comp.is_completed,
            "completed_at": comp.completed_at,
            "completed_by_user_id": user.id,
            "completed_by_user_name": user.full_name,
        }

    def validate_clockout_checklists(self, user: User, target_date: date) -> dict:
        checklists = self.get_employee_checklists(user, target_date)
        missing_items = []
        for cl in checklists:
            if not cl["is_mandatory"]:
                continue
            for it in cl["items"]:
                if it["is_mandatory"] and not it["is_completed"]:
                    missing_items.append({
                        "template_id": cl["id"],
                        "template_title": cl["title"],
                        "item_id": it["id"],
                        "item_title": it["title"],
                        "shift_period": cl["shift_period"],
                    })
        return {
            "date": target_date,
            "all_mandatory_completed": len(missing_items) == 0,
            "missing_mandatory_count": len(missing_items),
            "missing_items": missing_items,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  Module B.2: Digital HACCP Registry
    # ═══════════════════════════════════════════════════════════════════════════

    def create_haccp_device(self, data: HaccpDeviceCreate) -> HaccpDevice:
        device = HaccpDevice(
            tenant_id=self.tenant_id,
            name=data.name,
            min_temp=data.min_temp,
            max_temp=data.max_temp,
            is_active=data.is_active,
        )
        self.session.add(device)
        self.session.commit()
        self.session.refresh(device)
        return device

    def get_haccp_devices(self, active_only: bool = True) -> List[HaccpDevice]:
        q = select(HaccpDevice).where(HaccpDevice.tenant_id == self.tenant_id)
        if active_only:
            q = q.where(HaccpDevice.is_active == True)
        return list(self.session.exec(q.order_by(HaccpDevice.name)).all())

    def delete_haccp_device(self, device_id: UUID) -> None:
        device = self.session.get(HaccpDevice, device_id)
        if not device or device.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="HACCP device not found")
        device.is_active = False
        self.session.add(device)
        self.session.commit()

    def create_haccp_log(self, user: User, data: HaccpLogCreate) -> dict:
        device_name = data.device_name
        min_temp = data.min_temp
        max_temp = data.max_temp

        if data.device_id:
            device = self.session.get(HaccpDevice, data.device_id)
            if not device or device.tenant_id != self.tenant_id:
                raise HTTPException(status_code=404, detail="HACCP device not found")
            device_name = device.name
            if min_temp is None:
                min_temp = device.min_temp
            if max_temp is None:
                max_temp = device.max_temp

        if not device_name or not device_name.strip():
            raise HTTPException(status_code=400, detail="device_name or valid device_id is required")

        is_within_norm = True
        if data.log_type == HaccpLogType.TEMPERATURE:
            if data.measured_temp is None:
                raise HTTPException(status_code=400, detail="measured_temp is required for TEMPERATURE logs")
            if min_temp is not None and data.measured_temp < min_temp:
                is_within_norm = False
            if max_temp is not None and data.measured_temp > max_temp:
                is_within_norm = False

        log_entry = HaccpLog(
            tenant_id=self.tenant_id,
            log_type=data.log_type,
            device_id=data.device_id,
            device_name=device_name.strip(),
            min_temp=min_temp,
            max_temp=max_temp,
            measured_temp=data.measured_temp,
            is_within_norm=is_within_norm,
            corrective_action=data.corrective_action,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(log_entry)
        self.session.commit()
        self.session.refresh(log_entry)

        return {
            "id": log_entry.id,
            "log_type": log_entry.log_type,
            "device_id": log_entry.device_id,
            "device_name": log_entry.device_name,
            "min_temp": log_entry.min_temp,
            "max_temp": log_entry.max_temp,
            "measured_temp": log_entry.measured_temp,
            "is_within_norm": log_entry.is_within_norm,
            "corrective_action": log_entry.corrective_action,
            "user_id": log_entry.user_id,
            "user_name": user.full_name,
            "created_at": log_entry.created_at,
        }

    def get_haccp_logs(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        violations_only: bool = False,
    ) -> List[dict]:
        q = select(HaccpLog).where(HaccpLog.tenant_id == self.tenant_id)
        if start_date:
            start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
            q = q.where(HaccpLog.created_at >= start_dt)
        if end_date:
            end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)
            q = q.where(HaccpLog.created_at <= end_dt)
        if violations_only:
            q = q.where(HaccpLog.is_within_norm == False)

        logs = self.session.exec(q.order_by(HaccpLog.created_at.desc())).all()
        result = []
        for l in logs:
            u = self.session.get(User, l.user_id)
            result.append({
                "id": l.id,
                "log_type": l.log_type,
                "device_id": l.device_id,
                "device_name": l.device_name,
                "min_temp": l.min_temp,
                "max_temp": l.max_temp,
                "measured_temp": l.measured_temp,
                "is_within_norm": l.is_within_norm,
                "corrective_action": l.corrective_action,
                "user_id": l.user_id,
                "user_name": u.full_name if u else "Nieznany",
                "created_at": l.created_at,
            })
        return result

    def export_haccp_pdf(self, start_date: date, end_date: date) -> BytesIO:
        logs = self.get_haccp_logs(start_date=start_date, end_date=end_date)
        config = self.session.get(RestaurantConfig, self.tenant_id)
        venue_name = config.name if config else "Lokal Gastronomiczny"

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50

        p.setFont("Helvetica-Bold", 15)
        p.drawString(40, y, f"Karta Kontroli HACCP (Sanepid) - {venue_name}")
        y -= 20
        p.setFont("Helvetica", 10)
        p.drawString(40, y, f"Okres raportu: {start_date.isoformat()} do {end_date.isoformat()}")
        y -= 25

        p.setFont("Helvetica-Bold", 9)
        p.drawString(40, y, "Data / Czas")
        p.drawString(135, y, "Urzadzenie / Obszar")
        p.drawString(260, y, "Norma")
        p.drawString(320, y, "Pomiar")
        p.drawString(375, y, "Status")
        p.drawString(430, y, "Podpis cyfrowy")
        p.line(40, y - 5, 555, y - 5)
        y -= 18

        p.setFont("Helvetica", 8)
        for l in logs:
            if y < 65:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 8)

            dt_str = l["created_at"].strftime("%Y-%m-%d %H:%M")
            norm_str = (
                f"{l['min_temp']}..{l['max_temp']} C"
                if l["min_temp"] is not None and l["max_temp"] is not None
                else "-"
            )
            meas_str = (
                f"{l['measured_temp']:.1f} C"
                if l["measured_temp"] is not None
                else ("WYKONANO" if l["log_type"] == HaccpLogType.SANITATION else "-")
            )
            status_str = "OK" if l["is_within_norm"] else "PRZEKROCZENIE!"

            if not l["is_within_norm"]:
                p.setFillColor(colors.red)
            else:
                p.setFillColor(colors.black)

            p.drawString(40, y, dt_str)
            p.drawString(135, y, str(l["device_name"])[:22])
            p.drawString(260, y, norm_str)
            p.drawString(320, y, meas_str)
            p.drawString(375, y, status_str)
            p.drawString(430, y, f"{l['user_name'][:18]} ({str(l['user_id'])[:6]})")
            y -= 14

            if l.get("corrective_action"):
                p.setFont("Helvetica-Oblique", 8)
                p.drawString(60, y, f"Uwaga korygujaca: {l['corrective_action']}")
                p.setFont("Helvetica", 8)
                y -= 14

        p.setFillColor(colors.black)
        p.save()
        buffer.seek(0)
        return buffer

    # ═══════════════════════════════════════════════════════════════════════════
    #  Module C: Announcement Board with Read Receipts
    # ═══════════════════════════════════════════════════════════════════════════

    def create_announcement(
        self,
        author: User,
        data: AnnouncementCreate,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> dict:
        ann = Announcement(
            tenant_id=self.tenant_id,
            author_id=author.id,
            title=data.title,
            content=data.content,
            is_pinned=data.is_pinned,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(ann)
        self.session.commit()
        self.session.refresh(ann)

        # Notify all active employees in the same tenant
        active_employees = self.session.exec(
            select(User).where(
                User.tenant_id == self.tenant_id,
                User.is_active == True,
                User.role_system == RoleSystem.EMPLOYEE,
            )
        ).all()

        push_svc = PushService(self.session)
        notif_title = f"Nowe ogłoszenie: {ann.title}"
        notif_body = ann.content[:180] + ("..." if len(ann.content) > 180 else "")

        all_tokens: List[str] = []
        for emp in active_employees:
            self.session.add(
                Notification(
                    user_id=emp.id,
                    title=notif_title,
                    body=notif_body,
                )
            )
            all_tokens.extend(push_svc._get_user_tokens(emp.id))

        self.session.commit()

        if all_tokens:
            push_data = {"type": "ANNOUNCEMENT", "announcement_id": str(ann.id)}
            if background_tasks is not None:
                background_tasks.add_task(send_push_to_tokens, all_tokens, notif_title, notif_body, push_data)
            else:
                send_push_to_tokens(all_tokens, notif_title, notif_body, push_data, session=self.session)

        return self._serialize_manager_announcement(ann, active_employees)

    def _serialize_manager_announcement(
        self,
        ann: Announcement,
        active_employees: Optional[List[User]] = None,
    ) -> dict:
        if active_employees is None:
            active_employees = list(
                self.session.exec(
                    select(User).where(
                        User.tenant_id == self.tenant_id,
                        User.is_active == True,
                        User.role_system == RoleSystem.EMPLOYEE,
                    )
                ).all()
            )
        author = self.session.get(User, ann.author_id)
        receipts = self.session.exec(
            select(AnnouncementReadReceipt).where(
                AnnouncementReadReceipt.announcement_id == ann.id
            )
        ).all()
        receipt_by_user = {r.user_id: r for r in receipts}

        read_by = []
        unread_by = []
        for emp in active_employees:
            rec = receipt_by_user.get(emp.id)
            if rec:
                read_by.append({
                    "user_id": emp.id,
                    "user_name": emp.full_name,
                    "read_at": rec.read_at,
                })
            else:
                unread_by.append({
                    "user_id": emp.id,
                    "user_name": emp.full_name,
                    "read_at": None,
                })

        # Also include any non-active or manager readers who confirmed
        active_ids = {e.id for e in active_employees}
        for r in receipts:
            if r.user_id not in active_ids:
                u = self.session.get(User, r.user_id)
                if u:
                    read_by.append({
                        "user_id": u.id,
                        "user_name": u.full_name,
                        "read_at": r.read_at,
                    })

        return {
            "id": ann.id,
            "title": ann.title,
            "content": ann.content,
            "is_pinned": ann.is_pinned,
            "author_id": ann.author_id,
            "author_name": author.full_name if author else "Manager",
            "created_at": ann.created_at,
            "read_count": len(read_by),
            "total_target_count": max(len(active_employees), len(read_by)),
            "read_by": read_by,
            "unread_by": unread_by,
        }

    def get_manager_announcements(self) -> List[dict]:
        announcements = self.session.exec(
            select(Announcement)
            .where(Announcement.tenant_id == self.tenant_id)
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        ).all()
        active_employees = list(
            self.session.exec(
                select(User).where(
                    User.tenant_id == self.tenant_id,
                    User.is_active == True,
                    User.role_system == RoleSystem.EMPLOYEE,
                )
            ).all()
        )
        return [self._serialize_manager_announcement(a, active_employees) for a in announcements]

    def get_announcement_receipts(self, announcement_id: UUID) -> dict:
        ann = self.session.get(Announcement, announcement_id)
        if not ann or ann.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Announcement not found")
        return self._serialize_manager_announcement(ann)

    def delete_announcement(self, announcement_id: UUID) -> None:
        ann = self.session.get(Announcement, announcement_id)
        if not ann or ann.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Announcement not found")
        receipts = self.session.exec(
            select(AnnouncementReadReceipt).where(
                AnnouncementReadReceipt.announcement_id == ann.id
            )
        ).all()
        for r in receipts:
            self.session.delete(r)
        self.session.delete(ann)
        self.session.commit()

    def get_employee_announcements(self, user: User) -> List[dict]:
        announcements = self.session.exec(
            select(Announcement)
            .where(Announcement.tenant_id == self.tenant_id)
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        ).all()
        receipts = self.session.exec(
            select(AnnouncementReadReceipt).where(
                AnnouncementReadReceipt.user_id == user.id,
                AnnouncementReadReceipt.tenant_id == self.tenant_id,
            )
        ).all()
        receipt_map = {r.announcement_id: r for r in receipts}

        items = []
        for a in announcements:
            author = self.session.get(User, a.author_id)
            rec = receipt_map.get(a.id)
            items.append({
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "is_pinned": a.is_pinned,
                "author_id": a.author_id,
                "author_name": author.full_name if author else "Manager",
                "created_at": a.created_at,
                "is_read": rec is not None,
                "read_at": rec.read_at if rec else None,
            })

        # Unread announcements highlighted at the top, then pinned, then newest
        items.sort(
            key=lambda x: (
                0 if not x["is_read"] else 1,
                0 if x["is_pinned"] else 1,
                -x["created_at"].timestamp(),
            )
        )
        return items

    def mark_announcement_read(self, user: User, announcement_id: UUID) -> dict:
        ann = self.session.get(Announcement, announcement_id)
        if not ann or ann.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Announcement not found")

        existing = self.session.exec(
            select(AnnouncementReadReceipt).where(
                AnnouncementReadReceipt.announcement_id == ann.id,
                AnnouncementReadReceipt.user_id == user.id,
            )
        ).first()

        if not existing:
            existing = AnnouncementReadReceipt(
                tenant_id=self.tenant_id,
                announcement_id=ann.id,
                user_id=user.id,
                read_at=datetime.now(timezone.utc),
            )
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)

        return {
            "status": "read",
            "announcement_id": str(ann.id),
            "user_id": str(user.id),
            "read_at": existing.read_at.isoformat(),
        }
