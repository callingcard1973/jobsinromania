#!/usr/bin/env python3
"""Patch dashboard to show CSV import confirmation after campaign creation."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# After CSV import, store result in the redirect message
old_import = """            if resp.status_code == 200 and resp.json().get('ok'):
                database = 'campaign_csv'
                # Find the email column from mapping
                for csv_col, db_col in col_map.items():
                    if db_col == 'email':
                        break"""

new_import = """            if resp.status_code == 200 and resp.json().get('ok'):
                csv_result = resp.json()
                database = 'campaign_csv'
                contacts_table = csv_result['table']
                csv_imported_rows = csv_result['rows']
                csv_imported_cols = csv_result['columns']
            else:
                err = resp.json().get('error', 'Unknown error') if resp.status_code != 200 else 'Import failed'
                return redirect(f'/new?msg=CSV+import+failed:+{err}&msg_type=error')"""
content = content.replace(old_import, new_import)

# Update the success redirect to include CSV info
old_redirect = "        return redirect(f'/{url_prefix}/?msg=Campaign+created+successfully')"
new_redirect = """        csv_msg = ''
        if csv_filename:
            csv_msg = f'+({csv_imported_rows}+rows+imported+from+CSV)'
        return redirect(f'/{url_prefix}/?msg=Campaign+created+successfully{csv_msg}')"""
content = content.replace(old_redirect, new_redirect)

# Also add a visual confirmation in the CSV preview JS - show green check after upload
old_preview_display = 'document.getElementById("csv_preview").style.display = "block";'
new_preview_display = """document.getElementById("csv_preview").style.display = "block";
      document.getElementById("csv_preview").insertAdjacentHTML("afterbegin",
        "<div style='background:#22c55e22;border:1px solid #22c55e;padding:10px;border-radius:8px;margin-bottom:10px;'>" +
        "CSV uploaded and parsed. <strong>" + d.rows + " rows</strong>, " + d.columns.length + " columns. " +
        "File saved on server as: <code>" + d.file + "</code></div>");"""
content = content.replace(old_preview_display, new_preview_display)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - CSV import confirmation added")
