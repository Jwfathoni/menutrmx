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
#  AUTO UPDATE REPO (git pull)
# =====================================================
def auto_update_repo():
    """Jika menu.py berada dalam folder git, lakukan git pull otomatis."""
    try:
        repo_dir = Path(__file__).resolve().parent
    except Exception:
        return

    if not (repo_dir / ".git").is_dir():
        return  # bukan repo git, diam saja

    try:
        console.print("[dim]🔄 Mohon tunggu, sedang memeriksa dan memperbarui menu...[/dim]")
        res = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True
        )
        out = (res.stdout or "").strip().lower()

        if res.returncode == 0:
            if out and "already up to date" not in out:
                console.print("[bold green]✅ Menu berhasil diperbarui ke versi terbaru.[/bold green]")
            else:
                console.print("[bold cyan]✔️ Menu sudah dalam versi terbaru. Tidak ada pembaruan diperlukan.[/bold cyan]")
    except:
        pass  # kalau error, diam saja


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
#  MERGE UNION SEMUA FILE
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
#  LOAD SEMUA TOKEN + UNION
# =====================================================
def load_all_tokens_union():
    token_files = find_token_files()
    all_data = [dedup_list(load_tokens(f)) for f in token_files]
    merged = merge_unique(all_data)
    return token_files, merged


# =====================================================
#  SYNC USERS (usr)
# =====================================================
def sync_users():
    super_clear()
    token_files = find_token_files()

    if not token_files:
        console.print(Panel.fit("[bold red]❌ Tidak ada refresh-tokens.json ditemukan.[/bold red]", border_style="red"))
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

        if new_keys or len(old_raw) != len(old) or len(old) != len(merged):
            changed_files += 1

        f.write_text(json.dumps(merged, indent=4, ensure_ascii=False), encoding="utf-8")

    console.print(Panel.fit(
        f"[bold green]✅ Sinkronisasi selesai.[/bold green]\n"
        f"[cyan]File tokens ditemukan:[/cyan] {len(token_files)}\n"
        f"[cyan]Data baru ditambahkan:[/cyan] {added_total}\n"
        f"[cyan]Duplikat dibersihkan:[/cyan] {cleaned_total}\n"
        f"[cyan]Total data sekarang:[/cyan] {len(merged)}",
        border_style="green"
    ))
    input("\nENTER...")


# =====================================================
#  RUSR SUB-MENU
# =====================================================
def remove_or_name_user_menu():
    super_clear()
    token_files, merged = load_all_tokens_union()

    if not merged:
        console.print(Panel.fit("[bold yellow]Tidak ada data user.[/bold yellow]", border_style="yellow"))
        input("\nENTER...")
        return

    # kumpulkan nomor & nama
    info = {}
    for item in merged:
        num = str(item.get("number", "")).strip()
        if not num:
            continue
        name = str(item.get("name", "")).strip()
        if num not in info or not info[num]:
            info[num] = name

    panel = Panel.fit(
        "[bold magenta]RUSR - Manajemen User[/bold magenta]\n\n"
        "[cyan]1.[/cyan] Beri/ubah [bold]nama[/bold] pada nomor\n"
        "[cyan]2.[/cyan] Hapus [bold]semua data yang terkait nomor tertentu[/bold]\n"
        "    (menghapus seluruh record dengan nomor tersebut di semua file)\n"
        "[cyan]b.[/cyan] Kembali",
        border_style="magenta"
    )
    console.print(panel)

    choice = console.input("[bold white]Pilih opsi [1/2/b]: [/bold white]").strip().lower()
    if choice == "1":
        name_user_flow(token_files, merged, info)
    elif choice == "2":
        delete_user_flow(token_files, merged, info)


# =====================================================
#  BERI / UBAH NAMA
# =====================================================
def name_user_flow(token_files, merged, info):
    super_clear()
    numbers = sorted(info.keys())

    t = Table(title="[bold green]📇 Beri/Ubah Nama Nomor[/bold green]", box=box.ROUNDED, border_style="green", width=70)
    t.add_column("No", justify="center")
    t.add_column("Number")
    t.add_column("Name")

    for i, num in enumerate(numbers, start=1):
        t.add_row(str(i), num, info[num] or "-")

    console.print(t)
    pilihan = console.input("\nPilih nomor [index/nomor/b]: ").strip()

    if pilihan == "b":
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

    new_name = console.input(f"Masukkan nama untuk {target}: ").strip()
    if not new_name:
        console.print("[yellow]Dibatalkan. Nama kosong.[/yellow]")
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
        f"✅ Nama untuk nomor {target} telah diperbarui menjadi: [yellow]{new_name}[/yellow]\n"
        f"Total data diupdate: {updated}",
        border_style="green"
    ))
    input("ENTER...")


# =====================================================
#  HAPUS SEMUA DATA NOMOR
# =====================================================
def delete_user_flow(token_files, merged, info):
    super_clear()
    numbers = sorted(info.keys())

    t = Table(title="[bold red]🗑️ Hapus Semua Data Nomor[/bold red]", box=box.ROUNDED, border_style="red", width=70)
    t.add_column("No", justify="center")
    t.add_column("Number")
    t.add_column("Name")

    for i, num in enumerate(numbers, start=1):
        t.add_row(str(i), num, info[num] or "-")

    console.print(t)
    pilihan = console.input("\nPilih nomor [index/nomor/b]: ").strip()

    if pilihan == "b":
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

    konfirmasi = console.input(
        f"[bold red]Yakin ingin menghapus SEMUA data yang terkait nomor {target}? (y/n): [/bold red]"
    ).strip().lower()

    if konfirmasi != "y":
        console.print("[yellow]Dibatalkan.[/yellow]")
        input("ENTER...")
        return

    jumlah_awal = len(merged)
    merged = [x for x in merged if str(x.get("number")).strip() != target]
    terhapus = jumlah_awal - len(merged)

    for f in token_files:
        f.write_text(json.dumps(merged, indent=4, ensure_ascii=False), encoding="utf-8")

    console.print(Panel.fit(
        f"✅ Semua data dengan nomor {target} telah dihapus.\n"
        f"Total data dihapus: {terhapus}",
        border_style="green"
    ))
    input("ENTER...")


# =====================================================
#  JALANKAN PROGRAM main.py
# =====================================================
def run_python(repo_path: Path):
    super_clear()
    console.print(
        Panel.fit(
            f"[cyan bold]Menjalankan: {repo_path.name}[/cyan bold]\n"
            "[dim]python main.py[/dim]",
            border_style="cyan"
        )
    )
    try:
        subprocess.run(["python", "main.py"], cwd=str(repo_path))
    except FileNotFoundError:
        console.print("[red bold]Python tidak ditemukan.[/red bold]")

    input("ENTER untuk kembali...")


# =====================================================
#  UPDATE SEMUA REPO
# =====================================================
def update_all_repos(repos):
    super_clear()
    console.print(Panel.fit("[yellow bold]Mengupdate semua repo (git pull)...[/yellow bold]", border_style="yellow"))

    for repo in repos:
        if not (repo / ".git").exists():
            console.print(f"[dim]- {repo.name}: skip (bukan repo git)[/dim]")
            continue

        console.print(f"[cyan]▶ {repo.name}[/cyan]")
        subprocess.run(["git", "pull"], cwd=str(repo))

    input("ENTER...")


# =====================================================
#  TABEL WELCOME
# =====================================================
def make_welcome():
    t = Table(show_header=False, box=box.DOUBLE, width=52, border_style="cyan")
    t.add_column(justify="center")
    t.add_row("[bold yellow]🌟 SELAMAT DATANG DI TERMUX 🌟[/bold yellow]")
    t.add_row("[dim]BY JONI WIJAYA FATHONI[/dim]")
    return t


# =====================================================
#  TABEL PROGRAM
# =====================================================
def make_menu_table(repos):
    t = Table(
        title="[bold green]📂 MENU UTAMA[/bold green]",
        title_justify="center",
        width=52,
        box=box.ROUNDED,
        border_style="green"
    )
    t.add_column("Key", justify="center", style="bold cyan")
    t.add_column("Aksi", justify="left")

    if repos:
        for i, r in enumerate(repos, start=1):
            t.add_row(str(i), f"Jalankan program [yellow]{r.name}[/yellow]")
    else:
        t.add_row("-", "[dim]Tidak ada folder dengan main.py[/dim]")

    t.add_row("up", "Update semua repo (git pull)")
    t.add_row("usr", "Sinkron & bersihkan refresh-tokens.json")
    t.add_row("rusr", "Kelola user (beri nama / hapus data nomor)")
    t.add_row("m", "Keluar ke shell")
    t.add_row("q", "Keluar Termux")
    return t


# =====================================================
#  TUTUP TERMUX
# =====================================================
def close_termux():
    if os.system("command -v termux-activity-stop >/dev/null 2>&1") == 0:
        os.system("termux-activity-stop")
    else:
        os.system("pkill -f com.termux")


# =====================================================
#  MAIN LOOP
# =====================================================
def main():
    while True:
        super_clear()
        repos = find_repos_with_mainpy()

        console.print(Align.center(make_welcome()))
        console.print()
        console.print(Align.center(make_menu_table(repos)))
        console.print()

        prompt = (
            f"Masukkan pilihan [1..{len(repos)}/up/usr/rusr/m/q]: "
            if repos else "Masukkan pilihan [up/usr/rusr/m/q]: "
        )
        pilih = console.input(f"[bold white]{prompt}[/bold white]").strip().lower()

        if pilih == "m":
            console.print("[cyan]Keluar menu...[/cyan]")
            break

        if pilih == "q":
            console.print("[red bold]Menutup Termux... sampai jumpa![/red bold]")
            close_termux()
            raise SystemExit(0)

        if pilih == "up":
            update_all_repos(repos)
            continue

        if pilih == "usr":
            sync_users()
            continue

        if pilih == "rusr":
            remove_or_name_user_menu()
            continue

        if pilih.isdigit():
            idx = int(pilih) - 1
            if 0 <= idx < len(repos):
                run_python(repos[idx])
            else:
                console.print("[red]Nomor tidak valid.[/red]")
                input("ENTER...")
        else:
            console.print("[red]Pilihan tidak dikenal.[/red]")
            input("ENTER...")


if __name__ == "__main__":
    auto_update_repo()  # 🔄 update repo sebelum menu tampil
    main()
