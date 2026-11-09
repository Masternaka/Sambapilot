"""Adaptateur Linux : métadonnées et requêtes systemd en lecture seule."""

import os
from pathlib import Path
import platform
import stat
import subprocess
from typing import Optional, Tuple

from .diagnostic import Observation, Service, SERVICES, TOOLS


SYSTEM_BIN_DIRS = (Path("/usr/bin"), Path("/usr/sbin"))
SYSTEMCTL = "/usr/bin/systemctl"


def service_command(name: str) -> Tuple[str, ...]:
    """Liste fermée de requêtes ; aucun shell, sudo ou verbe de modification."""
    if name not in SERVICES:
        raise ValueError("Service hors du périmètre du diagnostic.")
    return (SYSTEMCTL, "--system", "--no-pager", "--no-ask-password", "show", name,
            "--property=LoadState,ActiveState,UnitFileState")


def read_service(name: str) -> Service:
    command = service_command(name)
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
            timeout=3, check=False, shell=False,
            env={"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C", "SYSTEMD_PAGER": "cat"},
        )
    except subprocess.TimeoutExpired:
        return Service(name, "unknown", detail="Délai de consultation systemd dépassé.")
    except OSError:
        return Service(name, "unknown", detail="Consultation systemd impossible, sans élévation de droits.")
    if result.returncode != 0:
        return Service(name, "unknown", detail="Échec de la consultation systemd ; état non déduit.")
    properties = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    load = properties.get("LoadState", "unknown")
    active = properties.get("ActiveState", "unknown")
    enabled = properties.get("UnitFileState") or "unknown"
    if load == "not-found":
        return Service(name, "missing", load_state=load, detail="Unité systemd introuvable.")
    if load == "unknown" or active == "unknown":
        return Service(name, "unknown", detail="Réponse systemd incomplète.")
    return Service(name, "observed", load, active, enabled)


def observe_path(path: Path, directory: bool = False) -> Observation:
    try:
        info = path.stat()
    except FileNotFoundError:
        return Observation("missing", "Dossier absent." if directory else "Fichier absent.")
    except OSError:
        return Observation("unknown", "Métadonnées inaccessibles ; présence non déterminée.")
    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not correct_type:
        return Observation("unknown", "Le chemin ne correspond pas au type attendu.")
    return Observation("present", "Dossier présent." if directory else "Fichier présent ; contenu non lu.")


class HostProbe:
    mode = "live"

    def system(self) -> str:
        return platform.system()

    def os_release(self) -> Tuple[str, Optional[str]]:
        try:
            # Borne de lecture ; aucun fichier n'est interprété par un shell.
            with Path("/etc/os-release").open(encoding="utf-8", errors="replace") as stream:
                content = stream.read(65537)
            if len(content) > 65536:
                return "", "Fichier /etc/os-release trop volumineux ; lecture ignorée."
            return content, None
        except OSError:
            return "", "Lecture de /etc/os-release impossible."

    def omarchy_marker(self) -> Observation:
        try:
            path = Path.home() / ".local/share/omarchy"
        except RuntimeError:
            return Observation("unknown", "Dossier personnel non déterminé.")
        return observe_path(path, directory=True)

    def configuration(self) -> Observation:
        return observe_path(Path("/etc/samba/smb.conf"))

    def tool(self, name: str) -> Optional[str]:
        if name not in TOOLS:
            raise ValueError("Outil hors du périmètre du diagnostic.")
        # Ignorer PATH : un shim utilisateur pourrait installer un outil à son lancement.
        for directory in SYSTEM_BIN_DIRS:
            candidate = directory / name
            try:
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
            except OSError:
                # Non détecté ne signifie pas non installé ; poursuivre la recherche.
                continue
        return None

    def service(self, name: str) -> Service:
        if name not in SERVICES:
            raise ValueError("Service hors du périmètre du diagnostic.")
        try:
            available = Path(SYSTEMCTL).is_file() and os.access(SYSTEMCTL, os.X_OK)
        except OSError:
            available = False
        if not available:
            return Service(name, "unknown", detail="systemctl système indisponible.")
        return read_service(name)
