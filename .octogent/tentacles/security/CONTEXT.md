# Security Tentacle

## Scope
LAN & WiFi security audit for Tudor's infrastructure.

## Working Directory
`D:\MEMORY\CODE\SECURITY WIFI W11 LINUX\`

## Machines
- Laptop: Windows 11, Intel AX201 WiFi (no monitor mode)
- raspibig: 192.168.100.21 — main Pi
- raspi: 192.168.100.20 — secondary Pi

## Audit Status (2026-04-19)
- Lynis scores: raspibig=66/100, raspi=64/100
- Tools installed: nmap, wireshark, aircrack-ng, lynis

## Fixed
- Redis raspi — password: `InterJob2026!Redis`
- Port 9999 SimpleHTTP — killed
- PostgreSQL raspibig — localhost only
- PostgreSQL laptop PG18 — config patched (needs admin restart)

## Pending (awaiting Tudor)
- WiFi password `manuel222` — WEAK, change in router
- Disable WPA2 fallback → WPA3 only in router
- Intel AMT :16992 — disable in BIOS
- SMB :445 laptop — disable if unused
- Signal CLI :8081 raspi — add auth or bind localhost
- PostgreSQL laptop — restart service as admin
- raspibig: chmod 600 on /etc/postgresql/15/main/*.conf
- SSH hardening: AllowTcpForwarding NO, ClientAliveCountMax 2

## Key Files
- `lan_scan.py` — full LAN nmap scan script
- `pi_audit.sh` — Pi hardening audit script
- `scan_results/` — timestamped scan reports

## WiFi Info
- SSID: tudor5g, BSSID: 80:e1:bf:4b:25:c0, Ch36, 5GHz, WPA3/WPA2
- Router: Huawei 192.168.100.1
- For real WiFi pentest: need Alfa AWUS036ACH (~40€) or Kali live USB
