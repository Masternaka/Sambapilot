"""Fiche GTK : génération et copie explicites, aucun lancement de client réseau."""

from gi.repository import Gtk

from .connection import ConnectionError, format_connection, prepare_connection


class ConnectionWindow(Gtk.Window):
    def __init__(self, owner, report, share_name):
        super().__init__(title='Préparer les adresses du partage', transient_for=owner, modal=True)
        self.set_destroy_with_parent(True)
        self.set_default_size(780, 620)
        self.owner = owner
        self.report = report
        self.share_name = share_name
        self.snapshot = owner.inspection_snapshot
        self.generation = owner.inspection_generation
        self.active = True
        self.card = None
        self.connect('close-request', self.on_close)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        title = Gtk.Label(label='Partage : ' + share_name, xalign=0, wrap=True, selectable=True)
        title.add_css_class('heading')
        content.append(title)
        content.append(Gtk.Label(label='Indiquez le nom ou l’IPv4 du serveur. Aucune connexion ne sera tentée. '
                                'Les adresses copiées contiennent le serveur et le partage.', xalign=0, wrap=True))
        self.server = Gtk.Entry(placeholder_text='Exemple : serveur.local ou 192.0.2.10')
        self.server.set_tooltip_text('Serveur explicitement choisi ; aucun compte ou mot de passe')
        self.server.connect('changed', self.invalidate)
        content.append(self.server)
        self.generate_button = Gtk.Button(label='Préparer les adresses', halign=Gtk.Align.START)
        self.generate_button.connect('clicked', self.generate)
        content.append(self.generate_button)
        self.status = Gtk.Label(label='Aucune adresse préparée.', xalign=0, wrap=True, selectable=True)
        content.append(self.status)
        self.output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True,
                                   wrap_mode=Gtk.WrapMode.WORD_CHAR)
        area = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        area.set_child(self.output)
        content.append(area)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.copy_buttons = {}
        for key, title in (('windows', 'Copier pour Windows'), ('macos', 'Copier SMB pour macOS/Linux')):
            button = Gtk.Button(label=title)
            button.set_sensitive(False)
            button.connect('clicked', lambda _button, client=key: self.copy_address(client))
            self.copy_buttons[key] = button
            actions.append(button)
        close = Gtk.Button(label='Fermer')
        close.connect('clicked', lambda _button: self.close())
        actions.append(close)
        content.append(actions)
        self.set_child(content)

    def is_current(self):
        if not self.active or self.generation != self.owner.inspection_generation:
            return False
        if self.report.mode == 'demo':
            return not self.owner.file_shares_mode
        return self.owner.file_shares_mode and self.snapshot is self.owner.inspection_snapshot

    def invalidate(self, *_args):
        self.card = None
        self.output.get_buffer().set_text('')
        for button in self.copy_buttons.values():
            button.set_sensitive(False)
        self.status.set_text('Aperçu effacé ; préparez de nouvelles adresses.')

    def generate(self, _button=None):
        self.invalidate()
        if not self.is_current():
            self.status.set_text('La source a changé. Fermez la fiche et choisissez le partage à nouveau.')
            return
        try:
            card = prepare_connection(self.report, self.share_name, self.server.get_text())
        except ConnectionError as error:
            self.status.set_text(str(error))
            return
        self.card = card
        self.output.get_buffer().set_text(format_connection(card))
        for button in self.copy_buttons.values():
            button.set_sensitive(True)
        self.status.set_text('Adresses préparées uniquement. Aucun accès au serveur vérifié.')

    def copy_address(self, client):
        if self.card is None or not self.is_current():
            self.invalidate()
            return
        guide = next((guide for guide in self.card.guides if guide.key == client), None)
        if guide is None:
            return
        self.get_clipboard().set(guide.address)
        self.status.set_text('Adresse copiée. Aucune connexion ouverte.')

    def on_close(self, *_args):
        self.active = False
        self.invalidate()
        return False
