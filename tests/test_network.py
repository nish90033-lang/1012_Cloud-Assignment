import json
import os

import nacl_sim

ROOT = os.path.dirname(os.path.dirname(__file__))


def decide(rules, direction, port, addr, proto="tcp"):
    return nacl_sim.decide(rules, {"direction": direction, "protocol": proto, "port": port, "address": addr})[0]


def test_sample_packets_all_correct():
    rules = nacl_sim.load_rules(os.path.join(ROOT, "network", "nacl.json"))
    for line in open(os.path.join(ROOT, "network", "packets_sample.jsonl")):
        p = json.loads(line)
        assert nacl_sim.decide(rules, p)[0] == p["expected"], p["id"]


def test_blocked_range_beats_web_ports_and_other_rules():
    rules = nacl_sim.load_rules(os.path.join(ROOT, "network", "nacl.json"))
    for port in (80, 443, 22, 40000):
        assert decide(rules, "inbound", port, "198.51.100.200") == "deny"
    assert decide(rules, "inbound", 80, "203.0.113.5") == "allow"
    assert decide(rules, "inbound", 22, "10.20.5.130") == "allow"      # management subnet
    assert decide(rules, "inbound", 22, "10.20.5.20") == "deny"        # data subnet
    assert decide(rules, "inbound", 50000, "10.20.2.9") == "allow"     # replies from the app subnet
    assert decide(rules, "outbound", 8000, "10.20.3.254") == "allow"
    # Known consequence of the specified ephemeral range (1024-65535, which contains 8000): the reply rule for clients
    # anywhere also matches port 8000, so a stateless rule cannot tell a reply from a new connection. Documented in the report.
    assert decide(rules, "outbound", 8000, "10.20.4.1") == "allow"
    assert decide(rules, "outbound", 22, "10.20.4.1") == "deny"
    assert decide(rules, "outbound", 443, "192.0.2.1") == "deny"       # only ephemeral replies leave


def test_subnets_are_consecutive_and_smallest_fit():
    import ipaddress as ip
    nets = [ip.ip_network(n) for n in ("10.20.0.0/22", "10.20.4.0/24", "10.20.5.0/25", "10.20.5.128/27")]
    for need, n in zip((1000, 250, 100, 20), nets):
        assert n.num_addresses - 2 >= need
        assert (n.num_addresses // 2) - 2 < need  # one bit fewer would not fit
    for a, b in zip(nets, nets[1:]):
        assert int(a.broadcast_address) + 1 == int(b.network_address)
