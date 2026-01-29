# sysup Makefile

.PHONY: install install-user uninstall uninstall-user clean help

# Default target
help:
	@echo "SysUp Makefile - Available targets:"
	@echo "  make install        - Install sysup system-wide (requires sudo)"
	@echo "  make install-user   - Install sysup for current user only"
	@echo "  make uninstall      - Uninstall system-wide installation"
	@echo "  make uninstall-user - Uninstall user installation"
	@echo "  make clean          - Remove temporary files"

# System-wide installation (requires sudo)
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Installing sysup to /usr/local/bin..."
	sudo install -Dm755 main.py /usr/local/bin/sysup
	@echo ""
	@echo "✓ sysup installed successfully!"
	@echo "  Run 'sysup --version' to verify installation"
	@echo "  Run 'sysup --help' to see available options"

# User-only installation (no sudo needed)
install-user:
	@echo "Installing dependencies for user..."
	pip install --user -r requirements.txt
	@echo "Installing sysup to ~/.local/bin..."
	mkdir -p $(HOME)/.local/bin
	install -Dm755 main.py $(HOME)/.local/bin/sysup
	@echo ""
	@echo "✓ sysup installed to ~/.local/bin/sysup"
	@echo "  Make sure ~/.local/bin is in your PATH"
	@echo "  Add this to your ~/.bashrc or ~/.zshrc if needed:"
	@echo "    export PATH=\"\$$HOME/.local/bin:\$$PATH\""
	@echo ""
	@echo "  Run 'sysup --version' to verify installation"
	@echo "  Run 'sysup --help' to see available options"

# Uninstall system-wide installation
uninstall:
	@echo "Removing system-wide installation..."
	sudo rm -f /usr/local/bin/sysup
	@echo "✓ sysup uninstalled successfully!"

# Uninstall user installation
uninstall-user:
	@echo "Removing user installation..."
	rm -f $(HOME)/.local/bin/sysup
	@echo "✓ sysup uninstalled successfully!"

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete!"
