<?php
/**
 * CV Parser API — A2 Hosting PHP
 * Accepts file upload, returns structured JSON.
 * Deployed to: domain.tld/cv/api.php on all 14 job sites
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { echo json_encode(['error'=>'POST required']); exit; }

function extract_text(string $path, string $name): string {
    $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
    if ($ext === 'txt')  return file_get_contents($path);
    if (in_array($ext, ['html','htm'])) return strip_tags(file_get_contents($path));
    if ($ext === 'pdf') {
        $out = shell_exec('pdftotext -raw ' . escapeshellarg($path) . ' - 2>/dev/null');
        if ($out && strlen(trim($out)) > 20) return $out;
        return file_get_contents($path); // fallback raw bytes
    }
    if ($ext === 'docx') {
        $zip = new ZipArchive();
        if ($zip->open($path) === true) {
            $xml = $zip->getFromName('word/document.xml');
            $zip->close();
            if ($xml) return preg_replace('/<[^>]+>/',' ', $xml);
        }
    }
    return file_get_contents($path);
}

function parse_cv(string $text): array {
    $text = preg_replace('/\r\n|\r/', "\n", $text);
    $lines = array_values(array_filter(array_map('trim', explode("\n", $text)), fn($l)=>strlen($l)>1));

    // Email
    preg_match('/\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b/', $text, $em);
    $email = $em[1] ?? '';

    // Phone — E.164 and common formats
    preg_match('/(\+?\d[\d\s\-().]{7,14}\d)/', $text, $ph);
    $phone = $ph[1] ?? '';

    // Name — first line that looks like a name (2-4 words, mostly letters)
    $name = '';
    foreach (array_slice($lines,0,5) as $l) {
        if (preg_match('/^[A-ZÀ-Ö][a-zà-ö]+(\s[A-ZÀ-Ö][a-zà-ö]+){1,3}$/', $l)) { $name=$l; break; }
    }
    if (!$name && isset($lines[0])) $name = $lines[0];

    // Title — line after name that looks like a job title (not email/phone/address)
    $title = '';
    $skip = false;
    foreach (array_slice($lines,1,6) as $l) {
        if ($skip) break;
        if ($l === $name) continue;
        if (strpos($l,'@')!==false || preg_match('/^\+?\d/',$l)) continue;
        if (preg_match('/\b(engineer|developer|manager|analyst|designer|director|officer|specialist|consultant|coordinator|lead|senior|junior|architect|technician|worker|operator)\b/i', $l)) {
            $title = $l; $skip = true;
        }
    }

    // Sections
    $sections = ['experience'=>[], 'education'=>[], 'skills'=>[], 'languages'=>[]];
    $current = null;
    $buf = [];
    $section_pats = [
        'experience' => '/\b(experience|employment|work history|career)\b/i',
        'education'  => '/\b(education|qualification|study|degree|university|school)\b/i',
        'skills'     => '/\b(skills|competenc|technical|expertise)\b/i',
        'languages'  => '/\b(language)\b/i',
    ];
    foreach ($lines as $l) {
        $matched = false;
        foreach ($section_pats as $sec => $pat) {
            if (preg_match($pat, $l) && strlen($l) < 60) {
                if ($current && $buf) $sections[$current][] = implode("\n", $buf);
                $current = $sec; $buf = []; $matched = true; break;
            }
        }
        if (!$matched && $current) $buf[] = $l;
    }
    if ($current && $buf) $sections[$current][] = implode("\n", $buf);

    // Parse experience entries
    $experience = [];
    foreach ($sections['experience'] as $block) {
        $blines = array_values(array_filter(array_map('trim', explode("\n", $block))));
        $entry = ['company'=>'', 'role'=>'', 'start'=>'', 'end'=>'', 'description'=>''];
        $desc = [];
        foreach ($blines as $i => $bl) {
            // "Role - Company (YYYY-YYYY)" or "Role at Company, YYYY-YYYY"
            if ($i===0 && preg_match('/^(.+?)\s*[-–@at]\s*(.+?)\s*[\(\[,]?\s*(\d{4})\s*[-–]\s*(\d{4}|present|current)/i', $bl, $m)) {
                $entry['role']=$m[1]; $entry['company']=$m[2];
                $entry['start']=$m[3]; $entry['end']=preg_match('/present|current/i',$m[4])?'Present':$m[4];
            } elseif ($i===0) { $entry['role'] = $bl; }
            elseif ($i===1 && !$entry['company']) { $entry['company'] = $bl; }
            elseif (preg_match('/(\d{4})\s*[-–]\s*(\d{4}|present|current)/i', $bl, $m)) {
                if (!$entry['start']) { $entry['start']=$m[1]; $entry['end']=strtolower($m[2])==='present'?'Present':$m[2]; }
            } else { $desc[] = $bl; }
        }
        $entry['description'] = implode(' ', array_slice($desc,0,3));
        if ($entry['role']) $experience[] = $entry;
    }

    // Parse education
    $education = [];
    foreach ($sections['education'] as $block) {
        $blines = array_values(array_filter(array_map('trim', explode("\n", $block))));
        if (!$blines) continue;
        $ed = ['institution'=>'', 'degree'=>'', 'field'=>'', 'start'=>'', 'end'=>''];
        $ed['degree'] = $blines[0] ?? '';
        $ed['institution'] = $blines[1] ?? '';
        if (preg_match('/(\d{4})\s*[-–]\s*(\d{4})/i', implode(' ',$blines), $m)) {
            $ed['start']=$m[1]; $ed['end']=$m[2];
        }
        if ($ed['degree']) $education[] = $ed;
    }

    // Skills — comma or newline separated
    $skills = [];
    if ($sections['skills']) {
        $raw = implode(',', $sections['skills']);
        foreach (preg_split('/[,\n•·\-]+/', $raw) as $s) {
            $s = trim($s); if ($s && strlen($s)>1 && strlen($s)<50) $skills[] = $s;
        }
    }

    // Languages
    $languages = [];
    if ($sections['languages']) {
        foreach (array_filter(array_map('trim', explode("\n", implode("\n",$sections['languages'])))) as $l) {
            if (preg_match('/^([A-Za-z]+)\s*[-–:]\s*(.+)$/', $l, $m)) {
                $languages[] = ['language'=>trim($m[1]), 'level'=>trim($m[2])];
            } elseif (strlen($l)<40) {
                $languages[] = ['language'=>$l, 'level'=>''];
            }
        }
    }

    // Summary — first paragraph before any section
    $summary = '';
    foreach ($lines as $l) {
        $is_section = false;
        foreach ($section_pats as $pat) { if (preg_match($pat,$l)&&strlen($l)<60) {$is_section=true;break;} }
        if ($is_section) break;
        if ($l!==$name && $l!==$title && strpos($l,'@')===false && !preg_match('/^\+?\d/',$l) && strlen($l)>30) {
            $summary = $l; break;
        }
    }

    return compact('name','email','phone','title','summary','experience','education','skills','languages');
}

// --- Main ---
if (empty($_FILES['file'])) { echo json_encode(['error'=>'No file uploaded']); exit; }
$f = $_FILES['file'];
if ($f['error'] !== UPLOAD_ERR_OK) { echo json_encode(['error'=>'Upload error: '.$f['error']]); exit; }

$text = extract_text($f['tmp_name'], $f['name']);
if (!$text || strlen(trim($text)) < 20) { echo json_encode(['error'=>'Could not extract text from file']); exit; }

$cv = parse_cv($text);
echo json_encode(['status'=>'ok', 'cv'=>$cv, 'source'=>'php-parser']);
