import sys
import pytest

class StdoutRedirector:
    def __init__(self, filename):
        self.filename = filename
    def __enter__(self):
        self.file = open(self.filename, 'w', encoding='utf-8')
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = self.file
        sys.stderr = self.file
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.file.close()

if __name__ == "__main__":
    with StdoutRedirector("pytest_out.txt"):
        pytest.main(["tests/", "--tb=short", "--color=no"])
