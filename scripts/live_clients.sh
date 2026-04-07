#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-443}"

ss -Htn state established "( sport = :${PORT} )" \
  | awk '{print $4}' \
  | sed 's/^\[//; s/\]$//' \
  | sed 's/%.*//' \
  | rev | cut -d: -f2- | rev \
  | awk 'NF > 0' \
  | sort | uniq -c | sort -nr \
  | while read -r count ip; do
      printf "%s %s | " "$count" "$ip"
      geoiplookup "$ip" 2>/dev/null || echo "GeoIP lookup failed"
    done
