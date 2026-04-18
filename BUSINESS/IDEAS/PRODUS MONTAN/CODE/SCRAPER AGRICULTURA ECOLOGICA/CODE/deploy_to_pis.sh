#!/bin/bash
# Usage: ./deploy_to_pis.sh
# Copies project directories to remote Raspberry Pi hosts
# Adjust destinations and SSH user as needed.

SRC_DIR="$(pwd)/.."  # CODE parent directory
DEST_DIR="~/scraper_agro"  # remote base path
HOSTS=("raspibig" "raspi")

for host in "${HOSTS[@]}"; do
    echo "Deploying to $host..."
    # ensure destination exists
    ssh "$host" "mkdir -p $DEST_DIR"
    rsync -avz --delete "$SRC_DIR/CODE" "$SRC_DIR/DATA" "$host:$DEST_DIR/"
    echo "Done $host."
    echo

done

# Notes:
# - requires SSH keys set up for passwordless login to the hosts.
# - modifies remote directory to match local CODE/DATA structure.
# - run from the CODE directory.
#
# To retrieve the project from a host back to this machine, use rsync in reverse:
#
#   rsync -avz tudor@raspibig:~/scraper_agro/CODE .
#   rsync -avz tudor@raspibig:~/scraper_agro/DATA .
#
# or swap the source/target in the loop above if you prefer a dedicated pull script.
