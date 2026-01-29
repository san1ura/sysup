# SysUp - System Update Manager for Arch Linux

[![Version](https://img.shields.io/badge/version-2.0.6-blue.svg)](https://github.com/san1ura/sysup)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)
[![Arch Linux](https://img.shields.io/badge/platform-Arch%20Linux-1793D1.svg)](https://archlinux.org/)

A comprehensive system update manager for Arch Linux that provides unified management of Pacman, AUR helpers (yay/paru), Flatpak packages, and Git repositories.

## Features

- **Unified Updates**: Manage updates for Pacman, AUR, Flatpak, and Git repositories from a single interface
- **Dry Run Mode**: Preview pending updates before applying changes
- **Automatic Backups**: Create package list snapshots before each update operation
- **Statistics Tracking**: Monitor update history and track frequently updated packages
- **Smart Notifications**: Desktop notifications with webhook support for Discord and Slack
- **Parallel Updates**: Optional parallel execution for improved performance
- **Maintenance Tools**: Clean orphaned packages and manage package cache
- **Scheduled Updates**: Configure automatic daily or weekly updates via cron
- **Pre/Post Hooks**: Execute custom scripts before and after update operations
- **Git Repository Tracking**: Automatic updates for dotfiles and configuration repositories
- **Colorful Output**: Enhanced terminal interface with color-coded output
- **Configurable**: JSON-based configuration system

## Requirements

- **Arch Linux** or Arch-based distribution
- **Python 3.8+**
- **pacman-contrib** (provides `checkupdates`)
- **colorama** Python package
- Optional: **yay** or **paru** (AUR helpers)
- Optional: **flatpak** (for Flatpak support)
- Optional: **notify-send** (for desktop notifications)

## Installation

### Quick Installation (Recommended)

Using Make:

```bash
# Clone the repository
git clone https://github.com/san1ura/sysup.git
cd sysup

# System-wide installation (requires sudo)
make install

# Or user-only installation (no sudo needed)
make install-user
```

Verify Installation:

```bash
sysup --version
sysup --help
```

### Manual Installation

Install dependencies:

```bash
# Install pacman-contrib
sudo pacman -S pacman-contrib python-pip

# Install colorama
pip install colorama

# Optional: Install AUR helper
sudo pacman -S yay   # or paru

# Optional: Install Flatpak
sudo pacman -S flatpak
```

Install sysup:

```bash
# Clone the repository
git clone https://github.com/san1ura/sysup.git
cd sysup

# Make the script executable
chmod +x main.py

# Optional: Create a symbolic link for easy access
sudo ln -s "$(pwd)/main.py" /usr/local/bin/sysup
```

## Usage

### Basic Commands

```bash
# Update entire system (Pacman + AUR + Flatpak + Git repos)
sysup --update

# Preview updates without applying (dry run)
sysup --update --dry-run

# Update without confirmation prompts
sysup --update --noconfirm

# Display system information
sysup --info

# Show update statistics
sysup --stats

# Show current configuration
sysup --config
```

### Git Repository Management

```bash
# Add a Git repository to track
sysup --add-repo ~/dotfiles
sysup --add-repo ~/.config/nvim

# List all tracked repositories
sysup --list-repos

# Remove a repository from tracking
sysup --remove-repo ~/dotfiles
```

### Maintenance Operations

```bash
# Clean package cache
sysup --clear-cache pacman
sysup --clear-cache flatpak

# Remove orphaned packages
sysup --clean-orphans
```

### Backup Management

```bash
# Create a manual backup
sysup --backup

# List all available backups
sysup --list-backups
```

### Scheduled Updates

```bash
# Setup automatic daily updates (runs at 2 AM)
sysup --schedule daily

# Setup automatic weekly updates (runs at 2 AM on Sundays)
sysup --schedule weekly

# Remove scheduled updates
sysup --unschedule
```

## Configuration

Configuration file is located at `~/.config/sysup/config.json`

```json
{
  "enable_pacman": true,
  "enable_aur": true,
  "enable_flatpak": true,
  "enable_git_repos": true,
  "enable_notifications": true,
  "enable_backups": true,
  "parallel_updates": false,
  "noconfirm": false,
  "excluded_packages": [],
  "notification_methods": ["desktop"],
  "webhook_url": null,
  "email_address": null
}
```

### Configuration Options

- **enable_pacman**: Enable or disable Pacman updates
- **enable_aur**: Enable or disable AUR helper updates
- **enable_flatpak**: Enable or disable Flatpak updates
- **enable_git_repos**: Enable or disable Git repository updates
- **enable_notifications**: Enable or disable notifications
- **enable_backups**: Enable or disable automatic backups
- **parallel_updates**: Run updates in parallel (faster but less readable output)
- **noconfirm**: Skip all confirmation prompts
- **excluded_packages**: List of packages to exclude from updates
- **notification_methods**: List of notification methods (e.g., ["desktop", "webhook"])
- **webhook_url**: Discord or Slack webhook URL for notifications
- **email_address**: Email address for notifications (planned feature)

## Hooks

You can execute custom scripts before and after updates by placing executable scripts in:

- **Pre-update hooks**: `~/.config/sysup/hooks/pre-update/`
- **Post-update hooks**: `~/.config/sysup/hooks/post-update/`

Example hook script:

```bash
#!/bin/bash
# ~/.config/sysup/hooks/pre-update/backup-database.sh

echo "Backing up database..."
mysqldump -u root mydatabase > /backup/db-$(date +%Y%m%d).sql
echo "Database backup complete!"
```

Make the script executable:

```bash
chmod +x ~/.config/sysup/hooks/pre-update/backup-database.sh
```

## File Structure

```
~/.config/sysup/
├── config.json              # User configuration
├── repositories.json        # Tracked Git repositories
├── statistics.json          # Update statistics
├── backups/                 # Package list backups
│   ├── packages_20260125_143022.txt
│   └── packages_20260124_020000.txt
└── hooks/
    ├── pre-update/          # Pre-update hook scripts
    └── post-update/         # Post-update hook scripts

~/.local/state/sysup/
└── sysup.log               # Application logs
```

## Statistics

Track your update history and identify frequently updated packages:

```bash
sysup --stats
```

Example output:

```
=== Update Statistics ===
Total Updates: 42
Last Update: 2026-01-25 14:30:22

Top 10 Most Updated Packages:
  linux: 8 times
  firefox: 7 times
  python: 6 times
  ...

Recent Updates:
  2026-01-25 14:30:22 - pacman (23 packages)
  2026-01-24 02:00:15 - yay (5 packages)
  2026-01-23 10:15:30 - flatpak (2 packages)
```

## Notifications

### Desktop Notifications

Desktop notifications are enabled by default. Requires `notify-send`:

```bash
sudo pacman -S libnotify
```

### Webhook Notifications (Discord/Slack)

1. Create a webhook in Discord or Slack
2. Edit `~/.config/sysup/config.json`:

```json
{
  "notification_methods": ["desktop", "webhook"],
  "webhook_url": "https://discord.com/api/webhooks/your-webhook-url"
}
```

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the need for a unified update manager for Arch Linux
- Thanks to the Arch Linux community for their ecosystem
- Developed for Arch Linux users

## Contact

**san1ura** - GitHub: [@san1ura](https://github.com/san1ura)

Project Link: [https://github.com/san1ura/sysup](https://github.com/san1ura/sysup)

---

If you find this project useful, please consider giving it a star.
