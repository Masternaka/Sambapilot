"""Aperçu d'export GTK : le contenu examiné est figé avant la sélection de destination."""

from gi.repository import GLib, Gtk

from .report_export import PERSONAL_DATA_NOTICE, ReportExportError, prepare_report, save_report


class ReportExportWindow(Gtk.Window):
    def __init__(self, owner, report, generation):
        super().__init__(title="Aperçu du rapport Markdown", transient_for=owner, modal=True)
        self.set_destroy_with_parent(True)
        self.set_default_size(900, 650)
        self.owner = owner
        self.source_report = report
        self.generation = generation
        self.prepared = prepare_report(report)
        self.active = True
        self.connect("close-request", self.on_close)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        content.append(Gtk.Label(label=PERSONAL_DATA_NOTICE, wrap=True, xalign=0))
        self.preview = Gtk.TextView(editable=False, cursor_visible=False, monospace=True,
                                    wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.preview.get_buffer().set_text(self.prepared.markdown)
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_child(self.preview)
        content.append(scroll)
        self.status = Gtk.Label(label="Aucun fichier créé. Choisissez un nouveau nom en .md ; aucun écrasement.",
                                wrap=True, xalign=0, selectable=True)
        content.append(self.status)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.save_button = Gtk.Button(label="Choisir où enregistrer…")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self.choose_destination)
        close = Gtk.Button(label="Fermer")
        close.connect("clicked", lambda _button: self.close())
        actions.append(self.save_button)
        actions.append(close)
        content.append(actions)
        self.set_child(content)

    def is_current(self):
        return (self.active and self.owner.inspection_report is self.source_report
                and self.owner.inspection_generation == self.generation)

    def on_close(self, *_args):
        self.active = False
        return False

    def choose_destination(self, _button):
        if not self.is_current():
            self.status.set_text("Le rapport a changé. Fermez cet aperçu et préparez-en un nouveau.")
            self.save_button.set_sensitive(False)
            return
        self.save_button.set_sensitive(False)
        dialog = Gtk.FileDialog(title="Enregistrer un nouveau rapport Markdown", modal=True)
        dialog.set_initial_name("sambapilot-rapport.md")
        dialog.save(self, None, self.destination_selected)

    def destination_selected(self, dialog, result):
        try:
            selected = dialog.save_finish(result)
        except GLib.Error:
            if self.is_current():
                self.status.set_text("Enregistrement annulé ou indisponible. Aucun fichier créé.")
                self.save_button.set_sensitive(True)
            return
        if not self.is_current():
            return
        self.save_button.set_sensitive(True)
        filename = selected.get_path() if selected else None
        if not filename:
            self.status.set_text("Choisissez un chemin local pour un nouveau fichier .md.")
            return
        try:
            destination = save_report(self.prepared, filename)
        except ReportExportError as error:
            self.status.set_text(str(error))
            return
        self.status.set_text("Rapport enregistré : " + str(destination) + ". Aucun réglage système modifié.")
