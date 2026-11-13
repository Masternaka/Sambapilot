"""Préréglages descriptifs pour une création ; aucune identité ou permission réelle déduite."""

from dataclasses import dataclass, replace
from typing import Optional, Tuple

from .planning import PlanError, ShareDraft, validate_draft


@dataclass(frozen=True)
class ShareProfile:
    key: str
    title: str
    name: str
    path: str
    read_only: bool
    browseable: bool
    guidance: str


SHARE_PROFILES = (
    ShareProfile('personal', 'Personnel', 'Personnel', '/srv/partages/personnel', False, False,
                 'Pour un dossier personnel, choisir explicitement le compte autorisé. Masquer le partage ne remplace pas les restrictions d’accès.'),
    ShareProfile('family', 'Familial', 'Partage famille', '/srv/partages/famille', False, True,
                 'Choisir les comptes ou le groupe familial autorisés. Le groupe n’est ni détecté ni créé par ce profil.'),
    ShareProfile('media', 'Médias en lecture seule', 'Mediatheque', '/srv/partages/medias', True, True,
                 'Proposer la consultation des médias sans écriture Samba. Les droits réels du dossier restent à vérifier.'),
)


def profile_values(key: str, name: str = '', path: str = '') -> ShareProfile:
    """Compléter les champs vides ; conserver les textes saisis, même encore invalides."""
    profile = next((profile for profile in SHARE_PROFILES if profile.key == key), None)
    if profile is None:
        raise PlanError('Profil de partage inconnu.')
    return replace(profile, name=name if name else profile.name, path=path if path else profile.path)


def draft_from_profile(key: str, name: str = '', path: str = '', users: Tuple[str, ...] = (),
                       groups: Tuple[str, ...] = (), read_only: Optional[bool] = None,
                       browseable: Optional[bool] = None) -> ShareDraft:
    profile = profile_values(key, name, path)
    draft = ShareDraft(profile.name, profile.path, users, groups,
                       profile.read_only if read_only is None else read_only,
                       profile.browseable if browseable is None else browseable)
    validate_draft(draft)
    return draft
