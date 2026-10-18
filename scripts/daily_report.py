#!/usr/bin/env python3
"""
Daily Report Script
Aggregates task statuses, research candidates, content production, and business metrics
into a structured daily report for ChatGPT Lead Review.
Saves to metrics/daily/<date>-report.json and metrics/daily/<date>-report.md.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from validate_tasks import get_base_dir
from readiness import apply_readiness_gate

def generate_daily_report(date_str: Optional[str] = None, base_dir: Optional[Path] = None) -> Path:
    if base_dir is None:
        base_dir = get_base_dir()

    if not date_str:
        date_str = datetime.now().astimezone().strftime("%Y%m%d")

    tasks_dir = base_dir / "tasks"
    results_dir = base_dir / "results"
    research_dir = base_dir / "research"
    content_dir = base_dir / "content"
    metrics_dir = base_dir / "metrics" / "daily"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # 1. Collect task counts & tasks
    task_counts = {"queued": 0, "running": 0, "review": 0, "done": 0, "failed": 0}
    all_tasks = []

    for status in task_counts.keys():
        folder = tasks_dir / status
        if folder.exists():
            for tf in folder.glob("*.json"):
                task_counts[status] += 1
                try:
                    with open(tf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        all_tasks.append({
                            "id": data.get("id"),
                            "type": data.get("type"),
                            "priority": data.get("priority"),
                            "status": status,
                            "goal": data.get("goal"),
                            "result": data.get("result")
                        })
                except Exception:
                    pass

    # 2. Collect research products
    products_file = research_dir / "products" / f"{date_str}-products.json"
    top_products = []
    if not products_file.exists():
        # Fallback to most recent product file
        prod_files = sorted(list((research_dir / "products").glob("*-products.json")), reverse=True)
        if prod_files:
            products_file = prod_files[0]

    if products_file and products_file.exists():
        try:
            with open(products_file, "r", encoding="utf-8") as pf:
                p_data = json.load(pf)
                # Could be a list of products or dict with "candidates"
                candidates = p_data if isinstance(p_data, list) else p_data.get("candidates", [])
                gated_candidates = [apply_readiness_gate(c) for c in candidates]
                gated_candidates.sort(
                    key=lambda x: (x.get("readiness_score", 0), x.get("score", 0)),
                    reverse=True,
                )
                top_products = gated_candidates[:5]
        except Exception:
            pass

    # 3. Collect reviews for today
    reviews = []
    if results_dir.exists():
        for rf in results_dir.glob(f"*{date_str}*-review.json"):
            try:
                with open(rf, "r", encoding="utf-8") as f:
                    reviews.append(json.load(f))
            except Exception:
                pass
        # If none today, grab recent reviews
        if not reviews:
            for rf in sorted(list(results_dir.glob("*-review.json")), reverse=True)[:3]:
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        reviews.append(json.load(f))
                except Exception:
                    pass

    # 4. Content count
    content_count = {
        "scripts": len(list((content_dir / "scripts").glob("*.md"))),
        "posts": len(list((content_dir / "posts").glob("*.md"))),
        "articles": len(list((content_dir / "articles").glob("*.md")))
    }

    report_data = {
        "report_date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_summary": task_counts,
        "tasks": all_tasks,
        "content_inventory": content_count,
        "top_research_candidates": top_products,
        "recent_reviews": reviews
    }

    # Save JSON report
    json_path = metrics_dir / f"{date_str}-report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # Save Markdown report
    md_path = metrics_dir / f"{date_str}-report.md"
    md_content = f"""# Daily Executive Summary — {date_str}

**Generated At:** {report_data['generated_at']}
**Executor:** Antigravity  
**Lead Reviewer:** ChatGPT  

---

## 1. Task Queue Pipeline
- **Queued:** {task_counts['queued']}
- **Running:** {task_counts['running']}
- **Awaiting Lead Review:** {task_counts['review']}
- **Completed (Done):** {task_counts['done']}
- **Failed:** {task_counts['failed']}

---

## 2. Content Inventory
- Video Scripts: {content_count['scripts']}
- Social / Community Posts: {content_count['posts']}
- Long-form Articles: {content_count['articles']}

---

## 3. Top Researched Opportunities
"""

    if top_products:
        for idx, p in enumerate(top_products, 1):
            md_content += f"""### {idx}. {p.get('product', 'Unknown')} ({p.get('brand', 'Unknown')})
- **Score:** {p.get('score', 'N/A')} / 100 — **Recommendation:** {p.get('recommendation', 'N/A')}
- **Affiliate Readiness:** {p.get('readiness_score', 0)} / 100 — **Gate:** {p.get('readiness_gate', 'BLOCKED_NEEDS_VERIFICATION')}
- **Niche/Category:** {p.get('category', 'N/A')}
- **Commission Model:** {p.get('commission', 'needs_verification')} (Cookie: {p.get('cookie_window', 'needs_verification')})
- **Target Persona:** {p.get('target_audience', 'N/A')}
- **Key Angles:** {', '.join(p.get('content_angles', []))}
- **Source:** {p.get('source_url', 'N/A')}

"""
    else:
        md_content += "_No products researched yet for this cycle._\n\n"

    md_content += """---

## 4. Reviews Ready for Lead Approval
"""
    if reviews:
        for r in reviews:
            md_content += f"""### Task {r.get('task_id', 'Unknown')}
- **Decision Proposed:** {r.get('recommended_decision', 'N/A')} (Confidence: {r.get('confidence', 0):.2f})
- **Summary:** {r.get('executive_summary', 'N/A')}
- **Questions for Lead:**
"""
            for q in r.get("questions_for_lead", []):
                md_content += f"  - {q}\n"
            md_content += "- **Next Suggested Actions:**\n"
            for n in r.get("next_task_suggestions", []):
                md_content += f"  - {n}\n"
            md_content += "\n"
    else:
        md_content += "_No pending task reviews at this moment._\n\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"📊 Daily Report generated for {date_str}:")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")
    return md_path

def main():
    parser = argparse.ArgumentParser(description="Generate daily summary report.")
    parser.add_argument("--date", help="Report date YYYYMMDD (defaults to UTC today)")
    args = parser.parse_args()

    try:
        generate_daily_report(date_str=args.date)
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
