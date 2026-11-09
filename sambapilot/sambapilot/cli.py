"""Interface terminal ; l'affichage consomme le rapport du moteur commun."""

import argparse
import json
from typing import Optional, Sequence

from . import __version__
from .access import AccessReport, Right
from .demo import DemoProbe, SCENARIOS, access_demo, demo_configuration
from .planning import ACTIONS, PlanError, ShareDraft, format_plan, prepare_plan
from .diagnostic import Report, collect
from .system import HostProbe
from .inspection import InspectionError, format_inspection, inspect_file
from .file_planning import FilePlanSession
from .validation import format_validation, validate_plan
from .setup import DemoSetupProbe, HostSetupProbe, collect_installation_plan, format_installation
from .firewall import MANAGERS, FirewallIntent, FirewallPlanError, format_firewall, prepare_firewall


STATUS = {"present": "présent", "missing": "absent", "unknown": "inconnu",
          "not-checked": "non vérifié", "observed": "consulté"}


def safe_text(value: str) -> str:
    """Empêcher les données d'un système d'injecter des contrôles de terminal."""
    return "".join(char if char.isprintable() else "?" for char in value)


def render(report: Report) -> str:
    env = report.environment
    lines = [
        "SambaPilot — diagnostic en lecture seule",
        "Mode : " + ("DÉMONSTRATION — données fictives" if report.mode == "demo" else "machine locale"),
        "", "Environnement",
        "  Système : " + safe_text(env.system),
        "  Distribution : " + safe_text(env.distribution_name),
        "  Base Arch identifiée : " + ("oui" if env.arch_based else "non / inconnue"),
        "  Indice Omarchy : " + STATUS[env.omarchy_marker.status],
        "", "Configuration /etc/samba/smb.conf",
        "  " + STATUS[report.configuration.status] + " — " + report.configuration.detail,
    ]
    if report.tools:
        lines += ["", "Outils système (présence uniquement)"]
        for tool in report.tools:
            lines.append("  " + tool.name + " : " + (tool.path or "non détecté dans /usr/bin et /usr/sbin"))
    if report.services:
        lines += ["", "Services systemd (état brut)"]
        for service in report.services:
            detail = ("chargement=" + service.load_state + ", activité=" + service.active_state
                      + ", activation=" + service.unit_file_state)
            if service.detail:
                detail += " — " + service.detail
            lines.append("  " + service.name + " : " + STATUS[service.status] + " ; " + safe_text(detail))
    lines += ["", "Limites et remarques"] + ["  - " + safe_text(note) for note in report.notes]
    return "\n".join(lines)


def right_label(right: Right) -> str:
    return "oui" if right is True else "non" if right is False else "inconnu"


def render_access(report: AccessReport) -> str:
    lines = ["SambaPilot — Qui peut accéder à quoi ?",
             "Mode : " + ("DÉMONSTRATION — données fictives" if report.mode == "demo"
                           else "données déclarées"),
             "Estimation des droits déclarés, sans test d'accès réel.", ""]
    rows = [("Utilisateur", "Partage", "Lecture estimée", "Écriture estimée")]
    rows.extend((safe_text(item.user), safe_text(item.share), right_label(item.read),
                 right_label(item.write)) for item in report.decisions)
    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    for index, row in enumerate(rows):
        lines.append(" | ".join(value.ljust(widths[column]) for column, value in enumerate(row)))
        if index == 0:
            lines.append("-+-".join("-" * width for width in widths))
    lines += ["", "Explications par compte et partage"]
    for item in report.decisions:
        lines.append("  " + safe_text(item.user) + " / " + safe_text(item.share)
                     + " — " + safe_text(item.path))
        lines.append("    Samba : lecture=" + right_label(item.samba_read)
                     + ", écriture=" + right_label(item.samba_write)
                     + " ; fichiers : lecture=" + right_label(item.filesystem_read)
                     + ", écriture=" + right_label(item.filesystem_write))
        lines.extend("    " + safe_text(reason) for reason in (*item.reasons, *item.conflicts))
    lines += ["", "Limites"] + ["  - " + safe_text(note) for note in report.notes]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sambapilot", description="Gestion Samba — premier socle de diagnostic en lecture seule.")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    diagnostic = subcommands.add_parser("diagnostic", help="Examiner l'environnement sans le modifier.")
    diagnostic.add_argument("--demo", nargs="?", const="configured", choices=SCENARIOS,
                            help="Données fictives, sans consulter le système (défaut : configured).")
    diagnostic.add_argument("--json", action="store_true", help="Rapport structuré JSON, schéma version 1.")
    permissions = subcommands.add_parser("permissions", help="Afficher la matrice des accès déclarés.")
    permissions.add_argument("--demo", action="store_true", required=True,
                             help="Données fictives uniquement ; collecte réelle non implémentée.")
    permissions.add_argument("--json", action="store_true", help="Matrice structurée JSON, schéma version 1.")
    gui = subcommands.add_parser("gui", help="Ouvrir l’interface graphique GTK 4 de démonstration.")
    gui.add_argument("--demo", action="store_true", required=True,
                     help="Exemples fictifs et lecture de fichier sur choix explicite, sans modification.")
    plan = subcommands.add_parser("plan-partage", help="Préparer un changement de partage sans l’appliquer.")
    plan_source = plan.add_mutually_exclusive_group(required=True)
    plan_source.add_argument("--demo", action="store_true", help="Configuration fictive.")
    plan_source.add_argument("--config", help="Fichier choisi : aperçu en mémoire, sans enregistrement.")
    plan.add_argument("--action", choices=ACTIONS, required=True)
    plan.add_argument("--name", required=True, help="Nom du partage.")
    plan.add_argument("--path", help="Chemin Linux absolu du dossier.")
    plan.add_argument("--user", action="append", default=[], help="Utilisateur autorisé ; option répétable.")
    plan.add_argument("--group", action="append", default=[], help="Groupe autorisé ; option répétable, sans @.")
    plan.add_argument("--writable", action="store_true", help="Proposer la lecture et l’écriture.")
    plan.add_argument("--hidden", action="store_true", help="Masquer le partage dans la liste.")
    plan.add_argument("--json", action="store_true", help="Plan JSON avec configuration candidate et comparaison.")
    plan.add_argument("--validate", action="store_true", help="Contrôler explicitement une copie temporaire avec testparm déjà installé.")
    inspection = subcommands.add_parser("examiner-config", help="Lire un fichier explicitement choisi, sans le modifier.")
    inspection.add_argument("--config", required=True, help="Chemin d’un fichier régulier UTF-8 (1 Mio maximum).")
    inspection.add_argument("--json", action="store_true", help="Déclarations locales structurées, sans valeurs d’options inconnues.")
    setup = subcommands.add_parser("preparer-installation", help="Décrire les interventions nécessaires, sans les exécuter.")
    setup_source = setup.add_mutually_exclusive_group(required=True)
    setup_source.add_argument("--demo", nargs="?", const="fresh", choices=SCENARIOS, help="Données fictives (défaut : fresh).")
    setup_source.add_argument("--local", action="store_true", help="Consulter l’hôte et la base locale des paquets en lecture seule.")
    setup.add_argument("--json", action="store_true", help="Plan descriptif structuré JSON.")
    firewall = subcommands.add_parser("plan-pare-feu", help="Décrire un périmètre réseau choisi, sans consulter ni modifier le pare-feu.")
    firewall.add_argument("--manager", choices=MANAGERS, required=True)
    firewall.add_argument("--interface", required=True, help="Interface d’entrée explicitement choisie.")
    firewall.add_argument("--source", action="append", required=True, help="Source CIDR ; option répétable.")
    firewall.add_argument("--zone", help="Zone obligatoire pour firewalld uniquement.")
    firewall.add_argument("--legacy-netbios", action="store_true", help="Proposer aussi TCP 139 et UDP 137/138 pour les sources IPv4.")
    firewall.add_argument("--json", action="store_true", help="Intentions structurées JSON, sans commandes natives.")
    args = parser.parse_args(argv)
    if args.command == "plan-pare-feu":
        try:
            firewall_plan = prepare_firewall(FirewallIntent(args.manager, args.interface, tuple(args.source),
                                                           args.zone, args.legacy_netbios))
        except FirewallPlanError as error:
            parser.error(str(error))
        print(json.dumps(firewall_plan.to_dict(), ensure_ascii=True, indent=2) if args.json else format_firewall(firewall_plan))
        return 0
    if args.command == "preparer-installation":
        setup_plan = collect_installation_plan(DemoSetupProbe(args.demo) if args.demo else HostSetupProbe())
        print(json.dumps(setup_plan.to_dict(), ensure_ascii=True, indent=2) if args.json else format_installation(setup_plan))
        return 2 if setup_plan.status == "blocked" else 0
    if args.command == "examiner-config":
        try:
            report = inspect_file(args.config)
        except InspectionError as error:
            parser.error(str(error))
        print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2) if args.json else format_inspection(report))
        return 2 if report.status == "blocked" else 0
    if args.command == "plan-partage":
        try:
            if args.action == "remove":
                if args.path is not None or args.user or args.group or args.writable or args.hidden:
                    raise PlanError("Le retrait accepte uniquement le nom, sans nouveaux réglages.")
                draft = None
            else:
                draft = ShareDraft(args.name, args.path or "", tuple(args.user), tuple(args.group),
                                   not args.writable, not args.hidden)
            if args.config:
                proposal = FilePlanSession.open(args.config).preview(args.action, args.name, draft)
            else:
                proposal = prepare_plan(demo_configuration(), args.action, args.name, draft, mode="demo")
        except (PlanError, InspectionError) as error:
            parser.error(str(error))
        validation = validate_plan(proposal) if args.validate else None
        data = proposal.to_dict()
        if validation is not None:
            data["validation"] = validation.to_dict()
        print(json.dumps(data, ensure_ascii=True, indent=2) if args.json else format_plan(proposal)
              + ("\n\n" + format_validation(validation) if validation is not None else ""))
        return 4 if validation is not None and validation.status != "accepted" else 0
    if args.command == "gui":
        from .gui import launch_demo
        return launch_demo()
    if args.command == "permissions":
        matrix = access_demo()
        print(json.dumps(matrix.to_dict(), ensure_ascii=True, indent=2) if args.json else render_access(matrix))
        return 0
    probe = DemoProbe(args.demo) if args.demo else HostProbe()
    report = collect(probe)
    print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2) if args.json else render(report))
    return 0 if report.environment.system == "Linux" else 2
