#!/usr/bin/env python3
"""lhg-browser-ext 硬门②（警告级，不拦截）：写 manifest.json 后做快速体检提醒。

触发：PostToolUse / Write|Edit。只做提醒，永远 exit 0、不拦截写入。
manifest 改完常忘三件事：manifest_version 是否为 3、有无 MV2 残留字段、
icons 引用的文件是否存在；这里做一次轻量检查，缺了就提醒一句。

逃生方式：LHG_BE_HOOKS_OFF=1（环境变量）可关闭本提醒；
或 /plugin disable lhg-browser-ext 停用整个插件。
零第三方依赖。
"""

import json
import os
import sys


def quick_checks(manifest, root):
    tips = []
    if manifest.get("manifest_version") != 3:
        tips.append("manifest_version=%r：MV3 要求为 3" % manifest.get("manifest_version"))
    for bad in ("browser_action", "page_action"):
        if bad in manifest:
            tips.append("MV2 残留字段 %r：MV3 请用 action" % bad)
    bg = manifest.get("background", {}) or {}
    if "scripts" in bg:
        tips.append("MV2 残留 background.scripts：MV3 请用 background.service_worker")
    for size, rel in (manifest.get("icons", {}) or {}).items():
        if not os.path.isfile(os.path.join(root, rel)):
            tips.append("icons[%s]=%r 文件不存在" % (size, rel))
    return tips


def main() -> int:
    if os.environ.get("LHG_BE_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return 0
    if os.path.basename(file_path) != "manifest.json":
        return 0
    if not os.path.isfile(file_path):
        return 0

    try:
        with open(file_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError):
        return 0
    if not isinstance(manifest, dict):
        return 0

    tips = quick_checks(manifest, os.path.dirname(os.path.abspath(file_path)))
    if not tips:
        return 0

    msg = (
        "manifest 体检提醒（lhg-browser-ext）：manifest.json 刚写入，快速检查发现：\n%s\n"
        "完整审计请跑 /lhg-browser-ext:browser-ext-audit。\n"
        "关闭本提醒：export LHG_BE_HOOKS_OFF=1（当前会话有效）。"
    ) % "\n".join("- " + t for t in tips)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
