"""SPDX-License-Identifier: MIT"""
"""Copyright (c) 2026 Sergi Alvarez Triviño"""

import os
import re
import shutil
import sys
import time


SPACE_CALL_ARITY = {
    "slugify": 1,
    "slugToWord": 2,
    "parse": 3,
    "replaceInPageText": 2,
    "redirect": 1,
    "setSession": 2,
    "getSession": 1,
    "setLocalstorage": 2,
    "getLocalstorage": 1,
}


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HELPERS_SOURCE = os.path.join(SCRIPT_DIR, "helpers.php")
RUNTIME_DIRNAME = "neohp"


def ensure_runtime_helpers(target_dir):
    runtime_dir = os.path.join(os.path.abspath(target_dir), RUNTIME_DIRNAME)
    os.makedirs(runtime_dir, exist_ok=True)

    runtime_helpers_path = os.path.join(runtime_dir, "helpers.php")
    shutil.copy2(HELPERS_SOURCE, runtime_helpers_path)
    return runtime_helpers_path


def build_helpers_include(filepath, runtime_helpers_path):
    php_dir = os.path.dirname(os.path.abspath(filepath))
    relative_helpers = os.path.relpath(runtime_helpers_path, php_dir)
    relative_helpers = relative_helpers.replace(os.sep, "/")
    return f"<?php\ninclude_once __DIR__ . '/{relative_helpers}';\n"


def split_inline_comment(line):
    in_single = False
    in_double = False

    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "#" and not in_single and not in_double:
            return line[:i].rstrip(), line[i + 1 :].strip()

    return line.rstrip(), ""


def split_top_level_whitespace(payload, expected_parts):
    parts = []
    buff = []
    depth = 0
    in_single = False
    in_double = False

    for ch in payload:
        if ch == "'" and not in_double:
            in_single = not in_single
            buff.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buff.append(ch)
            continue

        if not in_single and not in_double:
            if ch in "([{" :
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)

            if ch.isspace() and depth == 0 and len(parts) < expected_parts - 1:
                current = "".join(buff).strip()
                if current:
                    parts.append(current)
                    buff = []
                continue

        buff.append(ch)

    tail = "".join(buff).strip()
    if tail:
        parts.append(tail)
    return parts


def normalize_space_call(expr):
    stripped = expr.strip()
    for fn_name, arity in SPACE_CALL_ARITY.items():
        prefix = f"{fn_name} "
        if stripped.startswith(prefix) and not stripped.startswith(f"{fn_name}("):
            payload = stripped[len(prefix) :].strip()
            args = split_top_level_whitespace(payload, arity)
            if len(args) == arity:
                return f"{fn_name}({', '.join(args)})"
    return expr


def load_space_functions():
    """Loads allowed space-separated function names from lib/spaceFunctions.txt"""
    path = os.path.join("lib", "spaceFunctions.txt")
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        }


def translate_line(line):
    indent_match = re.match(r"^(\s*)", line)
    indent = indent_match.group(1) if indent_match else ""
    stripped = line.strip()

    if not stripped:
        return "\n", False, False  # line, opens_block, is_else

    if stripped.startswith("#"):
        return f"{indent}// {stripped[1:].strip()}\n", False, False

    code, inline_comment = split_inline_comment(stripped)
    stripped = code.strip()
    comment_tail = f" // {inline_comment}" if inline_comment else ""

    if not stripped:
        return f"{indent}// {inline_comment}\n" if inline_comment else "\n", False, False

    # 1. include config.pyh -> include_once 'config.php';
    if stripped.startswith("include "):
        mod = stripped[len("include ") :].strip()
        mod_php = re.sub(r"\.pyh$", ".php", mod, flags=re.IGNORECASE)
        return f"{indent}include_once '{mod_php}';{comment_tail}\n", False, False

    # 2. Debug_on -> PHP error settings
    if stripped.lower() == "debug_on":
        code = (
            f"{indent}ini_set('display_errors', '1');\n"
            f"{indent}ini_set('display_startup_errors', '1');\n"
            f"{indent}error_reporting(E_ALL);{comment_tail}\n"
        )
        return code, False, False

    # 3. foreach dbData as row:
    match = re.match(r"^foreach\s+(.+?)\s+as\s+(.+?)\s*:$", stripped)
    if match:
        arr, var = match.groups()
        return (
            f"{indent}foreach ({translate_expr(arr)} as ${var.strip()}) {{{comment_tail}\n",
            True,
            False,
        )

    # 4. if condition:
    match = re.match(r"^if\s+(.+?)\s*:$", stripped)
    if match:
        cond = match.group(1)
        return f"{indent}if ({translate_expr(cond)}) {{{comment_tail}\n", True, False

    # 5. else -> } else {
    if stripped == "else":
        return f"{indent}}} else {{{comment_tail}\n", True, True

    # 5b. else x = y  -> } else { x = y; }
    match = re.match(r"^else\s+(.+)$", stripped)
    if match:
        statement = translate_expr(match.group(1))
        return f"{indent}}} else {{ {statement}; }}{comment_tail}\n", False, True

    # 5c. try:
    if re.match(r"^try\s*:$", stripped):
        return f"{indent}try {{{comment_tail}\n", True, False

    # 5d. except ExceptionType as err:
    match = re.match(
        r"^except\s+([A-Za-z_\\][A-Za-z0-9_\\]*)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)\s*:$",
        stripped,
    )
    if match:
        exc_type, exc_var = match.groups()
        php_exc_type = exc_type if exc_type.startswith("\\") else f"\\{exc_type}"
        return (
            f"{indent}}} catch ({php_exc_type} ${exc_var}) {{{comment_tail}\n",
            True,
            True,
        )

    # 5e. except ExceptionType:
    match = re.match(r"^except\s+([A-Za-z_\\][A-Za-z0-9_\\]*)\s*:$", stripped)
    if match:
        exc_type = match.group(1)
        php_exc_type = exc_type if exc_type.startswith("\\") else f"\\{exc_type}"
        return f"{indent}}} catch ({php_exc_type} $e) {{{comment_tail}\n", True, True

    # 5f. except:
    if re.match(r"^except\s*:$", stripped):
        return f"{indent}}} catch (\\Throwable $e) {{{comment_tail}\n", True, True

    # 5g. finally:
    if re.match(r"^finally\s*:$", stripped):
        return f"{indent}}} finally {{{comment_tail}\n", True, True

    # 6. loopCsv "file.csv" as city:
    match = re.match(r'^loopCsv\s+(["\'].+?["\'])\s+as\s+(.+?):$', stripped)
    if match:
        csv_file, var = match.groups()
        return (
            f"{indent}foreach (readCsv({csv_file}) as ${var.strip()}) {{{comment_tail}\n",
            True,
            False,
        )

    # 7. break
    if stripped == "break":
        return f"{indent}break;{comment_tail}\n", False, False

    # 8. Handle space-separated function calls loaded from lib/spaceFunctions.txt
    space_funcs = load_space_functions()
    first_word = stripped.split()[0] if stripped else ""
    if first_word in space_funcs and "(" not in stripped:
        args_payload = stripped[len(first_word) :].strip()
        if first_word in SPACE_CALL_ARITY:
            arg_count = SPACE_CALL_ARITY[first_word]
            raw_args = split_top_level_whitespace(args_payload, arg_count)
            if len(raw_args) == arg_count:
                translated_args = ", ".join(translate_expr(arg) for arg in raw_args)
                return (
                    f"{indent}{first_word}({translated_args});{comment_tail}\n",
                    False,
                    False,
                )

        translated_args = translate_expr(args_payload)
        return f"{indent}{first_word}({translated_args});{comment_tail}\n", False, False

    # 8b. Basic assignment support: lhs = rhs
    match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$", stripped)
    if match:
        lhs, rhs = match.groups()
        return f"{indent}${lhs} = {translate_expr(rhs)};{comment_tail}\n", False, False

    # 9. General Function mappings & assignments
    translated = translate_expr(stripped)
    return f"{indent}{translated};{comment_tail}\n", False, False


def translate_expr(expr):
    expr = normalize_space_call(expr.strip())

    # Auto-quote plain emails written without quotes.
    expr = re.sub(
        r"(?<![\w'\"])\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b(?![\w'\"])",
        r"'\1'",
        expr,
    )

    # Handle associative array shorthand: name -> "james" => 'name' => 'james'
    expr = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*", r"'\1' => ", expr)

    # Convert Python-like dict keys to PHP style ['key' => value]
    expr = re.sub(r'"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:\s*', r"'\1' => ", expr)
    expr = re.sub(r"'([a-zA-Z_][a-zA-Z0-9_]*)'\s*:\s*", r"'\1' => ", expr)

    # Map print -> echo
    expr = re.sub(r"\bprint\s+", "echo ", expr)

    # Built-in shorthand translations
    expr = re.sub(r"\bgetPost\b", "$_POST", expr)
    expr = re.sub(r"\bgetUrl\b", "($_SERVER['REQUEST_URI'] ?? '')", expr)
    expr = re.sub(r"\bparse\s*\(", "parseValue(", expr)
    expr = re.sub(r"\bcurl\s*\(", "httpRequest(", expr)
    expr = re.sub(r"\bdbQuery\s*\((.+?)\)", r"dbQuery($db, \1)", expr)
    expr = re.sub(r"\bexit\s*\((.*?)\)", r"respondJson(\1)", expr)

    # Fix calls written with parentheses but missing commas.
    expr = re.sub(r"\bsetSession\((.+?)\s+(.+?)\)", r"setSession(\1, \2)", expr)
    expr = re.sub(r"\bsetLocalstorage\((.+?)\s+(.+?)\)", r"setLocalstorage(\1, \2)", expr)

    # Wrap insert third argument when key=>value is used without []
    insert_match = re.match(r"^insert\((.+?),\s*(.+?),\s*(.+)\)$", expr)
    if insert_match:
        db_expr, table_expr, data_expr = insert_match.groups()
        data_expr = data_expr.strip()
        if "=>" in data_expr and not data_expr.startswith("["):
            expr = f"insert({db_expr}, {table_expr}, [{data_expr}])"

    # Space-call fallback when mixed in expressions
    expr = re.sub(r"\bredirect\s+(.+)$", r"redirect(\1)", expr)
    expr = re.sub(r"\bsetSession\s+(.+?)\s+(.+)$", r"setSession(\1, \2)", expr)
    expr = re.sub(r"\bgetSession\s+(.+)$", r"getSession(\1)", expr)
    expr = re.sub(r"\bsetLocalstorage\s+(.+?)\s+(.+)$", r"setLocalstorage(\1, \2)", expr)
    expr = re.sub(r"\bgetLocalstorage\s+(.+)$", r"getLocalstorage(\1)", expr)

    php_keywords = {
        "true",
        "false",
        "TRUE",
        "FALSE",
        "null",
        "NULL",
        "as",
        "and",
        "or",
        "not",
        "array",
        "echo",
        "include",
        "include_once",
        "require",
        "new",
        "break",
        "if",
        "else",
        "foreach",
        "response",
    }

    parts_in_quotes = re.split(r'(".*?"|\'.*?\')', expr)
    new_parts = []

    for i, part in enumerate(parts_in_quotes):
        if i % 2 == 1:
            new_parts.append(part)
        else:
            # Convert dot notation safely outside strings: arrayPost.customer -> $arrayPost['customer']
            part = re.sub(
                r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b",
                r"$\1['\2']",
                part,
            )

            # Python-style literals to PHP
            part = re.sub(r"\bTrue\b", "TRUE", part)
            part = re.sub(r"\bFalse\b", "FALSE", part)
            part = re.sub(r"\bNone\b", "NULL", part)

            def add_dollar(match):
                word = match.group(0)
                if word in php_keywords or word.startswith("$"):
                    return word
                return f"${word}"

            processed = re.sub(
                r"(?<!\$)\b[a-zA-Z_][a-zA-Z0-9_]*\b(?!\s*\()",
                add_dollar,
                part,
            )
            new_parts.append(processed)

    translated = "".join(new_parts)
    translated = translated.replace("$$", "$")
    translated = re.sub(r"\['\$([a-zA-Z_][a-zA-Z0-9_]*)'\]", r"['\1']", translated)
    translated = re.sub(r"respondJson\(\s*\{", "respondJson([", translated)
    translated = re.sub(r"\}\s*\)", "])", translated)
    return translated


def compile_file(filepath, runtime_helpers_path):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = re.split(r"(#\?|\?#)", content)
    output = []
    in_code_block = False
    helpers_included = False

    for part in parts:
        if part == "#?":
            in_code_block = True
            if not helpers_included:
                output.append(build_helpers_include(filepath, runtime_helpers_path))
                helpers_included = True
            else:
                output.append("<?php\n")
            continue
        elif part == "?#":
            in_code_block = False
            output.append("?>")
            continue

        if in_code_block:
            lines = part.splitlines()
            # Indentation block tracking stack: stores (indent_string, opens_else_flag)
            block_stack = []

            for line in lines:
                indent_match = re.match(r"^(\s*)", line)
                current_indent = len(indent_match.group(1)) if indent_match else 0

                # Close blocks whose indentation is higher than current line.
                # If current line is else, keep same-level block open for proper } else { emission.
                stripped_check = line.strip()
                is_current_else = bool(
                    re.match(r"^(else|except|finally)(\s|$|:)", stripped_check)
                )

                while block_stack and (
                    block_stack[-1] > current_indent
                    or (
                        block_stack[-1] == current_indent
                        and not is_current_else
                    )
                ):
                    top = block_stack.pop()
                    closing_indent = " " * top
                    output.append(f"{closing_indent}}}\n")

                translated_line, opens_block, is_else = translate_line(line)
                output.append(translated_line)

                if opens_block:
                    if is_else and block_stack and block_stack[-1] == current_indent:
                        block_stack.pop()
                    block_stack.append(current_indent)
                elif is_else and block_stack and block_stack[-1] == current_indent:
                    block_stack.pop()

            # Close any remaining unclosed blocks at the end of the script block
            while block_stack:
                top = block_stack.pop()
                closing_indent = " " * top
                output.append(f"{closing_indent}}}\n")
        else:
            output.append(part)

    php_content = "".join(output)
    out_path = re.sub(r"\.pyh$", ".php", filepath, flags=re.IGNORECASE)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(php_content)
    print(f"Compiled: {filepath} -> {out_path}")


def iter_pyh_files(target_dir):
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".pyh"):
                yield os.path.join(root, file)


def compile_all(target_dir):
    runtime_helpers_path = ensure_runtime_helpers(target_dir)
    for filepath in iter_pyh_files(target_dir):
        compile_file(filepath, runtime_helpers_path)


def snapshot_pyh_mtimes(target_dir):
    mtimes = {}
    for filepath in iter_pyh_files(target_dir):
        try:
            mtimes[filepath] = os.path.getmtime(filepath)
        except OSError:
            # File may disappear between walk and stat.
            continue
    return mtimes


def watch_and_compile(target_dir, interval=0.8):
    target_dir = os.path.abspath(target_dir)
    print(f"Watching: {target_dir} (recursive) | interval={interval}s")

    compile_all(target_dir)
    known_mtimes = snapshot_pyh_mtimes(target_dir)

    try:
        while True:
            runtime_helpers_path = ensure_runtime_helpers(target_dir)
            current_mtimes = snapshot_pyh_mtimes(target_dir)

            # Recompile changed and newly-created .pyh files.
            for filepath, mtime in current_mtimes.items():
                previous = known_mtimes.get(filepath)
                if previous is None or mtime > previous:
                    compile_file(filepath, runtime_helpers_path)

            known_mtimes = current_mtimes
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")


def main():
    args = sys.argv[1:]
    target_dir = "."
    watch_mode = False
    interval = 0.8

    if args and not args[0].startswith("--"):
        target_dir = args[0]
        args = args[1:]

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--watch", "-w"):
            watch_mode = True
            i += 1
            continue
        if arg == "--interval":
            if i + 1 >= len(args):
                print("Error: --interval requires a numeric value.")
                return
            try:
                interval = float(args[i + 1])
                if interval <= 0:
                    raise ValueError
            except ValueError:
                print("Error: --interval must be a positive number.")
                return
            i += 2
            continue
        if arg in ("--help", "-h"):
            print(
                "Usage: python3 interpreter.py [target_dir] [--watch|-w] [--interval seconds]"
            )
            print("  target_dir: directory to compile/watch recursively (default: .)")
            print("  --watch, -w: keep running and auto-compile changed .pyh files")
            print("  --interval: polling interval in seconds for watch mode (default: 0.8)")
            return

        print(f"Error: unknown argument: {arg}")
        print("Try: python3 interpreter.py --help")
        return

    if watch_mode:
        watch_and_compile(target_dir, interval)
    else:
        compile_all(target_dir)


if __name__ == "__main__":
    main()