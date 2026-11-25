# Fork-only CI helper (not part of the upstream change).
# This file was generated with the assistance of an AI coding tool.
# Usage: slice_extract.py <parse.cpp> <name> > out.h
# Copies format_double_shortest out of parse.cpp, renamed to <name>.
import sys

src = open(sys.argv[1]).read()
sig = "static inline void format_double_shortest(char (&buf)[64], double d) {"
start = src.index(sig)
assert src.count(sig) == 1
depth = 0
i = src.index("{", start)
while True:
    if src[i] == "{":
        depth += 1
    elif src[i] == "}":
        depth -= 1
        if depth == 0:
            break
    i += 1
body = src[start : i + 1].replace("format_double_shortest", sys.argv[2])
print(body)
