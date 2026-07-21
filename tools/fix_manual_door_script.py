from pathlib import Path

path = Path(__file__).resolve().parent / "apply_manual_door_check.py"
text = path.read_text(encoding="utf-8")
old = '''                       false);\n}\n\n",\n            "implementacion del check manual",'''
new = '''                       false);\n}\n\n""",\n            "implementacion del check manual",'''
if old not in text:
    raise RuntimeError("No se encontro el literal incompleto del check manual")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
