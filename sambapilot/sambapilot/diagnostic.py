"""Modèle de diagnostic partagé par les interfaces, indépendant du système."""

from dataclasses import asdict, dataclass
import shlex
from typing import Optional, Protocol, Tuple


TOOLS = ("pacman", "smbd", "testparm", "smbpasswd", "smbclient", "systemctl",
         "ufw", "firewall-cmd", "nft", "iptables")
SERVICES = ("smb.service", "nmb.service", "ufw.service", "firewalld.service",
            "nftables.service")


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
    arch_based: bool
    omarchy_marker: Observation


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
    def omarchy_marker(self) -> Observation: ...
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
        notes.append("Environnement non pris en charge : le diagnostic système cible Linux/Omarchy.")
        return Report(
            1, probe.mode,
            Environment(system, "unknown", "Non vérifiée", False,
                        Observation("not-checked", "Recherche réservée à Linux.")),
            (), Observation("not-checked", "Recherche réservée à Linux."), (), tuple(notes),
        )

    content, error = probe.os_release()
    release = parse_os_release(content)
    if error:
        notes.append(error)
    if "ID" not in release:
        notes.append("Distribution inconnue : /etc/os-release est absent, inaccessible ou incomplet.")
    distribution_id = release.get("ID", "unknown")
    arch_based = "arch" in {distribution_id, *release.get("ID_LIKE", "").split()}
    if not arch_based:
        notes.append("Distribution non identifiée comme Arch : aucune compatibilité Omarchy confirmée.")

    marker = probe.omarchy_marker()
    if marker.status == "present":
        notes.append("Le dossier Omarchy est un indice ; sa présence ne certifie pas une installation fonctionnelle.")
    tools = tuple(Tool(name, probe.tool(name)) for name in TOOLS)
    services = tuple(probe.service(name) for name in SERVICES)
    notes.append("La configuration Samba est repérée sans lire son contenu ni valider ses partages.")
    return Report(
        1, probe.mode,
        Environment(system, distribution_id, release.get("PRETTY_NAME", distribution_id),
                    arch_based, marker),
        tools, probe.configuration(), services, tuple(notes),
    )
