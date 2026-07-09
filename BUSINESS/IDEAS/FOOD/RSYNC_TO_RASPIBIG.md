# Rsync To Raspibig

## Reusable Command

```powershell
$homeMsys = $HOME -replace '\\', '/'
C:\msys64\usr\bin\bash.exe -lc "export HOME=$homeMsys; rsync -av --human-readable -e 'ssh -i \$HOME/.ssh/id_ed25519 -o UserKnownHostsFile=\$HOME/.ssh/known_hosts' /d/MEMORY/IDEAS/FOOD/ tudor@192.168.100.21:/opt/ACTIVE/FOOD/"
```

Run it from `D:/MEMORY/IDEAS/FOOD`.

## Scripted Usage

```powershell
.\sync_to_raspibig.ps1
```

or

```cmd
sync_to_raspibig.cmd
```

## Notes
- Remote target: `/opt/ACTIVE/FOOD/`
- Remote host: `tudor@192.168.100.21`
- Uses MSYS `rsync` with the existing Windows SSH key
- Does not delete existing remote files