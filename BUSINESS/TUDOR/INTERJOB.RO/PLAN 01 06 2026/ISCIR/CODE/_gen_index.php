<?php
// Generate operator index page for interjob.ro/iscir/
$csvFile = __DIR__ . '/operatori/_index.csv';
$outFile = __DIR__ . '/index.html';
if (!file_exists($csvFile)) { echo "NO_CSV"; exit; }
$fh = fopen($csvFile, 'r');
$header = fgetcsv($fh);
$ops = [];
while ($row = fgetcsv($fh)) {
    $d = array_combine($header, $row);
    if ($d['cui'] ?? '') $ops[] = $d;
}
fclose($fh);
ob_start();
?><!doctype html>
<html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Operatori RSVTI Autorizati ISCIR - Lista completa</title>
<style>
*{box-sizing:border-box;margin:0}body{font:15px/1.6 system-ui,sans-serif;background:#f5f6f8;color:#1b2330}
.wrap{max-width:960px;margin:0 auto;padding:20px}
h1{font-size:26px;margin:20px 0 6px}.count{color:#6b7a8e;font-size:14px;margin-bottom:20px}
.card{background:#fff;border:1px solid #e0e5ec;border-radius:10px;padding:14px 18px;margin:8px 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.card .name{font-weight:700;color:#143a5a;text-decoration:none}.card .county{color:#6b7a8e;font-size:13px}.card .seg{font-size:12px;background:#e8edf4;padding:2px 8px;border-radius:4px;color:#4a5a70}
.card .tel{color:#e08a1e;font-weight:700;text-decoration:none}
input{width:100%;padding:10px 14px;border:1px solid #d0d5dd;border-radius:8px;font-size:15px;margin-bottom:16px}
</style></head><body>
<div class="wrap">
<h1>Operatori RSVTI Autorizati ISCIR</h1>
<p class="count"><?= count($ops) ?> operatori autorizati</p>
<input type="text" id="filtru" placeholder="Cauta dupa nume, judet sau segment..." oninput="filterList()">
<div id="lista">
<?php foreach ($ops as $o):
    $url = 'operatori/' . htmlspecialchars($o['cui']) . '.html';
?><div class="card" data-search="<?= htmlspecialchars(strtolower($o['name'] . ' ' . $o['county'] . ' ' . $o['segment'])) ?>">
  <div><a class="name" href="<?= $url ?>"><?= htmlspecialchars($o['name']) ?></a>
  <div><span class="county"><?= htmlspecialchars($o['county']) ?></span> <span class="seg"><?= htmlspecialchars($o['segment']) ?></span></div></div>
  <a class="tel" href="tel:<?= htmlspecialchars($o['phone']) ?>"><?= htmlspecialchars($o['phone']) ?></a>
</div>
<?php endforeach; ?>
</div>
<script>function filterList(){var i=document.getElementById('filtru').value.toLowerCase();document.querySelectorAll('.card').forEach(function(c){c.style.display=c.dataset.search.includes(i)?'':'none'})}</script>
</div></body></html>
<?php
$html = ob_get_clean();
file_put_contents($outFile, $html);
echo "Generated index: " . filesize($outFile) . " bytes, " . count($ops) . " operators\n";
