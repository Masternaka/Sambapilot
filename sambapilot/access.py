"""Estimer des accès déclarés sans interroger ou modifier le système.

Ce modèle volontairement limité n'est pas un interpréteur de smb.conf.
None signifie inconnu, jamais autorisé par défaut.
"""

from dataclasses import asdict, dataclass
from typing import Optional, Tuple


Right = Optional[bool]


@dataclass(frozen=True)
class User:
    name: str
    groups: Optional[Tuple[str, ...]] = None
    samba_enabled: Right = None


@dataclass(frozen=True)
class Share:
    name: str
    path: str
    allowed_users: Tuple[str, ...] = ()
    allowed_groups: Tuple[str, ...] = ()
    read_only: bool = True
    write_users: Tuple[str, ...] = ()
    write_groups: Tuple[str, ...] = ()
    enabled: bool = True
    unsupported_options: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FileAccess:
    user: str
    share: str
    read: Right = None
    write: Right = None
    traverse: Right = None
    detail: str = "Permissions et ACL non établies."


@dataclass(frozen=True)
class AccessDecision:
    user: str
    share: str
    path: str
    samba_read: Right
    samba_write: Right
    filesystem_read: Right
    filesystem_write: Right
    read: Right
    write: Right
    reasons: Tuple[str, ...]
    conflicts: Tuple[str, ...]


@dataclass(frozen=True)
class AccessReport:
    schema_version: int
    mode: str
    decisions: Tuple[AccessDecision, ...]
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def intersect(*rights: Right) -> Right:
    """Un refus établi suffit ; sinon, une inconnue interdit de conclure oui."""
    if any(right is False for right in rights):
        return False
    if any(right is None for right in rights):
        return None
    return True


def matches(user: User, users: Tuple[str, ...], groups: Tuple[str, ...]) -> Right:
    if user.name in users:
        return True
    if groups and user.groups is None:
        return None
    return bool(set(user.groups or ()) & set(groups))


def evaluate(user: User, share: Share, files: FileAccess) -> AccessDecision:
    if (files.user, files.share) != (user.name, share.name):
        raise ValueError("Les observations ne correspondent pas au compte et au partage.")

    reasons = []
    conflicts = []
    fs_read = intersect(files.traverse, files.read)
    fs_write = intersect(files.traverse, files.write)
    if share.unsupported_options:
        # Une substitution d'identité pourrait aussi invalider les observations Linux.
        return AccessDecision(
            user.name, share.name, share.path, None, None, None, None, None, None,
            ("Options hors du modèle : " + ", ".join(share.unsupported_options)
             + ". Accès non déterminé.",), (),
        )

    allowed = (matches(user, share.allowed_users, share.allowed_groups)
               if share.allowed_users or share.allowed_groups else True)
    samba_read = intersect(share.enabled, user.samba_enabled, allowed)
    writable = (matches(user, share.write_users, share.write_groups)
                if share.read_only else True)
    samba_write = intersect(samba_read, writable)

    if not share.enabled:
        reasons.append("Partage désactivé dans les données déclarées.")
    if user.samba_enabled is False:
        reasons.append("Compte Samba déclaré désactivé ou absent.")
    elif user.samba_enabled is None:
        reasons.append("État du compte Samba inconnu.")
    if allowed is False:
        reasons.append("Compte hors des utilisateurs et groupes autorisés.")
    elif allowed is None:
        reasons.append("Appartenance aux groupes autorisés inconnue.")
    if share.read_only and writable is False:
        reasons.append("Partage en lecture seule pour ce compte.")
    elif writable is None:
        reasons.append("Appartenance aux groupes d'écriture inconnue.")
    if files.traverse is False:
        reasons.append("Traversée du chemin refusée selon les observations déclarées.")
    if fs_read is None or fs_write is None:
        reasons.append("Permissions de fichiers ou traversée incomplètement établies.")
    reasons.append(files.detail)

    for operation, samba, filesystem in (("lecture", samba_read, fs_read),
                                         ("écriture", samba_write, fs_write)):
        if samba is True and filesystem is False:
            conflicts.append("Conflit en " + operation
                             + " : autorisée par les règles Samba déclarées, refusée côté fichiers.")

    return AccessDecision(
        user.name, share.name, share.path, samba_read, samba_write, fs_read, fs_write,
        intersect(samba_read, fs_read), intersect(samba_write, fs_write),
        tuple(reasons), tuple(conflicts),
    )


def build_matrix(users: Tuple[User, ...], shares: Tuple[Share, ...],
                 observations: Tuple[FileAccess, ...], mode: str = "declared") -> AccessReport:
    """Produire toutes les paires sans inventer les observations manquantes."""
    user_names = {user.name for user in users}
    share_names = {share.name for share in shares}
    if len(user_names) != len(users) or len(share_names) != len(shares):
        raise ValueError("Les noms de comptes et de partages doivent être uniques.")
    facts = {}
    for observation in observations:
        key = (observation.user, observation.share)
        if observation.user not in user_names or observation.share not in share_names:
            raise ValueError("Observation pour un compte ou un partage inconnu.")
        if key in facts:
            raise ValueError("Observations en double pour un compte et un partage.")
        facts[key] = observation
    decisions = tuple(
        evaluate(user, share, facts.get((user.name, share.name), FileAccess(user.name, share.name)))
        for user in users for share in shares
    )
    return AccessReport(1, mode, decisions, (
        "Estimation sur données déclarées ; aucun accès réel ni authentification testés.",
        "Les droits de fichiers sont fournis, pas collectés ni déduits de la machine.",
        "Les droits des fichiers enfants, le réseau et le pare-feu ne sont pas vérifiés.",
        "Une information manquante reste inconnue ; aucune permission n'est modifiée.",
    ))
