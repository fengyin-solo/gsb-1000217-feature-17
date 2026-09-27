"""能效分析业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "energy_saving"
REQUIRED_FIELDS = ["报告编号", "电站编号", "分析周期"]
STATUS_ORDER = ["待生成", "已生成", "已审阅", "已归档"]
ACTION_RULES = {"生成报告": "已生成", "审阅确认": "已审阅", "归档报告": "已归档"}
NEGATIVE_ACTIONS = []
LOSS_FIELD = "损失明细"
UNCATEGORIZED = "未分类"


def _to_number(value: Any) -> float:
    """把数值字段统一成 float；空串、None、非法值都按 0 处理，不抛异常。"""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


class EnergySavingService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("报告编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        """报告明细：在原始记录上补一份归一化后的损失构成，与看板用同一套口径。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        detail = dict(entry)
        detail["损失构成"] = self._loss_breakdown([entry])
        return detail

    def dashboard(self, period: str | None = None) -> dict[str, Any]:
        """按分析周期聚合对比看板，与报告明细读同一份 store 数据。

        指定周期没有数据时返回该周期的空指标，不回退沿用其它周期的数字。
        """
        rows = store.rows(MODULE)
        periods = sorted({
            str(row.get("分析周期") or "").strip()
            for row in rows
            if str(row.get("分析周期") or "").strip()
        })
        selected = (period or "").strip() or (periods[-1] if periods else "")
        scoped = [row for row in rows if str(row.get("分析周期") or "").strip() == selected]

        efficiency, theory, actual = self._efficiency(scoped)
        trend = []
        for name in periods:
            period_rows = [row for row in rows if str(row.get("分析周期") or "").strip() == name]
            p_eff, p_theory, p_actual = self._efficiency(period_rows)
            trend.append({
                "分析周期": name,
                "系统效率": p_eff,
                "损失电量": round(p_theory - p_actual, 1),
                "报告数": len(period_rows),
            })

        return {
            "periods": periods,
            "period": selected,
            "cards": {
                "系统效率": efficiency,
                "理论发电量": round(theory, 1),
                "实际发电量": round(actual, 1),
                "损失电量": round(theory - actual, 1),
                "报告数": len(scoped),
            },
            "loss": self._loss_breakdown(scoped),
            "status": {status: sum(1 for row in scoped if row.get("status") == status) for status in STATUS_ORDER},
            "trend": trend,
            "reports": [
                {
                    "id": row.get("id"),
                    "报告编号": row.get("报告编号"),
                    "电站编号": row.get("电站编号"),
                    "分析周期": row.get("分析周期"),
                    "系统效率": row.get("系统效率"),
                    "报告状态": row.get("status"),
                }
                for row in scoped
            ],
        }

    @staticmethod
    def _efficiency(rows: list[dict[str, Any]]) -> tuple[float | None, float, float]:
        """系统效率按口径 实际合计/理论合计 计算；理论为 0 时返回 None 而不是硬凑数字。"""
        theory = sum(_to_number(row.get("理论发电量")) for row in rows)
        actual = sum(_to_number(row.get("实际发电量")) for row in rows)
        efficiency = round(actual / theory * 100, 1) if theory > 0 else None
        return efficiency, theory, actual

    @staticmethod
    def _loss_breakdown(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """汇总损失构成：明细里没写原因的归入「未分类」单独展示；
        理论-实际与明细合计对不上的差额也并入「未分类」，保证构成与发电量吻合。"""
        bucket: dict[str, float] = {}
        for row in rows:
            declared = 0.0
            items = row.get(LOSS_FIELD)
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    reason = str(item.get("原因") or "").strip() or UNCATEGORIZED
                    amount = _to_number(item.get("损失电量"))
                    bucket[reason] = bucket.get(reason, 0.0) + amount
                    declared += amount
            gap = _to_number(row.get("理论发电量")) - _to_number(row.get("实际发电量")) - declared
            if gap > 0:
                bucket[UNCATEGORIZED] = bucket.get(UNCATEGORIZED, 0.0) + gap
        total = sum(bucket.values())
        breakdown = [
            {
                "原因": reason,
                "损失电量": round(amount, 1),
                "占比": round(amount / total * 100, 1) if total > 0 else 0.0,
            }
            for reason, amount in bucket.items()
        ]
        breakdown.sort(key=lambda item: (-item["损失电量"], item["原因"]))
        return breakdown

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["报告状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"能效报告 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于能效分析可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["报告状态"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"能效报告已{action}"
