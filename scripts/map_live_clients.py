#!/usr/bin/env python3
import argparse
import html
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PORT = 443
DEFAULT_OUTPUT = "reports/live_clients_map.html"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build an HTML map for currently connected VPN client IPs."
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="VPN port (default: 443)")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output HTML file (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def get_live_ips(port: int) -> list[tuple[str, int]]:
    cmd = [
        "bash",
        "-lc",
        f"ss -Htn state established '( sport = :{port} )' | awk '{{print $4}}' | "
        "sed 's/^\\[//; s/\\]$//' | sed 's/%.*//' | rev | cut -d: -f2- | rev | "
        "awk 'NF > 0' | sort | uniq -c | sort -nr",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    pairs: list[tuple[str, int]] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            count = int(parts[0])
        except ValueError:
            continue
        ip = parts[1]
        pairs.append((ip, count))
    return pairs


def lookup_ip(ip: str) -> dict:
    url = f"https://ipwho.is/{ip}"
    request = urllib.request.Request(url, headers={"User-Agent": "telegram-vpn-bot/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.load(response)
    if not payload.get("success"):
        raise RuntimeError(payload.get("message", f"Failed to resolve {ip}"))
    return payload


def build_html(markers: list[dict]) -> str:
    markers_json = json.dumps(markers, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VPN Clients Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f5f7fb;
      color: #102a43;
    }}
    .header {{
      padding: 20px 24px 8px;
    }}
    .header h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .header p {{
      margin: 0;
      color: #486581;
    }}
    #map {{
      height: 70vh;
      margin: 16px 24px 24px;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 20px 60px rgba(16, 42, 67, 0.12);
    }}
    .list {{
      margin: 0 24px 24px;
      background: #fff;
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 20px 60px rgba(16, 42, 67, 0.08);
    }}
    .item {{
      padding: 12px 0;
      border-bottom: 1px solid #e6edf5;
    }}
    .item:last-child {{
      border-bottom: none;
    }}
    .ip {{
      font-weight: 700;
    }}
    .meta {{
      color: #486581;
      margin-top: 4px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Карта активных VPN-подключений</h1>
    <p>Точки строятся по IP-адресам, которые прямо сейчас держат TCP-соединения на VPN-порту.</p>
  </div>
  <div id="map"></div>
  <div class="list" id="list"></div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const markers = {markers_json};
    const map = L.map('map').setView([55.75, 37.62], 2);
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const bounds = [];
    const list = document.getElementById('list');

    markers.forEach((item) => {{
      const marker = L.marker([item.latitude, item.longitude]).addTo(map);
      marker.bindPopup(
        `<strong>${{item.ip}}</strong><br>` +
        `Подключений: ${{item.connections}}<br>` +
        `Страна: ${{item.country}}<br>` +
        `Город: ${{item.city || '-'}}<br>` +
        `Провайдер: ${{item.connection || '-'}}`
      );
      bounds.push([item.latitude, item.longitude]);

      const el = document.createElement('div');
      el.className = 'item';
      el.innerHTML =
        `<div class="ip">${{item.ip}} · ${{item.connections}} подключений</div>` +
        `<div class="meta">${{item.country}}, ${{item.city || '-'}} · ${{item.connection || '-'}}</div>`;
      list.appendChild(el);
    }});

    if (bounds.length === 1) {{
      map.setView(bounds[0], 6);
    }} else if (bounds.length > 1) {{
      map.fitBounds(bounds, {{ padding: [40, 40] }});
    }}
  </script>
</body>
</html>"""


def main():
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        live_ips = get_live_ips(args.port)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.stderr or exc.stdout or str(exc))

    if not live_ips:
        raise SystemExit("No active IPs found on the selected port.")

    markers: list[dict] = []
    for ip, count in live_ips:
        try:
            geo = lookup_ip(ip)
        except (RuntimeError, urllib.error.URLError) as exc:
            print(f"Warning: failed to resolve {ip}: {exc}", file=sys.stderr)
            continue
        latitude = geo.get("latitude")
        longitude = geo.get("longitude")
        if latitude is None or longitude is None:
            print(f"Warning: no coordinates for {ip}", file=sys.stderr)
            continue
        markers.append(
            {
                "ip": ip,
                "connections": count,
                "country": html.escape(geo.get("country", "-")),
                "city": html.escape(geo.get("city", "")),
                "connection": html.escape((geo.get("connection") or {}).get("isp", "")),
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    if not markers:
        raise SystemExit("No mappable IPs found.")

    output_path.write_text(build_html(markers), encoding="utf-8")
    print(f"Map saved to {output_path}")


if __name__ == "__main__":
    main()
