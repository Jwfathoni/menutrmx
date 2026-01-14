#!/usr/bin/env python3

import os
import sys
import json
import time
import select
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box

console = Console()
HOME = Path.home()


def super_clear():
    os.system("printf '\\033c'")
    console.clear()


def wait_enter_or_timeout(timeout: int = 7):
    console.print("[dim]Tekan ENTER untuk melanjutkan...[/dim]")
    try:
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            sys.stdin.readline()
    except Exception:
        time.sleep(timeout)


def auto_update_repo():
    try:
        repo_dir = Path(__file__).resolve().parent
    except Exception:
        return

    if not (repo_dir / ".git").is_dir():
        return

    try:
        super_clear()
        console.print("\n\n\n\n\n\n🔄 Mohon tunggu, sedang memeriksa dan memperbarui menu...\n")

        res = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True
        )
        out = (res.stdout or "").strip().lower()

        console.print()

        if res.returncode == 0:
            if out and "already up to date" not in out:
                msg = "✅ Menu berhasil diperbarui ke versi terbaru."
                style = "green"
            else:
                msg = "✔️ Menu sudah dalam versi terbaru. Tidak ada pembaruan diperlukan."
                style = "cyan"

            t = Table(
                title="[bold cyan]📘 Status Update Menu[/bold cyan]",
                title_justify="center",
                width=70,
                box=box.ROUNDED,
                border_style=style,
                show_header=False
            )
            t.add_column(justify="left")
            t.add_row(msg)
            console.print(t)

        wait_enter_or_timeout(10)

    except Exception:
        pass


def find_repos_with_mainpy():
    repos = []
    for p in sorted(HOME.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith(".") and (p / "main.py").is_file():
            repos.append(p)
    return repos


def find_token_files():
    token_files = []
    for p in sorted(HOME.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        f = p / "refresh-tokens.json"
        if f.is_file():
            token_files.append(f)
    return token_files


def load_tokens(path: Path) -> List[Dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []
    except Exception:
        return []


def make_key(item: Dict) -> Tuple:
    number = str(item.get("number", "")).strip()
    sid = str(item.get("subscriber_id", "")).strip()
    rt = str(item.get("refresh_token", "")).strip()
    if number and sid:
        return ("ns", number, sid)
    if rt:
        return ("rt", rt)
    return ("raw", number, sid, rt)


def dedup_list(lst: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in lst:
        k = make_key(it)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def merge_unique(all_lists: List[List[Dict]]) -> List[Dict]:
    merged = []
    seen = set()
    for lst in all_lists:
        for it in lst:
            k = make_key(it)
            if k in seen:
                continue
            seen.add(k)
            merged.append(it)
    return merged


def load_all_tokens_union():
    token_files = find_token_files()
    all
