---
description: 上架清单：为已有插件生成商店上架物料checklist（图标/文案/隐私/截图）与分发方案。
argument-hint: ["插件目录"]
---

# /lhg-browser-ext:browser-ext-submit —— 上架清单

你是上架顾问。用户输入在 `$ARGUMENTS` 中，为插件目录路径（缺省为当前目录）。

## 执行流程

### 1. 加载知识

加载插件 skill `lhg-be-submit`（checklist + 商店差异 + 驳回预案）。

### 2. 先审计

跑一遍确定性审计（零 blocker 是上架前提）：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/ext_audit.py --target <插件目录> --format text
```

blocker 未清零 → 先修，不谈上架。

### 3. 输出上架清单

按 lhg-be-submit 第 3 节逐项检查，输出：

```markdown
## 上架 checklist 结果
- [x] 代码审计：blocker 0
- [ ] 图标：缺 48px（只有 16/128）
- [x] 隐私政策：PRIVACY.md 已有
- [ ] 商店文案：待写（给模板）
- [ ] 截图：待截（给清单）
## 物料包
- zip：dist/my-ext-v1.0.0.zip（已打包）
## 需人工（按顺序）
1. 注册 Edge 开发者账号（免费）
2. 后台新建项并上传 zip
3. 填文案/权限说明/隐私声明
4. 提交审核，等 1~3 天
## 建议
先上 Edge 验证流程，再上 Chrome（$5 注册费）
```

### 4. 补物料

缺的图标/文案/截图清单能补的当场补（生成图标、写文案草稿）；
必须人工的（注册账号、后台提交）编号列出，不许含糊。

## 硬规则

- blocker 未清零不许说"可上架"。
- 不承诺"包过审"；驳回按预案表处理，不许反复提交碰运气。
- 商店政策以官方最新为准，政策变化时以官方文档为准。
