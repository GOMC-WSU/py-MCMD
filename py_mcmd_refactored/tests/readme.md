 # unit and integration tests
 ## Running the Test Suite

Pytest offers several output modes to suit different needs:

| Command                       | Description                                                                                 |
|-------------------------------|---------------------------------------------------------------------------------------------|
| `pytest -q`                   | **Quiet mode**: prints a dot (`.`) per passing test and one letter per failure.             |
| `pytest -v`                   | **Verbose mode**: shows each test’s full name and its PASS/FAIL status.                    |
| `pytest -vv`                  | **Very verbose**: even more detailed output, including setup/teardown of fixtures.          |
| `pytest --maxfail=1 -q`       | Stop after the first failure (quiet mode).                                                  |
| `pytest --disable-warnings`   | Suppress warning output. Can be combined with other flags (e.g. `-q`).                      |
| `pytest --collect-only -q`    | **Collection mode**: list all discovered tests without executing them.                      |

### Examples

```bash
# Quiet output:
pytest -q

# Verbose output with test names:
pytest -v

# Very verbose (shows fixture setup/teardown):
pytest -vv

# List all tests without running:
pytest --collect-only -q

# Quit after first failure (quiet):
pytest --maxfail=1 -q

