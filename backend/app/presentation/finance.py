"""Finance v2 presentation, sync, and export helpers."""

from __future__ import annotations

import io
from datetime import date, datetime, timezone
from typing import Any

_STATEMENT_ROWS = (
    ("revenue", "营业收入"),
    ("costOfServices", "营业成本"),
    ("grossProfit", "毛利"),
    ("operatingExpenses", "期间费用"),
    ("operatingProfit", "经营利润"),
    ("cashReceived", "已收现金"),
    ("cashPending", "待收现金"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_week_key(week: str, default_year: int) -> tuple[int, int] | None:
    if "-W" in week.upper():
        head, tail = week.upper().split("-W", 1)
        try:
            return int(head), int(tail)
        except ValueError:
            return None
    if week.upper().startswith("W"):
        try:
            return default_year, int(week[1:])
        except ValueError:
            return None
    return None


def _week_in_period(week: str, period: str, period_type: str) -> bool:
    if period_type == "quarter" and "-Q" in period.upper():
        year_s, q_s = period.upper().split("-Q", 1)
        try:
            year, quarter = int(year_s), int(q_s)
        except ValueError:
            return True
        parsed = _parse_week_key(week, year)
        if not parsed:
            return True
        wy, ww = parsed
        try:
            anchor = date.fromisocalendar(wy, ww, 4)
        except ValueError:
            return False
        return anchor.year == year and (anchor.month - 1) // 3 + 1 == quarter

    # month: 2026-05
    if len(period) >= 7 and period[4] == "-":
        try:
            year, month = int(period[:4]), int(period[5:7])
        except ValueError:
            return True
        parsed = _parse_week_key(week, year)
        if not parsed:
            return True
        wy, ww = parsed
        try:
            anchor = date.fromisocalendar(wy, ww, 4)
        except ValueError:
            return False
        return anchor.year == year and anchor.month == month
    return True


def _parse_payment_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _payment_in_period(payment: dict[str, Any], period: str, period_type: str) -> bool:
    at = _parse_payment_date(payment.get("at"))
    if at is None:
        return payment.get("status") == "pending"
    if period_type == "quarter" and "-Q" in period.upper():
        year_s, q_s = period.upper().split("-Q", 1)
        try:
            year, quarter = int(year_s), int(q_s)
        except ValueError:
            return True
        return at.year == year and (at.month - 1) // 3 + 1 == quarter
    if len(period) >= 7 and period[4] == "-":
        try:
            year, month = int(period[:4]), int(period[5:7])
        except ValueError:
            return True
        return at.year == year and at.month == month
    return True


def _project_total_cost(row: dict[str, Any]) -> float:
    breakdown = row.get("costBreakdown") or {}
    token = float(breakdown.get("token") if breakdown.get("token") is not None else row.get("cost") or 0)
    external = float(breakdown.get("external") or 0)
    tax = float(breakdown.get("tax") or 0)
    other = float(breakdown.get("other") or 0)
    total = token + external + tax + other
    row["costBreakdown"] = {
        "token": round(token, 2),
        "external": round(external, 2),
        "tax": round(tax, 2),
        "other": round(other, 2),
    }
    row["cost"] = round(total, 2)
    return total


def _rollup_payments(dashboard: dict[str, Any]) -> None:
    payments = dashboard.get("payments") or []
    costs = dashboard.setdefault("costs", {})
    by_project = costs.setdefault("byProject", [])
    index = {r.get("projectId"): r for r in by_project if r.get("projectId")}

    agg: dict[str, dict[str, float]] = {}
    for pay in payments:
        pid = pay.get("projectId")
        if not pid:
            continue
        bucket = agg.setdefault(pid, {"received": 0.0, "pending": 0.0})
        amount = float(pay.get("amount") or 0)
        if pay.get("status") == "received":
            bucket["received"] += amount
        elif pay.get("status") == "pending":
            bucket["pending"] += amount

    for pid, sums in agg.items():
        row = index.get(pid)
        if row is None:
            row = {"projectId": pid, "tokens": 0, "cost": 0, "sharePct": 0}
            by_project.append(row)
            index[pid] = row
        row["received"] = round(sums["received"], 2)
        row["pending"] = round(sums["pending"], 2)
        if sums["received"] or sums["pending"]:
            row["revenue"] = round(sums["received"] + sums["pending"], 2)


def _projects_by_id(dashboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p.get("id"): p for p in dashboard.get("projects") or [] if p.get("id")}


def _compute_health(
    row: dict[str, Any],
    project: dict[str, Any] | None,
) -> str:
    revenue = float(row.get("revenue") or 0)
    cost = float(row.get("cost") or 0)
    received = float(row.get("received") or 0)
    margin = float(row.get("margin") if row.get("margin") is not None else revenue - cost)
    margin_pct = row.get("marginPct")
    quoted = row.get("quoted")
    is_lead = (project or {}).get("pipelineColumn") == "lead" or str(row.get("projectId", "")).startswith("lead-")

    if revenue <= 0 and (quoted or is_lead):
        return "pipeline"
    if revenue > 0 and margin < 0:
        return "loss"
    if revenue <= 0 and cost > 0:
        return "watch"
    if revenue > 0 and received < cost:
        return "watch"
    if revenue > 0 and margin_pct is not None and float(margin_pct) >= 90 and float(row.get("pending") or 0) == 0:
        return "strong"
    if revenue > 0 and margin_pct is not None and float(margin_pct) >= 70:
        return "healthy"
    if revenue > 0:
        return "healthy"
    return "pipeline"


def _default_advisory(row: dict[str, Any], health: str) -> str:
    revenue = float(row.get("revenue") or 0)
    cost = float(row.get("cost") or 0)
    received = float(row.get("received") or 0)
    pending = float(row.get("pending") or 0)
    quoted = row.get("quoted")

    if health == "pipeline":
        return "线索阶段，建议控制登记成本，待 CEO 确认是否立项。"
    if health == "loss":
        return f"已签约但毛利为负（成本 ¥{cost:,.0f}），建议 Ops 与 CEO 复盘定价或范围。"
    if health == "watch" and revenue <= 0:
        return f"未签约已产生 Token 成本 ¥{cost:,.0f}，建议设 PoC 上限或暂停投入。"
    if health == "watch" and received < cost:
        return f"已收 ¥{received:,.0f} 未覆盖成本 ¥{cost:,.0f}，建议跟进回款或控本。"
    if health == "strong":
        return "已结项或全款到账，可作为同类项目定价基准。"
    if pending > 0:
        return f"按合同口径盈利；建议跟进待收 ¥{pending:,.0f}。"
    if revenue > 0:
        return "按合同口径盈利；成本结构健康。"
    if quoted:
        return f"报价区间 ¥{float(quoted):,.0f}，待签约前控制 Token 投入。"
    return "持续跟踪成本与签约进度。"


def _compute_health_and_advisory(dashboard: dict[str, Any]) -> None:
    costs = dashboard.setdefault("costs", {})
    projects = _projects_by_id(dashboard)
    watch = loss = 0

    for row in costs.get("byProject") or []:
        if row.get("projectId") == "_internal":
            continue
        pid = row.get("projectId")
        project = projects.get(pid)
        if project and not row.get("clientId"):
            row["clientId"] = project.get("clientId")
        if project and not row.get("quoted") and project.get("quotedAmount"):
            row["quoted"] = project.get("quotedAmount")

        revenue = float(row.get("revenue") or 0)
        cost = _project_total_cost(row)
        row["margin"] = round(revenue - cost, 2)
        if revenue > 0:
            row["marginPct"] = round((revenue - cost) / revenue * 100, 1)
        else:
            row["marginPct"] = None

        health = _compute_health(row, project)
        row["health"] = health
        if health == "watch":
            watch += 1
        if health == "loss":
            loss += 1

        source = row.get("advisorySource") or "rule"
        if source == "rule" or not row.get("advisory"):
            row["advisory"] = _default_advisory(row, health)[:120]
            row["advisorySource"] = "rule"
        else:
            row["advisory"] = str(row["advisory"])[:120]

        row["note"] = row.get("note") or row["advisory"]

    meta = costs.setdefault("meta", {})
    meta["watchProjectCount"] = watch
    meta["lossProjectCount"] = loss


def _rollup_share_pcts(costs: dict[str, Any]) -> None:
    by_project = [r for r in costs.get("byProject") or [] if r.get("projectId") != "_internal"]
    total_cost = sum(float(r.get("cost") or 0) for r in by_project) or 1.0
    for row in by_project:
        row["sharePct"] = round(float(row.get("cost") or 0) / total_cost * 100, 1)

    by_role = costs.get("byRole") or []
    role_total = sum(float(r.get("cost") or 0) for r in by_role) or 1.0
    for row in by_role:
        row["sharePct"] = round(float(row.get("cost") or 0) / role_total * 100, 1)

    for row in by_project:
        role_rows = row.get("byRole") or []
        proj_cost = float(row.get("cost") or 0) or 1.0
        for rr in role_rows:
            rr["sharePct"] = round(float(rr.get("cost") or 0) / proj_cost * 100, 1)


def _period_token_cost(costs: dict[str, Any]) -> float:
    period = costs.get("period") or ""
    period_type = costs.get("periodType") or "month"
    default_year = int(period[:4]) if len(period) >= 4 and period[:4].isdigit() else date.today().year
    weekly = costs.get("weekly") or []
    if weekly:
        matched = [
            float(w.get("cost") or 0)
            for w in weekly
            if _week_in_period(str(w.get("week") or ""), period, period_type)
        ]
        if matched:
            return round(sum(matched), 2)
    return float(costs.get("summary", {}).get("totalCost") or 0)


def _compute_statement(dashboard: dict[str, Any]) -> None:
    costs = dashboard.setdefault("costs", {})
    period = costs.get("period") or datetime.now().strftime("%Y-%m")
    period_type = costs.get("periodType") or "month"
    payments = dashboard.get("payments") or []

    period_payments = [p for p in payments if _payment_in_period(p, period, period_type)]
    cash_received = sum(float(p.get("amount") or 0) for p in period_payments if p.get("status") == "received")
    cash_pending = sum(float(p.get("amount") or 0) for p in period_payments if p.get("status") == "pending")

    revenue = cash_received + cash_pending
    if not period_payments and payments:
        revenue = float(costs.get("summary", {}).get("revenue") or 0)
        cash_received = float(costs.get("summary", {}).get("received") or 0)
        cash_pending = float(costs.get("summary", {}).get("pending") or 0)

    token_cost = _period_token_cost(costs)
    by_project = costs.get("byProject") or []
    external = sum(float((r.get("costBreakdown") or {}).get("external") or 0) for r in by_project)
    tax = sum(float((r.get("costBreakdown") or {}).get("tax") or 0) for r in by_project)
    other = sum(float((r.get("costBreakdown") or {}).get("other") or 0) for r in by_project)
    internal = next((r for r in by_project if r.get("projectId") == "_internal"), None)
    internal_cost = float(internal.get("cost") or 0) if internal else 0.0

    cost_of_services = round(token_cost + external + tax + other, 2)
    gross_profit = round(revenue - cost_of_services, 2)
    gross_margin_pct = round(gross_profit / revenue * 100, 1) if revenue > 0 else None
    operating_expenses = round(internal_cost, 2)
    operating_profit = round(gross_profit - operating_expenses, 2)

    tax_rate = costs.get("statement", {}).get("taxRatePct")
    tax_accrual = round(revenue * float(tax_rate) / 100, 2) if tax_rate else float(
        costs.get("statement", {}).get("taxAccrual") or 0
    )

    costs["statement"] = {
        "revenue": round(revenue, 2),
        "costOfServices": cost_of_services,
        "grossProfit": gross_profit,
        "grossMarginPct": gross_margin_pct,
        "operatingExpenses": operating_expenses,
        "operatingProfit": operating_profit,
        "cashReceived": round(cash_received, 2),
        "cashPending": round(cash_pending, 2),
        "taxAccrual": tax_accrual,
        "taxRatePct": tax_rate,
    }


def _mirror_summary(costs: dict[str, Any]) -> None:
    stmt = costs.get("statement") or {}
    summary = costs.setdefault("summary", {})
    summary["revenue"] = stmt.get("revenue", 0)
    summary["received"] = stmt.get("cashReceived", 0)
    summary["pending"] = stmt.get("cashPending", 0)
    summary["margin"] = stmt.get("grossProfit", 0)
    summary["marginPct"] = stmt.get("grossMarginPct")
    summary["totalCost"] = stmt.get("costOfServices", 0)
    summary["totalTokens"] = summary.get("totalTokens") or 0

    monthly_budget = float(summary.get("monthlyBudget") or 10000)
    total_cost = float(summary.get("totalCost") or 0)
    summary["budgetRemaining"] = round(max(0, monthly_budget - total_cost), 2)
    threshold = float((costs.get("meta") or {}).get("budgetAlertThresholdPct") or 80)
    summary["budgetAlert"] = monthly_budget > 0 and (total_cost / monthly_budget * 100) >= threshold
    if summary["budgetAlert"] and not summary.get("budgetAlertMessage"):
        summary["budgetAlertMessage"] = f"Token 成本已达月度预算 {threshold:.0f}%"


def _sync_weekly_finance_block(dashboard: dict[str, Any]) -> None:
    costs = dashboard.get("costs") or {}
    stmt = costs.get("statement") or {}
    reports = dashboard.get("weeklyReports") or []
    draft = next((r for r in reports if r.get("status") == "draft"), None)
    if not draft:
        return

    margin_pct = stmt.get("grossMarginPct")
    pending = stmt.get("cashPending") or 0
    text_parts = []
    if margin_pct is not None:
        text_parts.append(f"本月毛利 {margin_pct}%")
    if pending:
        text_parts.append(f"待收 ¥{pending:,.0f}")
    text = "；".join(text_parts) or "经营面平稳"

    metrics: list[dict[str, str]] = []
    if margin_pct is not None:
        metrics.append({"label": "毛利", "value": f"{margin_pct}%"})
    if pending:
        metrics.append({"label": "待收", "value": f"¥{pending:,.0f}"})
    metrics = metrics[:2]

    for block in draft.get("blocks") or []:
        if block.get("kind") == "finance":
            block["text"] = text[:120]
            block["metrics"] = metrics
            block["costsLink"] = True
            return

    draft.setdefault("blocks", []).append(
        {
            "kind": "finance",
            "title": "本周经营",
            "roleId": "ops",
            "text": text[:120],
            "metrics": metrics,
            "costsLink": True,
        }
    )


def _ensure_period_defaults(costs: dict[str, Any]) -> None:
    costs.setdefault("periodType", "month")
    costs.setdefault("period", datetime.now().strftime("%Y-%m"))
    costs.setdefault("currency", "CNY")
    costs.setdefault("maintainedBy", "ops")


def sync_finance(dashboard: dict[str, Any]) -> None:
    """Normalize costs domain, recompute statement, health, and weekly finance block."""
    costs = dashboard.setdefault("costs", {})
    _ensure_period_defaults(costs)
    _rollup_payments(dashboard)
    _compute_health_and_advisory(dashboard)
    _rollup_share_pcts(costs)
    _compute_statement(dashboard)
    _mirror_summary(costs)
    _sync_weekly_finance_block(dashboard)
    costs["lastSyncedAt"] = _now_iso()


def get_finance_project(dashboard: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    sync_finance(dashboard)
    for row in dashboard.get("costs", {}).get("byProject") or []:
        if row.get("projectId") == project_id:
            return row
    return None


def finance_summary_payload(dashboard: dict[str, Any]) -> dict[str, Any]:
    sync_finance(dashboard)
    costs = dashboard.get("costs") or {}
    return {
        "period": costs.get("period"),
        "periodType": costs.get("periodType"),
        "currency": costs.get("currency"),
        "statement": costs.get("statement"),
        "summary": costs.get("summary"),
        "meta": costs.get("meta"),
        "weekly": costs.get("weekly"),
        "byRole": costs.get("byRole"),
        "lastSyncedAt": costs.get("lastSyncedAt"),
    }


def finance_list_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "projectId": row.get("projectId"),
        "clientId": row.get("clientId"),
        "revenue": row.get("revenue"),
        "received": row.get("received"),
        "pending": row.get("pending"),
        "cost": row.get("cost"),
        "margin": row.get("margin"),
        "marginPct": row.get("marginPct"),
        "health": row.get("health"),
        "advisory": (row.get("advisory") or "")[:120],
        "quoted": row.get("quoted"),
        "tokens": row.get("tokens"),
        "sharePct": row.get("sharePct"),
    }


def _col_letter(index: int) -> str:
    """1-based column index → Excel column letters."""
    result = ""
    n = index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def _sheet_xml(rows: list[list[Any]]) -> str:
    import xml.sax.saxutils as xml

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    for r_idx, row in enumerate(rows, 1):
        parts.append(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row, 1):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                parts.append(f'<c r="{ref}"><v>{val}</v></c>')
            elif val is None:
                parts.append(f'<c r="{ref}"/>')
            else:
                text = xml.escape(str(val))
                parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        parts.append("</row>")
    parts.extend(["</sheetData>", "</worksheet>"])
    return "".join(parts)


def _workbook_xml(sheet_names: list[str]) -> str:
    import xml.sax.saxutils as xml

    sheets = "".join(
        f'<sheet name="{xml.escape(name)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
        for i, name in enumerate(sheet_names)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets></workbook>"
    )


def _build_xlsx_bytes(sheets: list[tuple[str, list[list[Any]]]]) -> bytes:
    import zipfile

    sheet_names = [name[:31] for name, _ in sheets]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(len(sheets))
            )
            + "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>',
        )
        zf.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        rels = "".join(
            f'<Relationship Id="rId{i + 1}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i + 1}.xml"/>'
            for i in range(len(sheets))
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>',
        )
        for i, (_, rows) in enumerate(sheets, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))
    return buf.getvalue()


def build_finance_xlsx(dashboard: dict[str, Any]) -> bytes:
    sync_finance(dashboard)
    costs = dashboard.get("costs") or {}
    stmt = costs.get("statement") or {}

    sheet1: list[list[Any]] = [
        ["期间", costs.get("period"), "类型", costs.get("periodType")],
        ["币种", costs.get("currency")],
        [],
        ["科目", "金额(CNY)", "field"],
    ]
    for key, label in _STATEMENT_ROWS:
        sheet1.append([label, stmt.get(key), key])
    if stmt.get("taxAccrual"):
        sheet1.append(["税费应计", stmt.get("taxAccrual"), "taxAccrual"])
    if stmt.get("taxRatePct") is not None:
        sheet1.append(["税率(%)", stmt.get("taxRatePct"), "taxRatePct"])

    sheet2: list[list[Any]] = [
        [
            "项目ID",
            "客户ID",
            "合同收入",
            "已收",
            "待收",
            "总成本",
            "Token",
            "外部",
            "税费",
            "其他",
            "毛利",
            "毛利率%",
            "健康度",
            "建议",
        ]
    ]
    for row in costs.get("byProject") or []:
        if row.get("projectId") == "_internal":
            continue
        bd = row.get("costBreakdown") or {}
        sheet2.append(
            [
                row.get("projectId"),
                row.get("clientId"),
                row.get("revenue"),
                row.get("received"),
                row.get("pending"),
                row.get("cost"),
                bd.get("token"),
                bd.get("external"),
                bd.get("tax"),
                bd.get("other"),
                row.get("margin"),
                row.get("marginPct"),
                row.get("health"),
                row.get("advisory"),
            ]
        )

    sheet3: list[list[Any]] = [["角色ID", "项目ID", "Tokens", "成本(CNY)", "Runs", "占比%"]]
    for row in costs.get("byProject") or []:
        pid = row.get("projectId")
        if pid == "_internal":
            continue
        for rr in row.get("byRole") or []:
            sheet3.append(
                [
                    rr.get("roleId"),
                    pid,
                    rr.get("tokens"),
                    rr.get("cost"),
                    rr.get("runs"),
                    rr.get("sharePct"),
                ]
            )
    if len(sheet3) == 1:
        for row in costs.get("byRole") or []:
            sheet3.append([row.get("roleId"), "", row.get("tokens"), row.get("cost"), row.get("runs"), row.get("sharePct")])

    sheet4: list[list[Any]] = [["ID", "客户ID", "项目ID", "金额", "标签", "状态", "日期"]]
    for pay in dashboard.get("payments") or []:
        sheet4.append(
            [
                pay.get("id"),
                pay.get("clientId"),
                pay.get("projectId"),
                pay.get("amount"),
                pay.get("label"),
                pay.get("status"),
                pay.get("at"),
            ]
        )

    return _build_xlsx_bytes(
        [
            ("损益摘要", sheet1),
            ("项目明细", sheet2),
            ("角色Token", sheet3),
            ("收款明细", sheet4),
        ]
    )
