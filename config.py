import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CREATOR_ID: int = int(os.getenv("CREATOR_ID", "0"))
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:SmmnmETgtbVscQeHfOSkSUZrqqtgaVel@postgres.railway.internal:5432/railway")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "crm.db") # Kept for FSM or legacy if needed

# FSM holatlarini saqlash joyi (Railway da /data/fsm.db, localda crm_fsm.db)
FSM_STORAGE_PATH: str = os.getenv("FSM_STORAGE_PATH", "crm_fsm.db")

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
