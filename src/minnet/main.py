import os
"""Minnet - Memory card matching game."""
import sys, os, json, random, gettext, locale
import time as _time
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from minnet import __version__
from minnet.accessibility import apply_large_text

TEXTDOMAIN = "minnet"
for p in [os.path.join(os.path.dirname(__file__), "locale"), "/usr/share/locale"]:
    if os.path.isdir(p):
        gettext.bindtextdomain(TEXTDOMAIN, p)
        locale.bindtextdomain(TEXTDOMAIN, p)
        break
gettext.textdomain(TEXTDOMAIN)
_ = gettext.gettext

CARD_EMOJIS = [
    "\U0001f431", "\U0001f436", "\U0001f42d", "\U0001f430", "\U0001f43b",
    "\U0001f437", "\U0001f438", "\U0001f42f", "\U0001f981", "\U0001f98a",
    "\U0001f427", "\U0001f99c", "\U0001f41d", "\U0001f98b", "\U0001f422",
    "\U0001f40b",
]
CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "minnet")
RESULTS_FILE = os.path.join(CONFIG_DIR, "results.json")

def _load_results():
    try:
        with open(RESULTS_FILE) as f: return json.load(f)
    except: return []

def _save_results(r):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(RESULTS_FILE, "w") as f: json.dump(r[-500:], f, ensure_ascii=False, indent=2)



def _settings_path():
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(xdg, "minnet")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")

def _load_settings():
    p = _settings_path()
    if os.path.exists(p):
        import json
        with open(p) as f:
            return json.load(f)
    return {}

def _save_settings(s):
    import json
    with open(_settings_path(), "w") as f:
        json.dump(s, f, indent=2)

class MemoryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="se.danielnylander.minnet",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        apply_large_text()
        win = self.props.active_window or MemoryWindow(application=self)
        win.present()
        if not self.settings.get("welcome_shown"):
            self._show_welcome(win)


    def do_startup(self):
        Adw.Application.do_startup(self)
        for name, cb, accel in [
            ("quit", lambda *_: self.quit(), "<Control>q"),
            ("about", self._on_about, None),
            ("export", self._on_export, "<Control>e"),
        ]:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accel: self.set_accels_for_action(f"app.{name}", [accel])

    def _on_about(self, *_):
        d = Adw.AboutDialog(application_name=_("Memory Training"), application_icon="minnet",
            version=__version__, developer_name="Daniel Nylander", website="https://www.autismappar.se",
            license_type=Gtk.License.GPL_3_0, developers=["Daniel Nylander"],
            copyright="\u00a9 2026 Daniel Nylander")
        d.present(self.props.active_window)

    def _on_export(self, *_):
        w = self.props.active_window
        if w: w.do_export()


class MemoryWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, default_width=550, default_height=700, title=_("Memory Training"))
        self.num_pairs = 6
        self.cards = []
        self.flipped = []
        self.matched = set()
        self.moves = 0
        self.start_time = 0
        self.results = _load_results()
        self._build_ui()
        self._new_game()

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)
        header = Adw.HeaderBar()
        box.append(header)

        menu = Gio.Menu()
        menu.append(_("Export Results"), "app.export")
        menu.append(_("About Memory Training"), "app.about")
        menu.append(_("Quit"), "app.quit")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))

        theme_btn = Gtk.Button(icon_name="weather-clear-night-symbolic",
                               tooltip_text=_("Toggle dark/light theme"))
        theme_btn.connect("clicked", self._toggle_theme)
        header.pack_end(theme_btn)

        diff_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        diff_box.set_margin_top(8)
        for pairs, label in [(4, _("Easy")), (6, _("Medium")), (8, _("Hard"))]:
            btn = Gtk.Button(label=label)
            btn.add_css_class("pill")
            btn.connect("clicked", self._set_difficulty, pairs)
            diff_box.append(btn)
        box.append(diff_box)

        self.stats_label = Gtk.Label(label=_("Moves: 0 | Time: 0s"))
        self.stats_label.add_css_class("title-4")
        self.stats_label.set_margin_top(8)
        box.append(self.stats_label)

        self.grid = Gtk.FlowBox(max_children_per_line=4, selection_mode=Gtk.SelectionMode.NONE,
                                 homogeneous=True, row_spacing=8, column_spacing=8)
        self.grid.set_margin_start(16)
        self.grid.set_margin_end(16)
        self.grid.set_margin_top(16)
        self.grid.set_vexpand(True)
        box.append(self.grid)

        new_btn = Gtk.Button(label=_("New Game"))
        new_btn.add_css_class("suggested-action")
        new_btn.add_css_class("pill")
        new_btn.set_halign(Gtk.Align.CENTER)
        new_btn.set_margin_top(8)
        new_btn.set_margin_bottom(8)
        new_btn.connect("clicked", lambda *_: self._new_game())
        box.append(new_btn)

        self.status_label = Gtk.Label(label="", xalign=0)
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_start(12)
        self.status_label.set_margin_bottom(4)
        box.append(self.status_label)
        GLib.timeout_add_seconds(1, self._tick)

    def _set_difficulty(self, btn, pairs):
        self.num_pairs = pairs
        self._new_game()

    def _new_game(self):
        self.cards = []
        self.flipped = []
        self.matched = set()
        self.moves = 0
        self.start_time = _time.time()

        emojis = random.sample(CARD_EMOJIS, self.num_pairs)
        deck = emojis * 2
        random.shuffle(deck)

        while (child := self.grid.get_first_child()):
            self.grid.remove(child)

        for i, emoji in enumerate(deck):
            btn = Gtk.Button(label="\u2753")
            btn.set_size_request(80, 80)
            btn.connect("clicked", self._on_card, i, emoji)
            self.grid.append(btn)
            self.cards.append({"emoji": emoji, "btn": btn, "flipped": False})

        self._update_stats()

    def _on_card(self, btn, idx, emoji):
        if len(self.flipped) >= 2 or idx in self.matched or self.cards[idx]["flipped"]:
            return
        self.cards[idx]["flipped"] = True
        btn.set_label(emoji)
        self.flipped.append(idx)

        if len(self.flipped) == 2:
            self.moves += 1
            i, j = self.flipped
            if self.cards[i]["emoji"] == self.cards[j]["emoji"]:
                self.matched.add(i)
                self.matched.add(j)
                self.flipped = []
                if len(self.matched) == len(self.cards):
                    self._game_won()
            else:
                GLib.timeout_add(800, self._flip_back, i, j)
            self._update_stats()

    def _flip_back(self, i, j):
        self.cards[i]["flipped"] = False
        self.cards[j]["flipped"] = False
        self.cards[i]["btn"].set_label("\u2753")
        self.cards[j]["btn"].set_label("\u2753")
        self.flipped = []
        return False

    def _update_stats(self):
        elapsed = int(_time.time() - self.start_time)
        self.stats_label.set_label(_("Moves: %d | Time: %ds") % (self.moves, elapsed))

    def _game_won(self):
        elapsed = int(_time.time() - self.start_time)
        from datetime import datetime
        self.results.append({"date": datetime.now().isoformat(), "pairs": self.num_pairs,
                              "moves": self.moves, "time": elapsed})
        _save_results(self.results)
        dialog = Adw.MessageDialog(transient_for=self,
            heading=_("Congratulations!"),
            body=_("You matched all pairs in %d moves and %d seconds!") % (self.moves, elapsed))
        dialog.add_response("ok", _("New Game"))
        dialog.connect("response", lambda *_: self._new_game())
        dialog.present()

    def do_export(self):
        from minnet.export import export_csv, export_json
        os.makedirs(CONFIG_DIR, exist_ok=True)
        ts = GLib.DateTime.new_now_local().format("%Y%m%d_%H%M%S")
        data = [{"date": r["date"], "details": f'{r["pairs"]} pairs',
                 "result": f'{r["moves"]} moves, {r["time"]}s'} for r in self.results]
        export_csv(data, os.path.join(CONFIG_DIR, f"export_{ts}.csv"))
        export_json(data, os.path.join(CONFIG_DIR, f"export_{ts}.json"))

    def _toggle_theme(self, *_):
        mgr = Adw.StyleManager.get_default()
        mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if mgr.get_dark() else Adw.ColorScheme.FORCE_DARK)

    def _tick(self):
        self.status_label.set_label(GLib.DateTime.new_now_local().format("%Y-%m-%d %H:%M:%S"))
        if len(self.matched) < len(self.cards):
            self._update_stats()
        return True


def main():
    app = MemoryApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()

    # ── Welcome Dialog ───────────────────────────────────────

    def _show_welcome(self, win):
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(480)

        page = Adw.StatusPage()
        page.set_icon_name("minnet")
        page.set_title(_("Welcome to Memory Training"))
        page.set_description(_(
            "Train your memory with card-matching games.\n\n✓ Classic memory card game\n✓ Multiple difficulty levels\n✓ Track your progress\n✓ Fun for the whole family"
        ))

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        page.set_child(btn)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()

