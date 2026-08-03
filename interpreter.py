import os
import re
import sys


def translate_line(line):
    # Strip trailing newline/whitespace for processing, but keep indentation
    indent_match = re.match(r"^(\s*)", line)
    indent = indent_match.group(1) if indent_match else ""
    stripped = line.strip()

    if not stripped or stripped.startswith("#"):
        return line

    # 1. include config.pyh -> include_once 'config.php';
    if stripped.startswith("include "):
        mod = stripped[len("include ") :].strip()
        mod_php = re.sub(r"\.pyh$", ".php", mod, flags=re.IGNORECASE)
        return f"{indent}include_once '{mod_php}';\n"

    # 2. Debug_on -> ini_set('display_errors', '1'); ...
    if stripped == "Debug_on":
        return (
            f"{indent}ini_set('display_errors', '1');\n"
            f"{indent}ini_set('display_startup_errors', '1');\n"
            f"{indent}error_reporting(E_ALL);\n"
        )

    # 3. foreach dbData as row: -> foreach ($dbData as $row) {
    match = re.match(r"^foreach\s+(.+?)\s+as\s+(.+?):$", stripped)
    if match:
        arr, var = match.groups()
        return f"{indent}foreach ({translate_expr(arr)} as ${var}) {{\n"

    # 4. if condition: -> if (condition) {
    match = re.match(r"^if\s+(.+?):$", stripped)
    if match:
        cond = match.group(1)
        return f"{indent}if ({translate_expr(cond)}) {{\n"

    # 5. else -> } else {
    if stripped == "else":
        # Usually needs a closing brace from previous if block, handled conceptually or standard block style
        return f"{indent}}} else {{\n"

    # 6. loopCsv "file.csv" as city: -> foreach (array_map('str_getcsv', file('file.csv')) as $city) {
    match = re.match(r'^loopCsv\s+(["\'].+?["\'])\s+as\s+(.+?):$', stripped)
    if match:
        csv_file, var = match.groups()
        return f"{indent}foreach (array_map('str_getcsv', file({csv_file})) as ${var}) {{\n"

    # 7. break
    if stripped == "break":
        return f"{indent}break;\n"

    # 8. Function mappings & assignments
    # Generic replacement for general code lines
    translated = translate_expr(stripped)
    return f"{indent}{translated};\n"


def translate_expr(expr):
    # Replace property access or method call dot: row.email -> $row['email'] or object -> property
    # For arrays/objects, we can map dot notation or handle basic variable names
    # Add $ to standard words unless they are keywords, strings, or numbers

    # Handle associative array shorthand: name -> "james" => 'name' => 'james'
    expr = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*", r"'\1' => ", expr)

    # Handle object/array property dot notation: arrayPost.customer -> $arrayPost['customer']
    # Let's do a simple pass for identifiers
    # Built-in function translations
    expr = re.sub(r"\bgetPost\s*", "$_POST", expr)
    expr = re.sub(r"\bsanitize\((.*?)\)", r"htmlspecialchars(\1)", expr)
    expr = re.sub(
        r'\bconnectDb\((["\'].*?["\'])\)', r"new PDO('sqlite:\1')", expr
    )  # simplified fallback
    expr = re.sub(
        r'\bselect\((\w+),\s*(["\'].*?["\']),\s*(.*?)\)',
        r"\1->query('SELECT * FROM ' . \2 . ' WHERE ' . \3)->fetchAll()",
        expr,
    )
    expr = re.sub(
        r"\binsert\((\w+),\s*(\w+),\s*(.*?)\)",
        r"// insert logic for \1, \2, \3",
        expr,
    )
    expr = re.sub(r"\bgetPingTelegram\b", "pingTelegram", expr)
    expr = re.sub(r"\bredirect\s+(.+)", r"header('Location: ' . \1); exit;", expr)
    expr = re.sub(r"\bsetSession\s+(.+?)\s+(.+)", r"$_SESSION[\1] = \2", expr)
    expr = re.sub(r"\bgetSession\s+(.+)", r"$_SESSION[\1]", expr)
    expr = re.sub(
        r'\bsetLocalstorage\s+(.+?)\s+(.+)',
        r"setcookie(\1, \2, time() + (86400 * 30), '/')",
        expr,
    )
    expr = re.sub(r"\getLocalstorage\s+(.+)", r"$_COOKIE[\1]", expr)
    expr = re.sub(r"\bdbQuery\((.*?)\)", r"$db->query(\1)", expr)
    expr = re.sub(r"\bexit\((.*?)\)", r"echo json_encode(\1); exit;", expr)

    # Add $ to variables
    # Basic word token replacement if not part of string or function name
    # Clean up standard variable names
    words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", expr)
    php_keywords = [
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
    ]
    for w in sorted(set(words), key=len, reverse=True):
        if w not in php_keywords and not expr.endswith(f"({w}"):
            # Check if it's not already prefixed with $
            expr = re.sub(rf"\b{w}\b", f"${w}", expr)

    return expr


def compile_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find blocks between #? and ?#
    parts = re.split(r"(#\?|\?#)", content)
    output = []
    in_code_block = False

    for part in parts:
        if part == "#?":
            in_code_block = True
            output.append("<?php\n")
            continue
        elif part == "?#":
            in_code_block = False
            output.append("?>")
            continue

        if in_code_block:
            lines = part.splitlines()
            for line in lines:
                translated = translate_line(line)
                output.append(translated)
        else:
            output.append(part)

    php_content = "".join(output)
    # Fix potential double closing braces or block closures if needed, or write out
    out_path = re.sub(r"\.pyh$", ".php", filepath, flags=re.IGNORECASE)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(php_content)
    print(f"Compiled: {filepath} -> {out_path}")


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".pyh"):
                compile_file(os.path.join(root, file))


if __name__ == "__main__":
    main()
