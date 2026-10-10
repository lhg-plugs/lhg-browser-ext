#!/usr/bin/env python3
"""lhg-browser-ext 插件冒烟测试：全部绿才算过。

检查项：
 1. 三个 JSON 合法（plugin.json / marketplace.json / hooks.json）
 2. 4 个 SKILL.md 都有 name/description frontmatter，且 150~320 行
 3. 4 个 commands 都有 description + argument-hint frontmatter
 4. 2 个 agents 都有 name/description/tools/model frontmatter
 5. skills 平台中立：不含 Claude Code 专有工具名
 6. fixtures：坏 fixture 的埋点规则必须全部命中且脚本 exit!=0；
    好 fixture 零 blocker 且 exit==0
 7. hooks 脚本：commit 拦截 / 非 commit 放行 / 逃生开关 / 写 manifest 提醒

用法：python3 smoke_test.py [--repo <插件根目录>]
退出码：0=全绿，1=有失败。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((PASS if cond else FAIL, name, detail))
    return cond


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    """解析 markdown 顶部 --- YAML 块（只取一层 key: value）。"""
    text = read(path)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for ln in text[3:end].split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", ln)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


PLUGIN = "lhg-browser-ext"
# 预期的埋点命中（坏 fixture 必须全部命中）
BE_BAD_MUST = {
    "BE-MV2-001", "BE-MV2-002", "BE-PERM-001", "BE-PERM-002",
    "BE-ICON-001", "BE-CSP-001", "BE-SEC-001", "BE-CS-001",
    "BE-STRUCT-001", "BE-PRIV-001",
}
# 平台中立红线：skill 正文不许出现这些 Claude Code 专有表述
NEUTRAL_DENY = ["Task tool", "Bash tool", "Edit tool", "Write tool", "Read tool",
                "AskUserQuestion", "subagent_type", "PreToolUse", "PostToolUse",
                "${CLAUDE_", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    AUDIT = os.path.join(repo, "scripts", "audit")

    # 1. JSON 合法
    for rel in [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                "hooks/hooks.json"]:
        p = os.path.join(repo, rel)
        try:
            d = json.loads(read(p))
            check("JSON 合法: " + rel, True)
            if rel.endswith("plugin.json"):
                check("plugin.json name==%s" % PLUGIN, d.get("name") == PLUGIN, str(d.get("name")))
                check("plugin.json version==1.0.0", d.get("version") == "1.0.0", str(d.get("version")))
                check("plugin.json 有 description/author",
                      all(d.get(k) for k in ("description", "author")))
            if rel.endswith("marketplace.json"):
                ps = d.get("plugins", [])
                check("marketplace.json source==./",
                      len(ps) == 1 and ps[0].get("source") == "./" and
                      ps[0].get("name") == PLUGIN, str(ps))
            if rel.endswith("hooks.json"):
                check("hooks.json 顶层有 hooks 包装", "hooks" in d)
                evts = d["hooks"]
                check("hooks.json 有 PreToolUse+PostToolUse",
                      "PreToolUse" in evts and "PostToolUse" in evts, str(list(evts)))
        except Exception as e:
            check("JSON 合法: " + rel, False, str(e))

    # 2. SKILL.md frontmatter + 行数 + 平台中立 + 出品区
    for skill in ["lhg-be-plan", "lhg-be-mv3", "lhg-be-features", "lhg-be-submit"]:
        p = os.path.join(repo, "skills", skill, "SKILL.md")
        fm = frontmatter(p)
        check("skill frontmatter: " + skill,
              bool(fm.get("name")) and bool(fm.get("description")),
              "name=%s" % fm.get("name"))
        nlines = len(read(p).split("\n"))
        check("skill 行数 150~320: %s (%d 行)" % (skill, nlines), 150 <= nlines <= 320, str(nlines))
        body = read(p)
        bad_words = [w for w in NEUTRAL_DENY if w in body]
        check("skill 平台中立: " + skill, not bad_words, "命中: %s" % bad_words)
        check("skill 有出品区: " + skill, "出品：刘洪光" in body and "https://github.com/lhg-skills" in body)
        check("skill 有自检与反馈: " + skill, "自检与反馈" in body)

    # 3. commands
    for cmd in ["browser-ext", "browser-ext-scaffold", "browser-ext-submit", "browser-ext-audit"]:
        p = os.path.join(repo, "commands", cmd + ".md")
        fm = frontmatter(p)
        check("command description+argument-hint: " + cmd,
              bool(fm.get("description")) and bool(fm.get("argument-hint")),
              str(fm.get("description"))[:50])

    # 4. agents
    for ag in ["be-builder", "be-auditor"]:
        p = os.path.join(repo, "agents", ag + ".md")
        fm = frontmatter(p)
        check("agent frontmatter: " + ag,
              all(fm.get(k) for k in ("name", "description", "tools", "model")),
              str({k: fm.get(k) for k in ("name", "model")}))

    # 5. 审计脚本冒烟
    def audit_hits(script, target):
        r = run([sys.executable, os.path.join(AUDIT, script),
                 "--target", os.path.join(repo, target), "--format", "json"])
        try:
            d = json.loads(r.stdout)
        except Exception:
            return None, r.returncode, []
        return d["summary"], r.returncode, [f["rule_id"] for f in d["findings"]]

    s, code, ids = audit_hits("ext_audit.py", "fixtures/be-bad")
    check("be 坏 fixture exit!=0", code != 0, "exit=%d" % code)
    check("be 坏 fixture blocker>0", s and s["blocker"] > 0, str(s))
    missing = BE_BAD_MUST - set(ids)
    check("be 埋点全命中 (%d/%d)" % (len(BE_BAD_MUST - missing), len(BE_BAD_MUST)),
          not missing, "缺失: %s" % sorted(missing))

    s, code, ids = audit_hits("ext_audit.py", "fixtures/be-good")
    check("be 好 fixture 零 blocker", s and s["blocker"] == 0, str(s))
    check("be 好 fixture 零 warning", s and s["warning"] == 0, str(s))
    check("be 好 fixture exit==0", code == 0, "exit=%d" % code)

    n = json.loads(run([sys.executable, os.path.join(AUDIT, "ext_audit.py"),
                        "--target", os.path.join(repo, "fixtures/be-good"),
                        "--format", "json"]).stdout)["summary"]["rules_run"]
    check("规则总数>=15 (%d)" % n, n >= 15, str(n))

    # 6. hooks 脚本
    def hook(script, payload, env=None):
        e = dict(os.environ); e.update(env or {})
        return run([sys.executable, os.path.join(repo, "hooks", script)],
                   input=payload, env=e)

    r = hook("pre_commit_audit.py", '{"tool_input":{"command":"git status"}}')
    check("hook: 非 commit 放行", r.returncode == 0 and not r.stdout.strip())
    r = hook("pre_commit_audit.py",
             '{"tool_input":{"command":"git commit -m \\"x\\""}}',
             {"CLAUDE_PROJECT_DIR": os.path.join(repo, "fixtures/be-bad")})
    try:
        d = json.loads(r.stdout)
        denied = d["hookSpecificOutput"]["permissionDecision"] == "deny"
    except Exception:
        denied = False
    check("hook: commit 有 blocker 拦截", denied, r.stdout[:120])
    r = hook("pre_commit_audit.py",
             '{"tool_input":{"command":"git commit -m \\"x\\""}}',
             {"CLAUDE_PROJECT_DIR": os.path.join(repo, "fixtures/be-bad"),
              "LHG_BE_HOOKS_OFF": "1"})
    check("hook: 逃生开关生效", r.returncode == 0 and not r.stdout.strip())

    with tempfile.TemporaryDirectory() as td:
        bad_m = os.path.join(td, "manifest.json")
        shutil.copy(os.path.join(repo, "fixtures/be-bad/manifest.json"), bad_m)
        r = hook("post_write_warn.py", json.dumps({"tool_input": {"file_path": bad_m}}))
        check("hook: 坏 manifest 提醒", "additionalContext" in r.stdout, r.stdout[:80])
        good_dir = os.path.join(td, "good")
        shutil.copytree(os.path.join(repo, "fixtures/be-good"), good_dir)
        r = hook("post_write_warn.py",
                 json.dumps({"tool_input": {"file_path": os.path.join(good_dir, "manifest.json")}}))
        check("hook: 规范 manifest 不提醒", not r.stdout.strip(), r.stdout[:80])
        txt = os.path.join(td, "a.txt")
        open(txt, "w").write("hello")
        r = hook("post_write_warn.py", json.dumps({"tool_input": {"file_path": txt}}))
        check("hook: 非 manifest 放行", not r.stdout.strip())
        r = hook("post_write_warn.py",
                 json.dumps({"tool_input": {"file_path": bad_m}}),
                 {"LHG_BE_HOOKS_OFF": "1"})
        check("hook: 写提醒逃生开关生效", not r.stdout.strip())

    # 报告
    print("=" * 60)
    print("%s 冒烟测试报告" % PLUGIN)
    print("=" * 60)
    fails = 0
    for st, name, detail in results:
        mark = "✓" if st == PASS else "✗"
        print("%s %s %s" % (mark, st, name))
        if detail and st == FAIL:
            print("    → %s" % detail)
        if st == FAIL:
            fails += 1
    print("=" * 60)
    print("共 %d 项，通过 %d，失败 %d" % (len(results), len(results) - fails, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
