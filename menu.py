#!/usr/bin/env python3
import os
import sys
import time
import select
import subprocess
import shutil
from pathlib import Path
from typing import List
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


def wait_enter_or_timeout(timeout: int = 5):
    console.print("[dim]Tekan ENTER untuk melanjutkan...[/dim]")
    try:
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            sys.stdin.readline()
    except Exception:
        time.sleep(timeout)


def auto_update_repo():
    """
    Auto git pull untuk repo menutrmx (tempat menu ini berada).
    """
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

        wait_enter_or_timeout(3)

    except Exception:
        pass


def find_repos_with_mainpy() -> List[Path]:
    """
    Cari semua folder di $HOME yang punya main.py
    """
    repos = []
    for p in sorted(HOME.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith(".") and (p / "main.py").is_file():
            repos.append(p)
    return repos


def ensure_neutral2_files(repos: List[Path]):
    """
    Pastikan setiap repo punya neutral2.py yang sama dengan neutral2.py di repo menutrmx (tempat menu.py ini).
    - Kalau di repo target belum ada neutral2.py → copy dari sumber.
    - Kalau ada tapi masih template (mengandung 'neutral2.py - template') → overwrite dengan sumber.
    """
    base_dir = Path(__file__).resolve().parent
    source = base_dir / "neutral2.py"   # neutral2.py punyamu dari repo GitHub

    if not source.is_file():
        # Kalau neutral2.py sumber tidak ada, kita nggak berani ngapa-ngapain
        console.print("[red]⚠ neutral2.py sumber tidak ditemukan di repo menutrmx.[/red]")
        console.print("[dim]Letakkan script neutral2.py milikmu di folder yang sama dengan menu.py[/dim]")
        wait_enter_or_timeout(5)
        return

    template_marker = "neutral2.py - template"

    for repo in repos:
        dest = repo / "neutral2.py"
        try:
            if not dest.is_file():
                # Belum ada neutral2.py -> copy dari sumber
                shutil.copyfile(source, dest)
            else:
                # Kalau ada tapi isinya template, replace
                try:
                    content = dest.read_text(encoding="utf-8")
                except Exception:
                    content = ""
                if template_marker in content:
                    shutil.copyfile(source, dest)
        except Exception as e:
            console.print(f"[red]Gagal sinkron neutral2.py di {repo.name}: {e}[/red]")


def make_welcome_table():
    t = Table(show_header=False, box=box.DOUBLE, width=70, border_style="cyan")
    t.add_column(justify="center")
    t.add_row("[bold yellow]🌟 SELAMAT DATANG DI TERMUX 🌟[/bold yellow]")
    t.add_row("[dim]BY JONI WIJAYA FATHONI[/dim]")
    return t


def make_menu_table(repos: List[Path]):
    t = Table(
        title="[bold green]📂 MENU UTAMA[/bold green]",
        title_justify="center",
        width=70,
        box=box.ROUNDED,
        border_style="green"
    )
    t.add_column("Key", justify="center", style="bold cyan", width=6)
    t.add_column("Aksi", justify="left", width=60)

    if repos:
        for i, repo in enumerate(repos, start=1):
            t.add_row(str(i), f"Jalankan [yellow]{repo.name}[/yellow] (main.py)")
            t.add_row(f"{i}a", f"Jalankan [yellow]{repo.name}[/yellow] (neutral2.py)")
    else:
        t.add_row("-", "[dim]Tidak ada folder dengan main.py di HOME[/dim]")

    t.add_row("q", "Keluar dari menu")
    return t


def run_python(repo_path: Path, script_name: str):
    super_clear()
    console.print(Panel.fit(
        f"[bold cyan]Menjalankan: [yellow]{repo_path.name}/{script_name}[/yellow][/bold cyan]\n"
        f"[dim]Perintah: {sys.executable} {script_name}[/dim]",
        border_style="cyan",
        width=70
    ))
    try:
        # Pakai interpreter yang sama dengan menu.py
        subprocess.run([sys.executable, script_name], cwd=str(repo_path))
    except FileNotFoundError:
        console.print("[bold red]Python tidak ditemukan. Install dulu: pkg install python[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error menjalankan {script_name}: {e}[/bold red]")
    input("ENTER...")


def main():
    while True:
        super_clear()
        repos = find_repos_with_mainpy()
        # Sinkron neutral2.py dulu (copy dari repo menutrmx ke semua repo target)
        ensure_neutral2_files(repos)

        console.print(Align.center(make_welcome_table()))
        console.print()
        console.print(Align.center(make_menu_table(repos)))
        console.print()

        prompt = "Pilih menu: "
        pilihan = console.input(prompt).strip().lower()

        if pilihan == "q":
            console.print("[bold red]Keluar dari menu... sampai jumpa! 👋[/bold red]")
            sys.exit(0)

        # --- angka + 'a' -> neutral2.py ---
        if pilihan.endswith("a") and pilihan[:-1].isdigit():
            idx = int(pilihan[:-1]) - 1
            if 0 <= idx < len(repos):
                run_python(repos[idx], "neutral2.py")
            else:
                console.print("[bold red]❌ Nomor tidak valid.[/bold red]")
                input("ENTER...")
            continue

        # --- angka saja -> main.py ---
        if pilihan.isdigit():
            idx = int(pilihan) - 1
            if 0 <= idx < len(repos):
                run_python(repos[idx], "main.py")
            else:
                console.print("[bold red]❌ Nomor tidak valid.[/bold red]")
                input("ENTER...")
            continue

        console.print("[bold red]❌ Pilihan tidak dikenali.[/bold red]")
        input("ENTER...")


if __name__ == "__main__":
    auto_update_repo()
    main()
