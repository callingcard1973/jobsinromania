<?php
// Deploy operator websites: extract zip, clean up
$targetDir = '/home/loaiidil/interjob.ro/iscir/operatori/';
$zipPath = $targetDir . 'iscir_operatori.zip';

// Ensure target exists
if (!is_dir($targetDir)) {
    mkdir($targetDir, 0755, true);
}

// Accept file upload
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['file'])) {
    $uploaded = $_FILES['file'];
    if ($uploaded['error'] === UPLOAD_ERR_OK) {
        move_uploaded_file($uploaded['tmp_name'], $zipPath);
        echo "Uploaded: " . $uploaded['name'] . " (" . filesize($zipPath) . " bytes)\n";
    } else {
        echo "Upload error: " . $uploaded['error'] . "\n";
        exit;
    }
} else {
    echo "No file uploaded. Send POST with file=@iscir_operatori.zip\n";
    exit;
}

// Extract zip
$zip = new ZipArchive();
if ($zip->open($zipPath) === TRUE) {
    $zip->extractTo($targetDir);
    $count = $zip->numFiles;
    $zip->close();
    echo "Extracted $count files to $targetDir\n";
} else {
    echo "Failed to open zip\n";
    exit;
}

// Delete zip
unlink($zipPath);
echo "Deleted zip\n";

// Verify
$files = glob($targetDir . '*.html');
echo "Verified: " . count($files) . " HTML files in $targetDir\n";
echo "DONE\n";
