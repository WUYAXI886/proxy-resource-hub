# 代理IP资源与检测工具库

> 面向跨境电商、社媒运营、数据采集等场景的开源代理IP工具与资源导航。  
> 由 [全网低价IP](https://socks5ip.com.cn) 维护。

## 这是什么项目

这个仓库汇集两类内容：

1. **实用工具** —— 可独立运行的代理检测脚本（零依赖、开箱即用）。
2. **资源导航** —— 整理主流代理IP平台、配置教程与检测入口，方便快速选型。

## 快速开始

### SOCKS5 代理可用性检测

```bash
python tools/socks5_checker.py \
  --host 127.0.0.1 \
  --port 1080 \
  --user username \
  --pass password \
  --target https://socks5ip.com.cn/wp-json/ip-quality/v1/detect
```

支持：

- 纯标准库实现，无需第三方依赖
- 检测 SOCKS5 握手、连接延迟、出口 IP
- 输出 JSON，方便集成到自动化流程
- 支持用户名/密码认证

详见 [`tools/README.md`](tools/README.md)。

## 在线资源

- [IP 质量检测](https://socks5ip.com.cn/ip-check)
- [代理线路检测](https://socks5ip.com.cn/proxy-check)
- [代理工具与教程中心](https://socks5ip.com.cn/dailigongjuzhongxin)

## 相关仓库

- [residential-ip-guide-cn](https://github.com/socks5ip/residential-ip-guide-cn) — 住宅 IP 与静态 IP 选型和接入指南
- [ip-zhishi-base](https://github.com/socks5ip/ip-zhishi-base) — IP 网络基础知识库

## 贡献与授权

欢迎提交 Issue 或 PR。工具代码以 MIT 协议发布。
