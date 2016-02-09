# FAQ

## Why python?

We are in the C++ world after all, why would I need python?

The standard library has everything we need. JSON, YAML, option parsing,
os.path, ...

## Why not built-in irony-mode?

Because the compile options issue is wider than irony-mode. By making this
standalone one can re-use it to work with other clang-tools or clang-compatible
tools. We only have to care about making this one tool right.
