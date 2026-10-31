#!/usr/bin/env python3
"""Dual-path Wake-on-LAN: blast magic packets on every configured NIC, then poll until up."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_PORTS = (9, 7, 12287)
DEFAULT_BROADCASTS = ("255.255.255.255",)
DEFAULT_POLL_SECONDS = 15


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit(
                "YAML config needs PyYAML (`pip install pyyaml`), or use config.example.json"
            ) from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict) or "targets" not in data:
        raise SystemExit(f"config must be an object with a targets list: {path}")
    return data


def send_magic_packet(
    mac_address: str,
    *,
    broadcast_ips: list[str],
    ports: list[int],
    unicast_ip: str | None = None,
    repeats: int = 3,
) -> None:
    clean_mac = mac_address.replace(":", "").replace("-", "").upper()
    if len(clean_mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac_address}")

    packet = bytes.fromhex("FF" * 6 + clean_mac * 16)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    destinations = list(broadcast_ips)
    if unicast_ip:
        destinations.append(unicast_ip)

    try:
        for _ in range(repeats):
            for dst in destinations:
                for port in ports:
                    try:
                        sock.sendto(packet, (dst, port))
                    except OSError:
                        pass
            time.sleep(0.05)
    finally:
        sock.close()


def is_host_alive(ip: str, timeout_sec: int = 1) -> bool:
    res = subprocess.run(
        ["ping", "-c", "1", "-W", str(timeout_sec), ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return res.returncode == 0


def first_alive(targets: list[dict[str, Any]]) -> dict[str, Any] | None:
    for t in targets:
        ip = t.get("ip")
        if ip and is_host_alive(str(ip), timeout_sec=1):
            return t
    return None


def wake(
    targets: list[dict[str, Any]],
    *,
    broadcast_ips: list[str],
    ports: list[int],
    poll_seconds: int,
    check_online: bool,
) -> dict[str, Any]:
    alive = first_alive(targets)

    for t in targets:
        send_magic_packet(
            str(t["mac"]),
            broadcast_ips=broadcast_ips,
            ports=ports,
            unicast_ip=str(t["ip"]) if t.get("ip") else None,
        )
        time.sleep(0.05)

    if alive:
        return {
            "status": "ALREADY_ONLINE",
            "message": (
                f"target already online via {alive.get('name', 'nic')} "
                f"({alive.get('ip')}); magic packets still sent on all paths"
            ),
            "target": alive,
        }

    lines = []
    for t in targets:
        lines.append(f"• {t.get('name', 'nic')}: {t['mac']}" + (f" ({t['ip']})" if t.get("ip") else ""))

    if not check_online:
        return {
            "status": "SENT",
            "message": "magic packets sent on all configured paths:\n" + "\n".join(lines),
        }

    online = None
    start = time.time()
    for _ in range(max(poll_seconds, 1)):
        time.sleep(1)
        online = first_alive(targets)
        if online:
            break

    elapsed = int(time.time() - start)
    if online:
        return {
            "status": "WOKEN_UP",
            "message": (
                f"wake ok in {elapsed}s via {online.get('name', 'nic')} "
                f"({online.get('ip')})"
            ),
            "target": online,
            "elapsed_seconds": elapsed,
        }

    return {
        "status": "SENT_PENDING",
        "message": (
            "magic packets sent, but no ping reply yet:\n"
            + "\n".join(lines)
            + "\n\nIf cold-boot WoL fails, enable PCIe wake in BIOS and disable ErP."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dual-path Wake-on-LAN helper")
    p.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path.home() / ".config" / "remote-wake" / "config.json",
        help="JSON (or YAML) config path",
    )
    p.add_argument("--quick", action="store_true", help="send only, skip online poll")
    p.add_argument("--json", action="store_true", help="print result as JSON")
    args = p.parse_args(argv)

    if not args.config.is_file():
        example = Path(__file__).resolve().parent / "config.example.json"
        print(
            f"missing config: {args.config}\n"
            f"copy {example} to that path and fill in your MACs/IPs",
            file=sys.stderr,
        )
        return 2

    cfg = load_config(args.config)
    targets = cfg["targets"]
    if not targets:
        raise SystemExit("config.targets is empty")

    broadcasts = list(cfg.get("broadcast_ips") or DEFAULT_BROADCASTS)
    # Also derive subnet broadcasts from target IPs when present
    for t in targets:
        ip = t.get("ip")
        if not ip:
            continue
        parts = str(ip).split(".")
        if len(parts) == 4 and all(x.isdigit() for x in parts):
            b = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
            if b not in broadcasts:
                broadcasts.append(b)

    ports = [int(x) for x in (cfg.get("ports") or DEFAULT_PORTS)]
    poll_seconds = int(cfg.get("poll_seconds") or DEFAULT_POLL_SECONDS)

    result = wake(
        targets,
        broadcast_ips=broadcasts,
        ports=ports,
        poll_seconds=poll_seconds,
        check_online=not args.quick,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
    return 0 if result["status"] in {"ALREADY_ONLINE", "WOKEN_UP", "SENT"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
