from pathlib import Path

path = Path(__file__).resolve().parents[1] / "firmware/src/adapters/lvgl_panel_view.cpp"
text = path.read_text(encoding="utf-8")
old = '''            const std::string_view start = event.start;
            const std::string_view day = start.size() >= 10U ? start.substr(8U, 2U) : start;
            const std::string_view month = start.size() >= 7U ? start.substr(5U, 2U) : "--";
'''
new = '''            const std::string_view start = event.start;
'''
if old in text:
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
