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

OUTPUT_DIR = ROOT / "site"

RECENT_SVG = OUTPUT_DIR / "recent-changes.svg"
ACTIVITY_SVG = OUTPUT_DIR / "repository-activity.svg"
STATISTICS_SVG = OUTPUT_DIR / "repository-statistics.svg"
INDEX_HTML = OUTPUT_DIR / "index.html"

RECENT_DAYS = 7
RECENT_HISTORY_DAYS = 370

MAX_RECENT_ROWS = 12
TOP_CONTRIBUTORS = 6

TIMEZONE_NAME = os.getenv(
    "ACTIVITY_TIMEZONE",
    "Asia/Shanghai",
)

TZ = ZoneInfo(TIMEZONE_NAME)


# ============================================================
# 不参与“有效代码修改”统计的内容
# ============================================================

IGNORED_FILES = {
    "README.md",
    "assets/repository-activity.svg",
    "assets/repository-statistics.svg",
    "assets/recent-changes.svg",
    "docs/activity.html",
    "docs/activity-data.json",
}

IGNORED_PREFIXES = (
    ".github/",
)

AUTO_COMMIT_MESSAGES = {
    "docs: auto-update repository activity",
}

BOT_AUTHORS = {
    "github-actions[bot]",
}


# ============================================================
# 作者名称统一
# ============================================================

AUTHOR_ALIASES = {
    "Leo-John": "Leo-John233",
    "Leo·John": "Leo-John233",
    "Leo-John233": "Leo-John233",
}


# ============================================================
# Git
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


# ============================================================
# 通用辅助
# ============================================================

def canonical_author(author: str) -> str:
    author = author.strip()

    return AUTHOR_ALIASES.get(
        author,
        author,
    )


def should_ignore_file(path: str) -> bool:
    if path in IGNORED_FILES:
        return True

    return any(
        path.startswith(prefix)
        for prefix in IGNORED_PREFIXES
    )


def is_bot_commit(commit: dict) -> bool:
    author = canonical_author(
        commit["author"]
    )

    if author in BOT_AUTHORS:
        return True

    if commit["subject"] in AUTO_COMMIT_MESSAGES:
        return True

    return False


def truncate(
    text: str,
    limit: int,
) -> str:

    text = text.strip()

    if len(text) <= limit:
        return text

    return text[: limit - 1] + "…"


def svg_text(text: str) -> str:
    return html.escape(
        str(text),
        quote=True,
    )


# ============================================================
# Git Log 解析
# ============================================================

def parse_log(raw: str) -> list[dict]:
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
            commit_time = datetime.fromisoformat(
                iso_time.strip()
            ).astimezone(TZ)

        except ValueError:
            continue

        commits.append(
            {
                "sha": sha.strip(),
                "short_sha": sha.strip()[:7],
                "author": canonical_author(
                    author
                ),
                "email": email_address.strip(),
                "subject": subject.strip(),
                "date": commit_time.date(),
            }
        )

    return commits


# ============================================================
# Commit 修改文件
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

    result: list[str] = []

    for path in raw.split("\0"):

        path = path.strip()

        if not path:
            continue

        if should_ignore_file(path):
            continue

        result.append(path)

    return result


# ============================================================
# 文件范围
# ============================================================

def get_scope(
    path: str,
) -> str:

    path = path.replace(
        "\\",
        "/",
    )

    parts = path.split("/")

    if not parts:
        return "-"

    if (
        parts[0] == "原始固件"
        and len(parts) >= 2
    ):
        return parts[1]

    return parts[0]


def summarize_scope(
    files: list[str],
) -> str:

    if not files:
        return "-"

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

    scopes: list[str] = []

    for path in files:

        scope = get_scope(
            path
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
# 最近一年有效代码历史
# ============================================================

def load_recent_history() -> list[dict]:
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

    for commit in parse_log(raw):

        if is_bot_commit(commit):
            continue

        files = get_commit_files(
            commit["sha"]
        )

        if not files:
            continue

        result.append(
            {
                **commit,
                "files": files,
                "file_count": len(files),
                "scope": summarize_scope(
                    files
                ),
            }
        )

    return result


# ============================================================
# 完整 Git 历史
# ============================================================

def load_full_history() -> list[dict]:
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

    return parse_log(raw)


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

    return [
        commit
        for commit in history
        if (
            start_date
            <= commit["date"]
            <= today
        )
    ]


# ============================================================
# GitHub 通用 SVG 风格
# ============================================================

COMMON_STYLE = """
.text {
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Helvetica,
        Arial,
        sans-serif;
}

.card {
    fill: #ffffff;
    stroke: #d0d7de;
    stroke-width: 1;
}

.title {
    fill: #24292f;
    font-size: 22px;
    font-weight: 400;
}

.header {
    fill: #57606a;
    font-size: 13px;
    font-weight: 600;
}

.normal {
    fill: #24292f;
    font-size: 14px;
    font-weight: 400;
}

.secondary {
    fill: #57606a;
    font-size: 13px;
    font-weight: 400;
}

.author {
    fill: #24292f;
    font-size: 14px;
    font-weight: 600;
}

.link {
    fill: #0969da;
    font-size: 14px;
    font-weight: 600;
}

.divider {
    stroke: #d8dee4;
    stroke-width: 1;
}

@media (prefers-color-scheme: dark) {

    .card {
        fill: #0d1117;
        stroke: #30363d;
    }

    .title,
    .normal,
    .author {
        fill: #c9d1d9;
    }

    .header,
    .secondary {
        fill: #8b949e;
    }

    .link {
        fill: #58a6ff;
    }

    .divider {
        stroke: #21262d;
    }
}
"""


# ============================================================
# 最近代码修改 SVG
# ============================================================

def generate_recent_svg(
    history: list[dict],
) -> None:

    commits = get_recent_commits(
        history
    )

    visible = commits[
        :MAX_RECENT_ROWS
    ]

    hidden_count = max(
        0,
        len(commits) - len(visible),
    )

    width = 1120

    title_y = 26
    card_y = 44

    header_height = 42
    row_height = 40
    footer_height = 42

    rows = max(
        1,
        len(visible),
    )

    card_height = (
        header_height
        + rows * row_height
        + footer_height
    )

    height = (
        card_y
        + card_height
        + 1
    )

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
        "<style>",
        COMMON_STYLE,
        "</style>",
        (
            '<text '
            'class="text title" '
            'x="0" '
            f'y="{title_y}">'
            f"最近 {RECENT_DAYS} 天代码提交 "
            f"{len(commits)} 次"
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

    header_y = (
        card_y + 27
    )

    svg.extend(
        [
            (
                '<text class="text header" '
                f'x="28" y="{header_y}">'
                "日期"
                "</text>"
            ),
            (
                '<text class="text header" '
                f'x="120" y="{header_y}">'
                "修改者"
                "</text>"
            ),
            (
                '<text class="text header" '
                f'x="300" y="{header_y}">'
                "修改内容"
                "</text>"
            ),
            (
                '<text class="text header" '
                f'x="900" y="{header_y}">'
                "范围"
                "</text>"
            ),
            (
                '<line class="divider" '
                'x1="0" '
                f'y1="{card_y + header_height}" '
                'x2="1119" '
                f'y2="{card_y + header_height}"/>'
            ),
        ]
    )

    rows_top = (
        card_y + header_height
    )

    if visible:

        for index, commit in enumerate(
            visible
        ):

            row_top = (
                rows_top
                + index * row_height
            )

            baseline = (
                row_top + 26
            )

            commit_date = commit[
                "date"
            ]

            date_text = (
                f"{commit_date.month}/"
                f"{commit_date.day}"
            )

            author = truncate(
                commit["author"],
                20,
            )

            subject = truncate(
                commit["subject"],
                60,
            )

            subject_text = (
                f"{subject}  "
                f"{commit['short_sha']}"
            )

            scope = truncate(
                commit["scope"],
                24,
            )

            if (
                commit["file_count"]
                > 1
            ):
                scope = (
                    f"{scope} · "
                    f"{commit['file_count']}"
                )

            svg.extend(
                [
                    (
                        '<text class="text normal" '
                        f'x="28" y="{baseline}">'
                        f"{svg_text(date_text)}"
                        "</text>"
                    ),
                    (
                        '<text class="text author" '
                        f'x="120" y="{baseline}">'
                        f"{svg_text(author)}"
                        "</text>"
                    ),
                    (
                        '<text class="text link" '
                        f'x="300" y="{baseline}">'
                        f"{svg_text(subject_text)}"
                        "</text>"
                    ),
                    (
                        '<text class="text secondary" '
                        f'x="900" y="{baseline}">'
                        f"{svg_text(scope)}"
                        "</text>"
                    ),
                ]
            )

            if index < len(visible) - 1:

                line_y = (
                    row_top
                    + row_height
                )

                svg.append(
                    (
                        '<line class="divider" '
                        'x1="28" '
                        f'y1="{line_y}" '
                        'x2="1090" '
                        f'y2="{line_y}"/>'
                    )
                )

    else:

        svg.append(
            (
                '<text class="text secondary" '
                'x="28" '
                f'y="{rows_top + 26}">'
                "最近 7 天暂无代码提交"
                "</text>"
            )
        )

    footer_y = (
        rows_top
        + rows * row_height
    )

    svg.append(
        (
            '<line class="divider" '
            'x1="0" '
            f'y1="{footer_y}" '
            'x2="1119" '
            f'y2="{footer_y}"/>'
        )
    )

    if hidden_count:

        footer_text = (
            f"显示最新 {len(visible)} 条，"
            f"另有 {hidden_count} 次提交"
        )

    else:

        footer_text = (
            "仅统计实际代码或项目文件修改"
        )

    svg.append(
        (
            '<text class="text secondary" '
            'x="28" '
            f'y="{footer_y + 27}">'
            f"{svg_text(footer_text)}"
            "</text>"
        )
    )

    svg.append(
        "</svg>"
    )

    RECENT_SVG.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )


# ============================================================
# Contribution Graph
# ============================================================

def contribution_counts(
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

        if (
            first_day
            <= commit["date"]
            <= today
        ):
            counts[
                commit["date"].isoformat()
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


ACTIVITY_STYLE = """
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

.month,
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
"""


def generate_activity_svg(
    history: list[dict],
) -> None:

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
        - timedelta(days=364)
    )

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
        today - grid_start
    ).days + 1

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
        "<style>",
        ACTIVITY_STYLE,
        "</style>",
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

    previous_month = None
    previous_x = -100

    for week in range(53):

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

        if (
            x - previous_x
            < 45
        ):
            continue

        previous_month = (
            week_date.month
        )

        previous_x = x

        svg.append(
            (
                '<text '
                'class="text month" '
                f'x="{x}" '
                f'y="{month_y}">'
                f"{week_date.strftime('%b')}"
                "</text>"
            )
        )

    weekday_labels = {
        1: "Mon",
        3: "Wed",
        5: "Fri",
    }

    for row, label in (
        weekday_labels.items()
    ):

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

    for offset in range(
        grid_days
    ):

        current = (
            grid_start
            + timedelta(days=offset)
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

        count = counts.get(
            current.isoformat(),
            0,
        )

        level = contribution_level(
            count
        )

        tooltip = (
            f"{count} contribution"
            f"{'s' if count != 1 else ''} "
            f"on {current.isoformat()}"
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
                f"<title>{svg_text(tooltip)}</title>"
                "</rect>"
            )
        )

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

    for index in range(5):

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
# Repository Statistics
# ============================================================

STATISTICS_STYLE = """
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

.metric-value {
    fill: #24292f;
    font-size: 22px;
    font-weight: 600;
}

.metric-label {
    fill: #57606a;
    font-size: 14px;
    font-weight: 400;
}

.section-title {
    fill: #24292f;
    font-size: 16px;
    font-weight: 600;
}

.contributor-name {
    fill: #0969da;
    font-size: 15px;
    font-weight: 600;
}

.contributor-count {
    fill: #57606a;
    font-size: 14px;
    font-weight: 400;
}

.footer {
    fill: #57606a;
    font-size: 13px;
    font-weight: 400;
}

.divider {
    stroke: #d8dee4;
    stroke-width: 1;
}

@media (prefers-color-scheme: dark) {

    .card {
        fill: #0d1117;
        stroke: #30363d;
    }

    .title,
    .metric-value,
    .section-title {
        fill: #c9d1d9;
    }

    .metric-label,
    .contributor-count,
    .footer {
        fill: #8b949e;
    }

    .contributor-name {
        fill: #58a6ff;
    }

    .divider {
        stroke: #21262d;
    }
}
"""


def repository_statistics(
    full_history: list[dict],
) -> dict:

    clean_history = [
        commit
        for commit in full_history
        if not is_bot_commit(commit)
    ]

    contributors: Counter = Counter(
        canonical_author(
            commit["author"]
        )
        for commit in clean_history
    )

    if clean_history:

        first_date = min(
            commit["date"]
            for commit in clean_history
        )

        last_date = max(
            commit["date"]
            for commit in clean_history
        )

    else:

        today = datetime.now(
            TZ
        ).date()

        first_date = today
        last_date = today

    return {
        "total_commits": len(
            clean_history
        ),
        "contributors": len(
            contributors
        ),
        "first_date": first_date,
        "last_date": last_date,
        "top": contributors.most_common(
            TOP_CONTRIBUTORS
        ),
    }


def generate_statistics_svg(
    full_history: list[dict],
) -> None:

    stats = repository_statistics(
        full_history
    )

    top = stats["top"]

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
        "<style>",
        STATISTICS_STYLE,
        "</style>",
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

        svg.extend(
            [
                (
                    '<text '
                    'class="text metric-value" '
                    f'x="{x}" '
                    f'y="{card_y + 38}" '
                    'text-anchor="middle">'
                    f"{svg_text(value)}"
                    "</text>"
                ),
                (
                    '<text '
                    'class="text metric-label" '
                    f'x="{x}" '
                    f'y="{card_y + 64}" '
                    'text-anchor="middle">'
                    f"{svg_text(label)}"
                    "</text>"
                ),
            ]
        )

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
        ) in enumerate(top):

            row_top = (
                rows_top
                + index * row_height
            )

            baseline = (
                row_top + 27
            )

            commit_text = (
                "1 commit"
                if count == 1
                else f"{count:,} commits"
            )

            svg.extend(
                [
                    (
                        '<text '
                        'class="text contributor-name" '
                        'x="28" '
                        f'y="{baseline}">'
                        f"{svg_text(author)}"
                        "</text>"
                    ),
                    (
                        '<text '
                        'class="text contributor-count" '
                        'x="1090" '
                        f'y="{baseline}" '
                        'text-anchor="end">'
                        f"{svg_text(commit_text)}"
                        "</text>"
                    ),
                ]
            )

            if index < len(top) - 1:

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
        "– "
        f"{stats['last_date'].isoformat()}"
    )

    svg.extend(
        [
            (
                '<text '
                'class="text footer" '
                'x="28" '
                f'y="{footer_y + 27}">'
                "Based on the complete Git history of this branch"
                "</text>"
            ),
            (
                '<text '
                'class="text footer" '
                'x="1090" '
                f'y="{footer_y + 27}" '
                'text-anchor="end">'
                f"{svg_text(date_range)}"
                "</text>"
            ),
        ]
    )

    svg.append(
        "</svg>"
    )

    STATISTICS_SVG.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )


# ============================================================
# GitHub Pages 首页
# ============================================================

def generate_index_html() -> None:

    repository = os.getenv(
        "GITHUB_REPOSITORY",
        "Leo-John233/OnStep",
    )

    repository_url = (
        "https://github.com/"
        + repository
    )

    page = """<!DOCTYPE html>
<html lang="zh-CN">

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>OnStep Repository Activity</title>

<style>

body {
    margin: 0;
    padding: 32px;
    background: #ffffff;
    color: #24292f;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Helvetica,
        Arial,
        sans-serif;
}

main {
    width: min(1120px, 100%);
    margin: 0 auto;
}

img {
    display: block;
    width: 100%;
    height: auto;
    margin-bottom: 28px;
}

a {
    color: #0969da;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.footer {
    margin-top: 24px;
    color: #57606a;
    font-size: 14px;
}

@media (prefers-color-scheme: dark) {

    body {
        background: #0d1117;
        color: #c9d1d9;
    }

    a {
        color: #58a6ff;
    }

    .footer {
        color: #8b949e;
    }
}

</style>

</head>

<body>

<main>

<img
    src="recent-changes.svg"
    alt="Recent Changes">

<img
    src="repository-activity.svg"
    alt="Repository Activity">

<img
    src="repository-statistics.svg"
    alt="Repository Statistics">

<div class="footer">
<a href="__REPOSITORY_URL__">
返回 GitHub Repository
</a>
</div>

</main>

</body>

</html>
"""

    page = page.replace(
        "__REPOSITORY_URL__",
        repository_url,
    )

    INDEX_HTML.write_text(
        page,
        encoding="utf-8",
    )

    (
        OUTPUT_DIR / ".nojekyll"
    ).write_text(
        "",
        encoding="utf-8",
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "读取最近一年有效代码历史"
    )

    recent_history = (
        load_recent_history()
    )

    print(
        "最近一年有效代码提交："
        f"{len(recent_history)}"
    )

    print(
        "读取完整 Git 历史"
    )

    full_history = (
        load_full_history()
    )

    print(
        "完整 Git 历史："
        f"{len(full_history)}"
    )

    print(
        "生成最近代码修改"
    )

    generate_recent_svg(
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
        "生成 GitHub Pages 首页"
    )

    generate_index_html()

    print(
        "完成"
    )


if __name__ == "__main__":
    main()
