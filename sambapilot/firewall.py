"""Intentions de règles SMB déclarées, sans lecture ni modification du pare-feu."""

from dataclasses import asdict, dataclass
import hashlib
import ipaddress
import json
import re
from typing import Optional, Tuple


MANAGERS = ("ufw", "firewalld", "nftables")
INTERFACE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,14}\Z")
ZONE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,16}\Z")
EXCLUDED = {
    4: tuple(ipaddress.ip_network(value) for value in
             ("0.0.0.0/8", "127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4", "240.0.0.0/4")),
    6: tuple(ipaddress.ip_network(value) for value in
             ("::/128", "::1/128", "::ffff:0:0/96", "fe80::/10", "ff00::/8")),
}


class FirewallPlanError(ValueError):
    pass


@dataclass(frozen=True)
class FirewallIntent:
    manager: str
    interface: str
    sources: Tuple[str, ...]
    zone: Optional[str] = None
    legacy_netbios: bool = False


@dataclass(frozen=True)
class FirewallRule:
    identifier: str
    family: str
    source: str
    interface: str
    protocol: str
    destination_port: int
    zone: Optional[str]
    direction: str = "incoming"
    decision: str = "allow"


@dataclass(frozen=True)
class FirewallPlan:
    schema_version: int
    mode: str
    intent: FirewallIntent
    rules: Tuple[FirewallRule, ...]
    sha256: str
    requirements: Tuple[str, ...]
    notes: Tuple[str, ...]
    existing_rules_checked: bool = False
    can_apply: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def parse_sources(text: str) -> Tuple[str, ...]:
    values = tuple(value.strip() for value in text.split(","))
    if any(not value for value in values):
        raise FirewallPlanError("Indiquer les réseaux en notation CIDR, séparés par des virgules sans élément vide.")
    return values


def prepare_firewall(intent: FirewallIntent) -> FirewallPlan:
    if intent.manager not in MANAGERS:
        raise FirewallPlanError("Choisir explicitement UFW, firewalld ou nftables ; aucun gestionnaire n’est déduit.")
    if not INTERFACE.fullmatch(intent.interface):
        raise FirewallPlanError("Indiquer une interface explicite, de 1 à 15 caractères simples, sans espace ni joker.")
    if intent.manager == "firewalld":
        if intent.zone is None or not ZONE.fullmatch(intent.zone):
            raise FirewallPlanError("Indiquer une zone firewalld explicite de 1 à 17 caractères simples.")
    elif intent.zone is not None:
        raise FirewallPlanError("La zone est réservée à firewalld ; elle ne peut pas être ignorée pour un autre gestionnaire.")
    if type(intent.legacy_netbios) is not bool:
        raise FirewallPlanError("Le choix NetBIOS doit être un booléen explicite.")
    if not intent.sources or len(intent.sources) > 16:
        raise FirewallPlanError("Indiquer entre 1 et 16 réseaux sources explicites.")
    networks = []
    for value in intent.sources:
        if value != value.strip() or value.count("/") != 1 or "%" in value:
            raise FirewallPlanError("Chaque source doit être un réseau CIDR explicite, sans portée '%' ni espace superflu.")
        if not value.split("/", 1)[1].isascii() or not value.split("/", 1)[1].isdigit():
            raise FirewallPlanError("Le préfixe CIDR doit être une longueur numérique.")
        try:
            network = ipaddress.ip_network(value, strict=True)
        except ValueError as error:
            raise FirewallPlanError("Source CIDR invalide ou avec bits d’hôte : indiquer le réseau exact, ou /32 et /128 pour un appareil.") from error
        if network.prefixlen == 0 or any(network.overlaps(excluded) for excluded in EXCLUDED[network.version]):
            raise FirewallPlanError("Ce réseau recouvre une plage hors périmètre : toutes adresses, boucle locale, lien local, multicast ou adresse spéciale.")
        if any(network.version == other.version and network.overlaps(other) for other in networks):
            raise FirewallPlanError("Des réseaux sources se répètent ou se chevauchent ; préciser un périmètre sans doublon.")
        networks.append(network)
    networks.sort(key=lambda network: (network.version, int(network.network_address), network.prefixlen))
    if intent.legacy_netbios and not any(network.version == 4 for network in networks):
        raise FirewallPlanError("L’option NetBIOS de cette version nécessite au moins une source IPv4.")
    normalized = FirewallIntent(intent.manager, intent.interface, tuple(str(network) for network in networks),
                                intent.zone, intent.legacy_netbios)
    rules = []
    for network in networks:
        ports = (("tcp", 445),)
        if intent.legacy_netbios and network.version == 4:
            ports += (("tcp", 139), ("udp", 137), ("udp", 138))
        for protocol, port in ports:
            basis = json.dumps([intent.manager, intent.interface, intent.zone, str(network), protocol, port],
                               sort_keys=True).encode("utf-8")
            rules.append(FirewallRule("sambapilot-" + hashlib.sha256(basis).hexdigest()[:16],
                                      "ipv4" if network.version == 4 else "ipv6", str(network),
                                      intent.interface, protocol, port, intent.zone))
    requirements = (
        "Confirmer le gestionnaire réellement utilisé et examiner toutes les règles effectives et leur ordre.",
        "Vérifier l’existence de l’interface et que les réseaux choisis correspondent aux appareils autorisés.",
        "Vérifier les ports et transports réellement configurés dans Samba.",
        "Choisir la persistance et prévoir l’identification ainsi que le retrait des seules règles ajoutées.",
        "Présenter la traduction propre au gestionnaire, sauvegarder les réglages et obtenir l’autorisation avant toute application.",
    )
    if intent.manager == "firewalld":
        requirements += ("Vérifier la zone, les interfaces et les sources qui lui sont associées ; aucune liaison de zone ne sera changée implicitement.",)
    elif intent.manager == "nftables":
        requirements += ("Identifier les tables, chaînes, hooks et priorités existants avant de traduire ces intentions en règles nftables.",)
    notes = [
        "Périmètre déclaré uniquement : aucun pare-feu interrogé, aucun port ouvert et aucun fichier écrit.",
        "Le gestionnaire choisi n’est ni détecté ni validé par cet aperçu.",
        "Les règles affichées sont des intentions, pas des commandes ou une configuration native du gestionnaire.",
        "Une autorisation supplémentaire ne ferme pas une règle plus large existante et ne garantit pas un accès exclusif.",
        "La découverte réseau et les transports non standard ne sont pas traités par cet aperçu.",
    ]
    if not any(network.version == 6 for network in networks):
        notes.append("Aucune intention IPv6 produite ; cela ne prouve pas que les accès IPv6 existants sont bloqués.")
    if intent.legacy_netbios:
        notes.append("NetBIOS demandé : TCP 139 et UDP 137/138 sont ajoutés aux seules sources IPv4 dans cette version.")
    else:
        notes.append("SMB direct uniquement : TCP 445. Aucun port NetBIOS n’est ajouté implicitement.")
    fingerprint = hashlib.sha256(json.dumps(asdict(normalized), sort_keys=True).encode("utf-8")).hexdigest()
    return FirewallPlan(1, "declared", normalized, tuple(rules), fingerprint, requirements, tuple(notes))


def format_firewall(plan: FirewallPlan) -> str:
    lines = ["SambaPilot — Aperçu de pare-feu, sans application",
             "Données déclarées ; règles existantes non examinées.",
             "Gestionnaire choisi : " + plan.intent.manager,
             "Interface choisie : " + plan.intent.interface]
    if plan.intent.zone:
        lines.append("Zone choisie : " + plan.intent.zone)
    lines += ["Empreinte du périmètre : " + plan.sha256, "", "Intentions de règles entrantes"]
    for rule in plan.rules:
        lines.append("  Autoriser " + rule.family + " depuis " + rule.source + " sur " + rule.interface
                     + " vers le port local " + str(rule.destination_port) + "/" + rule.protocol
                     + (" · zone " + rule.zone if rule.zone else ""))
    lines += ["", "Vérifications nécessaires avant une future application", *plan.requirements,
              "", *plan.notes]
    return "\n".join(lines)
