<!-- About 简介（推送后填写到仓库 About 栏）：
小白一句话→浏览器插件：想法澄清、MV3规范代码生成、权限最小化、上架checklist脚本化检测，Chrome/Edge通用。 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-browser-ext
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, browser-extension, chrome-extension, manifest-v3, mv3, chrome-web-store -->

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="lhg-browser-ext — 小白一句话→浏览器插件">
</p>

> **一句话介绍**：小白一句话→浏览器插件：想法澄清、MV3规范代码生成、权限最小化、上架checklist脚本化检测，Chrome/Edge通用。

**一键安装**：在 Claude Code 里运行

```bash
/plugin marketplace add lhg-plugs/lhg-browser-ext
/plugin install lhg-browser-ext@lhg-plugs
```

## 它能帮你做出什么

- **冒烟全绿**：`python3 smoke_test.py` 49 项全部通过（JSON 合法、frontmatter 完整、命令/skill/agent 齐全）。

## 它是什么

`lhg-browser-ext` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`browser-ext` 一句话想法 → 浏览器插件、`browser-ext-audit` 插件审计、`browser-ext-scaffold` 功能脚手架查询、`browser-ext-submit` 上架清单
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：lhg-be-features, lhg-be-mv3, lhg-be-plan, lhg-be-submit
- **2 个专家 agent**：be-auditor, be-builder
- **2 个 hooks**（`hooks/`：post_write_warn.py, pre_commit_audit.py），关键操作前自动把关

## 为什么是它

不是一个 prompt，而是一套互相兜底的机制：

1. **硬门，不是提醒**：hooks 在关键操作前自动拦截或警告（见 `hooks/`），而不是只在文档里写一句"请注意"。
2. **方法论沉淀在 skill 里**：流程、检查清单、口径都写在 `skills/` 的方法论里，命令只是入口；换个 agent 平台也能复用同一套做法。
3. **可验，不是可信**：`fixtures/` 备有坏/好对照用例，`smoke_test.py` 一键验证，规则有没有生效、自己跑一遍就知道。

## 快速上手

```bash
# 1. 安装（Claude Code 里运行）
/plugin marketplace add lhg-plugs/lhg-browser-ext
/plugin install lhg-browser-ext@lhg-plugs

# 2. 一句话想法 → 浏览器插件：功能范围界定、MV3代码生成、权限最小化、上架che
/lhg-browser-ext:browser-ext
```

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-browser-ext:browser-ext` | 一句话想法 → 浏览器插件：功能范围界定、MV3代码生成、权限最小化、上架checklist，一条龙交付。 | `/lhg-browser-ext:browser-ext` |
| `/lhg-browser-ext:browser-ext-audit` | 插件审计：对插件目录跑16条确定性规则（MV3规范/权限/图标/CSP），输出修复清单。 | `/lhg-browser-ext:browser-ext-audit` |
| `/lhg-browser-ext:browser-ext-scaffold` | 功能脚手架查询：输入想要的功能，匹配划词/去广告/快捷键/页面增强脚手架并输出架构要点。 | `/lhg-browser-ext:browser-ext-scaffold` |
| `/lhg-browser-ext:browser-ext-submit` | 上架清单：为已有插件生成商店上架物料checklist（图标/文案/隐私/截图）与分发方案。 | `/lhg-browser-ext:browser-ext-submit` |

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你需要一句话想法 → 浏览器插件时 → 用 `/lhg-browser-ext:browser-ext`
- 你需要插件审计时 → 用 `/lhg-browser-ext:browser-ext-audit`
- 你需要功能脚手架查询时 → 用 `/lhg-browser-ext:browser-ext-scaffold`

**什么时候不用：**

- 你只需要其中一个零散能力时 → 本插件是成套流程，单点需求用更轻量的 skill 更合适
- 你希望 AI 完全自由发挥、不接受任何自查与硬门时 → 它的规则审计与 hooks 会介入（可关，但那就别装它）
- 你的场景不在上面命令表覆盖范围内时 → 先看命令表，没有对应命令就别硬套

## 目录结构

```
lhg-browser-ext/
├── smoke_test.py          # 一键冒烟测试
├── ATTRIBUTION.md         # 灵感来源与许可声明
├── LICENSE                # MIT
├── README.md              # 本文件
├── .claude-plugin/
├── agents/
├── commands/
├── fixtures/
├── hooks/
├── scripts/
├── skills/
```

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（本次实测 49 项全部通过）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-browser-ext/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

同门插件见 [lhg-plugs](https://github.com/lhg-plugs)，86 个插件的完整矩阵在 [marketplace](https://github.com/lhg-plugs/marketplace) 维护。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
