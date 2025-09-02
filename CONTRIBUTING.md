# Contributing to LokKatha.ai - Smart Cultural Storyteller

Thank you for your interest in contributing! Please follow these guidelines to ensure a smooth development process.

## Coding Conventions
- Each service module in `app/services/` should focus on a single responsibility.
- Use `log_event` from `app/utils/log.py` for all logging. Do not use `print` in production code.
- Follow PEP8 for Python code style.
- Document all public functions with clear docstrings.

## Adding a New Feature or Service
1. Create a new module in `app/services/` for your feature.
2. Expose its functionality via a FastAPI route in `app/main.py`.
3. Add or update docstrings and update `docs/SERVICES.md` with the new interface.
4. If your feature requires new dependencies, add them to `requirements.txt` and document any system requirements in the README.

## Testing
- There is no formal test suite. Test your changes by running the app and using the UI at http://localhost:8000.
- Check `storyteller_log.txt` for runtime logs and errors.

## Pull Requests
- Briefly describe the feature or fix and affected modules.
- Keep pull requests focused and concise.
- Ensure your code passes basic manual testing before submitting.

## Environment Setup
- See the README and `.env.example` for setup instructions and required environment variables.
- Ensure `ffmpeg` and system TTS voices are available for media features.

## Questions?
Open an issue or contact the maintainer for help.
