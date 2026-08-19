from __future__ import annotations

import html
import os
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ============================================================
# 配置
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
ASSETS_DIR = ROOT / "assets"
ACTIVITY_SVG = ASSETS_DIR / "repository-activity.svg"
STATISTICS_SVG = ASSETS_DIR / "repository-statistics.svg"

RECENT_START = "<!-- RECENT_CHANGES:START -->"
RECENT_END = "<!-- RECENT_CHANGES:END -->"

AUTO_COMMIT_MESSAGE = "docs: auto-update repository activity"
RECENT_DAYS = 7
RECENT_HISTORY_DAYS = 370
TOP_CONTRIBUTORS = 6

TZ = ZoneInfo(os.getenv("ACTIVITY_TIMEZONE", "Asia/Shanghai"))

IGNORED_FILES = {
    "README.md",
    "assets/repository-activity.svg",
    "assets/repository-statistics.svg",
    "docs/activity.html",
    "docs/activity-data.json",
}

IGNORED_PREFIXES = (
    ".github/",
)

# 作者名称统一
AUTHOR_ALIASES = {
    "Leo-John": "Leo-John233",
    "Leo·John": "Leo-John233",
    "Leo-John233": "Leo-John233",
}

BOT_AUTHORS = {
    "github-actions[bot]",
}


# ============================================================
# Git / 文本辅助
# ============================================================

def git(*args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            *args,
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    return result.stdout


def should_ignore_file(path: str) -> bool:
    return (
        path in IGNORED_FILES
        or any(
            path.startswith(prefix)
            for prefix in IGNORED_PREFIXES
        )
    )


def canonical_author(author: str) -> str:
    author = author.strip()

    return AUTHOR_ALIASES.get(
        author,
        author,
    )


def format_author(author: str) -> str:
    # 使用 non-breaking hyphen
    # 防止 README 表格中的名字自动换行
    return canonical_author(
        author
    ).replace(
        "-",
        "\u2011",
    )


def markdown_escape(text: str) -> str:
    return (
        text
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def commit_url(sha: str) -> str:
    repository = os.getenv(
        "GITHUB_REPOSITORY",
        "",
    )

    if not repository:
        return ""

    return (
        f"https://github.com/"
        f"{repository}/commit/{sha}"
    )


def parse_log(raw: str) -> list[dict]:
    """
    解析 git log

    字段分隔符：
    \\x1f

    Commit 分隔符：
    \\x1e
    """

    commits: list[dict] = []

    for record in raw.split("\x1e"):

        record = record.strip()

        if not record:
            continue

        parts = record.split(
            "\x1f",
            4,
        )

        if len(parts) != 5:
            continue

        (
            sha,
            author,
            email_address,
            iso_time,
            subject,
        ) = parts

        try:

            local_time = (
                datetime
                .fromisoformat(
                    iso_time.strip()
                )
                .astimezone(TZ)
            )

        except ValueError:
            continue

        commits.append(
            {
                "sha": sha.strip(),
                "author": author.strip(),
                "email": email_address.strip(),
                "subject": subject.strip(),
                "date": (
                    local_time
                    .date()
                    .isoformat()
                ),
            }
        )

    return commits


# ============================================================
# Commit 文件范围
# ============================================================

def get_commit_files(
    sha: str,
) -> list[str]:

    raw = git(
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        "-z",
        sha,
    )

    return [
        path.strip()
        for path in raw.split("\0")
        if (
            path.strip()
            and not should_ignore_file(
                path.strip()
            )
        )
    ]


def scope_of(
    path: str,
) -> str:

    parts = (
        path
        .replace("\\", "/")
        .split("/")
    )

    if (
        parts
        and parts[0] == "原始固件"
        and len(parts) >= 2
    ):
        return parts[1]

    if parts:
        return parts[0]

    return "-"


def summarize_scope(
    files: list[str],
) -> str:

    if not files:
        return "-"

    # 单个文件直接显示路径
    if len(files) == 1:

        path = (
            files[0]
            .replace("\\", "/")
        )

        if path.startswith(
            "原始固件/"
        ):
            return path[
                len("原始固件/"):
            ]

        return path

    scopes: list[str] = []

    for path in files:

        scope = scope_of(
            path
        )

        if scope not in scopes:
            scopes.append(
                scope
            )

    if len(scopes) == 1:
        return scopes[0]

    if len(scopes) == 2:
        return (
            f"{scopes[0]} + "
            f"{scopes[1]}"
        )

    return "多个目录"


# ============================================================
# 最近一年历史
# ============================================================

def load_recent_history() -> list[dict]:
    """
    最近 7 天代码表格和最近一年 Contribution Graph 使用

    这里只读取约一年历史，并检查每个 Commit 修改的文件

    排除：
    README
    自动 SVG
    .github
    其他不参与代码统计的文件
    """

    raw = git(
        "log",
        f"--since={RECENT_HISTORY_DAYS} days ago",
        (
            "--pretty=format:"
            "%H%x1f"
            "%aN%x1f"
            "%aE%x1f"
            "%aI%x1f"
            "%s%x1e"
        ),
    )

    result: list[dict] = []

    for commit in parse_log(
        raw
    ):

        # 排除自动生成 Activity 的 Commit
        if (
            commit["subject"]
            == AUTO_COMMIT_MESSAGE
        ):
            continue

        files = get_commit_files(
            commit["sha"]
        )

        # 如果 Commit 只修改被忽略文件
        # 则不计入有效代码提交
        if not files:
            continue

        result.append(
            {
                **commit,
                "short_sha": (
                    commit["sha"][:7]
                ),
                "scope": (
                    summarize_scope(
                        files
                    )
                ),
                "file_count": len(
                    files
                ),
                "url": (
                    commit_url(
                        commit["sha"]
                    )
                ),
            }
        )

    return result


# ============================================================
# 完整 Git 历史
# ============================================================

def load_full_history() -> list[dict]:
    """
    Repository Statistics 使用当前分支完整可达历史

    与最近一年统计不同：

    这里不限制时间

    同时不会对数千条历史逐条执行 diff-tree

    因此即使仓库存在几千个 Commit
    也只需要一次 git log
    """

    raw = git(
        "log",
        (
            "--pretty=format:"
            "%H%x1f"
            "%aN%x1f"
            "%aE%x1f"
            "%aI%x1f"
            "%s%x1e"
        ),
    )

    return parse_log(
        raw
    )


# ============================================================
# README 最近代码修改
# ============================================================

def get_recent_commits(
    history: list[dict],
) -> list[dict]:

    today = datetime.now(
        TZ
    ).date()

    start = (
        today
        - timedelta(
            days=RECENT_DAYS - 1
        )
    )

    return [
        commit
        for commit in history
        if (
            start
            <= date.fromisoformat(
                commit["date"]
            )
            <= today
        )
    ]


def build_recent_changes(
    history: list[dict],
) -> str:

    commits = get_recent_commits(
        history
    )

    lines = [
        (
            f"最近 **{RECENT_DAYS} 天**"
            f"代码提交 **{len(commits)}** 次"
        ),
        "",
        "| 日期 | 修改者 | 修改内容 | 范围 |",
        "| :---: | :--- | :--- | :--- |",
    ]

    if not commits:

        lines.append(
            "| - | - | 暂无代码提交 | - |"
        )

        return "\n".join(
            lines
        )

    for commit in commits:

        commit_date = (
            date.fromisoformat(
                commit["date"]
            )
        )

        display_date = (
            f"{commit_date.month}/"
            f"{commit_date.day}"
        )

        author = markdown_escape(
            format_author(
                commit["author"]
            )
        )

        subject = markdown_escape(
            commit["subject"]
        )

        short_sha = (
            commit["short_sha"]
        )

        if commit["url"]:

            subject_text = (
                f"[{subject}]"
                f"({commit['url']}) "
                f"`{short_sha}`"
            )

        else:

            subject_text = (
                f"{subject} "
                f"`{short_sha}`"
            )

        scope = (
            commit["scope"]
            .replace(
                "`",
                "ˋ",
            )
        )

        if (
            commit["file_count"]
            > 1
        ):

            impact = (
                f"`{scope}` · "
                f"{commit['file_count']}"
            )

        else:

            impact = (
                f"`{scope}`"
            )

        lines.append(
            f"| {display_date} "
            f"| **{author}** "
            f"| {subject_text} "
            f"| {impact} |"
        )

    return "\n".join(
        lines
    )


def update_readme(
    history: list[dict],
) -> None:

    if not README.exists():
        raise FileNotFoundError(
            "README.md 不存在"
        )

    text = README.read_text(
        encoding="utf-8"
    )

    if (
        RECENT_START not in text
        or RECENT_END not in text
    ):

        raise RuntimeError(
            "README 中缺少 "
            "RECENT_CHANGES 标记"
        )

    before, rest = text.split(
        RECENT_START,
        1,
    )

    _, after = rest.split(
        RECENT_END,
        1,
    )

    README.write_text(
        (
            before
            + RECENT_START
            + "\n"
            + build_recent_changes(
                history
            )
            + "\n"
            + RECENT_END
            + after
        ),
        encoding="utf-8",
    )


# ============================================================
# 最近一年 Contribution 数据
# ============================================================

def contribution_counts(
    history: list[dict],
) -> Counter:

    today = datetime.now(
        TZ
    ).date()

    first_day = (
        today
        - timedelta(
            days=364
        )
    )

    counts: Counter = Counter()

    for commit in history:

        commit_date = (
            date.fromisoformat(
                commit["date"]
            )
        )

        if (
            first_day
            <= commit_date
            <= today
        ):

            counts[
                commit["date"]
            ] += 1

    return counts


def contribution_level(
    count: int,
) -> int:

    if count == 0:
        return 0

    if count == 1:
        return 1

    if count <= 3:
        return 2

    if count <= 6:
        return 3

    return 4


# ============================================================
# GitHub Contribution Graph CSS
# ============================================================

ACTIVITY_STYLE = """
.card{
    fill:#ffffff;
    stroke:#d0d7de;
    stroke-width:1;
}

.text{
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Helvetica,
        Arial,
        sans-serif;
}

.title{
    fill:#24292f;
    font-size:22px;
    font-weight:400;
}

.month,
.weekday{
    fill:#24292f;
    font-size:14px;
    font-weight:400;
}

.footer{
    fill:#57606a;
    font-size:14px;
    font-weight:400;
}

.level-0{
    fill:#ebedf0;
    stroke:rgba(27,31,35,.06);
    stroke-width:1;
}

.level-1{
    fill:#9be9a8;
}

.level-2{
    fill:#40c463;
}

.level-3{
    fill:#30a14e;
}

.level-4{
    fill:#216e39;
}

@media(prefers-color-scheme:dark){

    .card{
        fill:#0d1117;
        stroke:#30363d;
    }

    .title,
    .month,
    .weekday{
        fill:#c9d1d9;
    }

    .footer{
        fill:#8b949e;
    }

    .level-0{
        fill:#161b22;
        stroke:#1b1f23;
    }

    .level-1{
        fill:#0e4429;
    }

    .level-2{
        fill:#006d32;
    }

    .level-3{
        fill:#26a641;
    }

    .level-4{
        fill:#39d353;
    }
}
"""


# ============================================================
# GitHub 风格最近一年 Contribution Graph
# ============================================================

def generate_activity_svg(
    history: list[dict],
) -> None:

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    counts = contribution_counts(
        history
    )

    total = sum(
        counts.values()
    )

    today = datetime.now(
        TZ
    ).date()

    first_day = (
        today
        - timedelta(
            days=364
        )
    )

    # --------------------------------------------------------
    # GitHub 原生比例
    # --------------------------------------------------------

    width = 1120
    height = 278

    card_y = 44
    card_width = 1119
    card_height = 233

    cell = 14
    gap = 5
    step = cell + gap

    grid_left = 80
    grid_top = 94

    month_y = 84

    footer_y = 253
    legend_x = 872

    # --------------------------------------------------------
    # 计算网格起始星期日
    # --------------------------------------------------------

    offset_to_sunday = (
        first_day.weekday() + 1
    ) % 7

    grid_start = (
        first_day
        - timedelta(
            days=offset_to_sunday
        )
    )

    grid_days = (
        today
        - grid_start
    ).days + 1

    # --------------------------------------------------------
    # SVG
    # --------------------------------------------------------

    svg: list[str] = [

        (
            '<svg '
            'xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}" '
            'preserveAspectRatio="xMinYMin meet" '
            'role="img">'
        ),

        (
            "<style>"
            + ACTIVITY_STYLE
            + "</style>"
        ),

        (
            '<text '
            'class="text title" '
            'x="0" '
            'y="26">'
            f"{total} contributions in the last year"
            "</text>"
        ),

        (
            '<rect '
            'class="card" '
            'x="0.5" '
            f'y="{card_y + 0.5}" '
            f'width="{card_width - 1}" '
            f'height="{card_height - 1}" '
            'rx="6" '
            'ry="6"/>'
        ),
    ]

    # --------------------------------------------------------
    # 月份
    # --------------------------------------------------------

    previous_month = None
    previous_x = -100

    for week in range(
        53
    ):

        week_date = (
            grid_start
            + timedelta(
                days=week * 7 + 3
            )
        )

        if (
            week_date.month
            == previous_month
        ):
            continue

        x = (
            grid_left
            + week * step
        )

        # 防止月份文字重叠
        if (
            x - previous_x
            < 45
        ):
            continue

        previous_month = (
            week_date.month
        )

        previous_x = x

        month_name = (
            week_date.strftime(
                "%b"
            )
        )

        svg.append(
            (
                '<text '
                'class="text month" '
                f'x="{x}" '
                f'y="{month_y}">'
                f"{month_name}"
                "</text>"
            )
        )

    # --------------------------------------------------------
    # 星期
    # --------------------------------------------------------

    weekday_labels = {
        1: "Mon",
        3: "Wed",
        5: "Fri",
    }

    for (
        row,
        label,
    ) in weekday_labels.items():

        y = (
            grid_top
            + row * step
            + 12
        )

        svg.append(
            (
                '<text '
                'class="text weekday" '
                'x="35" '
                f'y="{y}">'
                f"{label}"
                "</text>"
            )
        )

    # --------------------------------------------------------
    # Contribution 方格
    # --------------------------------------------------------

    for offset in range(
        grid_days
    ):

        current = (
            grid_start
            + timedelta(
                days=offset
            )
        )

        if (
            current < first_day
            or current > today
        ):
            continue

        week = (
            offset // 7
        )

        if week >= 53:
            continue

        # Sunday = 0
        row = (
            current.weekday() + 1
        ) % 7

        x = (
            grid_left
            + week * step
        )

        y = (
            grid_top
            + row * step
        )

        date_string = (
            current.isoformat()
        )

        count = counts.get(
            date_string,
            0,
        )

        level = (
            contribution_level(
                count
            )
        )

        tooltip = html.escape(
            (
                f"{count} "
                f"contribution"
                f"{'s' if count != 1 else ''} "
                f"on {date_string}"
            )
        )

        svg.append(
            (
                '<rect '
                f'class="level-{level}" '
                f'x="{x}" '
                f'y="{y}" '
                f'width="{cell}" '
                f'height="{cell}" '
                'rx="2" '
                'ry="2">'
                f"<title>{tooltip}</title>"
                "</rect>"
            )
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    svg.append(
        (
            '<text '
            'class="text footer" '
            'x="60" '
            f'y="{footer_y}">'
            "Learn how we count contributions"
            "</text>"
        )
    )

    svg.append(
        (
            '<text '
            'class="text footer" '
            f'x="{legend_x}" '
            f'y="{footer_y}">'
            "Less"
            "</text>"
        )
    )

    # --------------------------------------------------------
    # Less -> More 图例
    # --------------------------------------------------------

    for index in range(
        5
    ):

        x = (
            legend_x
            + 40
            + index * step
        )

        svg.append(
            (
                '<rect '
                f'class="level-{index}" '
                f'x="{x}" '
                f'y="{footer_y - 13}" '
                f'width="{cell}" '
                f'height="{cell}" '
                'rx="2" '
                'ry="2"/>'
            )
        )

    svg.append(
        (
            '<text '
            'class="text footer" '
            f'x="{legend_x + 140}" '
            f'y="{footer_y}">'
            "More"
            "</text>"
        )
    )

    svg.append(
        "</svg>"
    )

    ACTIVITY_SVG.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )


# ============================================================
# 完整历史 Repository Statistics
# ============================================================

def repository_statistics(
    full_history: list[dict],
) -> dict:

    contributors: Counter = Counter()

    for commit in full_history:

        author = canonical_author(
            commit["author"]
        )

        # Contributors 中不显示 GitHub Actions Bot
        if author in BOT_AUTHORS:
            continue

        if (
            commit["subject"]
            == AUTO_COMMIT_MESSAGE
        ):
            continue

        contributors[
            author
        ] += 1

    if full_history:

        first_date = min(
            date.fromisoformat(
                commit["date"]
            )
            for commit in full_history
        )

        last_date = max(
            date.fromisoformat(
                commit["date"]
            )
            for commit in full_history
        )

    else:

        first_date = (
            datetime.now(
                TZ
            ).date()
        )

        last_date = (
            first_date
        )

    return {

        # 完整当前分支 Git 历史
        "total_commits": len(
            full_history
        ),

        # 排除自动 Bot 后的 Commit 作者数量
        "contributors": len(
            contributors
        ),

        "first_date": (
            first_date
        ),

        "last_date": (
            last_date
        ),

        "top": (
            contributors
            .most_common(
                TOP_CONTRIBUTORS
            )
        ),
    }


# ============================================================
# Repository Statistics CSS
# ============================================================

STATISTICS_STYLE = """
.card{
    fill:#ffffff;
    stroke:#d0d7de;
    stroke-width:1;
}

.text{
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Helvetica,
        Arial,
        sans-serif;
}

.title{
    fill:#24292f;
    font-size:22px;
    font-weight:400;
}

.metric-value{
    fill:#24292f;
    font-size:22px;
    font-weight:600;
}

.metric-label{
    fill:#57606a;
    font-size:14px;
    font-weight:400;
}

.section-title{
    fill:#24292f;
    font-size:16px;
    font-weight:600;
}

.contributor-name{
    fill:#0969da;
    font-size:15px;
    font-weight:600;
}

.contributor-count{
    fill:#57606a;
    font-size:14px;
    font-weight:400;
}

.footer{
    fill:#57606a;
    font-size:13px;
    font-weight:400;
}

.divider{
    stroke:#d8dee4;
    stroke-width:1;
}

@media(prefers-color-scheme:dark){

    .card{
        fill:#0d1117;
        stroke:#30363d;
    }

    .title,
    .metric-value,
    .section-title{
        fill:#c9d1d9;
    }

    .metric-label,
    .contributor-count,
    .footer{
        fill:#8b949e;
    }

    .contributor-name{
        fill:#58a6ff;
    }

    .divider{
        stroke:#21262d;
    }
}
"""


# ============================================================
# GitHub 风格 Repository Statistics SVG
# ============================================================

def generate_statistics_svg(
    full_history: list[dict],
) -> None:

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stats = repository_statistics(
        full_history
    )

    top = stats[
        "top"
    ]

    # --------------------------------------------------------
    # GitHub 风格尺寸
    # --------------------------------------------------------

    width = 1120

    card_y = 44

    metric_height = 92

    contributors_title_height = 48

    row_height = 42

    footer_height = 42

    row_count = max(
        1,
        len(top),
    )

    card_height = (
        metric_height
        + contributors_title_height
        + row_count * row_height
        + footer_height
    )

    height = (
        card_y
        + card_height
        + 1
    )

    divider_y = (
        card_y
        + metric_height
    )

    contributors_title_y = (
        divider_y
        + 30
    )

    rows_top = (
        divider_y
        + contributors_title_height
    )

    footer_y = (
        rows_top
        + row_count * row_height
    )

    # --------------------------------------------------------
    # 顶部三个指标
    # --------------------------------------------------------

    metrics = [

        (
            f"{stats['total_commits']:,}",
            "Commits",
        ),

        (
            f"{stats['contributors']:,}",
            "Contributors",
        ),

        (
            f"Since {stats['first_date'].year}",
            "Repository history",
        ),
    ]

    svg: list[str] = [

        (
            '<svg '
            'xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}" '
            'preserveAspectRatio="xMinYMin meet" '
            'role="img">'
        ),

        (
            "<style>"
            + STATISTICS_STYLE
            + "</style>"
        ),

        (
            '<text '
            'class="text title" '
            'x="0" '
            'y="26">'
            "Repository statistics"
            "</text>"
        ),

        (
            '<rect '
            'class="card" '
            'x="0.5" '
            f'y="{card_y + 0.5}" '
            'width="1118" '
            f'height="{card_height - 1}" '
            'rx="6" '
            'ry="6"/>'
        ),
    ]

    # --------------------------------------------------------
    # 统计值
    # --------------------------------------------------------

    metric_centers = [
        186,
        560,
        934,
    ]

    for (
        x,
        (
            value,
            label,
        ),
    ) in zip(
        metric_centers,
        metrics,
    ):

        svg.append(
            (
                '<text '
                'class="text metric-value" '
                f'x="{x}" '
                f'y="{card_y + 38}" '
                'text-anchor="middle">'
                f"{html.escape(value)}"
                "</text>"
            )
        )

        svg.append(
            (
                '<text '
                'class="text metric-label" '
                f'x="{x}" '
                f'y="{card_y + 64}" '
                'text-anchor="middle">'
                f"{html.escape(label)}"
                "</text>"
            )
        )

    # --------------------------------------------------------
    # 三个指标之间的分隔线
    # --------------------------------------------------------

    for x in (
        373,
        747,
    ):

        svg.append(
            (
                '<line '
                'class="divider" '
                f'x1="{x}" '
                f'y1="{card_y + 18}" '
                f'x2="{x}" '
                f'y2="{card_y + 74}"/>'
            )
        )

    # --------------------------------------------------------
    # Contributors 区域
    # --------------------------------------------------------

    svg.append(
        (
            '<line '
            'class="divider" '
            'x1="0" '
            f'y1="{divider_y}" '
            'x2="1119" '
            f'y2="{divider_y}"/>'
        )
    )

    svg.append(
        (
            '<text '
            'class="text section-title" '
            'x="28" '
            f'y="{contributors_title_y}">'
            "Top contributors"
            "</text>"
        )
    )

    if top:

        for (
            index,
            (
                author,
                count,
            ),
        ) in enumerate(
            top
        ):

            row_top = (
                rows_top
                + index * row_height
            )

            baseline = (
                row_top
                + 27
            )

            if count == 1:

                count_text = (
                    "1 commit"
                )

            else:

                count_text = (
                    f"{count:,} commits"
                )

            svg.append(
                (
                    '<text '
                    'class="text contributor-name" '
                    'x="28" '
                    f'y="{baseline}">'
                    f"{html.escape(author)}"
                    "</text>"
                )
            )

            svg.append(
                (
                    '<text '
                    'class="text contributor-count" '
                    'x="1090" '
                    f'y="{baseline}" '
                    'text-anchor="end">'
                    f"{count_text}"
                    "</text>"
                )
            )

            # 行分隔线
            if (
                index
                < len(top) - 1
            ):

                line_y = (
                    row_top
                    + row_height
                )

                svg.append(
                    (
                        '<line '
                        'class="divider" '
                        'x1="28" '
                        f'y1="{line_y}" '
                        'x2="1090" '
                        f'y2="{line_y}"/>'
                    )
                )

    else:

        svg.append(
            (
                '<text '
                'class="text contributor-count" '
                'x="28" '
                f'y="{rows_top + 27}">'
                "No contributor data"
                "</text>"
            )
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    svg.append(
        (
            '<line '
            'class="divider" '
            'x1="0" '
            f'y1="{footer_y}" '
            'x2="1119" '
            f'y2="{footer_y}"/>'
        )
    )

    date_range = (
        f"{stats['first_date'].isoformat()} "
        f"– "
        f"{stats['last_date'].isoformat()}"
    )

    svg.append(
        (
            '<text '
            'class="text footer" '
            'x="28" '
            f'y="{footer_y + 27}">'
            "Based on the complete Git history of this branch"
            "</text>"
        )
    )

    svg.append(
        (
            '<text '
            'class="text footer" '
            'x="1090" '
            f'y="{footer_y + 27}" '
            'text-anchor="end">'
            f"{html.escape(date_range)}"
            "</text>"
        )
    )

    svg.append(
        "</svg>"
    )

    STATISTICS_SVG.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    print(
        "读取最近一年有效代码历史"
    )

    recent_history = (
        load_recent_history()
    )

    print(
        "最近一年有效代码提交 "
        f"{len(recent_history)}"
    )

    print(
        "读取完整 Git 历史"
    )

    full_history = (
        load_full_history()
    )

    print(
        "当前分支完整历史提交 "
        f"{len(full_history)}"
    )

    print(
        "更新 README"
    )

    update_readme(
        recent_history
    )

    print(
        "生成 Repository Activity"
    )

    generate_activity_svg(
        recent_history
    )

    print(
        "生成 Repository Statistics"
    )

    generate_statistics_svg(
        full_history
    )

    print(
        "完成"
    )


if __name__ == "__main__":
    main()
