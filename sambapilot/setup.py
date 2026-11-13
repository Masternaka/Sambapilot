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
from .distributions import PROFILES


QUERY_PATHS = {profile.query_tool: tuple(directory + profile.query_tool for directory in ("/usr/bin/", "/usr/sbin/"))
               for profile in PROFILES.values()}



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
    tool = next((tool for tool, paths in QUERY_PATHS.items() if executable in paths), None)
    profile = next((profile for profile in PROFILES.values() if profile.query_tool == tool), None)
    if profile is None or name not in profile.packages:
        raise ValueError("Requête de paquet hors du périmètre autorisé.")
    if tool == "pacman":
        command = (executable, "--query", "--", name)
    elif tool == "dpkg-query":
        command = (executable, "--show", "--showformat=${Package}\t${Status}\t${Version}\n", "--", name)
    else:
        command = (executable, "--query", "--queryformat", "%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\n", "--", name)
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", timeout=3, shell=False, check=False,
            env={"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return Package(name, "unknown", detail="Base locale des paquets non consultable.")
    output, error = result.stdout.rstrip("\r\n"), result.stderr.strip()
    version = None
    missing = False
    # Ne jamais déduire l'absence du seul code de sortie ou d'une sortie vide.
    if tool == "pacman":
        fields = output.split()
        if result.returncode == 0 and not error and len(fields) == 2 and fields[0] == name:
            version = fields[1]
        missing = (result.returncode == 1 and not output
                   and error == "error: package '" + name + "' was not found")
    elif tool == "dpkg-query":
        fields = output.split("\t")
        if result.returncode == 0 and not error and len(fields) == 3 and fields[0] == name:
            status = fields[1].split()
            if len(status) == 3 and status[1] == "ok":
                if status[2] == "installed":
                    version = fields[2]
                elif status[2] in {"config-files", "not-installed"}:
                    missing = True
        missing = missing or (result.returncode == 1 and not output
                              and error == "dpkg-query: no packages found matching " + name)
    else:
        fields = output.split("\t")
        if result.returncode == 0 and not error and len(fields) == 2 and fields[0] == name:
            version = fields[1]
        missing = (result.returncode == 1 and not error and output == "package " + name + " is not installed")
    if version and re.fullmatch(r"[A-Za-z0-9_.+:~\-]+", version):
        return Package(name, "installed", version, "Paquet déclaré installé par la base locale.")
    if missing:
        return Package(name, "missing", detail="Paquet explicitement non installé dans la base locale.")
    return Package(name, "unknown", detail="Réponse de la base locale ambiguë ou en erreur ; absence non déduite.")


class HostSetupProbe(HostProbe):
    def package(self, name: str, family: str = "arch") -> Package:
        profile = PROFILES.get(family)
        if profile is None or name not in profile.packages:
            raise ValueError("Paquet hors du périmètre autorisé.")
        executable = self.tool(profile.query_tool)
        return (query_package(name, executable) if executable in QUERY_PATHS[profile.query_tool]
                else Package(name, "unknown", detail="Outil système de consultation non détecté."))


class DemoSetupProbe(DemoProbe):
    def package(self, name: str, family: str = "arch") -> Package:
        if name not in self.profile.packages or family != self.profile.key:
            raise ValueError("Paquet hors du périmètre autorisé.")
        if self.scenario == "restricted":
            return Package(name, "unknown", detail="Base locale fictive inaccessible.")
        if self.scenario == "fresh":
            return Package(name, "missing", detail="Paquet fictif absent.")
        return Package(name, "installed", "exemple", "Version fictive, sans lien avec une version publiée.")


def build_installation_plan(report: Report, packages: Tuple[Package, ...]) -> InstallationPlan:
    profile = PROFILES.get(report.environment.distribution_family)
    expected_packages = profile.packages if profile else ()
    if (len(packages) != len(expected_packages) or {package.name for package in packages} != set(expected_packages)
            or any(package.status not in {"installed", "missing", "unknown"} for package in packages)):
        raise ValueError("Les états des paquets attendus doivent être uniques et explicites.")
    tools = {tool.name: tool.path for tool in report.tools}
    package_map = {package.name: package for package in packages}
    steps = []
    blockers = []
    supported = report.environment.system == "Linux" and profile is not None
    query_available = profile is not None and tools.get(profile.query_tool) in QUERY_PATHS[profile.query_tool]
    if not supported:
        blockers.append("La cible doit être Arch, Debian ou Fedora sous Linux ; aucune installation proposée pour ce système.")
    if not query_available:
        blockers.append("L’outil système de consultation des paquets n’est pas disponible.")
    if not tools.get("systemctl"):
        blockers.append("systemctl n’est pas détecté ; la gestion des services doit être examinée.")
    for name, expected in (profile.package_tools if profile else ()):
        package = package_map[name]
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
        if not supported or not query_available:
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
    service_name = profile.services[0] if profile else "non déterminé"
    service = next((item for item in report.services if item.name == service_name), None)
    if service and service.status == "observed" and service.unit_file_state.startswith("masked"):
        service_state = "blocked"
        blockers.append("Le service " + service_name + " est masqué ; aucun démasquage automatique proposé.")
        service_detail = "Examiner la raison du masquage avant de proposer une intervention."
    elif service and service.status == "observed" and service.load_state == "loaded" and service.active_state == "active":
        service_state, service_detail = "retained", "Conserver le service actif ; ne pas le redémarrer pour la préparation de ce plan."
    elif service and service.status == "observed" and service.load_state == "loaded" and service.active_state == "inactive":
        service_state, service_detail = "needed", "Proposer un démarrage uniquement après configuration validée, droits vérifiés et autorisation."
    elif service and service.status == "missing" and package_map.get("samba", Package("samba", "unknown")).status == "missing":
        service_state, service_detail = "after-packages", "Réexaminer le service après une future installation autorisée du paquet."
    else:
        service_state, service_detail = "blocked", "Diagnostiquer le service absent, en échec ou dans un état non déterminé."
        blockers.append("État du service " + service_name + " à résoudre avant activation.")
    steps.append(SetupStep("smb-service", "Service de partage " + service_name, service_state, service_detail))
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
    basis = json.dumps({"diagnostic": asdict(report), "packages": [asdict(package_map[name]) for name in expected_packages]},
                       ensure_ascii=True, sort_keys=True).encode("utf-8")
    return InstallationPlan(2, report.mode, "blocked" if blockers else "review", report, packages,
                            tuple(steps), tuple(blockers), hashlib.sha256(basis).hexdigest(), (
                                "Plan descriptif uniquement : aucune commande d’installation ou de modification n’est exécutée.",
                                "Les dépendances, conflits, versions à installer et éventuelles mises à jour ne sont pas encore calculés.",
                                "Aucune base de dépôts n’est synchronisée et aucun paquet n’est téléchargé.",
                                "Les choix de comptes, dossiers, réseau et démarrage restent à confirmer ; aucune ouverture réseau implicite.",
                                "Toute future exécution devra relire l’état, détailler la transaction et obtenir une autorisation explicite pour les interventions proposées.",
                            ))


def collect_installation_plan(probe) -> InstallationPlan:
    report = collect(probe)
    profile = PROFILES.get(report.environment.distribution_family)
    tools = {tool.name: tool.path for tool in report.tools}
    if (report.environment.system == "Linux" and profile is not None
            and tools.get(profile.query_tool) in QUERY_PATHS[profile.query_tool]):
        packages = tuple(probe.package(name, profile.key) for name in profile.packages)
    else:
        packages = tuple(Package(name, "unknown", detail="Requête non effectuée sur cet environnement.")
                         for name in (profile.packages if profile else ()))
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
