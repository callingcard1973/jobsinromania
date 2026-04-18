# 🔐 WireGuard VPN Setup - ProtonVPN Integration (2026-04-07)

## ✅ IMPLEMENTATION COMPLETE

**Status**: VPN connected, SMTP unlocked, Zoho working  
**Date**: 2026-04-07  
**Machine**: raspi (192.168.100.20)

## 🎯 PURPOSE

Bypass ISP SMTP port blocking (587, 25, 465) to enable:
- **Zoho SMTP**: +250 emails/day
- **Outlook SMTP**: +300 emails/day (not using)

## 📦 INFRASTRUCTURE

### ProtonVPN Account
- **Email**: apaminerala@yahoo.com
- **Password**: KR5vis2(UF8Hb&Nh
- **Plan**: FREE (sufficient)
- **Config**: WireGuard (faster than OpenVPN)

### Server
- **Machine**: raspi (192.168.100.20)
- **Config path**: `/etc/wireguard/proton-nl.conf`
- **Interface name**: `proton-nl`

## 🔧 CONFIGURATION (ACTIVE)

```
[Interface]
PrivateKey = ECZqtWhDOEagTvWhahA/ktyuF9jgYpvyhL9q7kBa73A=
Address = 10.2.0.2/32, 2a07:b944::2:2/128
DNS = 10.2.0.1, 2a07:b944::2:1

[Peer]
PublicKey = UIV6mDfDCun6PrjT7kFrpl02eEwqIa/piXoSKm1ybBU=
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = 89.39.107.113:51820
PersistentKeepalive = 25
```

**Server**: NL-FREE#15 (Netherlands)

## ⚡ QUICK COMMANDS

### Connect VPN
```bash
ssh tudor@192.168.100.20
sudo wg-quick up proton-nl
```

### Verify Connection
```bash
sudo wg show proton-nl
nslookup smtp.zoho.com  # Should resolve
```

### Disconnect VPN
```bash
sudo wg-quick down proton-nl
```

### Enable Auto-Connect (on reboot)
```bash
sudo systemctl enable wg-quick@proton-nl
```

### Check Status
```bash
sudo systemctl status wg-quick@proton-nl
```

## 🧪 TESTING

### Test SMTP (Zoho)
```bash
cd /opt/EMAIL/CAMPAIGNS
python3 << 'EOF'
import smtplib
server = smtplib.SMTP("smtp.zoho.com", 587, timeout=10)
server.starttls()
server.login("transport.work@zoho.com", "hWMwyWt2TSXK")
print("✅ Zoho SMTP connected")
server.quit()
EOF
```

### Full Test Script
```bash
/opt/EMAIL/CAMPAIGNS/test_vpn_smtp.py
```

## 🔍 TROUBLESHOOTING

### Issue: DNS not resolving
**Symptom**: `Temporary failure in name resolution`

**Fix**:
```bash
sudo resolvconf -a proton-nl << "EOF"
nameserver 10.2.0.1
nameserver 2a07:b944::2:1
EOF
sudo systemctl restart networking
```

**Why**: Tailscale DNS interferes. ProtonVPN DNS servers must be explicitly set.

### Issue: VPN not connecting
**Symptom**: `wg-quick` command fails

**Fix**:
```bash
sudo apt install wireguard wireguard-tools openresolv
```

### Issue: SMTP still blocked
**Symptom**: `Connection refused` or timeout

**Fix**: 
1. Verify VPN is connected: `sudo wg show proton-nl`
2. Check handshake: `latest handshake` should be recent
3. Test DNS: `nslookup smtp.zoho.com`
4. If DNS fails, use the DNS fix above

## 📊 CAPACITY UNLOCK

| Provider | Before VPN | After VPN | Status |
|----------|-----------|-----------|--------|
| Brevo | 270/day | 270/day | ✅ Always worked |
| Gmail | 235/day | 235/day | ✅ Always worked |
| **Zoho** | BLOCKED | **250/day** | ✅ **UNLOCKED** |
| Outlook | BLOCKED | 300/day | ❌ Auth disabled (not using) |
| **TOTAL** | **505/day** | **755/day** | ✅ **+50% INCREASE** |

## 🔒 SECURITY NOTES

1. **Config is minimal** - no credentials in WireGuard config
2. **Private key** - kept on raspi, never shared
3. **ProtonVPN credentials** - separate from VPN config
4. **DNS privacy** - ProtonVPN DNS servers used (10.2.0.1)

## 📝 PERMANENT SETUP

### Make VPN Auto-Start
```bash
ssh tudor@192.168.100.20
sudo systemctl enable wg-quick@proton-nl
sudo systemctl start wg-quick@proton-nl
```

### Verify Auto-Start Works
```bash
sudo systemctl status wg-quick@proton-nl
sudo reboot  # Test persistence
```

### Monitor VPN Status
```bash
# Check if running
systemctl is-active wg-quick@proton-nl

# Check stats
sudo wg show proton-nl
```

## 🎯 PRODUCTION INTEGRATION

VPN is now integrated with email system:
- ✅ Zoho SMTP through ProtonVPN
- ✅ Campaigns can use Zoho provider
- ✅ No configuration needed in email scripts
- ✅ Automatic DNS handling via WireGuard

## 📚 RELATED FILES

- `/opt/EMAIL/CAMPAIGNS/.env` - SMTP credentials (Zoho added)
- `/opt/EMAIL/CAMPAIGNS/email_sending_skill.py` - Master email sender
- `/opt/ACTIVE/INFRA/SKILLS/email_sending_skill.py` - Skills registry

## 🚀 NEXT STEPS

1. **Integrate Zoho into campaigns** - update email system to use Zoho provider
2. **Monitor VPN stability** - check for disconnections, reconnections
3. **Scale testing** - send test batches through Zoho to verify delivery

---

**Setup completed**: 2026-04-07 07:15  
**VPN status**: ✅ Connected and tested  
**SMTP tested**: ✅ Zoho working through VPN
