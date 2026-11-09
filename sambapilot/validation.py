"""Contrôle explicite d'un candidat avec le testparm système déjà installé."""

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
from typing import Optional, Tuple

from .inspection import MAX_CONFIG_BYTES, InspectionError, read_configuration
from .planning import FIELDS, IDENTITY, PlanError, SharePlan, digest, scan_sections, validate_name
from .system import HostProbe


GLOBAL_FIELDS = {"workgroup", "netbios name", "server string", "server role", "security",
                 "server min protocol", "server max protocol"}
TIMEOUT_SECONDS = 5
MAX_DIAGNOSTICS = 8192
NOTES = (
    "Le candidat est contrôlé, jamais installé ; aucun service n’est rechargé.",
    "Un retour positif de testparm ne certifie pas les comptes, les droits des fichiers ou les accès réseau.",
    "Les avertissements de Samba restent à examiner, même avec un code de retour nul.",
    "Les fichiers temporaires sont nettoyés à la fin du contrôle ; un échec de nettoyage est signalé.",
)


@dataclass(frozen=True)
class ValidationResult:
    status: str
    candidate_sha256: str
    message: str
    tool: Optional[str] = None
    returncode: Optional[int] = None
    diagnostics: str = ""
    notes: Tuple[str, ...] = NOTES
    can_apply: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def check_validation_scope(plan: SharePlan) -> None:
    if digest(plan.candidate) != plan.candidate_sha256:
        raise PlanError("Le contenu candidat ne correspond plus à son empreinte.")
    if len(plan.candidate.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise PlanError("Le candidat dépasse la limite de 1 Mio.")
    content = plan.candidate[1:] if plan.candidate.startswith("\ufeff") else plan.candidate
    sections = scan_sections(content)
    lines = content.splitlines()
    for section in sections:
        global_section = section.name.casefold() == "global"
        if not global_section:
            validate_name(section.name)
        allowed = GLOBAL_FIELDS if global_section else FIELDS | {"comment"}
        seen = set()
        for key, index in section.fields:
            if key not in allowed or key in seen:
                raise PlanError("Le candidat contient une option hors du périmètre de validation ou répétée : " + key + ".")
            seen.add(key)
            value = lines[index].split("=", 1)[1].strip()
            if any(char in value for char in ("%", "`")):
                raise PlanError("Les substitutions ne sont pas prises en charge pour ce contrôle.")
            if global_section and key == "server role" and value.casefold() != "standalone server":
                raise PlanError("Seul le rôle standalone server est pris en charge pour ce contrôle.")
            if global_section and key == "security" and value.casefold() != "user":
                raise PlanError("Seule la sécurité user est prise en charge pour ce contrôle.")
            if key == "valid users":
                for token in re.split(r"[\s,]+", value):
                    if token and not IDENTITY.fullmatch(token[1:] if token.startswith("+") else token):
                        raise PlanError("La liste d’accès nécessite une résolution hors du périmètre de validation.")


def source_is_current(plan: SharePlan) -> bool:
    if plan.mode != "file":
        return True
    if not plan.source:
        return False
    try:
        return read_configuration(plan.source).sha256 == plan.baseline_sha256
    except InspectionError:
        return False


def _diagnostics(output: Optional[bytes], directory: str) -> str:
    text = (output or b"")[-MAX_DIAGNOSTICS:].decode("utf-8", errors="replace")
    text = text.replace(directory, "<temporaire>")
    return "".join(char if char.isprintable() or char in "\n\t" else "?" for char in text).strip()


def validate_plan(plan: SharePlan) -> ValidationResult:
    """Aucun appel externe sans demande ; aucun exécutable provenant du PATH."""
    def result(status, message, tool=None, returncode=None, diagnostics=""):
        return ValidationResult(status, plan.candidate_sha256, message, tool, returncode, diagnostics)

    try:
        check_validation_scope(plan)
    except PlanError as error:
        return result("unsupported", str(error))
    if platform.system() != "Linux":
        return result("unavailable", "Le contrôle natif est réservé à Linux avec Samba déjà installé.")
    tool = HostProbe().tool("testparm")
    if tool is None:
        return result("unavailable", "testparm système non détecté. Aucune installation n’a été tentée.")
    if not source_is_current(plan):
        return result("stale", "Le fichier source a changé ou est devenu inaccessible. Rechargez-le avant tout contrôle.", tool)
    try:
        with tempfile.TemporaryDirectory(prefix="sambapilot-validation-") as directory:
            candidate_path = Path(directory) / "candidate.conf"
            descriptor = os.open(candidate_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(plan.candidate.encode("utf-8"))
            try:
                completed = subprocess.run(
                    (tool, "--suppress-prompt", "--debuglevel=0", str(candidate_path)),
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    timeout=TIMEOUT_SECONDS, check=False, shell=False, cwd=directory,
                    env={"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C"},
                )
                diagnostics = _diagnostics(completed.stderr, directory)
                status = "accepted" if completed.returncode == 0 else "rejected" if completed.returncode == 1 else "error"
                code = completed.returncode
            except subprocess.TimeoutExpired as error:
                status, code = "timeout", None
                diagnostics = _diagnostics(error.stderr, directory)
    except OSError:
        return result("error", "La préparation, l’exécution ou le nettoyage du contrôle a échoué. Aucun changement appliqué.", tool)
    if not source_is_current(plan):
        return result("stale", "Le fichier source a changé ou est devenu inaccessible pendant le contrôle. Résultat abandonné.", tool)
    messages = {
        "accepted": "testparm a accepté la configuration candidate. Aucun changement appliqué.",
        "rejected": "testparm a rejeté la configuration candidate. Aucun changement appliqué.",
        "error": "testparm s’est interrompu ou a retourné un code inattendu ; contrôle non concluant.",
        "timeout": "Le délai de contrôle est dépassé ; aucune acceptation ne peut être conclue.",
    }
    return result(status, messages[status], tool, code, diagnostics)


def format_validation(validation: ValidationResult) -> str:
    lines = ["Contrôle Samba de la configuration candidate", validation.message,
             "Empreinte du candidat : " + validation.candidate_sha256]
    if validation.returncode is not None:
        lines.append("Code de retour : " + str(validation.returncode))
    if validation.diagnostics:
        lines += ["", "Messages de Samba :", validation.diagnostics]
    lines += ["", *validation.notes]
    return "\n".join(lines)
