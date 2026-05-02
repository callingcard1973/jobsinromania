param(
    [string]$Remote = "tudor@192.168.100.21:/opt/ACTIVE/FOOD/"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$windowsHome = $HOME -replace '\\', '/'

function Convert-ToMsysPath {
  param([string]$WindowsPath)

  $normalized = ([System.IO.Path]::GetFullPath($WindowsPath)) -replace '\\', '/'
  if ($normalized -match '^([A-Za-z]):/(.*)$') {
    $drive = $matches[1].ToLowerInvariant()
    $rest = $matches[2]
    return "/$drive/$rest"
  }

  return $normalized
}

$source = Convert-ToMsysPath $scriptDir

$msysCommand = @"
export HOME="$windowsHome"
rsync -av --human-readable \
  --exclude '.git/' \
  --exclude '.venv/' \
  -e "ssh -i \"$HOME/.ssh/id_ed25519\" -o UserKnownHostsFile=\"$HOME/.ssh/known_hosts\"" \
  "$source/" \
  "$Remote"
"@

& 'C:\msys64\usr\bin\bash.exe' -lc $msysCommand
exit $LASTEXITCODE