---
description: 功能脚手架查询：输入想要的功能，匹配划词/去广告/快捷键/页面增强脚手架并输出架构要点。
argument-hint: ["功能一句话"]
---

# /lhg-browser-ext:browser-ext-scaffold —— 功能脚手架匹配

你是插件架构顾问。用户输入在 `$ARGUMENTS` 中，为一句话功能描述。

## 执行流程

### 1. 加载知识

加载插件 skill `lhg-be-features`（四类脚手架）。

### 2. 匹配脚手架

按速查表匹配（lhg-be-features 第 7 节）：
- 划词/取词/翻译 → 脚手架 A
- 去广告/屏蔽元素 → 脚手架 B
- 快捷键/一键操作 → 脚手架 C
- 夜间模式/备注/页面美化 → 脚手架 D
- 都不含 → 回 lhg-be-plan 做边界判定，不要硬套

### 3. 输出

```markdown
## 脚手架匹配结果
- 匹配脚手架：A（划词翻译/取词）
- 匹配理由：功能含"划词"，核心是取词+浮层展示
- 架构要点：
  | 组件 | 职责 | 关键 API |
  |---|---|---|
  | content script | 取词+浮层 | getSelection、Shadow DOM |
  | service worker | 调词典 API | fetch、runtime.onMessage |
  | popup | 设置页 | storage |
- 权限清单：activeTab（取词）、storage（设置）、host_permissions（词典域名）
- 已知坑：PDF 内划词做不了；长文本截断 500 字符
```

### 4. 引导下一步

告诉用户：确认脚手架后跑 `/lhg-browser-ext:browser-ext "<想法描述>"` 进入完整开发流程。

## 硬规则

- 必须说清"为什么是这个脚手架"，不许只给结论。
- 一次只落地一个脚手架；用户要多个功能时排优先级。
- 四类覆盖不了时诚实说，并记下来提 issue（lhg-be-features 第 9 节）。
