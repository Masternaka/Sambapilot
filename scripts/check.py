"""Vérifications locales sans dépendance, import de l'application ou écriture."""

import ast
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    python_files = sorted(path for folder in ('sambapilot', 'tests', 'scripts')
                          for path in (ROOT / folder).rglob('*.py'))
    for path in python_files:
        try:
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as error:
            errors.append(str(error))
    documents = [ROOT / 'README.md', ROOT / 'AGENTS.md', *sorted((ROOT / 'docs').rglob('*.md'))]
    links = 0
    for path in documents:
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as error:
            errors.append(str(error))
            continue
        for target in re.findall(r'\]\(([^)]+)\)', content):
            if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            destination = (path.parent / unquote(target.split('#', 1)[0])).resolve()
            if ROOT not in destination.parents or not destination.is_file():
                errors.append(str(path.relative_to(ROOT)) + ' : lien local invalide : ' + target)
            links += 1
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(str(len(python_files)) + ' fichiers Python : syntaxe valide')
    print(str(links) + ' liens locaux valides dans ' + str(len(documents)) + ' documents (cibles uniquement)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
