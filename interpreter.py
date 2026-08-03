import os
import re
import sys


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

    if not stripped or stripped.startswith("#"):
        return line, False, False  # line, opens_block, is_else

    # 1. include config.pyh -> include_once 'config.php';
    if stripped.startswith("include "):
        mod = stripped[len("include ") :].strip()
        mod_php = re.sub(r"\.pyh$", ".php", mod, flags=re.IGNORECASE)
        return f"{indent}include_once '{mod_php}';\n", False, False

    # 2. Debug_on -> PHP error settings
    if stripped.lower() == "debug_on":
        code = (
            f"{indent}ini_set('display_errors', '1');\n"
            f"{indent}ini_set('display_startup_errors', '1');\n"
            f"{indent}error_reporting(E_ALL);\n"
        )
        return code, False, False

    # 3. foreach dbData as row:
    match = re.match(r"^foreach\s+(.+?)\s+as\s+(.+?):$", stripped)
    if match:
        arr, var = match.groups()
        return (
            f"{indent}foreach ({translate_expr(arr)} as ${var}) {{\n",
            True,
            False,
        )

    # 4. if condition:
    match = re.match(r"^if\s+(.+?):$", stripped)
    if match:
        cond = match.group(1)
        return f"{indent}if ({translate_expr(cond)}) {{\n", True, False

    # 5. else -> } else {
    if stripped == "else":
        return f"{indent}}} else {{\n", True, True

    # 6. loopCsv "file.csv" as city:
    match = re.match(r'^loopCsv\s+(["\'].+?["\'])\s+as\s+(.+?):$', stripped)
    if match:
        csv_file, var = match.groups()
        return (
            f"{indent}foreach (array_map('str_getcsv', file({csv_file})) as ${var}) {{\n",
            True,
            False,
        )

    # 7. break
    if stripped == "break":
        return f"{indent}break;\n", False, False

    # 8. Handle space-separated function calls loaded from lib/spaceFunctions.txt
    space_funcs = load_space_functions()
    first_word = stripped.split()[0] if stripped else ""
    if first_word in space_funcs:
        args_payload = stripped[len(first_word) :].strip()
        translated_args = translate_expr(args_payload)
        return f"{indent}{first_word}({translated_args});\n", False, False

    # 9. General Function mappings & assignments
    translated = translate_expr(stripped)
    return f"{indent}{translated};\n", False, False


def translate_expr(expr):
    # Handle associative array shorthand: name -> "james" => 'name' => 'james'
    expr = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*", r"'\1' => ", expr)

    # Map print -> echo
    expr = re.sub(r"\bprint\s+", "echo ", expr)

    # Built-in shorthand translations
    expr = re.sub(r"\bgetPost\s*", "$_POST", expr)
    expr = re.sub(r"\bgetUrl\s*", "$_SERVER['REQUEST_URI']", expr)
    expr = re.sub(r"\bsanitize\((.*?)\)", r"htmlspecialchars(\1)", expr)
    expr = re.sub(
        r'\bconnectDb\((["\'].*?["\'])\)', r"new PDO('sqlite:\1')", expr
    )
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
    expr = re.sub(r"\bredirect\s+(.+)", r"header('Location: ' . \1); exit;", expr)
    expr = re.sub(r"\bsetSession\s+(.+?)\s+(.+)", r"$_SESSION[\1] = \2", expr)
    expr = re.sub(r"\bgetSession\s+(.+)", r"$_SESSION[\1]", expr)
    expr = re.sub(
        r'\bsetLocalstorage\s+(.+?)\s+(.+)',
        r"setcookie(\1, \2, time() + (86400 * 30), '/')",
        expr,
    )
    expr = re.sub(r"\bgetLocalstorage\s+(.+)", r"$_COOKIE[\1]", expr)
    expr = re.sub(r"\bdbQuery\((.*?)\)", r"$db->query(\1)", expr)
    expr = re.sub(r"\bexit\((.*?)\)", r"echo json_encode(\1); exit;", expr)

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

            def add_dollar(match):
                word = match.group(0)
                if word in php_keywords or word.startswith("$"):
                    return word
                return f"${word}"

            processed = re.sub(
                r"\b[a-zA-Z_][a-zA-Z0-9_]*\b(?!\s*\()", add_dollar, part
            )
            new_parts.append(processed)

    return "".join(new_parts)


def compile_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

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
            # Indentation block tracking stack: stores (indent_string, opens_else_flag)
            block_stack = []

            for line in lines:
                indent_match = re.match(r"^(\s*)", line)
                current_indent = len(indent_match.group(1)) if indent_match else 0

                # Close blocks whose indentation is greater than or equal to current line, unless it's an 'else'
                stripped_check = line.strip()
                is_current_else = stripped_check == "else"

                while block_stack and block_stack[-1]["indent"] >= current_indent:
                    top = block_stack.pop()
                    # If the block we are popping was an else, we need to close the parent 'if' block too
                    closing_indent = " " * top["indent"]
                    output.append(f"{closing_indent}}}\n")
                    if top["was_else"] and block_stack:
                        # Pop the matching initial 'if' block container if necessary
                        pass

                translated_line, opens_block, is_else = translate_line(line)
                output.append(translated_line)

                if opens_block:
                    if is_else:
                        # Pop the previous 'if' block tracker so we don't double close prematurely
                        if block_stack:
                            block_stack.pop()
                    block_stack.append(
                        {
                            "indent": current_indent,
                            "was_else": is_else,
                        }
                    )

            # Close any remaining unclosed blocks at the end of the script block
            while block_stack:
                top = block_stack.pop()
                closing_indent = " " * top["indent"]
                output.append(f"{closing_indent}}}\n")
        else:
            output.append(part)

    php_content = "".join(output)
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