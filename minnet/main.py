"""Minnet — Working memory training games."""

import gettext
import json
import locale
import random
from datetime import datetime
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from minnet import __version__
from minnet.export import show_export_dialog

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
for d in [Path(__file__).parent.parent / "po", Path("/usr/share/locale")]:
    if d.is_dir():
        locale.bindtextdomain("minnet", str(d))
        gettext.bindtextdomain("minnet", str(d))
        break
gettext.textdomain("minnet")
_ = gettext.gettext

APP_ID = "se.danielnylander.minnet"

CARD_EMOJIS = ["🐱", "🐶", "🐟", "🌸", "⭐", "🎈", "🚗", "🏠",
               "🌈", "🦋", "🍎", "🎵", "🌻", "🐸", "🎂", "🦄"]


def _config_dir():
    p = Path(GLib.get_user_config_dir()) / "minnet"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _load_results():
    path = _config_dir() / "results.json"
    if path.exists():
        try: return json.loads(path.read_text())
        except Exception: pass
    return []

def _save_results(results):
    (_config_dir() / "results.json").write_text(
        json.dumps(results[-300:], indent=2, ensure_ascii=False))


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Memory Training"))
        self.set_default_size(500, 650)
        self.results = _load_results()
        self.pairs = 4
        self.cards = []
        self.revealed = []
        self.matched = set()
        self.moves = 0
        self.score = 0

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        header = Adw.HeaderBar()
        main_box.append(header)

        self.score_label = Gtk.Label(label="⭐ 0")
        self.score_label.add_css_class("title-3")
        header.pack_start(self.score_label)

        export_btn = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Export (Ctrl+E)"))
        export_btn.connect("clicked", lambda *_: self._on_export())
        header.pack_end(export_btn)

        menu = Gio.Menu()
        menu.append(_("Export Results"), "win.export")
        menu.append(_("About Memory Training"), "app.about")
        menu.append(_("Quit"), "app.quit")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        ea = Gio.SimpleAction.new("export", None)
        ea.connect("activate", lambda *_: self._on_export())
        self.add_action(ea)

        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.add_controller(ctrl)

        # Difficulty
        diff_box = Gtk.Box(spacing=0, halign=Gtk.Align.CENTER)
        diff_box.add_css_class("linked")
        diff_box.set_margin_top(8)
        first = None
        for label, n in [(_("Easy"), 4), (_("Medium"), 6), (_("Hard"), 8)]:
            btn = Gtk.ToggleButton(label=label)
            if first is None:
                first = btn
                btn.set_active(True)
            else:
                btn.set_group(first)
            btn.connect("toggled", self._on_diff, n)
            diff_box.append(btn)
        main_box.append(diff_box)

        # Card grid
        self.grid = Gtk.FlowBox()
        self.grid.set_max_children_per_line(4)
        self.grid.set_min_children_per_line(4)
        self.grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.grid.set_homogeneous(True)
        self.grid.set_column_spacing(8)
        self.grid.set_row_spacing(8)
        self.grid.set_margin_top(16)
        self.grid.set_margin_start(16)
        self.grid.set_margin_end(16)
        self.grid.set_margin_bottom(8)
        main_box.append(self.grid)

        # Moves label
        self.moves_label = Gtk.Label(label=_("Moves: 0"))
        self.moves_label.add_css_class("dim-label")
        self.moves_label.set_margin_top(8)
        main_box.append(self.moves_label)

        # New game button
        new_btn = Gtk.Button(label=_("New Game"))
        new_btn.add_css_class("suggested-action")
        new_btn.add_css_class("pill")
        new_btn.set_halign(Gtk.Align.CENTER)
        new_btn.set_margin_top(8)
        new_btn.connect("clicked", lambda *_: self._new_game())
        main_box.append(new_btn)

        spacer = Gtk.Box(vexpand=True)
        main_box.append(spacer)

        self.status = Gtk.Label(label="", xalign=0)
        self.status.add_css_class("dim-label")
        self.status.set_margin_start(12)
        self.status.set_margin_bottom(4)
        main_box.append(self.status)
        GLib.timeout_add_seconds(1, self._tick)

        self._new_game()

    def _tick(self):
        self.status.set_label(GLib.DateTime.new_now_local().format("%Y-%m-%d %H:%M:%S"))
        return True

    def _on_key(self, ctrl, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK and keyval in (Gdk.KEY_e, Gdk.KEY_E):
            self._on_export()
            return True
        return False

    def _on_export(self):
        show_export_dialog(self, self.results, _("Memory Training Results"), lambda m: self.status.set_label(m))

    def _on_diff(self, btn, n):
        if btn.get_active():
            self.pairs = n
            self._new_game()

    def _new_game(self):
        emojis = random.sample(CARD_EMOJIS, self.pairs)
        self.cards = emojis * 2
        random.shuffle(self.cards)
        self.revealed = []
        self.matched = set()
        self.moves = 0
        self.moves_label.set_label(_("Moves: 0"))
        self._build_cards()

    def _build_cards(self):
        child = self.grid.get_first_child()
        while child:
            nc = child.get_next_sibling()
            self.grid.remove(child)
            child = nc

        cols = 4 if self.pairs <= 6 else 4
        self.grid.set_max_children_per_line(cols)
        self.grid.set_min_children_per_line(cols)

        self.card_buttons = []
        for i, emoji in enumerate(self.cards):
            btn = Gtk.Button(label="❓")
            btn.add_css_class("title-2")
            btn.set_size_request(80, 80)
            btn.connect("clicked", self._on_card_click, i)
            self.grid.insert(btn, -1)
            self.card_buttons.append(btn)

    def _on_card_click(self, btn, idx):
        if idx in self.matched or idx in self.revealed:
            return
        if len(self.revealed) >= 2:
            return

        btn.set_label(self.cards[idx])
        self.revealed.append(idx)

        if len(self.revealed) == 2:
            self.moves += 1
            self.moves_label.set_label(_("Moves: %d") % self.moves)
            i, j = self.revealed
            if self.cards[i] == self.cards[j]:
                self.matched.add(i)
                self.matched.add(j)
                self.revealed = []
                if len(self.matched) == len(self.cards):
                    self.score += 1
                    self.score_label.set_label(f"⭐ {self.score}")
                    self.results.append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "pairs": self.pairs,
                        "moves": self.moves,
                        "won": True,
                    })
                    _save_results(self.results)
                    self.status.set_label(_("🎉 You found all pairs in %d moves!") % self.moves)
            else:
                GLib.timeout_add(800, self._hide_cards, i, j)

    def _hide_cards(self, i, j):
        if i < len(self.card_buttons):
            self.card_buttons[i].set_label("❓")
        if j < len(self.card_buttons):
            self.card_buttons[j].set_label("❓")
        self.revealed = []
        return False


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

    def _on_activate(self, *_):
        win = self.props.active_window or MainWindow(self)
        a = Gio.SimpleAction(name="about")
        a.connect("activate", self._on_about)
        self.add_action(a)
        qa = Gio.SimpleAction(name="quit")
        qa.connect("activate", lambda *_: self.quit())
        self.add_action(qa)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        win.present()

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(
            application_name=_("Memory Training"),
            application_icon=APP_ID,
            version=__version__,
            developer_name="Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://www.autismappar.se",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            comments=_("Working memory training games for autism and ADHD"),
        )
        dialog.present(self.props.active_window)


def main():
    app = App()
    return app.run()
