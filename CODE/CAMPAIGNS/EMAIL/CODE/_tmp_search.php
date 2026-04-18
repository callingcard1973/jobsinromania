<?php
ini_set('max_execution_time',600);
error_reporting(E_ALL);
ini_set('display_errors',1);
header('Content-Type:text/plain');

$new='+33 7 51 17 13 56';
$patterns=['0722 789 938','0722789938','0722-789-938','+40 722 789 938','+40722789938','40722789938','+33751171356'];
$wa_old='wa.me/40722789938';
$wa_new='wa.me/33751171356';

// === WORDPRESS DATABASES ===
echo "=== WORDPRESS DATABASES ===\n";
$all=glob('/home/loaiidil/*/wp-config.php');
$db_total=0;
foreach($all as $f){
  $d=basename(dirname($f));
  $c=file_get_contents($f);
  preg_match_all("/define\s*\(\s*'(DB_NAME|DB_USER|DB_PASSWORD)'\s*,\s*'([^']*)'/", $c, $m, PREG_SET_ORDER);
  $cfg=[];
  foreach($m as $match) $cfg[$match[1]]=$match[2];
  if(!isset($cfg['DB_NAME'])||!isset($cfg['DB_USER'])||!isset($cfg['DB_PASSWORD']))continue;
  preg_match("/table_prefix\s*=\s*'([^']*)'/", $c, $tp);
  if(!isset($tp[1]))continue;
  $db=@new mysqli('localhost',$cfg['DB_USER'],$cfg['DB_PASSWORD'],$cfg['DB_NAME']);
  if($db->connect_error)continue;
  $pf=$tp[1];
  $affected=0;
  foreach($patterns as $old){
    foreach(['posts','options','postmeta'] as $tbl){
      $col=($tbl=='options')?'option_value':($tbl=='postmeta'?'meta_value':'post_content');
      $r=@$db->query("UPDATE {$pf}{$tbl} SET {$col}=REPLACE({$col},'{$old}','{$new}') WHERE {$col} LIKE '%{$old}%'");
      if($r) $affected+=$db->affected_rows;
    }
  }
  // Also fix wa.me links
  foreach(['posts','options','postmeta'] as $tbl){
    $col=($tbl=='options')?'option_value':($tbl=='postmeta'?'meta_value':'post_content');
    $r=@$db->query("UPDATE {$pf}{$tbl} SET {$col}=REPLACE({$col},'{$wa_old}','{$wa_new}') WHERE {$col} LIKE '%{$wa_old}%'");
    if($r) $affected+=$db->affected_rows;
  }
  if($affected>0){
    echo "$d: $affected replacements\n";
    $db_total+=$affected;
  }
  $db->close();
}
echo "DB total: $db_total\n\n";

// === STATIC HTML FILES ===
echo "=== STATIC HTML FILES ===\n";
$html_total=0;
$dirs=glob('/home/loaiidil/*',GLOB_ONLYDIR);
foreach($dirs as $dir){
  $domain=basename($dir);
  $files=glob("$dir/*.html");
  foreach($files as $hf){
    $content=@file_get_contents($hf);
    if(!$content)continue;
    $changed=false;
    foreach($patterns as $old){
      if(strpos($content,$old)!==false){
        $content=str_replace($old,$new,$content);
        $changed=true;
      }
    }
    if(strpos($content,$wa_old)!==false){
      $content=str_replace($wa_old,$wa_new,$content);
      $changed=true;
    }
    if($changed){
      file_put_contents($hf,$content);
      echo "$domain/".basename($hf).": updated\n";
      $html_total++;
    }
  }
}
echo "HTML total: $html_total files\n\n";
echo "=== GRAND TOTAL: $db_total DB + $html_total HTML ===\n";
echo "All replaced with $new\nDONE\n";
?>
