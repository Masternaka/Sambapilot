"""Constat de montage : moteur et exemples sans commande système ni lecture implicite."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import PurePosixPath
import re
from typing import Optional, Tuple


MAX_MOUNTINFO_BYTES = 1024 * 1024
VOLUME_SCENARIOS = ('mounted', 'unmounted', 'readonly', 'missing-path', 'unknown')
LOCAL_FILESYSTEMS = {'ext2', 'ext3', 'ext4', 'btrfs', 'xfs', 'tmpfs', 'overlay', 'vfat', 'exfat', 'ntfs3', 'f2fs'}


class VolumeError(ValueError):
    pass


@dataclass(frozen=True)
class MountEntry:
    identifier: int
    point: str
    filesystem: str
    device: str
    read_only: Optional[bool]


@dataclass(frozen=True)
class DirectoryObservation:
    status: str
    device: Optional[str] = None


@dataclass(frozen=True)
class VolumeReport:
    schema_version: int
    mode: str
    path: str
    expected_mount: str
    expected_mounted: Optional[bool]
    actual_mount: Optional[str]
    filesystem: Optional[str]
    read_only: Optional[bool]
    directory_status: str
    on_expected_mount: Optional[bool]
    observed_at: str
    basis_sha256: Optional[str]
    notes: Tuple[str, ...]
    can_apply: bool = False

    def to_dict(self):
        return asdict(self)


def validate_volume_paths(path: str, expected_mount: str) -> None:
    if expected_mount == '/':
        raise VolumeError('Choisir le point de montage du volume attendu, distinct de la racine /.')
    for value in (path, expected_mount):
        if (not isinstance(value, str) or not value or len(value) > 4096 or not value.startswith('/') or value.startswith('//')
                or value != value.strip() or '\\' in value or '%' in value
                or any(not char.isprintable() for char in value)
                or any(part in {'.', '..', ''} for part in value.split('/')[1:])):
            raise VolumeError('Choisir des chemins Linux absolus simples, sans contrôle, variable, lien supposé ou traversée ; pas de barre finale.')
    if PurePosixPath(expected_mount) not in (PurePosixPath(path), *PurePosixPath(path).parents):
        raise VolumeError('Le dossier doit se trouver dans le point de montage attendu.')


def _decode_point(raw: str) -> str:
    if re.search(r'\\(?!040|011|012|134)', raw):
        raise VolumeError('Échappement mountinfo non reconnu.')
    return re.sub(r'\\(040|011|012|134)', lambda match: chr(int(match.group(1), 8)), raw)


def parse_mountinfo(content: str) -> Tuple[MountEntry, ...]:
    if not content.strip() or len(content.encode('utf-8')) > MAX_MOUNTINFO_BYTES:
        raise VolumeError('Table des montages vide ou trop volumineuse.')
    entries = []
    identifiers = set()
    for line in content.splitlines():
        before, separator, after = line.partition(' - ')
        fields, tail = before.split(), after.split()
        if (not separator or len(fields) < 6 or len(tail) != 3 or not fields[0].isdigit()
                or not fields[1].isdigit() or not re.fullmatch(r'[0-9]+:[0-9]+', fields[2])
                or not re.fullmatch(r'[A-Za-z0-9_.-]+', tail[0])):
            raise VolumeError('Table des montages incomplète ou non reconnue.')
        point = _decode_point(fields[4])
        if (not point.startswith('/') or point.startswith('//') or str(PurePosixPath(point)) != point
                or any(part in {'.', '..'} for part in point.split('/'))):
            raise VolumeError('Point de montage non reconnu.')
        identifier = int(fields[0])
        if identifier in identifiers:
            raise VolumeError('Identifiants de montage répétés.')
        identifiers.add(identifier)
        mount_options, super_options = set(fields[5].split(',')), set(tail[2].split(','))
        if any({'ro', 'rw'} <= options for options in (mount_options, super_options)):
            raise VolumeError('Options de montage contradictoires.')
        read_only = True if 'ro' in mount_options | super_options else False if 'rw' in mount_options and 'rw' in super_options else None
        # Les noms de périphérique et sources réseau peuvent contenir des secrets : ne pas les conserver.
        entries.append(MountEntry(identifier, point, tail[0], fields[2], read_only))
    return tuple(entries)


def _covers(point: str, path: str) -> bool:
    return PurePosixPath(point) in (PurePosixPath(path), *PurePosixPath(path).parents)


def collect_volume(path: str, expected_mount: str, probe) -> VolumeReport:
    validate_volume_paths(path, expected_mount)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    notes = [
        'Constat ponctuel : aucun montage, démontage, dossier créé, partage activé ou fichier de configuration modifié.',
        'Les droits Samba, permissions effectives, ACL, règles de sécurité et accès réseau ne sont pas vérifiés.',
        'Un montage présent ne certifie pas l’identité du disque attendu : UUID et fstab ne sont pas consultés.',
        'Les chemins du dossier et du point de montage figurent dans ce rapport.',
    ]

    def report(expected=None, actual=None, directory='unknown', on_expected=None, basis=None):
        return VolumeReport(1, probe.mode, path, expected_mount, expected,
                            actual.point if actual else None, actual.filesystem if actual else None,
                            actual.read_only if actual else None, directory, on_expected,
                            now, basis, tuple(notes))

    if probe.system() != 'Linux':
        notes.append('Constat local réservé à Linux ; aucune autre sonde lancée.')
        return report()
    content, error = probe.mountinfo()
    if error:
        notes.append('Table des montages inaccessible ; aucune absence déduite.')
        return report()
    try:
        entries = parse_mountinfo(content)
    except VolumeError:
        notes.append('Table des montages non concluante ; aucune absence déduite.')
        return report()
    basis = hashlib.sha256(content.encode('utf-8')).hexdigest()
    covering = [entry for entry in entries if _covers(entry.point, path)]
    expected = [entry for entry in entries if entry.point == expected_mount]
    # Les empilements et leurs racines masquées nécessitent une analyse dédiée.
    if len({entry.point for entry in covering}) != len(covering) or not covering:
        notes.append('Montages empilés ou couverture indéterminée ; examen manuel requis.')
        return report(basis=basis)
    actual = max(covering, key=lambda entry: len(PurePosixPath(entry.point).parts))
    if not expected:
        notes.append('Point attendu absent de la table ; le dossier pourrait relever du volume parent. Aucune inspection du dossier effectuée.')
        return report(False, actual, 'not-checked', False, basis)
    if actual.point != expected_mount:
        notes.append('Un montage imbriqué couvre le dossier ; il ne correspond pas au point attendu. Dossier non inspecté.')
        return report(True, actual, 'not-checked', False, basis)
    if any(entry.filesystem not in LOCAL_FILESYSTEMS for entry in covering):
        notes.append('Système de fichiers automatique, distant ou hors périmètre ; aucune consultation du dossier pour éviter un automontage ou un accès réseau.')
        return report(True, actual, 'not-checked', None, basis)
    observation = probe.directory(path)
    following, error = probe.mountinfo()
    if error or following != content:
        notes.append('La table a changé ou ne peut plus être relue ; observations abandonnées. Refaire le constat.')
        return report()
    if observation.status == 'present' and observation.device != actual.device:
        notes.append('Le périphérique du dossier ne correspond pas au constat de montage ; résultat indéterminé.')
        return report(True, actual, 'unknown', None, basis)
    if actual.read_only:
        notes.append('Le montage est déclaré en lecture seule ; aucune écriture de test effectuée.')
    if observation.status == 'present':
        notes.append('Dossier présent sur le montage constaté ; cela ne prouve pas les droits d’accès d’un utilisateur.')
    else:
        notes.append('Dossier absent ou non vérifiable ; aucune création automatique proposée.')
    return report(True, actual, observation.status, True if observation.status == 'present' else None, basis)


class DemoVolumeProbe:
    mode = 'demo'

    def __init__(self, scenario: str, expected_mount: str):
        if scenario not in VOLUME_SCENARIOS:
            raise VolumeError('Scénario de volume inconnu.')
        self.scenario, self.expected_mount = scenario, expected_mount

    def system(self):
        return 'Linux'

    def mountinfo(self):
        if self.scenario == 'unknown':
            return '', 'fictif'
        root = '1 0 8:1 / / rw - ext4 /dev/fiction rw\n'
        if self.scenario == 'unmounted':
            return root, None
        point = self.expected_mount.replace('\\', '\\134').replace(' ', '\\040')
        flags = 'ro' if self.scenario == 'readonly' else 'rw'
        return root + f'2 1 8:2 / {point} {flags} - ext4 /dev/fiction2 {flags}\n', None

    def directory(self, _path):
        return DirectoryObservation('missing' if self.scenario == 'missing-path' else 'present', '8:2')


def format_volume(report: VolumeReport) -> str:
    def clean(value):
        return ''.join(char if char.isprintable() else '?' for char in str(value))
    def state(value):
        return 'oui' if value is True else 'non' if value is False else 'inconnu'
    directories = {'present': 'présent', 'missing': 'absent', 'not-directory': 'composant non répertoire ou lien refusé',
                   'not-checked': 'non consulté', 'unknown': 'inconnu'}
    lines = ['SambaPilot — Examen du volume',
             'DÉMONSTRATION — données fictives' if report.mode == 'demo' else 'Constat local en lecture seule',
             'Dossier : ' + clean(report.path), 'Point attendu : ' + clean(report.expected_mount),
             'Point attendu monté : ' + state(report.expected_mounted),
             'Montage couvrant le dossier : ' + clean(report.actual_mount or 'inconnu'),
             'Système de fichiers : ' + clean(report.filesystem or 'inconnu'),
             'Montage en lecture seule : ' + state(report.read_only),
             'Dossier : ' + directories[report.directory_status],
             'Dossier constaté sur le point attendu : ' + state(report.on_expected_mount),
             'Date du constat : ' + report.observed_at, 'Empreinte de la table : ' + (report.basis_sha256 or 'non disponible'), '']
    return '\n'.join(lines + ['- ' + note for note in report.notes])
