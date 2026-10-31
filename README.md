# remote-wake

局域网 **双通道 Wake-on-LAN**：对同一台机器的有线 / 无线网卡同时打魔术包，再 ping 轮询，看哪条通道先醒。

适合「家里有一台常关机的算力机 / 游戏机」，用手机、Telegram、或桌面 Agent（Grok Bot 等）远程叫醒。

## 为什么是双通道

很多主板冷关机后，有线网卡 WOL 开着、Wi‑Fi 却睡死了；或者反过来。两条物理链路一起广播，成功率更高。

实测（同机房局域网）：一条命令发出去后，约 **5 秒** 内有网卡回 ping。

## 快速开始

```bash
git clone https://github.com/<you>/remote-wake.git
cd remote-wake
mkdir -p ~/.config/remote-wake
cp config.example.json ~/.config/remote-wake/config.json
# 填真实 MAC / 局域网 IP（不要把这份文件提交到 git）
python3 remote_wake.py
```

只发包、不等在线：

```bash
python3 remote_wake.py --quick
```

机器可读结果：

```bash
python3 remote_wake.py --json
```

可选：把脚本链到 PATH：

```bash
ln -sf "$(pwd)/remote_wake.py" ~/.local/bin/remote-wake
```

## 配置

`~/.config/remote-wake/config.json`（也支持 YAML，需 `pip install pyyaml`）：

| 字段 | 含义 |
|------|------|
| `targets` | 同一主机的多块网卡：`name` / `mac` / 可选 `ip`（用于探测与单播） |
| `broadcast_ips` | 广播地址；缺省含 `255.255.255.255`，并会按目标 IP 推导 `x.y.z.255` |
| `ports` | 默认 `9` / `7` / `12287` |
| `poll_seconds` | 发送后轮询秒数，默认 15 |

## 和 Bot 一起用

本机 Agent（例如 Grok Bot）只要有 Shell 权限，你对它说「唤醒」即可：

1. Bot 在常开的网关机 / 工作站上执行 `remote-wake`
2. 魔术包从局域网打到目标机（无需公网暴露目标机）
3. Bot 把「几秒内哪条通道先回」回报给你

目标机需：主板 BIOS 开 WOL / PCIe 唤醒，关 ErP；系统侧网卡允许魔术包唤醒。

## License

MIT
