from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from utils.messages import (
    BTN_FIND_MECH, BTN_NEW_ORDER, BTN_MY_ORDERS, BTN_CANCEL, BTN_SKIP, BTN_BACK
)


def client_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=BTN_FIND_MECH)
    kb.button(text=BTN_NEW_ORDER)
    kb.button(text=BTN_MY_ORDERS)
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=BTN_CANCEL)
    return kb.as_markup(resize_keyboard=True)


def skip_cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=BTN_SKIP)
    kb.button(text=BTN_CANCEL)
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def location_cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📍 Joylashuvni yuborish", request_location=True)
    kb.button(text=BTN_CANCEL)
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
