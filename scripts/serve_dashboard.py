#!/usr/bin/env python3
"""
Affiliate Automation Dashboard Server
Lightweight Python built-in HTTP server providing web UI and REST API.
Serves dashboard/ frontend and /api/data endpoint.
"""

import sys
import os
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent

class DashboardRequestHandler(BaseHTTPRequestHandler):
    def get_project_data(self) -> Dict[str, Any]:
        base_dir = get_base_dir()
        tasks_dir = base_dir / "tasks"
        research_dir = base_dir / "research"
        content_dir = base_dir / "content"
        results_dir = base_dir / "results"
        metrics_dir = base_dir / "metrics"
        config_dir = base_dir / "config"

        # 1. Tasks by status
        statuses = ["queued", "running", "review", "done", "failed"]
        tasks_by_status = {s: [] for s in statuses}
        for s in statuses:
            s_dir = tasks_dir / s
            if s_dir.exists():
                for tf in sorted(s_dir.glob("*.json")):
                    try:
                        with open(tf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            tasks_by_status[s].append(data)
                    except Exception as e:
                        tasks_by_status[s].append({"id": tf.stem, "error": str(e), "status": s})

        # 2. Researched products
        products = []
        prod_files = sorted(list((research_dir / "products").glob("*-products.json")), reverse=True)
        for pf in prod_files:
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    p_data = json.load(f)
                    cands = p_data if isinstance(p_data, list) else p_data.get("candidates", [])
                    for c in cands:
                        c["source_file"] = pf.name
                        products.append(c)
            except Exception:
                pass

        # Sort products by score descending
        products.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 3. Content assets
        content_assets = []
        for c_type in ["scripts", "posts", "articles"]:
            c_dir = content_dir / c_type
            if c_dir.exists():
                for cf in sorted(c_dir.glob("*.md")):
                    content_assets.append({
                        "filename": cf.name,
                        "type": c_type,
                        "path": str(cf.relative_to(base_dir)),
                        "size_bytes": cf.stat().st_size
                    })

        # 4. Review results
        reviews = []
        if results_dir.exists():
            for rf in sorted(results_dir.glob("*-review.json"), reverse=True):
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        reviews.append(json.load(f))
                except Exception:
                    pass

        # 5. Configs
        affiliate_cfg = {}
        scoring_cfg = {}
        if (config_dir / "affiliate.json").exists():
            with open(config_dir / "affiliate.json", "r", encoding="utf-8") as f:
                affiliate_cfg = json.load(f)
        if (config_dir / "scoring.json").exists():
            with open(config_dir / "scoring.json", "r", encoding="utf-8") as f:
                scoring_cfg = json.load(f)

        # 6. Latest daily report
        latest_report = None
        daily_md_files = sorted(list((metrics_dir / "daily").glob("*-report.md")), reverse=True)
        if daily_md_files:
            try:
                with open(daily_md_files[0], "r", encoding="utf-8") as f:
                    latest_report = {
                        "filename": daily_md_files[0].name,
                        "content": f.read()
                    }
            except Exception:
                pass

        return {
            "status": "healthy",
            "counts": {s: len(tasks_by_status[s]) for s in statuses},
            "tasks": tasks_by_status,
            "top_products": products[:20],
            "content_assets": content_assets,
            "reviews": reviews,
            "config": {
                "affiliate": affiliate_cfg,
                "scoring": scoring_cfg
            },
            "latest_report": latest_report
        }

    def do_GET(self):
        base_dir = get_base_dir()
        dashboard_dir = base_dir / "dashboard"

        # API endpoint
        if self.path == "/api/data" or self.path == "/api/status":
            data = self.get_project_data()
            payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
            return

        # Serve Dashboard Static Files
        req_path = self.path.split("?")[0]
        if req_path in ["", "/", "/index.html"]:
            file_path = dashboard_dir / "index.html"
            content_type = "text/html; charset=utf-8"
        elif req_path == "/app.js":
            file_path = dashboard_dir / "app.js"
            content_type = "application/javascript; charset=utf-8"
        elif req_path == "/style.css":
            file_path = dashboard_dir / "style.css"
            content_type = "text/css; charset=utf-8"
        else:
            # Fallback to local files in dashboard
            clean_path = req_path.lstrip("/")
            file_path = dashboard_dir / clean_path
            if clean_path.endswith(".js"):
                content_type = "application/javascript"
            elif clean_path.endswith(".css"):
                content_type = "text/css"
            elif clean_path.endswith(".json"):
                content_type = "application/json"
            else:
                content_type = "text/plain"

        if file_path.exists() and file_path.is_file():
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def log_message(self, format, *args):
        # Keep logs clean
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

def run_server(host: str = "127.0.0.1", port: int = 8000, single_request: bool = False):
    server_address = (host, port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print(f"🚀 Affiliate Automation Dashboard running at http://{host}:{port}/")
    print(f"📊 Live API endpoint: http://{host}:{port}/api/data")
    print("Press Ctrl+C to terminate.")

    if single_request:
        httpd.handle_request()
    else:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server.")
        finally:
            httpd.server_close()

def main():
    parser = argparse.ArgumentParser(description="Serve the Affiliate Automation Command Center dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--single-request", action="store_true", help="Handle exactly one request and exit (for automated testing)")

    args = parser.parse_args()
    run_server(host=args.host, port=args.port, single_request=args.single_request)

if __name__ == "__main__":
    main()
