#!/usr/bin/env python3
import os
import json
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


# =====================================================
#  SUPER CLEAR
# =====================================================
def super_clear():
    os.system("printf '\\033c'")
    console.clear()


# =====================================================
#  CARI FOLDER DGN main.py
# =====================================================
def find_repos_with_mainpy():
    repos = []
    for p in sorted(HOME.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith(".") and (p / "main.py").is_file():
            repos.append(p)
    return repos


# =====================================================
#  CARI refresh-tokens.json
# =====================================================
def find_token_files():
    token_files = []
    for p in sorted(HOME.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        f = p / "refresh-tokens.json"
        if f.is_file():
            token_files.append(f)
    return token_files


# =====================================================
#  LOAD JSON LIST AMAN
# =====================================================
def load_tokens(path: Path) -> List[Dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []
    except Exception:
        return []


# =====================================================
#  KEY DEDUP (UTAMA number+subscriber_id)
# =====================================================
def make_key(item: Dict) -> Tuple:
    number = str(item.get("number", "")).strip()
    sid = str(item.get("subscriber_id", "")).strip()
    rt = str(item.get("refresh_token", "")).strip()

    if number and sid:
        return ("ns", number, sid)
    if rt:
        return ("rt", rt)
    return ("raw", number, sid, rt)


# =====================================================
#  DEDUP LIST
# =====================================================
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


# =====================================================
#  MERGE UNION SEMUA FILE TANPA DUPLIKAT
# =====================================================
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


# =====================================================
#  SYNC USERS (usr) + bersihkan duplikat
# =====================================================
def sync_users():
    super_clear()
    token_files = find_token_files()

    if not token_files:
        console.print(Panel.fit(
            "[bold red]❌ Tidak ada refresh-tokens.json ditemukan.[/bold red]",
            border_style="red"
        ))
        input("\nENTER...")
        return

    all_data = []
    for f in token_files:
        cleaned = dedup_list(load_tokens(f))
        all_data.append(cleaned)

    merged = merge_unique(all_data)

    changed_files = 0
    added_total = 0
    cleaned_total = 0

    for f in token_files:
        old_raw = load_tokens(f)
        old = dedup_list(old_raw)

        old_keys = {make_key(x) for x in old}
        merged_keys = {make_key(x) for x in merged}

        new_keys = merged_keys - old_keys
        added_total += len(new_keys)
        cleaned_total += (len(old_raw) - len(old))

        if new_keys or (len(old_raw) != len(old)) or (len(old) != len(merged)):
            changed_files += 1

        f.write_text(
            json.dumps(merged, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    console.print(Panel.fit(
        f"[bold green]✅ Sinkronisasi selesai & duplikat dibersihkan![/bold green]\n"
        f"[cyan]Total file ditemukan:[/cyan] {len(token_files)}\n"
        f"[cyan]File berubah:[/cyan] {changed_files}\n"
        f"[cyan]Total data baru ditambahkan:[/cyan] {added_total}\n"
        f"[cyan]Total duplikat dibersihkan:[/cyan] {cleaned_total}\n"
        f"[cyan]Total data union sekarang:[/cyan] {len(merged)}",
        border_style="green"
    ))
    input("\nENTER untuk kembali ke menu...")


# =====================================================
#  REMOVE USER (rusr)
# =====================================================
def remove_user_menu():
    super_clear()
    token_files = find_token_files()

    if not token_files:
        console.print(Panel.fit(
            "[bold red]❌ Tidak ada refresh-tokens.json ditemukan.[/bold red]",
            border_style="red"
        ))
        input("\nENTER...")
        return

    # load + dedup semua file
    all_data = [dedup_list(load_tokens(f)) for f in token_files]
    merged = merge_unique(all_data)

    # ambil daftar nomor unik
    numbers = sorted({str(x.get("number")).strip() for x in merged if x.get("number")})

    if not numbers:
        console.print(Panel.fit(
            "[bold yellow]Tidak ada nomor tersimpan.[/bold yellow]",
            border_style="yellow"
        ))
        input("\nENTER...")
        return

    # tampilkan rich table nomor
    t = Table(
        title="[bold red]📛 DAFTAR NOMOR TERSIMPAN (rusr)[/bold red]",
        title_justify="center",
        box=box.ROUNDED,
        border_style="red",
        width=60
    )
    t.add_column("No", justify="center", style="bold cyan")
    t.add_column("Number", justify="left", style="white")

    for i, num in enumerate(numbers, start=1):
        t.add_row(str(i), num)

    console.print(t)
    console.print()

    pilih = console.input(
        "[bold white]Pilih nomor yg mau dihapus [index / ketik nomornya / b=back]: [/bold white]"
    ).strip().lower()

    if pilih == "b":
        return

    # tentukan nomor target
    target = None
    if pilih.isdigit():
        idx = int(pilih) - 1
        if 0 <= idx < len(numbers):
            target = numbers[idx]
    else:
        # kalau user mengetik langsung nomor
        if pilih in numbers:
            target = pilih

    if not target:
        console.print("[bold red]❌ Pilihan tidak valid.[/bold red]")
        input("ENTER...")
        return

    # hapus dari merged union
    new_merged = [x for x in merged if str(x.get("number")).strip() != target]

    # tulis balik ke semua file dengan union yang sudah dibersihkan
    for f in token_files:
        f.write_text(
            json.dumps(new_merged, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    console.print(Panel.fit(
        f"[bold green]✅ Nomor {target} telah dihapus dari semua refresh-tokens.json[/bold green]\n"
        f"[cyan]Total data sekarang:[/cyan] {len(new_merged)}",
        border_style="green"
    ))
    input("\nENTER untuk kembali ke menu...")


# =====================================================
#  JALANKAN python main.py
# =====================================================
def run_python(repo_path: Path):
    super_clear()
    console.print(
        Panel.fit(
            f"[bold cyan]Menjalankan:[/bold cyan] [yellow]{repo_path.name}[/yellow]\n"
            f"[dim]python main.py[/dim]",
            border_style="cyan",
        )
    )

    try:
        subprocess.run(["python", "main.py"], cwd=str(repo_path))
    except FileNotFoundError:
        console.print("[bold red]❌ Python tidak ditemukan. Install python dulu.[/bold red]")

    input("\nENTER untuk kembali ke menu...")


# =====================================================
#  UPDATE SEMUA REPO (git pull)
# =====================================================
def update_all_repos(repos):
    super_clear()
    console.print(
        Panel.fit("[bold yellow]Update semua repositori (git pull)[/bold yellow]",
                  border_style="yellow")
    )

    if not repos:
        console.print("[dim]Tidak ada repo dengan main.py.[/dim]")
        input("\nENTER...")
        return

    for repo in repos:
        if not (repo / ".git").exists():
            console.print(f"[dim]- {repo.name} (skip, bukan git repo)[/dim]")
            continue

        console.print(f"\n[bold cyan]▶ {repo.name}[/bold cyan]")

        try:
            res = subprocess.run(
                ["git", "pull"],
                cwd=str(repo),
                capture_output=True,
                text=True
            )
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()

            if res.returncode == 0:
                console.print(f"[green]{out if out else '✓ up-to-date'}[/green]")
            else:
                console.print(f"[bold red]{err if err else '❌ gagal pull'}[/bold red]")

        except FileNotFoundError:
            console.print("[bold red]❌ Git belum terinstall.[/bold red]")
            break

    input("\nENTER untuk kembali ke menu...")


# =====================================================
#  TABEL WELCOME
# =====================================================
def make_welcome_table():
    t = Table(show_header=False, box=box.DOUBLE, width=52, border_style="cyan")
    t.add_column(justify="center")
    t.add_row("[bold yellow]🌟 SELAMAT DATANG DI TERMUX 🌟[/bold yellow]")
    t.add_row("[dim]BY JONI WIJAYA FATHONI[/dim]")
    return t


# =====================================================
#  TABEL PROGRAM
# =====================================================
def make_program_table(repos):
    t = Table(
        title="[bold green]📂 DAFTAR PROGRAM[/bold green]",
        title_justify="center",
        box=box.ROUNDED,
        border_style="green",
        width=52
    )
    t.add_column("No", justify="center", style="bold cyan")
    t.add_column("Program", justify="left")

    if repos:
        for i, repo in enumerate(repos, start=1):
            t.add_row(str(i), f"Jalankan [yellow]{repo.name}[/yellow]")
    else:
        t.add_row("-", "[dim]Tidak ada folder dengan main.py[/dim]")

    t.add_row("up", "Update semua repo (git pull)")
    t.add_row("usr", "Sinkron & bersihkan refresh-tokens.json")
    t.add_row("rusr", "Lihat & hapus nomor dari semua tokens")
    t.add_row("m", "Keluar menu (shell biasa)")
    t.add_row("q", "Keluar Termux")

    return t


# =====================================================
#  TUTUP TERMUX BENERAN
# =====================================================
def close_termux():
    if os.system("command -v termux-activity-stop >/dev/null 2>&1") == 0:
        os.system("termux-activity-stop")
        return
    try:
        os.system("pkill -f com.termux")
    except:
        pass


# =====================================================
#  MAIN LOOP
# =====================================================
def main():
    while True:
        super_clear()
        repos = find_repos_with_mainpy()

        console.print(Align.center(make_welcome_table()))
        console.print()
        console.print(Align.center(make_program_table(repos)))
        console.print()

        prompt = f"Masukkan pilihan [1..{len(repos)}/up/usr/rusr/m/q]: " if repos else "Masukkan pilihan [up/usr/rusr/m/q]: "
        pilih = console.input(f"[bold white]{prompt}[/bold white]").strip().lower()

        if pilih == "m":
            console.print("\n[bold cyan]Keluar menu. Shell biasa aktif.[/bold cyan]")
            break

        if pilih == "q":
            console.print("\n[bold red]Menutup Termux... sampai jumpa! 👋[/bold red]")
            close_termux()
            raise SystemExit(0)

        if pilih == "up":
            update_all_repos(repos)
            continue

        if pilih == "usr":
            sync_users()
            continue

        if pilih == "rusr":
            remove_user_menu()
            continue

        if pilih.isdigit():
            idx = int(pilih) - 1
            if 0 <= idx < len(repos):
                run_python(repos[idx])
            else:
                console.print("[bold red]❌ Nomor tidak valid.[/bold red]")
                input("ENTER...")
        else:
            console.print("[bold red]❌ Pilihan tidak dikenali.[/bold red]")
            input("ENTER...")


if __name__ == "__main__":
    main()
