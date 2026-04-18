# 🖥️ SERVER LOCATIONS - EMAIL VPN PROJECT

## 📍 DISTRIBUTED ARCHITECTURE 

### 📧 EMAIL SYSTEM: RASPIBIG (192.168.100.21)
```bash
/opt/EMAIL/CAMPAIGNS/
├── .env                           # 🔑 TOATE credentials SMTP (Zoho, Outlook, etc.)
├── multi_gmail_batch_system.py    # 📧 Sistem email principal (optimizat)
├── outlook_smtp_test.py           # 🧪 Test Outlook SMTP (needs creation)
├── zoho_smtp_test.py             # 🧪 Test Zoho SMTP (needs creation)
├── gmail_test.py                 # 🧪 Test Gmail SMTP (needs creation)
└── brevo_test.py                 # 🧪 Test Brevo API (needs creation)
```

### 🔗 VPN INFRASTRUCTURE: RASPI (192.168.100.20)  
```bash
/home/tudor/vpn/
├── proton-credentials.txt        # 🔑 ProtonVPN login credentials
├── working.ovpn                  # ⚠️ NEEDS DOWNLOAD - real ProtonVPN config
├── proton-real.ovpn             # ❌ Fake config (nu funcționează)
└── test configs/                 # ❌ Various failed configs
```

## 🔄 ARCHITECTURE EXPLANATION

**Why Split Architecture:**
- **Raspibig**: Main production server - handles email campaigns
- **Raspi**: Secondary server - handles VPN connection (isolates network changes)  
- **Connection**: VPN on raspi routes traffic → raspibig uses VPN connection for SMTP

### Backup & Optimization Location
```bash
/opt/EMAIL/CAMPAIGNS/
├── multi_gmail_batch_system_backup.py  # 💾 Backup BEFORE optimization
└── multi_gmail_batch_system.py         # ✅ Current optimized version
```

## 🔑 CREDENTIALS DISTRIBUTION

### ProtonVPN Credentials (RASPI: /home/tudor/vpn/proton-credentials.txt)
```
apaminerala@yahoo.com
KR5vis2(UF8Hb&Nh
```

### SMTP Credentials (RASPIBIG: /opt/EMAIL/CAMPAIGNS/.env)
```bash
# Zoho SMTP (BLOCKED - needs VPN from raspi)
ZOHO_EMAIL=transport.work@zoho.com
ZOHO_PASSWORD=hWMwyWt2TSXK

# Outlook SMTP (BLOCKED - needs VPN from raspi)  
OUTLOOK_EMAIL=manpowerdristor@outlook.com
OUTLOOK_PASSWORD=GmiNPbNYrrN@u39

# Working providers (current)
BREVO_API_KEY=... (active)
GMAIL_CREDENTIALS=... (active)
```

## 🚀 ACCESS COMMANDS

### SSH to Email Server (RASPIBIG)
```bash
ssh tudor@192.168.100.21
cd /opt/EMAIL/CAMPAIGNS  
ls -la
```

### SSH to VPN Server (RASPI)
```bash
ssh tudor@192.168.100.20
cd /home/tudor/vpn
ls -la
```

### Check Current Email System Status (RASPIBIG)
```bash
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 multi_gmail_batch_system.py --status'
```

### Check VPN Status (RASPI)
```bash
ssh tudor@192.168.100.20 'ps aux | grep openvpn | grep -v grep'
```

## 🔧 VPN SETUP COMMANDS (DISTRIBUTED SETUP)

### 1. Check VPN Directory Ready (RASPI)
```bash
ssh tudor@192.168.100.20 'ls -la /home/tudor/vpn/'
# Should show: proton-credentials.txt
```

### 2. Upload Real ProtonVPN Config (TO RASPI)
```bash
# From laptop after downloading from protonvpn.com
scp netherlands.ovpn tudor@192.168.100.20:/home/tudor/vpn/working.ovpn
```

### 3. Connect VPN (ON RASPI)
```bash
ssh tudor@192.168.100.20 'cd /home/tudor/vpn && sudo openvpn --config working.ovpn --auth-user-pass proton-credentials.txt --daemon'
```

### 4. Test SMTP via VPN (FROM RASPIBIG through RASPI)
```bash
# Create test scripts first, then run
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 outlook_smtp_test.py && python3 zoho_smtp_test.py'
```

### 5. Network Routing (Auto-configured)
```bash
# Raspibig will automatically route through raspi's VPN connection
# No additional configuration needed - both servers on same network
```

## 📊 EMAIL SYSTEM STATUS (Current)

### Active Campaigns on Raspibig
```bash
/opt/EMAIL/CAMPAIGNS/
├── LUCIAN/     # Campaign 1 - 505 emails/day
├── VIRGIL/     # Campaign 2 - 505 emails/day  
└── ELENA/      # Campaign 3 - 505 emails/day
Total: 1,515 emails/day
```

### Provider Status Check
```bash
# Check which providers are working
cd /opt/EMAIL/CAMPAIGNS
python3 -c "
print('Current capacity per campaign:')
print('✅ Brevo: 270 emails/day')  
print('✅ Gmail Warmed: 130 emails/day')
print('✅ Gmail Fresh: 105 emails/day')
print('❌ Zoho: BLOCKED (needs VPN)')
print('❌ Outlook: BLOCKED (needs VPN)')
print('Total current: 505/day per campaign')
print('Target with VPN: 1,055/day per campaign')
"
```

## ⚠️ MISSING FILE (5 MINUTE FIX)

### What's Missing (ON RASPI)
```bash
/home/tudor/vpn/working.ovpn  # Real ProtonVPN config with valid certificates
```

### How to Get It
1. **Download**: https://account.protonvpn.com/downloads
2. **Login**: apaminerala@yahoo.com / KR5vis2(UF8Hb&Nh
3. **Choose**: OpenVPN config for NETHERLANDS FREE
4. **Upload**: `scp config.ovpn tudor@192.168.100.20:/home/tudor/vpn/working.ovpn` ⚠️ (RASPI not raspibig)

### Verification Commands
```bash
# Check file exists (ON RASPI)
ssh tudor@192.168.100.20 'ls -la /home/tudor/vpn/working.ovpn'

# Check file has valid certificate (ON RASPI)
ssh tudor@192.168.100.20 'cd /home/tudor/vpn && sudo openvpn --config working.ovpn --verb 3 | head -10'

# Test SMTP blocked status (ON RASPIBIG - should fail until VPN active)
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 outlook_smtp_test.py'
```

## 🎯 EXPECTED RESULT

**After VPN Connection (DISTRIBUTED SETUP)**:
```bash
# 1. VPN connected on RASPI:
ssh tudor@192.168.100.20 'ps aux | grep openvpn'  # ✅ Should show openvpn process

# 2. SMTP should work from RASPIBIG through RASPI's VPN:
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 outlook_smtp_test.py'  # ✅ Should connect
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 zoho_smtp_test.py'     # ✅ Should connect

# 3. Email capacity result:
# Current: 505 emails/day per campaign (Brevo + Gmail only)
# New: 1,055 emails/day per campaign (+Zoho +Outlook via VPN)
# System total: 3,165 emails/day (vs current 1,515/day)
```

**Current Test Status (CONFIRMED BLOCKED)**:
```bash
# ❌ Without VPN (current state):
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 outlook_smtp_test.py'
# Result: "❌ Outlook SMTP failed: timed out"
```

---
**Email Server**: raspibig (192.168.100.21) - `/opt/EMAIL/CAMPAIGNS/`  
**VPN Server**: raspi (192.168.100.20) - `/home/tudor/vpn/`  
**Missing**: 1 real ProtonVPN config file (5min download to raspi)  
**Architecture**: Email server routes through VPN server automatically