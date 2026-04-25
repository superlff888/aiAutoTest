"""
千行 Bug 率自动计算工具

模式：
1. GitLab URL 模式：输入 GitLab Compare 链接，自动调用 API 获取 diff 数据计算
2. 分支模式：指定分支名 + 项目路径，自动与 master 对比
3. Git Diff 模式：对比两个分支/提交的变更行数
4. 静态扫描模式（实验性）：扫描当前目录下所有代码文件的行数，分配 Bug 计算千行 Bug 率

Git Diff / GitLab 模式变更量计算（代码行级别）：
  新增行   — 基准分支没有，目标分支有的代码行（纯新增）
  更新行   — 两个分支都有，但内容被修改的代码行
  删除行   — 基准分支有，目标分支没有的代码行（纯删除）
  变更总量 = 新增行 + 更新行 + 删除行
  千行 Bug 率 = Bug 数 / 变更总量 * 1000

Usage:
    python bug_rate_calculator.py --gitlab-url "https://..." --bugs 10  # GitLab URL 模式
    python bug_rate_calculator.py --branch feat-1.0 --project g/p --bugs 10  # 分支模式
    python bug_rate_calculator.py --diff master main --bugs 10        # Git Diff 模式
    python bug_rate_calculator.py                                    # 静态扫描（实验性），10 个 Bug
"""

import argparse
import json
import os
import re
import subprocess
import sys
import io
import urllib.parse
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 加载配置文件
_config_path = Path(__file__).parent / "config.json"
_config = {}
if _config_path.exists():
    with open(_config_path, "r", encoding="utf-8") as f:
        _config = json.load(f)

DEFAULT_GITLAB_TOKEN = _config.get("gitlab_token", "")
DEFAULT_GITLAB_DOMAIN = _config.get("gitlab_domain", "gitlab.starcharge.com")

# Windows GBK 终端兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# ===== 配置区 =====

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".sh", ".bash", ".php", ".c", ".cpp", ".h", ".cs",
}

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".idea", ".vscode", "build", "dist", ".tox",
    ".claude",
}

COMMENT_MARKERS = {
    ".py": ("#", '"""', "'''"),
    ".js": ("//",),
    ".ts": ("//",),
    ".jsx": ("//",),
    ".tsx": ("//",),
    ".java": ("//",),
    ".go": ("//",),
    ".rs": ("//",),
    ".rb": ("#",),
    ".sh": ("#",),
    ".bash": ("#",),
    ".php": ("//", "#"),
    ".c": ("//",),
    ".cpp": ("//",),
    ".h": ("//",),
    ".cs": ("//",),
}


# ===== 数据类 =====

@dataclass
class FileStat:
    """单个文件的统计信息"""
    path: str
    status: str = ""            # A=新增文件, M=修改文件, D=删除文件
    total_lines: int = 0
    code_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    new_lines: int = 0
    updated_lines: int = 0
    deleted_lines: int = 0
    bug_count: float = 0.0      # 静态模式分配
    bug_rate: float = 0.0       # 静态模式分配

    @property
    def changed_lines(self) -> int:
        return self.new_lines + self.updated_lines + self.deleted_lines


@dataclass
class ModuleStat:
    """模块（目录）的统计信息"""
    name: str
    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    new_lines: int = 0
    updated_lines: int = 0
    deleted_lines: int = 0
    files: List[FileStat] = field(default_factory=list)

    @property
    def changed_lines(self) -> int:
        return self.new_lines + self.updated_lines + self.deleted_lines


# ===== GitLab URL 模式 =====

# 支持的 URL 格式：
#   https://gitlab.example.com/group/project/-/compare/master...release-1.0
#   https://gitlab.example.com/group/project/-/compare/master...release-1.0?from_project_id=123
GITLAB_COMPARE_RE = re.compile(
    r"https?://(?P<domain>[^/]+)/(?P<path>.+?)/-/compare/(?P<base>[^\.]+)\.\.\.(?P<target>[^?]+)"
)
_CLEAN_JSON_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def parse_gitlab_url(url: str) -> Dict[str, str]:
    """解析 GitLab Compare URL"""
    if not (m := GITLAB_COMPARE_RE.match(url.strip())):
        print("无法解析 GitLab URL，格式应为：")
        print("  https://gitlab.xxx/group/project/-/compare/base...target")
        sys.exit(1)
    project_path = m.group("path").strip("/")
    return {
        "domain": m.group("domain"),
        "project": urllib.parse.quote(project_path, safe=""),
        "base": m.group("base"),
        "target": m.group("target"),
    }


def _clean_json(raw: str) -> str:
    """清理 GitLab API 响应中的控制字符（diff 内容常含非法字符导致 JSON 解析失败）"""
    return _CLEAN_JSON_RE.sub('', raw)


def get_gitlab_diff_stats(
    domain: str, project: str, base: str, target: str, token: str
) -> List[FileStat]:
    """通过 GitLab Compare API 获取 diff 统计（直连 API，自动找 merge base）"""
    all_diffs = []
    page = 1
    per_page = 100

    while True:
        url = (
            f"https://{domain}/api/v4/projects/{project}/repository/compare"
            f"?from={urllib.parse.quote(base)}&to={urllib.parse.quote(target)}"
            f"&straight=false&per_page={per_page}&page={page}"
        )

        req = urllib.request.Request(url)
        req.add_header("PRIVATE-TOKEN", token)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                stdout = resp.read().decode("utf-8")
        except Exception as e:
            print(f"  API 请求失败: {e}")
            sys.exit(1)

        try:
            result = json.loads(_clean_json(stdout))
        except json.JSONDecodeError:
            print(f"  API 返回数据解析失败")
            sys.exit(1)

        # 检查 API 错误响应（如项目/分支不存在）
        if "message" in result and "diffs" not in result:
            msg = result["message"]
            match msg.lower():
                case _ if "not found" in msg or "404" in msg:
                    print("  错误：项目或分支不存在")
                    print(f"  GitLab 返回: {msg}")
                case _:
                    print(f"  API 错误: {msg}")
            sys.exit(1)

        if not (diffs := result.get("diffs", [])):
            break
        all_diffs.extend(diffs)

        if len(diffs) < per_page:
            break
        page += 1

    if not all_diffs:
        print("未获取到任何 diff 数据")
        print("  提示：该目标分支可能已合并到 master，GitLab Compare API 在合并场景下无法返回 diff 数据")
        sys.exit(0)

    stats = []
    for d in all_diffs:
        filepath = d.get("new_path") or d.get("old_path", "")
        if not filepath:
            continue

        if not (ext := os.path.splitext(filepath)[1]) or ext not in CODE_EXTENSIONS:
            continue
        if filepath.startswith(".claude"):
            continue

        match (d.get("new_file", False), d.get("deleted_file", False)):
            case (False, True):
                status = "D"
            case (True, False):
                status = "A"
            case _:
                status = "M"

        # 从 diff 字符串统计新增/删除行（排除 +++ / --- 头部行）
        added = deleted = 0
        for l in d.get("diff", "").split("\n"):
            if l.startswith("+") and not l.startswith("+++"):
                added += 1
            elif l.startswith("-") and not l.startswith("---"):
                deleted += 1

        updated = min(added, deleted)
        new_only = added - updated
        deleted_only = deleted - updated

        stats.append(FileStat(
            path=filepath,
            status=status,
            new_lines=new_only,
            updated_lines=updated,
            deleted_lines=deleted_only,
        ))

    return stats


# ===== 核心逻辑 =====

def count_lines(filepath: str) -> Tuple[int, int, int, int]:
    """
    统计文件：总行数、有效代码行数、空行数、注释行数
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return 0, 0, 0, 0

    ext = os.path.splitext(filepath)[1]
    comment_markers = COMMENT_MARKERS.get(ext, ("#",))
    line_comment = comment_markers[0]
    block_comments = comment_markers[1:] if len(comment_markers) > 1 else ()

    total = len(lines)
    blank = 0
    comments = 0
    in_block_comment = False
    block_close = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            blank += 1
            continue

        if in_block_comment:
            comments += 1
            if block_close and block_close in stripped:
                in_block_comment = False
            continue

        started_block = False
        for marker in block_comments:
            if stripped.startswith(marker):
                in_block_comment = True
                block_close = marker
                comments += 1
                if stripped.endswith(marker) and len(stripped) > len(marker) * 2:
                    in_block_comment = False
                started_block = True
                break

        if started_block:
            continue

        if stripped.startswith(line_comment):
            comments += 1
            continue

    code = total - blank - comments
    return total, code, blank, comments


def scan_directory(directory: str, exclude: set = None) -> List[FileStat]:
    """递归扫描目录下所有代码文件"""
    exclude = exclude or EXCLUDE_DIRS
    stats = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude]

        for filename in sorted(files):
            if (ext := os.path.splitext(filename)[1]) not in CODE_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            total, code, blank, comments = count_lines(filepath)

            if total == 0:
                continue

            rel_path = os.path.relpath(filepath)
            stat = FileStat(
                path=rel_path,
                total_lines=total,
                code_lines=code,
                blank_lines=blank,
                comment_lines=comments,
            )
            stats.append(stat)

    return stats


def get_git_diff_stats(base: str, target: str) -> List[FileStat]:
    """
    获取 Git diff 统计：对比 base 和 target 分支，返回每个文件的变更行数
    base   → 基准分支（如 master）
    target → 对比分支（如 main）
    """
    ref = f"{base}...{target}"

    # 1. 获取文件状态（A/M/D/R）
    cmd_status = ["git", "-c", "core.quotePath=false", "diff", "--name-status", ref]
    result = subprocess.run(cmd_status, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"Git 命令执行失败: {' '.join(cmd_status)}")
        print(f"错误信息: {result.stderr}")
        sys.exit(1)

    # 2. 获取增删行数
    cmd_numstat = ["git", "-c", "core.quotePath=false", "diff", "--numstat", ref]
    result2 = subprocess.run(cmd_numstat, capture_output=True, text=True, encoding='utf-8')

    # 构建 numstat 查找表
    numstat_map: Dict[str, Tuple[int, int]] = {}
    if result2.stdout.strip():
        for line in result2.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) == 3:
                added_str, deleted_str, filepath = parts
                added = int(added_str) if added_str != "-" else 0
                deleted = int(deleted_str) if deleted_str != "-" else 0
                numstat_map[filepath] = (added, deleted)

    stats = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0]

        match status:
            case "A" | "M" | "D":
                filepath = parts[1]
            case _ if status.startswith("R"):
                if len(parts) >= 3:
                    filepath = parts[2]
                else:
                    continue
                status = "M"
            case _:
                continue

        if not (ext := os.path.splitext(filepath)[1]) or ext not in CODE_EXTENSIONS:
            continue

        # 排除 .claude 目录下的文件
        if filepath.startswith(".claude"):
            continue

        added, deleted = numstat_map.get(filepath, (0, 0))

        updated = min(added, deleted)
        new_only = added - updated
        deleted_only = deleted - updated

        stat = FileStat(
            path=filepath,
            status=status,
            new_lines=new_only,
            updated_lines=updated,
            deleted_lines=deleted_only,
        )
        stats.append(stat)

    return stats


def calculate_bug_rate_static(stats: List[FileStat], bug_count: int) -> List[FileStat]:
    """静态模式：按代码总行数分配 Bug"""
    total_code = sum(s.code_lines for s in stats)
    if total_code == 0:
        return stats

    quotients = []
    for stat in stats:
        exact = stat.code_lines / total_code * bug_count
        quotients.append((stat, exact, exact - int(exact)))

    remaining = bug_count
    for stat, exact, frac in quotients:
        stat.bug_count = int(exact)
        remaining -= stat.bug_count

    quotients.sort(key=lambda x: x[2], reverse=True)
    for stat, exact, frac in quotients:
        if remaining <= 0:
            break
        stat.bug_count += 1
        remaining -= 1

    for stat in stats:
        if stat.code_lines > 0:
            stat.bug_rate = stat.bug_count / stat.code_lines * 1000

    return stats


def group_by_module_static(stats: List[FileStat]) -> Dict[str, ModuleStat]:
    """静态模式：按一级子目录分组统计"""
    modules: Dict[str, ModuleStat] = {}

    for stat in stats:
        parts = Path(stat.path).parts
        module_name = parts[0] if len(parts) > 1 else os.path.dirname(stat.path) or "根目录"

        if module_name not in modules:
            modules[module_name] = ModuleStat(name=module_name)

        mod = modules[module_name]
        mod.total_files += 1
        mod.total_lines += stat.total_lines
        mod.code_lines += stat.code_lines
        mod.files.append(stat)

    return modules


def group_by_module_diff(stats: List[FileStat]) -> Dict[str, ModuleStat]:
    """Diff 模式：按一级子目录分组统计"""
    modules: Dict[str, ModuleStat] = {}

    for stat in stats:
        parts = Path(stat.path).parts
        module_name = parts[0] if len(parts) > 1 else os.path.dirname(stat.path) or "根目录"

        if module_name not in modules:
            modules[module_name] = ModuleStat(name=module_name)

        mod = modules[module_name]
        mod.total_files += 1
        mod.total_lines += stat.total_lines
        mod.code_lines += stat.code_lines
        mod.new_lines += stat.new_lines
        mod.updated_lines += stat.updated_lines
        mod.deleted_lines += stat.deleted_lines
        mod.files.append(stat)

    return modules


# ===== 输出 =====

def print_static_summary(stats: List[FileStat], modules: Dict[str, ModuleStat], bug_count: int):
    """静态模式汇总报告"""
    total_files = len(stats)
    total_code = sum(s.code_lines for s in stats)
    total_blank = sum(s.blank_lines for s in stats)
    total_comments = sum(s.comment_lines for s in stats)
    overall_rate = bug_count / total_code * 1000 if total_code > 0 else 0

    print("=" * 70)
    print(" [REPORT] 千行 Bug 率统计报告 (静态扫描)")
    print("=" * 70)
    print(f"  Bug 总数:     {bug_count}")
    print(f"  文件总数:     {total_files}")
    print(f"  代码总行数:   {total_code}")
    print(f"  空行数:       {total_blank}")
    print(f"  注释行数:     {total_comments}")
    print(f"  千行 Bug 率:  {overall_rate:.2f}‰")
    print("=" * 70)

    print(f"\n {'模块':<30} {'文件数':>6} {'代码行':>8} {'Bug数':>6} {'千行Bug率':>10}")
    print("-" * 70)
    for name, mod in sorted(modules.items()):
        mod_code = mod.code_lines
        mod_bug = round(mod_code / total_code * bug_count) if total_code > 0 else 0
        mod_rate = mod_bug / mod_code * 1000 if mod_code > 0 else 0
        print(f" {name:<30} {mod.total_files:>6} {mod_code:>8} {mod_bug:>6} {mod_rate:>10.2f}‰")
    print("-" * 70)


def print_diff_summary(stats: List[FileStat], modules: Dict[str, ModuleStat],
                       bug_count: int, base: str, target: str):
    """Git diff 模式汇总报告"""
    total_files = len(stats)
    total_new = sum(s.new_lines for s in stats)
    total_updated = sum(s.updated_lines for s in stats)
    total_deleted = sum(s.deleted_lines for s in stats)
    total_changed = total_new + total_updated + total_deleted
    overall_rate = bug_count / total_changed * 1000 if total_changed > 0 else 0

    print("=" * 75)
    print(f" [REPORT] 千行 Bug 率统计报告 (Git Diff: {base} -> {target})")
    print("=" * 75)
    print(f"  Bug 总数:           {bug_count}")
    print(f"  变更文件数:         {total_files}")
    print(f"  新增行:             {total_new}")
    print(f"  更新行:             {total_updated}")
    print(f"  删除行:             {total_deleted}")
    print(f"  变更总行数:         {total_changed}")
    print(f"  千行 Bug 率:        {overall_rate:.2f}‰")
    print("=" * 75)

    hdr = f" {'模块':<25} {'新增行':>6} {'更新行':>6} {'删除行':>6} {'Bug数':>6} {'千行Bug率':>10}"
    print(hdr)
    print("-" * len(hdr))
    overall_rate = bug_count / total_changed * 1000 if total_changed > 0 else 0
    for name, mod in sorted(modules.items()):
        # 按模块变更量占比分配 Bug，再算千行率（所有模块共享同一基准率）
        mod_bug = mod.changed_lines / total_changed * bug_count if total_changed > 0 else 0
        mod_rate = overall_rate if mod.changed_lines > 0 else 0
        row = f" {name:<25} {mod.new_lines:>6} {mod.updated_lines:>6} {mod.deleted_lines:>6} {mod_bug:>6.0f} {mod_rate:>10.2f}‰"
        print(row)
    print("-" * len(hdr))


STATUS_LABEL = {"A": "新增", "M": "修改", "D": "删除"}


def print_detail(stats: List[FileStat], diff_mode: bool = False):
    """打印文件级明细"""
    match diff_mode:
        case True:
            print(f"\n {'文件':<50} {'状态':>6} {'新增行':>6} {'更新行':>6} {'删除行':>6}")
        case False:
            print(f"\n {'文件':<55} {'代码行':>7}")
    print("-" * 75)

    for f in stats:
        match diff_mode:
            case True:
                label = STATUS_LABEL.get(f.status, f.status)
                print(f"    {f.path:<50} {label:>6} {f.new_lines:>6} {f.updated_lines:>6} {f.deleted_lines:>6}")
            case False:
                print(f"    {f.path:<55} {f.code_lines:>7}")


# ===== 主入口 =====

def main():
    parser = argparse.ArgumentParser(
        description="千行 Bug 率自动计算工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 静态扫描当前目录
  python bug_rate_calculator.py --bugs 10

  # 对比 master 和 main 分支的变更
  python bug_rate_calculator.py --diff master main --bugs 10

  # 对比最近5次提交
  python bug_rate_calculator.py --diff HEAD~5 HEAD --bugs 3

  # GitLab Compare URL 模式
  python bug_rate_calculator.py --gitlab-url "https://gitlab.xxx/group/proj/-/compare/master...release-1.0" --bugs 10 --token "glpat-xxx"

  # 分支模式（简洁）：指定分支名，自动与 master 对比
  python bug_rate_calculator.py --branch feature-4.5.5 --project group/project --bugs 10 --detail

  # Token 也可通过环境变量提供
  export GITLAB_TOKEN="glpat-xxx"
  python bug_rate_calculator.py --branch feature-4.5.5 --project group/project --bugs 10
        """,
    )
    parser.add_argument("--dir", default=".", help="要扫描的目录 (默认: 当前目录)")
    parser.add_argument("--bugs", type=int, default=10, help="Bug 总数 (默认: 10)")
    parser.add_argument("--detail", action="store_true", help="显示文件级明细")
    parser.add_argument(
        "--diff", nargs=2, metavar=("BASE", "TARGET"),
        help="Git Diff 模式：对比 BASE 和 TARGET 分支/提交 "
             "(例: --diff master main)"
    )
    parser.add_argument(
        "--gitlab-url", metavar="URL",
        help="GitLab Compare URL，例: https://gitlab.xxx/group/proj/-/compare/master...release-1.0"
    )
    parser.add_argument(
        "--token", default=DEFAULT_GITLAB_TOKEN,
        help="GitLab Personal Access Token（也可通过环境变量 GITLAB_TOKEN 提供）"
    )
    parser.add_argument(
        "--branch", metavar="NAME",
        help="分支模式：指定目标分支名，自动与 master 对比（需配合 --project）"
    )
    parser.add_argument(
        "--project", metavar="PATH",
        help="GitLab 项目路径，如 cloud-product-two/vpp-operation（分支模式必需）"
    )
    parser.add_argument(
        "--domain", default=DEFAULT_GITLAB_DOMAIN,
        help="GitLab 域名（默认: gitlab.starcharge.com）"
    )
    args = parser.parse_args()
    token = args.token or os.environ.get("GITLAB_TOKEN")

    match (args.gitlab_url, args.branch, args.diff):
        case (url, _, _) if url:
            # GitLab URL 模式
            if not token:
                print("需要提供 GitLab Token，通过以下方式之一：")
                print("  1. 命令行参数: --token glpat-xxx")
                print("  2. 环境变量:   export GITLAB_TOKEN=glpat-xxx")
                sys.exit(1)
            info = parse_gitlab_url(args.gitlab_url)

            print(f"GitLab 模式: {info['domain']}")
            print(f"  项目: {info['project']}")
            print(f"  分支: {info['base']} -> {info['target']}")
            print(f"  Bug 总数: {args.bugs}\n")

            stats = get_gitlab_diff_stats(
                info["domain"], info["project"], info["base"], info["target"], token
            )
            if not stats:
                print("未找到代码变更文件")
                sys.exit(0)

            modules = group_by_module_diff(stats)
            label = f"{info['base']} -> {info['target']}"
            print_diff_summary(stats, modules, args.bugs, label.split(" -> ")[0], label.split(" -> ")[1])
            if args.detail:
                print_detail(stats, diff_mode=True)

        case (_, branch, _) if branch:
            # 分支模式（简洁模式：指定分支名，自动与 master 对比）
            if not token:
                print("需要提供 GitLab Token，通过以下方式之一：")
                print("  1. 命令行参数: --token glpat-xxx")
                print("  2. 环境变量:   export GITLAB_TOKEN=glpat-xxx")
                sys.exit(1)
            if not args.project:
                print("分支模式需指定项目路径: --project group/project")
                sys.exit(1)

            project_encoded = urllib.parse.quote(args.project, safe="")
            base = "master"
            target = args.branch

            print(f"分支模式: {args.domain}")
            print(f"  项目: {args.project}")
            print(f"  分支: {base} -> {target}")
            print(f"  Bug 总数: {args.bugs}\n")

            stats = get_gitlab_diff_stats(args.domain, project_encoded, base, target, token)
            if not stats:
                print("未找到代码变更文件")
                sys.exit(0)

            modules = group_by_module_diff(stats)
            print_diff_summary(stats, modules, args.bugs, base, target)
            if args.detail:
                print_detail(stats, diff_mode=True)

        case (_, _, (base, target)):
            # Git Diff 模式
            print(f"Git Diff 模式: {base} -> {target}")
            print(f"Bug 总数: {args.bugs}\n")

            stats = get_git_diff_stats(base, target)
            if not stats:
                print("未找到代码变更文件")
                sys.exit(0)

            modules = group_by_module_diff(stats)
            print_diff_summary(stats, modules, args.bugs, base, target)
            if args.detail:
                print_detail(stats, diff_mode=True)

        case _:
            # 静态扫描模式
            if not os.path.isdir(args.dir):
                print(f"错误: 目录 '{args.dir}' 不存在")
                sys.exit(1)

            print(f"静态扫描模式: {args.dir}")
            print(f"Bug 总数: {args.bugs}\n")

            stats = scan_directory(args.dir)
            if not stats:
                print("未找到任何代码文件")
                sys.exit(0)

            stats = calculate_bug_rate_static(stats, args.bugs)
            modules = group_by_module_static(stats)

            print_static_summary(stats, modules, args.bugs)
            if args.detail:
                print_detail(stats)

    print()


if __name__ == "__main__":
    main()
