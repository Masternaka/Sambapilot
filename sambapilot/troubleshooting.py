"""Pistes de dépannage issues d'un constat, sans sonde ni modification supplémentaire."""

from dataclasses import asdict, dataclass
from typing import Tuple

from .diagnostic import Report


SYMPTOMS = {"invisible": "Le partage n’apparaît pas",
            "denied": "L’accès est refusé",
            "readonly": "Impossible d’écrire"}


@dataclass(frozen=True)
class Finding:
    key: str
    status: str
    observation: str
    next_step: str


@dataclass(frozen=True)
class TroubleshootingReport:
    schema_version: int
    mode: str
    symptom: str
    diagnostic: Report
    findings: Tuple[Finding, ...]
    can_apply: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def troubleshoot(report: Report, symptom: str) -> TroubleshootingReport:
    if symptom not in SYMPTOMS:
        raise ValueError("Symptôme inconnu.")
    findings = []
    if report.environment.system != "Linux":
        findings.append(Finding("platform", "unknown", "Le diagnostic local exige Linux.",
                                "Utiliser Arch, Debian ou Fedora ; les exemples restent disponibles sur les autres systèmes."))
        return TroubleshootingReport(1, report.mode, symptom, report, tuple(findings))
    tools = {tool.name: tool.path for tool in report.tools}
    findings.append(Finding("server", "observed" if tools.get("smbd") else "unknown",
                            "Exécutable smbd détecté." if tools.get("smbd") else "Exécutable smbd non détecté dans les chemins système.",
                            "Consulter le plan de préparation pour connaître l’état du paquet ; la détection d’un outil ne prouve pas le fonctionnement du serveur."))
    service_name = report.environment.samba_service
    service = next((item for item in report.services if item.name == service_name), None)
    if service is None or service.status == "unknown":
        status, observation = "unknown", "État du service Samba non déterminé."
    elif service.status == "missing":
        status, observation = "attention", "Unité " + service.name + " introuvable."
    elif service.unit_file_state.startswith("masked"):
        status, observation = "attention", "Le service " + service.name + " est masqué."
    elif service.active_state == "active":
        status, observation = "observed", "Le service " + service.name + " est actif ; cela ne prouve pas un accès client."
    else:
        status, observation = "attention", "Service " + service.name + " : " + service.active_state + "."
    findings.append(Finding("service", status, observation,
                            "Examiner l’état du service et sa configuration avant de proposer un démarrage ou un redémarrage."))
    config = report.configuration
    findings.append(Finding("configuration", "attention" if config.status == "missing" else "observed" if config.status == "present" else "unknown",
                            "Configuration Samba : " + config.detail,
                            "Choisir explicitement le fichier dans l’examen de configuration ; son contenu n’a pas été lu par ce diagnostic."))
    if symptom == "invisible":
        findings.append(Finding("discovery", "unknown", "Découverte réseau et visibilité du partage non vérifiées.",
                                "Essayer une connexion directe avec une adresse de serveur connue, puis examiner le nom du partage et le réglage browseable dans le fichier choisi."))
    else:
        findings.append(Finding("identity", "unknown", "Authentification et droits du compte non vérifiés.",
                                "Vérifier le compte utilisé par le client, les restrictions Samba et les groupes autorisés ; aucun mot de passe n’est demandé ici."))
    if symptom == "readonly":
        findings.append(Finding("write", "unknown", "Droits d’écriture, ACL et état du volume non vérifiés.",
                                "Comparer read only et write list aux permissions Linux et à la traversée des dossiers parents ; vérifier aussi si le volume est monté en lecture seule."))
    findings.append(Finding("network", "unknown", "Règles effectives du pare-feu et connexion réseau non testées.",
                            "Vérifier le chemin réseau depuis un appareil client autorisé et examiner les restrictions existantes ; aucun port n’est ouvert par cet assistant."))
    findings.append(Finding("security", "unknown", "Contrôles SELinux/AppArmor non examinés.",
                            "Examiner les refus et les politiques applicables si les autres contrôles ne suffisent pas ; ne pas désactiver ces protections pour contourner un refus."))
    return TroubleshootingReport(1, report.mode, symptom, report, tuple(findings))


def format_troubleshooting(report: TroubleshootingReport) -> str:
    def clean(value):
        return "".join(char if char.isprintable() else "?" for char in value)
    lines = ["SambaPilot — Assistant de dépannage", SYMPTOMS[report.symptom],
             "DÉMONSTRATION — données fictives" if report.mode == "demo" else "Constat local en lecture seule",
             "Pistes à vérifier : aucune cause certifiée, aucun accès réseau testé, aucun changement appliqué."]
    states = {"observed": "constaté", "attention": "à examiner", "unknown": "non vérifié"}
    for finding in report.findings:
        lines.extend(("", "[" + states[finding.status] + "] " + clean(finding.observation),
                      "  Suite : " + clean(finding.next_step)))
    return "\n".join(lines)
