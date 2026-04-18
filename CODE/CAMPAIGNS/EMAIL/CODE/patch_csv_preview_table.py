#!/usr/bin/env python3
"""Add data preview table (first 5 rows) after CSV upload so user can verify data loaded correctly."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# 1. Update the /api/csv-preview endpoint to return sample rows
old_return = '''    return jsonify({"columns": header, "rows": row_count - 1, "file": fname, "delimiter": delim})'''
new_return = '''    # Get first 5 sample rows for preview
    sample_reader = csvmod.reader(io.StringIO(text), delimiter=delim)
    next(sample_reader)  # skip header
    sample_rows = []
    for i, row in enumerate(sample_reader):
        if i >= 5:
            break
        sample_rows.append(row[:len(header)])
    return jsonify({"columns": header, "rows": row_count - 1, "file": fname, "delimiter": delim, "sample": sample_rows})'''
content = content.replace(old_return, new_return)

# 2. Show preview table in the JS callback after upload
old_confirmation = '''        "File saved on server as: <code>" + d.file + "</code></div>");'''
new_confirmation = '''        "File saved on server as: <code>" + d.file + "</code></div>");
      // Show preview table with first 5 rows
      var previewHtml = "<div style='margin-top:10px;overflow-x:auto;'><table style='font-size:12px;border-collapse:collapse;'><tr>";
      d.columns.forEach(function(col) {
        previewHtml += "<th style='padding:6px 10px;background:#334155;color:#38bdf8;border:1px solid #475569;white-space:nowrap;'>" + col + "</th>";
      });
      previewHtml += "</tr>";
      (d.sample || []).forEach(function(row) {
        previewHtml += "<tr>";
        row.forEach(function(cell) {
          var display = (cell || "").substring(0, 50);
          if (cell && cell.length > 50) display += "...";
          previewHtml += "<td style='padding:4px 10px;border:1px solid #334155;color:#e2e8f0;white-space:nowrap;'>" + display + "</td>";
        });
        previewHtml += "</tr>";
      });
      previewHtml += "</table></div>";
      document.getElementById("csv_preview").insertAdjacentHTML("beforeend", previewHtml);'''
content = content.replace(old_confirmation, new_confirmation)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - CSV preview shows first 5 rows after upload")
