"""Relier la lecture explicite d'un fichier à un plan qui ne sera pas appliqué."""

from dataclasses import replace
from typing import Optional

from .inspection import ConfigurationSnapshot, read_configuration
from .planning import PlanError, ShareDraft, SharePlan, prepare_plan, validate_draft


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
            raise PlanError("Le contenu du fichier a changé depuis son chargement. "
                            "Rechargez-le et examinez les nouveaux réglages avant de préparer un autre aperçu.")

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
