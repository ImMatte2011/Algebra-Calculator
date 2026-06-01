Contributing

Thanks for contributing! Guidelines:

- Code style: follow existing project conventions. Keep changes minimal and focused.
- Tests: add pytest tests under `rpi4/tests` (use existing tests as examples).
- Linting: run `ruff`/`flake8` if available in your environment.
- Commits: use small descriptive commits. Open a PR against `main` or `develop` branch.
- CI: PRs should run tests automatically (add GitHub Actions workflow later).
- ESP32: hardware-specific changes should be tested on device or with mocks. Use `scripts/deploy_esp32.py` to generate `esp32/settings.py` for flashing.

Process:
1. Fork the repo.
2. Create a feature branch.
3. Add tests and documentation for your change.
4. Open a PR and request review.

Contact: open an issue if you're unsure where to start.
