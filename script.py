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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from colorama import Fore, Style, init


@dataclass(frozen=True)
class Config:
    """Application configuration constants."""
    
    author: str = "san1ura"
    version: str = "2.0.0"
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
        return self.config_dir / f"{self.app_name}.json"

    @property
    def repos_file(self) -> Path:
        """Path to Git repositories list file."""
        return self.config_dir / "repositories.json"

    def ensure_dirs(self) -> None:
        """Create necessary directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def __post_init__(self) -> None:
        """Initialize directories on instantiation."""
        self.ensure_dirs()


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
        """Clear package cache for the specified helper.
        
        Args:
            helper: Package manager name (pacman, flatpak, yay, paru)
            
        Raises:
            ValueError: If helper is not found or unsupported
        """
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


class AURManager:
    """Manager for AUR helpers (yay, paru)."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def has_updates(self, helper: str) -> bool:
        """Check if updates are available for an AUR helper.
        
        Args:
            helper: Name of the AUR helper (yay or paru)
            
        Returns:
            True if updates are available, False otherwise
        """
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
            
        except subprocess.CalledProcessError as error:
            print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}{helper.capitalize()}")
            self.logger.info(f"No updates for {helper} (returncode: {error.returncode})")
            return False

    def update(self, helper: str, noconfirm: bool = False) -> None:
        """Update packages using the specified AUR helper.
        
        Args:
            helper: Name of the AUR helper
            noconfirm: If True, skip confirmation prompts
        """
        if not self.has_updates(helper):
            return

        try:
            cmd = [helper, "-Syu"]
            if noconfirm:
                cmd.append("--noconfirm")
                
            self.logger.info(f"Updating {helper}...")
            subprocess.run(cmd, text=True, check=True)
            print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}{helper.capitalize()}")
            self.logger.info(f"Successfully updated {helper}")
            
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating {helper}: {error.stderr if error.stderr else 'Unknown error'}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(f"{error_msg} (returncode: {error.returncode})")


class PacmanManager:
    """Manager for Pacman package manager."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
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
            
        except subprocess.CalledProcessError as error:
            print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}Pacman")
            self.logger.info(f"No updates for Pacman (returncode: {error.returncode})")
            return False

    def update(self, noconfirm: bool = False) -> None:
        """Update system packages using Pacman.
        
        Args:
            noconfirm: If True, skip confirmation prompts
        """
        if not self.has_updates():
            return

        try:
            cmd = ["sudo", "pacman", "-Syu"]
            if noconfirm:
                cmd.append("--noconfirm")
                
            self.logger.info("Updating Pacman...")
            subprocess.run(cmd, text=True, check=True)
            print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}Pacman")
            self.logger.info("Successfully updated Pacman")
            
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating Pacman: {error.stderr if error.stderr else 'Unknown error'}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(f"{error_msg} (returncode: {error.returncode})")


class FlatpakManager:
    """Manager for Flatpak packages."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

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
            
        except subprocess.CalledProcessError as error:
            self.logger.error(f"Error checking Flatpak updates: {error}")
            return False

    def update(self) -> None:
        """Update Flatpak packages."""
        if not self.has_updates():
            return

        try:
            self.logger.info("Updating Flatpak...")
            subprocess.run(["flatpak", "update", "-y"], check=True)
            print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}Flatpak")
            self.logger.info("Successfully updated Flatpak")
            
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating Flatpak: {error.stderr if error.stderr else 'Unknown error'}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(f"{error_msg} (returncode: {error.returncode})")


class GitRepository:
    """Manager for Git repositories."""
    
    def __init__(self, repo_path: str):
        """Initialize Git repository manager.
        
        Args:
            repo_path: Path to the Git repository
            
        Raises:
            ValueError: If path is not a valid Git repository
        """
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.logger = logging.getLogger(__name__)
        
        if not self.repo_path.exists():
            raise ValueError(f"Path does not exist: {self.repo_path}")
            
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"{self.repo_path} is not a Git repository")

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        """Execute a Git command in the repository.
        
        Args:
            args: Git command arguments
            
        Returns:
            CompletedProcess instance with command results
        """
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

    def update(self) -> None:
        """Pull new commits from remote repository."""
        try:
            if self.has_new_commits():
                self.logger.info(f"Pulling updates for {self.repo_path.name}...")
                print(f"{Fore.RED}{Style.BRIGHT}Available -> {Style.RESET_ALL}{self.repo_path.name.capitalize()}")
                
                self._run_git(["pull"])
                
                print(f"{Fore.RED}{Style.BRIGHT}Updated -> {Style.RESET_ALL}{self.repo_path.name.capitalize()}")
                self.logger.info(f"Successfully updated {self.repo_path.name}")
            else:
                print(f"{Fore.GREEN}Already up to date -> {Style.RESET_ALL}{self.repo_path.name.capitalize()}")
                self.logger.info(f"No updates for {self.repo_path.name}")
                
        except subprocess.CalledProcessError as error:
            error_msg = f"Error updating {self.repo_path.name}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            self.logger.error(
                f"{error_msg} (returncode: {error.returncode}, "
                f"stderr: {error.stderr if error.stderr else 'None'})"
            )


def setup_logging(config: Config) -> None:
    """Configure logging system."""
    logging.basicConfig(
        filename=config.log_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


class RepositoryManager:
    """Manager for Git repositories list."""
    
    def __init__(self, config: Config):
        self.config = config
        self.repos_file = config.repos_file
        self.logger = logging.getLogger(__name__)
        
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
        """Add a new repository to the list.
        
        Args:
            repo_path: Path to the Git repository
        """
        # Validate the repository
        try:
            repo = GitRepository(repo_path)
            normalized_path = str(repo.repo_path)
        except ValueError as error:
            print(f"{Fore.RED}Error: {error}{Style.RESET_ALL}")
            return
        
        # Load existing repos
        repos = self._load_repos()
        
        # Check if already exists
        if normalized_path in repos:
            print(f"{Fore.YELLOW}Repository already tracked: {normalized_path}{Style.RESET_ALL}")
            return
        
        # Add and save
        repos.append(normalized_path)
        self._save_repos(repos)
        
        print(f"{Fore.GREEN}Added repository: {normalized_path}{Style.RESET_ALL}")
        self.logger.info(f"Added repository: {normalized_path}")
    
    def remove_repo(self, repo_path: str) -> None:
        """Remove a repository from the list.
        
        Args:
            repo_path: Path to the Git repository
        """
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
    
    def update_all(self) -> None:
        """Update all tracked repositories."""
        repos = self._load_repos()
        
        if not repos:
            self.logger.info("No repositories to update")
            return
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== Updating Git Repositories ==={Style.RESET_ALL}")
        
        for repo_path in repos:
            if not Path(repo_path).exists():
                print(f"{Fore.YELLOW}Skipping (not found): {repo_path}{Style.RESET_ALL}")
                self.logger.warning(f"Repository path not found: {repo_path}")
                continue
            
            try:
                repo = GitRepository(repo_path)
                repo.update()
            except ValueError as error:
                print(f"{Fore.YELLOW}Skipping (invalid): {repo_path} - {error}{Style.RESET_ALL}")
                self.logger.warning(f"Invalid repository: {repo_path} - {error}")
            except Exception as error:
                print(f"{Fore.RED}Error updating {repo_path}: {error}{Style.RESET_ALL}")
                self.logger.error(f"Error updating {repo_path}: {error}")


def update_system(config: Config) -> None:
    """Update all system components."""
    logger = logging.getLogger(__name__)
    logger.info("Starting system update...")
    
    try:
        aur = AURManager()
        pacman = PacmanManager()
        flatpak = FlatpakManager()
        repo_manager = RepositoryManager(config)
        
        # Update AUR helpers
        for helper in ["yay", "paru"]:
            if Utils.has_helper(helper):
                aur.update(helper)
        
        # Update Pacman
        pacman.update()
        
        # Update Flatpak
        if Utils.has_helper("flatpak"):
            flatpak.update()
        
        # Update tracked Git repositories
        repo_manager.update_all()
        
        logger.info("System update completed successfully")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Update cancelled by user{Style.RESET_ALL}")
        logger.info("Update cancelled by user")
        sys.exit(0)
    except Exception as error:
        logger.error(f"Unexpected error during system update: {error}")
        print(f"{Fore.RED}An error occurred: {error}{Style.RESET_ALL}")
        sys.exit(1)


def parse_arguments(config: Config) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        config: Application configuration
        
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog=config.app_name,
        description="System update tool for Arch Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Version {config.version} by {config.author}"
    )
    
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update entire system (Pacman, AUR, Flatpak, Git repos)"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="Display system information"
    )
    
    parser.add_argument(
        "--clear-cache",
        metavar="HELPER",
        type=str,
        help=f"Clear cache for specified helper (pacman, flatpak)"
    )
    
    parser.add_argument(
        "--add-repo",
        metavar="PATH",
        type=str,
        help="Add a Git repository to track for updates"
    )
    
    parser.add_argument(
        "--remove-repo",
        metavar="PATH",
        type=str,
        help="Remove a Git repository from tracking"
    )
    
    parser.add_argument(
        "--list-repos",
        action="store_true",
        help="List all tracked Git repositories"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {config.version}"
    )
    
    return parser.parse_args()


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
    
    # Parse arguments
    args = parse_arguments(config)
    
    # Initialize repository manager
    repo_manager = RepositoryManager(config)
    
    # Execute requested action
    if args.update:
        update_system(config)
        
    elif args.info:
        Utils.show_info()
        
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
            
    elif args.add_repo:
        repo_manager.add_repo(args.add_repo)
        
    elif args.remove_repo:
        repo_manager.remove_repo(args.remove_repo)
        
    elif args.list_repos:
        repo_manager.list_repos()
        
    else:
        # No arguments provided, show help
        parse_arguments(config).print_help()


if __name__ == "__main__":
    main()
