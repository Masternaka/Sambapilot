"""Données fictives : ce module ne consulte jamais le système hôte."""

from typing import Optional, Tuple

from .diagnostic import Observation, Service
from .access import AccessReport, FileAccess, Share, User, build_matrix


SCENARIOS = ("fresh", "configured", "restricted")


def demo_shares():
    return (
        Share("Famille", "/srv/partages/famille", allowed_groups=("famille",), read_only=False),
        Share("Medias", "/srv/partages/medias", allowed_groups=("famille",)),
        Share("Prive", "/srv/partages/prive", allowed_users=("alex",), read_only=False),
    )


def demo_configuration() -> str:
    from .planning import ShareDraft, render_section
    return ("# Configuration fictive SambaPilot\n[global]\n    workgroup = WORKGROUP\n"
            "    server role = standalone server\n\n" + "\n".join(
                render_section(ShareDraft(share.name, share.path, share.allowed_users,
                                          share.allowed_groups, share.read_only))
                for share in demo_shares()))


def access_demo() -> AccessReport:
    users = (
        User("alex", ("famille",), True),
        User("lea", ("famille",), True),
        User("visiteur", (), False),
        User("inconnu"),
    )
    shares = demo_shares()
    observations = (
        FileAccess("alex", "Famille", True, False, True, "Écriture fictive refusée par les permissions Linux."),
        FileAccess("lea", "Famille", True, True, True, "Permissions fictives de lecture et d'écriture."),
        FileAccess("alex", "Medias", True, True, True, "Permissions fictives côté fichiers."),
        FileAccess("lea", "Medias", True, True, True, "Permissions fictives côté fichiers."),
        FileAccess("alex", "Prive", True, True, True, "Permissions fictives côté fichiers."),
    )
    return build_matrix(users, shares, observations, mode="demo")


class DemoProbe:
    mode = "demo"

    def __init__(self, scenario: str = "configured") -> None:
        if scenario not in SCENARIOS:
            raise ValueError("Scénario inconnu.")
        self.scenario = scenario

    def system(self) -> str:
        return "Linux"

    def os_release(self) -> Tuple[str, Optional[str]]:
        return 'ID=arch\nPRETTY_NAME="Arch Linux (démonstration Omarchy)"\n', None

    def omarchy_marker(self) -> Observation:
        return Observation("present", "Dossier Omarchy fictif.")

    def configuration(self) -> Observation:
        if self.scenario == "fresh":
            return Observation("missing", "Configuration fictive absente.")
        if self.scenario == "restricted":
            return Observation("unknown", "Métadonnées fictives inaccessibles.")
        return Observation("present", "Fichier fictif présent ; contenu non lu.")

    def tool(self, name: str) -> Optional[str]:
        available = {"pacman", "systemctl"}
        if self.scenario != "fresh":
            available |= {"smbd", "testparm", "smbpasswd", "smbclient", "ufw", "nft", "iptables"}
        return "/usr/bin/" + name if name in available else None

    def service(self, name: str) -> Service:
        if self.scenario == "restricted":
            return Service(name, "unknown", detail="Accès systemd fictif refusé.")
        if self.scenario == "configured" and name in {"smb.service", "ufw.service"}:
            return Service(name, "observed", "loaded", "active", "enabled")
        return Service(name, "missing", load_state="not-found", detail="Unité fictive absente.")
