import os
import re
from pathlib import Path
from collections import defaultdict

IGNORED = set()


def normalize_name(name):
    # Strip prefix if already present (underscore or space)
    name_no_prefix = re.sub(r"^\d{2}[ _]", "", name)
    # Normalize: replace non-alphanumeric and non-dot/underscore with underscore, lowercase
    name_clean = re.sub(r"[^a-zA-Z0-9_.]+", "_", name_no_prefix).lower()
    return name_clean


def get_next_index(used_indices):
    # Find lowest available 2-digit index
    for i in range(1000):
        idx = f"{i:02}"
        if idx not in used_indices:
            return idx
    raise Exception("Ran out of prefix numbers")


def standardize_directory(root, include_hidden=False, ignore_dirs=None):
    table = []
    root = Path(root)
    ignore_dirs = set(ignore_dirs or [])

    for current_dir, dirs, files in os.walk(root):
        rel_dir = Path(current_dir).relative_to(root)
        # Skip ignored dirs
        if any(part in ignore_dirs for part in rel_dir.parts):
            for d in dirs:
                if d in ignore_dirs:
                    table.append(["Folder", str(Path(current_dir)/d), str(Path(current_dir)/d), "Ignored"])
            continue

        current_path = Path(current_dir)
        used_prefixes = set()
        folder_counter = defaultdict(list)
        file_counter = defaultdict(list)

        entries = [(True, d) for d in dirs] + [(False, f) for f in files]
        # First pass: collect existing prefixes
        for is_dir, name in entries:
            if not include_hidden and name.startswith('.'):
                table.append(["Hidden", name, name, "Skipped (hidden)"])
                continue
            prefix_match = re.match(r"^(\d{2})[ _](.+)$", name)
            if prefix_match:
                # If normalized matches, treat as compliant
                base = prefix_match.group(2)
                if normalize_name(base) == normalize_name(name[len(prefix_match.group(0)):]):
                    used_prefixes.add(prefix_match.group(1))
                    table.append(["Folder" if is_dir else "File", str(current_path/name), str(current_path/name), "Unchanged"])
        # Second pass: propose renames
        for is_dir, name in entries:
            if not include_hidden and name.startswith('.'):
                continue
            path = current_path / name
            prefix_match = re.match(r"^(\d{2})[ _](.+)$", name)
            if prefix_match and normalize_name(prefix_match.group(2)) == normalize_name(name[len(prefix_match.group(1))+1:]):
                continue  # already compliant
            # Propose new name
            normalized = normalize_name(name)
            new_prefix = get_next_index(used_prefixes)
            used_prefixes.add(new_prefix)
            new_name = f"{new_prefix}_{normalized}"
            # Resolve conflicts
            counter = folder_counter if (path.is_dir()) else file_counter
            idx = 1
            while (current_path / new_name).exists() or new_name in counter[new_prefix]:
                new_name = f"{new_prefix}_{normalized}_{idx}"
                idx += 1
            counter[new_prefix].append(new_name)
            new_path = current_path / new_name
            table.append(["Folder" if path.is_dir() else "File", str(path), str(new_path), "Renamed"])

    return table


def save_table(table, out_path):
    lines = ["| Type | Original Name | New Name | Action |",
             "|------|----------------|----------|--------|"]
    for row in table:
        lines.append("| " + " | ".join(row) + " |")
    Path(out_path).write_text("\n".join(lines))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dry-run: Standardize file/folder names recursively.")
    parser.add_argument("--apply", action="store_true", help="Apply changes instead of just showing")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files/folders")
    parser.add_argument("--ignore", action="append", help="Subdirectory name to ignore", default=[])
    args = parser.parse_args()

    cwd = os.getcwd()
    result_table = standardize_directory(cwd, include_hidden=args.include_hidden, ignore_dirs=args.ignore)
    save_table(result_table, Path(cwd) / "standardization_preview.md")

    for row in result_table:
        print("\t".join(row))

    if args.apply:
        # Apply renames
        for row in result_table:
            if row[3] == "Renamed":
                old, new = Path(row[1]), Path(row[2])
                old.rename(new)
        print("\nAll changes applied.")


if __name__ == "__main__":
    main()
