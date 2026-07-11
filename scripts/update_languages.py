#!/usr/bin/env python3
"""
erchoc/erchoc 语言代码行数统计器
- 克隆所有非 fork 仓库(--depth 1)
- 用 cloc 统计各语言真实代码行数
- 生成 assets/languages.svg(TOP5 + 百分比, github_dark 低调风)
- 更新 README 里 languages.svg 的 ?v= 版本号(破 camo 缓存)

由 .github/workflows/update-languages.yml 每天调用。
本地测试：GH_USER=erchoc GH_TOKEN=$(gh auth token) MAX_REPOS=3 python scripts/update_languages.py
"""
import json
import os
import re
import subprocess
import tempfile
import urllib.request

USER = os.environ.get("GH_USER", "erchoc")
TOKEN = os.environ.get("GH_TOKEN", "")
MAX_REPOS = int(os.environ.get("MAX_REPOS", "0"))  # 0=不限；测试时设小值
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG = os.path.join(ROOT, "assets", "languages.svg")
README = os.path.join(ROOT, "README.md")

# GitHub Linguist 官方语言色（进度条填充，融入 GitHub 原生风格）
LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5",
    "Go": "#00ADD8", "Java": "#b07219", "Rust": "#dea584", "C": "#555555",
    "C++": "#f34b7d", "C#": "#178600", "Ruby": "#701516", "PHP": "#4F5D95",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "Scala": "#c22d40",
    "Shell": "#89e051", "HTML": "#e34c26", "CSS": "#563d7c", "Vue": "#41b883",
    "Sass": "#c6538c", "Dockerfile": "#384d54", "Makefile": "#427819",
    "Lua": "#000080", "Dart": "#00B4AB", "Elixir": "#6e4a7e", "SQL": "#e38c00",
}
DEFAULT_COLOR = "#3fb950"

BG = "#0d1117"
FG = "#c9d1d9"
DIM = "#8b949e"
TRACK = "#21262d"


def api(path):
    url = "https://api.github.com" + path
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "lang-bot",
    })
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def list_repos():
    repos = []
    page = 1
    while page <= 10:
        data = api("/users/%s/repos?per_page=100&page=%d&type=owner" % (USER, page))
        if not data:
            break
        for r in data:
            if r.get("fork"):
                continue
            if r.get("size", 0) == 0:
                continue
            repos.append((r["name"], r["clone_url"]))
        if len(data) < 100:
            break
        page += 1
    if MAX_REPOS:
        repos = repos[:MAX_REPOS]
    return repos


def authed_url(url):
    if TOKEN:
        return url.replace("https://", "https://x-access-token:%s@" % TOKEN)
    return url


def count_all():
    totals = {}
    repos = list_repos()
    print("待扫描仓库: %d" % len(repos))
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, url) in enumerate(repos, 1):
            dest = os.path.join(tmp, name)
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "-q", authed_url(url), dest],
                    check=True, timeout=180,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                print("  [%d/%d] %s clone 失败，跳过" % (i, len(repos), name))
                continue
            try:
                out = subprocess.run(
                    ["cloc", "--json", "--quiet", dest],
                    capture_output=True, text=True, timeout=180,
                )
                data = json.loads(out.stdout or "{}")
            except Exception:
                print("  [%d/%d] %s cloc 失败" % (i, len(repos), name))
                continue
            for lang, info in data.items():
                if lang in ("header", "SUM") or not isinstance(info, dict):
                    continue
                code = info.get("code", 0)
                if code:
                    totals[lang] = totals.get(lang, 0) + code
            print("  [%d/%d] %s done" % (i, len(repos), name))
    return totals


def build_svg(totals):
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda x: -x[1])[:5]
    W = 360
    row_h = 36
    H = 16 + len(top) * row_h + 8
    parts = []
    for i, (lang, lines) in enumerate(top):
        y = 16 + i * row_h
        pct = lines / total * 100
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)
        bar_w = 150
        bar_x = W - bar_w - 16
        fill_w = bar_w * pct / 100
        parts.append(
            '\n<text x="14" y="{y1}" font-family="-apple-system,Segoe UI,Helvetica,Arial" '
            'font-size="14" font-weight="600" fill="{fg}">{lang}</text>'
            '\n<text x="14" y="{y2}" font-family="-apple-system,Segoe UI,Helvetica,Arial" '
            'font-size="11" fill="{dim}">{lines} lines</text>'
            '\n<rect x="{bx}" y="{by}" rx="4" ry="4" width="{bw}" height="8" fill="{track}"/>'
            '\n<rect x="{bx}" y="{by}" rx="4" ry="4" width="{fw:.0f}" height="8" fill="{color}"/>'
            '\n<text x="{tx}" y="{ty}" font-family="-apple-system,Segoe UI,Helvetica,Arial" '
            'font-size="12" font-weight="600" fill="{color}" text-anchor="end">{pct:.1f}%</text>'
            .format(y1=y + 12, fg=FG, lang=lang, y2=y + 27, dim=DIM,
                    lines=format(int(lines), ","), bx=bar_x, by=y + 11, bw=bar_w,
                    track=TRACK, fw=fill_w, color=color, tx=W - 16, ty=y + 19, pct=pct)
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        '\n<rect width="{W}" height="{H}" rx="8" ry="8" fill="{bg}"/>{rows}'
        '\n</svg>'
    ).format(W=W, H=H, bg=BG, rows="".join(parts))


def update_readme(version):
    with open(README, encoding="utf-8") as f:
        content = f.read()
    new = re.sub(r"(assets/languages\.svg\?v=)[\w]+", lambda m: m.group(1) + version, content)
    if new == content:
        return
    with open(README, "w", encoding="utf-8") as f:
        f.write(new)
    print("✅ README 版本号 → ?v=" + version)


def main():
    totals = count_all()
    if not totals:
        print("⚠️ 未统计到任何语言代码")
        return
    total = sum(totals.values())
    print("总代码行数: %d" % total)
    for lang, lines in sorted(totals.items(), key=lambda x: -x[1])[:5]:
        print("  %s: %d (%.1f%%)" % (lang, lines, lines / total * 100))

    os.makedirs(os.path.dirname(SVG), exist_ok=True)
    with open(SVG, "w", encoding="utf-8") as f:
        f.write(build_svg(totals))
    print("✅ 已生成 assets/languages.svg")
    update_readme(version=str(total))


if __name__ == "__main__":
    main()
