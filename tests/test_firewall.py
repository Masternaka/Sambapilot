import contextlib
from dataclasses import replace
import io
import json
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.firewall import FirewallIntent, FirewallPlanError, format_firewall, parse_sources, prepare_firewall


class FirewallTests(unittest.TestCase):
    def setUp(self):
        self.intent = FirewallIntent("ufw", "enp3s0", ("192.168.1.0/24",))

    def test_default_is_one_incoming_smb_rule_with_explicit_scope(self):
        plan = prepare_firewall(self.intent)
        self.assertFalse(plan.can_apply)
        self.assertFalse(plan.existing_rules_checked)
        self.assertEqual(plan.mode, "declared")
        self.assertEqual(len(plan.rules), 1)
        rule = plan.rules[0]
        self.assertEqual((rule.family, rule.source, rule.interface, rule.protocol, rule.destination_port),
                         ("ipv4", "192.168.1.0/24", "enp3s0", "tcp", 445))
        self.assertEqual(rule.direction, "incoming")
        self.assertEqual(rule.decision, "allow")

    def test_ipv6_is_explicit_and_never_inferred(self):
        plan = prepare_firewall(replace(self.intent, sources=("fd12:3456::/64",)))
        self.assertEqual(len(plan.rules), 1)
        self.assertEqual(plan.rules[0].family, "ipv6")
        ipv4_only = prepare_firewall(self.intent)
        self.assertTrue(any("ne prouve pas" in note for note in ipv4_only.notes))

    def test_mixed_families_do_not_expand_scope(self):
        plan = prepare_firewall(replace(self.intent, sources=("fd12:3456::/64", "192.168.1.0/24")))
        self.assertEqual({rule.family for rule in plan.rules}, {"ipv4", "ipv6"})
        self.assertEqual(len(plan.rules), 2)
        self.assertEqual(plan.intent.sources, ("192.168.1.0/24", "fd12:3456::/64"))

    def test_individual_clients_use_host_prefixes(self):
        plan = prepare_firewall(replace(self.intent, sources=("192.168.1.5/32", "fd12:3456::123/128")))
        self.assertEqual(len(plan.rules), 2)
        self.assertEqual({rule.source for rule in plan.rules}, {"192.168.1.5/32", "fd12:3456::123/128"})

    def test_host_bits_are_refused_instead_of_widening_network(self):
        for value in ("192.168.1.5/24", "fd12:3456::123/64"):
            with self.subTest(value=value), self.assertRaises(FirewallPlanError):
                prepare_firewall(replace(self.intent, sources=(value,)))

    def test_world_special_and_overlapping_special_ranges_are_refused(self):
        for value in ("0.0.0.0/0", "::/0", "127.0.0.1/32", "0.0.0.0/8", "169.254.1.0/24", "224.0.0.0/4",
                      "255.255.255.255/32", "0.0.0.0/1", "::1/128", "fe80::/64", "ff02::/16",
                      "::ffff:192.168.1.0/120"):
            with self.subTest(value=value), self.assertRaises(FirewallPlanError):
                prepare_firewall(replace(self.intent, sources=(value,)))

    def test_ambiguous_sources_never_trigger_dns_resolution(self):
        for value in ("maison.local", "192.168.1.5", "192.168.1.0/255.255.255.0", "fd12::%enp3s0/64",
                      "192.168.1.0/24 ", "192.168.1.0/２４", "192.168.1.0/24; reboot"):
            with self.subTest(value=value), patch("socket.getaddrinfo", side_effect=AssertionError("DNS")), \
                    self.assertRaises(FirewallPlanError):
                prepare_firewall(replace(self.intent, sources=(value,)))

    def test_duplicate_and_overlapping_source_networks_are_refused(self):
        for sources in (("192.168.1.0/24", "192.168.1.0/24"), ("192.168.0.0/16", "192.168.1.0/24"),
                        ("fd12:3456::/48", "fd12:3456:0:1::/64"), ("fd12:3456::/64", "fd12:3456:0:0::/64")):
            with self.subTest(sources=sources), self.assertRaises(FirewallPlanError):
                prepare_firewall(replace(self.intent, sources=sources))

    def test_empty_or_excessive_sources_are_refused(self):
        for sources in ((), tuple("10.0." + str(index) + ".0/24" for index in range(17))):
            with self.subTest(sources=sources), self.assertRaises(FirewallPlanError):
                prepare_firewall(replace(self.intent, sources=sources))

    def test_interface_is_not_optional_or_a_wildcard(self):
        for interface in ("", "*", "enp*", "enp3s0 wlan0", "enp3s0;reboot", "-i", "x" * 16, "éth0"):
            with self.subTest(interface=interface), self.assertRaises(FirewallPlanError):
                prepare_firewall(replace(self.intent, interface=interface))

    def test_manager_is_explicit_and_zone_only_belongs_to_firewalld(self):
        for intent in (replace(self.intent, manager=""), replace(self.intent, manager="iptables"),
                       replace(self.intent, manager="firewalld"), replace(self.intent, zone="home"),
                       replace(self.intent, manager="firewalld", zone="home;reboot"),
                       replace(self.intent, manager="firewalld", zone="x" * 18)):
            with self.subTest(intent=intent), self.assertRaises(FirewallPlanError):
                prepare_firewall(intent)
        plan = prepare_firewall(replace(self.intent, manager="firewalld", zone="home"))
        self.assertEqual(plan.rules[0].zone, "home")
        self.assertTrue(any("liaison de zone" in requirement for requirement in plan.requirements))

    def test_nftables_requires_examining_chains_before_native_translation(self):
        plan = prepare_firewall(replace(self.intent, manager="nftables"))
        self.assertTrue(any("hooks" in requirement for requirement in plan.requirements))
        self.assertFalse(plan.can_apply)

    def test_netbios_is_opt_in_and_limited_to_ipv4(self):
        plan = prepare_firewall(replace(self.intent, sources=("192.168.1.0/24", "fd12:3456::/64"), legacy_netbios=True))
        self.assertEqual(len(plan.rules), 5)
        ipv4 = {(rule.protocol, rule.destination_port) for rule in plan.rules if rule.family == "ipv4"}
        self.assertEqual(ipv4, {("tcp", 445), ("tcp", 139), ("udp", 137), ("udp", 138)})
        self.assertEqual([(rule.protocol, rule.destination_port) for rule in plan.rules if rule.family == "ipv6"], [("tcp", 445)])
        with self.assertRaises(FirewallPlanError):
            prepare_firewall(replace(self.intent, sources=("fd12:3456::/64",), legacy_netbios=True))
        with self.assertRaises(FirewallPlanError):
            prepare_firewall(replace(self.intent, legacy_netbios="yes"))

    def test_ids_are_stable_when_unrelated_sources_or_legacy_rules_are_added(self):
        first = prepare_firewall(self.intent)
        other = prepare_firewall(replace(self.intent, sources=("192.168.1.0/24", "fd12:3456::/64"), legacy_netbios=True))
        self.assertEqual(first.rules[0].identifier, other.rules[0].identifier)
        self.assertNotEqual(first.sha256, other.sha256)

    def test_fingerprint_is_independent_of_source_order(self):
        one = prepare_firewall(replace(self.intent, sources=("fd12:3456::/64", "192.168.1.0/24")))
        two = prepare_firewall(replace(self.intent, sources=("192.168.1.0/24", "fd12:3456::/64")))
        self.assertEqual(one, two)

    def test_gui_source_parser_keeps_errors_instead_of_dropping_empty_fields(self):
        self.assertEqual(parse_sources("192.168.1.0/24, fd12:3456::/64"), ("192.168.1.0/24", "fd12:3456::/64"))
        for value in ("", "192.168.1.0/24,", ",192.168.1.0/24", "192.168.1.0/24,,fd12:3456::/64"):
            with self.subTest(value=value), self.assertRaises(FirewallPlanError):
                parse_sources(value)

    def test_cli_is_pure_and_outputs_declared_intentions(self):
        with patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("pathlib.Path.open", side_effect=AssertionError("file")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")), \
                patch("socket.socket", side_effect=AssertionError("network")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["plan-pare-feu", "--manager", "ufw", "--interface", "enp3s0", "--source", "192.168.1.0/24", "--json"]), 0)
        plan = json.loads(output.getvalue())
        self.assertFalse(plan["can_apply"])
        self.assertFalse(plan["existing_rules_checked"])
        self.assertEqual(plan["mode"], "declared")
        self.assertNotIn("commands", plan)

    def test_cli_invalid_or_incomplete_request_returns_usage_error(self):
        for args in ([], ["--manager", "ufw", "--interface", "enp3s0", "--source", "0.0.0.0/0"],
                     ["--manager", "firewalld", "--interface", "enp3s0", "--source", "192.168.1.0/24"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["plan-pare-feu", *args])
            self.assertEqual(caught.exception.code, 2)

    def test_human_report_does_not_claim_exclusive_access_or_native_enforcement(self):
        text = format_firewall(prepare_firewall(self.intent))
        self.assertIn("ne garantit pas un accès exclusif", text)
        self.assertIn("pas des commandes", text)
        self.assertIn("aucun port ouvert", text)


if __name__ == "__main__":
    unittest.main()
