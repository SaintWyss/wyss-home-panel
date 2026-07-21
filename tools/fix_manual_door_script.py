from pathlib import Path

path = Path(__file__).resolve().parent / "apply_manual_door_check.py"
text = path.read_text(encoding="utf-8")
marker = '            "implementacion del check manual",'
marker_at = text.find(marker)
if marker_at < 0:
    raise RuntimeError("No se encontro el marcador de implementacion del check manual")
closing = r'''\n\n",'''
closing_at = text.rfind(closing, 0, marker_at)
if closing_at < 0:
    raise RuntimeError("No se encontro el cierre incompleto antes del marcador")
corrected = text[:closing_at] + r'''\n\n""",''' + text[closing_at + len(closing):]
compile(corrected, str(path), "exec")
path.write_text(corrected, encoding="utf-8")
