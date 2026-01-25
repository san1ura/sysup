[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/san1ura/sysup)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)
[![Arch Linux](https://img.shields.io/badge/platform-Arch%20Linux-1793D1.svg)](https://archlinux.org/)

A powerful, feature-rich system update manager for Arch Linux that handles Pacman, AUR helpers (yay/paru), Flatpak packages, and Git repositories - all in one place.

## Features

-  **Unified Updates**: Update Pacman, AUR, Flatpak, and Git repos with a single command
-  **Dry Run Mode**: Preview what will be updated before making changes
-  **Automatic Backups**: Create package list backups before each update
-  **Statistics Tracking**: Monitor update history and most frequently updated packages
-  **Smart Notifications**: Desktop notifications and webhook support (Discord/Slack)
-  **Parallel Updates**: Optional parallel execution for faster updates
-  **Maintenance Tools**: Clean orphaned packages and cache
-  **Scheduled Updates**: Set up automatic daily or weekly updates via cron
-  **Pre/Post Hooks**: Run custom scripts before and after updates
-  **Git Repository Tracking**: Automatically update your dotfiles and config repos
-  **Colorful Output**: Beautiful, easy-to-read terminal interface
-  **Configurable**: Customize behavior via JSON configuration

##  Requirements

- **Arch Linux** or Arch-based distribution
- **Python 3.8+**
- **pacman-contrib** (for `checkupdates`)
- **colorama** Python package
- Optional: **yay** or **paru** (AUR helpers)
- Optional: **flatpak** (for Flatpak support)
- Optional: **notify-send** (for desktop notifications)

## 🔧 Installation

### Install dependencies

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

### Install sysup

```bash
# Clone the repository
git clone https://github.com/san1ura/sysup.git
cd sysup

# Make the script executable
chmod +x main.py

# Optional: Create a symbolic link for easy access
sudo ln -s "$(pwd)/main.py" /usr/local/bin/sysup
```

##  Usage

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

##  Configuration

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

- **enable_pacman**: Enable/disable Pacman updates
- **enable_aur**: Enable/disable AUR helper updates
- **enable_flatpak**: Enable/disable Flatpak updates
- **enable_git_repos**: Enable/disable Git repository updates
- **enable_notifications**: Enable/disable notifications
- **enable_backups**: Enable/disable automatic backups
- **parallel_updates**: Run updates in parallel (faster but less readable output)
- **noconfirm**: Skip all confirmation prompts
- **excluded_packages**: List of packages to exclude from updates
- **notification_methods**: List of notification methods (e.g., ["desktop", "webhook"])
- **webhook_url**: Discord/Slack webhook URL for notifications
- **email_address**: Email address for notifications (future feature)

##  Hooks

You can run custom scripts before and after updates by placing executable scripts in:

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

Don't forget to make it executable:
```bash
chmod +x ~/.config/sysup/hooks/pre-update/backup-database.sh
```

## 📁 File Structure

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

## 📊 Statistics

Track your update history and see which packages are updated most frequently:

```bash
sysup --stats
```

Output example:
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

## 🔔 Notifications

### Desktop Notifications

Desktop notifications are enabled by default (requires `notify-send`):

```bash
sudo pacman -S libnotify
```

### Webhook Notifications (Discord/Slack)

1. Create a webhook in Discord/Slack
2. Edit `~/.config/sysup/config.json`:

```json
{
  "notification_methods": ["desktop", "webhook"],
  "webhook_url": "https://discord.com/api/webhooks/your-webhook-url"
}
```

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need for a unified update manager for Arch Linux
- Thanks to the Arch Linux community for the amazing ecosystem
- Built with ❤️ for Arch users

## 📧 Contact

**san1ura** - GitHub: [@san1ura](https://github.com/san1ura)

Project Link: [https://github.com/san1ura/sysup](https://github.com/san1ura)

---

⭐ If you find this project useful, please consider giving it a star!
