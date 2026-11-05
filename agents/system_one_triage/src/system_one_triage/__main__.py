"""`python -m system_one_triage "ticket text"` prints the routing decision as JSON."""

import asyncio
import json
import sys

from system_one_triage.client import build_client
from system_one_triage.settings import get_settings
from system_one_triage.triage import triage


async def main(text: str) -> None:
    decision = await triage(text, build_client(get_settings()))
    print(json.dumps(decision.as_dict(), indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -m system_one_triage "ticket text"')
    asyncio.run(main(sys.argv[1]))
