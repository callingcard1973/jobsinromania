from __future__ import annotations

import subprocess
from pathlib import Path


HOST = '192.168.100.21'
REMOTE_DIR = '/opt/ACTIVE/DB/ASOCIATII/ASOC_PROP'
BASE_DIR = Path(__file__).resolve().parent

FILES_TO_UPLOAD = [
    'ONG_REGISTRU_NATIONAL.tsv',
    'ONG_SHORTLIST_5000.tsv',
    'raspibig_ong_ingest_remote.py',
]


def run(command: list[str]) -> None:
    print('Running:', ' '.join(command))
    subprocess.run(command, check=True)


def main() -> None:
    for file_name in FILES_TO_UPLOAD:
        local_path = BASE_DIR / file_name
        if not local_path.exists():
            raise FileNotFoundError(f'Missing file: {local_path}')
        run(['scp', str(local_path), f'{HOST}:{REMOTE_DIR}/{file_name}'])

    run(['ssh', HOST, f'python3 {REMOTE_DIR}/raspibig_ong_ingest_remote.py'])


if __name__ == '__main__':
    main()