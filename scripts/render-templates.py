#!/usr/bin/env python3
"""Render the cron wrapper templates and shellcheck the result.

The wrappers are Jinja, so shellcheck cannot read templates/*.j2 directly —
and the `wp_monitoring_alert_email` conditional means each template produces
two materially different scripts. This renders both branches with
representative values and runs shellcheck over everything.

    python3 scripts/render-templates.py           # render to a temp dir, print paths
    python3 scripts/render-templates.py --check   # render, shellcheck, exit non-zero on failure
"""

import os
import subprocess
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Representative values; the point is valid shell, not real configuration.
CONTEXT = {
    "item": {"key": "example.com"},
    "wp_monitoring_dir": "/home/web/monitoring",
    "wp_monitoring_log_file": "/srv/www/example.com/logs/access.log",
    "wp_monitoring_traffic_hours": 24,
    "wp_monitoring_weekly_hours": 168,
    "wp_monitoring_security_hours": 6,
    "wp_monitoring_security_threshold": 100,
    "wp_monitoring_traffic_retention_days": 30,
    "wp_monitoring_security_retention_days": 7,
    "wp_monitoring_weekly_retention_days": 90,
}


def render(outdir):
    tpl_dir = os.path.join(ROOT, "templates")
    env = Environment(loader=FileSystemLoader(tpl_dir), keep_trailing_newline=True)
    written = []
    for name in sorted(os.listdir(tpl_dir)):
        if not name.endswith(".j2"):
            continue
        for email in ("alerts@example.com", ""):
            label = "mail" if email else "nomail"
            body = env.get_template(name).render(
                wp_monitoring_alert_email=email, **CONTEXT
            )
            path = os.path.join(outdir, f"{label}-{name[:-3]}")
            with open(path, "w") as fh:
                fh.write(body)
            written.append(path)
    return written


def main():
    check = "--check" in sys.argv
    outdir = tempfile.mkdtemp(prefix="wp-monitoring-render-")
    written = render(outdir)

    if not check:
        for path in written:
            print(path)
        return 0

    failed = subprocess.call(["shellcheck", *written])
    if failed:
        print(f"\nRendered scripts are in {outdir}", file=sys.stderr)
        return failed

    print(f"shellcheck clean across {len(written)} rendered wrappers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
