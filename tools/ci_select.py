"""The tests of the quick CI job for a PR (#2089).

A PR that changes only Markdown files runs only the doc tests: the test files that read a `.md` file, directly or
through a module of the repository that they import. Each other PR runs `ruff` and the full fast suite.
The selection reads the code, so a new test that reads a `.md` file needs no marker.
Usage: `python3 tools/ci_select.py BASE` prints nothing (run all) or the doc test files (the job runs only them).
"""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = re.compile(r"""["'][^"'\s]*\.md["']|LEARNINGS|SKILL""")     # a string that names a Markdown file
IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+)?import\s+\(?([\w., ]+)", re.M)


def reads_md(path):
    with open(path) as f:
        return bool(MD.search(f.read()))


def imports(text):
    """The module names that a file imports: `import a, b`, `from a import b` (a and a.b)."""
    out = set()
    for base, names in IMPORT.findall(text):
        for n in names.split(","):
            n = n.split(" as ")[0].strip()
            out |= {base, f"{base}.{n}"} if base else {n}
    return out


def modules(root=ROOT):
    """Module name → its file, for the modules of the repository (root, tools/, game/)."""
    out = {}
    for d in ("", "tools", "game"):
        for p in glob.glob(os.path.join(root, d, "*.py")):
            name = os.path.basename(p)[:-3]
            out.setdefault(name, p)
            if d:
                out.setdefault(f"{d}.{name}", p)
    return out


def doc_tests(root=ROOT):
    """The test files that read a Markdown file, sorted."""
    mods = {n: p for n, p in modules(root).items() if reads_md(p)}
    out = []
    for p in sorted(glob.glob(os.path.join(root, "tests", "test_*.py")) + glob.glob(os.path.join(root, "framework", "tests", "test_*.py"))):
        with open(p) as f:
            text = f.read()
        if MD.search(text) or imports(text) & mods.keys():
            out.append(os.path.relpath(p, root))
    return out


def select(files, root=ROOT):
    """None (run all) or the doc tests, when each changed file is a Markdown file."""
    if not files or not all(f.endswith(".md") for f in files):
        return None
    return doc_tests(root)


def main(argv):
    files = subprocess.run(["git", "diff", "--name-only", argv[1], "HEAD"], cwd=ROOT, check=True,
                           capture_output=True, text=True).stdout.split()
    tests = select(files)
    print(" ".join(tests or []))
    print(f"{len(files)} changed files: " + ("doc tests only" if tests else "all tests"), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
