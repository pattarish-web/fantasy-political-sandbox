import ast
code = '''
doc = f"""
    body {{ font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 16px; line-height: 1.7;
      max-width: 50rem; margin: 0 auto; padding: 1.25rem; background: #f7f4ef; color: #1c1a17; }}
"""
'''
try:
    ast.parse(code)
    print("OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}, offset {e.offset}: {e.msg}")
