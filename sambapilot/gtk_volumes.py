"""Examen ponctuel d'un volume : sources explicites et retours asynchrones invalidables."""

from threading import Thread
from gi.repository import GLib, Gtk

from .volumes import DemoVolumeProbe, VOLUME_SCENARIOS, VolumeError, collect_volume, format_volume
from .volume_system import HostVolumeProbe


class VolumePage(Gtk.Box):
    def __init__(self, source_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(self, 'set_margin_' + side)(24)
        self.source_changed = source_changed
        self.source, self.generation, self.report = 'demo', 0, None
        title = Gtk.Label(label='Examiner le volume d’un dossier', xalign=0)
        title.add_css_class('title-1')
        self.append(title)
        self.append(Gtk.Label(label='Un dossier existant ne prouve pas qu’un disque est monté. '
                              'Choisissez le point attendu ; aucun montage ou partage ne sera activé.', xalign=0, wrap=True))
        self.path = Gtk.Entry(text='/mnt/medias/films')
        self.mountpoint = Gtk.Entry(text='/mnt/medias')
        for caption, entry in (('Dossier à examiner', self.path), ('Point de montage attendu', self.mountpoint)):
            label = Gtk.Label(label=caption, xalign=0)
            label.set_mnemonic_widget(entry)
            self.append(label)
            self.append(entry)
        self.scenario = Gtk.DropDown.new_from_strings(['Monté · exemple', 'Non monté · exemple', 'Lecture seule · exemple',
                                                      'Dossier absent · exemple', 'État inconnu · exemple'])
        self.scenario.set_tooltip_text('Scénario fictif de montage ; aucune lecture locale')
        self.append(self.scenario)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        demo = Gtk.Button(label='Afficher l’exemple')
        demo.connect('clicked', self.use_demo)
        self.local = Gtk.Button(label='Examiner ces chemins localement (lecture seule)')
        self.local.connect('clicked', self.examine_local)
        actions.append(demo)
        actions.append(self.local)
        self.append(actions)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.append(self.status)
        self.output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        area = Gtk.ScrolledWindow(hexpand=True, vexpand=True, min_content_height=350)
        area.set_child(self.output)
        self.append(area)
        self.show_report(collect_volume(self.path.get_text(), self.mountpoint.get_text(),
                                       DemoVolumeProbe('mounted', self.mountpoint.get_text())))
        self.path.connect('changed', self.invalidate)
        self.mountpoint.connect('changed', self.invalidate)
        self.scenario.connect('notify::selected', self.use_demo)

    def invalidate(self, *_args):
        self.generation += 1
        self.report = None
        self.source = 'none'
        self.output.get_buffer().set_text('')
        self.local.set_sensitive(True)
        self.status.set_text('Constat effacé. Choisissez un exemple ou demandez une nouvelle lecture locale.')
        self.source_changed()

    def show_report(self, report):
        self.report = report
        self.output.get_buffer().set_text(format_volume(report))
        self.status.set_text(('Exemple fictif' if report.mode == 'demo' else 'Constat local')
                             + ' · ' + report.observed_at + ' · Aucun changement appliqué.')

    def use_demo(self, *_args):
        self.invalidate()
        self.source = 'demo'
        try:
            scenario = VOLUME_SCENARIOS[self.scenario.get_selected()]
            report = collect_volume(self.path.get_text(), self.mountpoint.get_text(),
                                    DemoVolumeProbe(scenario, self.mountpoint.get_text()))
        except VolumeError as error:
            self.status.set_text(str(error))
        else:
            self.show_report(report)
        self.source_changed()

    def examine_local(self, _button=None):
        from .volumes import validate_volume_paths
        self.invalidate()
        path, point = self.path.get_text(), self.mountpoint.get_text()
        try:
            validate_volume_paths(path, point)
        except VolumeError as error:
            self.status.set_text(str(error))
            return
        self.source = 'live'
        self.local.set_sensitive(False)
        self.status.set_text('Lecture de la table et des métadonnées des chemins choisis…')
        self.source_changed()
        Thread(target=self.read_local, args=(self.generation, path, point), daemon=True).start()

    def read_local(self, generation, path, point):
        try:
            report = collect_volume(path, point, HostVolumeProbe())
        except (OSError, VolumeError):
            report = None
        GLib.idle_add(self.receive_report, generation, report)

    def receive_report(self, generation, report):
        if generation != self.generation:
            return False
        self.local.set_sensitive(True)
        if report is None:
            self.status.set_text('Constat interrompu ; état du volume inconnu.')
        else:
            self.show_report(report)
        return False

    def close(self):
        self.generation += 1
