<?php
/**
 * scan_mailbox_dnc.php
 * Self-contained script to scan A2 IMAP mailboxes for opt-out/unsubscribe requests.
 * Usage: Update $BATCH array at the top, then run via web or CLI.
 * 
 * Deploy to any writable A2 directory, execute, clean up.
 */

// === CONFIG ===
$PW = 'InterJobScan2026!';
$API_TOKEN = 'KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453';

// Edit this batch before each run:
$BATCH = [
    'office@interjob.ro',
    'crm@interjob.ro',
    'office@factoryjobs.eu',
    'office@farmworkers.eu',
    // add more...
];

// === OPT-OUT KEYWORDS ===
$OPT_KW = [
    'unsubscribe', 'dezabonare', 'stop', 'opt-out', 'opt out',
    'nu mai', 'remove', 'delete', 'nu trimite', 'do not send',
    'please remove', 'spam', 'not interested', 'nu ma mai', 'nu mă mai',
    'renunț', 'renunt', 'sterge', 'șterge', 'take me off',
    'cease', 'desist', 'nu mai contacta',
];

// === FALSE POSITIVE SKIP ===
function is_false_positive($body_lower) {
    $skip = [
        'you have been unsubscribed',
        'your unsubscribe request',
        'an api key has been deleted',
        'smtp2go spam/bounce',
        'stopped us in our tracks',
    ];
    foreach ($skip as $s) {
        if (strpos($body_lower, $s) !== false) return true;
    }
    return false;
}

// === MAIN ===
$found = [];

foreach ($BATCH as $email) {
    $mbox = @imap_open("{localhost:993/imap/ssl/novalidate-cert}INBOX", $email, $PW, OP_READONLY, 0);
    if (!$mbox) { echo "FAIL: $email - " . imap_last_error() . "\n"; continue; }
    
    $total = imap_num_msg($mbox);
    echo "OK: $email ($total msgs)\n";
    
    for ($i = $total; $i >= max(1, $total - 300); $i--) {
        $h = @imap_headerinfo($mbox, $i);
        if (!$h) continue;
        
        $subj = mb_decode_mimeheader($h->subject ?? '');
        $from = $h->from[0]->mailbox . '@' . $h->from[0]->host;
        $name = $h->from[0]->personal ?? '';
        $date = date('Y-m-d H:i', $h->udate);
        $lower = strtolower($subj . ' ' . $name . ' ' . $from);
        
        foreach ($OPT_KW as $kw) {
            if (strpos($lower, $kw) !== false) {
                // Fetch body
                $body = '';
                for ($p = 1; $p <= 3; $p++) {
                    $part = @imap_fetchbody($mbox, $i, $p);
                    if (!empty(trim($part ?? '')) && $part !== ' ') { $body = $part; break; }
                }
                if (empty($body)) $body = @imap_body($mbox, $i);
                $body_l = strtolower(mb_convert_encoding($body ?? '', 'UTF-8', 'UTF-8,ISO-8859-1,ISO-8859-2'));
                
                if (!is_false_positive($body_l)) {
                    $found[] = [
                        'box' => $email, 'from' => $from, 'name' => $name,
                        'subj' => $subj, 'date' => $date, 'kw' => $kw,
                        'body' => substr(preg_replace('/\s+/', ' ', $body_l), 0, 300),
                    ];
                }
                break;
            }
        }
    }
    imap_close($mbox);
}

// === REPORT ===
echo "\n=== OPT-OUTS FOUND: " . count($found) . " ===\n";
if (count($found) > 0) {
    $csv = fopen('mailbox_optouts.csv', 'w');
    fputcsv($csv, ['email', 'source_mailbox', 'date', 'subject', 'keyword', 'reason_body']);
    
    foreach ($found as $o) {
        echo "BOX: {$o['box']}\nFROM: {$o['from']}\nSUBJ: {$o['subj']}\nDATE: {$o['date']}\nKW: '{$o['kw']}'\nBODY: {$o['body']}\n\n";
        fputcsv($csv, [$o['from'], $o['box'], $o['date'], $o['subj'], $o['kw'], $o['body']]);
    }
    fclose($csv);
    echo "CSV written: mailbox_optouts.csv\n";
} else {
    echo "No opt-outs found. All clear.\n";
}
