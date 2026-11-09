"""Inventaire des déclarations locales d'un fichier choisi, sans effet système.

Aucune inclusion n'est suivie et aucune permission effective n'est déduite.
"""

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Optional, Tuple

from .planning import IDENTITY, PlanError, scan_sections


MAX_CONFIG_BYTES = 1024 * 1024
ALIASES = {"writable": "read only", "writeable": "read only", "write ok": "read only",
           "browsable": "browseable", "public": "guest ok"}
INVERTED = {"writable", "writeable", "write ok"}
KNOWN = {"path", "read only", "browseable", "guest ok", "valid users", "comment"}


class InspectionError(ValueError):
    pass


@dataclass(frozen=True)
class ConfigurationSnapshot:
    source: str
    content: str
    sha256: str

    def inspect(self) -> "InspectionReport":
        return inspect_content(self.content, self.source, "file", self.sha256)


@dataclass(frozen=True)
class DeclaredShare:
    name: str
    path: Optional[str]
    read_only: Optional[bool]
    browseable: Optional[bool]
    guest_ok: Optional[bool]
    access_list_status: str
    users: Tuple[str, ...]
    unix_groups: Tuple[str, ...]
    unresolved_principals: Tuple[str, ...]
    unparsed_options: Tuple[str, ...]
    issues: Tuple[str, ...]


@dataclass(frozen=True)
class InspectionReport:
    schema_version: int
    mode: str
    source: str
    sha256: str
    status: str
    shares: Tuple[DeclaredShare, ...]
    special_sections: Tuple[str, ...]
    issues: Tuple[str, ...]
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


NOTES = (
    "Déclarations de ce fichier uniquement ; aucun état effectif du serveur n'est certifié.",
    "Les valeurs absentes restent inconnues : héritage global et valeurs par défaut non évalués.",
    "Aucun fichier inclus, registre Samba ou usershare n'est consulté.",
    "Aucun compte, groupe, dossier partagé, ACL, service ou pare-feu n'est interrogé.",
    "Lecture seule : aucun fichier écrit, aucun programme lancé et aucun testparm exécuté.",
    "Les valeurs d'options non prises en charge ne sont pas reproduites dans ce rapport.",
)


def _boolean(raw: str) -> Optional[bool]:
    return {"yes": True, "true": True, "1": True,
            "no": False, "false": False, "0": False}.get(raw.casefold())


def inspect_content(content: str, source: str = "Contenu fourni", mode: str = "provided",
                    fingerprint: Optional[str] = None) -> InspectionReport:
    fingerprint = fingerprint or hashlib.sha256(content.encode("utf-8")).hexdigest()
    if content.startswith("\ufeff"):
        content = content[1:]
    try:
        sections = scan_sections(content)
    except PlanError as error:
        return InspectionReport(1, mode, source, fingerprint, "blocked", (), (), (str(error),), NOTES)
    lines = content.splitlines()
    result = []
    special = []
    issues = []
    for section in sections:
        if section.name.casefold() in {"global", "homes", "printers"}:
            special.append(section.name)
            if section.name.casefold() != "global":
                issues.append("Section spéciale non développée : " + section.name + ".")
            continue
        values = {}
        row_issues = []
        unknown = set()
        for key, index in section.fields:
            canonical = ALIASES.get(key, key)
            if canonical not in KNOWN:
                unknown.add(key)
                continue
            if canonical == "comment":
                continue
            raw = lines[index].split("=", 1)[1].strip()
            values.setdefault(canonical, []).append((key, raw))

        def single(key):
            declarations = values.get(key, [])
            if len(declarations) > 1:
                row_issues.append("Paramètre répété ou synonymes concurrents : " + key + ". Valeur non déterminée.")
                return None
            return declarations[0] if declarations else None

        path_value = single("path")
        path = path_value[1] if path_value else None
        if path is not None and ("%" in path or '"' in path or "'" in path):
            row_issues.append("Chemin déclaré avec substitution ou guillemets : chemin effectif non déterminé.")
        if not path:
            path = None
            row_issues.append("Chemin local absent, vide ou ambigu ; aucun dossier déduit.")
        booleans = {}
        for key in ("read only", "browseable", "guest ok"):
            declaration = single(key)
            value = _boolean(declaration[1]) if declaration else None
            if declaration and value is None:
                row_issues.append("Valeur booléenne non reconnue pour " + key + ".")
            if declaration and declaration[0] in INVERTED and value is not None:
                value = not value
            booleans[key] = value
        principals = single("valid users")
        users, groups, unresolved = [], [], []
        access_status = "not-declared" if "valid users" not in values else "unknown"
        if principals is not None:
            tokens = tuple(token for token in re.split(r"[\s,]+", principals[1]) if token)
            access_status = "empty" if not tokens else "declared"
            for token in tokens:
                if token.startswith("+") and IDENTITY.fullmatch(token[1:]):
                    groups.append(token[1:])
                elif IDENTITY.fullmatch(token):
                    users.append(token)
                else:
                    unresolved.append(token)
            if unresolved:
                access_status = "partial"
                row_issues.append("Certains destinataires nécessitent une résolution non prise en charge (netgroups, domaine ou substitution).")
        if unknown:
            row_issues.append("Options non interprétées ; elles peuvent modifier le comportement du partage.")
        result.append(DeclaredShare(section.name, path, booleans["read only"], booleans["browseable"],
                                    booleans["guest ok"], access_status, tuple(users), tuple(groups),
                                    tuple(unresolved), tuple(sorted(unknown)), tuple(row_issues)))
    return InspectionReport(1, mode, source, fingerprint, "inspected", tuple(result), tuple(special),
                            tuple(issues), NOTES)


def read_configuration(filename: str) -> ConfigurationSnapshot:
    """Ouvrir seulement un fichier régulier explicite, avec lecture bornée."""
    if not filename or "\x00" in filename:
        raise InspectionError("Indiquer un chemin de fichier non vide, sans caractère nul.")
    path = Path(filename).absolute()
    try:
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode):
            raise InspectionError("Choisir un fichier régulier directement, sans lien symbolique, dossier ou fichier spécial.")
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (initial.st_dev, initial.st_ino):
                raise InspectionError("Le fichier choisi a changé avant son ouverture ; recommencer la sélection.")
            if before.st_size > MAX_CONFIG_BYTES:
                raise InspectionError("Fichier trop volumineux : limite de lecture de 1 Mio.")
            data = stream.read(MAX_CONFIG_BYTES + 1)
            after = os.fstat(stream.fileno())
            identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if identity(before) != identity(after):
                raise InspectionError("Le fichier a changé pendant la lecture ; aucun rapport conservé.")
        if len(data) > MAX_CONFIG_BYTES:
            raise InspectionError("Fichier trop volumineux : limite de lecture de 1 Mio.")
        content = data.decode("utf-8")
    except UnicodeError as error:
        raise InspectionError("Encodage non pris en charge : choisir un fichier texte UTF-8.") from error
    except OSError as error:
        raise InspectionError("Lecture impossible : vérifier le chemin et les droits, sans lancer SambaPilot avec sudo.") from error
    return ConfigurationSnapshot(str(path), content, hashlib.sha256(data).hexdigest())


def inspect_file(filename: str) -> InspectionReport:
    return read_configuration(filename).inspect()


def format_inspection(report: InspectionReport) -> str:
    def boolean(value):
        return "oui" if value is True else "non" if value is False else "non déclaré / inconnu"

    def clean(text):
        return "".join(char if char.isprintable() else "?" for char in text)

    access_labels = {"not-declared": "non déclarée ici", "unknown": "ambiguë / inconnue",
                     "empty": "liste vide déclarée ; aucune restriction par cette liste seule",
                     "declared": "destinataires déclarés", "partial": "destinataires partiellement reconnus"}

    lines = ["SambaPilot — Examen de configuration en lecture seule",
             "Source : " + clean(report.source), "Empreinte SHA-256 : " + report.sha256,
             "Périmètre : déclarations locales, sans calcul des droits effectifs.", ""]
    if report.status == "blocked":
        lines.append("Analyse bloquée : aucun inventaire fiable produit. Cela ne signifie pas qu’il n’existe aucun partage.")
    else:
        lines.append(str(len(report.shares)) + " sections de partage déclarées dans ce fichier.")
    for share in report.shares:
        lines += ["", "[" + clean(share.name) + "]",
                  "  Chemin déclaré : " + clean(share.path or "non déclaré / inconnu"),
                  "  Lecture seule déclarée : " + boolean(share.read_only),
                  "  Visibilité déclarée : " + boolean(share.browseable),
                  "  Accès invité déclaré : " + boolean(share.guest_ok),
                  "  Liste d’accès : " + access_labels[share.access_list_status],
                  "  Utilisateurs déclarés : " + clean(", ".join(share.users) or "aucun nom identifié"),
                  "  Groupes UNIX déclarés : " + clean(", ".join(share.unix_groups) or "aucun groupe identifié")]
        if share.unresolved_principals:
            lines.append("  Destinataires non résolus : " + clean(", ".join(share.unresolved_principals)))
        if share.unparsed_options:
            lines.append("  Options non interprétées : " + clean(", ".join(share.unparsed_options)))
        lines.extend("  À vérifier : " + clean(issue) for issue in share.issues)
    if report.special_sections:
        lines += ["", "Sections spéciales non développées : " + clean(", ".join(report.special_sections))]
    lines += ["", *[clean(issue) for issue in report.issues], "", *report.notes]
    return "\n".join(lines)
