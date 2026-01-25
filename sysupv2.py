#!/usr/bin/env python3
"""
sysup - Arch Linux System Update Tool
Manages updates for Pacman, AUR helpers, Flatpak, and Git repositories.
"""

import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from colorama import Fore, Style, init


@dataclass
class Config:
    """Application configuration constants."""
    
    author: str = "san1ura"
    version: str = "3.0.0"
    app_name: str = "sysup"
    supported_helpers: Tuple[str, ...] = ("yay", "paru")

    @property
    def log_dir(self) -> Path:
        """Directory for log files."""
        return Path.home() / ".local" / "state" / self.app_name

    @property
    def log_file(self) -> Path:
        """Path to main log file."""
        return self.log_dir / f"{self.app_name}.log"

    @property
    def config_dir(self) -> Path:
        """Directory for configuration files."""
        return Path.home() / ".config" / self.app_name

    @property
    def config_file(self) -> Path:
        """Path to main configuration file."""
        return self.config_dir / "config.json"

    @property
    def repos_file(self) -> Path:
        """Path to Git repositories list file."""
        return self.config_dir / "repositories.json"
    
    @property
    def backup_dir(self) -> Path:
        """Directory for backups."""
        return self.config_dir / "backups"
    
    @property
    def stats_file(self) -> Path:
        """Path to statistics file."""
        return self.config_dir / "statistics.json"
    
    @property
    def hooks_dir(self) -> Path:
        """Directory for hook scripts."""
        return self.config_dir / "hooks"

    def ensure_dirs(self) -> None:
        """Create necessary directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        
        # Create hook subdirectories
        (self.hooks_dir / "pre-update").mkdir(exist_ok=True)
        (self.hooks_dir / "post-update").mkdir(exist_ok=True)

    def __post_init__(self) -> None:
        """Initialize directories on instantiation."""
        self.ensure_dirs()


@dataclass
class UserConfig:
    """User configurable settings."""
    
    enable_pacman: bool = True
    enable_aur: bool = True
    enable_flatpak: bool = True
    enable_git_repos: bool = True
    enable_notifications: bool = True
    enable_backups: bool = True
    parallel_updates: bool = False
    noconfirm: bool = False
    excluded_packages: List[str] = field(default_factory=list)
    notification_methods: List[str] = field(default_factory=lambda: ["desktop"])
    webhook_url: Optional[str] = None
    email_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enable_pacman": self.enable_pacman,
            "enable_aur": self.enable_aur,
            "enable_flatpak": self.enable_flatpak,
            "enable_git_repos": self.enable_git_repos,
            "enable_notifications": self.enable_notifications,
            "enable_backups": self.enable_backups,
            "parallel_updates": self.parallel_updates,
            "noconfirm": self.noconfirm,
            "excluded_packages": self.excluded_packages,
            "notification_methods": self.notification_methods,
            "webhook_url": self.webhook_url,
            "email_address": self.email_address,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserConfig':
        """Create from dictionary."""
        return cls(
            enable_pacman=data.get("enable_pacman", True),
            enable_aur=data.get("enable_aur", True),
            enable_flatpak=data.get("enable_flatpak", True),
            enable_git_repos=data.get("enable_git_repos", True),
            enable_notifications=data.get("enable_notifications", True),
            enable_backups=data.get("enable_backups", True),
            parallel_updates=data.get("parallel_updates", False),
            noconfirm=data.get("noconfirm", False),
            excluded_packages=data.get("excluded_packages", []),
            notification_methods=data.get("notification_methods", ["desktop"]),
            webhook_url=data.get("webhook_url"),
            email_address=data.get("email_address"),
        )


class ConfigManager:
    """Manager for user configuration."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> UserConfig:
        """Load user configuration from file."""
        if not self.config.config_file.exists():
            return UserConfig()
        
        try:
            with open(self.config.config_file, 'r') as f:
                data = json.load(f)
                return UserConfig.from_dict(data)
        except (json.JSONDecodeError, IOError) as error:
            self.logger.error(f"Error loading config: {error}")
            return UserConfig()
    
    def save(self, user_config: UserConfig) -> None:
        """Save user configuration to file."""
        try:
            with open(self.config.config_file, 'w') as f:
                json.dump(user_config.to_dict(), f, indent=2)
            self.logger.info("Configuration saved")
        except IOError as error:
            self.logger.error(f"Error saving config: {error}")
            raise


class Utils:
    """Utility functions for system operations."""
    
    @staticmethod
    def has_helper(helper: str) -> bool:
        """Check if a helper program is available in PATH."""
        return shutil.which(helper) is not None

    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal screen."""
        subprocess.run(["clear"], check=False)

    @staticmethod
    def show_info() -> None:
        """Display system information."""
        
        def run_command(cmd: str) -> str:
            """Execute shell command and return output or 'Unknown' on error."""
            try:
                return subprocess.check_output(cmd, shell=True, text=True).strip()
            except subprocess.CalledProcessError:
                return "Unknown"

        info = {
            "OS": run_command("cat /etc/os-release | grep ^PRETTY_NAME= | cut -d= -f2 | tr -d '\"'"),
            "Kernel": platform.release(),
            "Architecture": platform.machine(),
            "Hostname": platform.node(),
            "Python Version": platform.python_version(),
            "CPU": run_command("lscpu | grep 'Model name' | cut -d: -f2"),
            "RAM": run_command("free -h | awk '/Mem:/ {print $2}'"),
            "Disk (root)": run_command("df -h / | awk 'NR==2 {print $2}'"),
            "Package Manager": "pacman",
            "User": os.getenv("USER", "Unknown"),
        }

        print(f"{Fore.CYAN}{Style.BRIGHT}=== System Information ==={Style.RESET_ALL}")
        for key, value in info.items():
            print(f"{Fore.GREEN}{key:<16}{Style.RESET_ALL}: {Fore.WHITE}{value}")

    @staticmethod
    def clear_cache(helper: str) -> None:
        """Clear package cache for the specified helper."""
        helper = helper.lower()
        
        if not Utils.has_helper(helper):
            raise ValueError(f"Helper not found: {helper}")
        
        try:
            if helper == "pacman":
                logging.info("Clearing pacman cache...")
                subprocess.run(
                    ["sudo", "paccache", "-r", "-k", "0"],
                    text=True,
                    check=True
                )
                print(f"{Fore.GREEN}Cache cleared for pacman{Style.RESET_ALL}")
                
            elif helper == "flatpak":
                logging.info("Clearing flatpak cache...")
                subprocess.run(
                    ["flatpak", "uninstall", "--unused", "-y"],
                    text=True,
                    check=True
                )
                print(f"{Fore.GREEN}Cache cleared for flatpak{Style.RESET_ALL}")
                
            else:
                raise ValueError(f"Unsupported helper: {helper}")
                
        except subprocess.CalledProcessError as error:
            logging.error(f"Failed to clear cache for {helper}: {error}")
            print(f"{Fore.RED}Error clearing cache: {error}{Style.RESET_ALL}")
            raise


class NotificationManager:
    """Manager for sending notifications."""
    
    def __init__(self, user_config: UserConfig):
        self.user_config = user_config
        self.logger = logging.getLogger(__name__)
    
    def send(self, title: str, message: str, urgency: str = "normal") -> None:
        """Send notification via configured methods."""
        if not self.user_config.enable_notifications:
            return
        
        for method in self.user_config.notification_methods:
            if method == "desktop":
                self._send_desktop(title, message, urgency)
            elif method == "webhook" and self.user_config.webhook_url:
                self._send_webhook(title, message)
    
    def _send_desktop(self, title: str, message: str, urgency: str) -> None:
        """Send desktop notification."""
        if not Utils.has_helper("notify-send"):
            return
        
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, title, message],
                check=False
            )
        except Exception as error:
            self.logger.error(f"Failed to send desktop notification: {error}")
    
    def _send_webhook(self, title: str, message: str) -> None:
        """Send webhook notification (Discord/Slack format)."""
        import urllib.request
        import urllib.error
        
        try:
            data = json.dumps({
                "content": f"**{title}**\n{message}"
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.user_config.webhook_url, #type: ignore
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=10)
        except (urllib.error.URLError, Exception) as error:
            self.logger.error(f"Failed to send webhook notification: {error}")


class BackupManager:
    """Manager for creating backups."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def create_backup(self) -> Optional[str]:
        """Create backup of package lists."""
        if not Utils.has_helper("pacman"):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.config.backup_dir / f"packages_{timestamp}.txt"
        
        try:
            # Get list of explicitly installed packages
            result = subprocess.run(
                ["pacman", "-Qqe"],
                capture_output=True,
                text=True,
                check=True
            )
            
            with open(backup_file, 'w') as f:
                f.write(result.stdout)
            
            self.logger.info(f"Backup created: {backup_file}")
            print(f"{Fore.GREEN}Backup created: {backup_file.name}{Style.RESET_ALL}")
            
            # Keep only last 10 backups
            self._cleanup_old_backups()
            
            return str(backup_file)
            
        except Exception as error:
            self.logger.error(f"Failed to create backup: {error}")
            return None
    
    def _cleanup_old_backups(self, keep: int = 10) -> None:
        """Remove old backups, keeping only the most recent ones."""
        backups = sorted(
            self.config.backup_dir.glob("packages_*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for backup in backups[keep:]:
            try:
                backup.unlink()
                self.logger.info(f"Removed old backup: {backup.name}")
            except Exception as error:
                self.logger.error(f"Failed to remove old backup {backup.name}: {error}")
    
    def list_backups(self) -> None:
        """List all available backups."""
        backups = sorted(
            self.config.backup_dir.glob("packages_*.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not backups:
            print(f"{Fore.YELLOW}No backups found{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}{Style.BRIGHT}=== Available Backups ==={Style.RESET_ALL}")
        for i, backup in enumerate(backups, 1):
            size = backup.stat().st_size
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{i}. {backup.name} ({size} bytes) - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")


class StatisticsManager:
    """Manager for tracking update statistics."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load statistics from file."""
        if not self.config.stats_file.exists():
            return {
                "total_updates": 0,
                "last_update": None,
                "package_updates": {},
                "update_history": []
            }
        
        try:
            with open(self.config.stats_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                "total_updates": 0,
                "last_update": None,
                "package_updates": {},
                "update_history": []
            }
    
    def _save_stats(self, stats: Dict[str, Any]) -> None:
        """Save statistics to file."""
        try:
            with open(self.config.stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
        except IOError as error:
            self.logger.error(f"Failed to save statistics: {error}")
    
    def record_update(self, component: str, packages: List[str] = []) -> None:
        """Record an update event."""
        stats = self._load_stats()
        stats["total_updates"] += 1
        stats["last_update"] = datetime.now().isoformat()
        
        if packages:
            for pkg in packages:
                stats["package_updates"][pkg] = stats["package_updates"].get(pkg, 0) + 1
        
        stats["update_history"].append({
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "package_count": len(packages) if packages else 0
        })
        
        # Keep only last 100 history entries
        stats["update_history"] = stats["update_history"][-100:]
        
        self._save_stats(stats)
    
    def show_stats(self) -> None:
        """Display statistics."""
        stats = self._load_stats()
        
        print(f"{Fore.CYAN}{Style.BRIGHT}=== Update Statistics ==={Style.RESET_ALL}")
        print(f"{Fore.GREEN}Total Updates:{Style.RESET_ALL} {stats['total_updates']}")
        
        if stats['last_update']:
            last_update = datetime.fromisoformat(stats['last_update'])
            print(f"{Fore.GREEN}Last Update:{Style.RESET_ALL} {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if stats['package_updates']:
            print(f"\n{Fore.CYAN}Top 10 Most Updated Packages:{Style.RESET_ALL}")
            sorted_pkgs = sorted(
                stats['package_updates'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            for pkg, count in sorted_pkgs:
                print(f"  {pkg}: {count} times")
        
        if stats['update_history']:
            print(f"\n{Fore.CYAN}Recent Updates:{Style.RESET_ALL}")
            for entry in stats['update_history'][-5:]:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                print(f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {entry['component']} ({entry['package_count']} packages)")


class HookManager:
    """Manager for pre/post update hooks."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def run_hooks(self, hook_type: str) -> None:
        """Run all hooks of specified type.
        
        Args:
            hook_type: Either 'pre-update' or 'post-update'
        """
        hook_dir = self.config.hooks_dir / hook_type
        
        if not hook_dir.exists():
            return
        
        scripts = sorted(hook_dir.glob("*"))
        executable_scripts = [s for s in scripts if os.access(s, os.X_OK)]
        
        if not executable_scripts:
            return
        
        print(f"{Fore.CYAN}Running {hook_type} hooks...{Style.RESET_ALL}")
        
        for script in executable_scripts:
            try:
                self.logger.info(f"Running hook: {script.name}")
                result = subprocess.run(
                    [str(script)],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    print(f"{Fore.GREEN}✓ {script.name}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ {script.name} (exit code: {result.returncode}){Style.RESET_ALL}")
                    self.logger.error(f"Hook {script.name} failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"{Fore.RED}✗ {script.name} (timeout){Style.RESET_ALL}")
                self.logger.error(f"Hook {script.name} timed out")
            except Exception as error:
                print(f"{Fore.RED}✗ {script.name} (error: {error}){Style.RESET_ALL}")
                self.logger.error(f"Hook {script.name} failed: {error}")


class AURManager:
    """Manager for AUR helpers (yay, paru)."""
    
    def __init__(self, stats_manager: StatisticsManager):
        self.logger = logging.getLogger(__name__)
        self.stats_manager = stats_manager

    def has_updates(self, helper: str) -> bool:
        """Check if updates are available for an AUR helper."""
        if not Utils.has_helper(helper):
            return False

        try:
            self.logger.info(f"Checking updates for {helper}...")
            subprocess.run(
                [helper, "-Qua"],
                text=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                check=True
            )
            print(f"{Fore.RED}Available -> {Style.RESET_ALL}{helper.capitalize()}")
            self.logger.info(f"Updates available for {helper}")
            return True
            
        except subprocess.CalledProcessError:
            print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}{helper.capitalize()}")
            self.logger.info(f"No updates for {helper}")
            return False

    def update(self, helper: str, noconfirm: bool = False) -> bool:
        """Update packages using the specified AUR helper."""
        if not self.has_updates(helper):
            return False

        try:
            cmd = [helper, "-Syu"]
            if noconfirm:
                cmd.append("--noconfirm")
                
            self.logger.info(f"Updating {helper}...")
            subprocess.run(cmd, text=True, check=True)
            print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}{helper.capitalize()}")
            self.logger.info(f"Successfully updated {helper}")
            self.stats_manager.record_update(helper)
            return True
            
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating {helper}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(f"{error_msg} (returncode: {error.returncode})")
            return False


class PacmanManager:
    """Manager for Pacman package manager."""
    
    def __init__(self, stats_manager: StatisticsManager):
        self.logger = logging.getLogger(__name__)
        self.stats_manager = stats_manager
        
        if not Utils.has_helper("checkupdates"):
            raise RuntimeError(
                "Missing dependency: pacman-contrib\n"
                "Install with: sudo pacman -S pacman-contrib"
            )

    def has_updates(self) -> bool:
        """Check if Pacman updates are available."""
        try:
            self.logger.info("Checking updates for Pacman...")
            subprocess.run(
                ["checkupdates"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"{Fore.RED}Available -> {Style.RESET_ALL}Pacman")
            self.logger.info("Updates available for Pacman")
            return True
            
        except subprocess.CalledProcessError:
            print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}Pacman")
            self.logger.info("No updates for Pacman")
            return False

    def update(self, noconfirm: bool = False) -> bool:
        """Update system packages using Pacman."""
        if not self.has_updates():
            return False

        try:
            cmd = ["sudo", "pacman", "-Syu"]
            if noconfirm:
                cmd.append("--noconfirm")
                
            self.logger.info("Updating Pacman...")
            subprocess.run(cmd, text=True, check=True)
            print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}Pacman")
            self.logger.info("Successfully updated Pacman")
            self.stats_manager.record_update("pacman")
            return True
            
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating Pacman"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(f"{error_msg} (returncode: {error.returncode})")
            return False
    
    def clean_orphans(self) -> None:
        """Remove orphaned packages."""
        try:
            # Get list of orphaned packages
            result = subprocess.run(
                ["pacman", "-Qtdq"],
                capture_output=True,
                text=True,
                check=True
            )
            
            orphans = result.stdout.strip().split('\n')
            if orphans and orphans[0]:
                print(f"{Fore.YELLOW}Found {len(orphans)} orphaned packages{Style.RESET_ALL}")
                subprocess.run(["sudo", "pacman", "-Rns"] + orphans + ["--noconfirm"], check=True)
                print(f"{Fore.GREEN}Removed orphaned packages{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}No orphaned packages found{Style.RESET_ALL}")
                
        except subprocess.CalledProcessError:
            print(f"{Fore.GREEN}No orphaned packages found{Style.RESET_ALL}")


class FlatpakManager:
    """Manager for Flatpak packages."""
    
    def __init__(self, stats_manager: StatisticsManager):
        self.logger = logging.getLogger(__name__)
        self.stats_manager = stats_manager

    def has_updates(self) -> bool:
        """Check if Flatpak updates are available."""
        try:
            result = subprocess.run(
                ["flatpak", "update"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout:
                output_lower = result.stdout.lower()
                if "nothing to do" in output_lower or not result.stdout.strip():
                    print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}Flatpak")
                    return False
                    
                print(f"{Fore.RED}Available -> {Style.RESET_ALL}Flatpak")
                return True
                
            print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}Flatpak")
            return False
            
        except subprocess.CalledProcessError:
            return False

    def update(self) -> bool:
        """Update Flatpak packages."""
        if not self.has_updates():
            return False

        try:
            self.logger.info("Updating Flatpak...")
            subprocess.run(["flatpak", "update", "-y"], check=True)
            print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}Flatpak")
            self.logger.info("Successfully updated Flatpak")
            self.stats_manager.record_update("flatpak")
            return True
            
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating Flatpak"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(f"{error_msg} (returncode: {error.returncode})")
            return False


class GitRepository:
    """Manager for Git repositories."""
    
    def __init__(self, repo_path: str):
        """Initialize Git repository manager."""
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.logger = logging.getLogger(__name__)
        
        if not self.repo_path.exists():
            raise ValueError(f"Path does not exist: {self.repo_path}")
            
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"{self.repo_path} is not a Git repository")

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        """Execute a Git command in the repository."""
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            check=True,
            text=True,
            capture_output=True
        )

    def has_new_commits(self) -> bool:
        """Check if remote repository has new commits."""
        try:
            self._run_git(["fetch"])
            result = self._run_git(["rev-list", "--count", "HEAD..@{u}"])
            return int(result.stdout.strip()) > 0
        except subprocess.CalledProcessError:
            return False

    def update(self) -> bool:
        """Pull new commits from remote repository."""
        try:
            if self.has_new_commits():
                self.logger.info(f"Pulling updates for {self.repo_path.name}...")
                # Capitalize first letter of repo name
                display_name = self.repo_path.name.capitalize()
                print(f"{Fore.RED}{Style.BRIGHT}Available -> {Style.RESET_ALL}{display_name}")
                
                self._run_git(["pull"])
                
                print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}{display_name}")
                self.logger.info(f"Successfully updated {self.repo_path.name}")
                return True
            else:
                # Capitalize first letter of repo name
                display_name = self.repo_path.name.capitalize()
                print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}{display_name}")
                self.logger.info(f"No updates for {self.repo_path.name}")
                return False
                
        except subprocess.CalledProcessError as error:
            display_name = self.repo_path.name.capitalize()
            error_msg = f"Error updating {display_name}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(
                f"{error_msg} (returncode: {error.returncode}, "
                f"stderr: {error.stderr if error.stderr else 'None'})"
            )
            return False


class RepositoryManager:
    """Manager for Git repositories list."""
    
    def __init__(self, config: Config, stats_manager: StatisticsManager):
        self.config = config
        self.repos_file = config.repos_file
        self.logger = logging.getLogger(__name__)
        self.stats_manager = stats_manager
        
    def _load_repos(self) -> List[str]:
        """Load repository list from JSON file."""
        if not self.repos_file.exists():
            return []
        
        try:
            with open(self.repos_file, 'r') as f:
                data = json.load(f)
                return data.get('repositories', [])
        except (json.JSONDecodeError, IOError) as error:
            self.logger.error(f"Error loading repositories file: {error}")
            return []
    
    def _save_repos(self, repos: List[str]) -> None:
        """Save repository list to JSON file."""
        try:
            with open(self.repos_file, 'w') as f:
                json.dump({'repositories': repos}, f, indent=2)
            self.logger.info(f"Saved {len(repos)} repositories")
        except IOError as error:
            self.logger.error(f"Error saving repositories file: {error}")
            raise
    
    def add_repo(self, repo_path: str) -> None:
        """Add a new repository to the list."""
        try:
            repo = GitRepository(repo_path)
            normalized_path = str(repo.repo_path)
        except ValueError as error:
            print(f"{Fore.RED}Error: {error}{Style.RESET_ALL}")
            return
        
        repos = self._load_repos()
        
        if normalized_path in repos:
            print(f"{Fore.YELLOW}Repository already tracked: {normalized_path}{Style.RESET_ALL}")
            return
        
        repos.append(normalized_path)
        self._save_repos(repos)
        
        print(f"{Fore.GREEN}Added repository: {normalized_path}{Style.RESET_ALL}")
        self.logger.info(f"Added repository: {normalized_path}")
    
    def remove_repo(self, repo_path: str) -> None:
        """Remove a repository from the list."""
        normalized_path = str(Path(repo_path).expanduser().resolve())
        repos = self._load_repos()
        
        if normalized_path not in repos:
            print(f"{Fore.YELLOW}Repository not found in tracked list: {normalized_path}{Style.RESET_ALL}")
            return
        
        repos.remove(normalized_path)
        self._save_repos(repos)
        
        print(f"{Fore.GREEN}Removed repository: {normalized_path}{Style.RESET_ALL}")
        self.logger.info(f"Removed repository: {normalized_path}")
    
    def list_repos(self) -> None:
        """Display all tracked repositories."""
        repos = self._load_repos()
        
        if not repos:
            print(f"{Fore.YELLOW}No repositories tracked yet{Style.RESET_ALL}")
            print(f"Add repositories with: {Fore.CYAN}sysup --add-repo /path/to/repo{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}{Style.BRIGHT}=== Tracked Git Repositories ==={Style.RESET_ALL}")
        for i, repo in enumerate(repos, 1):
            status = f"{Fore.GREEN}✓{Style.RESET_ALL}" if Path(repo).exists() else f"{Fore.RED}✗{Style.RESET_ALL}"
            print(f"{status} {i}. {repo}")
        print(f"\nTotal: {len(repos)} repositories")
    
    def update_all(self) -> int:
        """Update all tracked repositories. Returns number of updated repos."""
        repos = self._load_repos()
        
        if not repos:
            self.logger.info("No repositories to update")
            return 0
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== Updating Git Repositories ==={Style.RESET_ALL}")
        
        updated_count = 0
        for repo_path in repos:
            if not Path(repo_path).exists():
                print(f"{Fore.YELLOW}Skipping (not found): {repo_path}{Style.RESET_ALL}")
                self.logger.warning(f"Repository path not found: {repo_path}")
                continue
            
            try:
                repo = GitRepository(repo_path)
                if repo.update():
                    updated_count += 1
                    self.stats_manager.record_update(f"git:{repo.repo_path.name}")
            except ValueError as error:
                print(f"{Fore.YELLOW}Skipping (invalid): {repo_path} - {error}{Style.RESET_ALL}")
                self.logger.warning(f"Invalid repository: {repo_path} - {error}")
            except Exception as error:
                print(f"{Fore.RED}Error updating {repo_path}: {error}{Style.RESET_ALL}")
                self.logger.error(f"Error updating {repo_path}: {error}")
        
        return updated_count


class CronManager:
    """Manager for scheduling automatic updates."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def setup_schedule(self, frequency: str) -> None:
        """Setup cron job for automatic updates.
        
        Args:
            frequency: 'daily' or 'weekly'
        """
        script_path = Path(__file__).resolve()
        
        if frequency == "daily":
            cron_time = "0 2 * * *"  # 2 AM every day
        elif frequency == "weekly":
            cron_time = "0 2 * * 0"  # 2 AM every Sunday
        else:
            print(f"{Fore.RED}Invalid frequency. Use 'daily' or 'weekly'{Style.RESET_ALL}")
            return
        
        cron_entry = f"{cron_time} {sys.executable} {script_path} --update --noconfirm\n"
        
        try:
            # Get current crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                check=False
            )
            
            current_cron = result.stdout if result.returncode == 0 else ""
            
            # Check if entry already exists
            if str(script_path) in current_cron:
                print(f"{Fore.YELLOW}Cron job already exists. Updating...{Style.RESET_ALL}")
                # Remove old entry
                lines = [line for line in current_cron.split('\n') if str(script_path) not in line]
                current_cron = '\n'.join(lines)
            
            # Add new entry
            new_cron = current_cron.rstrip() + '\n' + cron_entry
            
            # Install new crontab
            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=new_cron)
            
            print(f"{Fore.GREEN}Cron job scheduled for {frequency} updates at 2 AM{Style.RESET_ALL}")
            self.logger.info(f"Scheduled {frequency} updates")
            
        except Exception as error:
            print(f"{Fore.RED}Error setting up cron job: {error}{Style.RESET_ALL}")
            self.logger.error(f"Failed to setup cron: {error}")
    
    def remove_schedule(self) -> None:
        """Remove cron job."""
        script_path = Path(__file__).resolve()
        
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                print(f"{Fore.YELLOW}No crontab found{Style.RESET_ALL}")
                return
            
            current_cron = result.stdout
            
            if str(script_path) not in current_cron:
                print(f"{Fore.YELLOW}No scheduled updates found{Style.RESET_ALL}")
                return
            
            # Remove entry
            lines = [line for line in current_cron.split('\n') if str(script_path) not in line]
            new_cron = '\n'.join(lines)
            
            # Install new crontab
            process = subprocess.Popen(
                ["crontab", "-"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=new_cron)
            
            print(f"{Fore.GREEN}Removed scheduled updates{Style.RESET_ALL}")
            self.logger.info("Removed cron job")
            
        except Exception as error:
            print(f"{Fore.RED}Error removing cron job: {error}{Style.RESET_ALL}")
            self.logger.error(f"Failed to remove cron: {error}")


def setup_logging(config: Config) -> None:
    """Configure logging system."""
    logging.basicConfig(
        filename=config.log_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def update_system(config: Config, user_config: UserConfig, dry_run: bool = False) -> None:
    """Update all system components."""
    logger = logging.getLogger(__name__)
    logger.info("Starting system update...")
    
    if dry_run:
        print(f"{Fore.CYAN}{Style.BRIGHT}=== DRY RUN MODE ==={Style.RESET_ALL}")
        print("No actual changes will be made\n")
    
    try:
        stats_manager = StatisticsManager(config)
        notification_manager = NotificationManager(user_config)
        backup_manager = BackupManager(config)
        hook_manager = HookManager(config)
        
        # Create backup if enabled
        if user_config.enable_backups and not dry_run:
            backup_manager.create_backup()
        
        # Run pre-update hooks
        if not dry_run:
            hook_manager.run_hooks("pre-update")
        
        update_results = {
            "pacman": False,
            "aur": False,
            "flatpak": False,
            "git_repos": 0
        }
        
        if user_config.parallel_updates and not dry_run:
            # Parallel updates
            print(f"{Fore.CYAN}Running parallel updates...{Style.RESET_ALL}\n")
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                if user_config.enable_pacman:
                    pacman = PacmanManager(stats_manager)
                    futures.append(("pacman", executor.submit(pacman.update, user_config.noconfirm)))
                
                if user_config.enable_aur:
                    aur = AURManager(stats_manager)
                    for helper in ["yay", "paru"]:
                        if Utils.has_helper(helper):
                            futures.append((helper, executor.submit(aur.update, helper, user_config.noconfirm)))
                
                if user_config.enable_flatpak and Utils.has_helper("flatpak"):
                    flatpak = FlatpakManager(stats_manager)
                    futures.append(("flatpak", executor.submit(flatpak.update)))
                
                for name, future in futures:
                    try:
                        result = future.result(timeout=600)  # 10 minute timeout
                        if name == "pacman":
                            update_results["pacman"] = result
                        elif name in ["yay", "paru"]:
                            update_results["aur"] = result or update_results["aur"]
                        elif name == "flatpak":
                            update_results["flatpak"] = result
                    except Exception as error:
                        logger.error(f"Error in parallel update for {name}: {error}")
            
            # Git repos are updated sequentially
            if user_config.enable_git_repos:
                repo_manager = RepositoryManager(config, stats_manager)
                update_results["git_repos"] = repo_manager.update_all()
        else:
            # Sequential updates
            if user_config.enable_pacman:
                pacman = PacmanManager(stats_manager)
                if dry_run:
                    print(f"{Fore.CYAN}Would update: Pacman{Style.RESET_ALL}")
                else:
                    update_results["pacman"] = pacman.update(user_config.noconfirm)
            
            if user_config.enable_aur:
                aur = AURManager(stats_manager)
                for helper in ["yay", "paru"]:
                    if Utils.has_helper(helper):
                        if dry_run:
                            print(f"{Fore.CYAN}Would update: {helper.capitalize()}{Style.RESET_ALL}")
                        else:
                            result = aur.update(helper, user_config.noconfirm)
                            update_results["aur"] = result or update_results["aur"]
            
            if user_config.enable_flatpak and Utils.has_helper("flatpak"):
                flatpak = FlatpakManager(stats_manager)
                if dry_run:
                    print(f"{Fore.CYAN}Would update: Flatpak{Style.RESET_ALL}")
                else:
                    update_results["flatpak"] = flatpak.update()
            
            if user_config.enable_git_repos:
                repo_manager = RepositoryManager(config, stats_manager)
                if dry_run:
                    repos = repo_manager._load_repos()
                    for repo_path in repos:
                        repo_name = Path(repo_path).name.capitalize()
                        print(f"{Fore.CYAN}Would update: {repo_name}{Style.RESET_ALL}")
                else:
                    update_results["git_repos"] = repo_manager.update_all()
        
        # Run post-update hooks
        if not dry_run:
            hook_manager.run_hooks("post-update")
        
        # Send notification
        if not dry_run:
            total_updates = sum([
                1 if update_results["pacman"] else 0,
                1 if update_results["aur"] else 0,
                1 if update_results["flatpak"] else 0,
                update_results["git_repos"]
            ])
            
            if total_updates > 0:
                notification_manager.send(
                    "System Update Complete",
                    f"Successfully updated {total_updates} component(s)",
                    "normal"
                )
        
        logger.info("System update completed successfully")
        print(f"\n{Fore.GREEN}{Style.BRIGHT}Update completed!{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Update cancelled by user{Style.RESET_ALL}")
        logger.info("Update cancelled by user")
        sys.exit(0)
    except Exception as error:
        logger.error(f"Unexpected error during system update: {error}")
        print(f"{Fore.RED}An error occurred: {error}{Style.RESET_ALL}")
        sys.exit(1)


def parse_arguments(config: Config) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog=config.app_name,
        description="Advanced system update tool for Arch Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {config.app_name} --update                    Update entire system
  {config.app_name} --update --dry-run          Preview updates without applying
  {config.app_name} --add-repo ~/dotfiles       Track a Git repository
  {config.app_name} --schedule daily            Setup daily automatic updates
  {config.app_name} --stats                     Show update statistics
  {config.app_name} --clean-orphans             Remove orphaned packages
  
Version {config.version} by {config.author}
        """
    )
    
    # Update operations
    update_group = parser.add_argument_group('Update Operations')
    update_group.add_argument(
        "--update",
        action="store_true",
        help="Update entire system (Pacman, AUR, Flatpak, Git repos)"
    )
    update_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be updated without making changes"
    )
    update_group.add_argument(
        "--noconfirm",
        action="store_true",
        help="Skip confirmation prompts during update"
    )
    
    # Repository management
    repo_group = parser.add_argument_group('Repository Management')
    repo_group.add_argument(
        "--add-repo",
        metavar="PATH",
        type=str,
        help="Add a Git repository to track for updates"
    )
    repo_group.add_argument(
        "--remove-repo",
        metavar="PATH",
        type=str,
        help="Remove a Git repository from tracking"
    )
    repo_group.add_argument(
        "--list-repos",
        action="store_true",
        help="List all tracked Git repositories"
    )
    
    # Maintenance operations
    maint_group = parser.add_argument_group('Maintenance Operations')
    maint_group.add_argument(
        "--clear-cache",
        metavar="HELPER",
        type=str,
        help="Clear cache for specified helper (pacman, flatpak)"
    )
    maint_group.add_argument(
        "--clean-orphans",
        action="store_true",
        help="Remove orphaned packages"
    )
    
    # Backup operations
    backup_group = parser.add_argument_group('Backup Operations')
    backup_group.add_argument(
        "--backup",
        action="store_true",
        help="Create backup of package list"
    )
    backup_group.add_argument(
        "--list-backups",
        action="store_true",
        help="List all available backups"
    )
    
    # Scheduling
    schedule_group = parser.add_argument_group('Scheduling')
    schedule_group.add_argument(
        "--schedule",
        metavar="FREQUENCY",
        type=str,
        choices=["daily", "weekly"],
        help="Setup automatic updates (daily or weekly)"
    )
    schedule_group.add_argument(
        "--unschedule",
        action="store_true",
        help="Remove scheduled automatic updates"
    )
    
    # Information
    info_group = parser.add_argument_group('Information')
    info_group.add_argument(
        "--info",
        action="store_true",
        help="Display system information"
    )
    info_group.add_argument(
        "--stats",
        action="store_true",
        help="Show update statistics"
    )
    info_group.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {config.version}"
    )
    
    return parser.parse_args()


def show_config(user_config: UserConfig) -> None:
    """Display current configuration."""
    print(f"{Fore.CYAN}{Style.BRIGHT}=== Current Configuration ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}Enable Pacman:{Style.RESET_ALL} {user_config.enable_pacman}")
    print(f"{Fore.GREEN}Enable AUR:{Style.RESET_ALL} {user_config.enable_aur}")
    print(f"{Fore.GREEN}Enable Flatpak:{Style.RESET_ALL} {user_config.enable_flatpak}")
    print(f"{Fore.GREEN}Enable Git Repos:{Style.RESET_ALL} {user_config.enable_git_repos}")
    print(f"{Fore.GREEN}Enable Notifications:{Style.RESET_ALL} {user_config.enable_notifications}")
    print(f"{Fore.GREEN}Enable Backups:{Style.RESET_ALL} {user_config.enable_backups}")
    print(f"{Fore.GREEN}Parallel Updates:{Style.RESET_ALL} {user_config.parallel_updates}")
    print(f"{Fore.GREEN}No Confirm:{Style.RESET_ALL} {user_config.noconfirm}")
    
    if user_config.excluded_packages:
        print(f"\n{Fore.CYAN}Excluded Packages:{Style.RESET_ALL}")
        for pkg in user_config.excluded_packages:
            print(f"  - {pkg}")
    
    print(f"\n{Fore.CYAN}Notification Methods:{Style.RESET_ALL} {', '.join(user_config.notification_methods)}")
    
    if user_config.webhook_url:
        print(f"{Fore.GREEN}Webhook URL:{Style.RESET_ALL} {user_config.webhook_url}")


def main() -> None:
    """Main entry point."""
    # Initialize colorama
    init(autoreset=True)
    
    # Initialize configuration
    config = Config()
    
    # Setup logging
    setup_logging(config)
    
    # Verify we're on Arch Linux
    if not Utils.has_helper("pacman"):
        print(f"{Fore.RED}Error: This tool is only for Arch Linux and Arch-based distributions{Style.RESET_ALL}")
        sys.exit(1)
    
    # Load user configuration
    config_manager = ConfigManager(config)
    user_config = config_manager.load()
    
    # Parse arguments
    args = parse_arguments(config)
    parser = argparse.ArgumentParser()
    
    # Initialize managers
    stats_manager = StatisticsManager(config)
    repo_manager = RepositoryManager(config, stats_manager)
    backup_manager = BackupManager(config)
    cron_manager = CronManager(config)
    
    # Handle --noconfirm flag
    if args.noconfirm:
        user_config.noconfirm = True
    
    # Execute requested action
    if args.update:
        update_system(config, user_config, dry_run=args.dry_run)
        
    elif args.info:
        Utils.show_info()
        
    elif args.stats:
        stats_manager.show_stats()
        
    elif args.config:
        show_config(user_config)
        
    elif args.clear_cache:
        helper = args.clear_cache.lower()
        allowed_helpers = ["pacman", "flatpak"]
        
        if helper not in allowed_helpers:
            print(f"{Fore.RED}Error: Unsupported helper '{helper}'{Style.RESET_ALL}")
            print(f"Supported helpers: {', '.join(allowed_helpers)}")
            sys.exit(1)
            
        try:
            Utils.clear_cache(helper)
        except Exception as error:
            print(f"{Fore.RED}Error: {error}{Style.RESET_ALL}")
            sys.exit(1)
    
    elif args.clean_orphans:
        pacman = PacmanManager(stats_manager)
        pacman.clean_orphans()
        
    elif args.add_repo:
        repo_manager.add_repo(args.add_repo)
        
    elif args.remove_repo:
        repo_manager.remove_repo(args.remove_repo)
        
    elif args.list_repos:
        repo_manager.list_repos()
    
    elif args.backup:
        backup_manager.create_backup()
    
    elif args.list_backups:
        backup_manager.list_backups()
    
    elif args.schedule:
        cron_manager.setup_schedule(args.schedule)
    
    elif args.unschedule:
        cron_manager.remove_schedule()
        
    else:
        # No arguments provided, show help
        parser = argparse.ArgumentParser(
            prog=config.app_name,
            description="Advanced system update tool for Arch Linux",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""
Examples:
  {config.app_name} --update                    Update entire system
  {config.app_name} --update --dry-run          Preview updates without applying
  {config.app_name} --add-repo ~/dotfiles       Track a Git repository
  {config.app_name} --schedule daily            Setup daily automatic updates
  {config.app_name} --stats                     Show update statistics
  {config.app_name} --clean-orphans             Remove orphaned packages
  
Version {config.version} by {config.author}
        """
        )
        parser.print_help()


if __name__ == "__main__":
    main()
