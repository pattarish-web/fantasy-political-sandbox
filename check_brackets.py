with open('app/export_html.py', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('doc = f"""<!DOCTYPE html>')
end = text.find('"""', start+10)
f_text = text[start:end]
for i, line in enumerate(f_text.split('\n')):
    if '{' in line:
        print(f'{i}: {line}')
