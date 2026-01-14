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
                msg = "✅ Menu berhasil diperbarui!"
                style = "green"
            else:
                msg = "✔️ Menu sudah versi terbaru."
                style = "cyan"

            t = Table(title="📘 Status Update", width=70, box=box.ROUNDED, border_style=style, show_header=False)
            t.add_column()
            t.add_row(msg)
            console.print(t)

        wait_enter_or_timeout(5)

    except Exception:
        pass


def find_repos_with_mainpy():
    repos = []
    for p in sorted(HOME.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith(".") and (p / "main.py").is_file():
            repos.append(p)
    return repos


def ensure_neutral2_files(repos: List[Path]):
    template = """#!/usr/bin/env python3

def main():
    print("neutral2.py - template. Silakan edit untuk fungsionalitas lain.\n")

if __name__ == "__main__":
    main()
"""
    for repo in repos:
        neutral_path = repo / "neutral2.py"
        if not neutral_path.is_file():
            try:
                neutral_path.write_text(template, encoding="utf-8")
            except Exception:
                pass


def make_welcome_table():
    t = Table(show_header=False, box=box.DOUBLE, width=70, border_style="cyan")
    t.add_column(justify="center")
    t.add_row("[bold yellow]🌟 SELAMAT DATANG DI TERMUX 🌟[/bold yellow]")
    t.add_row("[dim]BY JONI WIJAYA FATHONI[/dim]")
    return t


def make_menu_table(repos):
    t = Table(
        title="📂 MENU UTAMA",
        title_justify="center",
        width=70,
        box=box.ROUNDED,
        border_style="green"
    )
    t.add_column("Key", justify="center", style="bold cyan", width=6)
    t.add_column("Aksi", justify="left", width=60)

    if repos:
        for i, repo in enumerate(repos, start=1):
            t.add_row(str(i), f"Jalankan {repo.name} (main.py)")
            t.add_row(f"{i}a", f"Jalankan {repo.name} (neutral2.py)")
    else:
        t.add_row("-", "[dim]Tidak ada folder dengan main.py[/dim]")

    t.add_row("q", "Keluar dari menu")
    return t


def run_python(repo: Path, script: str):
    super_clear()
    console.print(Panel.fit(
        f"[cyan]Menjalankan[/cyan] [yellow]{repo.name}/{script}[/yellow]\n\n"
        f"[dim]Command: python {script}[/dim]",
        border_style="cyan",
        width=70
    ))

    try:
        subprocess.run([sys.executable, script], cwd=str(repo))
    except Exception as e:
        console.print(f"[red]Gagal menjalankan: {e}[/red]")

    input("ENTER...")


def main():
    while True:
        super_clear()
        repos = find_repos_with_mainpy()
        ensure_neutral2_files(repos)

        console.print(Align.center(make_welcome_table()))
        console.print()
        console.print(Align.center(make_menu_table(repos)))
        console.print()

        pilihan = console.input("Pilih menu: ").strip().lower()

        if pilihan == "q":
            console.print("[bold red]Keluar... 👋[/bold red]")
            sys.exit(0)

        # --- Neutral handler (angka + a) ---
        if pilihan.endswith("a") and pilihan[:-1].isdigit():
            idx = int(pilihan[:-1]) - 1
            if 0 <= idx < len(repos):
                return run_python(repos[idx], "neutral2.py")
            else:
                console.print("[red]Nomor tidak valid![/red]")
                input("ENTER...")
                continue

        # --- Main handler (angka saja) ---
        if pilihan.isdigit():
            idx = int(pilihan) - 1
            if 0 <= idx < len(repos):
                return run_python(repos[idx], "main.py")
            else:
                console.print("[red]Nomor tidak valid![/red]")
                input("ENTER...")
                continue

        console.print("[red]Pilihan tidak dikenali[/red]")
        input("ENTER...")


if __name__ == "__main__":
    auto_update_repo()
    main()
