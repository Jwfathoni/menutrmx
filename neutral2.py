#!/usr/bin/env python3
"""
Auto Purchase - Multi Account Version (Termux / Linux)
Otomatis loop semua saved accounts dari refresh-tokens.json
"""

import sys
import os
import time
import argparse
import json
from datetime import datetime

# ==== DEPENDENCIES ====
try:
    import pexpect
except ImportError:
    print("❌ pexpect not installed!")
    print("Please run: pip install pexpect")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.align import Align
except ImportError:
    print("❌ rich not installed!")
    print("Please run: pip install rich")
    sys.exit(1)

console = Console()


class MultiAccountPurchase:
    def __init__(self, timeout=180):
        self.timeout = timeout
        self.child = None
        self.accounts = []
        self.results = []  # Track results per account

    def load_accounts(self, tokens_file='refresh-tokens.json'):
        """Load saved accounts from refresh-tokens.json"""
        try:
            if not os.path.exists(tokens_file):
                console.print(f"[red]❌ File not found: {tokens_file}[/red]")
                return False

            with open(tokens_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                self.accounts = [str(acc.get('number', f'Account_{i}')) for i, acc in enumerate(data)]
            else:
                console.print("[red]❌ Invalid JSON structure (expected array)[/red]")
                return False

            if not self.accounts:
                console.print("[red]❌ No accounts found in file[/red]")
                return False

            console.print(f"[green]✓ Loaded {len(self.accounts)} account(s)[/green]")
            return True

        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Invalid JSON: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error loading accounts: {e}[/red]")
            return False

    def show_accounts_table(self):
        """Display accounts in a nice table"""
        table = Table(title="[bold cyan]Saved Accounts[/bold cyan]", box=box.ROUNDED)
        table.add_column("No", style="cyan", justify="center")
        table.add_column("Account Number", style="yellow")
        table.add_column("Status", style="green")

        for idx, account in enumerate(self.accounts, 1):
            table.add_row(str(idx), str(account), "Ready")

        console.print(table)
        console.print()

    def step(self, message: str, status: str = "info", indent: int = 0):
        """Print formatted step"""
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

    def start_program(self):
        """Start main.py"""
        self.step("Starting main.py...", status='processing')

        project_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            os.chdir(project_dir)
        except Exception:
            pass

        cmd = f'"{sys.executable}" -u main.py'

        with console.status("[cyan]Initializing...", spinner="dots"):
            # pexpect untuk Termux / Linux
            self.child = pexpect.spawn(
                cmd,
                encoding='utf-8',
                timeout=self.timeout
            )
            time.sleep(2)

        # Handle initial "Press Enter" prompt
        try:
            index = self.child.expect([
                r'Press Enter to continue',
                r'Press enter',
                pexpect.TIMEOUT
            ], timeout=3)

            if index != 2:
                self.step("Handling initial prompt", status='info', indent=1)
                self.child.sendline('')
                time.sleep(1)
        except Exception:
            pass

        self.step("Program initialized", status='success')
        time.sleep(1)

    def wait_and_send(self, patterns, response, description="", show_step=True, timeout=None):
        """Wait for pattern and send response. Optional timeout overrides default."""
        if isinstance(patterns, str):
            patterns = [patterns]
        if timeout is None:
            timeout = self.timeout

        try:
            if show_step:
                self.step(f"Waiting for: {description}", status='processing', indent=2)

            index = self.child.expect(patterns, timeout=timeout)

            if show_step:
                self.step(f"Found: {patterns[index]}", status='success', indent=3)
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
                self.step("Program terminated", status='error', indent=3)
            return None

    def switch_account(self, account_index):
        """Switch to specific account"""
        console.print()
        self.step(f"Switching to account #{account_index + 1}: {self.accounts[account_index]}", status='switch', indent=1)

        # Open account menu immediately (don't wait long for main menu)
        self.step("Opening account menu", status='processing', indent=2)
        self.child.sendline('1')
        time.sleep(0.8)

        # Wait for saved accounts prompt or a quick menu indicator
        try:
            idx = self.child.expect(
                [r'SAVED ACCOUNTS', r'Pilihan', r'No users', r'Pilih menu', pexpect.TIMEOUT],
                timeout=5
            )
            if idx == 4:
                self.step("Timeout waiting for account menu", status='warning', indent=2)
                return False
        except Exception:
            self.step("Exception while opening account menu", status='error', indent=2)
            return False

        time.sleep(0.3)

        # Select account by number (account_index + 1)
        self.step(f"Selecting account number: {account_index + 1}", status='sending', indent=2)
        self.child.sendline(str(account_index + 1))
        time.sleep(2)

        # Wait for confirmation or return to main menu
        try:
            self.child.expect(['Pilih menu', 'pilih menu'], timeout=5)
            self.step(f"Account switched successfully", status='success', indent=2)
            return True
        except pexpect.TIMEOUT:
            self.step(f"Failed to switch account", status='error', indent=2)
            return False

    def purchase_single(self, family_code, package_number, choice, account_name=""):
        """Execute single purchase for current account"""
        console.print()
        console.rule(f"[bold cyan]Purchase Process - {account_name}[/bold cyan]", style="cyan")
        console.print()

        self.step("Starting transaction", status='shopping', indent=1)

        # Check press-enter
        try:
            idx = self.child.expect([r'Press Enter', r'Press enter', pexpect.TIMEOUT], timeout=2)
            if idx != 2:
                self.child.sendline('')
                time.sleep(1)
        except Exception:
            pass

        # Main Menu - We're already at main menu; send option 6 directly
        self.step("Sending Request To Neutral Server...", status='sending', indent=2)
        try:
            self.child.sendline('6')
            time.sleep(2)
        except Exception:
            self.step("Failed to send menu option 6; continuing", status='warning', indent=2)

        # Family Code
        idx = self.wait_and_send(['Enter family code', 'family code'], family_code, 'Family Code')
        if idx is None:
            self.child.sendline(family_code)
            time.sleep(2)

        # Package
        idx = self.wait_and_send(['Pilih paket', 'nomor'], str(package_number), 'Package Selection')
        if idx is None:
            self.child.sendline(str(package_number))
            time.sleep(2)

        # Choice
        idx = self.wait_and_send(['Pilihan:', 'pilihan:'], str(choice), 'Action Choice')
        if idx is None:
            self.child.sendline(str(choice))
            time.sleep(2)

        # Wait for result
        console.print()
        self.step("Processing...", status='processing', indent=2)

        with console.status("[yellow]Waiting for result...", spinner="dots"):
            try:
                result_patterns = [
                    'Purchase successful!', 'SUCCESS', 'Purchase result:',
                    'transaction_code', 'Failed', 'FAILED', 'error',
                ]

                index = self.child.expect(result_patterns, timeout=120)
                console.print()

                if index <= 3:  # Success
                    panel = Panel(
                        f"[bold green]✓ Purchase Completed![/bold green]\n\n"
                        f"[dim]Account: {account_name}[/dim]",
                        border_style="green", box=box.ROUNDED,
                        title="[bold green]SUCCESS[/bold green]"
                    )
                    console.print(panel)

                    # After success: detect whether we see 'Press enter' or 'Pilih paket' and handle both flows
                    self.step("Checking post-purchase prompts...", status='processing', indent=2)
                    try:
                        idx = self.child.expect(
                            [r'Press Enter', r'Press enter', r'Pilih paket', r'pilih paket', r'Pilih menu', r'pilih menu'],
                            timeout=6
                        )
                        if idx in (0, 1):
                            self.step("Detected 'Press enter' prompt — sending Enter", status='info', indent=2)
                            try:
                                self.child.sendline('')
                                time.sleep(0.5)
                            except Exception:
                                pass
                            try:
                                idx2 = self.child.expect(
                                    [r'Pilih paket', r'pilih paket', r'Pilih menu', r'pilih menu'],
                                    timeout=6
                                )
                                if idx2 in (0, 1):
                                    self.step("Detected 'Pilih paket' prompt — Sending Request To Neutral Server...",
                                              status='sending', indent=2)
                                    self.child.sendline('00')
                                    time.sleep(0.5)
                                    try:
                                        self.child.expect([r'Pilih menu', r'pilih menu'], timeout=6)
                                        self.step("Returned to main menu", status='success', indent=2)
                                    except pexpect.TIMEOUT:
                                        self.step("Did not see main menu after sending '00'", status='warning', indent=2)
                                else:
                                    self.step("Already at main menu", status='success', indent=2)
                            except pexpect.TIMEOUT:
                                self.step("No 'Pilih paket' after pressing Enter; proceeding", status='warning', indent=2)
                        elif idx in (2, 3):
                            # Directly at 'Pilih paket'
                            self.step("Detected 'Pilih paket' prompt — Sending Request To Neutral Server...",
                                      status='sending', indent=2)
                            self.child.sendline('00')
                            time.sleep(0.5)
                            try:
                                self.child.expect([r'Pilih menu', r'pilih menu'], timeout=6)
                                self.step("Returned to main menu", status='success', indent=2)
                            except pexpect.TIMEOUT:
                                self.step("Did not see main menu after sending '00'", status='warning', indent=2)
                        else:
                            self.step("Already at main menu", status='success', indent=2)
                    except pexpect.TIMEOUT:
                        # Retry pressing Enter once
                        self.step("No post-purchase prompt detected; retrying Enter...", status='warning', indent=2)
                        try:
                            self.child.sendline('')
                            time.sleep(0.5)
                            idx3 = self.child.expect(
                                [r'Pilih paket', r'pilih paket', r'Pilih menu', r'pilih menu'],
                                timeout=6
                            )
                            if idx3 in (0, 1):
                                self.step("Detected 'Pilih paket' after retry — Sending Request To Neutral Server...",
                                          status='sending', indent=2)
                                self.child.sendline('00')
                                time.sleep(0.5)
                                try:
                                    self.child.expect([r'Pilih menu', r'pilih menu'], timeout=6)
                                    self.step("Returned to main menu", status='success', indent=2)
                                except pexpect.TIMEOUT:
                                    self.step("Did not see main menu after sending '00'", status='warning', indent=2)
                            elif idx3 in (2, 3):
                                self.step("Already at main menu after retry", status='success', indent=2)
                        except pexpect.TIMEOUT:
                            self.step("No post-purchase prompt after retry; proceeding", status='warning', indent=2)
                        except Exception:
                            self.step("Exception while retrying post-purchase prompts", status='warning', indent=2)

                    time.sleep(1)
                    return True
                else:  # Failed
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
                    f"[bold yellow]⚠ Timeout[/bold yellow]\n\n"
                    f"[dim]Account: {account_name}[/dim]",
                    border_style="yellow", box=box.ROUNDED,
                    title="[bold yellow]TIMEOUT[/bold yellow]"
                )
                console.print(panel)
                return False

    def close(self):
        """Close program gracefully"""
        if self.child is not None:
            try:
                if self.child.isalive():
                    self.child.sendline('99')
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
        """Show final summary of all purchases"""
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

        success_count = sum(1 for _, result in self.results if result)
        total = len(self.results)

        console.print()
        if success_count == total:
            console.print(f"[bold green]🎉 All purchases successful! ({success_count}/{total})[/bold green]")
        elif success_count > 0:
            console.print(f"[bold yellow]⚠ Partial success: {success_count}/{total}[/bold yellow]")
        else:
            console.print(f"[bold red]❌ All purchases failed (0/{total})[/bold red]")


def main():
    parser = argparse.ArgumentParser(prog='Auto Purchase XL - Multi Account (Termux)')
    parser.add_argument('--tokens', default='refresh-tokens.json', help='Path to tokens file')
    parser.add_argument('--family', default='f4fd69c7-12a4-4047-a1f2-f4072a7c543e')
    parser.add_argument('--package', type=int, default=19)
    parser.add_argument('--choice', type=int, default=5)
    parser.add_argument('--delay', type=int, default=3, help='Delay between accounts (seconds)')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation and run immediately')
    args = parser.parse_args()

    console.print()
    header = Panel(
        Align.center(
            "[bold cyan]AUTO BUY MASTIF XL[/bold cyan]\n"
            "[dim]Multi-Account Mode (Termux/Linux)[/dim]\n"
            "[dim]BY Neutral[/dim]"
        ),
        border_style="cyan", box=box.DOUBLE, padding=(1, 2)
    )
    console.print(header)
    console.print()

    auto = MultiAccountPurchase(timeout=180)

    # Load accounts
    if not auto.load_accounts(args.tokens):
        console.print("[red]Exiting...[/red]")
        return

    # Show accounts
    auto.show_accounts_table()

    # Confirm (skip if --confirm provided)
    if not args.confirm:
        confirm = console.input(f"[cyan]Process {len(auto.accounts)} account(s)?[/cyan] (y/n): ")
        if confirm.lower() != 'y':
            console.print("[yellow]Cancelled by user[/yellow]")
            return
    else:
        console.print("[green]Auto-confirm enabled; proceeding with purchases...[/green]")

    try:
        auto.start_program()

        # Loop through all accounts
        for idx, account in enumerate(auto.accounts):
            console.print()
            console.rule(f"[bold yellow]Account {idx + 1}/{len(auto.accounts)}[/bold yellow]", style="yellow")
            console.print()

            # Switch account
            if not auto.switch_account(idx):
                console.print(f"[red]Failed to switch to account {idx + 1}, skipping...[/red]")
                auto.results.append((account, False))
                continue

            # Purchase for this account
            result = auto.purchase_single(args.family, args.package, args.choice, account)
            auto.results.append((account, result))

            # Delay before next account
            if idx < len(auto.accounts) - 1:
                console.print(f"\n[dim]Waiting {args.delay}s before next account...[/dim]")
                time.sleep(args.delay)

        # Show summary
        auto.show_summary()

        console.print("\n[dim]Press Enter to exit...[/dim]")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass

    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        try:
            auto.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)
