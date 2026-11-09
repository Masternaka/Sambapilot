"""Page GTK de préparation de l'installation, sans bouton d'exécution."""

from threading import Thread
from gi.repository import GLib, Gtk

from .demo import SCENARIOS
from .setup import DemoSetupProbe, HostSetupProbe, collect_installation_plan, format_installation


class InstallationPage(Gtk.Box):
    def __init__(self, source_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ("top", "bottom", "start", "end"):
            getattr(self, "set_margin_" + side)(24)
        self.source_changed = source_changed
        self.source = "demo"
        self.generation = 0
        self.current_plan = collect_installation_plan(DemoSetupProbe("fresh"))
        title = Gtk.Label(label="Préparer l’installation", xalign=0)
        title.add_css_class("title-1")
        self.append(title)
        self.append(Gtk.Label(label="Examinez les composants et les étapes nécessaires. "
                              "Aucun paquet ne sera installé et aucun réglage ne sera appliqué.", xalign=0, wrap=True))
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.scenario = Gtk.DropDown.new_from_strings(["Sans Samba · exemple", "Déjà installé · exemple", "Accès restreint · exemple"])
        self.scenario.set_tooltip_text("Scénario utilisé lors de la préparation d’un plan d’exemple")
        controls.append(self.scenario)
        demo = Gtk.Button(label="Préparer l’exemple")
        demo.connect("clicked", self.prepare_demo)
        controls.append(demo)
        self.append(controls)
        local = Gtk.Button(label="Examiner cet ordinateur (lecture seule)", halign=Gtk.Align.START)
        local.connect("clicked", self.examine_local)
        self.append(local)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.append(self.status)
        self.output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        area = Gtk.ScrolledWindow(hexpand=True, vexpand=True, min_content_height=350)
        area.set_child(self.output)
        self.append(area)
        self.append(Gtk.Label(label="La transaction exacte, les comptes, les dossiers et les réseaux restent à examiner. "
                              "Cette page ne peut exécuter aucune intervention.", xalign=0, wrap=True))
        self.display_plan(self.current_plan)

    def display_plan(self, plan):
        self.current_plan = plan
        self.output.get_buffer().set_text(format_installation(plan))
        origin = "Exemple fictif" if plan.mode == "demo" else "Constat local en lecture seule"
        self.status.set_text(origin + " · " + ("points bloquants à résoudre" if plan.status == "blocked"
                                               else "choix et interventions à examiner") + ". Aucun changement exécuté.")

    def prepare_demo(self, _button=None):
        self.generation += 1
        self.source = "demo"
        index = self.scenario.get_selected()
        scenario = SCENARIOS[index] if 0 <= index < len(SCENARIOS) else "fresh"
        self.display_plan(collect_installation_plan(DemoSetupProbe(scenario)))
        self.source_changed()

    def examine_local(self, _button):
        self.generation += 1
        self.source = "live"
        self.current_plan = None
        self.output.get_buffer().set_text("")
        self.status.set_text("Consultation locale des composants, services et paquets ; aucune installation…")
        self.source_changed()
        Thread(target=self.read_local, args=(self.generation,), daemon=True).start()

    def read_local(self, generation):
        try:
            plan = collect_installation_plan(HostSetupProbe())
        except (OSError, ValueError):
            GLib.idle_add(self.receive_plan, generation, None)
            return
        GLib.idle_add(self.receive_plan, generation, plan)

    def receive_plan(self, generation, plan):
        if generation != self.generation:
            return False
        if plan is None:
            self.current_plan = None
            self.output.get_buffer().set_text("")
            self.status.set_text("Consultation interrompue ; aucun plan local ni changement appliqué.")
        else:
            self.display_plan(plan)
        return False

    def close(self):
        self.generation += 1
