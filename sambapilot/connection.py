"""Fiches de connexion calculées depuis un inventaire, sans accès réseau ou hôte."""

from dataclasses import asdict, dataclass
from ipaddress import IPv4Address
import re
from typing import Optional, Tuple
from urllib.parse import quote

from .inspection import InspectionReport
from .planning import PlanError, validate_name


class ConnectionError(ValueError):
    pass


@dataclass(frozen=True)
class ClientGuide:
    key: str
    title: str
    address: str
    steps: Tuple[str, ...]


@dataclass(frozen=True)
class ConnectionCard:
    schema_version: int
    mode: str
    source: str
    source_sha256: str
    read_at: Optional[str]
    server: str
    share: str
    guides: Tuple[ClientGuide, ...]
    notes: Tuple[str, ...]
    network_verified: Optional[bool] = None
    can_apply: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def validate_server(server: str) -> str:
    if not isinstance(server, str) or any(not char.isprintable() for char in server):
        raise ConnectionError("Le serveur doit être un nom DNS ou une IPv4, sans caractère de contrôle.")
    server = server.strip().lower()
    if not server or len(server) > 253:
        raise ConnectionError("Indiquez uniquement un nom DNS ou une IPv4, sans adresse smb://, chemin, compte ou mot de passe.")
    if re.fullmatch(r"[0-9.]+", server):
        try:
            return str(IPv4Address(server))
        except ValueError as error:
            raise ConnectionError("Adresse IPv4 invalide.") from error
    labels = (server[:-1] if server.endswith('.') else server).split('.')
    if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part in labels):
        raise ConnectionError("Nom DNS ou IPv4 uniquement ; URL, identifiants, port et IPv6 ne sont pas pris en charge par cette fiche.")
    return server


def prepare_connection(report: InspectionReport, share_name: str, server: str) -> ConnectionCard:
    if report.status != 'inspected' or report.mode not in {'demo', 'file'}:
        raise ConnectionError("Choisissez un inventaire de démonstration ou un fichier examiné sans blocage.")
    if not isinstance(share_name, str):
        raise ConnectionError("Choisissez un nom de partage dans l’inventaire.")
    matches = [share for share in report.shares if share.name.casefold() == share_name.casefold()]
    if len(matches) != 1:
        raise ConnectionError("Le partage doit être unique et présent dans l’inventaire courant.")
    share = matches[0]
    try:
        validate_name(share.name)
    except PlanError as error:
        raise ConnectionError("Ce nom de partage ne permet pas de construire une fiche portable : " + str(error)) from error
    if share.name.endswith('.'):
        raise ConnectionError("Les noms de partage terminés par un point ne sont pas pris en charge par cette fiche portable.")
    server = validate_server(server)
    uri = 'smb://' + server + '/' + quote(share.name, safe='')
    unc = '\\\\' + server + '\\' + share.name
    guides = (
        ClientGuide('windows', 'Windows', unc, (
            'Ouvrir l’Explorateur de fichiers.',
            'Coller l’adresse Windows dans la barre d’adresse, puis valider.',
            'Si une authentification est demandée, utiliser un compte autorisé sur le serveur.')),
        ClientGuide('macos', 'macOS', uri, (
            'Dans le Finder, choisir Aller → Se connecter au serveur (⌘K).',
            'Coller l’adresse SMB et demander la connexion.',
            'Utiliser un compte autorisé si le serveur demande une authentification.')),
        ClientGuide('linux', 'Linux', uri, (
            'Ouvrir un gestionnaire de fichiers prenant en charge SMB.',
            'Coller l’adresse SMB dans la barre d’emplacement ; dans GNOME Fichiers, utiliser aussi Autres emplacements → Connexion à un serveur.',
            'Utiliser un compte autorisé si demandé. La prise en charge SMB du gestionnaire doit déjà être disponible.')),
    )
    notes = [
        'Données fictives : le serveur saisi n’est pas contacté.' if report.mode == 'demo'
        else 'Déclaration du fichier choisi : le serveur saisi n’est pas contacté.',
        'Le nom ou l’IPv4 du serveur est fourni par vous ; il n’est pas déduit du chemin Linux du dossier.',
        'Aucune résolution DNS, authentification, connexion réseau, ouverture de port ou vérification de droits réalisée.',
        'Cette fiche contient le nom du serveur, du partage et la source ; aucun mot de passe n’est collecté.',
        'Lecture ponctuelle : la fiche n’est pas une surveillance de la configuration du serveur.',
    ]
    if share.browseable is False:
        notes.append('Le partage est déclaré masqué dans les listes ; cela ne prouve pas qu’une connexion directe est autorisée.')
    if share.read_only is True:
        notes.append('Lecture seule déclarée ; les droits effectifs du compte et des fichiers restent inconnus.')
    else:
        notes.append('Les droits effectifs de lecture et d’écriture restent inconnus, même si une écriture est déclarée.')
    if share.issues or share.unparsed_options or share.missing_fields or share.ambiguous_fields:
        notes.append('L’inventaire comporte des réglages incomplets, ambigus ou non interprétés ; cette adresse ne les résout pas.')
    return ConnectionCard(1, report.mode, report.source, report.sha256, report.read_at,
                          server, share.name, guides, tuple(notes))


def format_connection(card: ConnectionCard) -> str:
    def clean(value):
        return ''.join(char if char.isprintable() else '?' for char in value)
    lines = ['SambaPilot — Fiche de connexion',
             'DÉMONSTRATION — données fictives' if card.mode == 'demo' else 'Fichier choisi — accès non vérifié',
             'Partage : ' + clean(card.share), 'Serveur saisi : ' + card.server,
             'Source : ' + clean(card.source), 'Empreinte : ' + card.source_sha256,
             'Date de lecture : ' + (card.read_at or 'non disponible'), '']
    for guide in card.guides:
        lines.extend((guide.title, '  ' + guide.address))
        lines.extend('  ' + str(index) + '. ' + step for index, step in enumerate(guide.steps, 1))
        lines.append('')
    lines.extend('  - ' + note for note in card.notes)
    return '\n'.join(lines)
