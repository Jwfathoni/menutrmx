#!/usr/bin/env python3
"""
Auto Purchase XL - Multi Account (Termux / Linux)

- Loop semua akun dari refresh-tokens.json
- Integrasi dengan script CLI utama (main.py)
- Cocok dipanggil dari menutrmx (menu.py) via opsi "Xa" (misal 1a, 2a, dst)
"""

import sys
import os
import time
import argparse
import json
from datetime import datetime

try:
    import pexpect
except ImportError:
    print("❌ pexpect belum terinstall.")
    print("Jalankan: pip install pexpect")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.align import Align
except ImportError:
    print("❌ rich belum terinstall.")
    print("Jalankan: pip install rich")
    sys.exit(1)

console = Console()


class MultiAccountPurchase:
    def __init__(self, timeout=180):
        self.timeout = timeout
        self.child = None
        self.accounts = []
        self.results = []  # (account, result_bool)

    # ================== UTIL & UI ==================
    def step(self, message: str, status: str = "info", indent: int = 0):
        icons = {
            'info': '📋', 'success': '✅', 'warning': '⚠️', 'error': '❌',
            'processing': '⏳', 'sending': '📤', 'shopping': '🛒',
            'account': '👤', 'switch': '🔄',
        }
        colors = {
            'info': 'cyan', 'success': 'green', 'warning': 'yellow',
            'error': 'red', 'processing': 'blue', 'sending': 'magenta',
            'shopping': 'bright_cyan', 'account': 'bright_magenta', 'switch': 'bright_yellow',
        }
        icon = icons.get(status, '•')
        color = colors.get(status, 'white')
        indent_str = "  " * indent
        timestamp = datetime.now().strftime('%H:%M:%S')
        console.print(f"[dim]{timestamp}[/dim] {indent_str}[{color}]{icon} {message}[/{color}]")

    # ================== TOKENS ==================
    def load_accounts(self, tokens_file='refresh-tokens.json'):
        """Load saved accounts dari refresh-tokens.json (array of object)."""
        try:
            if not os.path.exists(tokens_file):
                console.print(f"[red]❌ File tidak ditemukan: {tokens_file}[/red]")
                return False
            with open(tokens_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                self.accounts = [str(acc.get('number', f'Account_{i}')) for i, acc in enumerate(data)]
            else:
                console.print("[red]❌ Struktur JSON invalid (harus array)[/red]")
                return False

            if not self.accounts:
                console.print("[red]❌ Tidak ada akun di file tokens[/red]")
                return False

            console.print(f"[green]✓ {len(self.accounts)} akun berhasil dimuat[/green]")
            return True

        except json.JSONDecodeError as e:
            console.print(f"[red]❌ JSON error: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error saat load accounts: {e}[/red]")
            return False

    def show_accounts_table(self):
        table = Table(title="[bold cyan]Saved Accounts[/bold cyan]", box=box.ROUNDED)
        table.add_column("No", style="cyan", justify="center")
        table.add_column("Account Number", style="yellow")
        table.add_column("Status", style="green")
        for idx, account in enumerate(self.accounts, 1):
            table.add_row(str(idx), str(account), "Ready")
        console.print(table)
        console.print()

    # ================== MAIN.PY INTERACTION ==================
    def start_program(self):
        """Start main.py (di direktori yang sama dengan neutral2.py)."""
        self.step("Starting main.py...", status='processing')
        project_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            os.chdir(project_dir)
        except Exception:
            pass

        cmd = f'"{sys.executable}" -u main.py'
        with console.status("[cyan]Initializing CLI...[/cyan]", spinner="dots"):
            self.child = pexpect.spawn(cmd, encoding='utf-8', timeout=self.timeout)
            time.sleep(2)

        # Handle "Press Enter" awal kalau ada
        try:
            idx = self.child.expect([r'Press Enter to continue', r'Press enter', pexpect.TIMEOUT], timeout=3)
            if idx != 2:
                self.step("Handling initial prompt", status='info', indent=1)
                self.child.sendline('')
                time.sleep(1)
        except Exception:
            pass

        self.step("Program initialized", status='success')
        time.sleep(1)

    def wait_and_send(self, patterns, response, description="", show_step=True, timeout=None):
        """Tunggu pattern, lalu kirim response."""
        if isinstance(patterns, str):
            patterns = [patterns]
        if timeout is None:
            timeout = self.timeout

        try:
            if show_step:
                self.step(f"Menunggu: {description}", status='processing', indent=2)

            index = self.child.expect(patterns, timeout=timeout)

            if show_step:
                self.step(f"Ketemu: {patterns[index]}", status='success', indent=3)
                self.step("Sending Request To Neutral Server...", status='sending', indent=3)

            self.child.sendline(response)
            time.sleep(1)
            return index
        except pexpect.TIMEOUT:
            if show_step:
                self.step(f"TIMEOUT: {description}", status='error', indent=3)
            return None
        except pexpect.EOF:
            if show_step:
                self.step("Program terminated (EOF)", status='error', indent=3)
            return None

    def switch_account(self, account_index: int):
        """Pindah ke akun tertentu via menu account di main.py"""
        console.print()
        self.step(f"Switching to account #{account_index + 1}: {self.accounts[account_index]}",
                  status='switch', indent=1)

        # buka menu akun
        self.step("Opening account menu", status='processing', indent=2)
        self.child.sendline('1')
        time.sleep(0.8)

        try:
            idx = self.child.expect(
                [r'SAVED ACCOUNTS', r'Pilihan', r'No users', r'Pilih menu', pexpect.TIMEOUT],
                timeout=5
            )
            if idx == 4:
                self.step("Timeout menunggu account menu", status='warning', indent=2)
                return False
        except Exception:
            self.step("Exception saat buka account menu", status='error', indent=2)
            return False

        time.sleep(0.3)

        # pilih akun (1,2,3,...)
        self.step(f"Selecting account number: {account_index + 1}", status='sending', indent=2)
        self.child.sendline(str(account_index + 1))
        time.sleep(2)

        try:
            self.child.expect(['Pilih menu', 'pilih menu'], timeout=5)
            self.step("Account switched successfully", status='success', indent=2)
            return True
        except pexpect.TIMEOUT:
            self.step("Gagal switch account (timeout)", status='error', indent=2)
            return False

    def purchase_single(self, family_code, package_number, choice, account_name=""):
        """1x proses beli untuk 1 akun (current user di main.py)."""
        console.print()
        console.rule(f"[bold cyan]Purchase Process - {account_name}[/bold cyan]", style="cyan")
        console.print()

        self.step("Starting transaction", status='shopping', indent=1)

        # press-enter kalau diminta
        try:
            idx = self.child.expect([r'Press Enter', r'Press enter', pexpect.TIMEOUT], timeout=2)
            if idx != 2:
                self.child.sendline('')
                time.sleep(1)
        except Exception:
            pass

        # dari main menu → pilih menu pembelian (opsi 6 di script kamu)
        self.step("Sending Request To Neutral Server...", status='sending', indent=2)
        try:
            self.child.sendline('6')
            time.sleep(2)
        except Exception:
            self.step("Gagal kirim opsi menu 6 (lanjut coba)", status='warning', indent=2)

        # input family code
        idx = self.wait_and_send(['Enter family code', 'family code'], family_code, 'Family Code')
        if idx is None:
            self.child.sendline(family_code)
            time.sleep(2)

        # pilih paket
        idx = self.wait_and_send(['Pilih paket', 'nomor'], str(package_number), 'Package Selection')
        if idx is None:
            self.child.sendline(str(package_number))
            time.sleep(2)

        # pilih aksi (misal 5 = beli, 4 = cek, dll)
        idx = self.wait_and_send(['Pilihan:', 'pilihan:'], str(choice), 'Action Choice')
        if idx is None:
            self.child.sendline(str(choice))
            time.sleep(2)

        console.print()
        self.step("Processing...", status='processing', indent=2)

        # tunggu hasil sukses / fail
        with console.status("[yellow]Waiting for result...[/yellow]", spinner="dots"):
            try:
                result_patterns = [
                    'Purchase successful!', 'SUCCESS', 'Purchase result:',
                    'transaction_code', 'Failed', 'FAILED', 'error',
                ]
                index = self.child.expect(result_patterns, timeout=120)
                console.print()

                # index 0..3 = dianggap sukses
                if index <= 3:
                    panel = Panel(
                        f"[bold green]✓ Purchase Completed![/bold green]\n\n"
                        f"[dim]Account: {account_name}[/dim]",
                        border_style="green", box=box.ROUNDED,
                        title="[bold green]SUCCESS[/bold green]"
                    )
                    console.print(panel)

                    # setelah sukses, beresin balik ke main menu
                    self._post_purchase_cleanup()
                    return True
                else:
                    panel = Panel(
                        f"[bold red]✗ Purchase Failed[/bold red]\n\n"
                        f"[dim]Account: {account_name}[/dim]",
                        border_style="red", box=box.ROUNDED,
                        title="[bold red]FAILED[/bold red]"
                    )
                    console.print(panel)
                    return False

            except pexpect.TIMEOUT:
                panel = Panel(
                    f"[bold yellow]⚠ Timeout menunggu hasil[/bold yellow]\n\n"
                    f"[dim]Account: {account_name}[/dim]",
                    border_style="yellow", box=box.ROUNDED,
                    title="[bold yellow]TIMEOUT[/bold yellow]"
                )
                console.print(panel)
                return False

    def _post_purchase_cleanup(self):
        """Balik ke main menu dari berbagai skenario (Press Enter / Pilih paket)."""
        self.step("Checking post-purchase prompts...", status='processing', indent=2)
        try:
            idx = self.child.expect(
                [r'Press Enter', r'Press enter', r'Pilih paket', r'pilih paket', r'Pilih menu', r'pilih menu'],
                timeout=6
            )
            if idx in (0, 1):
                # diminta tekan enter dulu
                self.step("Detected 'Press enter' prompt — sending Enter", status='info', indent=2)
                try:
                    self.child.sendline('')
                    time.sleep(0.5)
                except Exception:
                    pass
                # setelah enter, mungkin ketemu Pilih paket / Pilih menu
                try:
                    idx2 = self.child.expect(
                        [r'Pilih paket', r'pilih paket', r'Pilih menu', r'pilih menu'],
                        timeout=6
                    )
                    if idx2 in (0, 1):
                        self.step("Detected 'Pilih paket' — kirim '00' untuk balik menu", status='sending', indent=2)
                        self.child.sendline('00')
                        time.sleep(0.5)
                        try:
                            self.child.expect([r'Pilih menu', r'pilih menu'], timeout=6)
                            self.step("Returned to main menu", status='success', indent=2)
                        except pexpect.TIMEOUT:
                            self.step("Tidak lihat main menu setelah '00'", status='warning', indent=2)
                    else:
                        self.step("Already at main menu", status='success', indent=2)
                except pexpect.TIMEOUT:
                    self.step("Tidak ada 'Pilih paket' setelah Enter", status='warning', indent=2)

            elif idx in (2, 3):
                # langsung di Pilih paket
                self.step("Detected 'Pilih paket' — kirim '00' untuk balik menu", status='sending', indent=2)
                self.child.sendline('00')
                time.sleep(0.5)
                try:
                    self.child.expect([r'Pilih menu', r'pilih menu'], timeout=6)
                    self.step("Returned to main menu", status='success', indent=2)
                except pexpect.TIMEOUT:
                    self.step("Tidak lihat main menu setelah '00'", status='warning', indent=2)
            else:
                self.step("Already at main menu", status='success', indent=2)

        except pexpect.TIMEOUT:
            self.step("Tidak ada prompt lanjut; coba Enter sekali lagi", status='warning', indent=2)
            try:
                self.child.sendline('')
                time.sleep(0.5)
            except Exception:
                pass

        time.sleep(1)

    # ================== CLEANUP & SUMMARY ==================
    def close(self):
        if self.child is not None:
            try:
                if self.child.isalive():
                    self.child.sendline('99')  # asumsi 99 = exit
                    try:
                        self.child.expect(pexpect.EOF, timeout=3)
                    except Exception:
                        pass
                self.child.close()
            except Exception:
                try:
                    self.child.close(force=True)
                except Exception:
                    pass

    def show_summary(self):
        console.print()
        console.rule("[bold cyan]Summary Report[/bold cyan]", style="cyan")
        console.print()

        table = Table(box=box.ROUNDED)
        table.add_column("No", style="cyan", justify="center")
        table.add_column("Account", style="yellow")
        table.add_column("Result", style="white")

        for idx, (account, result) in enumerate(self.results, 1):
            status_text = "[green]✓ Success[/green]" if result else "[red]✗ Failed[/red]"
            table.add_row(str(idx), str(account), status_text)

        console.print(table)
        success_count = sum(1 for _, r in self.results if r)
        total = len(self.results)

        console.print()
        if total == 0:
            console.print("[yellow]Tidak ada akun yang diproses.[/yellow]")
        elif success_count == total:
            console.print(f"[bold green]🎉 Semua transaksi sukses! ({success_count}/{total})[/bold green]")
        elif success_count > 0:
            console.print(f"[bold yellow]⚠ Partial success: {success_count}/{total}[/bold yellow]")
        else:
            console.print(f"[bold red]❌ Semua transaksi gagal (0/{total})[/bold red]")


def main():
    parser = argparse.ArgumentParser(prog='Auto Purchase XL - Multi Account (Termux)')
    parser.add_argument('--tokens', default='refresh-tokens.json', help='Path to tokens file')
    parser.add_argument('--family', default='f4fd69c7-12a4-4047-a1f2-f4072a7c543e')
    parser.add_argument('--package', type=int, default=19)
    parser.add_argument('--choice', type=int, default=5)
    parser.add_argument('--delay', type=int, default=3, help='Delay antara akun (detik)')
    parser.add_argument('--confirm', action='store_true', help='Skip konfirmasi & langsung jalan')
    args = parser.parse_args()

    console.print()
    header = Panel(
        Align.center(
            "[bold cyan]AUTO BUY MASTIF XL[/bold cyan]\n"
            "[dim]Multi-Account Mode (Termux)[/dim]\n"
            "[dim]BY Neutral[/dim]"
        ),
        border_style="cyan", box=box.DOUBLE, padding=(1, 2)
    )
    console.print(header)
    console.print()

    auto = MultiAccountPurchase(timeout=180)

    if not auto.load_accounts(args.tokens):
        console.print("[red]Keluar karena tidak bisa load akun.[/red]")
        return

    auto.show_accounts_table()

    if not args.confirm:
        confirm = console.input(f"[cyan]Proses {len(auto.accounts)} akun?[/cyan] (y/n): ")
        if confirm.lower() != 'y':
            console.print("[yellow]Dibatalkan oleh user.[/yellow]")
            return
    else:
        console.print("[green]Auto-confirm aktif; langsung proses semua akun...[/green]")

    try:
        auto.start_program()

        for idx, account in enumerate(auto.accounts):
            console.print()
            console.rule(f"[bold yellow]Account {idx + 1}/{len(auto.accounts)}[/bold yellow]", style="yellow")
            console.print()

            if not auto.switch_account(idx):
                console.print(f"[red]Gagal switch ke account {idx + 1}, skip...[/red]")
                auto.results.append((account, False))
                continue

            result = auto.purchase_single(args.family, args.package, args.choice, account)
            auto.results.append((account, result))

            if idx < len(auto.accounts) - 1:
                console.print(f"\n[dim]Tunggu {args.delay}s sebelum akun berikutnya...[/dim]")
                time.sleep(args.delay)

        auto.show_summary()
        console.print("\n[dim]Tekan ENTER untuk keluar...[/dim]")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Dihentikan oleh user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        auto.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)
