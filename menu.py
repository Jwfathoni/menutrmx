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
        console.print("\n\n\n\n\n\n🔄 Memeriksa & memperbarui menu...\n")

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
                msg = "✅ Menu diperbarui."
                style = "green"
            else:
                msg = "✔️ Menu sudah versi terbaru."
                style = "cyan"

            t = Table(
                title="[bold cyan]📘 STATUS UPDATE[/bold cyan]",
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
    all_data = [dedup_list(load_tokens(f)) for f in token_files]
    merged = merge_unique(all_data)
    return token_files, merged

def build_info_by_number(merged: List[Dict]) -> Dict[str, str]:
    info_by_number: Dict[str, str] = {}
    for item in merged:
        num = str(item.get("number", "")).strip()
        if not num:
            continue
        name = str(item.get("name", "")).strip()
        if num not in info_by_number or not info_by_number[num]:
            info_by_number[num] = name
    return info_by_number

def sync_users():
    super_clear()
    token_files = find_token_files()

    if not token_files:
        console.print(Panel.fit(
            "[bold red]❌ Tidak ada refresh-tokens.json[/bold red]",
            border_style="red",
            width=70
        ))
        input("ENTER...")
        return

    all_data = [dedup_list(load_tokens(f)) for f in token_files]
    merged = merge_unique(all_data)

    added_total = 0
    cleaned_total = 0

    for f in token_files:
        before_raw = load_tokens(f)
        before = dedup_list(before_raw)

        cleaned_total += (len(before_raw) - len(before))

        before_keys = {make_key(x) for x in before}
        merged_keys = {make_key(x) for x in merged}

        added_total += len(merged_keys - before_keys)

        f.write_text(json.dumps(merged, indent=4, ensure_ascii=False), encoding="utf-8")

    console.print(Panel.fit(
        f"[bold green]✅ Sinkronisasi selesai[/bold green]\n"
        f"[cyan]File tokens:[/cyan] {len(token_files)}\n"
        f"[cyan]Data baru:[/cyan] {added_total}\n"
        f"[cyan]Duplikat dibersihkan:[/cyan] {cleaned_total}\n"
        f"[cyan]Total data:[/cyan] {len(merged)}",
        border_style="green",
        width=70
    ))
    input("ENTER...")

def remove_or_name_user_menu():
    super_clear()
    token_files, merged = load_all_tokens_union()

    if not merged:
        console.print(Panel.fit(
            "[bold yellow]Tidak ada data user.[/bold yellow]",
            border_style="yellow",
            width=70
        ))
        input("ENTER...")
        return

    info_by_number = build_info_by_number(merged)

    if not info_by_number:
        console.print(Panel.fit(
            "[bold yellow]Tidak ada nomor valid.[/bold yellow]",
            border_style="yellow",
            width=70
        ))
        input("ENTER...")
        return

    panel = Panel.fit(
        "[bold magenta]RUSR - Manajemen User[/bold magenta]\n\n"
        "[cyan]1.[/cyan] Ubah nama nomor\n"
        "[cyan]2.[/cyan] Hapus data nomor\n"
        "[cyan]00.[/cyan] Kembali\n"
        "[cyan]b.[/cyan] Kembali",
        border_style="magenta",
        width=70
    )
    console.print(panel)

    choice = console.input("Pilih [1/2/00/b]: ").strip().lower()

    if choice in ("b", "00"):
        return

    if choice == "1":
        name_user_flow(token_files, merged, info_by_number)
    elif choice == "2":
        delete_user_flow(token_files, merged, info_by_number)

def name_user_flow(token_files, merged, info_by_number):
    super_clear()
    numbers = sorted(info_by_number.keys())

    t = Table(
        title="[bold green]📇 Ubah Nama Nomor[/bold green]",
        box=box.ROUNDED,
        border_style="green",
        width=70
    )
    t.add_column("No", justify="center", style="bold cyan", width=6)
    t.add_column("Number", justify="left", width=32)
    t.add_column("Name", justify="left", width=32)

    for i, num in enumerate(numbers, start=1):
        name = info_by_number[num] or "-"
        t.add_row(str(i), num, name)

    console.print(t)
    pilihan = console.input("\nPilih [index/nomor/00/b]: ").strip()

    if pilihan.lower() in ("b", "00"):
        return

    target = None
    if pilihan.isdigit():
        idx = int(pilihan) - 1
        if 0 <= idx < len(numbers):
            target = numbers[idx]
    elif pilihan in numbers:
        target = pilihan

    if not target:
        console.print("[bold red]❌ Pilihan tidak valid.[/bold red]")
        input("ENTER...")
        return

    new_name = console.input(f"Nama baru untuk {target}: ").strip()
    if not new_name:
        console.print("[yellow]Nama kosong, dibatalkan.[/yellow]")
        input("ENTER...")
        return

    updated = 0
    for item in merged:
        if str(item.get("number")).strip() == target:
            item["name"] = new_name
            updated += 1

    for f in token_files:
        f.write_text(json.dumps(merged, indent=4, ensure_ascii=False), encoding="utf-8")

    console.print(Panel.fit(
        f"[bold green]✅ Nama {target} → [yellow]{new_name}[/yellow][/bold green]\n"
        f"[cyan]Record diupdate:[/cyan] {updated}",
        border_style="green",
        width=70
    ))
    input("ENTER...")

def delete_user_flow(token_files, merged, info_by_number):
    super_clear()
    numbers = sorted(info_by_number.keys())

    t = Table(
        title="[bold red]🗑️ Hapus Data Nomor[/bold red]",
        box=box.ROUNDED,
        border_style="red",
        width=70
    )
    t.add_column("No", justify="center", style="bold cyan", width=6)
    t.add_column("Number", justify="left", width=32)
    t.add_column("Name", justify="left", width=32)

    for i, num in enumerate(numbers, start=1):
        name = info_by_number[num] or "-"
        t.add_row(str(i), num, name)

    console.print(t)
    pilihan = console.input("\nPilih [index/nomor/00/b]: ").strip()

    if pilihan.lower() in ("b", "00"):
        return

    target = None
    if pilihan.isdigit():
        idx = int(pilihan) - 1
        if 0 <= idx < len(numbers):
            target = numbers[idx]
    elif pilihan in numbers:
        target = pilihan

    if not target:
        console.print("[bold red]❌ Pilihan tidak valid.[/bold red]")
        input("ENTER...")
        return

    konfirm = console.input(
        f"[bold red]Hapus SEMUA data nomor {target}? (y/n): [/bold red]"
    ).strip().lower()

    if konfirm != "y":
        console.print("[yellow]Dibatalkan.[/yellow]")
        input("ENTER...")
        return

    before = len(merged)
    new_merged = [x for x in merged if str(x.get("number")).strip() != target]
    removed = before - len(new_merged)

    for f in token_files:
        f.write_text(json.dumps(new_merged, indent=4, ensure_ascii=False), encoding="utf-8")

    console.print(Panel.fit(
        f"[bold green]✅ Nomor {target} dihapus[/bold green]\n"
        f"[cyan]Record dihapus:[/cyan] {removed}\n"
        f"[cyan]Total sekarang:[/cyan] {len(new_merged)}",
        border_style="green",
        width=70
    ))
    input("ENTER...")

def run_python(repo_path: Path):
    super_clear()
    console.print(Panel.fit(
        f"[bold cyan]Menjalankan: [yellow]{repo_path.name}[/yellow][/bold cyan]\n"
        "[dim]python main.py[/dim]",
        border_style="cyan",
        width=70
    ))
    try:
        subprocess.run(["python", "main.py"], cwd=str(repo_path))
    except FileNotFoundError:
        console.print("[bold red]Python tidak ditemukan. pkg install python[/bold red]")
    input("ENTER...")

def update_all_repos(repos):
    super_clear()
    console.print(Panel.fit(
        "Update semua repo (git pull)",
        border_style="yellow",
        width=70
    ))

    if not repos:
        console.print("[dim]Tidak ada folder dengan main.py.[/dim]")
        input("ENTER...")
        return

    for repo in repos:
        if not (repo / ".git").is_dir():
            console.print(f"[dim]- {repo.name}: skip[/dim]")
            continue

        console.print(f"\n[bold cyan]▶ {repo.name}[/bold cyan]")
        try:
            subprocess.run(["git", "pull"], cwd=str(repo))
        except FileNotFoundError:
            console.print("[bold red]Git belum terinstall. pkg install git[/bold red]")
            break

    input("ENTER...")

def make_welcome_table():
    t = Table(show_header=False, box=box.DOUBLE, width=70, border_style="cyan")
    t.add_column(justify="center")
    t.add_row("[bold yellow]🌟 SELAMAT DATANG DI TERMUX 🌟[/bold yellow]")
    t.add_row("[dim]BY JONI WIJAYA FATHONI[/dim]")
    return t

def make_menu_table(repos):
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
            t.add_row(str(i), f"Jalankan [yellow]{repo.name}[/yellow]")
    else:
        t.add_row("-", "[dim]Tidak ada folder dengan main.py[/dim]")

    t.add_row("up", "Update semua repo")
    t.add_row("usr", "Sinkron & bersihkan tokens")
    t.add_row("rusr", "Kelola user (nama / hapus)")
    t.add_row("q", "Keluar dari menu")
    return t

def make_user_table(info_by_number: Dict[str, str]):
    t = Table(
        title="[bold magenta]📇 DAFTAR NOMOR TERSIMPAN[/bold magenta]",
        title_justify="center",
        width=70,
        box=box.ROUNDED,
        border_style="magenta"
    )
    t.add_column("No", justify="center", style="bold cyan", width=6)
    t.add_column("Number", justify="left", width=32)
    t.add_column("Name", justify="left", width=32)

    numbers = sorted(info_by_number.keys())
    for i, num in enumerate(numbers, start=1):
        name = info_by_number[num] or "-"
        t.add_row(str(i), num, name)

    return t

def main():
    while True:
        super_clear()
        repos = find_repos_with_mainpy()
        _, merged = load_all_tokens_union()
        info_by_number = build_info_by_number(merged) if merged else {}

        console.print(Align.center(make_welcome_table()))
        console.print()
        console.print(Align.center(make_menu_table(repos)))
        console.print()

        if info_by_number:
            console.print(Align.center(make_user_table(info_by_number)))
            console.print()

        prompt = (
            f"Masukkan pilihan [1..{len(repos)}/up/usr/rusr/q]: "
            if repos else "Masukkan pilihan [up/usr/rusr/q]: "
        )
        pilihan = console.input(prompt).strip().lower()

        if pilihan == "q":
            console.print("[bold red]Keluar dari menu... 👋[/bold red]")
            raise SystemExit(0)

        if pilihan == "up":
            update_all_repos(repos)
            continue

        if pilihan == "usr":
            sync_users()
            continue

        if pilihan == "rusr":
            remove_or_name_user_menu()
            continue

        if pilihan.isdigit():
            idx = int(pilihan) - 1
            if 0 <= idx < len(repos):
                run_python(repos[idx])
            else:
                console.print("[bold red]❌ Nomor tidak valid.[/bold red]")
                input("ENTER...")
        else:
            console.print("[bold red]❌ Pilihan tidak dikenali.[/bold red]")
            input("ENTER...")

if __name__ == "__main__":
    auto_update_repo()
    main()
