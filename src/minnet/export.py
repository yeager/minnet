"""Export functionality for minnet."""
import csv
import json
import gettext
import os
from datetime import datetime
from minnet import __version__

_ = gettext.gettext

APP_LABEL = _("Memory Training")
WEBSITE = "www.autismappar.se"


def _footer():
    return f"{APP_LABEL} v{__version__} — {WEBSITE}"


def export_csv(data, filepath):
    """Export data to CSV with branding footer."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([_("Date"), _("Details"), _("Result")])
        for entry in data:
            writer.writerow([entry.get("date", ""), entry.get("details", ""), entry.get("result", "")])
        writer.writerow([])
        writer.writerow([_footer()])


def export_json(data, filepath):
    """Export data to JSON with branding."""
    out = {
        "app": APP_LABEL,
        "version": __version__,
        "_website": WEBSITE,
        "exported": datetime.now().isoformat(),
        "data": data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def export_pdf(data, filepath):
    """Export data to simple text-PDF with branding footer."""
    lines = [f"{APP_LABEL} — {_(\"Export\")}", ""]
    for entry in data:
        lines.append(f"{entry.get(\'date\', \'\')} | {entry.get(\'details\', \'\')} | {entry.get(\'result\', \'\')}")
    lines.extend(["", _footer()])
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
