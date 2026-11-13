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
from .inspection import InspectionError, format_inspection, inspect_content, inspect_file
from .file_planning import FilePlanSession
from .report_export import ReportExportError, prepare_report, save_report
from .validation import format_validation, validate_plan
from .setup import DemoSetupProbe, HostSetupProbe, collect_installation_plan, format_installation
from .firewall import MANAGERS, FirewallIntent, FirewallPlanError, format_firewall, prepare_firewall
from .distributions import PROFILES
from .troubleshooting import SYMPTOMS, format_troubleshooting, troubleshoot
from .connection import ConnectionError, format_connection, prepare_connection, validate_server
from .share_profiles import SHARE_PROFILES, draft_from_profile
from .volumes import DemoVolumeProbe, VOLUME_SCENARIOS, VolumeError, collect_volume, format_volume
from .volume_system import HostVolumeProbe
from .share_diagnostic import ShareDiagnosticError, format_share_diagnostic, prepare_share_diagnostic


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
        "  Famille : " + env.distribution_family,
        "  Gestionnaire de paquets : " + (env.package_manager or "non déterminé"),
        "  Service Samba attendu : " + (env.samba_service or "non déterminé"),
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
    diagnostic.add_argument("--distribution", choices=tuple(PROFILES), help="Distribution fictive, uniquement avec --demo (défaut : arch).")
    diagnostic.add_argument("--json", action="store_true", help="Rapport structuré JSON, schéma version 2.")
    help_command = subcommands.add_parser("depannage", help="Expliquer les pistes d’un symptôme, sans intervention.")
    help_source = help_command.add_mutually_exclusive_group(required=True)
    help_source.add_argument("--demo", nargs="?", const="configured", choices=SCENARIOS)
    help_source.add_argument("--local", action="store_true", help="Demander explicitement un diagnostic local en lecture seule.")
    help_command.add_argument("--symptom", choices=tuple(SYMPTOMS), required=True)
    help_command.add_argument("--distribution", choices=tuple(PROFILES), help="Distribution fictive, uniquement avec --demo.")
    help_command.add_argument("--json", action="store_true")
    connection = subcommands.add_parser("fiche-connexion", help="Préparer les adresses et les instructions client sans connexion réseau.")
    connection_source = connection.add_mutually_exclusive_group(required=True)
    connection_source.add_argument("--demo", action="store_true", help="Partages fictifs uniquement.")
    connection_source.add_argument("--config", help="Fichier choisi, lu uniquement pour ses déclarations.")
    connection.add_argument("--share", required=True, help="Nom d’un partage présent dans la source choisie.")
    connection.add_argument("--server", required=True, help="Nom DNS ou IPv4 du serveur, sans URL ni identifiants.")
    connection.add_argument("--json", action="store_true", help="Fiche structurée ; accès réseau inconnu et can_apply faux.")
    share_diagnostic = subcommands.add_parser('diagnostic-partage', help='Regrouper les réglages, incertitudes, connexion et dépannage d’un partage.')
    share_source = share_diagnostic.add_mutually_exclusive_group(required=True)
    share_source.add_argument('--demo', action='store_true', help='Inventaire fictif, sans consultation de l’hôte.')
    share_source.add_argument('--config', help='Configuration choisie explicitement.')
    share_diagnostic.add_argument('--share', required=True)
    share_diagnostic.add_argument('--symptom', choices=tuple(SYMPTOMS), default='invisible')
    share_diagnostic.add_argument('--server', help='Nom DNS ou IPv4 fourni explicitement ; aucune connexion.')
    share_volume = share_diagnostic.add_mutually_exclusive_group()
    share_volume.add_argument('--demo-volume', choices=VOLUME_SCENARIOS, help='Exemple de volume, uniquement avec --demo.')
    share_volume.add_argument('--local-volume', action='store_true', help='Confirmer que le dossier du fichier appartient à cet ordinateur et demander son constat Linux.')
    share_diagnostic.add_argument('--mountpoint', help='Point de montage attendu, obligatoire pour examiner le volume.')
    share_diagnostic.add_argument('--json', action='store_true')
    volume = subcommands.add_parser("examiner-volume", help="Examiner le montage attendu d’un dossier, sans le monter ni activer de partage.")
    volume_source = volume.add_mutually_exclusive_group(required=True)
    volume_source.add_argument("--demo", nargs="?", const="mounted", choices=VOLUME_SCENARIOS, help="Constat fictif sans consultation de l’hôte.")
    volume_source.add_argument("--local", action="store_true", help="Demander explicitement une lecture locale Linux.")
    volume.add_argument("--path", required=True, help="Dossier Linux absolu choisi explicitement.")
    volume.add_argument("--mountpoint", required=True, help="Point de montage attendu, distinct de / ; aucune détection implicite.")
    volume.add_argument("--json", action="store_true", help="Constat structuré ; informations inconnues conservées en null.")
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
    plan.add_argument("--name", help="Nom du partage, obligatoire sauf création avec --profile.")
    plan.add_argument("--profile", choices=tuple(profile.key for profile in SHARE_PROFILES),
                      help="Préremplir une création : personal, family ou media ; comptes et groupes à choisir explicitement.")
    plan.add_argument("--path", help="Chemin Linux absolu du dossier.")
    plan.add_argument("--user", action="append", default=[], help="Utilisateur autorisé ; option répétable.")
    plan.add_argument("--group", action="append", default=[], help="Groupe autorisé ; option répétable, sans @.")
    plan_access = plan.add_mutually_exclusive_group()
    plan_access.add_argument("--writable", action="store_true", default=None, help="Proposer la lecture et l’écriture.")
    plan_access.add_argument("--read-only", dest="writable", action="store_false", help="Proposer la lecture seule, y compris avec un profil.")
    plan_visibility = plan.add_mutually_exclusive_group()
    plan_visibility.add_argument("--hidden", action="store_true", default=None, help="Masquer le partage dans la liste.")
    plan_visibility.add_argument("--visible", dest="hidden", action="store_false", help="Afficher le partage, y compris avec un profil.")
    plan.add_argument("--json", action="store_true", help="Plan JSON avec configuration candidate et comparaison.")
    plan.add_argument("--validate", action="store_true", help="Contrôler explicitement une copie temporaire avec testparm déjà installé.")
    inspection = subcommands.add_parser("examiner-config", help="Lire un fichier explicitement choisi, sans le modifier.")
    inspection.add_argument("--config", required=True, help="Chemin d’un fichier régulier UTF-8 (1 Mio maximum).")
    inspection_format = inspection.add_mutually_exclusive_group()
    inspection_format.add_argument("--json", action="store_true", help="Déclarations locales structurées, sans valeurs d’options inconnues.")
    inspection_format.add_argument("--markdown", action="store_true", help="Aperçu Markdown avec chemins et identifiants ; aucun enregistrement.")
    inspection_format.add_argument("--export", metavar="RAPPORT.md", help="Créer un rapport Markdown sans écraser de fichier ; exige --confirm-export.")
    inspection.add_argument("--confirm-export", action="store_true", help="Confirmer l’enregistrement avec chemins et identifiants déclarés.")
    setup = subcommands.add_parser("preparer-installation", help="Décrire les interventions nécessaires, sans les exécuter.")
    setup_source = setup.add_mutually_exclusive_group(required=True)
    setup_source.add_argument("--demo", nargs="?", const="fresh", choices=SCENARIOS, help="Données fictives (défaut : fresh).")
    setup_source.add_argument("--local", action="store_true", help="Consulter l’hôte et la base locale des paquets en lecture seule.")
    setup.add_argument("--json", action="store_true", help="Plan descriptif structuré JSON.")
    setup.add_argument("--distribution", choices=tuple(PROFILES), help="Distribution fictive, uniquement avec --demo (défaut : arch).")
    firewall = subcommands.add_parser("plan-pare-feu", help="Décrire un périmètre réseau choisi, sans consulter ni modifier le pare-feu.")
    firewall.add_argument("--manager", choices=MANAGERS, required=True)
    firewall.add_argument("--interface", required=True, help="Interface d’entrée explicitement choisie.")
    firewall.add_argument("--source", action="append", required=True, help="Source CIDR ; option répétable.")
    firewall.add_argument("--zone", help="Zone obligatoire pour firewalld uniquement.")
    firewall.add_argument("--legacy-netbios", action="store_true", help="Proposer aussi TCP 139 et UDP 137/138 pour les sources IPv4.")
    firewall.add_argument("--json", action="store_true", help="Intentions structurées JSON, sans commandes natives.")
    args = parser.parse_args(argv)
    if getattr(args, "distribution", None) is not None and not args.demo:
        parser.error("--distribution choisit uniquement une distribution fictive avec --demo ; l’hôte est détecté automatiquement.")
    if args.command == 'diagnostic-partage':
        if args.demo_volume and not args.demo:
            parser.error('--demo-volume exige --demo ; aucune simulation de volume ne sera jointe à un fichier réel.')
        if args.local_volume and not args.config:
            parser.error('--local-volume exige un fichier choisi ; ne pas consulter l’hôte depuis les exemples.')
        if bool(args.mountpoint) != bool(args.demo_volume or args.local_volume):
            parser.error('Fournir --mountpoint avec --demo-volume ou --local-volume, ensemble uniquement.')
        try:
            server = validate_server(args.server) if args.server is not None else None
            source = (inspect_content(demo_configuration(), 'Exemple fictif en mémoire', 'demo')
                      if args.demo else inspect_file(args.config))
            result = prepare_share_diagnostic(source, args.share, args.symptom, server)
            if args.demo_volume or args.local_volume:
                if result.share.path is None:
                    raise ShareDiagnosticError('Le chemin déclaré du partage est inconnu ; aucun volume ne peut être examiné.')
                volume = collect_volume(result.share.path, args.mountpoint,
                                         DemoVolumeProbe(args.demo_volume, args.mountpoint) if args.demo_volume else HostVolumeProbe())
                if args.config and inspect_file(args.config).sha256 != source.sha256:
                    raise ShareDiagnosticError('La configuration a changé pendant le constat ; recharger sa déclaration.')
                result = prepare_share_diagnostic(source, args.share, args.symptom, server, volume)
        except (InspectionError, ShareDiagnosticError, ConnectionError, VolumeError) as error:
            parser.error(str(error))
        print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2) if args.json else format_share_diagnostic(result))
        return 0
    if args.command == "examiner-volume":
        try:
            report = collect_volume(args.path, args.mountpoint,
                                    DemoVolumeProbe(args.demo, args.mountpoint) if args.demo else HostVolumeProbe())
        except VolumeError as error:
            parser.error(str(error))
        print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2) if args.json else format_volume(report))
        return 0 if args.demo or report.basis_sha256 is not None else 2
    if args.command == "fiche-connexion":
        try:
            server = validate_server(args.server)
            report = (inspect_content(demo_configuration(), "Exemple fictif en mémoire", "demo")
                      if args.demo else inspect_file(args.config))
            card = prepare_connection(report, args.share, server)
        except (ConnectionError, InspectionError) as error:
            parser.error(str(error))
        print(json.dumps(card.to_dict(), ensure_ascii=True, indent=2) if args.json else format_connection(card))
        return 0
    if args.command == "depannage":
        report = collect(DemoProbe(args.demo, args.distribution or "arch") if args.demo else HostProbe())
        result = troubleshoot(report, args.symptom)
        print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2) if args.json else format_troubleshooting(result))
        return 0 if report.environment.system == "Linux" else 2
    if args.command == "plan-pare-feu":
        try:
            firewall_plan = prepare_firewall(FirewallIntent(args.manager, args.interface, tuple(args.source),
                                                           args.zone, args.legacy_netbios))
        except FirewallPlanError as error:
            parser.error(str(error))
        print(json.dumps(firewall_plan.to_dict(), ensure_ascii=True, indent=2) if args.json else format_firewall(firewall_plan))
        return 0
    if args.command == "preparer-installation":
        setup_plan = collect_installation_plan(DemoSetupProbe(args.demo, args.distribution or "arch") if args.demo else HostSetupProbe())
        print(json.dumps(setup_plan.to_dict(), ensure_ascii=True, indent=2) if args.json else format_installation(setup_plan))
        return 2 if setup_plan.status == "blocked" else 0
    if args.command == "examiner-config":
        if (args.export is not None) != args.confirm_export:
            parser.error("--export et --confirm-export sont requis ensemble. Consultez d’abord l’aperçu avec --markdown.")
        try:
            report = inspect_file(args.config)
        except InspectionError as error:
            parser.error(str(error))
        if args.markdown or args.export is not None:
            try:
                prepared = prepare_report(report)
                if args.export is not None:
                    output = save_report(prepared, args.export)
                    print("Rapport Markdown enregistré : " + safe_text(str(output)))
                else:
                    print(prepared.markdown, end="")
            except ReportExportError as error:
                parser.error(str(error))
        else:
            print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2) if args.json else format_inspection(report))
        return 2 if report.status == "blocked" else 0
    if args.command == "plan-partage":
        try:
            if args.profile and args.action != "create":
                raise PlanError("Les profils sont réservés aux créations ; examiner les réglages existants pour modifier ou retirer un partage.")
            if not args.profile and not args.name:
                raise PlanError("Indiquer --name ou choisir --profile pour une création.")
            if args.action == "remove":
                if args.path is not None or args.user or args.group or args.writable is not None or args.hidden is not None:
                    raise PlanError("Le retrait accepte uniquement le nom, sans nouveaux réglages.")
                draft = None
            elif args.profile:
                draft = draft_from_profile(args.profile, args.name or "", args.path or "", tuple(args.user), tuple(args.group),
                                           None if args.writable is None else not args.writable,
                                           None if args.hidden is None else not args.hidden)
                args.name = draft.name
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
        if args.profile:
            data["profile"] = args.profile
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
    probe = DemoProbe(args.demo, args.distribution or "arch") if args.demo else HostProbe()
    report = collect(probe)
    print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2) if args.json else render(report))
    return 0 if report.environment.system == "Linux" else 2
