"""Vérifier le paquet déjà installé hors des sources, sans installation ni sonde hôte."""

from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    import sambapilot
    from sambapilot.demo import demo_configuration
    if ROOT in Path(sambapilot.__file__).resolve().parents:
        raise RuntimeError('Le test doit charger le paquet installé, pas les sources du dépôt.')
    if metadata.version('sambapilot') != sambapilot.__version__:
        raise RuntimeError('Versions du paquet installé et du module incohérentes.')
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
    print('Paquet installé vérifié : versions, commandes fictives, aperçu/export et simulation de sauvegarde.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
