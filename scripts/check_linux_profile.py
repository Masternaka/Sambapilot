"""Contrôle CI des requêtes réelles de paquets déjà présents ; aucune installation."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sambapilot.diagnostic import parse_os_release
from sambapilot.distributions import PROFILES, identify_profile
from sambapilot.setup import HostSetupProbe


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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
