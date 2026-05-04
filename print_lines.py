
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[390:425], 391):
    print(f'{i}: {line}', end='')

