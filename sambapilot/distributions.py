"""Profils de lecture seule pour les distributions ciblées, sans commandes d'installation."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class DistributionProfile:
    key: str
    name: str
    package_manager: str
    query_tool: str
    package_tools: Tuple[Tuple[str, Tuple[str, ...]], ...]
    services: Tuple[str, ...]

    @property
    def packages(self) -> Tuple[str, ...]:
        return tuple(name for name, _tools in self.package_tools)


PROFILES = {
    "arch": DistributionProfile("arch", "Arch Linux", "pacman", "pacman",
                                (("samba", ("smbd", "testparm", "smbpasswd")),
                                 ("smbclient", ("smbclient",))), ("smb.service", "nmb.service")),
    "debian": DistributionProfile("debian", "Debian", "apt", "dpkg-query",
                                  (("samba", ("smbd",)),
                                   ("samba-common-bin", ("testparm", "smbpasswd")),
                                   ("smbclient", ("smbclient",))), ("smbd.service", "nmbd.service")),
    "fedora": DistributionProfile("fedora", "Fedora", "dnf", "rpm",
                                  (("samba", ("smbd",)),
                                   ("samba-common-tools", ("testparm", "smbpasswd")),
                                   ("samba-client", ("smbclient",))), ("smb.service", "nmb.service")),
}
FIREWALL_SERVICES = ("ufw.service", "firewalld.service", "nftables.service")


def identify_profile(distribution_id: str, id_like: str = "") -> Optional[DistributionProfile]:
    # L'identité exacte prime sur les familles ; une filiation ambiguë est refusée.
    if distribution_id in PROFILES:
        return PROFILES[distribution_id]
    candidates = set(id_like.split()) & PROFILES.keys()
    return PROFILES[next(iter(candidates))] if len(candidates) == 1 else None
