"""
Example: sample Python code with intentional issues for demo purposes.
Run `python main.py review examples/sample_code.py` to see AI review in action.
"""

import os
import hashlib


def get_user(username, password):
    # BAD: plain MD5 for password — AI should flag this
    hashed = hashlib.md5(password.encode()).hexdigest()

    conn = None
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{hashed}'"  # BAD: SQL injection
    # cursor.execute(query)
    return query


def divide(a, b):
    return a / b  # Missing zero-division guard


def process_items(items):
    result = []
    for i in range(len(items)):  # Should use enumerate
        result.append(items[i] * 2)
    return result


class DataProcessor:
    def __init__(self):
        self.data = []

    def load(self, filepath):
        with open(filepath) as f:  # No encoding, no error handling
            self.data = f.readlines()

    def transform(self):
        output = {}
        for line in self.data:
            parts = line.split(",")
            output[parts[0]] = parts[1]  # IndexError if fewer than 2 columns
        return output
