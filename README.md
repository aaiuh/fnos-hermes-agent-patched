# Hermes Agent for fnOS（fork，含反代与 PWA 补丁集）

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Platform: fnOS](https://img.shields.io/badge/Platform-fnOS-green.svg)]()
[![Arch: x86_64 | arm64](https://img.shields.io/badge/Arch-x86__64%20%7C%20arm64-orange.svg)]()

[iranee/fnos-hermes-agent](https://github.com/iranee/fnos-hermes-agent) 的 fork。在本体功能（官方 WebApp 对话、多渠道接入、飞牛应用中心 fpk 部署）之上，叠加了一个小补丁集，并自动跟随上游：

- **反向代理子路径部署**：WebApp 外壳支持在网关反代（带 `X-Forwarded-Prefix` 的子路径）后面运行，登录跳转保留前缀；飞牛面板「打开 WebApp」入口在登录门（gated）模式下同样可用。
- **PWA 安装**：内置 manifest 与图标，登录门对 manifest/图标匿名放行（Chrome 安装判定不带 cookie 抓取，这是 gated 部署下 PWA 可安装的关键），浏览器可将 WebApp 安装为独立应用。
- **自动跟随上游**：每日工作流检查官方 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) 稳定版 tag，出新版自动 bump 应用版本、重放补丁集并重新出包；上游改动与补丁冲突时构建自动失败报警，不会静默丢补丁。

补丁集内容见 `patches/`（内核白名单快照 + PWA 资产）与 `scripts/apply-fork-patches.py`（在 `prepare-runtime` 发布后的源码树上重放并同步回执清单）。外壳层的反代改动直接在 `app/server`、`app/ui` 源码中。

## 与上游的差异

| 位置 | 改动 |
|---|---|
| `app/server/webapp-control.py` | 反代子路径下的 WebApp 配置解锁 |
| `app/server/webapp-runtime.js` | 健康探测接受 302 登录跳转；面板 launch 返回登录页地址 |
| `app/ui/index.html` | 面板内嵌 iframe 对登录页撤占位层 |
| `patches/core/`（构建时注入） | 官方内核 `middleware.py`/`web_server_static_assets.py` 白名单：`/manifest.webmanifest`、`/icon-192.png`、`/icon-512.png` 匿名放行 |
| `patches/pwa/`（构建时注入） | manifest + 图标 + `index.html` manifest link |
| `scripts/` + `.github/workflows/` | 补丁重放与每日自动跟随 |

其余内容（安装步骤、目录结构、进程架构、端口说明等）与上游一致，见上游 README。

## 版本

版本号沿用上游格式 `<内核版本>-<序号>`。fork 序号从 09 起（与上游 08 区分）。

## 免责声明

本仓库仅作为服务集成工具的分发渠道，不对 Hermes Agent 软件本身的安全性、稳定性作任何保证。使用过程中产生的所有风险由用户自行承担。上游原作者为 [iranee](https://github.com/iranee)，官方内核来自 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)。
