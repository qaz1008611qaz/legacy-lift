"""Scan a code base for Python 2 constructs and local import edges.

Python 2 sources usually cannot be parsed by the Python 3 ``ast`` module,
so the scanner works line by line with conservative regular expressions.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# (rule id, pattern, weight, short hint for the migration prompt)
RULES = [
    ("print-statement", re.compile(r"^\s*print\s+(?![(=])\S"), 1, "print x -> print(x)"),
    ("except-comma", re.compile(r"^\s*except\s+[\w.]+\s*,\s*\w+\s*:"), 2, "except E, e -> except E as e"),
    ("dict-iter", re.compile(r"\.(iteritems|itervalues|iterkeys)\s*\("), 2, "iteritems() -> items()"),
    ("has-key", re.compile(r"\.has_key\s*\("), 2, "d.has_key(k) -> k in d"),
    ("xrange", re.compile(r"\bxrange\s*\("), 1, "xrange -> range"),
    ("raw-input", re.compile(r"\braw_input\s*\("), 1, "raw_input -> input"),
    ("unicode-type", re.compile(r"\b(unicode|basestring)\b"), 3, "str/bytes semantics, needs review"),
    ("legacy-stdlib", re.compile(r"^\s*(import|from)\s+(urllib2|urlparse|ConfigParser|Queue|StringIO|cPickle|HTMLParser)\b"), 2, "renamed stdlib module"),
    ("old-octal", re.compile(r"(?<![\w.])0[0-7]+\b"), 1, "0755 -> 0o755"),
    ("exec-statement", re.compile(r"^\s*exec\s+[\"'\w]"), 3, "exec statement -> exec()"),
    ("long-literal", re.compile(r"\b\d+[lL]\b"), 1, "10L -> 10"),
]

FROM_RE = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+\(?([\w\s,*]+)")
IMPORT_RE = re.compile(r"^\s*import\s+([\w.]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+as\s+\w+)?)*)")


@dataclass
class Finding:
    rule: str
    line: int
    weight: int
    hint: str


@dataclass
class ModuleReport:
    name: str
    path: str
    lines: int
    findings: list = field(default_factory=list)
    imports: set = field(default_factory=set)

    @property
    def risk(self) -> int:
        return sum(f.weight for f in self.findings)


def module_name(root: str, path: str) -> str:
    rel = os.path.relpath(path, root)[:-3].replace(os.sep, ".")
    return rel[: -len(".__init__")] if rel.endswith(".__init__") else rel


def _strip_strings(line: str) -> str:
    line = line.split("#", 1)[0]
    return re.sub(r"(\"[^\"]*\"|'[^']*')", '""', line)


def scan_file(root: str, path: str) -> ModuleReport:
    with open(path, encoding="utf-8", errors="replace") as fh:
        source = fh.read().splitlines()
    report = ModuleReport(module_name(root, path), path, len(source))
    for no, raw in enumerate(source, 1):
        code = _strip_strings(raw)
        for rule, pattern, weight, hint in RULES:
            if pattern.search(code):
                report.findings.append(Finding(rule, no, weight, hint))
        m = FROM_RE.match(code)
        if m:  # "from pkg import a, b" may import submodules pkg.a / pkg.b
            names = [n.split()[0] for n in m.group(2).split(",") if n.strip() and n.strip() != "*"]
            report.imports.add((m.group(1), tuple(names)))
            continue
        m = IMPORT_RE.match(code)
        if m:
            report.imports.update((n.split()[0], ()) for n in m.group(1).split(","))
    return report


def scan_repo(root: str) -> dict:
    """Return {module name: ModuleReport}; imports are resolved to local modules only."""
    reports = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "venv", "__pycache__"))]
        for fn in filenames:
            if fn.endswith(".py"):
                rep = scan_file(root, os.path.join(dirpath, fn))
                reports[rep.name] = rep
    local = set(reports)
    for rep in reports.values():
        package = rep.name.rsplit(".", 1)[0] if "." in rep.name else ""
        resolved = set()
        for base, names in rep.imports:
            # Python 2 implicit relative imports: "import utils" inside shop/ means shop.utils
            for prefix in ([base, f"{package}.{base}"] if package else [base]):
                hits = {f"{prefix}.{n}" for n in names} & local
                if hits:
                    resolved |= hits
                    break
                if prefix in local:
                    resolved.add(prefix)
                    break
        resolved.discard(rep.name)
        rep.imports = resolved
    return reports
