<?php
// Direct DB install for hb_content module
define('_PS_ROOT_DIR_', __DIR__ . '/../../../../..');
define('_DB_SERVER_', 'localhost');
define('_DB_USER_', 'loaiidil_ps');
define('_DB_PASSWD_', 'your_db_pass');
define('_DB_NAME_', 'loaiidil_ps');
define('_DB_PREFIX_', 'psc8_');

$pdo = new PDO("mysql:host=localhost;dbname=loaiidil_ps;charset=utf8mb4", 'loaiidil_ps', 'your_db_pass');
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

// 1. Register module
$pdo->exec("INSERT IGNORE INTO psc8_module (name,active) VALUES ('hb_content',1)");
$id_module = $pdo->query("SELECT id_module FROM psc8_module WHERE name='hb_content'")->fetchColumn();

$pdo->exec("INSERT IGNORE INTO psc8_module_shop (id_module,id_shop) VALUES ($id_module,1)");

// 2. Config defaults
$defaults = [
    'HB_HERO_EYEBROW'      => 'Echipamente certificate CE · Partener AVP Park Turcia',
    'HB_HERO_TITLE'        => 'Locuri de joacă',
    'HB_HERO_SUBTITLE'     => 'pentru comunitatea ta',
    'HB_HERO_TEXT'         => '226 produse — structuri de joacă, leagăne, fitness exterior, mobilier urban.',
    'HB_HERO_BTN_CATALOG'  => 'Vezi catalogul',
    'HB_HERO_BTN_PACKAGES' => 'Pachete & Prețuri',
    'HB_CTA_TITLE'         => 'AUDIT TEREN GRATUIT',
    'HB_CTA_TEXT'          => 'Venim la tine, măsurăm terenul și îți lăsăm un proiect orientativ fără niciun cost.',
    'HB_CTA_BTN'           => 'Programează acum →',
    'HB_PKG_LABEL'         => 'Pachete complete cu prețuri fixe',
    'HB_PKG_TEXT'          => '3 pachete gata configurate — de la 18.000 RON · montaj ISCIR inclus · documentație SEAP completă',
    'HB_PKG_BTN'           => 'Vezi pachete și prețuri →',
    'HB_CAT_TITLE'         => 'Catalog',
    'HB_CAT_SUBTITLE'      => 'Echipamente',
    'HB_CAT_TEXT'          => '226 produse AVP Park — structuri de joacă, leagăne, echipamente fitness exterior',
];

$stmt = $pdo->prepare("INSERT IGNORE INTO psc8_configuration (name,value,id_shop_group,id_shop,date_add,date_upd) VALUES (?,?,NULL,NULL,NOW(),NOW())");
foreach ($defaults as $k => $v) {
    $stmt->execute([$k, json_decode('"'.$v.'"')]);
}

// 3. Admin tab
$pdo->exec("INSERT IGNORE INTO psc8_tab (id_parent,class_name,module,active,icon) VALUES (
    (SELECT id_tab FROM psc8_tab t2 WHERE t2.class_name='AdminParentModulesSf'),
    'AdminHbContent','hb_content',1,'edit'
)");
$id_tab = $pdo->query("SELECT id_tab FROM psc8_tab WHERE class_name='AdminHbContent'")->fetchColumn();

foreach ($pdo->query("SELECT id_lang FROM psc8_lang")->fetchAll(PDO::FETCH_COLUMN) as $id_lang) {
    $pdo->exec("INSERT IGNORE INTO psc8_tab_lang (id_tab,id_lang,name) VALUES ($id_tab,$id_lang,'Conținut Site')");
}

// 4. Write hb_content.json
$map = [
    'hero_eyebrow'          => 'HB_HERO_EYEBROW',
    'hero_title'            => 'HB_HERO_TITLE',
    'hero_subtitle'         => 'HB_HERO_SUBTITLE',
    'hero_text'             => 'HB_HERO_TEXT',
    'hero_btn_catalog'      => 'HB_HERO_BTN_CATALOG',
    'hero_btn_packages'     => 'HB_HERO_BTN_PACKAGES',
    'cta_title'             => 'HB_CTA_TITLE',
    'cta_text'              => 'HB_CTA_TEXT',
    'cta_btn'               => 'HB_CTA_BTN',
    'packages_label'        => 'HB_PKG_LABEL',
    'packages_text'         => 'HB_PKG_TEXT',
    'packages_btn'          => 'HB_PKG_BTN',
    'catalog_hero_title'    => 'HB_CAT_TITLE',
    'catalog_hero_subtitle' => 'HB_CAT_SUBTITLE',
    'catalog_hero_text'     => 'HB_CAT_TEXT',
];
$data = [];
$cfgStmt = $pdo->prepare("SELECT value FROM psc8_configuration WHERE name=? LIMIT 1");
foreach ($map as $jk => $ck) {
    $cfgStmt->execute([$ck]);
    $data[$jk] = $cfgStmt->fetchColumn() ?: '';
}
file_put_contents(__DIR__ . '/../../../../../hb_content.json', json_encode($data, JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT));

echo "OK: module=$id_module tab=$id_tab\n";
unlink(__FILE__);
?>
