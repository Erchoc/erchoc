#!/usr/bin/env python3
"""
erchoc/erchoc profile 进度自动更新器（tokyonight 极简配色）
- 拉 GitHub API 取 followers / total stars
- 生成 assets/progress.svg
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

# tokyonight 调色板
BG = "#1a1b26"
FG = "#c0caf5"
DIM = "#565f89"
LBL = "#7dcfff"
TRACK = "#292e42"
C1 = "#7aa2f7"   # blue
C2 = "#bb9af7"   # purple


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
    W, H = 460, 104
    bar_x = 118
    bar_w = W - bar_x - 46
    r1, r2 = 22, 66

    def row(y, label, cur, goal, pct, c1, c2):
        gid = "g%d" % int(y)
        fill_w = bar_w * pct / 100
        return (
            '\n  <text x="14" y="{y1}" font-family="Segoe UI,Helvetica,Arial" font-size="10" '
            'font-weight="700" letter-spacing="1.2" fill="{lbl}">{label}</text>'
            '\n  <text x="14" y="{y2}" font-family="Segoe UI,Helvetica,Arial" font-size="17" '
            'font-weight="700" fill="{fg}">{cur}<tspan fill="{dim}" font-size="12" '
            'font-weight="600"> / {goal}</tspan></text>'
            '\n  <rect x="{bx}" y="{by}" rx="5" ry="5" width="{bw}" height="9" fill="{track}"/>'
            '\n  <defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
            '</linearGradient></defs>'
            '\n  <rect x="{bx}" y="{by}" rx="5" ry="5" width="{fw:.0f}" height="9" fill="url(#{gid})"/>'
            '\n  <text x="{tx}" y="{ty}" font-family="Segoe UI,Helvetica,Arial" font-size="12" '
            'font-weight="700" fill="{c1}" text-anchor="end">{pct:.0f}%</text>'
        ).format(y1=y - 6, y2=y + 10, lbl=LBL, label=label, fg=FG, cur=cur,
                 dim=DIM, goal=goal, bx=bar_x, by=y - 2, bw=bar_w, track=TRACK,
                 gid=gid, fw=fill_w, tx=W - 14, ty=y + 6, c1=c1, c2=c2, pct=pct)

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'font-family="Segoe UI,Helvetica,Arial">'
        '\n<rect width="{W}" height="{H}" rx="10" ry="10" fill="{bg}"/>'
        '{r1}{r2}'
        '\n</svg>'
    ).format(W=W, H=H, bg=BG,
             r1=row(r1, "FOLLOWERS", followers, FOLLOWERS_GOAL, fp, C1, C2),
             r2=row(r2, "STARS", stars, STARS_GOAL, sp, C2, C1))


def update_readme(version):
    with open(README, encoding="utf-8") as f:
        content = f.read()
    new = re.sub(r"(assets/progress\.svg\?v=)[\w]+", lambda m: m.group(1) + version, content)
    if new == content:
        print("⚠️ README 未找到 progress.svg?v= 引用，跳过版本号")
        return
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
