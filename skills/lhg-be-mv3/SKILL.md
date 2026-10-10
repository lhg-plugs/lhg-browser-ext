---
name: lhg-be-mv3
description: MV3开发规范：manifest字段、service worker、permissions最小化、content script匹配、action/popup、storage、消息通信。写插件代码前加载。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-be-mv3：MV3 开发规范

> 目标：生成的插件"一次写对"——manifest 合规、无 MV2 残留、权限最小、
> service worker 不踩 DOM 坑。规范要点基于 Chrome 扩展公开文档的公开知识
> （未复制原文），实现细节为原创总结。

## 1. 何时使用

- 生成/修改浏览器插件代码时 → 加载本 skill
- 审计报 BE-MV2/BE-PERM/BE-SW/BE-CSP 类问题时 → 按对应章节修复
- 用户问"为什么插件不工作/后台脚本没反应"时 → 按第 5 节排查

## 2. 输入与输出

- **输入**：lhg-be-plan 输出的功能范围说明书（功能拆分 + 权限清单已定）
- **输出**：插件目录（manifest.json + 引用的 js/html/css/图标文件）
- **硬约束**：manifest_version 必须为 3；Chrome/Edge 通用（Firefox 需单独适配，见 lhg-be-submit）

## 3. 目录结构（约定）

```
my-ext/
├── manifest.json          # 清单：版本/权限/入口声明（唯一必需文件）
├── sw.js                  # service worker：后台逻辑（按需）
├── content.js             # content script：注入页面的脚本（按需）
├── popup.html / popup.js  # 弹窗界面（按需）
├── options.html           # 选项页（按需）
├── icons/                 # 图标：16/32/48/128（128 必需，见上架）
├── PRIVACY.md             # 隐私政策（申请敏感权限时必需）
└── PERMISSIONS.md         # 权限说明（权限>2 个时建议）
```

## 4. manifest.json 规范

```json
{
  "manifest_version": 3,
  "name": "插件名",
  "description": "一句话功能",
  "version": "1.0.0",
  "permissions": ["storage", "activeTab"],
  "host_permissions": ["https://api.example.com/*"],
  "background": { "service_worker": "sw.js" },
  "action": { "default_popup": "popup.html", "default_title": "插件名" },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  },
  "content_scripts": [
    { "matches": ["https://example.com/*"], "js": ["content.js"] }
  ]
}
```

铁律：
- **permissions vs host_permissions**：`permissions` 放 chrome.* 能力（storage/tabs/alarms），
  `host_permissions` 放网址（跨站 fetch 才需要）。混放是新手最常见的错。
- **权限最小化**：能用 activeTab 不用 tabs；能写具体域名不写 `<all_urls>`；
  每多一个权限，上架审核多一分被拒风险（BE-PERM-001/002）。
- **content_scripts.matches 能窄不宽**：只在目标网站注入；全站注入要写理由。
- **MV2 残留零容忍**：browser_action/page_action/background.scripts/background.persistent
  出现即 blocker（BE-MV2-002）——复制网上的老教程最容易中招。
- **CSP**：不许自定义放宽（unsafe-eval/unsafe-inline 即 blocker，BE-CSP-001）；
  远程代码加载在 MV3 下被禁止，更新走商店发版。

## 5. service worker（后台脚本，最容易踩坑）

```js
// sw.js：事件驱动，无 DOM，无常驻
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ on: true });
});
// 定时任务：用 alarms，不许 setInterval（SW 会被休眠，interval 丢任务）
chrome.alarms.create("tick", { periodInMinutes: 60 });
chrome.alarms.onAlarm.addListener((alarm) => { /* ... */ });
```

铁律：
- **无 DOM 环境**：service worker 里用 `document`/`window` 必报错（BE-SW-001）；
  需要 DOM 操作的一律放 content script。
- **会被休眠**：5 分钟无事件即休眠；全局变量不可靠，状态一律走 chrome.storage。
- **不许 setInterval 做定时**：用 chrome.alarms（需声明 alarms 权限）。
- **调试**：在 `chrome://extensions` 开开发者模式 → 点"service worker"看日志；
  "后台没反应"先查是不是被休眠了，再查 manifest 的 background 声明。

## 6. content script（页面注入脚本）

```js
// content.js：运行在页面上下文，可操作 DOM，但与页面 JS 隔离
(function () {
  "use strict";
  // 只做最小注入：监听/改 DOM/发消息；重逻辑放 service worker
  document.addEventListener("mouseup", () => {
    const text = window.getSelection().toString().trim();
    if (text) chrome.runtime.sendMessage({ type: "select", text });
  });
})();
```

铁律：
- **与页面 JS 环境隔离**：页面定义的全局变量你读不到，反之亦然；
  需要交互时用 `window.postMessage` 或 DOM 事件桥接。
- **注入时机**：默认 document_idle；需要更早用 `"run_at": "document_start"`。
- **样式隔离**：注入的浮层用 Shadow DOM 或带前缀的类名，避免被页面 CSS 污染。
- **性能**：content script 在每个匹配页面都跑一遍，重逻辑节制，
  matches 范围越小越好。

## 7. 组件通信（三件套关系）

```
popup ←→ service worker：chrome.runtime.sendMessage / onMessage
content script ←→ service worker：同上（content 不能直调 chrome.tabs 等受限 API）
content script → 页面：DOM 操作 / postMessage
service worker → 外部：fetch（需 host_permissions 声明域名）
```

- popup 关闭即销毁：状态放 storage，不放 popup 的内存变量。
- 发消息要处理"对方不存在"：service worker 休眠时首条消息可能丢，
  重要操作加重试或用 chrome.storage 做信箱。

## 8. 数据存储

- `chrome.storage.local`：本地设置/缓存（5MB+，够用）。
- `chrome.storage.sync`：跨设备同步（100KB 上限，只放小配置）。
- 敏感数据不许明文存（如 token 尽量走 chrome.identity 的 OAuth 流程）。

## 9. 反模式

- ❌ 抄 MV2 老教程：browser_action/background.persistent 照抄 → BE-MV2-002
- ❌ 权限大礼包：tabs + `<all_urls>` 开局 → 审核被拒三连
- ❌ SW 里操作 DOM：`document.querySelector` 写进 sw.js → 运行时报错
- ❌ setInterval 定时：SW 休眠后任务丢失 → 用 alarms
- ❌ popup 里存状态：弹窗一关数据全丢 → 状态走 storage
- ❌ innerHTML 拼用户输入：XSS 面 → 用 textContent（BE-SEC-002）
- ❌ eval 解析数据：CSP 拦截 + 注入风险 → 用 JSON.parse（BE-SEC-001）

## 10. 自检与反馈

**质检门**（代码交付前）：
- [ ] manifest_version 为 3，无 MV2 残留字段
- [ ] 权限清单与 lhg-be-plan 一致，逐条有用途
- [ ] 引用的文件全部存在（sw.js/content.js/popup/icons）
- [ ] 图标含 128px 且文件存在
- [ ] 跑 `python3 scripts/audit/ext_audit.py --target <插件目录>` 零 blocker

**标准冒烟用例**：用 fixtures/be-good 跑审计 → 应零 blocker 零 warning。

**一键反馈**：规范覆盖不了的 API 坑（如某 chrome.* API 行为异常），以
`[QC] <API 名+现象>` 为标题提交到 https://github.com/lhg-plugs/lhg-browser-ext/issues，
正文写清"复现步骤 → 实际表现 → 期望表现"。

## 11. 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
