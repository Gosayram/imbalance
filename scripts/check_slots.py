import ast
import sys
from pathlib import Path

found = []
for f in Path('src/imbalance/graph').glob('*.py'):
    tree = ast.parse(f.read_text())
    for n in ast.walk(tree):
        if not isinstance(n, ast.ClassDef):
            continue
        for d in n.decorator_list:
            if isinstance(d, ast.Call) and hasattr(d.func, 'id') and d.func.id == 'dataclass':
                k = {x.arg: x.value for x in d.keywords}
                s = k.get('slots')
                if not (s and isinstance(s, ast.Constant) and s.value):
                    found.append(f'{f}:{n.lineno} class {n.name}')

if found:
    for msg in found:
        print(msg)
    sys.exit(1)
else:
    print('All graph dataclasses have slots=True')
