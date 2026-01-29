# sysup Makefile - Minimal version
install:
	pip install -r requirements.txt
	sudo install -Dm755 main.py /usr/local/bin/sysup
	@echo "sysup installed successfully!"

install-user:
	pip install --user -r requirements.txt
	mkdir -p $(HOME)/.local/bin
	install -Dm755 main.py $(HOME)/.local/bin/sysup
	@echo "sysup installed to ~/.local/bin/sysup"

uninstall:
	sudo rm -f /usr/local/bin/sysup

uninstall-user:
	rm -f $(HOME)/.local/bin/sysup
