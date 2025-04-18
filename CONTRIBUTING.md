# Contributing to PyTest SQLite POC

Thank you for considering contributing to this project! Here are some guidelines to help you get started.

## Development Setup

1. Fork the repository
2. Clone your fork
   ```bash
   git clone https://github.com/your-username/pytest-sqlite-poc.git
   cd pytest-sqlite-poc
   ```
3. Set up the development environment using Docker (recommended)
   ```bash
   task setup
   ```

## Making Changes

1. Create a new branch for your feature or bugfix
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Run the tests to ensure everything works
   ```bash
   task test
   ```
4. Commit your changes with a descriptive message
   ```bash
   git commit -m "Add feature: description of your changes"
   ```

## Pull Request Process

1. Push your changes to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a pull request against the main repository
3. Ensure your PR description clearly describes the problem and solution
4. Wait for review and address any feedback

## Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Include docstrings for functions and classes
- Write tests for new functionality

## Testing

- All tests should pass before submitting a PR
- Add new tests for new functionality
- Ensure tests are isolated and don't depend on external state

Thank you for your contributions!
