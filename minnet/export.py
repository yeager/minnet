"""Export functionality for Memory Training."""

import csv
import io
import json
from datetime import datetime

import gettext
_ = gettext.gettext

from minnet import __version__

APP_LABEL = _("Memory Training")
AUTHOR = "Daniel Nylander"
WEBSITE = "www.autismappar.se"

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib


def data_to_csv(items, label=""):
    """Export data as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    if items and isinstance(items[0], dict):
        writer.writerow(items[0].keys())
        for item in items:
            writer.writerow(item.values())
    writer.writerow([])
    writer.writerow([f"{APP_LABEL} v{__version__} — {WEBSITE}"])
    return output.getvalue()


def data_to_json(items, label=""):
    """Export data as JSON."""
    data = {
        "data": items,
        "_exported_by": f"{APP_LABEL} v{__version__}",
        "_author": AUTHOR,
        "_website": WEBSITE,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_data_pdf(items, title, output_path):
    """Export data as PDF."""
    try:
        import cairo
    except ImportError:
        try:
            import cairocffi as cairo
        except ImportError:
            return False

    width, height = 595, 842
    surface = cairo.PDFSurface(output_path, width, height)
    ctx = cairo.Context(surface)

    ctx.set_font_size(24)
    ctx.move_to(40, 50)
    ctx.show_text(title)

    ctx.set_font_size(12)
    ctx.move_to(40, 75)
    ctx.show_text(datetime.now().strftime("%Y-%m-%d"))

    y = 110
    ctx.set_font_size(12)
    for item in items:
        if y > height - 40:
            surface.show_page()
            y = 40
        if isinstance(item, dict):
            text = " | ".join(str(v) for v in item.values())
        else:
            text = str(item)
        ctx.move_to(40, y)
        ctx.show_text(text[:80])
        y += 20

    ctx.set_font_size(9)
    ctx.set_source_rgb(0.5, 0.5, 0.5)
    footer = f"{APP_LABEL} v{__version__} — {WEBSITE} — {datetime.now().strftime('%Y-%m-%d')}"
    ctx.move_to(40, height - 20)
    ctx.show_text(footer)

    surface.finish()
    return True


def show_export_dialog(window, items, title="", status_callback=None):
    """Show export dialog."""
    dialog = Adw.AlertDialog.new(_("Export"), _("Choose export format:"))
    dialog.add_response("cancel", _("Cancel"))
    dialog.add_response("csv", _("CSV"))
    dialog.add_response("json", _("JSON"))
    dialog.add_response("pdf", _("PDF"))
    dialog.set_default_response("csv")
    dialog.set_close_response("cancel")
    dialog.connect("response", _on_response, window, items, title, status_callback)
    dialog.present(window)


def _on_response(dialog, response, window, items, title, status_callback):
    if response == "cancel":
        return
    ext = response
    fd = Gtk.FileDialog.new()
    fd.set_title(_("Save Export"))
    fd.set_initial_name(f"minnet_{datetime.now().strftime('%Y-%m-%d')}.{ext}")
    fd.save(window, None, _on_save, items, title, ext, status_callback)


def _on_save(dialog, result, items, title, ext, status_callback):
    try:
        gfile = dialog.save_finish(result)
    except GLib.Error:
        return
    path = gfile.get_path()
    try:
        if ext == "csv":
            with open(path, "w") as f:
                f.write(data_to_csv(items))
        elif ext == "json":
            with open(path, "w") as f:
                f.write(data_to_json(items))
        elif ext == "pdf":
            export_data_pdf(items, title or APP_LABEL, path)
        if status_callback:
            status_callback(_("Exported %s") % ext.upper())
    except Exception as e:
        if status_callback:
            status_callback(_("Export error: %s") % str(e))
