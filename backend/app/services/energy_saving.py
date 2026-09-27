"""能效分析业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "energy_saving"
REQUIRED_FIELDS = ["报告编号", "电站编号", "分析周期"]
STATUS_ORDER = ["待生成", "已生成", "已审阅", "已归档"]
ACTION_RULES = {"生成报告": "已生成", "审阅确认": "已审阅", "归档报告": "已归档"}
NEGATIVE_ACTIONS = []
UNCATEGORIZED = "未分类"


def _num(value: Any) -> float | None:
    """把数值或数字字符串统一成 float；空值与非数字返回 None，不猜数。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _period_of(row: dict[str, Any]) -> str:
    return str(row.get("分析周期") or "").strip()


def _loss_items(row: dict[str, Any]) -> dict[str, float]:
    """单条报告的损失构成：按原因归集，缺少损失原因时归入未分类。"""
    items: dict[str, float] = {}
    composition = row.get("损失构成")
    if isinstance(composition, dict):
        for reason, value in composition.items():
            amount = _num(value)
            if amount is None:
                continue
            key = str(reason).strip() or UNCATEGORIZED
            items[key] = items.get(key, 0.0) + amount
    if not items:
        theory = _num(row.get("理论发电量"))
        actual = _num(row.get("实际发电量"))
        if theory is not None and actual is not None:
            gap = round(max(theory - actual, 0.0), 2)
            if gap > 0:
                items[UNCATEGORIZED] = gap
    return items


def _sorted_items(totals: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"reason": reason, "value": round(amount, 2)}
        for reason, amount in sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    ]


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
        return store.find(MODULE, entry_id)

    def dashboard(self, *, period: str | None = None) -> dict[str, Any]:
        """按分析周期排列的对比看板：与报告明细读同一份 store 数据，只按所选周期汇总。"""
        rows = store.rows(MODULE)
        periods = sorted({_period_of(row) for row in rows if _period_of(row)})
        selected = period if period in periods else (periods[-1] if periods else "")
        cards: list[dict[str, Any]] = []
        loss_totals: dict[str, float] = {}
        for row in rows:
            if _period_of(row) != selected:
                continue
            loss_items = _loss_items(row)
            for reason, amount in loss_items.items():
                loss_totals[reason] = loss_totals.get(reason, 0.0) + amount
            cards.append({
                "id": row.get("id"),
                "报告编号": row.get("报告编号"),
                "电站编号": row.get("电站编号"),
                "分析周期": _period_of(row),
                "理论发电量": _num(row.get("理论发电量")),
                "实际发电量": _num(row.get("实际发电量")),
                "系统效率": _num(row.get("系统效率")),
                "报告状态": row.get("status"),
                "损失构成": _sorted_items(loss_items),
            })
        cards.sort(key=lambda card: str(card.get("电站编号") or ""))
        return {
            "periods": periods,
            "period": selected,
            "cards": cards,
            "loss": _sorted_items(loss_totals),
            "trend": [self._trend_point(item, rows) for item in periods],
        }

    def _trend_point(self, period: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        period_rows = [row for row in rows if _period_of(row) == period]
        efficiencies = [value for value in (_num(row.get("系统效率")) for row in period_rows) if value is not None]
        theory = sum(value for value in (_num(row.get("理论发电量")) for row in period_rows) if value is not None)
        actual = sum(value for value in (_num(row.get("实际发电量")) for row in period_rows) if value is not None)
        loss = sum(sum(_loss_items(row).values()) for row in period_rows)
        status_counts: dict[str, int] = {status: 0 for status in STATUS_ORDER}
        for row in period_rows:
            status = str(row.get("status") or "")
            status_counts[status] = status_counts.get(status, 0) + 1
        return {
            "period": period,
            "报告数": len(period_rows),
            "平均系统效率": round(sum(efficiencies) / len(efficiencies), 2) if efficiencies else None,
            "理论发电量": round(theory, 2),
            "实际发电量": round(actual, 2),
            "损失电量": round(loss, 2),
            "状态分布": status_counts,
        }

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
