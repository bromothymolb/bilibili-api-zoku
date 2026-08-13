import os

# Check the code.
commands = [
    "ruff check bilibili_api/*",
    "pyright bilibili_api/*"
]

exit_code = 0

for cmd in commands:
    print(f"Running {cmd}")
    print("------------------------------------------------------------")
    code = os.system(cmd)
    print(f"------------------------------------------------exit code: {code}")
    if code:
        exit_code = 1

exit(exit_code)
