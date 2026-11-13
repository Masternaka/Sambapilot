"""Modèle de diagnostic partagé par les interfaces, indépendant du système."""

from dataclasses import asdict, dataclass
import shlex
from typing import Optional, Protocol, Tuple

from .distributions import FIREWALL_SERVICES, PROFILES, identify_profile


TOOLS = ("pacman", "dpkg-query", "rpm", "smbd", "testparm", "smbpasswd", "smbclient", "systemctl",
         "ufw", "firewall-cmd", "nft", "iptables")
SERVICES = tuple(dict.fromkeys(name for profile in PROFILES.values() for name in profile.services)) + FIREWALL_SERVICES


@dataclass(frozen=True)
class Observation:
    status: str
    detail: str


@dataclass(frozen=True)
class Tool:
    name: str
    path: Optional[str]


@dataclass(frozen=True)
class Service:
    name: str
    status: str
    load_state: str = "unknown"
    active_state: str = "unknown"
    unit_file_state: str = "unknown"
    detail: str = ""


@dataclass(frozen=True)
class Environment:
    system: str
    distribution_id: str
    distribution_name: str
    distribution_family: str
    package_manager: Optional[str]
    samba_service: Optional[str]


@dataclass(frozen=True)
class Report:
    schema_version: int
    mode: str
    environment: Environment
    tools: Tuple[Tool, ...]
    configuration: Observation
    services: Tuple[Service, ...]
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class Probe(Protocol):
    """Contrat de lecture seule ; aucune opération d'application des réglages."""

    mode: str

    def system(self) -> str: ...
    def os_release(self) -> Tuple[str, Optional[str]]: ...
    def configuration(self) -> Observation: ...
    def tool(self, name: str) -> Optional[str]: ...
    def service(self, name: str) -> Service: ...


def parse_os_release(content: str) -> dict:
    """Lire les valeurs sans exécuter ni développer le contenu du fichier."""
    values = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        if key not in {"ID", "ID_LIKE", "PRETTY_NAME"}:
            continue
        try:
            parts = shlex.split(raw, comments=True)
        except ValueError:
            continue
        if len(parts) == 1:
            values[key] = parts[0]
    return values


def collect(probe: Probe) -> Report:
    system = probe.system()
    notes = [
        "Lecture seule : aucune installation, écriture système ou élévation de droits.",
        "Un outil détecté ne prouve pas qu'un service fonctionne.",
        "Les règles effectives du pare-feu et l'accès depuis un autre appareil ne sont pas vérifiés.",
    ]
    if system != "Linux":
        notes.append("Environnement non pris en charge : le diagnostic système cible Arch, Debian et Fedora sous Linux.")
        return Report(
            2, probe.mode,
            Environment(system, "unknown", "Non vérifiée", "unknown", None, None),
            (), Observation("not-checked", "Recherche réservée à Linux."), (), tuple(notes),
        )

    content, error = probe.os_release()
    release = parse_os_release(content)
    if error:
        notes.append(error)
    if "ID" not in release:
        notes.append("Distribution inconnue : /etc/os-release est absent, inaccessible ou incomplet.")
    distribution_id = release.get("ID", "unknown")
    profile = identify_profile(distribution_id, release.get("ID_LIKE", ""))
    if profile is None:
        notes.append("Distribution non reconnue comme Arch, Debian ou Fedora : compatibilité non établie.")
    elif distribution_id != profile.key:
        notes.append("Famille détectée par ID_LIKE ; cela ne certifie pas la compatibilité de cette distribution dérivée.")
    if profile and profile.key == "fedora":
        notes.append("SELinux peut restreindre les accès Samba ; son état et ses règles ne sont pas consultés.")
    tools = tuple(Tool(name, probe.tool(name)) for name in TOOLS)
    services = tuple(probe.service(name) for name in ((profile.services if profile else ()) + FIREWALL_SERVICES))
    notes.append("La configuration Samba est repérée sans lire son contenu ni valider ses partages.")
    return Report(
        2, probe.mode,
        Environment(system, distribution_id, release.get("PRETTY_NAME", distribution_id),
                    profile.key if profile else "unknown", profile.package_manager if profile else None,
                    profile.services[0] if profile else None),
        tools, probe.configuration(), services, tuple(notes),
    )
