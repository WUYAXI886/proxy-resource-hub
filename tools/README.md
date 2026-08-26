# 工具说明

本目录存放与代理IP相关的开源小工具，全部基于标准库实现，无需额外安装依赖。

## socks5_checker.py

一个轻量级的 SOCKS5 代理连通性检测脚本，用于快速验证代理是否可用、测量连接延迟并查看出口 IP。

### 功能

- 完整实现 RFC 1928 SOCKS5 握手
- 支持无认证和用户名/密码认证
- 通过代理请求远程接口，输出出口 IP
- 零第三方依赖，Python 3.8+ 即可运行

### 用法

```bash
# 基础检测
python socks5_checker.py --host 127.0.0.1 --port 1080

# 带认证
python socks5_checker.py --host 127.0.0.1 --port 1080 --user myuser --pass mypass

# 指定目标检测接口
python socks5_checker.py --host 127.0.0.1 --port 1080 \
  --target https://httpbin.org/ip

# 输出 JSON 供脚本调用
python socks5_checker.py --host 127.0.0.1 --port 1080 --json
```

### 输出示例

```json
{
  "proxy": "127.0.0.1:1080",
  "auth": false,
  "target": "https://socks5ip.com.cn/wp-json/ip-quality/v1/detect",
  "success": true,
  "connect_latency_ms": 45.21,
  "total_latency_ms": 312.55,
  "exit_ip": "203.0.113.45",
  "target_response": {
    "ip": "203.0.113.45",
    "success": true
  }
}
```

### 在线检测

如果你暂时没有本地代理，也可以直接访问在线工具：

- [IP 质量检测](https://socks5ip.com.cn/ip-check)
- [代理线路检测](https://socks5ip.com.cn/proxy-check)
