"""Contrôle CI des paquets et montages Linux ; métadonnées sur une fixture temporaire, sans installation."""

import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sambapilot.diagnostic import parse_os_release
from sambapilot.distributions import PROFILES, identify_profile
from sambapilot.setup import HostSetupProbe
from sambapilot.volume_system import HostVolumeProbe
from sambapilot.volumes import parse_mountinfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected', choices=tuple(PROFILES), required=True)
    args = parser.parse_args()
    probe = HostSetupProbe()
    if probe.system() != 'Linux':
        raise RuntimeError('Ce contrôle exige le conteneur Linux attendu.')
    content, error = probe.os_release()
    release = parse_os_release(content)
    profile = identify_profile(release.get('ID', ''), release.get('ID_LIKE', ''))
    if error or profile is None or profile.key != args.expected:
        raise RuntimeError('Distribution du conteneur différente du profil attendu.')
    packages = [probe.package(name, profile.key) for name in profile.packages]
    if any(package.status == 'unknown' for package in packages):
        raise RuntimeError('Une requête réelle de paquet est ambiguë ou a échoué.')
    tool_packages = [name for name, tools in profile.package_tools if 'testparm' in tools]
    if not any(package.name in tool_packages and package.status == 'installed' for package in packages):
        raise RuntimeError('Le paquet fournissant testparm doit déjà être installé par la CI.')
    print(profile.name + ' : ' + ', '.join(package.name + '=' + package.status for package in packages))
    volume = HostVolumeProbe()
    table, error = volume.mountinfo()
    if error or not parse_mountinfo(table):
        raise RuntimeError('La table mountinfo réelle du conteneur ne peut pas être analysée.')
    # Dossiers privés de travail, jamais un vrai point de montage à créer ou modifier.
    with tempfile.TemporaryDirectory(prefix='sambapilot-volume-ci-', dir='/tmp') as directory:
        root = Path(directory)
        folder = root / 'dossier'
        folder.mkdir()
        link = root / 'lien'
        link.symlink_to(folder, target_is_directory=True)
        if volume.directory(str(folder)).status != 'present':
            raise RuntimeError('Le dossier temporaire doit être constaté sans lire son contenu.')
        if volume.directory(str(root / 'absent')).status != 'missing':
            raise RuntimeError('L’absence du dossier temporaire doit être distinguée d’une erreur.')
        if volume.directory(str(link)).status != 'not-directory':
            raise RuntimeError('Un lien symbolique ne doit pas être suivi par la sonde de volume.')
    print('Mountinfo Linux et métadonnées : dossier temporaire présent, absent et lien refusé ; aucun montage effectué.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
