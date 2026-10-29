"""Thin island-style laptop keyboard; no feet or perspective."""
from .keyboard import build as build_keyboard


def build():
    return build_keyboard('laptop')
