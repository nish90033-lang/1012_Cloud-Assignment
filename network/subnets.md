# Task 5: Subnet allocation for 10.20.0.0/16

## Method
Allocate from the largest requirement to the smallest, starting at 10.20.0.0, each subnet placed right after the previous one.
For each requirement H, find the smallest host-bit count `b` with `2^b - 2 >= H`; the prefix is `32 - b`.

| Subnet | Hosts needed | Working | b | Prefix |
|---|---|---|---|---|
| app | 1,000 | 2^9 - 2 = 510 < 1000; 2^10 - 2 = 1022 >= 1000 | 10 | /22 |
| public | 250 | 2^7 - 2 = 126 < 250; 2^8 - 2 = 254 >= 250 | 8 | /24 |
| data | 100 | 2^6 - 2 = 62 < 100; 2^7 - 2 = 126 >= 100 | 7 | /25 |
| management | 20 | 2^4 - 2 = 14 < 20; 2^5 - 2 = 30 >= 20 | 5 | /27 |

## Result

| Subnet | Network address | Prefix | Usable host range | Broadcast | Usable hosts |
|---|---|---|---|---|---|
| app | 10.20.0.0 | /22 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1,022 |
| public | 10.20.4.0 | /24 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data | 10.20.5.0 | /25 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management | 10.20.5.128 | /27 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

Each subnet starts at the address right after the previous broadcast address
(10.20.3.255 -> 10.20.4.0; 10.20.4.255 -> 10.20.5.0; 10.20.5.127 -> 10.20.5.128).

## NACL for the public subnet (network/nacl.json)
Inbound: 100 deny all from 198.51.100.0/24; 110 allow tcp 80; 120 allow tcp 443; 130 allow tcp 22 from management (10.20.5.128/27);
140 allow tcp 1024-65535 from app (10.20.0.0/22) = replies to connections the load balancer opened towards the app subnet.
Outbound: 100 allow tcp 8000 to app (10.20.0.0/22); 110 allow tcp 1024-65535 to 0.0.0.0/0 = replies to clients (ephemeral ports).
Everything else is denied by the implicit final deny.

## Why a NACL needs separate reply rules and rule order
A NACL is stateless: it does not remember that an outbound packet was a reply to an allowed inbound one, so each direction
is evaluated on its own and replies need explicit rules on the ephemeral port range. Rules are evaluated from the lowest number
and the first match wins, so the deny for 198.51.100.0/24 (rule 100) must have a lower number than the allow rules for ports 80/443
(110/120); if it were numbered higher, a packet from that range to port 443 would match the allow first and get through.
