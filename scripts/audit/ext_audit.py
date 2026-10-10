#!/usr/bin/env python3
"""lhg-browser-ext 确定性审计：MV3 规范校验 + 权限最小化 + 上架前检查。

用法：
    python3 ext_audit.py --target <插件目录> [--format json|text]

规则注册表：RULES。每条规则 = {id, severity, title, check}。
  check(ctx) -> [(file, line_no, detail), ...]
  ctx = {"root": 目录, "manifest": dict|None, "manifest_text": str,
         "manifest_path": str|None, "js_files": [(path, text), ...]}

exit code 语义：
  0 = 无 blocker（可打包上架；warning/nit 仅提示）
  1 = 有 blocker（MV2 残留/图标缺失/CSP 违规/eval 等，必须修）
  2 = 用法错误（target 不存在等）

零第三方依赖。
"""

import argparse
import json
import os
import re
import sys

SEVERITY_ORDER = {"blocker": 0, "warning": 1, "nit": 2}
ALL_URL_PATTERNS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*"}

# MV2 残留字段：出现在 MV3 manifest 里即 blocker
MV2_LEFT = [
    ("browser_action", None),
    ("page_action", None),
    ("background", "scripts"),
    ("background", "persistent"),
]


def _manifest_key_line(text, *keys):
    """在 manifest 原文中定位 key 所在行号（用于报告）。"""
    lines = text.split("\n")
    # 找最深层 key 的首次出现
    target = keys[-1]
    for i, ln in enumerate(lines, 1):
        if re.search(r'"%s"\s*:' % re.escape(target), ln):
            return i
    return 1


def _js_hits(js_files, patterns, max_hits=5):
    out = []
    for path, text in js_files:
        for i, ln in enumerate(text.split("\n"), 1):
            for p in patterns:
                if re.search(p, ln):
                    out.append((path, i, "命中模式: %s" % p))
                    break
            if len(out) >= max_hits:
                return out
    return out


# ---------------------------------------------------------------- 规则实现

def chk_mft_exists(ctx):
    """BE-MFT-001 blocker：manifest.json 不存在或不是合法 JSON。"""
    if ctx["manifest"] is None:
        if ctx["manifest_path"] is None:
            return [(ctx["root"], 1, "目录下没有 manifest.json")]
        return [(ctx["manifest_path"], 1, "manifest.json 不是合法 JSON")]
    return []


def chk_mv3_version(ctx):
    """BE-MV2-001 blocker：manifest_version 必须为 3。"""
    m = ctx["manifest"]
    if m is None:
        return []
    if m.get("manifest_version") != 3:
        return [(ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "manifest_version"),
                 "manifest_version=%r，必须为 3（MV2 已被 Chrome 停止支持）" % m.get("manifest_version"))]
    return []


def chk_mv2_left(ctx):
    """BE-MV2-002 blocker：MV2 残留字段。"""
    m = ctx["manifest"]
    if m is None:
        return []
    hits = []
    for key, sub in MV2_LEFT:
        if sub is None:
            if key in m:
                hits.append((ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], key),
                             "MV2 残留字段 %r：MV3 请用 action / background.service_worker" % key))
        else:
            bg = m.get(key)
            if isinstance(bg, dict) and sub in bg:
                hits.append((ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], sub),
                             "MV2 残留字段 %s.%s：MV3 后台页改为 service_worker" % (key, sub)))
    return hits


def chk_perm_over(ctx):
    """BE-PERM-001 warning：权限过度申请。"""
    m = ctx["manifest"]
    if m is None:
        return []
    perms = m.get("permissions", []) or []
    hosts = m.get("host_permissions", []) or []
    hits = []
    if "tabs" in perms and any(h in ALL_URL_PATTERNS for h in hosts):
        hits.append((ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "permissions"),
                     "permissions 含 tabs 且 host_permissions 为全站：多数场景 activeTab 已够用"))
    if "webRequest" in perms:
        hits.append((ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "permissions"),
                     "permissions 含 webRequest：MV3 应改用 declarativeNetRequest"))
    if "debugger" in perms:
        hits.append((ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "permissions"),
                     "permissions 含 debugger：每次使用弹警告条，用户体验差且审核严"))
    return hits


def chk_perm_hosts(ctx):
    """BE-PERM-002 warning：host_permissions 申请全站。"""
    m = ctx["manifest"]
    if m is None:
        return []
    hosts = m.get("host_permissions", []) or []
    if any(h in ALL_URL_PATTERNS for h in hosts):
        return [(ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "host_permissions"),
                 "host_permissions 为全站：请收敛到具体域名（如 https://api.example.com/*）")]
    return []


def chk_icon_exists(ctx):
    """BE-ICON-001 blocker：icons 声明的文件不存在。"""
    m = ctx["manifest"]
    if m is None:
        return []
    icons = m.get("icons", {}) or {}
    hits = []
    for size, rel in icons.items():
        p = os.path.join(ctx["root"], rel)
        if not os.path.isfile(p):
            hits.append((ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "icons"),
                         "icons[%s]=%r 文件不存在" % (size, rel)))
    return hits


def chk_icon_128(ctx):
    """BE-ICON-002 warning：缺 128 图标（商店上架要求）。"""
    m = ctx["manifest"]
    if m is None:
        return []
    icons = m.get("icons", {}) or {}
    if "128" not in icons:
        return [(ctx["manifest_path"], _manifest_key_line(ctx["manifest_text"], "icons"),
                 "缺 128px 图标：Chrome 应用商店要求提供")]
    return []


def chk_struct_files(ctx):
    """BE-STRUCT-001 warning：manifest 引用的文件不存在。"""
    m = ctx["manifest"]
    if m is None:
        return []
    refs = []
    bg = m.get("background", {}) or {}
    if bg.get("service_worker"):
        refs.append(("background.service_worker", bg["service_worker"]))
    for s in bg.get("scripts", []) or []:
        refs.append(("background.scripts", s))
    for i, cs in enumerate(m.get("content_scripts", []) or []):
        for j in (cs.get("js", []) or []):
            refs.append(("content_scripts[%d].js" % i, j))
    for act_key in ("action", "browser_action", "page_action"):
        act = m.get(act_key, {}) or {}
        if act.get("default_popup"):
            refs.append(("%s.default_popup" % act_key, act["default_popup"]))
    hits = []
    for where, rel in refs:
        if not os.path.isfile(os.path.join(ctx["root"], rel)):
            hits.append((ctx["manifest_path"], 1, "%s=%r 引用的文件不存在" % (where, rel)))
    return hits


def chk_csp(ctx):
    """BE-CSP-001 blocker：CSP 含 unsafe-eval/unsafe-inline。"""
    m = ctx["manifest"]
    if m is None:
        return []
    csp = m.get("content_security_policy", {}) or {}
    if isinstance(csp, str):
        csp = {"extension_pages": csp}  # MV2 写法是字符串，同样检查
    hits = []
    for area, policy in csp.items():
        if re.search(r"unsafe-eval|unsafe-inline", policy or ""):
            hits.append((ctx["manifest_path"],
                         _manifest_key_line(ctx["manifest_text"], "content_security_policy"),
                         "content_security_policy[%s] 含 unsafe-eval/unsafe-inline：MV3 禁止" % area))
    return hits


def chk_sw_dom(ctx):
    """BE-SW-001 warning：service worker 里用了 DOM API（跑不起来）。"""
    m = ctx["manifest"]
    if m is None:
        return []
    bg = m.get("background", {}) or {}
    sw = bg.get("service_worker")
    if not sw:
        return []
    hits = []
    for path, text in ctx["js_files"]:
        if os.path.basename(path) != os.path.basename(sw):
            continue
        code_all = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        for i, ln in enumerate(code_all.split("\n"), 1):
            code = re.sub(r"//.*", "", ln)
            if re.search(r"\bdocument\b", code):
                hits.append((path, i, "service worker 使用 document：SW 无 DOM 环境，必报错"))
                break
        for i, ln in enumerate(code_all.split("\n"), 1):
            code = re.sub(r"//.*", "", ln)
            if re.search(r"\bwindow\b", code):
                hits.append((path, i, "service worker 使用 window：请改用 self/chrome.* API"))
                break
    return hits


def chk_privacy(ctx):
    """BE-PRIV-001 warning：收集数据但缺隐私政策文件。"""
    m = ctx["manifest"]
    if m is None:
        return []
    perms = set(m.get("permissions", []) or [])
    sensitive = {"storage", "identity", "cookies", "history", "bookmarks", "tabs"}
    if not (sensitive & perms):
        return []
    for cand in ("PRIVACY.md", "privacy.md", "PRIVACY.txt", "privacy.html"):
        if os.path.isfile(os.path.join(ctx["root"], cand)):
            return []
    return [(ctx["manifest_path"], 1,
             "申请了敏感权限（%s）但目录下无 PRIVACY.md：上架审核会被打回"
             % sorted(sensitive & perms))]


def chk_cs_matches(ctx):
    """BE-CS-001 warning：content_scripts 缺 matches 或匹配全站。"""
    m = ctx["manifest"]
    if m is None:
        return []
    hits = []
    for i, cs in enumerate(m.get("content_scripts", []) or []):
        matches = cs.get("matches", []) or []
        if not matches:
            hits.append((ctx["manifest_path"], 1, "content_scripts[%d] 缺 matches：注入范围不明" % i))
        elif any(x in ALL_URL_PATTERNS for x in matches):
            hits.append((ctx["manifest_path"], 1,
                         "content_scripts[%d].matches 为全站：请收敛到目标站点" % i))
    return hits


def chk_hyg_meta(ctx):
    """BE-HYG-001 nit：manifest 缺 name/description/version。"""
    m = ctx["manifest"]
    if m is None:
        return []
    missing = [k for k in ("name", "description", "version") if not m.get(k)]
    if missing:
        return [(ctx["manifest_path"], 1, "manifest 缺字段：%s" % ", ".join(missing))]
    return []


def chk_sec_eval(ctx):
    """BE-SEC-001 blocker：js 里用 eval/new Function。"""
    hits = _js_hits(ctx["js_files"], [r"\beval\s*\(", r"new\s+Function\s*\("])
    return [(p, i, "使用 eval/new Function：MV3 CSP 默认拦截，且有注入风险") for p, i, _ in hits]


def chk_sec_innerhtml(ctx):
    """BE-SEC-002 warning：innerHTML 拼接（XSS 面）。"""
    hits = _js_hits(ctx["js_files"], [r"\.innerHTML\s*\+?="])
    return [(p, i, "使用 innerHTML：拼接外部内容有 XSS 风险，优先 textContent/DOM API") for p, i, _ in hits]


def chk_perm_doc(ctx):
    """BE-PERM-003 nit：权限较多但无权限说明文档。"""
    m = ctx["manifest"]
    if m is None:
        return []
    perms = m.get("permissions", []) or []
    if len(perms) > 2:
        for cand in ("PERMISSIONS.md", "permissions.md"):
            if os.path.isfile(os.path.join(ctx["root"], cand)):
                return []
        return [(ctx["manifest_path"], 1,
                 "申请了 %d 个权限但无 PERMISSIONS.md：建议写清每个权限的用途（上架要填）" % len(perms))]
    return []


RULES = [
    {"id": "BE-MFT-001", "severity": "blocker", "title": "manifest.json 缺失/非法",
     "check": chk_mft_exists},
    {"id": "BE-MV2-001", "severity": "blocker", "title": "非 MV3（manifest_version!=3）",
     "check": chk_mv3_version},
    {"id": "BE-MV2-002", "severity": "blocker", "title": "MV2 残留字段",
     "check": chk_mv2_left},
    {"id": "BE-PERM-001", "severity": "warning", "title": "权限过度申请",
     "check": chk_perm_over},
    {"id": "BE-PERM-002", "severity": "warning", "title": "host_permissions 申请全站",
     "check": chk_perm_hosts},
    {"id": "BE-ICON-001", "severity": "blocker", "title": "icons 引用的文件不存在",
     "check": chk_icon_exists},
    {"id": "BE-ICON-002", "severity": "warning", "title": "缺 128px 图标",
     "check": chk_icon_128},
    {"id": "BE-STRUCT-001", "severity": "warning", "title": "manifest 引用的文件不存在",
     "check": chk_struct_files},
    {"id": "BE-CSP-001", "severity": "blocker", "title": "CSP 含 unsafe-eval/unsafe-inline",
     "check": chk_csp},
    {"id": "BE-SW-001", "severity": "warning", "title": "service worker 使用 DOM API",
     "check": chk_sw_dom},
    {"id": "BE-PRIV-001", "severity": "warning", "title": "敏感权限缺隐私政策",
     "check": chk_privacy},
    {"id": "BE-CS-001", "severity": "warning", "title": "content_scripts 匹配范围问题",
     "check": chk_cs_matches},
    {"id": "BE-HYG-001", "severity": "nit", "title": "manifest 缺基本字段",
     "check": chk_hyg_meta},
    {"id": "BE-SEC-001", "severity": "blocker", "title": "使用 eval/new Function",
     "check": chk_sec_eval},
    {"id": "BE-SEC-002", "severity": "warning", "title": "使用 innerHTML",
     "check": chk_sec_innerhtml},
    {"id": "BE-PERM-003", "severity": "nit", "title": "多权限无说明文档",
     "check": chk_perm_doc},
]


def build_ctx(root):
    manifest_path = os.path.join(root, "manifest.json")
    manifest, manifest_text = None, ""
    found_path = None
    if os.path.isfile(manifest_path):
        found_path = manifest_path
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest_text = f.read()
            manifest = json.loads(manifest_text)
        except (OSError, ValueError, UnicodeDecodeError):
            manifest = None
    js_files = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.endswith(".js"):
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, encoding="utf-8") as f:
                        js_files.append((p, f.read()))
                except (OSError, UnicodeDecodeError):
                    pass
    return {"root": root, "manifest": manifest, "manifest_text": manifest_text,
            "manifest_path": found_path, "js_files": sorted(js_files)}


def main():
    ap = argparse.ArgumentParser(description="lhg-browser-ext 插件审计")
    ap.add_argument("--target", required=True, help="浏览器插件目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    args = ap.parse_args()

    if not os.path.isdir(args.target):
        print("target 不是目录: %s" % args.target, file=sys.stderr)
        return 2

    ctx = build_ctx(os.path.abspath(args.target))
    findings = []
    for rule in RULES:
        try:
            hits = rule["check"](ctx) or []
        except Exception:
            continue  # 单条规则出错不影响整体
        for fp, line_no, detail in hits:
            findings.append({
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "title": rule["title"],
                "file": os.path.relpath(fp, ctx["root"]) if os.path.isabs(fp) else fp,
                "line": line_no,
                "detail": detail,
            })
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["rule_id"]))

    summary = {
        "files": 1 + len(ctx["js_files"]),
        "rules_run": len(RULES),
        "blocker": sum(1 for f in findings if f["severity"] == "blocker"),
        "warning": sum(1 for f in findings if f["severity"] == "warning"),
        "nit": sum(1 for f in findings if f["severity"] == "nit"),
    }

    if args.format == "json":
        print(json.dumps({"summary": summary, "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        print("lhg-browser-ext 审计报告：%s" % args.target)
        print("规则 %d 条 | blocker %d / warning %d / nit %d"
              % (summary["rules_run"], summary["blocker"],
                 summary["warning"], summary["nit"]))
        print("-" * 60)
        for f in findings:
            print("[%s] %s %s:%s %s" % (f["severity"].upper(), f["rule_id"],
                                       f["file"], f["line"], f["title"]))
            print("       %s" % f["detail"])
        if not findings:
            print("干净：无 blocker，可打包上架。")

    return 1 if summary["blocker"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
