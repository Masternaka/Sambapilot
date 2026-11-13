"""Fiche GTK par partage, observations locales explicites et sources invalidables."""

from threading import Thread
from gi.repository import GLib, Gtk

from .inspection import InspectionError, read_configuration
from .share_diagnostic import ShareDiagnosticError, format_share_diagnostic, prepare_share_diagnostic
from .troubleshooting import SYMPTOMS
from .volumes import DemoVolumeProbe, VOLUME_SCENARIOS, VolumeError, collect_volume, validate_volume_paths
from .volume_system import HostVolumeProbe


class ShareDiagnosticWindow(Gtk.Window):
    def __init__(self, owner, report, share_name):
        super().__init__(title='Diagnostic du partage', transient_for=owner, modal=True)
        self.set_destroy_with_parent(True)
        self.set_default_size(900, 740)
        self.owner, self.source_report, self.share_name = owner, report, share_name
        self.source_generation, self.snapshot = owner.inspection_generation, owner.inspection_snapshot
        self.active, self.source_stale, self.generation = True, False, 0
        self.volume, self.prepared = None, None
        self.connect('close-request', self.on_close)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        content.append(Gtk.Label(label='Partage : ' + share_name, xalign=0, selectable=True, wrap=True))
        content.append(Gtk.Label(label='Déclarations et droits effectifs restent distincts. '
                                'Aucune consultation locale ni connexion réseau à l’ouverture.', xalign=0, wrap=True))
        self.server = Gtk.Entry(placeholder_text='Serveur facultatif : nom DNS ou IPv4, sans identifiants')
        self.server.set_tooltip_text('Préparer les adresses, sans résolution DNS ni connexion')
        self.symptom = Gtk.DropDown.new_from_strings(list(SYMPTOMS.values()))
        self.symptom.set_tooltip_text('Symptôme à examiner pour ce partage')
        content.append(self.server)
        content.append(self.symptom)
        content.append(Gtk.Label(label='Volume facultatif : indiquer le point attendu. Le fichier peut provenir d’un autre serveur.', xalign=0, wrap=True))
        self.mountpoint = Gtk.Entry(placeholder_text='Point attendu, par exemple /mnt/medias')
        content.append(self.mountpoint)
        self.local_confirm = Gtk.CheckButton(label='Je confirme que le dossier décrit appartient à cet ordinateur')
        self.local_confirm.set_sensitive(report.mode == 'file')
        content.append(self.local_confirm)
        volume_actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.volume_scenario = Gtk.DropDown.new_from_strings(['Monté · exemple', 'Non monté · exemple', 'Lecture seule · exemple',
                                                            'Dossier absent · exemple', 'État inconnu · exemple'])
        self.volume_scenario.set_sensitive(report.mode == 'demo')
        self.demo_button = Gtk.Button(label='Examiner le volume fictif')
        self.demo_button.set_sensitive(report.mode == 'demo')
        self.demo_button.connect('clicked', self.examine_demo)
        self.local_button = Gtk.Button(label='Examiner le dossier sur cet ordinateur')
        self.local_button.set_sensitive(False)
        self.local_button.connect('clicked', self.examine_local)
        for widget in (self.volume_scenario, self.demo_button, self.local_button):
            volume_actions.append(widget)
        content.append(volume_actions)
        self.status = Gtk.Label(xalign=0, selectable=True, wrap=True)
        content.append(self.status)
        self.output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        area = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        area.set_child(self.output)
        content.append(area)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.copy_buttons = {}
        for key, title in (('windows', 'Copier Windows'), ('macos', 'Copier SMB')):
            button = Gtk.Button(label=title)
            button.connect('clicked', lambda _button, client=key: self.copy_address(client))
            self.copy_buttons[key] = button
            actions.append(button)
        close = Gtk.Button(label='Fermer')
        close.connect('clicked', lambda _button: self.close())
        actions.append(close)
        content.append(actions)
        self.set_child(content)
        for entry in (self.server, self.mountpoint):
            entry.connect('changed', self.invalidate)
        for dropdown in (self.symptom, self.volume_scenario):
            dropdown.connect('notify::selected', self.invalidate)
        self.local_confirm.connect('toggled', self.invalidate)
        self.refresh()

    def is_current(self):
        if not self.active or self.source_stale or self.source_generation != self.owner.inspection_generation:
            return False
        return (not self.owner.file_shares_mode if self.source_report.mode == 'demo' else
                self.owner.file_shares_mode and self.snapshot is self.owner.inspection_snapshot)

    def invalidate(self, *_args):
        self.generation += 1
        self.volume = None
        self.refresh()

    def refresh(self):
        self.prepared = None
        for button in self.copy_buttons.values():
            button.set_sensitive(False)
        self.local_button.set_sensitive(False)
        if not self.is_current():
            self.output.get_buffer().set_text('')
            self.status.set_text('La source a changé ou doit être rechargée. Fermez cette fiche et rechargez le fichier.')
            return
        try:
            symptom = tuple(SYMPTOMS)[self.symptom.get_selected()]
            self.prepared = prepare_share_diagnostic(self.source_report, self.share_name, symptom,
                                                      self.server.get_text() or None, self.volume)
        except ShareDiagnosticError as error:
            self.output.get_buffer().set_text('')
            self.status.set_text(str(error))
            return
        self.output.get_buffer().set_text(format_share_diagnostic(self.prepared))
        for button in self.copy_buttons.values():
            button.set_sensitive(self.prepared.connection is not None)
        self.local_button.set_sensitive(self.source_report.mode == 'file' and self.local_confirm.get_active()
                                         and self.prepared.share.path is not None)
        self.status.set_text('Fiche ponctuelle ; aucun accès réel certifié. ' + self.prepared.connection_notice)

    def volume_inputs(self):
        if not self.is_current() or self.prepared is None or self.prepared.share.path is None:
            raise VolumeError('Le chemin du partage est inconnu ou la source n’est plus courante.')
        path, point = self.prepared.share.path, self.mountpoint.get_text()
        validate_volume_paths(path, point)
        return path, point

    def examine_demo(self, _button=None):
        self.invalidate()
        if self.source_report.mode != 'demo':
            return
        try:
            path, point = self.volume_inputs()
            self.volume = collect_volume(path, point, DemoVolumeProbe(VOLUME_SCENARIOS[self.volume_scenario.get_selected()], point))
        except VolumeError as error:
            self.status.set_text(str(error))
            return
        self.refresh()

    def examine_local(self, _button=None):
        self.invalidate()
        if self.source_report.mode != 'file' or not self.local_confirm.get_active():
            self.status.set_text('Confirmez que le dossier du fichier choisi appartient à cet ordinateur.')
            return
        try:
            path, point = self.volume_inputs()
        except VolumeError as error:
            self.status.set_text(str(error))
            return
        self.local_button.set_sensitive(False)
        self.status.set_text('Vérification de la source et constat du volume local en cours…')
        Thread(target=self.read_local, args=(self.generation, path, point), daemon=True).start()

    def read_local(self, generation, path, point):
        volume, error, stale = None, None, False
        try:
            if read_configuration(self.source_report.source).sha256 != self.source_report.sha256:
                stale = True
            else:
                volume = collect_volume(path, point, HostVolumeProbe())
                stale = read_configuration(self.source_report.source).sha256 != self.source_report.sha256
        except InspectionError:
            stale = True
        except (OSError, VolumeError):
            error = 'Le constat de volume est indisponible ; aucune absence n’est déduite.'
        GLib.idle_add(self.receive_volume, generation, volume, error, stale)

    def receive_volume(self, generation, volume, error=None, stale=False):
        if generation != self.generation or not self.is_current():
            return False
        self.source_stale = stale
        self.volume = None if stale or error else volume
        self.refresh()
        if error and not stale:
            self.status.set_text(error)
        return False

    def copy_address(self, client):
        if not self.is_current() or self.prepared is None or self.prepared.connection is None:
            self.refresh()
            return
        guide = next((guide for guide in self.prepared.connection.guides if guide.key == client), None)
        if guide is not None:
            self.get_clipboard().set(guide.address)
            self.status.set_text('Adresse copiée ; aucune connexion ouverte.')

    def on_close(self, *_args):
        self.active = False
        self.generation += 1
        self.volume, self.prepared = None, None
        return False
