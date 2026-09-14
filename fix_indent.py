with open('vacinas_cli.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.startswith("import numpy as np"):
        spaces = len(lines[i-1]) - len(lines[i-1].lstrip())
        lines[i] = " " * spaces + "import numpy as np\n"
with open('vacinas_cli.py', 'w') as f:
    f.writelines(lines)
