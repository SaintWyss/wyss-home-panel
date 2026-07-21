from pathlib import Path

path = Path(__file__).resolve().parent / "apply_manual_door_check.py"
text = path.read_text(encoding="utf-8")
needle = r'''\n}\n\n",\n            "implementacion del check manual",'''
replacement = r'''\n}\n\n""",\n            "implementacion del check manual",'''
count = text.count(needle)
if count != 1:
    raise RuntimeError(f"Literal incompleto esperado una vez; encontrado {count}")
corrected = text.replace(needle, replacement, 1)
compile(corrected, str(path), "exec")
path.write_text(corrected, encoding="utf-8")
