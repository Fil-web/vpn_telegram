#!/usr/bin/env python3
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB_PATH = "/etc/x-ui/x-ui.db"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Show human-readable x-ui client audit information."
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Path to x-ui.db (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--email",
        help="Show only one client by email, for example tg_1017786982",
    )
    parser.add_argument(
        "--suspicious-ip-count",
        type=int,
        default=3,
        help="Mark client as suspicious when IP count is greater or equal to this value (default: 3)",
    )
    parser.add_argument(
        "--ips-only",
        action="store_true",
        help="Show compact list: user -> all known IPs",
    )
    parser.add_argument(
        "--sort-by-traffic",
        action="store_true",
        help="Sort output by total traffic, descending",
    )
    parser.add_argument(
        "--suspicious-only",
        action="store_true",
        help="Show only clients with suspicious IP behavior or limit overflow",
    )
    parser.add_argument(
        "--high-traffic-gb",
        type=float,
        default=60.0,
        help="Mark client as high traffic when total usage reaches this many GB (default: 60)",
    )
    parser.add_argument(
        "--new-user-days",
        type=int,
        default=3,
        help="Treat user as new for this many days from creation time (default: 3)",
    )
    parser.add_argument(
        "--new-user-heavy-gb",
        type=float,
        default=15.0,
        help="Mark new user as suspicious when traffic reaches this many GB (default: 15)",
    )
    return parser.parse_args()


def fmt_bytes(value: int | None) -> str:
    if not value:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def fmt_ts(value: int | None) -> str:
    if not value:
        return "never"
    if value > 10_000_000_000:
        value = value / 1000
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_ips(raw: str | None) -> list[str]:
    if not raw:
        return []
    raw = raw.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, dict):
            values: list[str] = []
            for item in parsed.values():
                if isinstance(item, list):
                    values.extend(str(value).strip() for value in item if str(value).strip())
                elif str(item).strip():
                    values.append(str(item).strip())
            return values
        if isinstance(parsed, str) and parsed.strip():
            return [parsed.strip()]
    except json.JSONDecodeError:
        pass

    normalized = raw.replace("\n", ",").replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def load_clients(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute("SELECT id, remark, port, settings FROM inbounds").fetchall()
    clients: dict[str, dict] = {}
    for inbound_id, remark, port, settings_raw in rows:
        if not settings_raw:
            continue
        settings = json.loads(settings_raw)
        for client in settings.get("clients", []):
            email = client.get("email")
            if not email:
                continue
            clients[email] = {
                "inbound_id": inbound_id,
                "inbound_remark": remark,
                "inbound_port": port,
                "comment": client.get("comment") or "",
                "email": email,
                "client_id": client.get("id") or "",
                "sub_id": client.get("subId") or "",
                "tg_id": str(client.get("tgId") or ""),
                "limit_ip": client.get("limitIp", 0),
                "enabled": bool(client.get("enable", True)),
                "created_at": client.get("created_at"),
                "updated_at": client.get("updated_at"),
            }
    return clients


def load_traffic(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        """
        SELECT inbound_id, email, enable, up, down, all_time, expiry_time, total, last_online
        FROM client_traffics
        """
    ).fetchall()
    result: dict[str, dict] = {}
    for inbound_id, email, enable, up, down, all_time, expiry_time, total, last_online in rows:
        result[email] = {
            "inbound_id": inbound_id,
            "enabled": bool(enable),
            "up": up or 0,
            "down": down or 0,
            "all_time": all_time or 0,
            "expiry_time": expiry_time or 0,
            "total": total or 0,
            "last_online": last_online or 0,
        }
    return result


def load_ips(conn: sqlite3.Connection) -> dict[str, list[str]]:
    rows = conn.execute("SELECT client_email, ips FROM inbound_client_ips").fetchall()
    return {email: parse_ips(raw) for email, raw in rows}


def build_status(limit_ip: int, ip_count: int, suspicious_threshold: int) -> str:
    if limit_ip and ip_count > limit_ip:
        return "LIMIT EXCEEDED"
    if ip_count >= suspicious_threshold:
        return "SUSPICIOUS"
    return "OK"


def timestamp_to_datetime(value: int | None) -> datetime | None:
    if not value:
        return None
    if value > 10_000_000_000:
        value = value / 1000
    return datetime.fromtimestamp(value, tz=timezone.utc)


def build_risk_flags(
    *,
    client: dict,
    traffic_info: dict,
    ip_count: int,
    status: str,
    high_traffic_bytes: int,
    new_user_days: int,
    new_user_heavy_bytes: int,
) -> list[str]:
    flags: list[str] = []
    total_traffic = traffic_info.get("all_time", 0) or 0
    created_at = timestamp_to_datetime(client.get("created_at"))
    now = datetime.now(timezone.utc)

    if status == "LIMIT EXCEEDED":
        flags.append("LIMIT_EXCEEDED")
    elif status == "SUSPICIOUS":
        flags.append("MULTI_IP")

    if total_traffic >= high_traffic_bytes:
        flags.append("HIGH_TRAFFIC")

    if created_at is not None:
        age_days = (now - created_at).total_seconds() / 86400
        if age_days <= new_user_days and total_traffic >= new_user_heavy_bytes:
            flags.append("NEW_BUT_HEAVY_USAGE")

    if client.get("limit_ip") == 1 and total_traffic >= new_user_heavy_bytes:
        flags.append("STRICT_LIMIT_USER")

    if not flags:
        flags.append("NORMAL")

    return flags


def main():
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    clients = load_clients(conn)
    traffic = load_traffic(conn)
    ips_map = load_ips(conn)
    conn.close()

    emails = sorted(clients)
    if args.email:
        emails = [email for email in emails if email == args.email]

    if not emails:
        raise SystemExit("No matching clients found.")

    high_traffic_bytes = int(args.high_traffic_gb * 1024 * 1024 * 1024)
    new_user_heavy_bytes = int(args.new_user_heavy_gb * 1024 * 1024 * 1024)

    if args.sort_by_traffic:
        emails = sorted(
            emails,
            key=lambda email: traffic.get(email, {}).get("all_time", 0),
            reverse=True,
        )

    for email in emails:
        client = clients[email]
        traffic_info = traffic.get(email, {})
        ips = ips_map.get(email, [])
        ip_count = len(ips)
        status = build_status(client["limit_ip"], ip_count, args.suspicious_ip_count)
        risk_flags = build_risk_flags(
            client=client,
            traffic_info=traffic_info,
            ip_count=ip_count,
            status=status,
            high_traffic_bytes=high_traffic_bytes,
            new_user_days=args.new_user_days,
            new_user_heavy_bytes=new_user_heavy_bytes,
        )

        if args.suspicious_only and risk_flags == ["NORMAL"]:
            continue

        if args.ips_only:
            print(
                f"{email} | tgId={client['tg_id'] or '-'} | limitIp={client['limit_ip']} | ipCount={ip_count} | traffic={fmt_bytes(traffic_info.get('all_time', 0))} | status={status} | risk={','.join(risk_flags)} | ips={', '.join(ips) if ips else '-'}"
            )
            continue

        print(f"User: {email}")
        print(f"Comment: {client['comment'] or '-'}")
        print(f"Telegram ID: {client['tg_id'] or '-'}")
        print(f"Client UUID: {client['client_id'] or '-'}")
        print(f"Subscription ID: {client['sub_id'] or '-'}")
        print(
            f"Inbound: {client['inbound_remark']} (id={client['inbound_id']}, port={client['inbound_port']})"
        )
        print(f"Enabled: {'yes' if client['enabled'] else 'no'}")
        print(f"limitIp: {client['limit_ip']}")
        print(f"Known IP count: {ip_count}")
        print(f"Known IPs: {', '.join(ips) if ips else '-'}")
        print(f"Traffic up: {fmt_bytes(traffic_info.get('up', 0))}")
        print(f"Traffic down: {fmt_bytes(traffic_info.get('down', 0))}")
        print(f"Traffic total: {fmt_bytes(traffic_info.get('all_time', 0))}")
        print(f"Last online: {fmt_ts(traffic_info.get('last_online', 0))}")
        print(f"Status: {status}")
        print(f"Risk flags: {', '.join(risk_flags)}")
        print("-" * 48)


if __name__ == "__main__":
    main()
