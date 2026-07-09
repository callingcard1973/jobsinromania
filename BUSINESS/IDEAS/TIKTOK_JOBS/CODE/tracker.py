"""Log generated TikTok posts to raspibig tiktok_posts table."""
import subprocess
import sys
import io

if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RASPI = "tudor@192.168.100.21"


def esc(s):
    return (s or "").replace("'", "''")


def log_post(job_id, source, lang, channel, hook, video_path):
    sql = (
        f"INSERT INTO tiktok_posts (job_id, source, lang, channel, hook, video_path) "
        f"VALUES ('{esc(job_id)}','{esc(source)}','{esc(lang)}','{esc(channel)}',"
        f"'{esc(hook)}','{esc(video_path)}') "
        f"ON CONFLICT (job_id, lang, channel) DO NOTHING RETURNING id;"
    )
    cmd = ["ssh", RASPI, f"sudo -u postgres psql -d interjob_master -t -A -c \"{sql}\""]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() or "EXISTS"


if __name__ == "__main__":
    print(log_post(*sys.argv[1:7]))
