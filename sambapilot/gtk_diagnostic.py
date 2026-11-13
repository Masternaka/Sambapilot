"""Diagnostic local demandé et dépannage partagé, sans accès hôte à l'ouverture."""

from datetime import datetime, timezone
from threading import Thread

from gi.repository import GLib, Gtk

from .cli import render
from .demo import DemoProbe, SCENARIOS
from .diagnostic import collect
from .distributions import PROFILES
from .system import HostProbe
from .troubleshooting import SYMPTOMS, format_troubleshooting, troubleshoot


class DiagnosticPage(Gtk.Box):
    def __init__(self, source_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ("top", "bottom", "start", "end"):
            getattr(self, "set_margin_" + side)(24)
        self.source_changed = source_changed
        self.source = "demo"
        self.generation = 0
        self.report = None
        title = Gtk.Label(label="Diagnostic et dépannage", xalign=0)
        title.add_css_class("title-1")
        self.append(title)
        self.append(Gtk.Label(label="Choisissez un exemple ou demandez un constat local. "
                              "Aucun fichier de configuration n’est lu et aucun réglage n’est appliqué.", xalign=0, wrap=True))
        examples = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.distribution = Gtk.DropDown.new_from_strings([profile.name + " · exemple" for profile in PROFILES.values()])
        self.scenario = Gtk.DropDown.new_from_strings(["Sans Samba · exemple", "Déjà installé · exemple", "Accès restreint · exemple"])
        self.scenario.set_selected(1)
        self.distribution.set_tooltip_text("Distribution des données fictives")
        self.scenario.set_tooltip_text("État des données fictives")
        examples.append(self.distribution)
        examples.append(self.scenario)
        demo = Gtk.Button(label="Revenir aux exemples")
        demo.connect("clicked", self.use_demo)
        examples.append(demo)
        self.append(examples)
        self.local = Gtk.Button(label="Examiner cet ordinateur (lecture seule)", halign=Gtk.Align.START)
        self.local.connect("clicked", self.examine_local)
        self.append(self.local)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.append(self.status)
        self.output = self.add_output(260)
        subtitle = Gtk.Label(label="Assistant de dépannage", xalign=0)
        subtitle.add_css_class("heading")
        self.append(subtitle)
        self.symptom = Gtk.DropDown.new_from_strings(list(SYMPTOMS.values()))
        self.symptom.set_tooltip_text("Symptôme à examiner à partir du constat affiché")
        self.symptom.connect("notify::selected", self.update_troubleshooting)
        self.append(self.symptom)
        self.help_output = self.add_output(240)
        self.distribution.connect("notify::selected", self.use_demo)
        self.scenario.connect("notify::selected", self.use_demo)
        self.show_report(collect(DemoProbe()))

    def add_output(self, height):
        output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True,
                              wrap_mode=Gtk.WrapMode.WORD_CHAR)
        area = Gtk.ScrolledWindow(hexpand=True, vexpand=True, min_content_height=height)
        area.set_child(output)
        self.append(area)
        return output

    def use_demo(self, *_args):
        self.generation += 1
        family = tuple(PROFILES)[self.distribution.get_selected()]
        scenario = SCENARIOS[self.scenario.get_selected()]
        self.source = "demo"
        self.show_report(collect(DemoProbe(scenario, family)))
        self.local.set_sensitive(True)
        self.source_changed()

    def show_report(self, report):
        self.report = report
        self.output.get_buffer().set_text(render(report))
        origin = "Exemple fictif" if report.mode == "demo" else "Constat local · Lecture seule"
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.status.set_text(origin + " · " + report.environment.distribution_name + " · Rapport produit : " + timestamp)
        self.update_troubleshooting()

    def update_troubleshooting(self, *_args):
        if self.report is None:
            self.help_output.get_buffer().set_text("")
            return
        symptom = tuple(SYMPTOMS)[self.symptom.get_selected()]
        self.help_output.get_buffer().set_text(format_troubleshooting(troubleshoot(self.report, symptom)))

    def examine_local(self, _button=None):
        self.generation += 1
        self.source = "live"
        self.report = None
        self.output.get_buffer().set_text("")
        self.update_troubleshooting()
        self.local.set_sensitive(False)
        self.status.set_text("Consultation locale des métadonnées, outils et services en cours…")
        self.source_changed()
        Thread(target=self.read_local, args=(self.generation,), daemon=True).start()

    def read_local(self, generation):
        try:
            report = collect(HostProbe())
        except (OSError, ValueError):
            report = None
        GLib.idle_add(self.receive_report, generation, report)

    def receive_report(self, generation, report):
        if generation != self.generation:
            return False
        self.local.set_sensitive(True)
        if report is None:
            self.status.set_text("Consultation interrompue ; aucun résultat local disponible.")
        else:
            self.show_report(report)
        return False

    def close(self):
        self.generation += 1
