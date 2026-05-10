import asyncio
import sys
import os

# Add the project root to sys.path to import factory_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from factory_agent.persistence.database import engine

async def migrate():
    print(f"Connecting to database via {engine.url.drivername}...")
    
    async with engine.begin() as conn:
        # Check if we are on MySQL or SQLite to handle 'IF NOT EXISTS' if possible
        # MySQL doesn't support 'ADD COLUMN IF NOT EXISTS' easily without a procedure
        # So we use a try-except block for each column.
        
        print("Attempting to add 'sources' column to 'plans' table...")
        try:
            # Using standard SQL for compatibility
            await conn.execute(text("ALTER TABLE plans ADD COLUMN sources JSON"))
            print("Successfully added 'sources' column.")
        except Exception as e:
            err_msg = str(e).lower()
            if "duplicate column" in err_msg or "already exists" in err_msg:
                print("Column 'sources' already exists. Skipping.")
            else:
                print(f"Error adding 'sources': {e}")

        print("Attempting to add 'safety_content' column to 'plans' table...")
        try:
            await conn.execute(text("ALTER TABLE plans ADD COLUMN safety_content TEXT"))
            print("Successfully added 'safety_content' column.")
        except Exception as e:
            err_msg = str(e).lower()
            if "duplicate column" in err_msg or "already exists" in err_msg:
                print("Column 'safety_content' already exists. Skipping.")
            else:
                print(f"Error adding 'safety_content': {e}")

    print("Migration process completed.")

if __name__ == "__main__":
    asyncio.run(migrate())
