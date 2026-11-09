"""Plans de partage en mémoire : validation et comparaison, sans effet système."""

from dataclasses import asdict, dataclass
import difflib
import hashlib
from pathlib import PurePosixPath
import re
from typing import Optional, Tuple


ACTIONS = ("create", "update", "remove")
RESERVED = {"global", "homes", "printers"}
FIELDS = {"path", "valid users", "read only", "browseable", "guest ok"}
INDIRECT = {"include", "copy", "config file", "registry shares"}
IDENTITY = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,31}\$?\Z")
HEADER = re.compile(r"\[([^\[\]]+)\]\Z")


class PlanError(ValueError):
    """Demande invalide ou configuration hors du périmètre pris en charge."""


@dataclass(frozen=True)
class ShareDraft:
    name: str
    path: str
    users: Tuple[str, ...] = ()
    groups: Tuple[str, ...] = ()
    read_only: bool = True
    browseable: bool = True


@dataclass(frozen=True)
class SharePlan:
    schema_version: int
    mode: str
    action: str
    name: str
    baseline_sha256: str
    candidate_sha256: str
    candidate: str
    diff: str
    changes: Tuple[str, ...]
    notes: Tuple[str, ...]
    can_apply: bool = False
    source: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def matches_source(self, source: str) -> bool:
        return self.baseline_sha256 == digest(source)


@dataclass(frozen=True)
class Section:
    name: str
    start: int
    end: int
    fields: Tuple[Tuple[str, int], ...]


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_name(name: str) -> None:
    if (not name or len(name) > 80 or name != name.strip() or not name[0].isalnum()
            or any(not (char.isalnum() or char in " _-.") for char in name)):
        raise PlanError("Nom de partage : 1 à 80 lettres, chiffres, espaces, points, tirets ou traits de soulignement ; commencer par une lettre ou un chiffre.")
    if name.casefold() in RESERVED:
        raise PlanError("Les sections global, homes et printers sont réservées.")


def validate_draft(draft: ShareDraft) -> None:
    validate_name(draft.name)
    path = draft.path
    if (not path.startswith("/") or path.startswith("//") or path != path.strip()
            or any(not char.isprintable() for char in path)
            or any(char in path for char in ("\\", "%", '"', "'"))
            or any(part in {".", ".."} for part in path.split("/"))
            or PurePosixPath(path) == PurePosixPath("/")):
        raise PlanError("Choisir un chemin Linux absolu vers un dossier, sans variable, traversée '..', guillemet ni caractère de contrôle ; la racine '/' est refusée.")
    if not draft.users and not draft.groups:
        raise PlanError("Indiquer au moins un utilisateur ou un groupe autorisé.")
    for names in (draft.users, draft.groups):
        if len(names) != len(set(names)):
            raise PlanError("Un compte ou groupe ne doit pas apparaître en double.")
        if any(not IDENTITY.fullmatch(name) for name in names):
            raise PlanError("Utiliser des identifiants Linux simples, sans préfixe '@', espace ou séparateur. Les groupes sont saisis séparément.")
    if type(draft.read_only) is not bool or type(draft.browseable) is not bool:
        raise PlanError("Les choix de lecture seule et de visibilité doivent être des booléens.")


def parse_identities(text: str) -> Tuple[str, ...]:
    if not text.strip():
        return ()
    names = tuple(item.strip() for item in text.split(","))
    if any(not name for name in names):
        raise PlanError("Séparer les comptes ou groupes par des virgules, sans élément vide.")
    return names


def draft_fields(draft: ShareDraft) -> dict:
    validate_draft(draft)
    return {
        "path": draft.path,
        "valid users": " ".join((*draft.users, *("+" + group for group in draft.groups))),
        "read only": "yes" if draft.read_only else "no",
        "browseable": "yes" if draft.browseable else "no",
        "guest ok": "no",
    }


def render_section(draft: ShareDraft, newline: str = "\n") -> str:
    fields = draft_fields(draft)
    return newline.join(["[" + draft.name + "]", *("    " + key + " = " + value
                                                   for key, value in fields.items()), ""])


def scan_sections(source: str) -> Tuple[Section, ...]:
    if any(not char.isprintable() and char not in "\n\r\t" for char in source):
        raise PlanError("La configuration contient des caractères de contrôle non pris en charge.")
    sections = []
    names = set()
    current = None
    fields = []
    lines = source.splitlines(keepends=True)
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.endswith("\\"):
            raise PlanError("Les lignes de configuration continuées ne sont pas prises en charge.")
        match = HEADER.fullmatch(line)
        if match:
            if current is not None:
                sections.append(Section(current[0], current[1], index, tuple(fields)))
            name = match.group(1).strip()
            if name.casefold() in names:
                raise PlanError("Plusieurs sections portent le même nom ; intervention automatique refusée.")
            names.add(name.casefold())
            current, fields = (name, index), []
            continue
        if line.startswith("[") or "=" not in line or current is None:
            raise PlanError("Structure de configuration non prise en charge ; aucun aperçu produit.")
        key = " ".join(line.split("=", 1)[0].casefold().split())
        if key in INDIRECT:
            raise PlanError("Configuration indirecte non prise en charge : " + key + ".")
        fields.append((key, index))
    if current is not None:
        sections.append(Section(current[0], current[1], len(lines), tuple(fields)))
    return tuple(sections)


def prepare_plan(source: str, action: str, name: str,
                 draft: Optional[ShareDraft] = None, mode: str = "preview") -> SharePlan:
    original_source = source
    bom = "\ufeff" if source.startswith("\ufeff") else ""
    source = source[len(bom):]
    if action not in ACTIONS:
        raise PlanError("Action inconnue.")
    validate_name(name)
    if action == "remove":
        if draft is not None:
            raise PlanError("Le retrait d’une déclaration n’accepte pas de nouveaux réglages.")
    else:
        if draft is None or draft.name != name:
            raise PlanError("Le formulaire doit correspondre au nom du partage demandé.")
        validate_draft(draft)
    sections = scan_sections(source)
    target = next((section for section in sections if section.name.casefold() == name.casefold()), None)
    if action == "create" and target is not None:
        raise PlanError("Un partage porte déjà ce nom (sans distinction de casse).")
    if action != "create" and target is None:
        raise PlanError("Le partage à modifier ou retirer n’existe pas dans la configuration fournie.")
    lines = source.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in source else "\n"
    if target is not None:
        keys = [key for key, _index in target.fields]
        unknown = set(keys) - FIELDS - {"comment"}
        if unknown or len(keys) != len(set(keys)):
            raise PlanError("La section contient des options avancées ou répétées ; elle doit être examinée manuellement.")
    if action == "create":
        separator = "" if not source or source.endswith(newline * 2) else newline if source.endswith(newline) else newline * 2
        candidate = source + separator + render_section(draft, newline)
    elif action == "remove":
        candidate = "".join(lines[:target.start] + lines[target.end:])
    else:
        values = draft_fields(draft)
        replacement = list(lines[target.start:target.end])
        existing = set()
        for key, index in target.fields:
            if key not in values:
                continue
            existing.add(key)
            original = lines[index]
            if original.split("=", 1)[1].strip() != values[key]:
                prefix = original.split("=", 1)[0]
                replacement[index - target.start] = prefix + "= " + values[key] + newline
        missing = ["    " + key + " = " + value + newline
                   for key, value in values.items() if key not in existing]
        if missing:
            if replacement and not replacement[-1].endswith(("\n", "\r")):
                replacement[-1] += newline
            replacement.extend(missing)
        candidate = "".join(lines[:target.start] + replacement + lines[target.end:])
    changes = (("Retirer uniquement la déclaration du partage ; conserver le dossier et tous ses fichiers.",)
               if action == "remove" else (
                   "Dossier proposé : " + draft.path,
                   "Utilisateurs : " + (", ".join(draft.users) or "aucun accès individuel"),
                   "Groupes : " + (", ".join(draft.groups) or "aucun accès par groupe"),
                   "Accès : " + ("lecture seule" if draft.read_only else "lecture et écriture"),
                   "Visible dans la liste : " + ("oui" if draft.browseable else "non"),
                   "Accès invité : désactivé.",
               ))
    diff_lines = difflib.unified_diff(source.splitlines(keepends=True), candidate.splitlines(keepends=True),
                                     fromfile="configuration-avant", tofile="configuration-proposee")
    comparison = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                         for line in diff_lines)
    candidate = bom + candidate
    return SharePlan(1, mode, action, name, digest(original_source), digest(candidate), candidate, comparison,
                     changes, (
                         "Aperçu uniquement : aucun fichier, compte, droit, service ou pare-feu modifié.",
                         "La préparation seule ne contrôle pas le candidat avec testparm ; consulter le résultat d’un contrôle explicite, s’il a été demandé.",
                         "Existence du dossier, comptes, groupes, ACL et accès réseau non vérifiés.",
                         "Masquer un partage ne retire pas les droits d’accès directs.",
                         "Une application future nécessitera un nouvel état de référence, une sauvegarde et une confirmation explicite.",
                     ))


def format_plan(plan: SharePlan) -> str:
    actions = {"create": "Création", "update": "Modification", "remove": "Retrait"}
    return "\n".join((
        "SambaPilot — Aperçu de partage",
        "DÉMONSTRATION — configuration fictive" if plan.mode == "demo" else "Configuration fournie — aperçu uniquement",
        "Source : " + "".join(char if char.isprintable() else "?" for char in plan.source) if plan.source else "Source : contenu en mémoire",
        actions[plan.action] + " : " + plan.name, "",
        *plan.changes, "", "Comparaison :", plan.diff or "Aucun changement de contenu.",
        "", *plan.notes,
    ))


class PlanSession:
    """Un aperçu devient caduc dès que le formulaire est modifié ou annulé."""

    def __init__(self, source: str, mode: str = "preview") -> None:
        self.source = source
        self.mode = mode
        self.current: Optional[SharePlan] = None

    def discard(self) -> None:
        self.current = None

    def preview(self, action: str, name: str, draft: Optional[ShareDraft] = None) -> SharePlan:
        self.discard()
        self.current = prepare_plan(self.source, action, name, draft, self.mode)
        return self.current
