from aiogram.fsm.state import State, StatesGroup

# --- MIJOZ VA BUYURTMA (ORDER) Kiritish jarayoni ---
class NewOrder(StatesGroup):
    client_name = State()
    client_phone = State()
    car_model = State()
    car_number = State()
    mileage = State()
    problem = State()
    car_condition = State()
    price = State()
    cost = State()
    warranty = State()
    next_service_time = State()
    security_code = State()

# --- QIDIRUV VA TO'LOV ---
class SearchState(StatesGroup):
    query = State()

class PartialPayment(StatesGroup):
    amount = State()

class PayDebtState(StatesGroup):
    amount = State()

# --- USTA SOZLAMALARI ---
class SettingsState(StatesGroup):
    workshop_name = State()
    address = State()
    phone = State()
    warranty_days = State()
    reminder_time = State()

# --- ADMIN PANEL ---
class AddMaster(StatesGroup):
    waiting_for_id = State()
    confirming = State()

class SearchMaster(StatesGroup):
    waiting_for_query = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

# --- SHOGIRD/XODIM QO'SHISH ---
class AddWorker(StatesGroup):
    waiting_for_id = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_branch_name = State()

