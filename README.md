# remote-wake

局域网 **双通道 Wake-on-LAN（网络唤醒）工具**：对同一台目标主机的 **有线（以太网）** 与 **无线（Wi-Fi）** 双物理链路同时并发发送魔术包，并多网卡轮询探活，实时反馈哪条通道率先就绪。

适合在家里/工作室有一台常驻关机或睡眠的高性能算力机、游戏机或开发机，通过局域网网关设备、手机 Telegram 机器人或 AI Agent 随时随地秒级远程开机。

---

## 💡 为什么需要「双通道」唤醒？

传统的网络唤醒工具通常只有一个 MAC 地址或单纯发送一次全网广播，在现代 Windows 11 + 高性能 Wi-Fi 7 / 2.5G/5G 有线主板环境下极易失败：

1. **Wi-Fi 睡眠路由器丢包**：现代 Wi-Fi 6/7 路由器为了节能，在无线客户端休眠时会直接丢弃 `255.255.255.255` 全局广播包。**必须配合定向单播（Unicast to IP）+ 多端口连续重发**，路由器才会将数据帧精确投递至待机的无线网卡。
2. **冷关机 vs 睡眠差异**：
   - **Wi-Fi**：仅支持在系统「睡眠（Sleep / S3 / S0ix）」状态下无线唤醒，彻底关机后无线模块断电断握手，无法冷开机。
   - **网线（以太网）**：支持在「彻底关机（Shutdown / S5）」状态下冷开机，只要插着网线，主板待机电路保持监听。
3. **双物理链路并发**：无论目标机当前是关机还是睡眠，是连着 Wi-Fi 还是插着网线，无需人工判断，一条指令双通道齐发，哪条链路通就从哪条链路秒级唤醒。

---

## 🚀 快速开始

### 1. 安装与配置

```bash
git clone https://github.com/<your-username>/remote-wake.git
cd remote-wake

# 创建本地配置文件（此文件已加入 .gitignore，不会泄露私密 MAC/IP）
mkdir -p ~/.config/remote-wake
cp config.example.json ~/.config/remote-wake/config.json
```

编辑 `~/.config/remote-wake/config.json` 填入目标机网卡信息：

```json
{
  "targets": [
    {
      "name": "有线网卡 (以太网)",
      "mac": "AA:BB:CC:DD:EE:01",
      "ip": "192.168.1.50"
    },
    {
      "name": "无线网卡 (Wi-Fi)",
      "mac": "AA:BB:CC:DD:EE:02",
      "ip": "192.168.1.51"
    }
  ],
  "broadcast_ips": [
    "192.168.1.255",
    "255.255.255.255"
  ],
  "ports": [9, 7, 12287],
  "poll_seconds": 15
}
```

### 2. 命令行调用

```bash
# 唤醒并轮询检测是否开机上线（默认 15 秒）
python3 remote_wake.py

# 只发唤醒包，不等待探活（秒级退出）
python3 remote_wake.py --quick

# 输出结构化 JSON（供脚本或上层服务调用）
python3 remote_wake.py --json
```

可选：将脚本加入系统 PATH：
```bash
ln -sf "$(pwd)/remote_wake.py" ~/.local/bin/remote-wake
```

---

## 🛠️ 目标主机配置指南（踩坑实录）

要让目标电脑能够被成功唤醒，需在 Windows 和主板 BIOS 中做一次性检查：

### 1. 有线网卡彻底关机（S5 冷开机）配置
- **关闭 Windows 快速启动（最重要）**：
  按 `Win + R` 输入 `powercfg.cpl` -> 左侧「选择电源按钮的功能」 -> 点击「更改当前不可用的设置」 -> **取消勾选「启用快速启动」**。（Windows 快速启动关机时会彻底卸载网卡驱动并断电）。
- **设备管理器网卡设置**：
  双击有线网卡 -> 「电源管理」勾选 **允许此设备唤醒计算机**；
  「高级」选项卡中将 **Wake on Magic Packet** 和 **Shutdown Wake-On-Lan（关机网络唤醒）** 设为 `Enabled`；将 **Energy Efficient Ethernet（节能以太网）** 设为 `Disabled`。
- **主板 BIOS 设置**：
  进 BIOS 将 **ErP / EuP Ready** 设为 `Disabled`（避免关机彻底切断所有待机电）；开启 **Wake Up By PCI-E Device** 或 **Resume By Onboard LAN**。关机后网口指示灯微亮即代表待机就绪。

### 2. Wi-Fi 无线睡眠唤醒（WoWLAN）配置
- **电脑使用习惯**：电脑不用时点击 **「睡眠（Sleep）」** 而非彻底关机。
- **网卡设置**：
  双击 Wi-Fi 网卡 -> 「电源管理」勾选 **允许此设备唤醒计算机**；
  「高级」选项卡中将 **Wake on Magic Packet** 与 **ARP Offload（ARP 卸载）** 设为 `Enabled`。

---

## 🤖 与 Telegram Bot / AI Agent 集成

可以将本工具作为网关常驻主机的本地技能，集成至 Telegram 机器人：

```python
import subprocess
import json

def handle_wake():
    res = subprocess.run(["remote-wake", "--json"], capture_output=True, text=True)
    data = json.loads(res.stdout)
    if data["status"] in ("WOKEN_UP", "ALREADY_ONLINE"):
        return f"🎉 唤醒成功！主机已就绪 ({data.get('alive_channel')})"
    return "📡 唤醒魔术包已通过双通道广播，正在等待主机响应..."
```

---

## 📄 License

[MIT License](LICENSE)
