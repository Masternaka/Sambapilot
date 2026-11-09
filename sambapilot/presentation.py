"""Données de présentation GTK, testables sans bibliothèque graphique."""

from dataclasses import dataclass
from typing import Optional, Tuple

from .access import AccessDecision, AccessReport, Right
from .demo import DemoProbe, access_demo
from .diagnostic import Report, collect
from .inspection import DeclaredShare, InspectionReport


def right_text(value: Right) -> str:
    return "Autorisé" if value is True else "Refusé" if value is False else "Inconnu"


def decision_status(decision: AccessDecision) -> str:
    if decision.conflicts:
        return "Conflit"
    if decision.read is None or decision.write is None:
        return "À vérifier"
    return "Déterminé sur l’exemple"


@dataclass(frozen=True)
class AccessFilters:
    user: Optional[str] = None
    share: Optional[str] = None
    query: str = ""
    conflicts_only: bool = False


@dataclass(frozen=True)
class DemoViewModel:
    diagnostic: Report
    accesses: AccessReport

    def __post_init__(self) -> None:
        # Cette première fenêtre ne doit jamais présenter une sonde réelle comme une démo.
        if self.diagnostic.mode != "demo" or self.accesses.mode != "demo":
            raise ValueError("La fenêtre actuelle accepte uniquement des rapports de démonstration.")

    @classmethod
    def create(cls) -> "DemoViewModel":
        return cls(collect(DemoProbe("configured")), access_demo())

    @property
    def users(self) -> Tuple[str, ...]:
        return tuple(sorted({row.user for row in self.accesses.decisions}))

    @property
    def shares(self) -> Tuple[str, ...]:
        return tuple(sorted({row.share for row in self.accesses.decisions}))

    @property
    def conflict_count(self) -> int:
        return sum(bool(row.conflicts) for row in self.accesses.decisions)

    @property
    def unknown_count(self) -> int:
        return sum(row.read is None or row.write is None for row in self.accesses.decisions)

    def filtered(self, filters: AccessFilters) -> Tuple[AccessDecision, ...]:
        query = filters.query.strip().casefold()
        return tuple(row for row in self.accesses.decisions
                     if (filters.user is None or row.user == filters.user)
                     and (filters.share is None or row.share == filters.share)
                     and (not filters.conflicts_only or row.conflicts)
                     and (not query or query in " ".join((row.user, row.share, row.path)).casefold()))


def decision_details(row: AccessDecision) -> str:
    return "\n".join((
        row.path,
        "",
        "Lecture estimée : " + right_text(row.read),
        "Écriture estimée : " + right_text(row.write),
        "",
        "Règles Samba déclarées : lecture " + right_text(row.samba_read).lower()
        + ", écriture " + right_text(row.samba_write).lower() + ".",
        "Permissions de fichiers déclarées : lecture " + right_text(row.filesystem_read).lower()
        + ", écriture " + right_text(row.filesystem_write).lower() + ".",
        "", *row.reasons, *row.conflicts,
        "", "Estimation sur données fictives ; aucun accès réel testé.",
    ))


@dataclass(frozen=True)
class DeclaredSharesView:
    """Présentation d'une lecture ponctuelle de fichier, sans droits effectifs déduits."""

    report: "InspectionReport"

    def __post_init__(self) -> None:
        if self.report.mode != "file":
            raise ValueError("Cette vue exige un rapport de fichier choisi, distinct de la démonstration.")

    @property
    def shares(self) -> Tuple["DeclaredShare", ...]:
        return self.report.shares if self.report.status == "inspected" else ()

    def filtered(self, query: str = "", category: str = "all") -> Tuple[DeclaredShare, ...]:
        if category not in ("all", "incomplete", "ambiguous", "unsupported"):
            raise ValueError("Filtre de déclaration inconnu.")
        query = query.strip().casefold()
        return tuple(share for share in self.shares
                     if (not query or query in (share.name + " " + (share.path or "")).casefold())
                     and (category == "all"
                          or category == "incomplete" and bool(share.missing_fields)
                          or category == "ambiguous" and bool(share.ambiguous_fields)
                          or category == "unsupported" and bool(share.unparsed_options or share.unresolved_principals)))

    @property
    def summary(self) -> str:
        if self.report.status != "inspected":
            return "Analyse bloquée : aucun inventaire fiable affichable. Consultez les explications du rapport."
        if not self.shares:
            return ("Aucune déclaration locale ordinaire dans ce fichier. "
                    "Cela ne prouve pas l’absence de partages sur le serveur.")
        return str(len(self.shares)) + " déclaration(s) locale(s) lue(s). Aucun accès effectif vérifié."


def declared_share_details(share: "DeclaredShare") -> str:
    def boolean(value):
        return "Oui" if value is True else "Non" if value is False else "Inconnu"

    access = {
        "not-declared": "Non déclarée localement ; aucun héritage calculé.",
        "empty": "Explicitement vide ; aucun accès effectif déduit.",
        "declared": "Destinataires déclarés ; existence des comptes et groupes non vérifiée.",
        "partial": "Partiellement reconnue ; certains destinataires restent non résolus.",
        "unknown": "Inconnue ou ambiguë.",
    }
    lines = [
        "Chemin déclaré : " + (share.path or "Inconnu"),
        "Lecture seule déclarée : " + boolean(share.read_only),
        "Visibilité déclarée : " + boolean(share.browseable),
        "Accès invité déclaré : " + boolean(share.guest_ok),
        "Liste d’accès : " + access.get(share.access_list_status, "Inconnue."),
        "Utilisateurs reconnus : " + (", ".join(share.users) or "Aucun identifiant résolu"),
        "Groupes UNIX reconnus : " + (", ".join(share.unix_groups) or "Aucun identifiant résolu"),
    ]
    if share.unresolved_principals:
        lines.append("Destinataires non résolus : " + ", ".join(share.unresolved_principals))
    if share.unparsed_options:
        lines.append("Options non interprétées (noms uniquement) : " + ", ".join(share.unparsed_options))
    lines.extend(share.issues)
    lines.append("Permissions Linux, ACL et accès réseau : inconnus ; aucun dossier partagé consulté.")
    return "\n".join(lines)


def declared_share_guidance(share: DeclaredShare) -> str:
    names = {"path": "chemin", "read only": "lecture seule", "browseable": "visibilité",
             "guest ok": "accès invité", "valid users": "liste d’accès"}
    lines = []
    if share.missing_fields:
        lines.append("Réglages incomplets : " + ", ".join(names[key] for key in share.missing_fields) + ". "
                     "Vérifiez les déclarations locales et les éventuels réglages globaux ; aucune valeur n’est supposée.")
    if share.ambiguous_fields:
        lines.append("Réglages ambigus ou non résolus : " + ", ".join(names[key] for key in share.ambiguous_fields) + ". "
                     "Examinez les répétitions, les valeurs non reconnues ou les substitutions dans le rapport.")
    if share.unparsed_options or share.unresolved_principals:
        lines.append("Interprétation non prise en charge : consultez les options et destinataires signalés "
                     "dans le rapport avant de déterminer leur effet. Aucun réglage n’est supprimé automatiquement.")
    if share.guest_ok is True:
        lines.append("Accès invité déclaré : la préparation automatique de modification ne le prend pas en charge.")
    if share.access_list_status == "empty":
        lines.append("Liste d’accès explicitement vide : ce n’est pas une liste manquante. "
                     "La modification guidée exige au moins un destinataire explicite.")
    if not lines:
        lines.append("Déclarations locales reconnues ; la préparation vérifie aussi les contraintes du rédacteur. "
                     "Les comptes, les permissions des fichiers et les accès réseau restent à vérifier.")
    return "\n".join(lines)
