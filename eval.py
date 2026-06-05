"""
eval.py — Order Enrichment Agent Evaluation Harness

Verdicts:  SAFE | CONDITIONALLY SAFE | NOT SAFE
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from variants import baseline, variant_a, variant_b, variant_c

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Variant A has a 30% random bug: prob(miss in N runs) = 0.70^N
# N=10 → 2.8% miss chance. B and C are deterministic so 3 runs is enough.
RUNS = {
    "baseline":  3,
    "variant_a": 10,
    "variant_b": 3,
    "variant_c": 3,
}

# 95% (not 100%) tolerates the baseline's own ~0.1% legitimate transient failure rate.
PASS_THRESHOLD = 0.95

# Variant C prepends ~310 chars of marketing copy; 300 is a clear ceiling.
SUMMARY_MAX_CHARS = 300

# Normal baseline runs complete in under 300ms. 3000ms catches genuine slowdowns only.
MAX_PROCESSING_MS = 3000

SUMMARY_LENGTH_RISKS = [
    "Mobile UI: summary fields truncated, useful info never shown to the user.",
    "CRM / ticketing systems: many fields cap at 100–255 chars; content is cut off.",
    "Push notifications / SMS: strict char limits mean only the marketing fluff is sent.",
    "LLM downstream processing: ~310 extra tokens of noise per order increases cost "
    "and reduces accuracy of any model that reads the summary.",
    "Log readability: operators scanning logs cannot find the signal in the noise.",
    "API payload size: minor but cumulative increase across high-volume pipelines.",
]


# ---------------------------------------------------------------------------
# Check functions
# Signature: (result, order) -> (passed: bool, reason: str)
# CRITICAL failure → NOT SAFE.  ADVISORY failure → CONDITIONALLY SAFE.
# ---------------------------------------------------------------------------

def check_required_fields(result: dict, order: dict) -> tuple[bool, str]:
    for key in ("order_id", "pricing", "shipping", "risk_assessment"):
        if key not in result:
            return False, f"missing required field: '{key}'"
    return True, ""


def check_order_id_preserved(result: dict, order: dict) -> tuple[bool, str]:
    expected = order.get("order_id")
    got = result.get("order_id")
    if got != expected:
        return False, f"order_id mismatch: input={expected!r}, output={got!r}"
    return True, ""


def check_has_risk_assessment(result: dict, order: dict) -> tuple[bool, str]:
    if "risk_assessment" not in result:
        return False, "risk_assessment field is absent"
    return True, ""


def check_risk_score_not_none(result: dict, order: dict) -> tuple[bool, str]:
    """None is acceptable only when the baseline sets an 'error' key after exhausting retries."""
    risk = result.get("risk_assessment")
    if not isinstance(risk, dict):
        return False, "risk assessment data is missing or was removed from this output"
    if risk.get("risk_score") is None and "error" not in risk:
        return False, "risk score is missing — the risk service was not called"
    return True, ""


def check_risk_level_not_stub(result: dict, order: dict) -> tuple[bool, str]:
    """'unknown' without an error key means the risk service was bypassed entirely."""
    risk = result.get("risk_assessment")
    if not isinstance(risk, dict):
        return False, "risk assessment data is missing or was removed from this output"
    if risk.get("risk_level") == "unknown" and "error" not in risk:
        return False, "risk level is 'unknown' with no explanation — risk scoring was skipped"
    return True, ""


def check_risk_recommendation_valid(result: dict, order: dict) -> tuple[bool, str]:
    risk = result.get("risk_assessment")
    if not isinstance(risk, dict):
        return False, "risk assessment data is missing or was removed from this output"
    valid_values = {"approve", "review", "manual_review"}
    recommendation = risk.get("recommendation")
    if recommendation not in valid_values:
        return False, (
            f"recommendation {recommendation!r} is not a recognised value "
            f"(expected one of {sorted(valid_values)})"
        )
    return True, ""


def check_shipping_structure(result: dict, order: dict) -> tuple[bool, str]:
    """Verifies the address tool's output contract, not the address content itself."""
    shipping = result.get("shipping")
    if not isinstance(shipping, dict):
        return False, "shipping is not a dict"
    if not isinstance(shipping.get("valid"), bool):
        return False, f"shipping.valid is not a boolean: {shipping.get('valid')!r}"
    confidence = shipping.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        return False, f"shipping.confidence is out of range or missing: {confidence!r}"
    if not isinstance(shipping.get("region_supported"), bool):
        return False, f"shipping.region_supported is not a boolean: {shipping.get('region_supported')!r}"
    return True, ""


def check_pricing_valid(result: dict, order: dict) -> tuple[bool, str]:
    pricing = result.get("pricing")
    if not isinstance(pricing, dict):
        return False, "pricing is not a dict"
    total = pricing.get("total")
    if not isinstance(total, (int, float)) or total <= 0:
        return False, f"pricing.total is invalid: {total!r}"
    return True, ""


def check_processing_time(result: dict, order: dict) -> tuple[bool, str]:
    ms = result.get("processing_time_ms")
    if ms is None:
        return False, "processing_time_ms field is missing"
    if not isinstance(ms, (int, float)) or ms < 0:
        return False, f"processing_time_ms has an invalid value: {ms!r}"
    if ms > MAX_PROCESSING_MS:
        return False, f"processing took {ms:.0f}ms — exceeds {MAX_PROCESSING_MS}ms ceiling"
    return True, ""


def check_summary_length(result: dict, order: dict) -> tuple[bool, str]:
    summary = result.get("summary", "")
    if not isinstance(summary, str):
        return False, f"summary is not a string: {type(summary).__name__}"
    if len(summary) > SUMMARY_MAX_CHARS:
        return False, f"summary is {len(summary)} chars (max {SUMMARY_MAX_CHARS})"
    return True, ""


CRITICAL_CHECKS: list[Callable] = [
    check_required_fields,
    check_order_id_preserved,
    check_has_risk_assessment,
    check_risk_score_not_none,
    check_risk_level_not_stub,
    check_risk_recommendation_valid,
    check_shipping_structure,
    check_pricing_valid,
]

ADVISORY_CHECKS: list[Callable] = [
    check_processing_time,
    check_summary_length,
]

ALL_CHECKS = CRITICAL_CHECKS + ADVISORY_CHECKS


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def load_orders() -> list[dict]:
    fixture = Path(__file__).parent / "fixtures" / "orders.jsonl"
    with fixture.open() as f:
        return [json.loads(line) for line in f]


def run_variant(module, orders: list[dict], runs: int) -> dict:
    counts = {
        check.__name__: {"pass": 0, "fail": 0, "failures": []}
        for check in ALL_CHECKS
    }
    total_runs = 0

    for order in orders:
        for run_i in range(runs):
            total_runs += 1
            try:
                result = module.enrich_order(order)
            except Exception as exc:
                for check in ALL_CHECKS:
                    counts[check.__name__]["fail"] += 1
                    counts[check.__name__]["failures"].append({
                        "order_id": order.get("order_id"),
                        "run": run_i + 1,
                        "reason": f"agent raised exception: {exc}",
                    })
                continue

            for check in ALL_CHECKS:
                passed, reason = check(result, order)
                if passed:
                    counts[check.__name__]["pass"] += 1
                else:
                    counts[check.__name__]["fail"] += 1
                    counts[check.__name__]["failures"].append({
                        "order_id": order.get("order_id"),
                        "run": run_i + 1,
                        "reason": reason,
                    })

    return {"total_runs": total_runs, "checks": counts}


# ---------------------------------------------------------------------------
# Scoring and verdict
# ---------------------------------------------------------------------------

def _check_passed(counts: dict, total: int) -> bool:
    return total > 0 and (counts["pass"] / total) >= PASS_THRESHOLD


def compute_verdicts(raw_results: dict) -> dict:
    verdicts = {}
    critical_names = {c.__name__ for c in CRITICAL_CHECKS}

    for name, data in raw_results.items():
        total = data["total_runs"]
        check_scores = {}
        critical_failed = False
        advisory_failed = False

        for check in ALL_CHECKS:
            cname = check.__name__
            counts = data["checks"][cname]
            passed = _check_passed(counts, total)
            pass_rate = counts["pass"] / total if total > 0 else 0.0

            if not passed:
                if cname in critical_names:
                    critical_failed = True
                else:
                    advisory_failed = True

            check_scores[cname] = {
                "severity": "critical" if cname in critical_names else "advisory",
                "pass_rate": round(pass_rate, 4),
                "pass_count": counts["pass"],
                "fail_count": counts["fail"],
                "passed_threshold": passed,
                "sample_failures": counts["failures"][:3],
            }

        if critical_failed:
            verdict = "NOT SAFE"
        elif advisory_failed:
            verdict = "CONDITIONALLY SAFE"
        else:
            verdict = "SAFE"

        verdicts[name] = {
            "verdict": verdict,
            "total_runs": total,
            "checks": check_scores,
        }
    return verdicts


# ---------------------------------------------------------------------------
# Report generation (Markdown + HTML)
# ---------------------------------------------------------------------------

CHECK_LABELS = {
    "check_required_fields":           "Required fields present",
    "check_order_id_preserved":        "Order ID matches input",
    "check_has_risk_assessment":       "Risk assessment never dropped",
    "check_risk_score_not_none":       "Risk score is a real number",
    "check_risk_level_not_stub":       "Risk level is not a stub",
    "check_risk_recommendation_valid": "Risk recommendation is a known value",
    "check_shipping_structure":        "Shipping output is structurally complete",
    "check_pricing_valid":             "Pricing total is valid",
    "check_processing_time":           f"Processing time under {MAX_PROCESSING_MS}ms",
    "check_summary_length":            f"Summary under {SUMMARY_MAX_CHARS} chars",
}

VERDICT_ICONS = {
    "SAFE":               "✅",
    "CONDITIONALLY SAFE": "⚠️",
    "NOT SAFE":           "❌",
}


def render_report(verdicts: dict) -> str:
    lines = []
    lines.append("# Order Enrichment Agent — Evaluation Report\n")
    lines.append(
        "Each variant was run against all 20 fixture orders multiple times. "
        "Checks are classified as **critical** (functional failures that block shipping) "
        "or **advisory** (quality/format issues that may be acceptable depending on context).\n"
    )
    lines.append("**Verdict key:**\n")
    lines.append("- ✅ **SAFE** — all checks pass")
    lines.append("- ⚠️ **CONDITIONALLY SAFE** — functional data correct; only advisory checks fail")
    lines.append("- ❌ **NOT SAFE** — functional failure; do not ship\n")

    lines.append("## Verdict Summary\n")
    lines.append("| Variant   | Runs | Verdict             |")
    lines.append("|-----------|------|---------------------|")
    for name, v in verdicts.items():
        icon = VERDICT_ICONS[v["verdict"]]
        lines.append(f"| {name:<9} | {v['total_runs']:>4} | {icon} {v['verdict']} |")
    lines.append("")

    for name, v in verdicts.items():
        icon = VERDICT_ICONS[v["verdict"]]
        lines.append(f"## {name}\n")
        lines.append(f"**Verdict: {icon} {v['verdict']}** — {v['total_runs']} total runs\n")
        lines.append("| Check | Severity | Pass rate | Result |")
        lines.append("|-------|----------|-----------|--------|")
        for check_name, score in v["checks"].items():
            label = CHECK_LABELS.get(check_name, check_name)
            severity = score["severity"].upper()
            pct = f"{score['pass_rate'] * 100:.1f}%"
            result_str = "PASS" if score["passed_threshold"] else "**FAIL**"
            lines.append(f"| {label} | {severity} | {pct} | {result_str} |")
        lines.append("")

        for check_name, score in v["checks"].items():
            if score["sample_failures"]:
                label = CHECK_LABELS.get(check_name, check_name)
                lines.append(f"**Sample failures — {label}:**\n")
                for failure in score["sample_failures"]:
                    lines.append(
                        f"- `{failure['order_id']}` run {failure['run']}: {failure['reason']}"
                    )
                lines.append("")

        if v["verdict"] == "CONDITIONALLY SAFE":
            lines.append("**Why CONDITIONALLY SAFE and not NOT SAFE:**\n")
            lines.append(
                "All functional data is intact — pricing, address validation, and risk "
                "scoring all work correctly. The only failure is the `summary` field "
                f"exceeding {SUMMARY_MAX_CHARS} characters due to a prepended marketing "
                "prefix (~310 chars). This is a **format regression**, not a data integrity "
                "or fraud-detection failure.\n"
            )
            lines.append(
                "This variant **can be shipped if the product team explicitly accepts "
                "verbose summaries** and confirms none of the following downstream "
                "systems are affected:\n"
            )
            for risk in SUMMARY_LENGTH_RISKS:
                lines.append(f"- {risk}")
            lines.append("")

    return "\n".join(lines)


VERDICT_COLORS = {
    "SAFE":               {"bg": "#dcfce7", "border": "#16a34a", "text": "#15803d"},
    "CONDITIONALLY SAFE": {"bg": "#fef9c3", "border": "#ca8a04", "text": "#a16207"},
    "NOT SAFE":           {"bg": "#fee2e2", "border": "#dc2626", "text": "#b91c1c"},
}

VERDICT_PLAIN = {
    "SAFE":               "Safe to ship",
    "CONDITIONALLY SAFE": "Safe with conditions",
    "NOT SAFE":           "Do not ship",
}


def _html_check_row(check_name: str, score: dict) -> str:
    label = CHECK_LABELS.get(check_name, check_name)
    severity = score["severity"].upper()
    pct = f"{score['pass_rate'] * 100:.1f}%"
    sev_color = "#dc2626" if score["severity"] == "critical" else "#ca8a04"
    if score["passed_threshold"]:
        result_html = '<span style="color:#16a34a;font-weight:600">PASS</span>'
        row_bg = "#f0fdf4"
    else:
        result_html = '<span style="color:#dc2626;font-weight:600">FAIL</span>'
        row_bg = "#fff1f2"

    failures_html = ""
    if score["sample_failures"]:
        items = "".join(
            f'<li><code style="background:#f1f5f9;padding:1px 4px;border-radius:3px">'
            f'{f["order_id"]}</code> run {f["run"]}: {f["reason"]}</li>'
            for f in score["sample_failures"]
        )
        failures_html = (
            f'<tr style="background:#fff8f8">'
            f'<td colspan="4" style="padding:6px 16px 10px 32px;font-size:12px;color:#6b7280">'
            f'<ul style="margin:4px 0;padding-left:16px">{items}</ul></td></tr>'
        )

    return (
        f'<tr style="background:{row_bg}">'
        f'<td style="padding:8px 12px">{label}</td>'
        f'<td style="padding:8px 12px;text-align:center">'
        f'<span style="font-size:11px;font-weight:600;color:{sev_color};'
        f'border:1px solid {sev_color};border-radius:3px;padding:1px 5px">'
        f'{severity}</span></td>'
        f'<td style="padding:8px 12px;text-align:center;font-weight:500">{pct}</td>'
        f'<td style="padding:8px 12px;text-align:center">{result_html}</td>'
        f'</tr>{failures_html}'
    )


def render_html_report(verdicts: dict) -> str:
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    cards_html = ""
    for name, v in verdicts.items():
        c = VERDICT_COLORS[v["verdict"]]
        emoji = VERDICT_ICONS[v["verdict"]]
        plain = VERDICT_PLAIN[v["verdict"]]
        cards_html += (
            f'<div style="flex:1;min-width:180px;border:2px solid {c["border"]};'
            f'border-radius:10px;background:{c["bg"]};padding:20px 16px;text-align:center">'
            f'<div style="font-size:32px;margin-bottom:6px">{emoji}</div>'
            f'<div style="font-size:16px;font-weight:700;color:#111;margin-bottom:4px">{name}</div>'
            f'<div style="font-size:13px;font-weight:600;color:{c["text"]};margin-bottom:6px">{plain}</div>'
            f'<div style="font-size:11px;color:#6b7280">{v["total_runs"]} runs · 20 orders</div>'
            f'</div>'
        )

    details_html = ""
    for name, v in verdicts.items():
        c = VERDICT_COLORS[v["verdict"]]
        emoji = VERDICT_ICONS[v["verdict"]]
        rows = "".join(_html_check_row(cn, sc) for cn, sc in v["checks"].items())

        cond_note = ""
        if v["verdict"] == "CONDITIONALLY SAFE":
            risk_items = "".join(f"<li>{r}</li>" for r in SUMMARY_LENGTH_RISKS)
            cond_note = (
                f'<div style="margin-top:16px;background:#fffbeb;border-left:4px solid #f59e0b;'
                f'padding:14px 16px;border-radius:0 6px 6px 0">'
                f'<p style="margin:0 0 8px;font-weight:600;color:#92400e">Why Conditionally Safe?</p>'
                f'<p style="margin:0 0 8px;color:#374151;font-size:14px">'
                f'All functional data is correct — pricing, address validation, and risk scoring '
                f'all work. The only issue is the <code style="background:#fef3c7;padding:1px 4px;'
                f'border-radius:3px">summary</code> field being too long (~370–560 chars vs the '
                f'{SUMMARY_MAX_CHARS}-char contract) due to a prepended marketing prefix.</p>'
                f'<p style="margin:0 0 6px;font-weight:600;color:#92400e;font-size:14px">'
                f'This becomes a problem if any of these systems consume the summary:</p>'
                f'<ul style="margin:0;padding-left:20px;color:#374151;font-size:14px">'
                f'{risk_items}</ul>'
                f'</div>'
            )

        details_html += (
            f'<div style="margin-bottom:32px">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">'
            f'<h2 style="margin:0;font-size:18px;color:#111">{name}</h2>'
            f'<span style="font-size:13px;font-weight:600;color:{c["text"]};'
            f'background:{c["bg"]};border:1px solid {c["border"]};'
            f'border-radius:20px;padding:2px 10px">{emoji} {v["verdict"]}</span>'
            f'</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px;'
            f'border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">'
            f'<thead><tr style="background:#f9fafb">'
            f'<th style="padding:10px 12px;text-align:left;color:#374151;font-weight:600">Check</th>'
            f'<th style="padding:10px 12px;text-align:center;color:#374151;font-weight:600">Severity</th>'
            f'<th style="padding:10px 12px;text-align:center;color:#374151;font-weight:600">Pass rate</th>'
            f'<th style="padding:10px 12px;text-align:center;color:#374151;font-weight:600">Result</th>'
            f'</tr></thead>'
            f'<tbody>{rows}</tbody>'
            f'</table>'
            f'{cond_note}'
            f'</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Order Enrichment Agent — Eval Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background:#f8fafc; color:#111; margin:0; padding:0; }}
    .container {{ max-width:860px; margin:0 auto; padding:32px 24px; }}
    code {{ font-family: ui-monospace, monospace; }}
  </style>
</head>
<body>
<div class="container">
  <div style="border-bottom:2px solid #e5e7eb;margin-bottom:28px;padding-bottom:20px">
    <h1 style="margin:0 0 6px;font-size:24px;color:#111">Order Enrichment Agent — Evaluation Report</h1>
    <p style="margin:0;color:#6b7280;font-size:14px">
      Run on {run_time} &nbsp;·&nbsp; 20 fixture orders &nbsp;·&nbsp; 4 variants
    </p>
  </div>

  <h2 style="font-size:16px;font-weight:600;color:#374151;margin-bottom:14px">Verdict Summary</h2>
  <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:36px">{cards_html}</div>

  <div style="background:#f1f5f9;border-radius:8px;padding:14px 16px;margin-bottom:32px;
              font-size:13px;color:#374151;line-height:1.6">
    <strong>How to read this report:</strong> Each variant was run against all 20 orders
    multiple times. A <strong>critical</strong> check failure means the change breaks something
    important — do not ship. An <strong>advisory</strong> check failure means the data is correct
    but there is a quality or format issue. The pass threshold is 95%.
  </div>

  <h2 style="font-size:16px;font-weight:600;color:#374151;margin-bottom:20px">Detailed Results</h2>
  {details_html}

  <div style="border-top:1px solid #e5e7eb;margin-top:16px;padding-top:14px;
              font-size:12px;color:#9ca3af;text-align:center">
    Generated by eval.py · threshold {int(PASS_THRESHOLD*100)}% · {run_time}
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    orders = load_orders()
    print(f"Loaded {len(orders)} orders.\n")

    modules = {
        "baseline":  baseline,
        "variant_a": variant_a,
        "variant_b": variant_b,
        "variant_c": variant_c,
    }

    raw_results = {}
    for name, module in modules.items():
        runs = RUNS[name]
        print(f"  {name:<12} {runs} run(s) × {len(orders)} orders ...", end=" ", flush=True)
        raw_results[name] = run_variant(module, orders, runs)
        print("done")

    verdicts = compute_verdicts(raw_results)

    report = render_report(verdicts)
    print("\n" + "=" * 60 + "\n")
    print(report)

    report_path = Path(__file__).parent / "report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport written    → {report_path}")

    html = render_html_report(verdicts)
    html_path = Path(__file__).parent / "report.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written → {html_path}")


if __name__ == "__main__":
    main()
