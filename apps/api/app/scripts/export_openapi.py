"""Write the API's OpenAPI schema to a file (used by the web app's `pnpm gen:api`).

Usage: python -m app.scripts.export_openapi <output.json>
"""

import json
import sys
from pathlib import Path

from app.main import create_app


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.export_openapi <output.json>")
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
