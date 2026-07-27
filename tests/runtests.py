#!/usr/bin/env python3

import subprocess
import sys
import os

TESTS = [
    "tests.testimport",
    "tests.testhistoric",
    "tests.testvalidator",
]

env = os.environ.copy()
env["PYTHONPATH"] = "src"

## NOTE: Each of these tests will print validation fails to std log output or optionally a file.
## NOTE: return code will be 0 if unrecoverable exception occurs or validation fails on stac.

for test in TESTS:
    print(f"Running {test}")

    result = subprocess.run(
        [sys.executable, "-m", test],
        env=env,
        cwd=os.getcwd(),
    )

    if result.returncode != 0:
        print(f"\nFAILED: {test}")
        sys.exit(result.returncode)

print("\nAll tests passed.")
