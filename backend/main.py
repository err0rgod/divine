import asyncio
from StreamStt import main

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nProgram exited cleanly.")