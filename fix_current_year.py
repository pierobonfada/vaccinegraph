import re
with open('vacinas_cli.py', 'r') as f:
    code = f.read()

code = code.replace(
    "    parser.add_argument('--end-year', type=int, default=2026, help=\"Ano final da análise.\")",
    "    import datetime\n    current_year = datetime.date.today().year\n    parser.add_argument('--end-year', type=int, default=current_year, help=\"Ano final da análise (padrão: ano atual).\")"
)

with open('vacinas_cli.py', 'w') as f:
    f.write(code)
