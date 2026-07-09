---
name: a2-disk-cleanup
description: "Inspect and free disk quota on the A2 loaiidil hosting account. Find large/unnecessary files across 34 domains, delete trash/test/error_log/stale WP files, and re-verify quota. Use when: disk quota exceeded, 'quota full', can't save files, or asked to 'clean up space', 'free quota', 'delete large files', 'inspect disk usage'. Combined with site-inspector agent for audit then delete."
---

# A2 Disk Cleanup

Clean disk quota on `loaiidil` A2 Hosting account (34 domains, cPanel UAPI only, no SSH).

## Connection

- Host: `nl1-cl8-ats1.a2hosting.com:2083`
- Auth: `Authorization: cpanel loaiidil:KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453`
- All file operations via `Fileman/*` endpoints
- Use `cpanel.sh` wrapper script from `C:\Users\apami\.agents\skills\a2-cpanel\scripts\cpanel.sh` (handles MSYS2 path mangling)

## Cleanup Targets (safe to delete)

| Target | Risk | Notes |
|--------|------|-------|
| `error_log` | Low | Accumulates over time, safe to remove |
| `.trash/` | Low | cPanel trash, safe to empty |
| Test files (`.txt`, `_test*.php`) | Low | Created during testing |
| Empty dirs under `wp-content/uploads/` | Low | No data loss |
| Stale `_maint_*.php` scripts | Low | Leftover from PHP bootstrap operations |
| Unused WP installations | High | Verify not in use before deleting |

## Limitations

- `Fileman/delete_files` endpoint is BROKEN on this A2 version ("could not find function")
- Fallback: overwrite files with empty content via `Fileman/save_file_content`
- Files that can't be deleted: note them in report, do not crash
- Total quota is account-level (~3.3MB for electricjobs.eu, but other domains consume the rest)

## Workflow

1. Inspect target domain(s) via `Fileman/list_files` recursively
2. Identify large files (>1MB) and known cleanup targets
3. For each file to delete: attempt `save_file_content` with empty string
4. After cleanup, try writing a 1-byte test file to verify quota freed
5. Report freed space and remaining blockers

## References

- Full cPanel API cheatsheet: `C:\Users\apami\.agents\skills\a2-cpanel\references\api-cheatsheet.md`
- WP bootstrap pattern: `C:\Users\apami\.agents\skills\a2-cpanel\references\wp-bootstrap.md`
