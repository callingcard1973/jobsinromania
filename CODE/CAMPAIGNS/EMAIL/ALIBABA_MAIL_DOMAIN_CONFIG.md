# Alibaba Mail Domain Configuration — expatsinromania.org

> **Date Created:** 2026-04-08  
> **Mail Provider:** Alibaba Cloud (Aliyun DirectMail)  
> **Region:** ap-southeast-1  
> **Domain:** expatsinromania.org  
> **Status:** ⏳ Pending DNS Configuration & Verification

---

## Overview

This document records all DNS records required by Alibaba Mail (AliyunDM) for the domain `expatsinromania.org`. Add these records at your DNS service provider. Configuration typically takes **1–10 minutes** to take effect. Click **"Refresh"** in the Alibaba Mail console to verify.

---

## DNS Records to Configure

### 1. Ownership Verification (TXT)

| Field         | Value                                      |
|---------------|--------------------------------------------|
| **Type**      | TXT                                        |
| **Host Record** | `aliyundm`                              |
| **Domain**    | expatsinromania.org                        |
| **Record Value** | `2640863cc4ce991e9f07`                  |
| **Status**    | To Be Verified                             |

> This proves you own the domain. Must be verified first before other records take effect.

---

### 2. SPF Verification (TXT)

| Field         | Value                                                        |
|---------------|--------------------------------------------------------------|
| **Type**      | TXT                                                          |
| **Host Record** | `@` (or leave blank depending on DNS provider)             |
| **Domain**    | expatsinromania.org                                          |
| **Record Value** | `v=spf1 include:spfdm-ap-southeast-1.aliyun.com -all`    |
| **Status**    | To Be Verified                                               |

> **Note:** If you already have an existing SPF record for this domain, append `include:spfdm-ap-southeast-1.aliyun.com` to it instead of creating a duplicate. Multiple SPF records will cause delivery failures.

---

### 3. DKIM Verification (TXT)

| Field         | Value                                                                                                                                                                                                                                     |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Type**      | TXT                                                                                                                                                                                                                                       |
| **Host Record** | `aliyun-ap-southeast-1._domainkey`                                                                                                                                                                                                     |
| **Domain**    | expatsinromania.org                                                                                                                                                                                                                       |
| **Record Value** | `v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCZa8NtJsJ1GtyALEh6P/RxzN/cUb8RcherMTbXNQr8lamGzyVOTxAqI1oBEF9g2en3QDde4H+6Ajtzs7barPsciK4Xc9xXdFimmSCAACMnZ9szuI6xTsIQp0xW74zixKPg2Xkra5rKYpbaBb2pSYX0hNx75dAP9TVB0kiUnsrqewIDAQAB` |
| **Key Size**  | 1024-Bit                                                                                                                                                                                                                                  |
| **Status**    | To Be Verified                                                                                                                                                                                                                            |

> **Note:** DKIM prevents domain spoofing and reduces the chance of emails being marked as spam. **Strongly recommended** if sending to Gmail and Yahoo to comply with their sender requirements.

---

### 4. DMARC Verification (TXT)

| Field         | Value                                                              |
|---------------|--------------------------------------------------------------------|
| **Type**      | TXT                                                                |
| **Host Record** | `_dmarc`                                                         |
| **Domain**    | expatsinromania.org                                                |
| **Record Value** | `v=DMARC1;p=none;rua=mailto:dmarc_report@service.aliyun.com`    |
| **Status**    | To Be Verified                                                     |

> **Note:** DMARC ensures sender identity authenticity and prevents fraudulent use of your domain. **Strongly recommended** for Gmail and Yahoo delivery compliance.  
> **Policy `p=none`** = monitor mode only (no rejection). Consider upgrading to `p=quarantine` or `p=reject` after monitoring reports.

---

### 5. MX Record Verification (Email Receiving)

| Field         | Value                                      |
|---------------|--------------------------------------------|
| **Type**      | MX                                         |
| **Host Record** | `@` (or leave blank)                     |
| **Domain**    | expatsinromania.org                        |
| **Priority**  | `10` *(use default if unspecified)*        |
| **Record Value** | `mxdm-ap-southeast-1.aliyun.com`        |
| **Status**    | To Be Verified                             |

> ⚠️ **Critical:** MX records are required for **receiving** email. Without them, you cannot receive mail on this domain. Add these in your DNS provider and keep them active at all times.

---

## Step-by-Step Verification Guide

### Step 1: Log in to your DNS Provider
- Go to the DNS management panel for `expatsinromania.org`
- Navigate to **DNS Records** or **Zone Editor**

### Step 2: Add Records in This Order
1. ✅ **Ownership TXT** (`aliyundm`) — verify ownership first
2. ✅ **SPF TXT** (`@`) — authorize Alibaba Mail servers
3. ✅ **DKIM TXT** (`aliyun-ap-southeast-1._domainkey`) — email signing
4. ✅ **DMARC TXT** (`_dmarc`) — sender policy framework
5. ✅ **MX Record** (`@`) — email receiving

### Step 3: Wait for Propagation
- Alibaba says **1–10 minutes** for their system
- Full DNS propagation may take up to **24–48 hours** globally

### Step 4: Verify in Alibaba Mail Console
- Go back to the Alibaba Mail domain configuration page
- Click **"Refresh"** button for each record
- Status should change from **"To Be Verified"** → **"Verified"** ✅

### Step 5: Verify with External Tools (Optional)
```bash
# Check TXT records
nslookup -type=TXT aliyundm.expatsinromania.org
nslookup -type=TXT expatsinromania.org
nslookup -type=TXT aliyun-ap-southeast-1._domainkey.expatsinromania.org
nslookup -type=TXT _dmarc.expatsinromania.org

# Check MX records
nslookup -type=MX expatsinromania.org
```

---

## DNS Record Summary (Quick Reference)

| # | Type | Host Record                           | Purpose              | Priority |
|---|------|---------------------------------------|----------------------|----------|
| 1 | TXT  | `aliyundm`                            | Ownership Verification | —      |
| 2 | TXT  | `@`                                   | SPF (Sender Policy)  | —        |
| 3 | TXT  | `aliyun-ap-southeast-1._domainkey`    | DKIM (Email Signing) | —        |
| 4 | TXT  | `_dmarc`                              | DMARC (Anti-Fraud)   | —        |
| 5 | MX   | `@`                                   | Mail Receiving       | `mxdm-ap-southeast-1.aliyun.com` |

---

## Important Notes

- **SPF:** Do NOT create multiple SPF TXT records on the root domain. Merge includes into a single record.
- **DKIM & DMARC:** Essential for delivery to **Gmail** and **Yahoo** — these providers enforce strict sender authentication (2024+ policy).
- **MX Records:** Must remain active permanently; removing them will break email receiving.
- **Region:** All records reference `ap-southeast-1` — ensure this matches your Alibaba Mail subscription region.

---

## Status Tracker

| Record     | Added to DNS | Verified in Alibaba | Propagation Checked |
|------------|:------------:|:-------------------:|:-------------------:|
| Ownership  | [ ]          | [ ]                 | [ ]                 |
| SPF        | [ ]          | [ ]                 | [ ]                 |
| DKIM       | [ ]          | [ ]                 | [ ]                 |
| DMARC      | [ ]          | [ ]                 | [ ]                 |
| MX Record  | [ ]          | [ ]                 | [ ]                 |

---

*Last updated: Jan 6, 2026, 11:27:46 UTC*
