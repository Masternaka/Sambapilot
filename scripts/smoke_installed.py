"""Vérifier le paquet déjà installé hors des sources, sans installation ni sonde hôte."""

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ICON_NAME = 'io.github.sambapilot.SambaPilot'
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def check_icons(package_root):
    """Refuser un paquet privé de ressources ou portant des PNG incohérents."""
    icons = []
    for size in ICON_SIZES:
        path = package_root / 'assets' / 'icons' / 'hicolor' / f'{size}x{size}' / 'apps' / (ICON_NAME + '.png')
        header = path.read_bytes()[:33]
        if len(header) != 33 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[8:16] != b'\x00\x00\x00\rIHDR':
            raise RuntimeError('Ressource PNG absente ou en-tête invalide : ' + str(path))
        width, height, depth, colour = struct.unpack('>IIBB', header[16:26])
        if (width, height, depth, colour) != (size, size, 8, 6):
            raise RuntimeError('Dimensions ou transparence PNG incorrectes : ' + str(path))
        icons.append(path)
    return tuple(icons)


def check_gtk(icons):
    """Essai natif explicite, uniquement avec GTK et un affichage déjà disponibles."""
    from sambapilot.gui import load_gtk
    Gtk = load_gtk()
    if not Gtk.init_check():
        raise RuntimeError('Le contrôle GTK exige une session graphique accessible.')
    from gi.repository import Gdk
    from sambapilot.gtk_app import SambaPilotApplication
    from sambapilot.troubleshooting import SYMPTOMS
    application = SambaPilotApplication()
    try:
        if not application.register(None):
            raise RuntimeError('Enregistrement de l’application GTK impossible.')
        application.activate()
        windows = application.get_windows()
        if len(windows) != 1:
            raise RuntimeError('La démonstration doit créer une fenêtre GTK unique.')
        window = windows[0]
        theme = Gtk.IconTheme.get_for_display(window.get_display())
        if Gtk.Window.get_default_icon_name() != ICON_NAME or not theme.has_icon(ICON_NAME):
            raise RuntimeError('L’icône du paquet installé n’est pas résolue par GTK.')
        for path in icons:
            texture = Gdk.Texture.new_from_filename(str(path))
            size = int(path.parent.parent.name.split('x')[0])
            if texture.get_width() != size or texture.get_height() != size:
                raise RuntimeError('Décodage natif PNG incorrect : ' + str(path))
        page = window.diagnostic_page
        for index, family in enumerate(('arch', 'debian', 'fedora')):
            page.distribution.set_selected(index)
            if page.source != 'demo' or page.report.environment.distribution_family != family:
                raise RuntimeError('Profil graphique installé incorrect.')
            for symptom_index, symptom in enumerate(SYMPTOMS):
                page.symptom.set_selected(symptom_index)
                buffer = page.help_output.get_buffer()
                text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
                if SYMPTOMS[symptom] not in text:
                    raise RuntimeError('Dépannage graphique installé incorrect.')
        for name in ('dashboard', 'installation', 'shares', 'access', 'prepare', 'configuration', 'firewall', 'maintenance'):
            if window.stack.get_child_by_name(name) is None:
                raise RuntimeError('Page GTK installée absente : ' + name)
        print('GTK installé : fenêtre et huit pages créées, trois profils fictifs, dépannage et huit PNG décodés ; icône résolue.')
    finally:
        for window in application.get_windows():
            window.invalidate_inspection_on_close()
            window.destroy()
        application.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gtk', action='store_true', help='Exiger le démarrage GTK et le décodage natif des icônes, sans installation.')
    args = parser.parse_args(argv)
    import sambapilot
    from sambapilot.demo import demo_configuration
    if ROOT in Path(sambapilot.__file__).resolve().parents:
        raise RuntimeError('Le test doit charger le paquet installé, pas les sources du dépôt.')
    if metadata.version('sambapilot') != sambapilot.__version__:
        raise RuntimeError('Versions du paquet installé et du module incohérentes.')
    icons = check_icons(Path(sambapilot.__file__).resolve().parent)
    print('Ressources installées : huit PNG avec dimensions et transparence conformes.')
    with tempfile.TemporaryDirectory(prefix='sambapilot-installed-check-') as directory:
        work = Path(directory)
        source = work / 'fixture.conf'
        source.write_text(demo_configuration(), encoding='utf-8')
        console_environment = dict(os.environ)
        console_environment.pop('PYTHONPATH', None)
        console_environment.pop('PYTHONHOME', None)
        console_environment['PYTHONDONTWRITEBYTECODE'] = '1'
        console = Path(sys.executable).parent / 'sambapilot'
        version = subprocess.run([str(console), '--version'], cwd=work, env=console_environment,
                                 capture_output=True, text=True, timeout=15, check=True).stdout.strip()
        if version != 'sambapilot ' + sambapilot.__version__:
            raise RuntimeError('Point d’entrée installé incohérent avec la version du module.')
        def command(*args):
            return subprocess.run([sys.executable, '-I', '-B', '-m', 'sambapilot', *args],
                                  cwd=work, capture_output=True, text=True, timeout=15, check=True).stdout
        diagnostic = json.loads(command('diagnostic', '--demo', '--json'))
        if diagnostic['mode'] != 'demo':
            raise RuntimeError('Le diagnostic installé doit rester en démonstration.')
        for family in ('arch', 'debian', 'fedora'):
            diagnostic = json.loads(command('diagnostic', '--demo', '--distribution', family, '--json'))
            if diagnostic['environment']['distribution_family'] != family or diagnostic['schema_version'] != 2:
                raise RuntimeError('Profil de distribution installé incorrect.')
            plan = json.loads(command('preparer-installation', '--demo', '--distribution', family, '--json'))
            if plan['can_apply'] is not False or plan['diagnostic']['environment']['distribution_family'] != family:
                raise RuntimeError('Plan de distribution installé incorrect.')
            help_report = json.loads(command('depannage', '--demo', '--distribution', family, '--symptom', 'readonly', '--json'))
            if help_report['can_apply'] is not False or help_report['mode'] != 'demo':
                raise RuntimeError('Dépannage installé incorrect.')
        json.loads(command('permissions', '--demo', '--json'))
        plan = json.loads(command('plan-partage', '--demo', '--action', 'remove', '--name', 'Medias', '--json'))
        if plan['can_apply'] is not False:
            raise RuntimeError('Le plan installé ne doit pas être applicable.')
        for args in (('preparer-installation', '--demo', '--json'),
                     ('plan-pare-feu', '--manager', 'ufw', '--interface', 'enp3s0', '--source', '192.168.1.0/24', '--json')):
            if json.loads(command(*args))['can_apply'] is not False:
                raise RuntimeError('La préparation installée doit rester descriptive.')
        preview = command('examiner-config', '--config', str(source), '--markdown')
        if not preview.startswith('# SambaPilot'):
            raise RuntimeError('Aperçu Markdown installé invalide.')
        output = work / 'report.md'
        command('examiner-config', '--config', str(source), '--export', str(output), '--confirm-export')
        if not output.is_file() or 'Famille' not in output.read_text(encoding='utf-8'):
            raise RuntimeError('Le rapport installé ne contient pas les déclarations attendues.')
        subprocess.run([sys.executable, '-I', '-B', '-m', 'sambapilot.backup_simulation', '--demo'],
                       cwd=work, capture_output=True, text=True, timeout=15, check=True)
    if args.gtk:
        check_gtk(icons)
    print('Paquet installé vérifié : versions, commandes fictives, aperçu/export et simulation de sauvegarde.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
