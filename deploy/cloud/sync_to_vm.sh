#!/bin/bash
# Trip-out handover: Mac -> VM. Run ON THE MAC.
#   1) silence Mac launchd  2) push state  3) re-enable VM cron.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
echo "1) disabling Mac launchd agents..."
for p in ~/Library/LaunchAgents/com.autoresearch.*.plist; do
  [ -e "$p" ] && launchctl unload "$p" 2>/dev/null && rm "$p"
done
echo "2) pushing storage/ + state/ to VM..."
rsync -az --exclude 'backups/' "$REPO/storage/" autoresearch-vm:~/autoresearch-trading-india/storage/
rsync -az "$REPO/state/" autoresearch-vm:~/autoresearch-trading-india/state/
echo "3) installing VM cron..."
scp -q "$REPO/deploy/cloud/crontab" autoresearch-vm:/tmp/crontab && ssh autoresearch-vm 'crontab /tmp/crontab && crontab -l | tail -3'
echo "DONE — VM is now the sole scheduler."
