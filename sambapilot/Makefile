PYTHON ?= python3

.PHONY: test check demo

test:
	$(PYTHON) -B -m unittest discover -s tests -v

check:
	$(PYTHON) -B -c 'import ast, pathlib; files = [*pathlib.Path("sambapilot").glob("*.py"), *pathlib.Path("tests").glob("*.py")]; [ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in files]; print(str(len(files)) + " fichiers Python vérifiés")'

demo:
	$(PYTHON) -B -m sambapilot diagnostic --demo
