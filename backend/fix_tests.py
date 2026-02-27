import re

filepath = 'tests/test_leave_requests.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace any dictionary containing "start_date" and "end_date" but NOT "reason"
# Example match: {"start_date": _in_days(1), "end_date": _in_days(2)}
new_content = re.sub(
    r'(\{\s*"start_date"\s*:\s*.*?\s*,\s*"end_date"\s*:\s*[^}]+?)(\s*\})',
    r'\1, "reason": "test"\2',
    content
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replaced!")
