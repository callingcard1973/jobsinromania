# 🖥️ SERVER ARCHITECTURE - EMAIL VPN PROJECT

## 📊 DISTRIBUTED SETUP SUMMARY

### 🏗️ ARCHITECTURE OVERVIEW
```
LAPTOP (Windows)
├── Project Management: D:\MEMORY\EMAIL\
├── Config Download: ProtonVPN website
└── Remote Control: SSH to both servers

RASPIBIG (192.168.100.21) 
├── 📧 EMAIL SYSTEM: /opt/EMAIL/CAMPAIGNS/
├── 🔑 SMTP Credentials: .env file
├── 📈 Current Capacity: 1,515 emails/day (3 campaigns)
└── 🎯 Target Capacity: 3,165 emails/day (with VPN)

RASPI (192.168.100.20)
├── 🔗 VPN CONNECTION: /home/tudor/vpn/
├── 🔑 ProtonVPN Creds: proton-credentials.txt  
├── ⚠️ Missing: working.ovpn (needs download)
└── 🌐 Network Gateway: Routes traffic for raspibig
```

## 🔄 HOW IT WORKS

### Current State (BLOCKED)
1. **Raspibig** tries to send emails via SMTP
2. **ISP blocks** SMTP ports (587, 25, 465)
3. **Result**: Only Brevo API + Gmail SMTP work = 505 emails/day

### Target State (VPN UNBLOCKED)  
1. **Raspi** connects to ProtonVPN
2. **Raspibig** routes traffic through raspi's VPN connection
3. **ISP blocking bypassed** via VPN tunnel
4. **Result**: All 5 providers work = 1,055 emails/day

## 📍 KEY LOCATIONS

### RASPIBIG (Email Server)
```bash
📧 EMAIL SYSTEM
/opt/EMAIL/CAMPAIGNS/
├── .env                      # ✅ All SMTP credentials
├── multi_gmail_batch_system.py  # ✅ Main email system
├── outlook_smtp_test.py      # ✅ Created today
└── zoho_smtp_test.py         # ✅ Created today

📊 CURRENT CAPACITY
├── Brevo: 270 emails/day     # ✅ Working (API)
├── Gmail Warmed: 130/day     # ✅ Working (SMTP)
├── Gmail Fresh: 105/day      # ✅ Working (SMTP)
├── Zoho: BLOCKED             # ❌ Needs VPN
└── Outlook: BLOCKED          # ❌ Needs VPN
```

### RASPI (VPN Server)
```bash
🔗 VPN INFRASTRUCTURE  
/home/tudor/vpn/
├── proton-credentials.txt    # ✅ ProtonVPN login
├── working.ovpn              # ⚠️ MISSING (needs download)
└── Various test configs/     # ❌ All have fake certificates

🔧 VPN STATUS
├── OpenVPN: ✅ Installed     # Ready for connection
├── Credentials: ✅ Configured
└── Real Config: ❌ Missing   # 5 minute download needed
```

## 🚀 DEPLOYMENT SEQUENCE

### Phase 1: Download Real Config (5 minutes)
```bash
# 1. Browser: https://account.protonvpn.com/downloads
# 2. Login: apaminerala@yahoo.com / KR5vis2(UF8Hb&Nh
# 3. Download: Netherlands FREE OpenVPN config
# 4. Upload: scp config.ovpn tudor@192.168.100.20:/home/tudor/vpn/working.ovpn
```

### Phase 2: Connect VPN (1 minute)
```bash
ssh tudor@192.168.100.20 'cd /home/tudor/vpn && sudo openvpn --config working.ovpn --auth-user-pass proton-credentials.txt --daemon'
```

### Phase 3: Test & Verify (2 minutes)
```bash
# Verify VPN connected
ssh tudor@192.168.100.20 'ps aux | grep openvpn'

# Test SMTP unblocked
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 outlook_smtp_test.py'
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && python3 zoho_smtp_test.py'
```

## 📊 CAPACITY COMPARISON

### Before VPN (Current - BLOCKED)
| Provider | Server | Status | Capacity |
|----------|--------|--------|----------|
| Brevo | raspibig | ✅ API | 270/day |
| Gmail Warmed | raspibig | ✅ SMTP | 130/day |
| Gmail Fresh | raspibig | ✅ SMTP | 105/day |
| Zoho | raspibig | ❌ BLOCKED | 0/day |
| Outlook | raspibig | ❌ BLOCKED | 0/day |
| **TOTAL** | | | **505/day** |

### After VPN (Target - UNBLOCKED)
| Provider | Server | VPN Route | Capacity |
|----------|--------|-----------|----------|
| Brevo | raspibig | Direct | 270/day |
| Gmail Warmed | raspibig | Direct | 130/day |
| Gmail Fresh | raspibig | Direct | 105/day |
| Zoho | raspibig | → raspi VPN | 250/day |
| Outlook | raspibig | → raspi VPN | 300/day |
| **TOTAL** | | | **1,055/day** |

**System Impact**: 1,515 → 3,165 emails/day (+110% increase)

## 🔧 TROUBLESHOOTING

### Common Issues

**1. VPN won't connect**
```bash
# Check certificate validity
ssh tudor@192.168.100.20 'cd /home/tudor/vpn && openssl x509 -in working.ovpn -text -noout'
# Should NOT show "base64 decode" errors
```

**2. SMTP still blocked after VPN**
```bash
# Verify VPN actually connected
ssh tudor@192.168.100.20 'curl -s ifconfig.me'  # Should show different IP

# Check raspibig can reach through VPN
ssh tudor@192.168.100.21 'curl -s ifconfig.me'  # Should show VPN IP
```

**3. Email system conflicts**
```bash
# Ensure no conflicts with current email campaigns
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS && ps aux | grep python'
```

## ✅ SUCCESS CRITERIA

**VPN Connection Success**:
- `ps aux | grep openvpn` shows active process on raspi
- `curl ifconfig.me` shows VPN IP from both servers

**SMTP Unblocking Success**:
- `python3 outlook_smtp_test.py` returns "✅ OUTLOOK SMTP WORKING!"  
- `python3 zoho_smtp_test.py` returns "✅ ZOHO SMTP WORKING!"

**Email System Success**:
- All 5 providers active simultaneously
- 1,055 emails/day capacity per campaign
- 3,165 emails/day total system capacity

---
**Architecture**: Distributed (2 servers)  
**Complexity**: Low (standard network routing)  
**Time to Deploy**: 8 minutes total  
**Business Impact**: +110% email capacity = +110% recruitment reach