# Contributing to sysup

First off, thank you for considering contributing to sysup! 🎉

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include logs** from `~/.local/state/sysup/sysup.log`
- **Mention your system info** (`sysup --info`)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List some examples of how it would be used**

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Make your changes:
   - Write clear, commented code
   - Follow the existing code style (PEP 8 for Python)
   - Add docstrings to functions and classes
   - Update documentation if needed
4. Test your changes thoroughly
5. Commit your changes:
   ```bash
   git commit -m "Add amazing feature"
   ```
6. Push to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```
7. Open a Pull Request

### Code Style Guidelines

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Write descriptive variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose
- Use meaningful commit messages

### Testing

Before submitting a PR:

- Test on a fresh Arch Linux installation if possible
- Test with different configurations (AUR helpers, with/without Flatpak, etc.)
- Test error cases and edge cases
- Check that logging works correctly

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/sysup.git
cd sysup

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make the script executable
chmod +x sysup.py

# Run the script
./sysup.py --help
```

## Project Structure

```
sysup/
├── sysup.py              # Main script
├── README.md             # Documentation
├── LICENSE               # MIT License
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── CONTRIBUTING.md      # This file
```

## Questions?

Feel free to open an issue with the `question` label if you have any questions!

Thank you for your contributions! 🙏
