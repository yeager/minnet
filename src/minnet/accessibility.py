"""Accessibility helpers for children\'s apps."""
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

_LARGE_TEXT_CSS = """
* { font-size: 18px; }
button > label { font-size: 20px; font-weight: bold; }
.pill > label { font-size: 20px; font-weight: bold; }
.title-1 { font-size: 36px; font-weight: bold; }
.title-2 { font-size: 28px; font-weight: bold; }
.title-3 { font-size: 24px; font-weight: 600; }
.title-4 { font-size: 20px; font-weight: 600; }
list row label, listview row label { font-size: 18px; }
entry > text { font-size: 18px; }
.dim-label { font-size: 15px; }
messagedialog label { font-size: 18px; }
"""

def apply_large_text():
    provider = Gtk.CssProvider()
    provider.load_from_string(_LARGE_TEXT_CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_USER)
