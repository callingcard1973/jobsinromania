#!/usr/bin/env python3
"""Update the template section to show dynamic placeholders from CSV columns."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

old_placeholders = """  <p style="color: #94a3b8; font-size: 13px;">
    Placeholders: <code>{company_name}</code>, <code>{email}</code>, <code>{city}</code>, <code>{unsubscribe_url}</code>
  </p>"""

new_placeholders = """  <div style="color: #94a3b8; font-size: 13px;">
    <p><strong>Built-in placeholders:</strong>
      <code>{company_name}</code> <code>{email}</code> <code>{city}</code> <code>{county}</code>
      <code>{employees}</code> <code>{sector_name}</code> <code>{contact_greeting}</code>
      <code>{contact_person}</code> <code>{position_text}</code> <code>{city_text}</code>
      <code>{unsubscribe_url}</code>
    </p>
    <div id="csv_placeholders" style="display:none; margin-top:10px; padding:10px; background:#22c55e11; border:1px solid #22c55e44; border-radius:8px;">
      <strong style="color:#22c55e;">Your CSV columns (click to insert):</strong><br>
      <span id="csv_placeholder_list"></span>
    </div>
  </div>
<script>
// After CSV upload, show available placeholders from column names
var _origCsvCallback = null;
(function() {
  var origFetch = document.getElementById("csv_file");
  if (!origFetch) return;
  var obs = new MutationObserver(function() {
    var maps = document.querySelectorAll(".col-map");
    if (maps.length === 0) return;
    var html = "";
    maps.forEach(function(m) {
      var val = m.value;
      html += "<code style='cursor:pointer;margin:3px;padding:2px 8px;background:#1e293b;border:1px solid #334155;border-radius:4px;' " +
              "onclick='insertPlaceholder(\\\"" + val + "\\\")'>{" + val + "}</code> ";
    });
    document.getElementById("csv_placeholder_list").innerHTML = html;
    document.getElementById("csv_placeholders").style.display = "block";
    // Update on column rename
    maps.forEach(function(m) {
      m.addEventListener("input", function() {
        var h = "";
        document.querySelectorAll(".col-map").forEach(function(s) {
          h += "<code style='cursor:pointer;margin:3px;padding:2px 8px;background:#1e293b;border:1px solid #334155;border-radius:4px;' " +
               "onclick='insertPlaceholder(\\\"" + s.value + "\\\")'>{" + s.value + "}</code> ";
        });
        document.getElementById("csv_placeholder_list").innerHTML = h;
      });
    });
  });
  obs.observe(document.getElementById("csv_columns"), {childList: true, subtree: true});
})();
function insertPlaceholder(name) {
  var ta = document.querySelector("textarea[name=template]");
  var pos = ta.selectionStart;
  var text = ta.value;
  var insert = "{" + name + "}";
  ta.value = text.substring(0, pos) + insert + text.substring(pos);
  ta.selectionStart = ta.selectionEnd = pos + insert.length;
  ta.focus();
}
</script>"""

content = content.replace(old_placeholders, new_placeholders)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Dynamic placeholder help added to template editor")
