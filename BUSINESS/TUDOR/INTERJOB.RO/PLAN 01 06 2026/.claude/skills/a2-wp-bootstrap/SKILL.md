---
name: a2-wp-bootstrap
description: "Modify WordPress sites on A2 Hosting (loaiidil) by writing PHP bootstrap scripts and executing them via curl. Use for: changing WP site title/tagline/permalink, updating options, modifying posts, running SQL queries, deactivating plugins, changing themes. Must be triggered for ANY WordPress mutation on A2 domains. Trigger words: 'WP config', 'change site title', 'update permalink', 'draft hello world', 'run SQL on', 'wp bootstrap', 'fix wp', 'WordPress settings'."
---

# A2 WordPress Bootstrap

Execute WordPress/MySQL operations on A2 Hosting via PHP bootstrap pattern. **No SSH, no wp-cli, no phpMyAdmin.**

## The Pattern

1. Read `wp-config.php` to get DB credentials
2. Write a small PHP file to the domain WP root
3. Execute via curl
4. Delete the PHP file

## Connection

Same as `a2-cpanel` skill: `nl1-cl8-ats1.a2hosting.com:2083`, auth `cpanel loaiidil:KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453`.

## Critical: Disk Quota Block

If `Fileman/save_file_content` fails with "Disk quota exceeded", **stop and report BLOCKED**. No workaround — must free quota first via `a2-disk-cleanup` skill.

## PHP Bootstrap Template

```php
<?php
$db = new mysqli('localhost', 'DB_USER', 'DB_PASSWORD', 'DB_NAME');
if ($db->connect_error) { die("DB fail: " . $db->connect_error); }
// One or more queries:
$db->query("UPDATE prefix_options SET option_value='VALUE1' WHERE option_name='NAME1'");
$db->query("UPDATE prefix_prefix SET ...");
$db->close();
echo "OK: count";
```

Better (uses WordPress API):
```php
<?php
require __DIR__.'/wp-load.php';
update_option('blogname', 'New Title');
update_option('blogdescription', 'New Tagline');
update_option('permalink_structure', '/%postname%/');
$post = get_page_by_path('hello-world', OBJECT, 'post');
if ($post) wp_update_post(['ID' => $post->ID, 'post_status' => 'draft']);
echo "OK";
```

## Permalink Fix Note

`flush_rewrite_rules()` in the bootstrap script crashes on some WP installs (broken LiteSpeed Cache plugin hook). **Never call `flush_rewrite_rules()`** — permalink changes take effect on next WP page load. Instead, force a 404 visit to trigger rewrite flush.

## Electricjobs.eu Specific

- DB: `loaiidil_wp872` / user `loaiidil_wp872` / pass `4)bS)281pV` / prefix `wpib_`
- Fix SQL ready:
  - `UPDATE wpib_options SET option_value='Electric Jobs EU' WHERE option_name='blogname'`
  - `UPDATE wpib_options SET option_value='Hire verified electrical and technical workers from 40+ countries' WHERE option_name='blogdescription'`
  - `UPDATE wpib_options SET option_value='Europe/Bucharest' WHERE option_name='timezone_string'`
  - `UPDATE wpib_options SET option_value='/%postname%/' WHERE option_name='permalink_structure'`
  - `UPDATE wpib_posts SET post_status='draft' WHERE post_name='hello-world'`
- File: `fix_ej.php` at domain root

## Verification

After executing, verify via curl that the site reflects changes. For permalink changes, visit a sample URL to confirm 200 (not just front page).

## References

- Full cPanel API cheatsheet: `C:\Users\apami\.agents\skills\a2-cpanel\references\api-cheatsheet.md`
- WP bootstrap reference: `C:\Users\apami\.agents\skills\a2-cpanel\references\wp-bootstrap.md`
- Site audit: `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ELECTRICJOBS.EU\AUDIT_2026_06_25.md`
