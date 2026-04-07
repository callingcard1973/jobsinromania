# Distributed Academic Security Lab Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a simplified distributed academic security research platform with Windows 11 research station and raspibig penetration testing engine.

**Architecture:** Distributed approach using Windows laptop (GUI tools, documentation, analysis) and Raspberry Pi (headless penetration testing, data collection) with secure communication channel and basic network isolation.

**Tech Stack:** Windows 11 Pro, Ubuntu/Kali Linux, Python 3.12, PostgreSQL, Docker, TLS/SSL, REST API

---

## Chunk 1: Core Infrastructure Setup

### Task 1: Create Security Project Directory Structure

**Files:**
- Create: `D:\MEMORY\SECURITY\CLAUDE.md`
- Create: `D:\MEMORY\SECURITY\setup\windows_setup.ps1`
- Create: `D:\MEMORY\SECURITY\setup\raspibig_setup.sh`
- Create: `D:\MEMORY\SECURITY\config\security_config.yml`
- Create: `D:\MEMORY\SECURITY\logs\setup.log`

- [ ] **Step 1: Create main security CLAUDE.md documentation**

```markdown
# SECURITY.md

## What This Is

D:\MEMORY\SECURITY — Academic cybersecurity research platform for educational WiFi security analysis and penetration testing methodology.

## Infrastructure

- **Windows 11 Research Station** (192.168.100.25): GUI tools, documentation, analysis platform
- **Raspibig Penetration Testing Engine** (192.168.100.21): Headless testing, data collection, WiFi research
- **Secure Communication**: TLS-encrypted REST API between systems
- **Network Isolation**: Software-based research network segmentation

## Academic Research Focus

- **WiFi Security Analysis**: Protocol research, vulnerability assessment (own networks only)
- **Penetration Testing Methodology**: Educational attack chain analysis
- **Network Security Research**: Academic study of defensive mechanisms
- **Documentation Standards**: Reproducible research methodology

## Legal and Ethical Framework

**AUTHORIZED RESEARCH ONLY**: This platform is designed exclusively for:
- Academic research and education
- Networks owned by the researcher
- Authorized testing with explicit written permission
- Controlled lab environments

**PROHIBITED**: Any unauthorized network access, illegal activities, or unethical research practices.

## Core Tools

### Windows 11 Research Station
- **Analysis**: Wireshark, NetworkMiner, Gephi
- **Documentation**: Obsidian, LaTeX, Jupyter Notebooks
- **Web Security**: Burp Suite, OWASP ZAP
- **Visualization**: Python data analysis stack

### Raspibig Penetration Testing Engine
- **WiFi Research**: Aircrack-ng, Kismet, WiFite2
- **Network Discovery**: Nmap, Masscan, Netdiscover
- **Framework**: Metasploit, custom scripts
- **Data Collection**: PostgreSQL, automated logging

## Quick Commands

- `security-status` — Check platform status
- `start-research <project>` — Begin documented research session
- `collect-data <target>` — Automated data collection (authorized only)
- `generate-report <project>` — Create academic research report

## Sensitive Files
- `config/security_config.yml` — API keys and credentials
- `research/active/` — Current research data
- `logs/audit/` — Activity audit trails
```

- [ ] **Step 2: Create Windows setup PowerShell script**

```powershell
# windows_setup.ps1 - Academic Security Research Station Setup

Write-Host "Setting up Windows 11 Academic Security Research Station..." -ForegroundColor Cyan

# Create directory structure
$SecurityRoot = "D:\MEMORY\SECURITY"
$Directories = @(
    "tools",
    "research\projects", 
    "research\templates",
    "research\reports",
    "data\raw",
    "data\processed", 
    "logs\audit",
    "config",
    "scripts\windows",
    "docs\methodology"
)

foreach ($dir in $Directories) {
    $fullPath = Join-Path $SecurityRoot $dir
    if (!(Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force
        Write-Host "Created: $fullPath" -ForegroundColor Green
    }
}

# Check for existing tools and create installation checklist
$RequiredTools = @{
    "Wireshark" = "https://www.wireshark.org/download.html"
    "Python 3.12" = "Already installed"
    "Git" = "git --version"
    "VS Code" = "code --version"
    "VirtualBox" = "https://www.virtualbox.org/wiki/Downloads"
}

Write-Host "`nTool Installation Status:" -ForegroundColor Yellow
foreach ($tool in $RequiredTools.Keys) {
    $status = $RequiredTools[$tool]
    Write-Host "  $tool`: $status" -ForegroundColor White
}

# Create Python virtual environment for security tools
$VenvPath = Join-Path $SecurityRoot "venv"
if (!(Test-Path $VenvPath)) {
    Write-Host "`nCreating Python virtual environment..." -ForegroundColor Cyan
    python -m venv "$VenvPath"
    & "$VenvPath\Scripts\Activate.ps1"
    pip install --upgrade pip
    Write-Host "Virtual environment created at: $VenvPath" -ForegroundColor Green
}

# Log setup completion
$LogEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Windows setup completed successfully"
Add-Content -Path "$SecurityRoot\logs\setup.log" -Value $LogEntry

Write-Host "`nWindows Security Research Station setup complete!" -ForegroundColor Green
Write-Host "Next: Run raspibig_setup.sh on the Raspberry Pi" -ForegroundColor Yellow
```

- [ ] **Step 3: Create Raspibig setup shell script**

```bash
#!/bin/bash
# raspibig_setup.sh - Academic Penetration Testing Engine Setup

echo "Setting up Raspibig Academic Penetration Testing Engine..."

# Create directory structure
SECURITY_ROOT="/opt/SECURITY"
sudo mkdir -p "$SECURITY_ROOT"/{tools,research/{projects,data,logs},config,scripts/raspibig,docs}

# Set permissions
sudo chown -R tudor:tudor "$SECURITY_ROOT"
chmod 750 "$SECURITY_ROOT"

# Update system packages
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential security tools
echo "Installing core security packages..."
sudo apt install -y \
    aircrack-ng \
    wireshark-common \
    nmap \
    masscan \
    netdiscover \
    kismet \
    hashcat \
    john \
    hydra \
    sqlmap \
    nikto \
    dirb \
    gobuster \
    wget \
    curl \
    git \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    docker.io \
    docker-compose

# Add user to required groups for wireless tools
sudo usermod -a -G wireshark,docker tudor

# Create Python virtual environment
python3 -m venv "$SECURITY_ROOT/venv"
source "$SECURITY_ROOT/venv/bin/activate"
pip install --upgrade pip

# Install Python security libraries
pip install \
    scapy \
    impacket \
    requests \
    psycopg2-binary \
    flask \
    python-dotenv \
    cryptography \
    paramiko \
    netaddr

# Setup PostgreSQL for research data
sudo -u postgres createuser tudor
sudo -u postgres createdb security_research -O tudor

# Create basic security configuration
cat > "$SECURITY_ROOT/config/security_config.yml" << 'EOF'
# Academic Security Research Configuration
research:
  authorized_networks:
    - "192.168.100.0/24"  # Own network only
  data_retention_days: 90
  enable_audit_logging: true
  
database:
  host: "localhost"
  port: 5432
  name: "security_research"
  user: "tudor"
  
api:
  host: "0.0.0.0"
  port: 8443
  ssl_enabled: true
  cert_path: "/opt/SECURITY/config/server.crt"
  key_path: "/opt/SECURITY/config/server.key"

tools:
  nmap_max_rate: 1000
  aircrack_wordlist: "/usr/share/wordlists/rockyou.txt"
  kismet_log_dir: "/opt/SECURITY/research/data/kismet"
EOF

# Log setup completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Raspibig setup completed successfully" >> "$SECURITY_ROOT/logs/setup.log"

echo "Raspibig Penetration Testing Engine setup complete!"
echo "Reboot required for group changes to take effect."
```

- [ ] **Step 4: Create unified configuration file**

```yaml
# security_config.yml - Distributed Academic Security Lab Configuration

lab_info:
  name: "Academic Security Research Lab"
  purpose: "Educational cybersecurity research and methodology"
  established: "2026-04-07"
  
infrastructure:
  windows_station:
    hostname: "laptop"
    ip: "192.168.100.25"
    role: "research_documentation_analysis"
    os: "Windows 11 Pro"
  
  raspibig_engine:
    hostname: "raspibig" 
    ip: "192.168.100.21"
    role: "penetration_testing_data_collection"
    os: "Ubuntu/Debian + Kali tools"

network:
  production_vlan: "192.168.100.0/24"
  research_subnet: "192.168.200.0/24"
  isolation_method: "software_based"
  
communication:
  protocol: "HTTPS/TLS"
  api_port: 8443
  auth_method: "JWT_tokens"
  encryption: "AES-256"

research_settings:
  authorized_targets:
    - "192.168.100.0/24"  # Own network
    - "192.168.200.0/24"  # Research subnet
  prohibited_targets:
    - "0.0.0.0/0"  # No external scanning
  max_scan_rate: 1000
  audit_logging: true
  data_retention_days: 90

academic_compliance:
  irb_approval_required: true
  ethics_checklist_mandatory: true
  research_documentation: "mandatory"
  legal_disclaimer: "required_all_activities"
```

- [ ] **Step 5: Initialize security project and commit setup**

```bash
cd "D:\MEMORY\SECURITY"
git init
git add .
git commit -m "Initial academic security lab setup

- Create project directory structure
- Add Windows and Raspibig setup scripts
- Configure basic security parameters
- Establish academic research framework

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>"
```

### Task 2: Install Core Windows Research Tools

**Files:**
- Create: `D:\MEMORY\SECURITY\scripts\windows\install_research_tools.ps1`
- Create: `D:\MEMORY\SECURITY\scripts\windows\setup_python_security.ps1`
- Create: `D:\MEMORY\SECURITY\tools\requirements.txt`

- [ ] **Step 1: Create comprehensive Windows tools installer**

```powershell
# install_research_tools.ps1 - Install core academic security research tools

param(
    [switch]$SkipCommercial,
    [switch]$EducationalOnly
)

Write-Host "Installing Academic Security Research Tools for Windows 11..." -ForegroundColor Cyan

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator. Please restart as Administrator."
    exit 1
}

# Install Chocolatey package manager if not present
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey package manager..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    
    # Secure Chocolatey installation with verification
    $ChocolateyUrl = 'https://community.chocolatey.org/install.ps1'
    $ChocolateyScript = Join-Path $env:TEMP "chocolatey-install.ps1"
    
    try {
        # Download securely over HTTPS
        Invoke-WebRequest -Uri $ChocolateyUrl -OutFile $ChocolateyScript -UseBasicParsing
        
        # Verify the script is from Chocolatey (basic check)
        $Content = Get-Content $ChocolateyScript -Raw
        if ($Content -match "chocolatey\.org" -and $Content -match "Set-ExecutionPolicy") {
            Write-Host "Chocolatey script verified, installing..." -ForegroundColor Green
            & $ChocolateyScript
        } else {
            Write-Error "Chocolatey script verification failed"
            exit 1
        }
    } finally {
        # Clean up downloaded script
        if (Test-Path $ChocolateyScript) {
            Remove-Item $ChocolateyScript -Force
        }
    }
}

# Core networking and analysis tools
$CoreTools = @(
    "wireshark",           # Protocol analysis
    "nmap",                # Network discovery
    "git",                 # Version control
    "vscode",              # Code editor
    "python3",             # Programming environment
    "nodejs",              # Web tools support
    "curl",                # HTTP testing
    "wget",                # File downloads
    "7zip",                # Archive handling
    "notepadplusplus"      # Text editing
)

Write-Host "`nInstalling core tools..." -ForegroundColor Yellow
foreach ($tool in $CoreTools) {
    try {
        Write-Host "Installing $tool..." -ForegroundColor White
        choco install $tool -y --no-progress
        Write-Host "✓ $tool installed successfully" -ForegroundColor Green
    } catch {
        Write-Warning "Failed to install $tool`: $_"
    }
}

# Educational tools (free versions)
if ($EducationalOnly) {
    $EducationalTools = @(
        "burp-suite-free-edition",  # Web security testing
        "owasp-zap",                # Web application security scanner
        "virtualbox"                # Virtualization platform
    )
    
    Write-Host "`nInstalling educational security tools..." -ForegroundColor Yellow
    foreach ($tool in $EducationalTools) {
        try {
            Write-Host "Installing $tool..." -ForegroundColor White
            choco install $tool -y --no-progress
            Write-Host "✓ $tool installed successfully" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to install $tool`: $_"
        }
    }
}

# Commercial tools (require licenses)
if (!$SkipCommercial) {
    Write-Host "`nCommercial tools requiring licenses:" -ForegroundColor Yellow
    Write-Host "  • Burp Suite Professional (educational discount available)" -ForegroundColor White
    Write-Host "  • VMware Workstation Pro (educational pricing)" -ForegroundColor White
    Write-Host "  • Nessus Professional (educational license)" -ForegroundColor White
    Write-Host "  Note: Install these manually with your educational credentials" -ForegroundColor Cyan
}

# Create tool verification script
$VerificationScript = @"
# Tool verification checklist
Write-Host "Verifying installed tools..." -ForegroundColor Cyan

`$tools = @{
    "Python" = { python --version }
    "Git" = { git --version }
    "Nmap" = { nmap --version }
    "Wireshark" = { Get-Process tshark -ErrorAction SilentlyContinue }
    "Node.js" = { node --version }
    "VS Code" = { code --version }
}

foreach (`$tool in `$tools.Keys) {
    try {
        `$result = & `$tools[`$tool]
        Write-Host "✓ `$tool`: Working" -ForegroundColor Green
    } catch {
        Write-Host "✗ `$tool`: Not found or not working" -ForegroundColor Red
    }
}
"@

Set-Content -Path "D:\MEMORY\SECURITY\scripts\windows\verify_tools.ps1" -Value $VerificationScript

Write-Host "`nTool installation completed!" -ForegroundColor Green
Write-Host "Run 'D:\MEMORY\SECURITY\scripts\windows\verify_tools.ps1' to verify installations" -ForegroundColor Yellow
```

- [ ] **Step 2: Create Python security environment setup**

```powershell
# setup_python_security.ps1 - Setup Python environment for security research

Write-Host "Setting up Python Security Research Environment..." -ForegroundColor Cyan

# Activate security virtual environment
$VenvPath = "D:\MEMORY\SECURITY\venv"
if (Test-Path "$VenvPath") {
    & "$VenvPath\Scripts\Activate.ps1"
    Write-Host "Activated security virtual environment" -ForegroundColor Green
} else {
    Write-Error "Virtual environment not found. Run windows_setup.ps1 first."
    exit 1
}

# Install essential Python security packages
$SecurityPackages = @(
    "scapy",                    # Packet manipulation
    "impacket",                 # Windows protocols
    "requests",                 # HTTP library
    "beautifulsoup4",           # Web scraping
    "selenium",                 # Web automation
    "cryptography",             # Cryptographic operations
    "paramiko",                 # SSH client
    "python-nmap",              # Nmap integration
    "netaddr",                  # Network address manipulation
    "psycopg2",                 # PostgreSQL adapter
    "flask",                    # Web framework for APIs
    "flask-restful",            # REST API framework
    "python-dotenv",            # Environment variables
    "jupyter",                  # Interactive notebooks
    "matplotlib",               # Data visualization
    "pandas",                   # Data analysis
    "numpy",                    # Numerical computing
    "seaborn"                   # Statistical visualization
)

Write-Host "`nInstalling Python security packages..." -ForegroundColor Yellow

# Create requirements.txt file
$RequirementsContent = @"
# Academic Security Research Python Requirements
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# Core Security Libraries
scapy>=2.5.0
impacket>=0.11.0
cryptography>=41.0.0
paramiko>=3.3.0

# Network Analysis
python-nmap>=0.7.1
netaddr>=0.9.0
requests>=2.31.0
beautifulsoup4>=4.12.0
selenium>=4.15.0

# Database and APIs  
psycopg2>=2.9.7
flask>=2.3.0
flask-restful>=0.3.10
python-dotenv>=1.0.0

# Data Analysis and Visualization
jupyter>=1.0.0
matplotlib>=3.7.0
pandas>=2.1.0
numpy>=1.25.0
seaborn>=0.12.0

# Development Tools
pylint>=2.17.0
black>=23.7.0
pytest>=7.4.0
"@

Set-Content -Path "D:\MEMORY\SECURITY\tools\requirements.txt" -Value $RequirementsContent

# Install packages from requirements.txt
Write-Host "Installing from requirements.txt..." -ForegroundColor White
pip install -r "D:\MEMORY\SECURITY\tools\requirements.txt"

# Verify installations
Write-Host "`nVerifying Python package installations..." -ForegroundColor Yellow
$TestScript = @"
import sys
packages = ['scapy', 'impacket', 'requests', 'cryptography', 'flask', 'pandas', 'numpy']
failed = []

for package in packages:
    try:
        __import__(package)
        print(f'✓ {package}')
    except ImportError:
        print(f'✗ {package}')
        failed.append(package)

if failed:
    print(f'\\nFailed packages: {failed}')
    sys.exit(1)
else:
    print('\\nAll packages installed successfully!')
"@

python -c $TestScript

Write-Host "`nPython security environment setup complete!" -ForegroundColor Green
```

- [ ] **Step 3: Create Python requirements file**

```text
# Academic Security Research Python Requirements
# Generated: 2026-04-07

# Core Security Libraries
scapy>=2.5.0
impacket>=0.11.0
cryptography>=41.0.0
paramiko>=3.3.0

# Network Analysis
python-nmap>=0.7.1
netaddr>=0.9.0
requests>=2.31.0
beautifulsoup4>=4.12.0
selenium>=4.15.0

# Database and APIs
psycopg2>=2.9.7
flask>=2.3.0
flask-restful>=0.3.10
python-dotenv>=1.0.0

# Data Analysis and Visualization
jupyter>=1.0.0
matplotlib>=3.7.0
pandas>=2.1.0
numpy>=1.25.0
seaborn>=0.12.0

# Development Tools
pylint>=2.17.0
black>=23.7.0
pytest>=7.4.0
```

- [ ] **Step 4: Run Windows setup script**

```powershell
# Execute Windows setup with educational tools
cd "D:\MEMORY\SECURITY"
.\setup\windows_setup.ps1
.\scripts\windows\install_research_tools.ps1 -EducationalOnly
.\scripts\windows\setup_python_security.ps1
.\scripts\windows\verify_tools.ps1
```

- [ ] **Step 5: Commit Windows setup completion**

```bash
cd "D:\MEMORY\SECURITY"
git add scripts/ tools/
git commit -m "Complete Windows research station setup

- Install core security research tools
- Setup Python security environment
- Add tool verification scripts
- Configure educational tool stack

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>"
```

## Chunk 2: Raspibig Penetration Testing Platform

### Task 3: Deploy Raspibig Security Environment

**Files:**
- Create: `/opt/SECURITY/scripts/raspibig/install_penetration_tools.sh`
- Create: `/opt/SECURITY/scripts/raspibig/configure_database.sh`
- Create: `/opt/SECURITY/scripts/raspibig/setup_wifi_research.sh`
- Create: `/opt/SECURITY/config/penetration_config.yml`

- [ ] **Step 1: Create comprehensive penetration tools installer**

```bash
#!/bin/bash
# install_penetration_tools.sh - Install academic penetration testing tools

set -euo pipefail

echo "Installing Academic Penetration Testing Tools on Raspibig..."

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
    echo "Error: This script requires sudo privileges"
    exit 1
fi

# Update package lists
echo "Updating package lists..."
sudo apt update

# Install Kali Linux keyring and repository with verification
echo "Adding Kali Linux repository for latest security tools..."
sudo apt install -y wget gpg

# Download and verify Kali signing key
KALI_KEY_URL="https://archive.kali.org/archive-key.asc"
KALI_KEY_FINGERPRINT="44C6513A8E4FB3D30875F758ED444FF07D8D0BF6"

echo "Downloading Kali signing key..."
wget -q -O /tmp/kali-archive-key.asc "$KALI_KEY_URL"

# Verify key fingerprint
if gpg --with-fingerprint /tmp/kali-archive-key.asc 2>/dev/null | grep -q "$KALI_KEY_FINGERPRINT"; then
    echo "✓ Kali signing key verified"
    sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/kali-archive-keyring.gpg < /tmp/kali-archive-key.asc
    echo 'deb https://http.kali.org/kali kali-rolling main contrib non-free' | sudo tee /etc/apt/sources.list.d/kali.list
else
    echo "✗ Kali signing key verification failed"
    echo "Expected fingerprint: $KALI_KEY_FINGERPRINT"
    exit 1
fi

# Clean up
rm -f /tmp/kali-archive-key.asc

# Set Kali repository to low priority to avoid conflicts
echo 'Package: *
Pin: release o=Kali
Pin-Priority: 50' | sudo tee /etc/apt/preferences.d/kali.pref

sudo apt update

# Core wireless security tools
WIRELESS_TOOLS=(
    "aircrack-ng"          # WiFi security auditing
    "kismet"               # Wireless network detector
    "reaver"               # WPS attack tool  
    "hashcat"              # Password cracking
    "john"                 # Password cracking
    "wordlists"            # Password wordlists
    "wifi-honey"           # WiFi honeypot
    "wifite"               # Automated WiFi auditing
)

# Network analysis and scanning
NETWORK_TOOLS=(
    "nmap"                 # Network discovery and security auditing
    "masscan"              # Fast port scanner
    "netdiscover"          # Network address discovering
    "arp-scan"             # ARP-based host discovery
    "netcat-openbsd"       # TCP/UDP swiss army knife
    "socat"                # Multipurpose relay
    "wireshark-common"     # Packet analysis
    "tcpdump"              # Packet capture
    "ettercap-text-only"   # Network security auditing
)

# Web application security
WEB_TOOLS=(
    "sqlmap"               # SQL injection testing
    "nikto"                # Web server scanner
    "dirb"                 # URL bruteforcer
    "gobuster"             # Directory/file/DNS bruteforcer
    "wfuzz"                # Web application bruteforcer
    "whatweb"              # Web technology identifier
)

# Exploitation frameworks and tools
EXPLOIT_TOOLS=(
    "metasploit-framework" # Penetration testing framework
    "exploit-db"           # Exploit database
    "searchsploit"         # Exploit search tool
    "armitage"             # Metasploit GUI
)

# System tools and utilities
SYSTEM_TOOLS=(
    "python3-pip"          # Python package manager
    "python3-dev"          # Python development headers
    "git"                  # Version control
    "curl"                 # HTTP client
    "wget"                 # File downloader
    "unzip"                # Archive extraction
    "build-essential"      # Compilation tools
    "postgresql"           # Database
    "postgresql-contrib"   # Database extensions
    "docker.io"            # Container platform
    "docker-compose"       # Container orchestration
)

# Install all tool categories
ALL_TOOLS=("${WIRELESS_TOOLS[@]}" "${NETWORK_TOOLS[@]}" "${WEB_TOOLS[@]}" "${EXPLOIT_TOOLS[@]}" "${SYSTEM_TOOLS[@]}")

echo "Installing ${#ALL_TOOLS[@]} security tools..."
for tool in "${ALL_TOOLS[@]}"; do
    echo "Installing $tool..."
    if sudo apt install -y "$tool"; then
        echo "✓ $tool installed successfully"
    else
        echo "✗ Failed to install $tool"
    fi
done

# Add user to required groups for wireless and docker access
echo "Adding user tudor to security groups..."
sudo usermod -a -G wireshark,docker,dialout tudor

# Install additional Python security libraries
echo "Installing Python security libraries..."
pip3 install --user \
    scapy \
    impacket \
    pycryptodome \
    paramiko \
    requests \
    beautifulsoup4 \
    netaddr \
    python-nmap \
    psycopg2-binary \
    flask \
    flask-restful \
    python-dotenv

# Update Metasploit database
echo "Initializing Metasploit database..."
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo msfdb init

# Update locate database for searchsploit
echo "Updating file database..."
sudo updatedb

# Create tool verification script
cat > /opt/SECURITY/scripts/raspibig/verify_penetration_tools.sh << 'EOF'
#!/bin/bash
# verify_penetration_tools.sh - Verify penetration testing tool installation

echo "Verifying penetration testing tools installation..."

# Tools to verify
declare -A tools=(
    ["aircrack-ng"]="aircrack-ng --version"
    ["nmap"]="nmap --version"
    ["metasploit"]="msfconsole --version"
    ["sqlmap"]="sqlmap --version"
    ["hashcat"]="hashcat --version"
    ["kismet"]="kismet --version"
    ["wireshark"]="tshark --version"
    ["python3"]="python3 --version"
    ["postgresql"]="psql --version"
    ["docker"]="docker --version"
)

passed=0
failed=0

for tool in "${!tools[@]}"; do
    if eval "${tools[$tool]}" &>/dev/null; then
        echo "✓ $tool: Working"
        ((passed++))
    else
        echo "✗ $tool: Not working"
        ((failed++))
    fi
done

echo
echo "Verification complete: $passed passed, $failed failed"

if [[ $failed -eq 0 ]]; then
    echo "All tools verified successfully!"
    exit 0
else
    echo "Some tools failed verification. Check installation."
    exit 1
fi
EOF

chmod +x /opt/SECURITY/scripts/raspibig/verify_penetration_tools.sh

# Log installation completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Penetration tools installation completed" >> /opt/SECURITY/logs/setup.log

echo "Penetration testing tools installation complete!"
echo "Run '/opt/SECURITY/scripts/raspibig/verify_penetration_tools.sh' to verify"
echo "Reboot recommended for group changes to take effect."
```

- [ ] **Step 2: Create database configuration script**

```bash
#!/bin/bash
# configure_database.sh - Setup PostgreSQL for security research data

set -euo pipefail

echo "Configuring PostgreSQL for academic security research..."

# Ensure PostgreSQL is running
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Generate secure random password for database user
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
echo "Generated secure database password: $DB_PASSWORD"

# Create research database and user
sudo -u postgres psql << EOF
-- Create security research database
CREATE DATABASE security_research;

-- Create research user with limited privileges
CREATE USER security_researcher WITH PASSWORD '$DB_PASSWORD';

-- Grant necessary privileges
GRANT CONNECT ON DATABASE security_research TO security_researcher;
\c security_research
GRANT CREATE ON SCHEMA public TO security_researcher;
GRANT USAGE ON SCHEMA public TO security_researcher;

-- Create core research tables
CREATE TABLE research_projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    authorized_targets JSONB,
    compliance_approved BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(100),
    notes TEXT
);

CREATE TABLE network_scans (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id),
    scan_type VARCHAR(100),
    target_range CIDR,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50),
    results JSONB,
    command_executed TEXT,
    authorized BOOLEAN DEFAULT FALSE
);

CREATE TABLE wifi_analysis (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id),
    ssid VARCHAR(255),
    bssid MACADDR,
    channel INTEGER,
    encryption VARCHAR(50),
    signal_strength INTEGER,
    discovery_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_type VARCHAR(100),
    results JSONB,
    authorized_analysis BOOLEAN DEFAULT FALSE
);

CREATE TABLE research_logs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_level VARCHAR(20),
    component VARCHAR(100),
    message TEXT,
    metadata JSONB
);

CREATE TABLE compliance_audit (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id),
    audit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    auditor VARCHAR(100),
    compliance_items JSONB,
    passed BOOLEAN,
    notes TEXT
);

-- Create indexes for performance
CREATE INDEX idx_research_projects_status ON research_projects(status);
CREATE INDEX idx_network_scans_project ON network_scans(project_id);
CREATE INDEX idx_wifi_analysis_project ON wifi_analysis(project_id);
CREATE INDEX idx_research_logs_timestamp ON research_logs(timestamp);

-- Grant table privileges
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO security_researcher;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO security_researcher;

EOF

# Create database configuration file with generated password
cat > /opt/SECURITY/config/database.env << EOF
# Database configuration for security research
DB_HOST=localhost
DB_PORT=5432
DB_NAME=security_research
DB_USER=security_researcher
DB_PASSWORD=$DB_PASSWORD
DB_SSL_MODE=prefer

# Connection pool settings
DB_POOL_SIZE=10
DB_POOL_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
EOF

echo "Database password saved to /opt/SECURITY/config/database.env"

# Secure the environment file
chmod 600 /opt/SECURITY/config/database.env

# Create database utility scripts
cat > /opt/SECURITY/scripts/raspibig/db_backup.sh << 'EOF'
#!/bin/bash
# db_backup.sh - Backup security research database

BACKUP_DIR="/opt/SECURITY/backups/database"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/security_research_$TIMESTAMP.sql"

echo "Creating database backup: $BACKUP_FILE"
pg_dump -h localhost -U security_researcher security_research > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE.gz"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete
EOF

cat > /opt/SECURITY/scripts/raspibig/db_status.sh << 'EOF'
#!/bin/bash
# db_status.sh - Check database status and research project summary

source /opt/SECURITY/config/database.env

echo "=== Security Research Database Status ==="
echo "Database: $DB_NAME on $DB_HOST:$DB_PORT"
echo

# Check database connection
if psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
    echo "✓ Database connection: OK"
else
    echo "✗ Database connection: FAILED"
    exit 1
fi

# Get research project summary
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    COUNT(*) as total_projects,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_projects,
    COUNT(CASE WHEN compliance_approved THEN 1 END) as approved_projects
FROM research_projects;
"

# Recent activity summary
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 'Last 24h Activity' as activity_type, COUNT(*) as count
FROM research_logs 
WHERE timestamp > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 'Network Scans (7d)', COUNT(*)
FROM network_scans 
WHERE start_time > NOW() - INTERVAL '7 days'
UNION ALL  
SELECT 'WiFi Analysis (7d)', COUNT(*)
FROM wifi_analysis 
WHERE discovery_time > NOW() - INTERVAL '7 days';
"
EOF

chmod +x /opt/SECURITY/scripts/raspibig/db_*.sh

echo "Database configuration complete!"
echo "Connection details saved to /opt/SECURITY/config/database.env"
```

- [ ] **Step 3: Create WiFi research setup script**

```bash
#!/bin/bash
# setup_wifi_research.sh - Configure WiFi security research capabilities

set -euo pipefail

echo "Setting up WiFi Security Research Environment..."

# Check for WiFi interfaces
echo "Detecting WiFi interfaces..."
wifi_interfaces=$(iw dev | grep Interface | awk '{print $2}')

if [[ -z "$wifi_interfaces" ]]; then
    echo "Warning: No WiFi interfaces detected"
    echo "You may need to connect an external WiFi adapter with monitor mode support"
    echo "Recommended: Alfa AWUS036ACS or similar"
else
    echo "WiFi interfaces found:"
    for interface in $wifi_interfaces; do
        echo "  - $interface"
        
        # Check monitor mode capability
        if iw "$interface" info | grep -q "monitor"; then
            echo "    ✓ Monitor mode supported"
        else
            echo "    ? Monitor mode capability unknown"
        fi
    done
fi

# Create WiFi research configuration
cat > /opt/SECURITY/config/wifi_research.yml << 'EOF'
# WiFi Security Research Configuration

research_parameters:
  monitor_mode_interface: null  # Set to your monitor-capable interface
  channel_scan_range: [1, 11]   # 2.4GHz channels (adjust for region)
  scan_duration_seconds: 300    # 5 minutes default
  
authorized_research:
  own_networks:
    - "YourHomeNetworkSSID"     # Replace with your network
  test_networks:
    - "TestLab_*"               # Lab networks with wildcard
  
prohibited_networks:
  - "*"                         # Default: prohibit all others
  
analysis_settings:
  capture_handshakes: true
  analyze_encryption: true
  detect_wps: true
  passive_monitoring: true
  active_attacks: false         # Disabled by default for safety

wordlists:
  primary: "/usr/share/wordlists/rockyou.txt"
  custom: "/opt/SECURITY/wordlists/custom.txt"
  
output:
  capture_directory: "/opt/SECURITY/research/data/wifi_captures"
  analysis_directory: "/opt/SECURITY/research/data/wifi_analysis"
  report_directory: "/opt/SECURITY/research/reports/wifi"
EOF

# Create WiFi research directories
mkdir -p /opt/SECURITY/research/data/{wifi_captures,wifi_analysis}
mkdir -p /opt/SECURITY/research/reports/wifi
mkdir -p /opt/SECURITY/wordlists

# Create WiFi analysis utility script
cat > /opt/SECURITY/scripts/raspibig/wifi_analyzer.py << 'EOF'
#!/usr/bin/env python3
"""
wifi_analyzer.py - Academic WiFi Security Research Tool
Educational use only - authorized networks only
"""

import os
import sys
import yaml
import argparse
import subprocess
from datetime import datetime
import psycopg2
from psycopg2.extras import Json

class WiFiResearchTool:
    def __init__(self, config_path="/opt/SECURITY/config/wifi_research.yml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load database config
        self.db_config = self._load_db_config()
        
    def _load_db_config(self):
        """Load database configuration from environment file"""
        db_config = {}
        env_file = "/opt/SECURITY/config/database.env"
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        db_config[key] = value
        
        return db_config
    
    def is_authorized_network(self, ssid):
        """Check if network is authorized for research"""
        authorized = self.config['authorized_research']['own_networks'] + \
                    self.config['authorized_research']['test_networks']
        
        for pattern in authorized:
            if pattern.endswith('*'):
                if ssid.startswith(pattern[:-1]):
                    return True
            elif ssid == pattern:
                return True
        
        return False
    
    def passive_scan(self, interface, duration=300):
        """Perform passive WiFi network discovery"""
        if not interface:
            print("Error: No monitor interface specified")
            return None
        
        print(f"Starting passive scan on {interface} for {duration} seconds...")
        
        # Use airodump-ng for passive scanning
        output_file = f"/opt/SECURITY/research/data/wifi_captures/scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cmd = [
            'airodump-ng',
            '--output-format', 'csv',
            '--write', output_file,
            interface
        ]
        
        try:
            # Run scan for specified duration
            proc = subprocess.Popen(cmd)
            subprocess.run(['sleep', str(duration)])
            proc.terminate()
            proc.wait()
            
            # Parse results
            return self._parse_airodump_results(f"{output_file}-01.csv")
            
        except Exception as e:
            print(f"Scan error: {e}")
            return None
    
    def _parse_airodump_results(self, csv_file):
        """Parse airodump-ng CSV output"""
        networks = []
        
        if not os.path.exists(csv_file):
            return networks
        
        with open(csv_file, 'r') as f:
            lines = f.readlines()
        
        # Find networks section (between two blank lines)
        in_networks = False
        for line in lines:
            line = line.strip()
            if not line:
                in_networks = True
                continue
            
            if in_networks and line.startswith('Station MAC'):
                break  # End of networks section
            
            if in_networks and ',' in line:
                parts = line.split(',')
                if len(parts) >= 14:
                    network = {
                        'bssid': parts[0].strip(),
                        'first_seen': parts[1].strip(),
                        'last_seen': parts[2].strip(),
                        'channel': parts[3].strip(),
                        'speed': parts[4].strip(),
                        'privacy': parts[5].strip(),
                        'cipher': parts[6].strip(),
                        'authentication': parts[7].strip(),
                        'power': parts[8].strip(),
                        'beacons': parts[9].strip(),
                        'iv': parts[10].strip(),
                        'lan_ip': parts[11].strip(),
                        'id_length': parts[12].strip(),
                        'essid': parts[13].strip(),
                        'key': parts[14].strip() if len(parts) > 14 else ''
                    }
                    networks.append(network)
        
        return networks
    
    def save_results(self, project_name, scan_results):
        """Save scan results to database"""
        if not self.db_config:
            print("Database not configured")
            return
        
        try:
            conn = psycopg2.connect(
                host=self.db_config.get('DB_HOST', 'localhost'),
                port=self.db_config.get('DB_PORT', 5432),
                database=self.db_config.get('DB_NAME'),
                user=self.db_config.get('DB_USER'),
                password=self.db_config.get('DB_PASSWORD')
            )
            
            cursor = conn.cursor()
            
            # Get or create project
            cursor.execute(
                "SELECT id FROM research_projects WHERE name = %s",
                (project_name,)
            )
            
            project_id = cursor.fetchone()
            if not project_id:
                cursor.execute(
                    "INSERT INTO research_projects (name, description, authorized_targets) VALUES (%s, %s, %s) RETURNING id",
                    (project_name, "WiFi Security Research", Json(self.config['authorized_research']))
                )
                project_id = cursor.fetchone()[0]
            else:
                project_id = project_id[0]
            
            # Save scan results
            for network in scan_results:
                cursor.execute("""
                    INSERT INTO wifi_analysis 
                    (project_id, ssid, bssid, channel, encryption, signal_strength, analysis_type, results, authorized_analysis)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    project_id,
                    network.get('essid', ''),
                    network.get('bssid', ''),
                    int(network.get('channel', 0)) if network.get('channel', '').isdigit() else 0,
                    network.get('privacy', ''),
                    int(network.get('power', 0)) if network.get('power', '').lstrip('-').isdigit() else 0,
                    'passive_scan',
                    Json(network),
                    self.is_authorized_network(network.get('essid', ''))
                ))
            
            conn.commit()
            print(f"Saved {len(scan_results)} networks to database")
            
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            if conn:
                conn.close()

def main():
    parser = argparse.ArgumentParser(description="Academic WiFi Security Research Tool")
    parser.add_argument('--interface', '-i', required=True, help="Monitor mode interface")
    parser.add_argument('--duration', '-d', type=int, default=300, help="Scan duration (seconds)")
    parser.add_argument('--project', '-p', required=True, help="Research project name")
    parser.add_argument('--passive-only', action='store_true', help="Passive scanning only")
    
    args = parser.parse_args()
    
    # Check if running as root (required for monitor mode)
    if os.geteuid() != 0:
        print("Error: WiFi research tools require root privileges")
        sys.exit(1)
    
    tool = WiFiResearchTool()
    
    print("=== Academic WiFi Security Research ===")
    print("AUTHORIZED RESEARCH ONLY")
    print(f"Project: {args.project}")
    print(f"Interface: {args.interface}")
    print(f"Duration: {args.duration} seconds")
    print()
    
    # Perform passive scan
    results = tool.passive_scan(args.interface, args.duration)
    
    if results:
        print(f"Discovered {len(results)} networks:")
        for network in results:
            ssid = network.get('essid', 'Hidden')
            authorized = "✓" if tool.is_authorized_network(ssid) else "✗"
            print(f"  {authorized} {ssid} ({network.get('privacy', 'Unknown')})")
        
        # Save results
        tool.save_results(args.project, results)
        print("\nResults saved to database")
    else:
        print("No results obtained")

if __name__ == '__main__':
    main()
EOF

chmod +x /opt/SECURITY/scripts/raspibig/wifi_analyzer.py

# Create simple interface management script
cat > /opt/SECURITY/scripts/raspibig/manage_wifi_interface.sh << 'EOF'
#!/bin/bash
# manage_wifi_interface.sh - WiFi interface management for research

usage() {
    echo "Usage: $0 {start|stop|status} <interface>"
    echo "  start <interface>  - Put interface in monitor mode"
    echo "  stop <interface>   - Return interface to managed mode"
    echo "  status             - Show all WiFi interfaces"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

case "$1" in
    "start")
        if [[ $# -ne 2 ]]; then
            usage
        fi
        interface="$2"
        echo "Starting monitor mode on $interface..."
        sudo airmon-ng start "$interface"
        ;;
    
    "stop")
        if [[ $# -ne 2 ]]; then
            usage
        fi
        interface="$2"
        echo "Stopping monitor mode on $interface..."
        sudo airmon-ng stop "$interface"
        ;;
    
    "status")
        echo "WiFi Interface Status:"
        echo "======================"
        iw dev
        echo
        echo "Monitor Mode Interfaces:"
        iw dev | grep -A 5 "type monitor" || echo "None active"
        ;;
    
    *)
        usage
        ;;
esac
EOF

chmod +x /opt/SECURITY/scripts/raspibig/manage_wifi_interface.sh

echo "WiFi research environment setup complete!"
echo
echo "Next steps:"
echo "1. Connect external WiFi adapter with monitor mode support"
echo "2. Configure your authorized networks in /opt/SECURITY/config/wifi_research.yml"
echo "3. Use ./manage_wifi_interface.sh to manage monitor mode"
echo "4. Use ./wifi_analyzer.py for authorized network research"
```

- [ ] **Step 4: Run Raspibig setup scripts**

```bash
# Execute on raspibig via SSH
ssh tudor@192.168.100.21 'bash -s' < /tmp/setup_commands.sh
```

Where setup_commands.sh contains:
```bash
cd /opt/SECURITY
sudo ./setup/raspibig_setup.sh
sudo ./scripts/raspibig/install_penetration_tools.sh  
sudo ./scripts/raspibig/configure_database.sh
sudo ./scripts/raspibig/setup_wifi_research.sh
sudo ./scripts/raspibig/verify_penetration_tools.sh
```

- [ ] **Step 5: Commit Raspibig setup completion**

```bash
# On Windows, commit the Raspibig configuration
cd "D:\MEMORY\SECURITY"
git add config/ scripts/
git commit -m "Complete Raspibig penetration testing platform setup

- Install comprehensive penetration testing tools
- Configure PostgreSQL research database
- Setup WiFi security research environment  
- Add management and verification scripts

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>"
```