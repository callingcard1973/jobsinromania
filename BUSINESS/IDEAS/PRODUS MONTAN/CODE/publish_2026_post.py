#!/usr/bin/env python3
"""Publish 2026 production interest post on agroevolution.com."""
import urllib.request
import ssl
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# --
API_TOKEN = "KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PHP = r"""<?php
define("ABSPATH", dirname(__FILE__) . "/");
require_once ABSPATH . "wp-load.php";

$content = <<<'HTML'
<img class="alignnone size-medium wp-image-270" src="https://agroevolution.com/wp-content/uploads/2024/02/cropped-Green-Agriculture-Farming-Business-Logo-2-300x300.png" alt="Agro Evolution - Produs Montan 2026" width="300" height="300" />

<strong>Subiect:</strong> Solicitare de oferta pentru produse agricole si alimentare - Productia 2026

&nbsp;

Stimate producator,

<strong>Gospodarii de Altadata Cooperativa Agricola</strong> (CUI 51957925), in parteneriat cu <strong>Agro Evolution</strong>, cauta furnizori pentru sezonul de productie 2026. Suntem interesati sa evaluam potentialul de colaborare pentru achizitia si distributia urmatoarelor categorii de produse:

<h3>Produse Montane Certificate (RNPM)</h3>
<ul>
 	<li><strong>Lapte si produse lactate</strong>: Branza, cascaval, telemea, smantana, unt, iaurt, urda (toate varietatile certificate Produs Montan)</li>
 	<li><strong>Produse apicole</strong>: Miere (salcam, poliflora, mana, zmeur, tei, rapita), propolis, polen, ceara, pastura</li>
 	<li><strong>Produse vegetale</strong>: Cartofi, legume de munte, fructe de padure (afine, zmeura, mure, catina), nuci, alune, castane, ciuperci salbatice</li>
 	<li><strong>Carne si preparate</strong>: Salam, carnati, sunca, pastrama, bacon, carne de vita/porc/oaie de munte</li>
 	<li><strong>Oua</strong>: Oua de gaina crescute la ferma de munte</li>
 	<li><strong>Peste</strong>: Pastrav si produse din peste de munte</li>
 	<li><strong>Paine si patiserie</strong>: Paine de casa, cozonac, produse de panificatie traditionala</li>
</ul>

<h3>Fructe si Legume Proaspete (Export)</h3>
<ul>
 	<li><strong>Fructe</strong>: Mere (Braeburn, Fuji, Golden Delicious, Granny Smith, Pink Lady, Royal Gala), capsuni, cirese, visine, prune, caise, piersici, pere</li>
 	<li><strong>Legume</strong>: Tomate (toate varietatile), castraveti, ardei gras, ardei iute, ceapa, usturoi, cartofi, varza, morcovi, sfecla, fasole, mazare, spanac, salata</li>
 	<li><strong>Ciuperci</strong>: Champignon, pleurotus, shiitake, ciuperci salbatice</li>
 	<li><strong>Plante aromatice</strong>: Coriandru, menta, patrunjel, marar, busuioc, cimbru, rozmarin</li>
</ul>

<h3>Ce oferim</h3>
<ul>
 	<li>Achizitie la preturi competitive, cu plata la termen</li>
 	<li>Distributie catre hipermarketuri (Kaufland, Lidl, Carrefour, Mega Image)</li>
 	<li>Export catre piata europeana (Franta, Germania, Marea Britanie, Italia, Spania)</li>
 	<li>Facturare unica prin cooperativa - simplificam procesul pentru producatorii mici</li>
 	<li>Listare gratuita in catalogul online: <a href="https://agroevolution.com/catalog/" target="_blank">agroevolution.com/catalog</a> (1.331 producatori, 3.812 produse)</li>
 	<li>Listare in magazinul online: <a href="https://agroevolution.com/shop/" target="_blank">agroevolution.com/shop</a></li>
</ul>

<h3>Cum puteti participa</h3>
Va rugam sa ne contactati cu:
<ol>
 	<li>Lista de produse disponibile si cantitati estimate pentru 2026</li>
 	<li>Preturile orientative (per kg sau per unitate)</li>
 	<li>Fotografii ale produselor (pentru catalog si magazin online)</li>
 	<li>Certificari detinute (Produs Montan, Bio, Produs Traditional, HACCP)</li>
</ol>

<strong>Contact:</strong>
Email: <strong><a href="mailto:tudor@agroevolution.com">tudor@agroevolution.com</a></strong>
WhatsApp: <strong><a href="https://wa.me/40723068733">+40 723 068 733</a></strong>
Catalog online: <strong><a href="https://agroevolution.com/catalog/">agroevolution.com/catalog</a></strong>
Magazin: <strong><a href="https://agroevolution.com/shop/">agroevolution.com/shop</a></strong>

&nbsp;

<em>Gospodarii de Altadata Cooperativa Agricola | CUI 51957925</em>
<em>Agregator national de produse montane si agricole certificate</em>

&nbsp;

#ProdusMontan #AgriculturaRomania #ProduseTraditionale #CooperativaAgricola #ExportAgricol #Miere #Branza #Cascaval #FructePadure #LegumeProaspete #Cartofi #ProduseMontane #FermierRoman #AgroEvolution #Kaufland #Lidl #Carrefour #MegaImage #HypermarketRomania #FurnizorAgricol #ProductieAgricola2026
HTML;

$existing = get_page_by_path("exprimam-interes-in-productie-2026", OBJECT, "post");
if ($existing) {
    wp_update_post(array("ID" => $existing->ID, "post_content" => $content));
    $post_id = $existing->ID;
    echo "Updated post ID=$post_id\n";
} else {
    $post_id = wp_insert_post(array(
        "post_title"   => "Exprimam interes in productie 2026 - Produse Montane si Agricole",
        "post_name"    => "exprimam-interes-in-productie-2026",
        "post_content" => $content,
        "post_status"  => "publish",
        "post_type"    => "post",
        "post_author"  => 1,
        "post_category" => array(2, 3, 51),
    ));
    echo "Created post ID=$post_id\n";
}

wp_set_post_categories($post_id, array(2, 3, 51));
wp_set_post_tags($post_id, array(
    "produs montan", "produse montane", "agricultura 2026",
    "cooperativa agricola", "export legume fructe",
    "miere", "branza", "cascaval", "lactate",
    "fructe padure", "cartofi munte", "produse traditionale",
    "Kaufland", "Lidl", "Carrefour", "hypermarket",
    "furnizor", "producator", "Romania"
));

header("X-LiteSpeed-Purge: *");
echo "URL: " . get_permalink($post_id) . "\n";
unlink(__FILE__);
?>"""


def main():
    boundary = "----FormBound7MA4YWxk"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="dir"\r\n\r\n'
        f"/home/{USER}/agroevolution.com\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        f"1\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file-1"; filename="post2026_temp.php"\r\n'
        f"Content-Type: application/x-php\r\n\r\n"
    ).encode("utf-8") + PHP.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"cpanel {USER}:{API_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    urllib.request.urlopen(req, timeout=30, context=CTX)
    print("Script uploaded, executing...")

    ctx2 = ssl.create_default_context()
    resp = urllib.request.urlopen(
        "https://agroevolution.com/post2026_temp.php", timeout=30, context=ctx2
    )
    print(resp.read().decode("utf-8"))


if __name__ == "__main__":
    main()
