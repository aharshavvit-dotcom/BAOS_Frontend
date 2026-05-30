import sys
import asyncio
import os
import uvicorn

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    port = int(os.getenv("BACKEND_PORT", "8001"))
    config = uvicorn.Config("main:app", host="127.0.0.1", port=port, reload=False)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
