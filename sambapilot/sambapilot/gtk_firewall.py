"""Formulaire GTK d'intentions de règles, sans appel au pare-feu système."""

from gi.repository import Gtk

from .firewall import MANAGERS, FirewallIntent, FirewallPlanError, format_firewall, parse_sources, prepare_firewall


class FirewallPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ("top", "bottom", "start", "end"):
            getattr(self, "set_margin_" + side)(24)
        self.current_plan = None
        title = Gtk.Label(label="Préparer les règles de pare-feu", xalign=0)
        title.add_css_class("title-1")
        self.append(title)
        self.append(Gtk.Label(label="Choisissez le périmètre à examiner. Le gestionnaire et les règles existantes "
                              "ne sont pas consultés ; aucun port ne sera ouvert.", xalign=0, wrap=True))
        self.manager = Gtk.DropDown.new_from_strings(["Choisir un gestionnaire", "UFW", "firewalld", "nftables"])
        self.interface = Gtk.Entry(placeholder_text="Nom de l’interface d’entrée")
        self.sources = Gtk.Entry(placeholder_text="Réseaux CIDR séparés par des virgules")
        self.zone = Gtk.Entry(placeholder_text="Zone existante à vérifier, pour firewalld")
        self.zone.set_sensitive(False)
        for text, widget in (("Gestionnaire choisi", self.manager), ("Interface d’entrée", self.interface),
                             ("Réseaux ou appareils autorisés (/32 ou /128 pour un appareil)", self.sources),
                             ("Zone firewalld", self.zone)):
            field = Gtk.Label(label=text, xalign=0, wrap=True)
            field.set_mnemonic_widget(widget)
            self.append(field)
            self.append(widget)
        self.legacy = Gtk.CheckButton(label="Ajouter NetBIOS pour les sources IPv4 (TCP 139, UDP 137/138)")
        self.append(self.legacy)
        self.append(Gtk.Label(label="Sans cette option, seul TCP 445 est proposé. Aucun réseau ni gestionnaire "
                              "n’est présélectionné.", xalign=0, wrap=True))
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        preview = Gtk.Button(label="Générer l’aperçu réseau")
        preview.add_css_class("suggested-action")
        preview.connect("clicked", self.preview)
        reset = Gtk.Button(label="Annuler le périmètre")
        reset.connect("clicked", self.reset)
        controls.append(preview)
        controls.append(reset)
        self.append(controls)
        self.status = Gtk.Label(label="Aucun périmètre défini. Aucun changement appliqué.", xalign=0, wrap=True, selectable=True)
        self.append(self.status)
        self.output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        area = Gtk.ScrolledWindow(hexpand=True, vexpand=True, min_content_height=320)
        area.set_child(self.output)
        self.append(area)
        for entry in (self.interface, self.sources, self.zone):
            entry.connect("changed", self.invalidate)
        self.manager.connect("notify::selected", self.manager_changed)
        self.legacy.connect("toggled", self.invalidate)

    def invalidate(self, *_args):
        self.current_plan = None
        self.output.get_buffer().set_text("")
        self.status.set_text("Périmètre à vérifier ; l’aperçu précédent a été abandonné.")

    def manager_changed(self, *_args):
        firewalld = self.manager.get_selected() == 2
        self.zone.set_sensitive(firewalld)
        if not firewalld:
            self.zone.set_text("")
        self.invalidate()

    def preview(self, _button=None):
        self.invalidate()
        try:
            index = self.manager.get_selected()
            manager = MANAGERS[index - 1] if 0 < index <= len(MANAGERS) else ""
            intent = FirewallIntent(manager, self.interface.get_text(), parse_sources(self.sources.get_text()),
                                    self.zone.get_text() if manager == "firewalld" else None, self.legacy.get_active())
            plan = prepare_firewall(intent)
        except FirewallPlanError as error:
            self.status.set_text("Aperçu refusé : " + str(error))
            return
        self.current_plan = plan
        self.output.get_buffer().set_text(format_firewall(plan))
        self.status.set_text("Intentions produites pour " + str(len(plan.rules)) + " règles. Aucun port ouvert ; règles existantes non examinées.")

    def reset(self, _button=None):
        self.manager.set_selected(0)
        self.interface.set_text("")
        self.sources.set_text("")
        self.zone.set_text("")
        self.legacy.set_active(False)
        self.invalidate()
        self.status.set_text("Périmètre abandonné. Aucun changement appliqué.")
