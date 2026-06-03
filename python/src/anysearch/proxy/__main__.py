"""Run the anysearch FastAPI proxy with ``python -m anysearch.proxy``."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("ANYSEARCH_PROXY_HOST", "0.0.0.0")
    port = int(os.environ.get("ANYSEARCH_PROXY_PORT", "4000"))
    uvicorn.run("anysearch.proxy.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
