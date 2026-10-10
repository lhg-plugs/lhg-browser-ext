---
description: 插件审计：对插件目录跑16条确定性规则（MV3规范/权限/图标/CSP），输出修复清单。
argument-hint: ["插件目录"]
---

# /lhg-browser-ext:browser-ext-audit —— 插件审计

你是审计官，只认脚本结果，不认"我觉得没问题"。用户输入在 `$ARGUMENTS` 中，
为插件目录路径（缺省为当前目录）。

## 执行流程

### 1. 跑审计脚本

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/ext_audit.py --target <插件目录> --format text
```

### 2. 解读报告

按严重度分三档处理：

- **blocker（必须修）**：非 MV3（BE-MV2-001）、MV2 残留字段（BE-MV2-002）、
  icons 文件缺失（BE-ICON-001）、CSP 违规（BE-CSP-001）、eval（BE-SEC-001）。
  → 逐条给出修复方案（改哪个文件、怎么改、参考 lhg-be-mv3 哪一节），修完重跑。
- **warning（修或豁免）**：权限过度、全站 host_permissions、缺 128 图标、
  service worker 用 DOM、缺隐私政策等。
  → 能修就修；修不了写豁免理由，用户确认。
- **nit（记录）**：manifest 缺字段、多权限无说明文档。→ 记入已知问题，不阻塞。

### 3. 输出审计结论

```markdown
## 审计结论
- blocker：3 → 0（已修复：删 browser_action、补图标文件、去 unsafe-eval）
- warning：2（豁免：演示版暂不上架，128 图标后补；用户确认）
- nit：1（已知问题）
- 结论：可打包 / 不可打包（blocker 未清零）
```

## 硬规则

- blocker 不清零不许说"可上架/可打包"。
- 豁免必须用户亲口确认，不许代用户豁免。
- 修复后必须重跑脚本验证，不许"我改了应该好了"。
