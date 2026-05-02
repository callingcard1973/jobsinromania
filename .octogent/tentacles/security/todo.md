# Security Todo

## Session 2026-04-19 — Ce s-a făcut
- Instalat nmap + Wireshark + aircrack-ng + lynis pe toate mașinile
- Scanat tot LAN-ul: 7 hosturi, toate serviciile identificate
- Identificat 192.168.100.23 = raspibig interfață secundară Docker
- FIXED: Redis raspi — parolă setată `InterJob2026!Redis`
- FIXED: Port 9999 SimpleHTTP directory listing — killed
- FIXED: PostgreSQL raspibig — bind localhost
- FIXED: PostgreSQL laptop PG18 — config patchat (nevoie restart admin)
- Lynis: raspibig=66/100, raspi=64/100
- Creat tentaclul `security` în Octogent
- Wireshark instalat pe laptop



## Update 2026-04-19 (session 2)
- Instalat: TCPView (laptop), fail2ban+ufw+rkhunter+nikto+chkrootkit (ambele Pis)
- UFW activ: raspibig (SSH/80/443/Grafana/LAN), raspi (SSH/80/443/8080)
- fail2ban activ pe ambele Pis
- rkhunter + chkrootkit: 0 rootkit-uri pe ambele Pis — CURAT
- Wireshark instalat pe laptop

## Pending
- [ ] Schimbă parola WiFi `manuel222` → passphrase lungă
- [ ] Dezactivează WPA2 fallback în router (WPA3-only)
- [ ] Restart postgresql-x64-18 ca admin pe laptop
- [ ] chmod 600 /etc/postgresql/15/main/*.conf pe raspibig
- [ ] SSH hardening pe ambele Pis
- [ ] Adaugă auth la Signal CLI :8081 pe raspi
- [ ] Instalează Nessus Essentials
- [ ] Cumpără Alfa AWUS036ACH pentru test WiFi real
- [ ] Dezactivează Intel AMT :16992 din BIOS (când e convenient)
