#!/usr/bin/env python3
"""
Script to compile translation files (.po to .mo) for internationalization.
Run this after updating .po translation files.
"""

import sys
from pathlib import Path
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

LOCALES_DIR = project_root / "backend" / "app" / "locales"


def compile_translations():
    """Compile all .po files to .mo files."""
    print("Compiling translation files...")

    if not LOCALES_DIR.exists():
        print(f"Error: Locales directory not found at {LOCALES_DIR}")
        sys.exit(1)

    compiled_count = 0
    errors = []

    # Find all .po files
    po_files = list(LOCALES_DIR.rglob("*.po"))

    if not po_files:
        print(f"No .po files found in {LOCALES_DIR}")
        return

    for po_file in po_files:
        try:
            # Create corresponding .mo file path
            mo_file = po_file.with_suffix(".mo")

            print(
                f"Compiling: {po_file.relative_to(project_root)} -> {mo_file.relative_to(project_root)}"
            )

            # Read .po file
            with open(po_file, "rb") as f:
                catalog = read_po(f, locale=po_file.parent.parent.name)

            # Write .mo file
            with open(mo_file, "wb") as f:
                write_mo(f, catalog)

            compiled_count += 1

        except Exception as e:
            error_msg = f"Error compiling {po_file}: {e}"
            errors.append(error_msg)
            print(f"✗ {error_msg}")

    print(f"\n{'=' * 60}")
    print(f"✓ Successfully compiled {compiled_count} translation file(s)")

    if errors:
        print(f"✗ {len(errors)} error(s) occurred:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("All translations compiled successfully!")


if __name__ == "__main__":
    compile_translations()
