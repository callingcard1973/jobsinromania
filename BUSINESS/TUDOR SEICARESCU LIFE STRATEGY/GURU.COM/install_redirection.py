#!/usr/bin/env python3
"""Install Redirection plugin on baneasa39.com via cPanel API."""
import requests
requests.packages.urllib3.disable_warnings()

HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
TOKEN = "T7ZV9TZJZ22E0YCEOUST8AAGQGQTZVU1"
H = {"Authorization": f"cpanel {USER}:{TOKEN}"}
DIR = f"/home/{USER}/baneasa39.com"

php = """<?php
$z = new ZipArchive;
$p = __DIR__ . '/wp-content/plugins/';
$r = $z->open($p . 'redirection.zip');
if ($r === TRUE) {
    $z->extractTo($p);
    $z->close();
    unlink($p . 'redirection.zip');
    echo 'INSTALLED';
} else {
    echo 'FAIL:' . $r;
}
"""

# Upload PHP as file
r = requests.post(f"{HOST}/execute/Fileman/save_file_content", headers=H, verify=False,
    data={"dir": DIR, "file": "extract_plugin.php", "content": php})
print(f"PHP saved: {r.status_code}")

# Execute
r2 = requests.get("https://baneasa39.com/extract_plugin.php", timeout=15)
print(f"Result: {r2.status_code} {r2.text[:100]}")

# Cleanup PHP
requests.post(f"{HOST}/execute/Fileman/save_file_content", headers=H, verify=False,
    data={"dir": DIR, "file": "extract_plugin.php", "content": "<?php //removed"})

# Verify
r3 = requests.get(f"{HOST}/execute/Fileman/list_files?dir={DIR}/wp-content/plugins/redirection&types=file", headers=H, verify=False)
data = r3.json().get("data")
if data:
    print(f"Plugin installed: {len(data)} files")
else:
    print("Plugin NOT found")
