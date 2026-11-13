"""Fiche par partage : déclarations, pistes et observations fournies, sans sonde implicite."""

from dataclasses import asdict, dataclass
from typing import Optional, Tuple

from .connection import ConnectionCard, ConnectionError, format_connection, prepare_connection
from .inspection import DeclaredShare, InspectionReport
from .presentation import declared_share_details, declared_share_guidance
from .troubleshooting import Finding, SYMPTOMS, symptom_findings
from .volumes import VolumeReport, format_volume


class ShareDiagnosticError(ValueError):
    pass


@dataclass(frozen=True)
class ShareDiagnostic:
    schema_version: int
    mode: str
    source: str
    source_sha256: str
    read_at: Optional[str]
    share: DeclaredShare
    symptom: str
    findings: Tuple[Finding, ...]
    connection: Optional[ConnectionCard]
    connection_notice: str
    volume: Optional[VolumeReport]
    notes: Tuple[str, ...]
    effective_read: Optional[bool] = None
    effective_write: Optional[bool] = None
    network_verified: Optional[bool] = None
    can_apply: bool = False

    def to_dict(self):
        return asdict(self)


def prepare_share_diagnostic(report: InspectionReport, name: str, symptom: str = 'invisible',
                             server: Optional[str] = None, volume: Optional[VolumeReport] = None) -> ShareDiagnostic:
    if report.status != 'inspected' or report.mode not in {'demo', 'file'}:
        raise ShareDiagnosticError('Choisissez un inventaire fictif ou un fichier examiné sans blocage.')
    matches = [share for share in report.shares if isinstance(name, str) and share.name.casefold() == name.casefold()]
    if len(matches) != 1:
        raise ShareDiagnosticError('Le partage doit être unique et présent dans l’inventaire courant.')
    if symptom not in SYMPTOMS:
        raise ShareDiagnosticError('Symptôme inconnu.')
    share = matches[0]
    if volume is not None:
        if share.path is None or volume.path != share.path:
            raise ShareDiagnosticError('Le constat de volume doit porter sur le chemin déclaré de ce partage.')
        if volume.mode != ('demo' if report.mode == 'demo' else 'live'):
            raise ShareDiagnosticError('Ne pas mélanger les volumes fictifs et les observations locales du fichier choisi.')
    findings = []
    if share.issues or share.unparsed_options or share.missing_fields or share.ambiguous_fields:
        findings.append(Finding('declaration', 'attention', 'Déclaration incomplète, ambiguë ou contenant des options non interprétées.',
                                'Examiner les incertitudes de ce partage ; aucune valeur héritée ou implicite n’est supposée.'))
    else:
        findings.append(Finding('declaration', 'declared', 'Réglages locaux du partage inventoriés.',
                                'Un inventaire compris ne remplace ni testparm ni une vérification d’accès depuis un client.'))
    if symptom == 'invisible':
        if share.browseable is False:
            status, observation = 'attention', 'Le partage est déclaré masqué dans la liste.'
        elif share.browseable is True:
            status, observation = 'declared', 'Le partage est déclaré visible ; sa découverte réseau reste non vérifiée.'
        else:
            status, observation = 'unknown', 'La visibilité effective n’est pas établie par cette déclaration.'
        findings.append(Finding('visibility', status, observation, 'Préparer une adresse directe si le serveur est connu ; cela ne certifie aucun accès.'))
    if symptom == 'readonly':
        if share.read_only is True:
            status, observation = 'attention', 'La déclaration demande une lecture seule.'
        elif share.read_only is False:
            status, observation = 'declared', 'La déclaration permet l’écriture ; les permissions effectives restent inconnues.'
        else:
            status, observation = 'unknown', 'Le choix de lecture seule n’est pas déterminé dans cette déclaration.'
        findings.append(Finding('declared-write', status, observation, 'Comparer ce réglage aux droits du compte, aux ACL et au volume avant de proposer une correction.'))
    findings.extend(symptom_findings(symptom))
    if volume is not None:
        attention = (volume.expected_mounted is False or volume.on_expected_mount is False
                     or volume.directory_status in {'missing', 'not-directory'} or volume.read_only is True)
        findings.append(Finding('volume', 'attention' if attention else 'unknown',
                                'Un constat de volume est joint, limité aux exemples.' if volume.mode == 'demo'
                                else 'Un constat du volume de cet ordinateur est joint ; il ne décrit pas automatiquement le serveur distant.',
                                'Examiner le point attendu, le dossier et les dates ; l’identité du disque et les droits Samba restent inconnus.'))
    connection = None
    connection_notice = 'Indiquez le serveur pour préparer les adresses ; aucune adresse n’est déduite du fichier.'
    if server is not None:
        try:
            connection = prepare_connection(report, share.name, server)
        except ConnectionError as error:
            connection_notice = str(error)
        else:
            connection_notice = 'Adresses préparées, sans résolution DNS ni connexion.'
    return ShareDiagnostic(1, report.mode, report.source, report.sha256, report.read_at, share, symptom,
                           tuple(findings), connection, connection_notice, volume, (
                               'Réglages déclarés et observations locales restent distincts ; les droits effectifs et l’accès réseau sont inconnus.',
                               'Un fichier choisi peut provenir d’un autre serveur ; son chemin déclaré n’est pas automatiquement celui de cet ordinateur.',
                               'Aucune sonde supplémentaire n’est lancée par la préparation de cette fiche.',
                               'Chemins, noms de comptes et groupes déclarés peuvent figurer dans cette fiche ; aucun mot de passe demandé.',
                               'Lecture ponctuelle : recharger le fichier pour actualiser sa déclaration. Aucun changement appliqué.',
                           ))


def format_share_diagnostic(report: ShareDiagnostic) -> str:
    def clean(value):
        return ''.join(char if char.isprintable() else '?' for char in str(value))
    lines = ['SambaPilot — Diagnostic du partage',
             'DÉMONSTRATION — données fictives' if report.mode == 'demo' else 'Fichier choisi — droits et accès non vérifiés',
             'Partage : ' + clean(report.share.name), 'Source : ' + clean(report.source),
             'Empreinte : ' + report.source_sha256, 'Date de lecture : ' + (report.read_at or 'non disponible'),
             '', 'Réglages déclarés', declared_share_details(report.share), declared_share_guidance(report.share),
             '', 'Dépannage : ' + SYMPTOMS[report.symptom]]
    states = {'declared': 'déclaré', 'attention': 'à examiner', 'unknown': 'non vérifié', 'observed': 'constaté'}
    for finding in report.findings:
        lines.extend(('[' + states[finding.status] + '] ' + finding.observation, '  Suite : ' + finding.next_step))
    lines.extend(('', 'Connexion', report.connection_notice))
    if report.connection is not None:
        lines.append(format_connection(report.connection))
    lines.extend(('', 'Dossier et volume'))
    lines.append(format_volume(report.volume) if report.volume is not None else
                 'Non examinés. Fournir le point attendu puis demander explicitement une simulation ou un constat local.')
    lines.extend(('', *report.notes))
    # Les détails et chemins sont du texte, jamais une séquence de contrôle terminal.
    return '\n'.join(''.join(char if char.isprintable() or char == '\n' else '?' for char in line) for line in lines)
