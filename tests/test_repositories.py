"""
Unit tests for the Database Repository Layer.
"""
import sys
import asyncio
from pathlib import Path
import uuid

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

from database.connection import async_session_factory
from repositories.port_repository import list_ports, get_port_by_code, upsert_port, port_exists
from repositories.assumption_repository import get_assumptions, get_assumption_value, get_assumptions_as_dict, update_assumption
from repositories.berth_repository import list_berths


async def async_test_port_repository():
    async with async_session_factory() as db:
        # 1. Upsert a test port
        port_code = f"T_{uuid.uuid4().hex[:6].upper()}"
        port_name = f"Test Port {port_code}"
        
        port = await upsert_port(db, port_code, port_name, country="TestLand", timezone="UTC")
        assert port is not None
        assert port.port_code == port_code
        assert port.port_name == port_name
        
        # 2. Check if exists
        exists = await port_exists(db, port_code)
        assert exists is True
        
        # 3. Retrieve by code
        retrieved = await get_port_by_code(db, port_code)
        assert retrieved is not None
        assert retrieved.port_name == port_name
        
        # 4. List ports and verify our test port is in the list
        all_ports = await list_ports(db)
        codes = [p.port_code for p in all_ports]
        assert port_code in codes

        # Clean up test port
        await db.delete(retrieved)
        await db.commit()


async def async_test_assumption_repository():
    async with async_session_factory() as db:
        # Create a temp port for testing assumptions
        port_code = f"A_{uuid.uuid4().hex[:6].upper()}"
        port = await upsert_port(db, port_code, "Temp Port", country="TestLand", timezone="UTC")
        
        # Add a temp assumption
        from database.baos_models import BaosAssumptionConfig
        assumption_id = uuid.uuid4()
        asm = BaosAssumptionConfig(
            assumption_id=assumption_id,
            port_id=port.port_id,
            assumption_key="test_rate",
            assumption_value=123.45,
            is_active=True
        )
        db.add(asm)
        await db.flush()

        # 1. Get value
        val = await get_assumption_value(db, port_code, "test_rate")
        assert val == 123.45

        # 2. Get as dict
        asm_dict = await get_assumptions_as_dict(db, port_code)
        assert asm_dict.get("test_rate") == 123.45

        # 3. Update assumption
        updated = await update_assumption(db, assumption_id, value=999.99, description="Updated description")
        assert updated is not None
        assert updated.assumption_value == 999.99
        assert updated.description == "Updated description"

        # Cleanup
        await db.delete(updated)
        await db.delete(port)
        await db.commit()


async def async_test_berth_repository():
    async with async_session_factory() as db:
        # Let's verify we can call list_berths for the seeded Chennai Port (INMAA)
        berths = await list_berths(db, "INMAA")
        assert isinstance(berths, list)
        # We seeded 24 berths, so it should be > 0
        assert len(berths) > 0


def run_all_async():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("  Running: Port Repository Tests")
        loop.run_until_complete(async_test_port_repository())
        print("  PASS: Port Repository")

        print("  Running: Assumption Repository Tests")
        loop.run_until_complete(async_test_assumption_repository())
        print("  PASS: Assumption Repository")

        print("  Running: Berth Repository Tests")
        loop.run_until_complete(async_test_berth_repository())
        print("  PASS: Berth Repository")
    finally:
        loop.close()


if __name__ == "__main__":
    try:
        run_all_async()
        print("\nAll Repository Tests Passed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\nRepository Tests Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
