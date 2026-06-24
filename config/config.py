import json
import os
import copy
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "settings.json"


class Config:
    """Менеджер конфигурации бота. Загружает/сохраняет settings.json."""

    _instance = None
    _data: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Загрузить конфигурацию из файла."""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except FileNotFoundError:
            self._data = {}
        except json.JSONDecodeError:
            self._data = {}

    def save(self):
        """Сохранить текущую конфигурацию в файл."""
        os.makedirs(CONFIG_PATH.parent, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)

    def reload(self):
        """Перезагрузить конфигурацию из файла."""
        self._load()

    def get(self, key: str, default=None):
        """
        Получить значение по ключу с поддержкой вложенных ключей через точку.
        Пример: config.get("welcome.channel_id")
        """
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value):
        """
        Установить значение по ключу с поддержкой вложенных ключей через точку.
        Пример: config.set("welcome.channel_id", 123456)
        Автоматически сохраняет в файл.
        """
        keys = key.split(".")
        data = self._data
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self.save()

    def get_embed_color(self) -> int:
        """Получить цвет embed'ов в формате int."""
        color_hex = self.get("embed_color", "7B2FBE")
        return int(color_hex, 16)

    def get_family_name(self) -> str:
        """Получить название семьи."""
        return self.get("family_name", "MAJESTIK")

    @property
    def data(self) -> dict:
        """Получить копию всех данных конфигурации."""
        return copy.deepcopy(self._data)

    def get_section(self, section: str) -> dict:
        """Получить целую секцию конфигурации."""
        return copy.deepcopy(self._data.get(section, {}))
