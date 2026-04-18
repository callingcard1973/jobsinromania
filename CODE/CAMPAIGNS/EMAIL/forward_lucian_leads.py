#!/usr/bin/env python3
"""Forward Lucian's hot leads summary to solonet.vacancy@gmail.com"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manpowerdristor@gmail.com"
SMTP_PASS = "pwat qgot nznt eggf"
TO = "solonet.vacancy@gmail.com"
CC = "manpower.dristor@gmail.com"

subject = "HOT LEADS din lucian.bpandp@gmail.com - Feb/Mar 2026 - URGENT"

body = """LEADS EXTRASE DIN CONTUL LUCIAN (lucian.bpandp@gmail.com)
Perioada: Februarie - Martie 2026
Extrase: 9 Aprilie 2026
============================================================

!!! URGENT - COMENZI FERME !!!

1. GORNEANU Mihaela <mihagor@yahoo.com> — 24 Feb
   -> 20 persoane DELIVERY in Bucuresti
   -> Salariu minim 4050 lei, cazare oferita
   -> Cere oferta pentru personal nou + existent

2. TARABOSTES DELIVERY <tarabostes.delivery@gmail.com> — 21 Mar
   Contact: Radu | Tel: 0725/241.044 | Dej
   -> 20 muncitori necalificati, CURIER/LIVRATOR
   -> Permis scuter 49cc (AM) obligatoriu
   -> Minim 6 luni, preferabil mai lung

3. MARIO RESORT <office@marioresort.ro> — 21-23 Feb
   Contact: Andrei Valeriu-Marian | Tel: 0744 11 77 17
   Locatie: Moinesti, Bacau
   -> 6 nepalezi, vorbitori engleza
   -> Intretinere spatii verzi + supraveghere parc aventura
   -> Perioada: mai-septembrie, 8 ore/zi
   -> Cazare + masa asigurate

4. MIHAELA FEODOROV <feodorovm@yahoo.com> — 30 Mar
   Tel: 0752 408 426
   -> 3 muncitori necalificati - productie elemente beton armat
   -> Aprilie-noiembrie, posibilitate prelungire
   -> Vrea sa discute telefonic

5. DATINA CONCEPT <datinaconcept@gmail.com> — 3 Mar
   Contact: Radu Stefanescu | Tel: +40749 253 971
   Email alt: florinradu.stefanescu@gmail.com
   -> 2 persoane asiatice CONSTRUCTII, necalificate
   -> Minimum engleza

---

INTERESATI - CER OFERTA:

6. HOMEY / Daria Ene <daria.ene@homey.com.ro> — 20-23 Feb
   Apartamente regim turistic, Bucuresti
   -> 4.000 curatenii/luna, tot anul (nu sezonier)
   -> Cer oferta de pret per angajat pentru echipa curatenie
   -> Au deja echipa interna, vor suplimentare

7. GRADINILE ROMANE <gradinileromane@gmail.com> — 25 Feb
   Tel: +40752804617
   -> Personal bucatarie din afara UE
   -> Cer draft contract + CV-uri

8. IZVORUL BUCOVINEI <izvorulbucovinei131@gmail.com> — 25 Feb
   Tel: 0749619946 (CORECTAT din 0749629956)
   -> Bucatar + camerista + aj. bucatar
   -> Au restaurant + cazare + sala evenimente

9. ANASTASIA MITRENGA <impexsolero@yahoo.com> — 28 Feb
   -> Sezon 15.05-01.10.2026, au restaurant
   -> 1 bucatar + 2 persoane pizza (pot fi din afara UE)

10. MAX INTERNATIONAL <office@maxinternational.ro> — 28 Feb
    Contact: Gligore Alina
    -> Ospatar + bucatar, nedeterminat
    -> Preferinta cetatenie romana

11. DELTA IDEAL SULINA / C.Istrate <c.istrates@yahoo.com> — 2 Mar
    -> 2 persoane sezon 2026

12. GREEN MOUNTAIN RESORT <info@green-mountain-resort.ro> — 2 Mar
    Tel: 0729016278
    -> 1 housekeeping, mai-octombrie

13. ZEN ECO VILLA / Anca Ioani <zenecovilla@gmail.com> — 3 Mar
    Sfantu Gheorghe, Tulcea | Tel: +40 745 351 798
    -> 1-2 persoane menaj + aj. bucatarie, sezonier
    -> Cer costuri integrale detaliate

14. OPUS VILLA / IOANA HOTEL SINAIA <contact@opusvilla.ro> — 4 Mar
    Contact: Darius Teiu, Director Hotel | Tel: 0735580000
    -> Vrea discutie telefonica
    -> Complex Opus + Ioana Boutique Hotel

15. PORTAL VILLAGE <office@portalgreen.ro> — 24 Feb
    Tel: +40745222759 | Sibiel
    -> 1 aj. bucatar bilingv RO+EN
    -> Prietenos, iubitor de natura/animale

16. CAMELIA GUGU / Domeniul Scrovistea <camelia823@yahoo.com> — 25 Feb
    Tel: 0727249024
    -> Camerista + bucatar + aj. bucatar + ospatar

17. HOTEL MIRAJ POIANA BRASOV <rezervari_miraj@yahoo.com> — 24 Feb
    Tel: 0268-406535
    -> Personal deja in tara, incepere IMEDIATA

18. CULACSIZ MARIANA <panaitmariana11@gmail.com> — 20-30 Mar
    Tel: 0722254040
    -> 2 cameriste sezonier
    -> A sunat dar nimeni nu a raspuns!

19. PINDUL EXIM <pindulexim@gmail.com> — 19 Mar
    Constanta
    -> Muncitori calificati constructii

20. NADAV KASHRI / KOPLAX SRL <nadav.kashri@gmail.com> — 31 Mar
    -> Tractoristi cu permis agricol + remorca
    -> Deja in Romania, conventia Viena

21. NESTE AUTOMOTIVE / Florina Popa <florina.popa@neste.ro> — 20 Feb
    Sos. Chitilei 431, Sector 1 | Tel: +4 031 425 35 45 | Mobil: 0740.121.560
    -> Personal curatenie + receptie

---

NU MAI ACTUAL:
- Rodica Prostean - deja lucreaza cu alta firma
- AFRONT TER - post ocupat
- WIZMAG - email gresit
- Anca Hirtie - anunt nu mai valabil
- Edit Kispal - nu are nevoie
- Tomas Morales - spaniol, nu intelege romana
- HR Carne Pui - nu e horeca, comert cu carne
- TOPO-SURVEY - nu multumesc
- HAISAN TAXI - intreaba de durata schimbare angajator (indecis)

+ 6x Google Forms "Cerere de initiere proces recrutare" (Feb 2026) - DE VERIFICAT IN SPREADSHEET

---
Generat automat din pipeline email, 9 aprilie 2026
"""

msg = MIMEMultipart()
msg["From"] = SMTP_USER
msg["To"] = TO
msg["Cc"] = CC
msg["Subject"] = subject
msg.attach(MIMEText(body, "plain", "utf-8"))

try:
    s = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    s.starttls()
    s.login(SMTP_USER, SMTP_PASS)
    s.sendmail(SMTP_USER, [TO, CC], msg.as_string())
    s.quit()
    print(f"Sent to {TO} + CC {CC}")
except Exception as e:
    print(f"Error: {e}")
