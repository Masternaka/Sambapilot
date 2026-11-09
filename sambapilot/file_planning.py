"""Relier la lecture explicite d'un fichier à un plan qui ne sera pas appliqué."""

from dataclasses import dataclass, replace
import difflib
from typing import Optional

from .inspection import ConfigurationSnapshot, read_configuration
from .planning import ACTIONS, PlanError, ShareDraft, SharePlan, prepare_plan, validate_draft, validate_name


class SourceChangedError(PlanError):
    """La source relue diffère de celle de la session ou de la relecture examinée."""


@dataclass(frozen=True)
class SourceReloadReview:
    origin: ConfigurationSnapshot
    latest: ConfigurationSnapshot
    diff: str


class FilePlanSession:
    mode = "file"

    def __init__(self, snapshot: ConfigurationSnapshot) -> None:
        self.snapshot = snapshot
        self.report = snapshot.inspect()
        self.current: Optional[SharePlan] = None
        if self.report.status != "inspected":
            raise PlanError("La configuration choisie ne peut pas être préparée automatiquement : "
                            + "; ".join(self.report.issues))

    @classmethod
    def open(cls, filename: str) -> "FilePlanSession":
        return cls(read_configuration(filename))

    @property
    def source(self) -> str:
        return self.snapshot.content

    def discard(self) -> None:
        self.current = None

    def check_current(self) -> None:
        self.discard()
        latest = read_configuration(self.snapshot.source)
        if latest.sha256 != self.snapshot.sha256:
            raise SourceChangedError("Le contenu du fichier a changé depuis son chargement. "
                            "Rechargez-le et examinez les nouveaux réglages avant de préparer un autre aperçu.")

    def prepare_reload(self) -> SourceReloadReview:
        """Relire pour examen, sans adopter la source ni manipuler les champs saisis."""
        self.discard()
        latest = read_configuration(self.snapshot.source)
        FilePlanSession(latest)  # Refuser les structures bloquées avant de proposer une reprise.
        diff = "".join(difflib.unified_diff(self.source.splitlines(keepends=True),
                                         latest.content.splitlines(keepends=True),
                                         fromfile="Source initiale", tofile="Source rechargée"))
        return SourceReloadReview(self.snapshot, latest, diff)

    def adopt_reload(self, review: SourceReloadReview, action: str, name: str) -> "FilePlanSession":
        """Vérifier à nouveau le fichier et les limites de l'action avant une adoption explicite."""
        self.discard()
        if review.origin is not self.snapshot or review.latest.source != self.snapshot.source:
            raise PlanError("Cette relecture n’appartient pas à la source de la session courante.")
        if action not in ACTIONS:
            raise PlanError("Action inconnue.")
        validate_name(name)
        latest = read_configuration(self.snapshot.source)
        if latest.sha256 != review.latest.sha256:
            raise SourceChangedError("Le fichier a encore changé depuis la relecture. "
                                     "Rechargez-le et examinez à nouveau les différences.")
        replacement = FilePlanSession(latest)
        if action == "update":
            replacement.draft_for(name)
        elif action == "remove":
            prepare_plan(replacement.source, "remove", name, mode="file")
        elif any(share.name.casefold() == name.casefold() for share in replacement.report.shares):
            raise PlanError("Le nom à créer existe dans la source rechargée. Aucun partage ne sera remplacé.")
        return replacement

    def draft_for(self, name: str) -> ShareDraft:
        row = next((share for share in self.report.shares if share.name == name), None)
        if (row is None or row.issues or row.guest_ok is not False
                or row.read_only is None or row.browseable is None or row.path is None
                or row.access_list_status != "declared"):
            raise PlanError("Ce partage a des réglages incomplets, avancés ou un accès invité. "
                            "Le formulaire ne peut pas les remplacer par des suppositions.")
        draft = ShareDraft(row.name, row.path, row.users, row.unix_groups, row.read_only, row.browseable)
        validate_draft(draft)
        # L'inspecteur comprend quelques synonymes qui restent hors du rédacteur prudent.
        prepare_plan(self.source, "update", name, draft, mode="file")
        return draft

    def preview(self, action: str, name: str, draft: Optional[ShareDraft] = None) -> SharePlan:
        self.check_current()
        plan = prepare_plan(self.source, action, name, draft, mode="file")
        self.current = replace(plan, source=self.snapshot.source)
        return self.current
