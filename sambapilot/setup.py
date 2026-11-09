"""Plan d'installation descriptif, sans moteur d'exécution ni commande de mutation."""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
import subprocess
from typing import Optional, Tuple

from .demo import DemoProbe
from .diagnostic import Report, collect
from .system import HostProbe


PACKAGES = ("samba", "smbclient")
PACKAGE_TOOLS = {"samba": ("smbd", "testparm", "smbpasswd"), "smbclient": ("smbclient",)}
PACMAN_PATHS = ("/usr/bin/pacman", "/usr/sbin/pacman")


@dataclass(frozen=True)
class Package:
    name: str
    status: str
    version: Optional[str] = None
    detail: str = ""


@dataclass(frozen=True)
class SetupStep:
    key: str
    title: str
    status: str
    detail: str


@dataclass(frozen=True)
class InstallationPlan:
    schema_version: int
    mode: str
    status: str
    diagnostic: Report
    packages: Tuple[Package, ...]
    steps: Tuple[SetupStep, ...]
    blockers: Tuple[str, ...]
    basis_sha256: str
    notes: Tuple[str, ...]
    can_apply: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def query_package(name: str, executable: str) -> Package:
    if name not in PACKAGES or executable not in PACMAN_PATHS:
        raise ValueError("Requête de paquet hors du périmètre autorisé.")
    try:
        result = subprocess.run(
            (executable, "--query", "--", name), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            timeout=3, shell=False, check=False, env={"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return Package(name, "unknown", detail="Base locale des paquets non consultable.")
    fields = result.stdout.strip().split()
    if (result.returncode == 0 and len(fields) == 2 and fields[0] == name
            and re.fullmatch(r"[A-Za-z0-9_.+:~\-]+", fields[1])):
        return Package(name, "installed", fields[1], "Paquet déclaré installé par la base locale.")
    missing = "error: package '" + name + "' was not found"
    if result.returncode == 1 and not result.stdout.strip() and result.stderr.strip() == missing:
        return Package(name, "missing", detail="Paquet explicitement absent de la base locale.")
    return Package(name, "unknown", detail="Réponse de la base locale ambiguë ou en erreur ; absence non déduite.")


class HostSetupProbe(HostProbe):
    def package(self, name: str) -> Package:
        if name not in PACKAGES:
            raise ValueError("Paquet hors du périmètre autorisé.")
        executable = self.tool("pacman")
        return (query_package(name, executable) if executable in PACMAN_PATHS
                else Package(name, "unknown", detail="pacman système non détecté."))


class DemoSetupProbe(DemoProbe):
    def package(self, name: str) -> Package:
        if name not in PACKAGES:
            raise ValueError("Paquet hors du périmètre autorisé.")
        if self.scenario == "restricted":
            return Package(name, "unknown", detail="Base locale fictive inaccessible.")
        if self.scenario == "fresh":
            return Package(name, "missing", detail="Paquet fictif absent.")
        return Package(name, "installed", "exemple", "Version fictive, sans lien avec une version publiée.")


def build_installation_plan(report: Report, packages: Tuple[Package, ...]) -> InstallationPlan:
    if (len(packages) != len(PACKAGES) or {package.name for package in packages} != set(PACKAGES)
            or any(package.status not in {"installed", "missing", "unknown"} for package in packages)):
        raise ValueError("Les états des deux paquets attendus doivent être uniques et explicites.")
    tools = {tool.name: tool.path for tool in report.tools}
    package_map = {package.name: package for package in packages}
    steps = []
    blockers = []
    supported = report.environment.system == "Linux" and report.environment.arch_based
    if not supported:
        blockers.append("La cible doit être un environnement Linux identifié comme Arch ; aucune installation proposée pour ce système.")
    if tools.get("pacman") not in PACMAN_PATHS:
        blockers.append("Le gestionnaire pacman système n’est pas disponible.")
    if not tools.get("systemctl"):
        blockers.append("systemctl n’est pas détecté ; la gestion des services doit être examinée.")
    for name in PACKAGES:
        package = package_map[name]
        expected = PACKAGE_TOOLS[name]
        detected = tuple(tool for tool in expected if tools.get(tool))
        state = "retained" if package.status == "installed" else "needed" if package.status == "missing" else "blocked"
        detail = ("Conserver le paquet existant ; aucune réinstallation automatique."
                  if package.status == "installed" else
                  "Prévoir ce paquet et les dépendances nécessaires après examen de la transaction et autorisation."
                  if package.status == "missing" else "Établir l’état du paquet avant toute proposition d’installation.")
        if package.status == "unknown":
            blockers.append("État inconnu du paquet " + name + ".")
        inconsistent = ((package.status == "installed" and len(detected) != len(expected))
                        or (package.status == "missing" and bool(detected)))
        if inconsistent:
            blockers.append("Incohérence entre la base des paquets et les exécutables détectés pour " + name + ".")
            state, detail = "blocked", "Examiner l’installation existante avant de remplacer ou réinstaller quoi que ce soit."
        if not supported or tools.get("pacman") not in PACMAN_PATHS:
            state, detail = "blocked", "Environnement ou gestionnaire non pris en charge ; aucune installation proposée."
        steps.append(SetupStep("package:" + name, "Paquet " + name, state, detail))

    config = report.configuration.status
    config_state = "review" if config == "present" else "needed" if config == "missing" else "blocked"
    if config_state == "blocked":
        blockers.append("Présence ou accessibilité de la configuration Samba non déterminée.")
    steps.append(SetupStep("configuration", "Configuration Samba", config_state,
                           "Examiner les réglages existants, préparer un candidat, le contrôler et prévoir une sauvegarde avant toute écriture."
                           if config == "present" else
                           "Préparer une configuration de serveur domestique avec accès invité désactivé, puis la contrôler."
                           if config == "missing" else "Résoudre l’état inconnu de la configuration avant toute création ou remplacement."))
    steps.append(SetupStep("accounts", "Comptes, groupes et permissions", "review",
                           "Choisir les dossiers et les identités autorisées ; examiner les comptes Linux, Samba et les ACL avant de proposer des changements."))
    service = next((item for item in report.services if item.name == "smb.service"), None)
    if service and service.status == "observed" and service.unit_file_state.startswith("masked"):
        service_state = "blocked"
        blockers.append("Le service smb.service est masqué ; aucun démasquage automatique proposé.")
        service_detail = "Examiner la raison du masquage avant de proposer une intervention."
    elif service and service.status == "observed" and service.load_state == "loaded" and service.active_state == "active":
        service_state, service_detail = "retained", "Conserver le service actif ; ne pas le redémarrer pour la préparation de ce plan."
    elif service and service.status == "observed" and service.load_state == "loaded" and service.active_state == "inactive":
        service_state, service_detail = "needed", "Proposer un démarrage uniquement après configuration validée, droits vérifiés et autorisation."
    elif service and service.status == "missing" and package_map["samba"].status == "missing":
        service_state, service_detail = "after-packages", "Réexaminer le service après une future installation autorisée du paquet."
    else:
        service_state, service_detail = "blocked", "Diagnostiquer le service absent, en échec ou dans un état non déterminé."
        blockers.append("État du service smb.service à résoudre avant activation.")
    steps.append(SetupStep("smb-service", "Service de partage smb.service", service_state, service_detail))
    startup_enabled = service is not None and service.status == "observed" and service.unit_file_state == "enabled"
    steps.append(SetupStep("startup", "Démarrage automatique", "retained" if startup_enabled else "review",
                           "Conserver l’activation persistante existante."
                           if startup_enabled else
                           "Choisir séparément l’activation au démarrage de l’ordinateur ; un service actif n’est pas forcément activé au démarrage."))
    active_firewalls = tuple(item.name for item in report.services
                             if item.name in {"ufw.service", "firewalld.service", "nftables.service"}
                             and item.status == "observed" and item.active_state == "active")
    firewall_detail = ("Plusieurs services de pare-feu sont actifs : identifier le gestionnaire et les règles effectives. "
                       if len(active_firewalls) > 1 else "Identifier le gestionnaire et les règles effectives. ")
    steps.append(SetupStep("firewall", "Pare-feu et réseau autorisé", "review", firewall_detail
                           + "Choisir le réseau et les interfaces avant de proposer des ouvertures ; aucun pare-feu ne sera désactivé."))
    steps.append(SetupStep("client-test", "Vérification depuis un autre appareil", "review",
                           "Prévoir des essais avec un compte autorisé et un compte non autorisé, en lecture puis en écriture selon les droits choisis."))
    basis = json.dumps({"diagnostic": asdict(report), "packages": [asdict(package_map[name]) for name in PACKAGES]},
                       ensure_ascii=True, sort_keys=True).encode("utf-8")
    return InstallationPlan(1, report.mode, "blocked" if blockers else "review", report, packages,
                            tuple(steps), tuple(blockers), hashlib.sha256(basis).hexdigest(), (
                                "Plan descriptif uniquement : aucune commande d’installation ou de modification n’est exécutée.",
                                "Les dépendances, conflits, versions à installer et éventuelles mises à jour ne sont pas encore calculés.",
                                "Aucune base de dépôts n’est synchronisée et aucun paquet n’est téléchargé.",
                                "Les choix de comptes, dossiers, réseau et démarrage restent à confirmer ; aucune ouverture réseau implicite.",
                                "Toute future exécution devra relire l’état, détailler la transaction et obtenir une autorisation explicite pour les interventions proposées.",
                            ))


def collect_installation_plan(probe) -> InstallationPlan:
    report = collect(probe)
    pacman = next((tool.path for tool in report.tools if tool.name == "pacman"), None)
    if report.environment.system == "Linux" and report.environment.arch_based and pacman in PACMAN_PATHS:
        packages = tuple(probe.package(name) for name in PACKAGES)
    else:
        packages = tuple(Package(name, "unknown", detail="Requête non effectuée sur cet environnement.") for name in PACKAGES)
    return build_installation_plan(report, packages)


def format_installation(plan: InstallationPlan) -> str:
    def clean(value):
        return "".join(char if char.isprintable() else "?" for char in value)

    states = {"retained": "conserver", "needed": "à prévoir", "blocked": "bloqué",
              "review": "à examiner", "after-packages": "après les paquets",
              "installed": "installé", "missing": "absent", "unknown": "inconnu"}
    lines = ["SambaPilot — Préparation de l’installation, sans exécution",
             "DÉMONSTRATION — données fictives" if plan.mode == "demo" else "Constat local en lecture seule",
             "État : " + ("points bloquants à résoudre" if plan.status == "blocked" else "choix et interventions à examiner"),
             "Empreinte du constat : " + plan.basis_sha256, "", "Paquets"]
    lines.extend("  " + package.name + " : " + states[package.status]
                 + (" · " + clean(package.version) if package.version else "")
                 + (" — " + clean(package.detail) if package.detail else "") for package in plan.packages)
    lines += ["", "Étapes proposées"]
    for step in plan.steps:
        lines += ["  " + clean(step.title) + " — " + states[step.status], "    " + clean(step.detail)]
    if plan.blockers:
        lines += ["", "Points bloquants", *["  - " + item for item in plan.blockers]]
    lines += ["", *plan.notes]
    return "\n".join(lines)
