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
    from sambapilot.gtk_app import SambaPilotApplication, SambaPilotWindow
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
        window.open_connection('Famille')
        try:
            sheet = window.connection_window
            if sheet is None:
                raise RuntimeError('Fiche de connexion graphique installée absente.')
            sheet.server.set_text('serveur.example.invalid')
            sheet.generate()
            if sheet.card is None or sheet.card.guides[1].address != 'smb://serveur.example.invalid/Famille':
                raise RuntimeError('Adresse de connexion graphique installée incorrecte.')
            sheet.server.set_text('autre.example.invalid')
            if sheet.card is not None or sheet.copy_buttons['macos'].get_sensitive():
                raise RuntimeError('La fiche de connexion doit être invalidée après modification.')
        finally:
            window.invalidate_connection()
        window.open_share_diagnostic('Famille')
        try:
            sheet = window.share_diagnostic_window
            if sheet is None or sheet.prepared.connection is not None or sheet.prepared.volume is not None:
                raise RuntimeError('Le diagnostic de partage installé ne doit pas lancer de contrôle implicite.')
            sheet.server.set_text('serveur.example.invalid')
            sheet.mountpoint.set_text('/srv/partages')
            sheet.volume_scenario.set_selected(1)
            sheet.examine_demo()
            if (sheet.prepared.connection is None or sheet.prepared.volume.expected_mounted is not False
                    or sheet.prepared.effective_write is not None):
                raise RuntimeError('Diagnostic de partage graphique installé incorrect.')
            sheet.server.set_text('autre.example.invalid')
            if sheet.prepared.volume is not None:
                raise RuntimeError('Le constat joint doit être invalidé après modification du formulaire.')
        finally:
            window.invalidate_connection()
        window.open_share_plan('create')
        window.share_profile.set_selected(3)
        window.fill_share_profile()
        if (window.plan_name.get_text() != 'Mediatheque' or window.plan_users.get_text()
                or window.plan_groups.get_text() or window.plan_session.current is not None):
            raise RuntimeError('Préremplissage graphique du profil incorrect.')
        window.plan_groups.set_text('famille')
        window.preview_share_plan(None)
        if window.plan_session.current is None or window.plan_session.current.can_apply:
            raise RuntimeError('Le profil graphique doit produire uniquement un aperçu après choix des identités.')
        volume_page = window.volume_page
        volume_page.scenario.set_selected(1)
        if volume_page.report is None or volume_page.report.expected_mounted is not False:
            raise RuntimeError('Le scénario installé de volume absent est incorrect.')
        volume_page.path.set_text('/mnt/medias/autre')
        if volume_page.report is not None:
            raise RuntimeError('Le constat de volume doit être invalidé après un changement de chemin.')
        print('GTK installé : fenêtre et huit pages créées, trois profils fictifs, dépannage et huit PNG décodés ; icône résolue.')
        print('Fiche de connexion installée : génération fictive et invalidation contrôlées, sans copie ni accès réseau.')
        print('Profil de partage installé : préremplissage sans identité, puis aperçu fictif après saisie explicite.')
        print('Examen du volume installé : exemple de montage absent et invalidation, sans consultation locale.')
        print('Diagnostic par partage installé : déclarations, adresses et volume fictif liés, sans consultation locale.')
    finally:
        for window in application.get_windows():
            if isinstance(window, SambaPilotWindow):
                window.invalidate_inspection_on_close()
            window.destroy()
        application.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gtk', action='store_true', help='Exiger le démarrage GTK et le décodage natif des icônes, sans installation.')
    options = parser.parse_args(argv)
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
        share_report = json.loads(command('diagnostic-partage', '--demo', '--share', 'Famille',
                                           '--server', 'serveur.example.invalid', '--demo-volume', 'unmounted',
                                           '--mountpoint', '/srv/partages', '--json'))
        if (share_report['can_apply'] is not False or share_report['effective_write'] is not None
                or share_report['share']['name'] != 'Famille' or share_report['volume']['expected_mounted'] is not False):
            raise RuntimeError('Diagnostic de partage installé incorrect.')
        volume_report = json.loads(command('examiner-volume', '--demo', 'unmounted', '--path', '/mnt/medias/films',
                                           '--mountpoint', '/mnt/medias', '--json'))
        if volume_report['expected_mounted'] is not False or volume_report['can_apply'] is not False:
            raise RuntimeError('Examen de volume installé incorrect.')
        for profile_key in ('personal', 'family', 'media'):
            profile_plan = json.loads(command('plan-partage', '--demo', '--action', 'create',
                                               '--profile', profile_key, '--user', 'alex', '--json'))
            if profile_plan['can_apply'] is not False or profile_plan['profile'] != profile_key:
                raise RuntimeError('Profil de partage installé incorrect.')
        connection = json.loads(command('fiche-connexion', '--demo', '--share', 'Famille',
                                         '--server', 'serveur.example.invalid', '--json'))
        if (connection['can_apply'] is not False or connection['network_verified'] is not None
                or connection['guides'][1]['address'] != 'smb://serveur.example.invalid/Famille'):
            raise RuntimeError('Fiche de connexion installée incorrecte.')
        plan = json.loads(command('plan-partage', '--demo', '--action', 'remove', '--name', 'Medias', '--json'))
        if plan['can_apply'] is not False:
            raise RuntimeError('Le plan installé ne doit pas être applicable.')
        for command_args in (('preparer-installation', '--demo', '--json'),
                     ('plan-pare-feu', '--manager', 'ufw', '--interface', 'enp3s0', '--source', '192.168.1.0/24', '--json')):
            if json.loads(command(*command_args))['can_apply'] is not False:
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
    if options.gtk:
        check_gtk(icons)
    print('Paquet installé vérifié : versions, commandes fictives, aperçu/export et simulation de sauvegarde.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
