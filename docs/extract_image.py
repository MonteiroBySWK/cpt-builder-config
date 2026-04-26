#!/usr/bin/env python3
import re, base64, sys
md = "/home/monteiro/docs/redes-avan/ATIVIDADE 1ª Avaliação.md"
out = "/home/monteiro/docs/redes-avan/activity_image.png"
with open(md, 'r', encoding='utf-8', errors='ignore') as f:
    s = f.read()
m = re.search(r'<data:image/png;base64,([^>]+)>', s, re.S)
if not m:
    print("No embedded image found in MD", file=sys.stderr)
    sys.exit(1)
b64 = m.group(1).strip()
b64 = ''.join(b64.split())
try:
    data = base64.b64decode(b64)
except Exception as e:
    print("Base64 decode error:", e, file=sys.stderr)
    sys.exit(1)
with open(out, 'wb') as f:
    f.write(data)
print("Wrote:", out)
