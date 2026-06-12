#!/bin/bash
# Trip-back handover: VM -> Mac. Run ON THE MAC.
# Rule: exactly ONE scheduler alive. This script enforces the order:
#   1) silence the VM cron  2) pull state  3) re-enable Mac launchd agents.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
echo "1) disabling VM cron..."
ssh autoresearch-vm 'crontab -r && echo "   VM cron removed"'
echo "2) pulling storage/ + state/ from VM..."
rsync -az autoresearch-vm:~/autoresearch-trading-india/storage/ "$REPO/storage/"
rsync -az autoresearch-vm:~/autoresearch-trading-india/state/ "$REPO/state/"
echo "3) reinstalling Mac launchd agents..."
for p in "$REPO"/deploy/launchd/com.autoresearch.*.plist; do
  cp "$p" ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/"$(basename "$p")"
done
launchctl list | grep autoresearch
echo "DONE — Mac is now the sole scheduler. (Keep the VM stopped or cron-less.)"
