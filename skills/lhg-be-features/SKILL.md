---
name: lhg-be-features
description: 浏览器插件常见功能脚手架：划词翻译/去广告/快捷键/页面增强四类，每类给架构要点与最小实现路径。选功能时加载。
license: MIT
compatibility: 适用于任何支持 Markdown 指令的 AI 编程助手（Claude Code、豆包、Workbuddy 等）
metadata:
  version: 1.0.0
  author: 刘洪光
---

# lhg-be-features：常见功能脚手架

> 目标：80% 的小白插件需求落在四类功能里——按脚手架抄架构，
> 只填业务逻辑，不重复踩坑。本 skill 的四类脚手架为本插件原创整理。

## 1. 何时使用

- 功能范围说明书里出现以下四类功能时 → 按对应脚手架实现
- 用户说"想要个 X 功能"但说不清怎么做时 → 用脚手架反推实现路径
- 不在四类里 → 回 lhg-be-plan 重新做边界判定，不要硬套

## 2. 输入与输出

- **输入**：功能名称 + 功能范围说明书
- **输出**：该功能的架构要点（用哪几个组件、关键 API、权限清单）
- **不输出**：完整业务代码（脚手架给骨架，业务逻辑现场写）

## 3. 脚手架 A：划词翻译/取词

**架构**：content script（取词+浮层） + service worker（调 API） + popup（设置）

| 要点 | 做法 |
|---|---|
| 取词 | content script 监听 `mouseup`/`selectionchange`，`window.getSelection()` 取文本 |
| 浮层 | Shadow DOM 隔离样式，定位在选中词附近；点空白处关闭 |
| 查词 | 发消息给 service worker，由 SW 调词典 API（content 直接 fetch 会受页面 CSP 影响） |
| API 选择 | 优先免费无 key 的词典 API；需 key 的走 popup 设置页让用户自己填 |
| 权限 | activeTab（取词）+ storage（设置）+ host_permissions（词典域名） |
| 坑 | PDF/图片选词做不了（提前告知，见 lhg-be-plan）；长文本截断前 500 字符 |

## 4. 脚手架 B：去广告/页面净化

**架构**：content script（删 DOM） + declarativeNetRequest（拦请求），二选一或组合

| 要点 | 做法 |
|---|---|
| 元素级 | content script 按选择器删/藏元素（如 `.ad-banner`）；用 MutationObserver 处理后加载的广告 |
| 请求级 | declarativeNetRequest 按规则拦截广告域名（需 declarativeNetRequest 权限 + 规则文件） |
| 规则维护 | 广告选择器放 storage，popup 提供"自定义规则"入口，用户可自行加 |
| 权限 | 目标站点的 matches + declarativeNetRequest（请求级才需要） |
| 坑 | **法律与道德**：只做"用户主动开启的个人净化"，不做分发牟利；部分站点反制频繁，规则要可更新 |
| 红线 | 不要碰视频网站的贴片广告商业逻辑做收费"去广告"产品——版权风险自负 |

## 5. 脚手架 C：快捷键效率工具

**架构**：commands API + service worker（执行）+ popup（快捷键说明）

| 要点 | 做法 |
|---|---|
| 声明 | manifest 的 `commands` 字段声明快捷键（如 Ctrl+Shift+K） |
| 执行 | service worker 监听 `chrome.commands.onCommand`，调 chrome.tabs/scripting 执行 |
| 可配置 | 用户可在 `chrome://extensions/shortcuts` 自行改键，插件内给说明即可 |
| 权限 | activeTab（操作当前页）+ scripting（注入执行） |
| 坑 | 快捷键可能与网站/其他插件冲突，默认键选冷僻组合；Mac/Win 差异在文档注明 |

## 6. 脚手架 D：页面增强（夜间模式/划线/备注）

**架构**：content script（改样式/加 DOM） + storage（存用户数据）+ popup（开关）

| 要点 | 做法 |
|---|---|
| 样式增强 | content script 注入 CSS（如夜间模式滤镜）；用类名开关，避免直接改 style 属性打架 |
| 数据增强 | 划线/备注存 storage，按 URL 做 key；页面加载时读出来还原 |
| 开关 | popup 放总开关 + 站点白名单；content script 先读开关再干活 |
| 权限 | activeTab 或具体站点 matches + storage |
| 坑 | SPA 页面（无刷新跳转）要用 MutationObserver 或 webNavigation 监听 URL 变化重跑初始化 |

## 7. 脚手架选择速查

| 用户说 | 脚手架 | 核心组件 |
|---|---|---|
| 划词/取词/翻译 | A | content + SW + popup |
| 去广告/屏蔽元素 | B | content / DNR |
| 快捷键/一键操作 | C | commands + SW |
| 夜间模式/备注/美化 | D | content + storage |
| 多个都要 | 先做一个 | 一次只落地一个脚手架，跑通再加 |

### 7.5 脚手架组合模式

一个插件长大后往往需要组合脚手架。组合原则：

- **一次加一个**：v1.0 只落地一个脚手架，跑通后再加第二个。
- **共享底座**：多个脚手架共用 service worker 时，消息类型加命名空间
  （如 `{type: "dict:query"}` vs `{type: "note:save"}`），避免互相踩。
- **popup 分区**：多功能 popup 按 Tab/分组组织，不要把所有开关堆在一起。
- **权限叠加检查**：加第二个脚手架时重跑权限最小化流程（lhg-be-plan 5.5），
  新增权限同样需要用途说明。

### 7.6 调试技巧

| 问题 | 查哪里 |
|---|---|
| content script 没跑 | manifest 的 matches 是否覆盖当前 URL；`chrome://extensions` 看是否报错 |
| service worker 没反应 | 点"service worker"看日志；是否被休眠；onMessage 是否 return true 保持通道 |
| popup 空白 | popup.html 的 script 是否被 CSP 拦（内联 script 在 MV3 下默认不允许，写外部 js 文件） |
| 权限弹窗没出现 | host_permissions 是安装时申请，permissions 增量需调 chrome.permissions.request |
| 跨域 fetch 失败 | host_permissions 是否声明了该域名；看 SW 控制台的网络错误 |

**注意**：MV3 的 popup 页面 CSP 禁止内联 `<script>`，所有逻辑必须写外部 js 文件
并用 `src` 引用——这是新手最高频的"为什么空白"原因。

### 7.7 脚手架自查清单

选定脚手架后、写代码前，对着打勾：

- [ ] 组件清单已列出（content/SW/popup 按需取舍，不多不少）
- [ ] 关键 API 已确认在 MV3 下可用（不确定的先查官方文档）
- [ ] 权限清单已输出，且通过了 lhg-be-plan 5.5 的最小化流程
- [ ] 该脚手架的"坑"已读过一遍，知道怎么避

## 8. 反模式

- ❌ 脚手架硬套：做"定时提醒"非要用划词脚手架 → 回 lhg-be-plan 重做边界判定
- ❌ content script 大包大揽：把 API 调用、 heavy 计算全放 content → 页面变卡，且受页面 CSP 限制
- ❌ 浮层样式污染：不用 Shadow DOM，浮层被页面 CSS 带偏 → 用户以为插件坏了
- ❌ 规则写死：去广告选择器写死在代码里 → 网站一改版就失效，规则要可配置
- ❌ 忽视 SPA：只在 load 时初始化 → 单页应用内跳转后功能失效

## 9. 自检与反馈

**质检门**：
- [ ] 脚手架已选定，且与功能范围说明书一致
- [ ] 架构要点已输出（组件 + 关键 API + 权限清单）
- [ ] 该脚手架的"坑"已告知用户
- [ ] 一次只落地一个脚手架

**标准冒烟用例**：输入"划词翻译" → 应匹配脚手架 A，输出含 content+SW+popup
三组件与 activeTab/storage 权限。

**一键反馈**：四类覆盖不了的高频功能，以 `[QC] <功能一句话>` 为标题提交到
https://github.com/lhg-plugs/lhg-browser-ext/issues，正文写清"功能描述 →
期望的脚手架 → 现有四类为什么不够"。

## 10. 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
