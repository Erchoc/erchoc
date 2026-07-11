#!/usr/bin/env python3
"""
erchoc/erchoc profile 进度自动更新器（低调 github_dark 单色版）
- 拉 GitHub API 取 followers / total stars
- 生成 assets/progress.svg（GitHub 原生深色 + 单色绿，无渐变）
- 更新 README.md 里 progress.svg 的 ?v= 版本号（破 camo 缓存）

由 .github/workflows/update-progress.yml 每 6 小时调用。
本地测试：GH_USER=erchoc GH_TOKEN=$(gh auth token) python scripts/update_progress.py
"""
import json
import os
import re
import urllib.request

USERNAME = os.environ.get("GH_USER", "erchoc")
TOKEN = os.environ.get("GH_TOKEN", "")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
SVG = os.path.join(ROOT, "assets", "progress.svg")

FOLLOWERS_GOAL = 500
STARS_GOAL = 1000

# GitHub 原生深色调色板（低调，无渐变）
BG = "#0d1117"
FG = "#c9d1d9"
DIM = "#8b949e"
TRACK = "#21262d"
FILL = "#3fb950"   # GitHub green，单色


def api(path):
    url = "https://api.github.com" + path
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "progress-bot",
    })
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def get_followers():
    return int(api("/users/" + USERNAME)["followers"])


def get_total_stars():
    total = 0
    page = 1
    while page <= 10:
        repos = api("/users/%s/repos?per_page=100&page=%d&type=owner" % (USERNAME, page))
        if not repos:
            break
        total += sum(r.get("stargazers_count", 0) for r in repos)
        if len(repos) < 100:
            break
        page += 1
    return total


def build_svg(followers, stars):
    fp = min(100.0, followers / FOLLOWERS_GOAL * 100)
    sp = min(100.0, stars / STARS_GOAL * 100)
    W, H = 420, 96
    bar_x = 110
    bar_w = W - bar_x - 42
    r1, r2 = 22, 64

    def row(y, label, cur, goal, pct):
        fill_w = bar_w * pct / 100
        return (
            '\n  <text x="14" y="{y1}" font-family="-apple-system,Segoe UI,Helvetica,Arial" font-size="10" '
            'font-weight="600" letter-spacing="0.8" fill="{dim}">{label}</text>'
            '\n  <text x="14" y="{y2}" font-family="-apple-system,Segoe UI,Helvetica,Arial" font-size="16" '
            'font-weight="600" fill="{fg}">{cur}<tspan fill="{dim}" font-size="12"> / {goal}</tspan></text>'
            '\n  <rect x="{bx}" y="{by}" rx="4" ry="4" width="{bw}" height="8" fill="{track}"/>'
            '\n  <rect x="{bx}" y="{by}" rx="4" ry="4" width="{fw:.0f}" height="8" fill="{fill}"/>'
            '\n  <text x="{tx}" y="{ty}" font-family="-apple-system,Segoe UI,Helvetica,Arial" font-size="12" '
            'font-weight="600" fill="{fill}" text-anchor="end">{pct:.0f}%</text>'
        ).format(y1=y - 6, y2=y + 9, dim=DIM, label=label, fg=FG, cur=cur,
                 goal=goal, bx=bar_x, by=y - 2, bw=bar_w, track=TRACK,
                 fw=fill_w, tx=W - 14, ty=y + 5, fill=FILL, pct=pct)

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        '\n<rect width="{W}" height="{H}" rx="8" ry="8" fill="{bg}"/>'
        '{r1}{r2}'
        '\n</svg>'
    ).format(W=W, H=H, bg=BG,
             r1=row(r1, "FOLLOWERS", followers, FOLLOWERS_GOAL, fp),
             r2=row(r2, "STARS", stars, STARS_GOAL, sp))


def update_readme(version):
    with open(README, encoding="utf-8") as f:
        content = f.read()
    new = re.sub(r"(assets/progress\.svg\?v=)[\w]+", lambda m: m.group(1) + version, content)
    if new == content:
        return  # 数据没变，不动 README
    with open(README, "w", encoding="utf-8") as f:
        f.write(new)
    print("✅ README 版本号 → ?v=" + version)


def main():
    followers = get_followers()
    stars = get_total_stars()
    print("followers=%d stars=%d" % (followers, stars))

    os.makedirs(os.path.dirname(SVG), exist_ok=True)
    with open(SVG, "w", encoding="utf-8") as f:
        f.write(build_svg(followers, stars))
    print("✅ 已生成 assets/progress.svg")

    update_readme(version="%d_%d" % (followers, stars))


if __name__ == "__main__":
    main()
