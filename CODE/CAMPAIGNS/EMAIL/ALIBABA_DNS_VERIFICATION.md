# Alibaba Mail — DNS Configuration Verification Guide

> **Domain:** expatsinromania.org  
> **Mail Provider:** Alibaba Cloud (AliyunDM)  
> **Updated:** Jan 6, 2026, 11:27:46  
> **Current:** Apr 8, 2026, 12:44:00  

This document describes how to verify the DNS configuration for your email domain. It covers query methods for ownership verification, Sender Policy Framework (SPF), DomainKeys Identified Mail (DKIM), Domain-based Message Authentication, Reporting, and Conformance (DMARC), and MX records.

Three query methods are described:
1. **Alibaba Cloud DNS check tool**
2. **Windows commands**
3. **macOS commands**

The examples use the domain **expatsinromania.org**.

---

## ⚠️ Important: Before You Begin

> **Before you use the following query methods, configure the required DNS records in the console of your domain name service provider (SP).**
>
> You can find the record values in the **Direct Mail console** on the **Email Domains > Configure** page.
>
> After the configuration is complete, use these methods to verify that the settings have taken effect.

> **When you run queries, replace the example domain name with your own domain name.**

---

## Method 1: Query Using the Alibaba Cloud DNS Check Tool

🔗 **https://dnscheck.aliyun.com/**

### Steps:
1. Open the URL above in your browser
2. Enter the record details as shown below
3. Click **"Query"** to check each record

### What to Query:

#### 1. Ownership Verification
**Purpose:** To prove that you own or control the domain name. This verification typically requires you to add a specific TXT record provided by the SP.

| Field | Value |
|-------|-------|
| **Domain to query** | `aliyundm.expatsinromania.org` |
| **Record type** | TXT |
| **Expected value** | `2640863cc4ce991e9f07` |

#### 2. SPF (Sender Policy Framework)
**Purpose:** To prevent sender spoofing by specifying a list of servers that are authorized to send email for your domain.

 **Important:** You can have only **one** SPF record. If you have multiple outbound IP addresses or mail providers, merge them into a single record.

| Field | Value |
|-------|-------|
| **Domain to query** | `expatsinromania.org` |
| **Record type** | TXT |
| **Expected value** | `v=spf1 include:spfdm-ap-southeast-1.aliyun.com -all` |

#### 3. DKIM (DomainKeys Identified Mail)
**Purpose:** To add a digital signature to your emails, allowing the receiving server to verify that the email was actually sent from your domain and was not altered in transit.

| Field | Value |
|-------|-------|
| **Domain to query** | `aliyun-ap-southeast-1._domainkey.expatsinromania.org` |
| **Record type** | TXT |
| **Expected value** | `v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCZa8NtJsJ1GtyALEh6P/RxzN/cUb8RcherMTbXNQr8lamGzyVOTxAqI1oBEF9g2en3QDde4H+6Ajtzs7barPsciK4Xc9xXdFimmSCAACMnZ9szuI6xTsIQp0xW74zixKPg2Xkra5rKYpbaBb2pSYX0hNx75dAP9TVB0kiUnsrqewIDAQAB` |

#### 4. DMARC (Domain-based Message Authentication, Reporting, and Conformance)
**Purpose:** To build on SPF and DKIM by telling receiving servers what to do if neither authentication method passes. It also provides a reporting mechanism for email authentication results.

| Field | Value |
|-------|-------|
| **Domain to query** | `_dmarc.expatsinromania.org` |
| **Record type** | TXT |
| **Expected value** | `v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com` |

#### 5. MX (Mail Exchange)
**Purpose:** To specify the mail server responsible for receiving email on behalf of your domain. Without this record, your domain cannot receive email.

| Field | Value |
|-------|-------|
| **Domain to query** | `expatsinromania.org` |
| **Record type** | MX |
| **Expected value** | `mxdm-ap-southeast-1.aliyun.com` |

---

## Method 2: Windows Commands (Command Prompt / PowerShell)

Open **Command Prompt** (`cmd`) or **PowerShell** and run the following commands.

### Quick — Run All At Once

Copy and paste this batch into Command Prompt:

```batch
echo === 1. Ownership Verification (TXT) ===
nslookup -type=TXT aliyundm.expatsinromania.org

echo === 2. SPF Record (TXT) ===
nslookup -type=TXT expatsinromania.org

echo === 3. DKIM Record (TXT) ===
nslookup -type=TXT aliyun-ap-southeast-1._domainkey.expatsinromania.org

echo === 4. DMARC Record (TXT) ===
nslookup -type=TXT _dmarc.expatsinromania.org

echo === 5. MX Record ===
nslookup -type=MX expatsinromania.org
```

### Individual Commands with Expected Results

#### 1. Ownership Verification
**Purpose:** To prove that you own or control the domain name. This verification typically requires you to add a specific TXT record provided by the SP.

```batch
nslookup -type=TXT aliyundm.expatsinromania.org
```
**Expected result:**
```
Non-authoritative answer:
aliyundm.expatsinromania.org   text = "2640863cc4ce991e9f07"
```
✅ See `2640863cc4ce991e9f07` → **Ownership verified**

---

#### 2. SPF (Sender Policy Framework)
**Purpose:** To prevent sender spoofing by specifying a list of servers that are authorized to send email for your domain.

 **Important:** You can have only **one** SPF record. If you have multiple outbound IP addresses or mail providers, merge them into a single record.

```batch
nslookup -type=TXT expatsinromania.org
```
**Expected result:**
```
Non-authoritative answer:
expatsinromania.org   text = "v=spf1 include:spfdm-ap-southeast-1.aliyun.com -all"
```
✅ See `v=spf1 include:spfdm-ap-southeast-1.aliyun.com -all` → **SPF verified**

---

#### 3. DKIM (DomainKeys Identified Mail)
**Purpose:** To add a digital signature to your emails, allowing the receiving server to verify that the email was actually sent from your domain and was not altered in transit.

```batch
nslookup -type=TXT aliyun-ap-southeast-1._domainkey.expatsinromania.org
```
**Expected result:**
```
Non-authoritative answer:
aliyun-ap-southeast-1._domainkey.expatsinromania.org   text = "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCZa8NtJsJ1GtyALEh6P/RxzN/cUb8RcherMTbXNQr8lamGzyVOTxAqI1oBEF9g2en3QDde4H+6Ajtzs7barPsciK4Xc9xXdFimmSCAACMnZ9szuI6xTsIQp0xW74zixKPg2Xkra5rKYpbaBb2pSYX0hNx75dAP9TVB0kiUnsrqewIDAQAB"
```
✅ See the full DKIM key starting with `v=DKIM1` → **DKIM verified**

---

#### 4. DMARC (Domain-based Message Authentication, Reporting, and Conformance)
**Purpose:** To build on SPF and DKIM by telling receiving servers what to do if neither authentication method passes. It also provides a reporting mechanism for email authentication results.

```batch
nslookup -type=TXT _dmarc.expatsinromania.org
```
**Expected result:**
```
Non-authoritative answer:
_dmarc.expatsinromania.org   text = "v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com"
```
✅ See `v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com` → **DMARC verified**

---

#### 5. MX (Mail Exchange)
**Purpose:** To specify the mail server responsible for receiving email on behalf of your domain. Without this record, your domain cannot receive email.

```batch
nslookup -type=MX expatsinromania.org
```
**Expected result:**
```
Non-authoritative answer:
expatsinromania.org   MX preference = 10, mail exchanger = mxdm-ap-southeast-1.aliyun.com
```
✅ See `mxdm-ap-southeast-1.aliyun.com` → **MX verified**

---

### Flush DNS Cache (if records are not showing)
```batch
ipconfig /flushdns
```

---

## Method 3: macOS Commands (Terminal)

Open **Terminal** and run the following commands using `dig`.

### Quick — Run All At Once

```bash
echo "=== 1. Ownership Verification (TXT) ==="
dig TXT aliyundm.expatsinromania.org +short

echo "=== 2. SPF Record (TXT) ==="
dig TXT expatsinromania.org +short

echo "=== 3. DKIM Record (TXT) ==="
dig TXT aliyun-ap-southeast-1._domainkey.expatsinromania.org +short

echo "=== 4. DMARC Record (TXT) ==="
dig TXT _dmarc.expatsinromania.org +short

echo "=== 5. MX Record ==="
dig MX expatsinromania.org +short
```

### Individual Commands with Expected Results

#### 1. Ownership Verification
**Purpose:** To prove that you own or control the domain name. This verification typically requires you to add a specific TXT record provided by the SP.

```bash
dig TXT aliyundm.expatsinromania.org +short
```
**Expected result:**
```
"2640863cc4ce991e9f07"
```
✅ See `2640863cc4ce991e9f07` → **Ownership verified**

---

#### 2. SPF (Sender Policy Framework)
**Purpose:** To prevent sender spoofing by specifying a list of servers that are authorized to send email for your domain.

 **Important:** You can have only **one** SPF record. If you have multiple outbound IP addresses or mail providers, merge them into a single record.

```bash
dig TXT expatsinromania.org +short
```
**Expected result:**
```
"v=spf1 include:spfdm-ap-southeast-1.aliyun.com -all"
```
✅ See the SPF record → **SPF verified**

---

#### 3. DKIM (DomainKeys Identified Mail)
**Purpose:** To add a digital signature to your emails, allowing the receiving server to verify that the email was actually sent from your domain and was not altered in transit.

```bash
dig TXT aliyun-ap-southeast-1._domainkey.expatsinromania.org +short
```
**Expected result:**
```
"v=DKIM1\; k=rsa\; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCZa8NtJsJ1GtyALEh6P/RxzN/cUb8RcherMTbXNQr8lamGzyVOTxAqI1oBEF9g2en3QDde4H+6Ajtzs7barPsciK4Xc9xXdFimmSCAACMnZ9szuI6xTsIQp0xW74zixKPg2Xkra5rKYpbaBb2pSYX0hNx75dAP9TVB0kiUnsrqewIDAQAB"
```
✅ See the full DKIM key → **DKIM verified**

---

#### 4. DMARC (Domain-based Message Authentication, Reporting, and Conformance)
**Purpose:** To build on SPF and DKIM by telling receiving servers what to do if neither authentication method passes. It also provides a reporting mechanism for email authentication results.

```bash
dig TXT _dmarc.expatsinromania.org +short
```
**Expected result:**
```
"v=DMARC1\;p=none\;rua=mailto:dmarc_report@service.aliyun.com"
```
✅ See the DMARC policy → **DMARC verified**

---

#### 5. MX (Mail Exchange)
**Purpose:** To specify the mail server responsible for receiving email on behalf of your domain. Without this record, your domain cannot receive email.

```bash
dig MX expatsinromania.org +short
```
**Expected result:**
```
10 mxdm-ap-southeast-1.aliyun.com.
```
✅ See `mxdm-ap-southeast-1.aliyun.com` → **MX verified**

---

### Flush DNS Cache on macOS
```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

---

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `NXDOMAIN` or no answer | Record not added yet | Add the record in your DNS provider |
| Old/wrong values | DNS cache | Flush DNS cache (see above), wait 1–10 min |
| Still not showing after 10 min | Wrong host record format | Check DNS provider syntax (some use `@`, some leave blank) |
| DKIM value too short | Record was truncated | Ensure the full record value was pasted — no extra spaces or line breaks |
| Multiple SPF records | Duplicate TXT on root | There must be only ONE SPF TXT record on `@`. Merge all includes into one |

---

## Online Verification Tools (Bonus)

| Tool | URL | What It Checks |
|------|-----|----------------|
| **Alibaba Cloud DNS Check** | https://dnscheck.aliyun.com/ | All DNS records |
| **MXToolbox** | https://mxtoolbox.com/ | MX, SPF, DKIM, DMARC, Blacklists |
| **DMARC Analyzer** | https://www.dmarcanalyzer.com/ | DMARC, SPF, DKIM |
| **DNS Checker** | https://dnschecker.org/ | Global DNS propagation |
| **Mail Tester** | https://www.mail-tester.com/ | Full email deliverability score |

### Quick Links via MXToolbox
- SPF: `https://mxtoolbox.com/Spf.aspx?domain=expatsinromania.org`
- MX: `https://mxtoolbox.com/MXLookup.aspx?domain=expatsinromania.org`
- DMARC: `https://mxtoolbox.com/DMARC.aspx?domain=expatsinromania.org`

---

## Verification Status Tracker

| # | Record | Method 1: Alibaba Tool | Method 2: Windows | Method 3: macOS | Alibaba Console |
|---|--------|:----------------------:|:------------------:|:----------------:|:----------------:|
| 1 | Ownership TXT | [ ] | [ ] | [ ] | [ ] |
| 2 | SPF TXT | [ ] | [ ] | [ ] | [ ] |
| 3 | DKIM TXT | [ ] | [ ] | [ ] | [ ] |
| 4 | DMARC TXT | [ ] | [ ] | [ ] | [ ] |
| 5 | MX Record | [ ] | [ ] | [ ] | [ ] |

---

---

## Appendix: Subdomain Example — China (Hangzhou) Region

### Understanding the Subdomain Structure

The domain **sub.example.com** is a subdomain of **example.com**:

```
example.com                    ← Root domain (parent)
└── sub.example.com            ← Subdomain (prefix = "sub")
```

- **Root domain:** `example.com`
- **Subdomain prefix:** `sub`
- **Full subdomain:** `sub.example.com`

When configuring DNS records for a subdomain, the **host record** changes to include the subdomain prefix `sub`. This is different from a root domain configuration where the host record is typically `@` or left blank.

### How Host Records Differ: Root Domain vs Subdomain

| Record | Root Domain Host Record | Subdomain Host Record |
|--------|------------------------|-----------------------|
| Ownership | `aliyundm` at `example.com` | `aliyundm.sub` at `example.com` |
| SPF | `@` at `example.com` | `sub` at `example.com` |
| DKIM | `aliyun-cn-hangzhou._domainkey` at `example.com` | `aliyun-cn-hangzhou._domainkey.sub` at `example.com` |
| DMARC | `_dmarc` at `example.com` | `_dmarc.sub` at `example.com` |
| MX | `@` at `example.com` | `sub` at `example.com` |

> **Rule:** For a subdomain, append the prefix `sub` to the host record. The records are added in the **root domain's** (`example.com`) DNS zone, not in a separate zone.

The examples below demonstrate DNS verification using the subdomain **sub.example.com** in the **China (Hangzhou)** region (`cn-hangzhou`). This follows the same verification process but uses different host records and server endpoints specific to the Hangzhou region.

### DNS Records for sub.example.com (Hangzhou Region)

These records are added in the DNS zone of **example.com** (the root domain):

| # | Type | Host Record (in example.com zone) | Full FQDN | Record Value |
|---|------|-----------------------------------|-----------|--------------|
| 1 | TXT | `aliyundm.sub` | `aliyundm.sub.example.com` | *(ownership token provided by Alibaba)* |
| 2 | TXT | `sub` | `sub.example.com` | `v=spf1 include:spfdm-cn-hangzhou.aliyun.com -all` |
| 3 | TXT | `aliyun-cn-hangzhou._domainkey.sub` | `aliyun-cn-hangzhou._domainkey.sub.example.com` | `v=DKIM1; k=rsa; p=...` *(key provided by Alibaba)* |
| 4 | TXT | `_dmarc.sub` | `_dmarc.sub.example.com` | `v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com` |
| 5 | MX | `sub` | `sub.example.com` | `mxdm-cn-hangzhou.aliyun.com` |

> **Key differences from root domain setup:**  
> 1. **Host records** include the subdomain prefix `sub` (e.g., `sub` instead of `@`, `aliyundm.sub` instead of `aliyundm`)  
> 2. **Region endpoints** use `cn-hangzhou` instead of `ap-southeast-1` (SPF include, DKIM selector, MX server)

---

### Method 1: Alibaba Cloud DNS Check Tool (Hangzhou Example)

🔗 **https://dnscheck.aliyun.com/**

| # | Record Type | Full FQDN to Query | Notes |
|---|------------|-------------------|-------|
| 1 | TXT | `aliyundm.sub.example.com` | Ownership — note `aliyundm.sub` prefix |
| 2 | TXT | `sub.example.com` | SPF — the subdomain itself |
| 3 | TXT | `aliyun-cn-hangzhou._domainkey.sub.example.com` | DKIM — selector includes subdomain |
| 4 | TXT | `_dmarc.sub.example.com` | DMARC — `_dmarc` + subdomain prefix |
| 5 | MX | `sub.example.com` | MX — the subdomain itself |

---

### Method 2: Windows Commands — sub.example.com (Hangzhou)

```batch
echo === 1. Ownership Verification (TXT) ===
nslookup -type=TXT aliyundm.sub.example.com

echo === 2. SPF Record (TXT) ===
nslookup -type=TXT sub.example.com

echo === 3. DKIM Record (TXT) ===
nslookup -type=TXT aliyun-cn-hangzhou._domainkey.sub.example.com

echo === 4. DMARC Record (TXT) ===
nslookup -type=TXT _dmarc.sub.example.com

echo === 5. MX Record ===
nslookup -type=MX sub.example.com
```

#### Expected Results

#### 1. Ownership
**Purpose:** To prove that you own or control the domain name. This verification typically requires you to add a specific TXT record provided by the SP.
```
Non-authoritative answer:
aliyundm.sub.example.com   text = "<ownership-token>"
```

**2. SPF:**
**Purpose:** To prevent sender spoofing by specifying a list of servers that are authorized to send email for your domain.

 **Important:** You can have only **one** SPF record. If you have multiple outbound IP addresses or mail providers, merge them into a single record.
```
Non-authoritative answer:
sub.example.com   text = "v=spf1 include:spfdm-cn-hangzhou.aliyun.com -all"
```

**3. DKIM:**
**Purpose:** To add a digital signature to your emails, allowing the receiving server to verify that the email was actually sent from your domain and was not altered in transit.
```
Non-authoritative answer:
aliyun-cn-hangzhou._domainkey.sub.example.com   text = "v=DKIM1; k=rsa; p=<DKIM-public-key>"
```

**4. DMARC:**
**Purpose:** To build on SPF and DKIM by telling receiving servers what to do if neither authentication method passes. It also provides a reporting mechanism for email authentication results.
```
Non-authoritative answer:
_dmarc.sub.example.com   text = "v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com"
```

**5. MX:**
**Purpose:** To specify the mail server responsible for receiving email on behalf of your domain. Without this record, your domain cannot receive email.
```
Non-authoritative answer:
sub.example.com   MX preference = 10, mail exchanger = mxdm-cn-hangzhou.aliyun.com
```

---

### Method 3: macOS Commands — sub.example.com (Hangzhou)

```bash
echo "=== 1. Ownership Verification (TXT) ==="
dig TXT aliyundm.sub.example.com +short

echo "=== 2. SPF Record (TXT) ==="
dig TXT sub.example.com +short

echo "=== 3. DKIM Record (TXT) ==="
dig TXT aliyun-cn-hangzhou._domainkey.sub.example.com +short

echo "=== 4. DMARC Record (TXT) ==="
dig TXT _dmarc.sub.example.com +short

echo "=== 5. MX Record ==="
dig MX sub.example.com +short
```

#### Expected Results

| # | Record | Purpose | Expected `dig` Output |
|---|--------|---------|----------------------|
| 1 | Ownership | Prove you own or control the domain name | `"<ownership-token>"` |
| 2 | SPF | Prevent sender spoofing by specifying authorized mail servers | `"v=spf1 include:spfdm-cn-hangzhou.aliyun.com -all"` |
| 3 | DKIM | Add digital signature to verify email authenticity and integrity | `"v=DKIM1\; k=rsa\; p=<DKIM-public-key>"` |
| 4 | DMARC | Tell receiving servers what to do if SPF/DKIM fail; provides reporting | `"v=DMARC1\;p=none\;rua=mailto:dmarc_report@service.aliyun.com"` |
| 5 | MX | Specify mail server that receives email for your domain | `10 mxdm-cn-hangzhou.aliyun.com.` |

---

### Region Reference Table

When configuring Alibaba Mail for different regions, the server endpoints change. Replace the region code in all record values:

| Region | Region Code | SPF Include | DKIM Selector | MX Server |
|--------|------------|-------------|---------------|-----------|
| China (Hangzhou) | `cn-hangzhou` | `spfdm-cn-hangzhou.aliyun.com` | `aliyun-cn-hangzhou._domainkey` | `mxdm-cn-hangzhou.aliyun.com` |
| China (Shanghai) | `cn-shanghai` | `spfdm-cn-shanghai.aliyun.com` | `aliyun-cn-shanghai._domainkey` | `mxdm-cn-shanghai.aliyun.com` |
| China (Beijing) | `cn-beijing` | `spfdm-cn-beijing.aliyun.com` | `aliyun-cn-beijing._domainkey` | `mxdm-cn-beijing.aliyun.com` |
| China (Shenzhen) | `cn-shenzhen` | `spfdm-cn-shenzhen.aliyun.com` | `aliyun-cn-shenzhen._domainkey` | `mxdm-cn-shenzhen.aliyun.com` |
| Singapore | `ap-southeast-1` | `spfdm-ap-southeast-1.aliyun.com` | `aliyun-ap-southeast-1._domainkey` | `mxdm-ap-southeast-1.aliyun.com` |
| Hong Kong | `cn-hongkong` | `spfdm-cn-hongkong.aliyun.com` | `aliyun-cn-hongkong._domainkey` | `mxdm-cn-hongkong.aliyun.com` |
| Australia (Sydney) | `ap-southeast-2` | `spfdm-ap-southeast-2.aliyun.com` | `aliyun-ap-southeast-2._domainkey` | `mxdm-ap-southeast-2.aliyun.com` |
| Germany (Frankfurt) | `eu-central-1` | `spfdm-eu-central-1.aliyun.com` | `aliyun-eu-central-1._domainkey` | `mxdm-eu-central-1.aliyun.com` |
| US (Virginia) | `us-east-1` | `spfdm-us-east-1.aliyun.com` | `aliyun-us-east-1._domainkey` | `mxdm-us-east-1.aliyun.com` |
| Japan (Tokyo) | `ap-northeast-1` | `spfdm-ap-northeast-1.aliyun.com` | `aliyun-ap-northeast-1._domainkey` | `mxdm-ap-northeast-1.aliyun.com` |

> **Pattern:** `spfdm-<region-code>.aliyun.com` / `aliyun-<region-code>._domainkey` / `mxdm-<region-code>.aliyun.com`

---

*Last updated: Jan 6, 2026, 11:27:46 UTC*
