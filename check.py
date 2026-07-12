import ast

snippet = '''
name = "test"
doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ประวัติ: {name}</title>
  <link rel="stylesheet" href="/static/app.css">
  <style>
    body {{ font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 16px; line-height: 1.7;
      max-width: 50rem; margin: 0 auto; padding: 1.25rem; background: #f7f4ef; color: #1c1a17; }}
"""
'''

try:
    ast.parse(snippet)
    print("OK")
except SyntaxError as e:
    print("Syntax error:", e)
