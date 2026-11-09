"""Données de présentation GTK, testables sans bibliothèque graphique."""

from dataclasses import dataclass
from typing import Optional, Tuple

from .access import AccessDecision, AccessReport, Right
from .demo import DemoProbe, access_demo
from .diagnostic import Report, collect


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
