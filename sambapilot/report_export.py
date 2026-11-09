"""Rapport Markdown d'un inventaire déjà lu, et enregistrement explicite sans écrasement."""

from dataclasses import dataclass
from datetime import datetime, timezone
import html
import os
from pathlib import Path
import re
import tempfile
from typing import Optional

from . import __version__
from .inspection import InspectionReport
from .presentation import declared_share_details, declared_share_guidance


PERSONAL_DATA_NOTICE = (
    "Ce rapport contient la source, les chemins et les identifiants déclarés. "
    "Vérifiez son contenu avant de l’enregistrer ou de le partager. "
    "Le fichier brut, les candidats et les valeurs des options non interprétées sont exclus."
)


class ReportExportError(ValueError):
    pass


@dataclass(frozen=True)
class MarkdownReport:
    markdown: str
    source_sha256: str


def escape_markdown(value: str) -> str:
    text = html.escape("".join(char if char.isprintable() else " " for char in value), quote=False)
    return re.sub(r'([\\`*_{}\[\]()#!|~])', r'\\\1', text)


def prepare_report(report: InspectionReport, created_at: Optional[datetime] = None) -> MarkdownReport:
    """Ne relit pas la source, ne lance aucune sonde et ne crée aucun fichier."""
    if report.mode not in ("file", "demo", "provided"):
        raise ReportExportError("Type de rapport non pris en charge pour cet export.")
    now = created_at if created_at is not None else datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ReportExportError("La date de création doit préciser son fuseau horaire.")
    modes = {"file": "Fichier choisi", "demo": "Démonstration — données fictives", "provided": "Contenu fourni"}
    lines = ["# SambaPilot — Rapport de configuration", "", PERSONAL_DATA_NOTICE, "",
             "## Source et dates", "",
             "- Version de SambaPilot : " + escape_markdown(__version__),
             "- Source : " + escape_markdown(report.source),
             "- Mode : " + modes[report.mode],
             "- Date de lecture (UTC) : " + escape_markdown(report.read_at or "Inconnue / non enregistrée"),
             "- Date de création du rapport (UTC) : " + now.astimezone(timezone.utc).isoformat(timespec="seconds"),
             "- Empreinte SHA-256 de la source lue : " + escape_markdown(report.sha256),
             "", "## Résultat de l’examen", ""]
    if report.status == "inspected":
        lines.append(str(len(report.shares)) + " déclaration(s) locale(s) ordinaire(s) inventoriée(s).")
        if not report.shares:
            lines.append("Cela ne prouve pas l’absence de partages sur le serveur.")
        for share in report.shares:
            lines += ["", "### " + escape_markdown(share.name), ""]
            lines += ["- " + escape_markdown(line) for line in declared_share_details(share).splitlines()]
            lines += ["", "Vérifications à effectuer :", ""]
            lines += ["- " + escape_markdown(line) for line in declared_share_guidance(share).splitlines()]
    else:
        lines.append("Analyse bloquée ou non concluante : aucun inventaire fiable présenté. "
                     "Cela ne signifie pas qu’il n’existe aucun partage.")
    if report.special_sections:
        lines += ["", "Sections spéciales non développées : " + escape_markdown(", ".join(report.special_sections))]
    if report.issues:
        lines += ["", "Points signalés par l’examen :", ""]
        lines += ["- " + escape_markdown(issue) for issue in report.issues]
    lines += ["", "## Limites et suites", "",
              "- Lecture ponctuelle : ce document décrit les données lues à la date indiquée ; la source n’est pas surveillée.",
              "- Les valeurs globales, les valeurs par défaut et les inclusions ne sont pas résolues.",
              "- Les comptes, les permissions Linux, les ACL et les accès réseau ne sont pas vérifiés.",
              "- Aucun contrôle testparm ni aucune sonde supplémentaire n’est lancé par cet export.",
              "- Le rapport inclut tout l’inventaire, indépendamment des filtres affichés dans la fenêtre.",
              "- Relire la source et contrôler les conditions réelles avant toute intervention.",
              "- Ce document n’est ni une sauvegarde complète de smb.conf ni un plan applicable.", ""]
    return MarkdownReport("\n".join(lines), report.sha256)


def save_report(report: MarkdownReport, filename: str) -> Path:
    """Publier un fichier UTF-8 complet en 0600, sans remplacer une destination existante."""
    destination = Path(filename).absolute()
    if destination.suffix.lower() != ".md":
        raise ReportExportError("Choisissez un nouveau fichier avec l’extension .md.")
    temporary = None
    try:
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".sambapilot-report-",
                                             suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                stream.write(report.markdown.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            # Un lien vers le fichier complet publie sans remplacer un fichier, lien ou dossier existant.
            os.link(temporary, destination)
        finally:
            if temporary is not None:
                os.unlink(temporary)
    except FileExistsError as error:
        raise ReportExportError("La destination existe déjà. Aucun écrasement ; choisissez un autre nom.") from error
    except OSError as error:
        raise ReportExportError("Échec de préparation, d’enregistrement ou de nettoyage du rapport. "
                                "Aucun fichier existant n’a été remplacé ; vérifiez la destination.") from error
    return destination
