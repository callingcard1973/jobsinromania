#!/usr/bin/env python3
"""Fix /new page: show CSV column placeholders directly in Step 4 after upload."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# Replace the CSV preview callback to also update Step 4 placeholder area directly
old_js = '''document.getElementById("csv_preview").insertAdjacentHTML("afterbegin",
        "<div style='background:#22c55e22;border:1px solid #22c55e;padding:10px;border-radius:8px;margin-bottom:10px;'>" +
        "CSV uploaded and parsed. <strong>" + d.rows + " rows</strong>, " + d.columns.length + " columns. " +
        "File saved on server as: <code>" + d.file + "</code></div>");'''

new_js = '''document.getElementById("csv_preview").insertAdjacentHTML("afterbegin",
        "<div style='background:#22c55e22;border:1px solid #22c55e;padding:10px;border-radius:8px;margin-bottom:10px;'>" +
        "CSV uploaded and parsed. <strong>" + d.rows + " rows</strong>, " + d.columns.length + " columns. " +
        "File saved on server as: <code>" + d.file + "</code></div>");
      // Populate Step 4 placeholder buttons
      var phHtml = "";
      d.columns.forEach(function(col) {
        var clean = col.toLowerCase().replace(/[^a-z0-9]/g, "_");
        phHtml += "<code style='cursor:pointer;color:#38bdf8;margin:3px;padding:3px 8px;background:#0f172a;border:1px solid #334155;border-radius:4px;display:inline-block;' " +
                  "onclick='insertPlaceholder(\\"" + clean + "\\")'>{" + clean + "}</code> ";
      });
      document.getElementById("csv_placeholder_list").innerHTML = phHtml;
      document.getElementById("csv_placeholders").style.display = "block";'''

content = content.replace(old_js, new_js)

# Also: when user renames a column in Step 2, update Step 4 placeholders live
old_submit = '''document.querySelector("form").addEventListener("submit", function() {
  var map = {};
  document.querySelectorAll(".col-map").forEach(function(s) {
    var csv_col = s.getAttribute("data-csv");
    map[csv_col] = s.value;
  });
  document.getElementById("csv_col_map").value = JSON.stringify(map);
});'''

new_submit = '''// Update placeholders in Step 4 when columns are renamed in Step 2
document.addEventListener("input", function(e) {
  if (!e.target.classList.contains("col-map")) return;
  var phHtml = "";
  document.querySelectorAll(".col-map").forEach(function(s) {
    var val = s.value;
    phHtml += "<code style='cursor:pointer;color:#38bdf8;margin:3px;padding:3px 8px;background:#0f172a;border:1px solid #334155;border-radius:4px;display:inline-block;' " +
              "onclick='insertPlaceholder(\\"" + val + "\\")'>{" + val + "}</code> ";
  });
  document.getElementById("csv_placeholder_list").innerHTML = phHtml;
});
document.querySelector("form").addEventListener("submit", function() {
  var map = {};
  document.querySelectorAll(".col-map").forEach(function(s) {
    var csv_col = s.getAttribute("data-csv");
    map[csv_col] = s.value;
  });
  document.getElementById("csv_col_map").value = JSON.stringify(map);
});'''

content = content.replace(old_submit, new_submit)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - CSV placeholders sync live between Step 2 and Step 4")
