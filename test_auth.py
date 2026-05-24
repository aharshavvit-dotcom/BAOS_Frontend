import sys
import asyncio
sys.path.append('d:/ML_berth_optimizer_app/berth_optimization_poc_app/backend')
from database.connection import async_session_factory
from services.auth_service import authenticate_user

async def main():
    try:
        async with async_session_factory() as db:
            user = await authenticate_user(db, 'admin@baos.ai', 'admin123')
            print('SUCCESS:', user)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
