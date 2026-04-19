# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio


def main() -> None:
    from .server import serve
    asyncio.run(serve())


if __name__ == "__main__":
    main()
