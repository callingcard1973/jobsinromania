#!/usr/bin/env python3
"""Update 2026 post contact info to French WhatsApp."""
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

$post = get_page_by_path("exprimam-interes-in-productie-2026", OBJECT, "post");
if (!$post) { echo "Post not found\n"; unlink(__FILE__); exit; }

$content = $post->post_content;

// Replace WhatsApp links and phone
$content = str_replace("https://wa.me/40723068733", "https://wa.me/33751171356", $content);
$content = str_replace("+40 723 068 733", "+33 7 51 17 13 56", $content);

wp_update_post(array("ID" => $post->ID, "post_content" => $content));
header("X-LiteSpeed-Purge: *");
echo "Updated post ID=" . $post->ID . "\n";
echo "URL: " . get_permalink($post->ID) . "\n";
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
        f'Content-Disposition: form-data; name="file-1"; filename="upd_contact_temp.php"\r\n'
        f"Content-Type: application/x-php\r\n\r\n"
    ).encode("utf-8") + PHP.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"cpanel {USER}:{API_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    urllib.request.urlopen(req, timeout=30, context=CTX)

    ctx2 = ssl.create_default_context()
    resp = urllib.request.urlopen(
        "https://agroevolution.com/upd_contact_temp.php", timeout=30, context=ctx2
    )
    print(resp.read().decode("utf-8"))


if __name__ == "__main__":
    main()
