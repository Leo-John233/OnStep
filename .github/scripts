from __future__ import annotations

import html
import os
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


# ============================================================
# 基础配置
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

README = ROOT / "README.md"

ASSETS_DIR = ROOT / "assets"

SVG_FILE = ASSETS_DIR / "repository-activity.svg"


RECENT_START = "<!-- RECENT_CHANGES:START -->"
RECENT_END = "<!-- RECENT_CHANGES:END -->"


AUTO_COMMIT_MESSAGE = "docs: auto-update repository activity"


# README 固定显示最近 7 天
RECENT_DAYS = 7


# 时区
TIMEZONE_NAME = os.getenv(
    "ACTIVITY_TIMEZONE",
    "Asia/Shanghai",
)

TZ = ZoneInfo(TIMEZONE_NAME)


# ============================================================
# 不参与代码统计的内容
# ============================================================

IGNORED_FILES = {
    "README.md",
    "assets/repository-activity.svg",
    "docs/activity.html",
    "docs/activity-data.json",
}


IGNORED_PREFIXES = (
    ".github/",
)


# ============================================================
# 作者名称统一
# ============================================================

AUTHOR_ALIASES = {
    "Leo-John": "Leo-John233",
}


# ============================================================
# Git
# ============================================================

def git(*args: str) -> str:
    """执行 Git 命令并正常显示中文路径"""

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


# ============================================================
# 文件过滤
# ============================================================

def should_ignore_file(file_path: str) -> bool:

    if file_path in IGNORED_FILES:
        return True

    return any(
        file_path.startswith(prefix)
        for prefix in IGNORED_PREFIXES
    )


# ============================================================
# Markdown 转义
# ============================================================

def markdown_escape(text: str) -> str:

    return (
        text
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


# ============================================================
# 作者显示
# ============================================================

def format_author(author: str) -> str:

    author = AUTHOR_ALIASES.get(
        author,
        author,
    )

    # 使用 non-breaking hyphen
    # 防止 Leo-John233 被 GitHub 拆成两行
    return author.replace(
        "-",
        "\u2011",
    )


# ============================================================
# Commit URL
# ============================================================

def get_commit_url(sha: str) -> str:

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


# ============================================================
# 获取 Commit 修改文件
# ============================================================

def get_commit_files(sha: str) -> list[str]:

    raw = git(
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        "-z",
        sha,
    )

    files: list[str] = []

    for file_path in raw.split("\0"):

        file_path = file_path.strip()

        if not file_path:
            continue

        if should_ignore_file(file_path):
            continue

        files.append(file_path)

    return files


# ============================================================
# 路径压缩
# ============================================================

def get_scope(file_path: str) -> str:

    parts = (
        file_path
        .replace("\\", "/")
        .split("/")
    )

    if not parts:
        return "-"

    # 原始固件/OnStepX/... -> OnStepX
    if (
        parts[0] == "原始固件"
        and len(parts) >= 2
    ):
        return parts[1]

    return parts[0]


def summarize_scope(files: list[str]) -> str:

    if not files:
        return "-"

    # --------------------------------------------------------
    # 单个文件
    # --------------------------------------------------------

    if len(files) == 1:

        path = files[0].replace(
            "\\",
            "/",
        )

        if path.startswith(
            "原始固件/"
        ):
            path = path[
                len("原始固件/"):
            ]

        return path

    # --------------------------------------------------------
    # 多个文件
    # --------------------------------------------------------

    scopes: list[str] = []

    for file_path in files:

        scope = get_scope(
            file_path
        )

        if scope not in scopes:
            scopes.append(scope)

    if len(scopes) == 1:
        return scopes[0]

    if len(scopes) == 2:
        return (
            f"{scopes[0]} + "
            f"{scopes[1]}"
        )

    return "多个目录"


# ============================================================
# 读取过去一年 Git 历史
# ============================================================

def load_history() -> list[dict]:

    raw = git(
        "log",
        "--since=370 days ago",
        "--pretty=format:%H%x1f%aN%x1f%aI%x1f%s",
    )

    commits: list[dict] = []

    for line in raw.splitlines():

        parts = line.split(
            "\x1f",
            3,
        )

        if len(parts) != 4:
            continue

        sha, author, iso_time, subject = parts

        sha = sha.strip()
        author = author.strip()
        subject = subject.strip()

        # ----------------------------------------------------
        # 排除自动 Commit
        # ----------------------------------------------------

        if subject == AUTO_COMMIT_MESSAGE:
            continue

        # ----------------------------------------------------
        # 修改文件
        # ----------------------------------------------------

        files = get_commit_files(
            sha
        )

        if not files:
            continue

        # ----------------------------------------------------
        # 时间
        # ----------------------------------------------------

        try:

            commit_time = datetime.fromisoformat(
                iso_time.strip()
            )

        except ValueError:
            continue

        commit_time = commit_time.astimezone(
            TZ
        )

        commits.append(
            {
                "sha": sha,
                "short_sha": sha[:7],
                "author": author,
                "subject": subject,
                "date": (
                    commit_time
                    .date()
                    .isoformat()
                ),
                "scope": summarize_scope(
                    files
                ),
                "file_count": len(
                    files
                ),
                "url": get_commit_url(
                    sha
                ),
            }
        )

    return commits


# ============================================================
# 最近 7 天
# ============================================================

def get_recent_commits(
    history: list[dict],
) -> list[dict]:

    today = datetime.now(
        TZ
    ).date()

    start_date = (
        today
        - timedelta(
            days=RECENT_DAYS - 1
        )
    )

    result: list[dict] = []

    for commit in history:

        commit_date = date.fromisoformat(
            commit["date"]
        )

        if (
            start_date
            <= commit_date
            <= today
        ):
            result.append(
                commit
            )

    return result


# ============================================================
# README 最近代码修改
# ============================================================

def build_recent_changes(
    history: list[dict],
) -> str:

    commits = get_recent_commits(
        history
    )

    # 不加句号、逗号等多余标点
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

        commit_date = date.fromisoformat(
            commit["date"]
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

        short_sha = commit[
            "short_sha"
        ]

        url = commit[
            "url"
        ]

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        if url:

            subject_text = (
                f"[{subject}]"
                f"({url}) "
                f"`{short_sha}`"
            )

        else:

            subject_text = (
                f"{subject} "
                f"`{short_sha}`"
            )

        # ----------------------------------------------------
        # 影响范围
        # ----------------------------------------------------

        scope = (
            commit["scope"]
            .replace(
                "`",
                "ˋ",
            )
        )

        file_count = commit[
            "file_count"
        ]

        if file_count > 1:

            impact = (
                f"`{scope}` · "
                f"{file_count}"
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


# ============================================================
# 更新 README
# ============================================================

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

    content = build_recent_changes(
        history
    )

    new_text = (
        before
        + RECENT_START
        + "\n"
        + content
        + "\n"
        + RECENT_END
        + after
    )

    README.write_text(
        new_text,
        encoding="utf-8",
    )


# ============================================================
# Contribution 数据
# ============================================================

def get_contribution_counts(
    history: list[dict],
) -> Counter:

    today = datetime.now(
        TZ
    ).date()

    first_day = (
        today
        - timedelta(days=364)
    )

    counts: Counter = Counter()

    for commit in history:

        commit_date = date.fromisoformat(
            commit["date"]
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


# ============================================================
# GitHub 颜色等级
# ============================================================

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
# GitHub 原生比例 Contribution Graph
# ============================================================

def generate_svg(
    history: list[dict],
) -> None:

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    counts = get_contribution_counts(
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
        - timedelta(days=364)
    )

    # ========================================================
    # GitHub 原生布局参数
    #
    # 这些参数按照用户提供的 GitHub 原生截图比例重新计算
    # ========================================================

    WIDTH = 1120
    HEIGHT = 278

    # --------------------------------------------------------
    # 标题
    # --------------------------------------------------------

    TITLE_X = 0
    TITLE_Y = 26

    # --------------------------------------------------------
    # 外框
    # --------------------------------------------------------

    CARD_X = 0
    CARD_Y = 44

    CARD_WIDTH = 1119
    CARD_HEIGHT = 233

    # --------------------------------------------------------
    # Contribution Grid
    #
    # 53 周
    # 7 行
    #
    # 每列：
    # 14 px 方格
    # 5 px 间隔
    # 总步长 19 px
    #
    # 53 × 19 ≈ 1007 px
    #
    # 与 GitHub 原生截图的网格宽度基本一致
    # --------------------------------------------------------

    CELL = 14
    GAP = 5
    STEP = CELL + GAP

    GRID_LEFT = 80
    GRID_TOP = 94

    MONTH_Y = 84

    FOOTER_Y = 253

    LEGEND_X = 872


    # ========================================================
    # 日期网格起点
    # ========================================================

    # Sunday = 一周第一行
    offset_to_sunday = (
        first_day.weekday() + 1
    ) % 7

    grid_start = (
        first_day
        - timedelta(
            days=offset_to_sunday
        )
    )

    total_grid_days = (
        today
        - grid_start
    ).days + 1


    # ========================================================
    # SVG
    # ========================================================

    svg: list[str] = [

        (
            '<svg '
            'xmlns="http://www.w3.org/2000/svg" '
            f'width="{WIDTH}" '
            f'height="{HEIGHT}" '
            f'viewBox="0 0 {WIDTH} {HEIGHT}" '
            'preserveAspectRatio="xMinYMin meet" '
            'role="img">'
        ),

        "<style>",

        """
        .card {
            fill: #ffffff;
            stroke: #d0d7de;
            stroke-width: 1;
        }

        .text {
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Helvetica,
                Arial,
                sans-serif;
        }

        .title {
            fill: #24292f;
            font-size: 22px;
            font-weight: 400;
        }

        .month {
            fill: #24292f;
            font-size: 14px;
            font-weight: 400;
        }

        .weekday {
            fill: #24292f;
            font-size: 14px;
            font-weight: 400;
        }

        .footer {
            fill: #57606a;
            font-size: 14px;
            font-weight: 400;
        }

        .level-0 {
            fill: #ebedf0;
            stroke: rgba(27, 31, 35, 0.06);
            stroke-width: 1;
        }

        .level-1 {
            fill: #9be9a8;
        }

        .level-2 {
            fill: #40c463;
        }

        .level-3 {
            fill: #30a14e;
        }

        .level-4 {
            fill: #216e39;
        }


        @media (prefers-color-scheme: dark) {

            .card {
                fill: #0d1117;
                stroke: #30363d;
            }

            .title,
            .month,
            .weekday {
                fill: #c9d1d9;
            }

            .footer {
                fill: #8b949e;
            }

            .level-0 {
                fill: #161b22;
                stroke: #1b1f23;
            }

            .level-1 {
                fill: #0e4429;
            }

            .level-2 {
                fill: #006d32;
            }

            .level-3 {
                fill: #26a641;
            }

            .level-4 {
                fill: #39d353;
            }
        }
        """,

        "</style>",


        # ====================================================
        # 标题
        #
        # 与 GitHub 原生一致
        # 位于 Contribution 卡片外部
        # ====================================================

        (
            '<text '
            'class="text title" '
            f'x="{TITLE_X}" '
            f'y="{TITLE_Y}">'
            f"{total} contributions in the last year"
            "</text>"
        ),


        # ====================================================
        # 外框
        # ====================================================

        (
            '<rect '
            'class="card" '
            f'x="{CARD_X + 0.5}" '
            f'y="{CARD_Y + 0.5}" '
            f'width="{CARD_WIDTH - 1}" '
            f'height="{CARD_HEIGHT - 1}" '
            'rx="6" '
            'ry="6"/>'
        ),
    ]


    # ========================================================
    # 月份
    # ========================================================

    previous_month = None
    previous_x = -100

    # 53 周
    for week in range(53):

        week_date = (
            grid_start
            + timedelta(
                days=week * 7 + 3
            )
        )

        month = week_date.month

        if month == previous_month:
            continue

        x = (
            GRID_LEFT
            + week * STEP
        )

        # 防止月标签重叠
        if (
            x - previous_x
            < 45
        ):
            continue

        previous_month = month
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
                f'y="{MONTH_Y}">'
                f"{month_name}"
                "</text>"
            )
        )


    # ========================================================
    # 星期标签
    # ========================================================

    weekday_labels = {
        1: "Mon",
        3: "Wed",
        5: "Fri",
    }

    for row, label in (
        weekday_labels.items()
    ):

        y = (
            GRID_TOP
            + row * STEP
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


    # ========================================================
    # 365 天 Contribution 方格
    # ========================================================

    for day_offset in range(
        total_grid_days
    ):

        current_day = (
            grid_start
            + timedelta(
                days=day_offset
            )
        )

        if current_day < first_day:
            continue

        if current_day > today:
            continue

        week = day_offset // 7

        if week >= 53:
            continue

        # Sunday = 0
        row = (
            current_day.weekday() + 1
        ) % 7

        x = (
            GRID_LEFT
            + week * STEP
        )

        y = (
            GRID_TOP
            + row * STEP
        )

        date_string = (
            current_day.isoformat()
        )

        count = counts.get(
            date_string,
            0,
        )

        level = contribution_level(
            count
        )

        if count == 1:

            tooltip = (
                f"1 contribution "
                f"on {date_string}"
            )

        else:

            tooltip = (
                f"{count} contributions "
                f"on {date_string}"
            )

        tooltip = html.escape(
            tooltip
        )

        svg.append(
            (
                '<rect '
                f'class="level-{level}" '
                f'x="{x}" '
                f'y="{y}" '
                f'width="{CELL}" '
                f'height="{CELL}" '
                'rx="2" '
                'ry="2">'
                f"<title>{tooltip}</title>"
                "</rect>"
            )
        )


    # ========================================================
    # GitHub 原生左下文本
    # ========================================================

    svg.append(
        (
            '<text '
            'class="text footer" '
            'x="60" '
            f'y="{FOOTER_Y}">'
            "Learn how we count contributions"
            "</text>"
        )
    )


    # ========================================================
    # Less
    # ========================================================

    svg.append(
        (
            '<text '
            'class="text footer" '
            f'x="{LEGEND_X}" '
            f'y="{FOOTER_Y}">'
            "Less"
            "</text>"
        )
    )


    # ========================================================
    # 图例方格
    # ========================================================

    for index in range(5):

        x = (
            LEGEND_X
            + 40
            + index * STEP
        )

        svg.append(
            (
                '<rect '
                f'class="level-{index}" '
                f'x="{x}" '
                f'y="{FOOTER_Y - 13}" '
                f'width="{CELL}" '
                f'height="{CELL}" '
                'rx="2" '
                'ry="2"/>'
            )
        )


    # ========================================================
    # More
    # ========================================================

    svg.append(
        (
            '<text '
            'class="text footer" '
            f'x="{LEGEND_X + 140}" '
            f'y="{FOOTER_Y}">'
            "More"
            "</text>"
        )
    )


    svg.append(
        "</svg>"
    )


    SVG_FILE.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "读取 Git 历史"
    )

    history = load_history()

    print(
        f"有效代码提交 {len(history)}"
    )

    print(
        "更新 README"
    )

    update_readme(
        history
    )

    print(
        "生成 Repository Activity"
    )

    generate_svg(
        history
    )

    print(
        "完成"
    )


if __name__ == "__main__":
    main()
