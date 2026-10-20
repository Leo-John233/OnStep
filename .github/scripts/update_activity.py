from __future__ import annotations

import base64
import fnmatch
import hashlib
import html
import json
import os
import re
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.parse import urlparse

# 配置
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "site"
BASE_BRANCH = os.getenv("ACTIVITY_BASE_BRANCH", "OnStep4.24-FeatureRelease")
ORIGINAL_BRANCH = os.getenv("ACTIVITY_ORIGINAL_BRANCH", "OnStep4.24-Original")
BRANCH_PATTERN = os.getenv("ACTIVITY_BRANCH_PATTERN", "*")
UPSTREAM_BRANCH = os.getenv("ACTIVITY_UPSTREAM_BRANCH", "release-4.24")
UPSTREAM_REF = f"refs/remotes/upstream/{UPSTREAM_BRANCH}"
UPSTREAM_URL = "https://github.com/hjd1964/OnStep"
EXCLUDED_BRANCHES = {ORIGINAL_BRANCH}
EXCLUDED_BRANCHES.update(
    item.strip()
    for item in os.getenv("ACTIVITY_EXCLUDED_BRANCHES", "").split(",")
    if item.strip()
)
TZ = ZoneInfo(os.getenv("ACTIVITY_TIMEZONE", "Asia/Shanghai"))
RECENT_DAYS = 7
RECENT_HISTORY_DAYS = 370
MAX_RECENT_ROWS = 12

IGNORED_FILES = {
    "README.md",
    "assets/repository-activity.svg",
    "assets/repository-statistics.svg",
    "assets/recent-changes.svg",
    "assets/branch-statistics.svg",
    "docs/activity.html",
    "docs/activity-data.json",
}
IGNORED_PREFIXES = (".github/", "site/")
AUTO_COMMIT_MESSAGES = {"docs: auto-update repository activity"}
BOT_AUTHORS = {"github-actions[bot]", "dependabot[bot]"}
AUTHOR_ALIASES = {
    "Leo-John": "Leo-John233",
    "Leo·John": "Leo-John233",
    "Leo-John233": "Leo-John233",
}
MAINTAINER = "Leo-John233"
# 2026-05-12 是本仓库创建日，用作识别二次开发贡献的时间边界。
PROJECT_START_DATE = date.fromisoformat(os.getenv("ACTIVITY_PROJECT_START_DATE", "2026-05-12"))
MAX_VISIBLE_PEOPLE = 3  # 上游仓库所有者置顶，再显示两名提交最多的开发者
MAX_BRANCH_PREVIEW = 3
GITHUB_USER_BY_AUTHOR = {
    "Leo-John233": "Leo-John233",
    "Linyu": "Sakuralinyu",  # 通过 GitHub 提交元数据确认
}


# Git 读取

def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode:
        raise RuntimeError(f"Git 命令失败 git {' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def git_ok(*args: str) -> bool:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=False,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def branch_ref(branch: str) -> str:
    remote = f"refs/remotes/origin/{branch}"
    return remote if git_ok("show-ref", "--verify", "--quiet", remote) else branch


def discover_branches() -> list[str]:
    """自动发现全部分支，只把非排除分支纳入统计。"""
    remote = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/")
    branches = []
    for line in remote.splitlines():
        line = line.strip()
        if line.startswith("origin/") and line != "origin/HEAD":
            branches.append(line[len("origin/"):])
    if not branches:
        branches = [
            s.strip() for s in git(
                "for-each-ref", "--format=%(refname:short)", "refs/heads/"
            ).splitlines() if s.strip()
        ]
    branches = sorted({
        name for name in branches
        if name not in EXCLUDED_BRANCHES and fnmatch.fnmatch(name, BRANCH_PATTERN)
    })
    if BASE_BRANCH not in branches:
        raise RuntimeError(f"未发现发布分支 {BASE_BRANCH} 请确认已获取全部分支")
    branches.remove(BASE_BRANCH)
    return [BASE_BRANCH, *branches]


def canonical_author(author: str) -> str:
    return AUTHOR_ALIASES.get(author.strip(), author.strip())


def is_bot_commit(commit: dict) -> bool:
    author = canonical_author(commit["author"])
    return (
        author in BOT_AUTHORS
        or "[bot]" in author.lower()
        or commit["subject"] in AUTO_COMMIT_MESSAGES
        or ("noreply@github.com" in commit["email"].lower()
            and "actions" in author.lower())
    )


def parse_log(raw: str) -> list[dict]:
    result = []
    for record in raw.split("\x1e"):
        parts = record.strip().split("\x1f", 4)
        if len(parts) != 5:
            continue
        sha, author, email, timestamp, subject = parts
        try:
            dt = datetime.fromisoformat(timestamp.strip()).astimezone(TZ)
        except ValueError:
            continue
        result.append({
            "sha": sha.strip(), "short_sha": sha.strip()[:7],
            "author": canonical_author(author), "email": email.strip(),
            "subject": subject.strip(), "date": dt.date(), "datetime": dt,
        })
    return result


def load_log(ref: str, days: int | None = None) -> list[dict]:
    args = ["log", ref]
    if days is not None:
        args.append(f"--since={days} days ago")
    args.append("--pretty=format:%H%x1f%aN%x1f%aE%x1f%aI%x1f%s%x1e")
    return parse_log(git(*args))


def should_ignore_file(path: str) -> bool:
    path = path.replace("\\", "/")
    return path in IGNORED_FILES or any(path.startswith(x) for x in IGNORED_PREFIXES)


@lru_cache(maxsize=None)
def get_commit_files(sha: str) -> tuple[str, ...]:
    raw = git("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", sha)
    return tuple(path for raw_path in raw.split("\0")
                 if (path := raw_path.strip()) and not should_ignore_file(path))


def summarize_scope(files: tuple[str, ...]) -> str:
    if not files:
        return ""
    if len(files) == 1:
        return files[0]
    roots = list(dict.fromkeys(p.split("/", 1)[0] for p in files))
    if len(roots) == 1:
        return f"{roots[0]} {len(files)} 个文件"
    return f"{len(files)} 个文件"


def load_recent_history(ref: str) -> list[dict]:
    commits = []
    for commit in load_log(ref, RECENT_HISTORY_DAYS):
        if is_bot_commit(commit):
            continue
        files = get_commit_files(commit["sha"])
        if not files:
            continue
        commits.append({
            **commit, "files": files,
            "file_count": len(files), "scope": summarize_scope(files),
        })
    return commits


def load_full_history(ref: str) -> list[dict]:
    return [c for c in load_log(ref) if not is_bot_commit(c)]


def combine_histories(histories: list[list[dict]]) -> list[dict]:
    """按完整 Commit SHA 跨分支去重，保留每次真实提交的唯一记录。"""
    unique: dict[str, dict] = {}
    for branch_history in histories:
        for commit in branch_history:
            unique.setdefault(commit["sha"], commit)
    return sorted(
        unique.values(),
        key=lambda c: (c["datetime"], c["sha"]), reverse=True,
    )


def last_n_days(history: list[dict], days: int) -> list[dict]:
    today = datetime.now(TZ).date()
    first = today - timedelta(days=days - 1)
    return [c for c in history if first <= c["date"] <= today]


def contribution_counts(history: list[dict]) -> Counter:
    counts: Counter = Counter()
    for commit in last_n_days(history, 365):
        counts[commit["date"].isoformat()] += 1
    return counts


def repository_statistics(history: list[dict]) -> dict:
    # 仓库整体历史仍按完整 SHA 去重，此处保留所有历史作者统计。
    counts = Counter(c["author"] for c in history)
    return {"total_commits": len(history), "contributors": len(counts),
            "authors": counts}


def inherited_commit_shas() -> set[str]:
    """使用现存 Original 及上游分支的 Git 历史识别继承提交。"""
    shas: set[str] = set()
    for ref in (branch_ref(ORIGINAL_BRANCH), UPSTREAM_REF):
        if git_ok("rev-parse", "--verify", f"{ref}^{{commit}}"):
            shas.update(git("rev-list", ref).splitlines())
    return shas


def developer_contributors(
    history: list[dict], inherited_shas: set[str], original_author: str
) -> list[dict]:
    """仅统计二次开发以来的独立有效提交，按次数与最近提交时间动态排序。"""
    counts: Counter = Counter()
    latest: dict[str, datetime] = {}
    examples: dict[str, str] = {}
    emails: dict[str, str] = {}
    for commit in history:
        if commit["sha"] in inherited_shas or commit["date"] < PROJECT_START_DATE:
            continue
        name = commit["author"]
        if name == original_author:
            # 原作者在维护区固定展示，其上游提交不计入二次开发者人数。
            continue
        counts[name] += 1
        if name not in latest or commit["datetime"] > latest[name]:
            latest[name] = commit["datetime"]
            examples[name] = commit["sha"]
            emails[name] = commit.get("email", "")

    result: list[dict] = []
    for name, count in counts.items():
        username = GITHUB_USER_BY_AUTHOR.get(name)
        if not username:
            # github noreply 地址包含可验证的 GitHub 用户名。
            match = re.fullmatch(
                r"(?:\d+\+)?([a-zA-Z0-9-]+)@users\.noreply\.github\.com",
                emails.get(name, "").lower(),
            )
            if match:
                username = match.group(1)
        result.append({
            "name": name, "count": count, "latest": latest[name],
            "last_sha": examples[name], "username": username,
        })
    return sorted(result, key=lambda x: (-x["count"], -x["latest"].timestamp(), x["name"].casefold()))


@lru_cache(maxsize=1)
def identify_upstream_author() -> dict:
    """从上游仓库 URL 识别 GitHub 仓库所有者，并读取该账户显示名。"""
    path_parts = urlparse(UPSTREAM_URL).path.strip("/").split("/")
    if len(path_parts) < 2 or not path_parts[0]:
        return {"name": "未知上游所有者", "username": None,
                "source": "repository_owner"}

    # GitHub 仓库路径 /OWNER/REPO 中的 OWNER 即仓库所有者。
    owner = path_parts[0]
    display_name = owner
    request = Request(
        f"https://api.github.com/users/{owner}",
        headers={"User-Agent": "OnStep-Repository-Activity/1.0",
                 "Accept": "application/vnd.github+json"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            profile = json.loads(response.read(50000).decode("utf-8"))
        if isinstance(profile, dict):
            display_name = (profile.get("name") or "").strip() or owner
    except (OSError, ValueError, UnicodeError) as exc:
        # 公共 API 暂不可用时，仍使用真实的 GitHub owner 登录名。
        print(f"无法读取上游 GitHub 所有者显示名，使用账号 {owner}: {exc}")

    return {"name": display_name, "username": owner,
            "source": "repository_owner"}


def upstream_information() -> dict:
    """比较 Original 与上游配置分支，同时识别上游仓库所有者。"""
    author_info = identify_upstream_author()
    info = {
        "source": UPSTREAM_URL, **{
            "author": author_info["name"],
            "author_username": author_info["username"],
            "author_source": author_info["source"],
        },
        "original_date": None, "original_sha": None,
        "upstream_date": None, "upstream_additions": None,
        "upstream_compare_url": None, "first_year": None,
    }
    original_ref = branch_ref(ORIGINAL_BRANCH)
    if git_ok("rev-parse", "--verify", f"{original_ref}^{{commit}}"):
        info["original_sha"] = git("rev-parse", original_ref).strip()
        first = git("log", "--reverse", "--format=%aI", original_ref).splitlines()
        if first:
            info["first_year"] = datetime.fromisoformat(first[0]).year
        latest = git("log", "-1", "--format=%aI", original_ref).strip()
        if latest:
            info["original_date"] = datetime.fromisoformat(latest).date().isoformat()
    if git_ok("rev-parse", "--verify", f"{UPSTREAM_REF}^{{commit}}"):
        latest = git("log", "-1", "--format=%aI", UPSTREAM_REF).strip()
        if latest:
            info["upstream_date"] = datetime.fromisoformat(latest).date().isoformat()
        if info["original_sha"] and git_ok("merge-base", "--is-ancestor", original_ref, UPSTREAM_REF):
            info["upstream_additions"] = int(git(
                "rev-list", "--count", f"{original_ref}..{UPSTREAM_REF}"
            ).strip())
            info["upstream_compare_url"] = (
                f"{UPSTREAM_URL}/compare/{info['original_sha']}...{UPSTREAM_BRANCH}"
            )
    return info


def branch_role(branch: str) -> str:
    if branch == BASE_BRANCH:
        return "发布分支"
    name = branch.lower()
    if name.endswith("dev") or "development" in name:
        return "开发分支"
    if "test" in name:
        return "测试分支"
    if "patch" in name or "temp" in name or "tmp" in name:
        return "临时分支"
    if name.startswith("push/"):
        return "协作分支"
    return "功能分支"


def slug(branch: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-")
    return f"{clean[:80] or 'branch'}-{hashlib.sha256(branch.encode()).hexdigest()[:12]}"


def repo_url() -> str:
    return f"https://github.com/{os.getenv('GITHUB_REPOSITORY', 'Leo-John233/OnStep')}"


def commit_url(sha: str) -> str:
    return f"{repo_url()}/commit/{sha}"


def branch_url(branch: str) -> str:
    return f"{repo_url()}/tree/{branch}"


# SVG 公共组件

def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def short_text(value: str, limit: int) -> str:
    """中英文等宽截断，避免长路径或长提交信息溢出列宽。"""
    units = 0
    output = []
    for ch in value:
        width = 2 if ord(ch) > 127 else 1
        if units + width > limit:
            return "".join(output).rstrip() + "…"
        output.append(ch)
        units += width
    return "".join(output)


COMMON_STYLE = """
.text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei","PingFang SC",Helvetica,Arial,sans-serif}
.title{fill:#24292f;font-size:24px;font-weight:650}.subtitle{fill:#57606a;font-size:14px}
.rightmeta{fill:#57606a;font-size:14px;font-weight:500;text-anchor:end}
.card{fill:#fff;stroke:#d0d7de;stroke-width:1}.line{stroke:#d8dee4;stroke-width:1}
.label{fill:#57606a;font-size:14px;font-weight:600}.normal{fill:#24292f;font-size:15px}
.bold{fill:#24292f;font-size:15px;font-weight:600}.muted{fill:#57606a;font-size:14px}
.link{fill:#0969da;font-size:15px;font-weight:600}.rightlink{fill:#0969da;font-size:14px;font-weight:600;text-anchor:end}.tiny{fill:#57606a;font-size:13px}
.metric{fill:#24292f;font-size:23px;font-weight:650;text-anchor:middle}
.metric-label{fill:#57606a;font-size:14px;text-anchor:middle}.subheading{fill:#24292f;font-size:15px;font-weight:600}
@media(prefers-color-scheme:dark){
.card{fill:#0d1117;stroke:#30363d}.title,.normal,.bold,.metric,.subheading{fill:#c9d1d9}
.subtitle,.rightmeta,.label,.muted,.tiny,.metric-label{fill:#8b949e}.link{fill:#58a6ff}
.line{stroke:#30363d}.rightlink{fill:#58a6ff}}
"""
ACTIVITY_STYLE = COMMON_STYLE + """
.month,.weekday{fill:#57606a;font-size:14px}.level-0{fill:#ebedf0;stroke:rgba(27,31,35,.06);stroke-width:1}
.level-1{fill:#9be9a8}.level-2{fill:#40c463}.level-3{fill:#30a14e}.level-4{fill:#216e39}
@media(prefers-color-scheme:dark){.month,.weekday{fill:#8b949e}.level-0{fill:#161b22;stroke:#1b1f23}
.level-1{fill:#0e4429}.level-2{fill:#006d32}.level-3{fill:#26a641}.level-4{fill:#39d353}}
"""


def header(title: str, subtitle: str, right: str = "") -> list[str]:
    """标题图标与已确认的 README 视觉风格保持一致。"""
    icons = {
        "最近代码修改": [
            '<path d="M11 6h18l6 6v20H11z" fill="#eaeef2" stroke="#d0d7de"/>',
            '<path d="M29 6v6h6" fill="none" stroke="#afb8c1"/>',
            '<path d="M16 15h14M16 20h10M16 25h8" fill="none" stroke="#afb8c1"/>',
            '<path d="M27 30l13-13 4 4-13 13-7 3z" fill="#f78166"/>',
            '<path d="M24 37l3-7 4 4z" fill="#57606a"/>',
        ],
        "代码活动热力图": [
            '<rect x="12" y="7" width="26" height="26" rx="5" fill="#2da44e"/>',
            '<path d="M14 9h22v3H14z" fill="#56d364" opacity=".55"/>',
        ],
        "仓库统计": [
            '<rect x="10" y="19" width="7" height="14" rx="1" fill="#6e40c9"/>',
            '<rect x="20" y="9" width="7" height="24" rx="1" fill="#8957e5"/>',
            '<rect x="30" y="15" width="7" height="18" rx="1" fill="#b392f0"/>',
        ],
    }
    parts = [*icons.get(title, []),
             f'<text class="text title" x="49" y="29">{esc(title)}</text>',
             f'<text class="text subtitle" x="0" y="57">{esc(subtitle)}</text>']
    if right:
        parts.append(f'<text class="text rightmeta" x="1110" y="29">{esc(right)}</text>')
    return parts


def svg_open(height: int, style: str = COMMON_STYLE) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" viewBox="0 0 1120 {height}" role="img">',
            "<style>", style, "</style>"]


def card(x: float, y: float, w: float, h: float) -> str:
    return f'<rect class="card" x="{x}" y="{y}" width="{w}" height="{h}" rx="6" ry="6"/>'


def line(y: int, x1: int = 1, x2: int = 1119) -> str:
    return f'<line class="line" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"/>'


def save_svg(path: Path, content: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([*content, "</svg>"]) + "\n", encoding="utf-8")


def svg_link(text: str, url: str, x: int, y: int, cls: str = "link") -> str:
    return f'<a href="{esc(url)}" target="_blank"><text class="text {cls}" x="{x}" y="{y}">{esc(text)}</text></a>'


# 最近代码修改

def generate_recent_svg(history: list[dict], output: Path, branch: str) -> None:
    current = last_n_days(history, RECENT_DAYS)
    visible = current[:MAX_RECENT_ROWS]
    hidden = len(current) - len(visible)
    card_top = 80
    header_h, row_h, footer_h = 46, 45, 39
    rows = max(1, len(visible))
    card_h = header_h + row_h * rows + footer_h
    svg = svg_open(card_top + card_h + 1)
    svg += header("最近代码修改", f"统计范围 {branch}", f"近 {RECENT_DAYS} 天 {len(current):,} 次提交")
    svg.append(card(.5, card_top + .5, 1118, card_h - 1))
    columns = [(28, "日期"), (128, "修改者"), (316, "修改内容"),
               (809, "提交版本"), (918, "影响范围")]
    for x, label in columns:
        svg.append(f'<text class="text label" x="{x}" y="109">{label}</text>')
    svg.append(line(card_top + header_h))
    for i, commit in enumerate(visible):
        y = card_top + header_h + i * row_h + 29
        when = commit["date"]
        svg.append(f'<text class="text normal" x="28" y="{y}">{when.month}/{when.day:02d}</text>')
        svg.append(f'<text class="text bold" x="128" y="{y}">{esc(short_text(commit["author"], 20))}</text>')
        link = commit_url(commit["sha"])
        svg.append(svg_link(short_text(commit["subject"], 56), link, 316, y))
        svg.append(svg_link(commit["short_sha"], link, 809, y))
        svg.append(f'<text class="text muted" x="918" y="{y}">{esc(short_text(commit["scope"], 24))}</text>')
        if i + 1 < len(visible):
            svg.append(line(card_top + header_h + (i + 1) * row_h, 26, 1093))
    if not visible:
        svg.append(f'<text class="text muted" x="28" y="154">最近 {RECENT_DAYS} 天没有有效代码提交</text>')
    footer_y = card_top + header_h + row_h * rows
    svg.append(line(footer_y))
    note = "仅统计实际代码或项目文件修改"
    if hidden:
        note += f" 另有 {hidden} 条未显示"
    svg.append(f'<text class="text tiny" x="28" y="{footer_y + 26}">{esc(note)}</text>')
    save_svg(output, svg)


# 年度代码活动热力图

def contribution_level(n: int) -> int:
    return 0 if n == 0 else 1 if n == 1 else 2 if n <= 3 else 3 if n <= 6 else 4


def generate_activity_svg(history: list[dict], output: Path, scope: str) -> None:
    counts = contribution_counts(history)
    total = sum(counts.values())
    today = datetime.now(TZ).date()
    first = today - timedelta(days=364)
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    card_top = 80
    svg = svg_open(314, ACTIVITY_STYLE)
    svg += header("代码活动热力图", f"统计范围 {scope}", f"近一年 {total:,} 次提交")
    svg.append(card(.5, card_top + .5, 1118, 233))
    grid_left, grid_top = 80, 130
    step, size = 19, 14
    month_mark = None
    prev_x = -100
    for w in range(53):
        month_date = start + timedelta(days=w * 7 + 3)
        if month_date.month == month_mark:
            continue
        x = grid_left + w * step
        if x - prev_x >= 45:
            svg.append(f'<text class="text month" x="{x}" y="120">{month_date.strftime("%b")}</text>')
            month_mark = month_date.month
            prev_x = x
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        svg.append(f'<text class="text weekday" x="32" y="{grid_top + row * step + 12}">{label}</text>')
    for offset in range((today - start).days + 1):
        current = start + timedelta(days=offset)
        if not first <= current <= today:
            continue
        w = offset // 7
        if w >= 53:
            continue
        row = (current.weekday() + 1) % 7
        x, y = grid_left + w * step, grid_top + row * step
        n = counts[current.isoformat()]
        svg.append(
            f'<rect class="level-{contribution_level(n)}" x="{x}" y="{y}" width="{size}" '
            f'height="{size}" rx="2" ry="2"><title>{current.isoformat()} {n} 次提交</title></rect>'
        )
    svg.append('<text class="text tiny" x="28" y="289">仅统计实际代码或项目文件修改</text>')
    svg.append('<text class="text tiny" x="869" y="289">Less</text>')
    for i in range(5):
        svg.append(f'<rect class="level-{i}" x="{909 + i * 19}" y="275" width="14" height="14" rx="2" ry="2"/>')
    svg.append('<text class="text tiny" x="1020" y="289">More</text>')
    save_svg(output, svg)


# 仓库统计 项目维护 上游信息

@lru_cache(maxsize=8)
def github_avatar_data_uri(username: str) -> str | None:
    """Download each GitHub avatar once and embed it directly in the SVG."""
    request = Request(
        f"https://github.com/{username}.png?size=96",
        headers={"User-Agent": "OnStep-Activity/1.0"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            mime = response.headers.get_content_type()
            picture = response.read(300_001)
        if mime not in {"image/png", "image/jpeg", "image/webp"}:
            print(f"Unsupported GitHub avatar format for {username}: {mime}")
            return None
        if not picture or len(picture) > 300_000:
            print(f"Invalid GitHub avatar size for {username}")
            return None
        encoded = base64.b64encode(picture).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except (OSError, ValueError) as exc:
        print(f"Could not load GitHub avatar for {username}: {exc}")
        return None


def avatar(
    cx: int, cy: int, bg: str, fg: str, username: str | None = None
) -> list[str]:
    """Round GitHub avatar; retain the original icon as a network fallback."""
    data_uri = github_avatar_data_uri(username) if username else None
    if data_uri:
        clip_id = f"avatar-clip-{cx}-{cy}"
        return [
            f'<defs><clipPath id="{clip_id}"><circle cx="{cx}" cy="{cy}" r="19"/></clipPath></defs>',
            f'<circle cx="{cx}" cy="{cy}" r="19" fill="{bg}"/>',
            f'<image href="{data_uri}" x="{cx - 19}" y="{cy - 19}" width="38" height="38" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip_id})"/>',
        ]
    return [
        f'<circle cx="{cx}" cy="{cy}" r="19" fill="{bg}"/>',
        f'<circle cx="{cx}" cy="{cy - 6}" r="5" fill="{fg}"/>',
        f'<path d="M{cx - 10} {cy + 12}v-3c0-11 20-11 20 0v3z" fill="{fg}"/>',
    ]


def generate_statistics_svg(
    history: list[dict], output: Path, scope: str, upstream: dict,
    developers: list[dict],
) -> None:
    """三列指标和原有外观保持一致，维护者按实际开发提交动态排列。"""
    stats = repository_statistics(history)
    year = upstream["first_year"]
    year_label = f"Since {year}" if year else "上游项目"
    svg = svg_open(402)
    svg += header("仓库统计", f"统计范围 {scope}")
    svg.append(card(.5, 80.5, 1118, 319))

    metrics = [
        (186, f"{stats['total_commits']:,}", "历史唯一提交"),
        (560, f"{len(developers):,}", "二次开发贡献者"),
        (934, year_label, "上游项目历史"),
    ]
    for x, value, label in metrics:
        svg.append(f'<text class="text metric" x="{x}" y="117">{esc(value)}</text>')
        svg.append(f'<text class="text metric-label" x="{x}" y="145">{esc(label)}</text>')
    svg.extend([
        '<line class="line" x1="373" y1="96" x2="373" y2="153"/>',
        '<line class="line" x1="747" y1="96" x2="747" y2="153"/>',
        line(168),
        '<text class="text subheading" x="28" y="195">项目维护</text>',
    ])

    # 上游仓库所有者固定首位；其余开发者按独立提交数降序动态填充。
    people = [{"name": upstream["author"], "username": upstream["author_username"],
               "role": "上游项目原作者", "count": None}]
    people.extend({**item, "role": ("二次开发维护者" if item["name"] == MAINTAINER
                                  else "项目开发贡献者")} for item in developers)
    positions = (48, 363, 678)  # 比旧版 48 和 576 的大间隔更紧凑
    for position, person in zip(positions, people[:MAX_VISIBLE_PEOPLE]):
        founder = person["count"] is None
        bg, fg = ("#fff1cc", "#9a6700") if founder else ("#ddf4ff", "#0969da")
        svg += avatar(position, 235, bg, fg, person["username"])
        name = short_text(person["name"], 24)
        if person["username"]:
            svg.append(svg_link(name, f"https://github.com/{person['username']}", position + 32, 229))
        else:
            svg.append(f'<text class="text bold" x="{position + 32}" y="229">{esc(name)}</text>')
        role = person["role"] if founder else f"{person['role']} · {person['count']:,} 次提交"
        svg.append(f'<text class="text muted" x="{position + 32}" y="253">{esc(role)}</text>')

    # 作者多于两名时，上游所有者加前两名显示在同一行；完整列表在 Pages 中查看。
    if len(people) > MAX_VISIBLE_PEOPLE:
        svg.append(svg_link("查看更多贡献者", "https://leo-john233.github.io/OnStep/contributors.html", 962, 195, "link"))

    svg.append(line(269))
    svg.append('<text class="text label" x="28" y="304">项目来源</text>')
    svg.append(svg_link("hjd1964/OnStep", UPSTREAM_URL, 119, 304))
    svg.append('<text class="text label" x="28" y="344">上游更新</text>')
    latest = upstream["upstream_date"] or "未获取"
    baseline = upstream["original_date"] or "未获取"
    svg.append(f'<text class="text normal" x="119" y="336">上游最新 {esc(latest)} · Original 基线 {esc(baseline)}</text>')
    additions = upstream["upstream_additions"]
    note = (f"上游相较 Original 新增 {additions:,} 次提交" if additions is not None
            else "上游更新差异暂不可比较")
    svg.append(f'<text class="text tiny" x="119" y="368">{esc(note)}</text>')
    if upstream["upstream_compare_url"]:
        svg.append(svg_link("查看上游更新", upstream["upstream_compare_url"], 1080, 368, "rightlink"))
    save_svg(output, svg)


def generate_contributors_html(developers: list[dict], upstream: dict) -> None:
    """完整二次开发作者名单，避免维护区域随贡献者数量增长而撑开。"""
    rows = []
    for i, item in enumerate(developers, 1):
        author = html.escape(item["name"])
        username = item["username"]
        if username:
            author_html = f'<a href="https://github.com/{html.escape(username, quote=True)}">{author}</a>'
            picture = f'<img src="https://github.com/{html.escape(username, quote=True)}.png?size=64" width="30" height="30" alt=""/>'
        else:
            author_html = author
            picture = '<span class="no-avatar">●</span>'
        rows.append(f'<tr><td>{i}</td><td>{picture}{author_html}</td><td>{item["count"]:,}</td>'
                    f'<td>{item["latest"].date().isoformat()}</td></tr>')
    table_rows = "\n".join(rows) or '<tr><td colspan="4">暂无二次开发提交</td></tr>'
    original_name = html.escape(upstream["author"])
    original_username = upstream.get("author_username")
    if original_username:
        author_link = (
            f'<a href="https://github.com/{html.escape(original_username, quote=True)}">'
            f'{original_name}</a>'
        )
    else:
        author_link = original_name
    page = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OnStep 二次开发贡献者</title><style>
:root{color-scheme:light dark}body{margin:0 auto;max-width:1000px;padding:32px;color:#24292f;background:#fff;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif}
h1{font-size:25px}p{color:#57606a;line-height:1.7}table{width:100%;border-collapse:collapse;border:1px solid #d0d7de;border-radius:6px}
th,td{text-align:left;padding:11px 16px;border-bottom:1px solid #d8dee4}th{font-weight:600}a{color:#0969da;text-decoration:none}
a:hover{text-decoration:underline}td:nth-child(2){display:flex;align-items:center;gap:10px}img{border-radius:50%;object-fit:cover}
.no-avatar{display:inline-flex;width:30px;height:30px;border-radius:50%;background:#eaeef2;color:#57606a;align-items:center;justify-content:center}
@media(prefers-color-scheme:dark){body{background:#0d1117;color:#c9d1d9}p{color:#8b949e}table,th,td{border-color:#30363d}a{color:#58a6ff}}
</style></head><body>
<h1>OnStep 二次开发贡献者</h1>
<p>原作者：__ORIGINAL_AUTHOR_LINK__。下列开发者按照独立提交数降序排列，提交 SHA 跨功能分支去重，并排除上游原始历史与机器人提交</p>
<p>统计起点：2026-05-12</p>
<table><thead><tr><th>排名</th><th>开发者</th><th>有效提交</th><th>最近提交</th></tr></thead><tbody>
__ROWS__
</tbody></table><p><a href="./">返回仓库动态统计</a></p></body></html>
""".replace("__ROWS__", table_rows).replace("__ORIGINAL_AUTHOR_LINK__", author_link).replace(
        "统计起点：2026-05-12", f"统计起点：{PROJECT_START_DATE.isoformat()}"
    )
    (OUTPUT_DIR / "contributors.html").write_text(page, encoding="utf-8")


def generate_branch_preview_svg(branches: list[dict], output: Path) -> None:
    """固定分支在 README 表格中展示，这里只预览最近更新的三个其他分支。"""
    other = [x for x in branches if x["branch"] != BASE_BRANCH]
    other.sort(key=lambda x: (-x.get("latest_ts", 0), x["branch"]))
    visible = other[:MAX_BRANCH_PREVIEW]
    count = max(1, len(visible))
    card_y, header_h, row_h, footer_h = 53, 45, 46, 42
    height = card_y + header_h + count * row_h + footer_h + 1
    svg = svg_open(height)
    svg.append(f'<text class="text subtitle" x="0" y="27">自动识别 {len(other)} 个其他分支 · 按最近更新时间排序</text>')
    svg.append(card(.5, card_y + .5, 1118, header_h + count * row_h + footer_h - 1))
    svg.append('<text class="text label" x="28" y="82">分支</text>')
    svg.append('<text class="text label" x="610" y="82">类型</text>')
    svg.append('<text class="text label" x="842" y="82">最近更新</text>')
    svg.append(line(card_y + header_h))
    if visible:
        for i, item in enumerate(visible):
            y = card_y + header_h + i * row_h + 29
            svg.append(svg_link(short_text(item["branch"], 55), item["url"], 28, y))
            svg.append(f'<text class="text muted" x="610" y="{y}">{esc(item["role"])}</text>')
            svg.append(f'<text class="text muted" x="842" y="{y}">{esc(item["latest_date"])}</text>')
            if i + 1 < len(visible):
                svg.append(line(card_y + header_h + (i + 1) * row_h, 26, 1093))
    else:
        svg.append('<text class="text muted" x="28" y="126">暂无其他分支</text>')
    foot = card_y + header_h + count * row_h
    svg.append(line(foot))
    svg.append(f'<text class="text tiny" x="28" y="{foot + 27}">默认显示最近更新的 {min(len(other), MAX_BRANCH_PREVIEW)} 个分支</text>')
    svg.append(svg_link("查看更多分支", "https://leo-john233.github.io/OnStep/", 1090, foot + 27, "rightlink"))
    save_svg(output, svg)


# GitHub Pages 分支切换

def generate_index_html(branches: list[dict]) -> None:
    # 所有分支选择项都来自运行时 Git 自动发现的结果
    options = ['<option value="">全部有效分支</option>']
    for item in branches:
        name = html.escape(item["branch"], quote=True)
        label = html.escape(item["role"], quote=True)
        options.append(f'<option value="{name}">{name} · {label}</option>')
    options_html = "\n".join(options)
    all_data = json.dumps(branches, ensure_ascii=False).replace("<", "\\u003c")
    version = datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
    source = html.escape(repo_url(), quote=True)
    # HTML 中 <img> 对应独立 SVG 输出，无需 JavaScript 框架
    page = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OnStep 仓库动态</title>
<style>
:root{color-scheme:light dark}
body{margin:0;padding:32px;background:#fff;color:#24292f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif}
main{width:min(1120px,100%);margin:0 auto}
h1{font-size:27px;margin:0 0 18px;font-weight:650}
.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}
label{font-weight:600}select{font:inherit;color:inherit;background:#fff;border:1px solid #d0d7de;border-radius:6px;padding:9px 12px;max-width:100%}
.meta{font-size:14px;color:#57606a;margin:0 0 24px;line-height:1.6}
img{display:block;width:100%;height:auto;margin:0 0 28px}
a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}
.footer{padding:6px 0 24px;color:#57606a;font-size:14px}
@media(prefers-color-scheme:dark){body{background:#0d1117;color:#c9d1d9}select{background:#161b22;border-color:#30363d}.meta,.footer{color:#8b949e}a{color:#58a6ff}}
@media(max-width:640px){body{padding:16px}h1{font-size:22px}}
</style>
</head>
<body>
<main>
<h1>OnStep 仓库动态</h1>
<div class="toolbar"><label for="branch">统计范围</label><select id="branch">__OPTIONS__</select></div>
<p class="meta" id="scope"></p>
<img id="recent" src="recent-changes.svg" alt="最近代码修改">
<img id="activity" src="repository-activity.svg" alt="代码活动热力图">
<img id="statistics" src="repository-statistics.svg" alt="仓库统计">
<div class="footer"><a href="contributors.html">查看二次开发贡献者</a> · <a href="__REPO__">返回 GitHub 仓库</a></div>
</main>
<script>
const branchList=__BRANCHES__;
const version='__VERSION__';
const select=document.getElementById('branch');
const scope=document.getElementById('scope');
const recent=document.getElementById('recent');
const activity=document.getElementById('activity');
const statistics=document.getElementById('statistics');
function url(path){return path+'?v='+encodeURIComponent(version)}
function applyBranch(name){
  const item=branchList.find(b=>b.branch===name);
  const prefix=item?'branches/'+item.slug+'/':'';
  select.value=item?item.branch:'';
  recent.src=url(prefix+'recent-changes.svg');
  activity.src=url(prefix+'repository-activity.svg');
  statistics.src=url(prefix+'repository-statistics.svg');
  scope.textContent=item?('当前分支 '+item.branch):('自动统计 '+branchList.length+' 个有效分支');
  const params=new URLSearchParams();
  if(item)params.set('branch',item.branch);
  history.replaceState(null,'',location.pathname+(item?'#'+params.toString():'#scope=all'));
}
const params=new URLSearchParams(location.hash.slice(1));
applyBranch(params.get('branch')||'');
select.addEventListener('change',()=>applyBranch(select.value));
</script>
</body>
</html>
"""
    page = (page.replace("__OPTIONS__", options_html)
            .replace("__REPO__", source)
            .replace("__BRANCHES__", all_data)
            .replace("__VERSION__", version))
    (OUTPUT_DIR / "index.html").write_text(page, encoding="utf-8")
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (OUTPUT_DIR / "branches.json").write_text(
        json.dumps(branches, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    branches = discover_branches()
    print(f"自动发现 {len(branches)} 个有效分支")
    for branch in branches:
        print(branch)
    upstream = upstream_information()
    inherited_shas = inherited_commit_shas()
    recent_histories: dict[str, list[dict]] = {}
    full_histories: dict[str, list[dict]] = {}
    branch_details: list[dict] = []

    for branch in branches:
        ref = branch_ref(branch)
        print(f"读取分支 {branch}")
        recent = load_recent_history(ref)
        full = load_full_history(ref)
        recent_histories[branch] = recent
        full_histories[branch] = full
        latest_raw = git("log", "-1", "--format=%cI", ref).strip()
        try:
            latest_dt = datetime.fromisoformat(latest_raw) if latest_raw else None
        except ValueError:
            latest_dt = None
        branch_details.append({
            "branch": branch, "slug": slug(branch), "role": branch_role(branch),
            "recent_commits": len(last_n_days(recent, RECENT_DAYS)),
            "total_commits": len(full), "url": branch_url(branch),
            "latest_ts": latest_dt.timestamp() if latest_dt else 0,
            "latest_date": latest_dt.date().isoformat() if latest_dt else "未知",
        })
        directory = OUTPUT_DIR / "branches" / slug(branch)
        generate_recent_svg(recent, directory / "recent-changes.svg", branch)
        generate_activity_svg(recent, directory / "repository-activity.svg", branch)
        generate_statistics_svg(full, directory / "repository-statistics.svg", branch, upstream, developer_contributors(full, inherited_shas, upstream["author"]))

    # 只有发布分支的最近修改单独展示
    generate_recent_svg(
        recent_histories[BASE_BRANCH], OUTPUT_DIR / "recent-changes.svg", BASE_BRANCH
    )

    # 排除 Original 及其他配置排除项，汇总时按完整 Commit SHA 去重
    all_recent = combine_histories(list(recent_histories.values()))
    all_full = combine_histories(list(full_histories.values()))
    scope = f"{len(branches)} 个分支"
    generate_activity_svg(all_recent, OUTPUT_DIR / "repository-activity.svg", scope)
    developers = developer_contributors(all_full, inherited_shas, upstream["author"])
    generate_statistics_svg(all_full, OUTPUT_DIR / "repository-statistics.svg", scope, upstream, developers)
    generate_contributors_html(developers, upstream)
    generate_branch_preview_svg(branch_details, OUTPUT_DIR / "branch-preview.svg")
    generate_index_html(branch_details)

    stats = repository_statistics(all_full)
    summary = {
        "scope": "active_branches", "excluded_branches": sorted(EXCLUDED_BRANCHES),
        "branches": branches,
        "refs": {branch: git("rev-parse", branch_ref(branch)).strip()
                 for branch in branches},
        "generated_at": datetime.now(TZ).isoformat(),
        "counting_method": "unique_full_commit_sha_across_active_branches",
        "total_commits": stats["total_commits"],
        "contributors": len(developers),
        "historical_authors": stats["contributors"],
        "maintainer_commits": next((x["count"] for x in developers if x["name"] == MAINTAINER), 0),
        "developers": [{"name": x["name"], "username": x["username"], "commits": x["count"],
                        "last_date": x["latest"].date().isoformat()} for x in developers],
        "activity_last_year": sum(contribution_counts(all_recent).values()),
        "recent_changes_branch": BASE_BRANCH,
        "upstream": upstream,
        "filters": {
            "activity": "排除机器人和只修改 README 或 .github 的提交",
            "statistics": "有效分支全部非机器人提交 按完整 SHA 跨分支去重",
            "developers": f"项目建立于 {PROJECT_START_DATE.isoformat()}，排除 Original 和上游历史 SHA",
        },
    }
    (OUTPUT_DIR / "repository-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"分支累计提交 {stats['total_commits']:,}")
    print(f"二次开发贡献者 {len(developers)}，历史作者 {stats['contributors']}")
    print(f"近一年有效代码提交 {summary['activity_last_year']:,}")
    print(f"生成完成 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
