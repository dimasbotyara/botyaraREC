"""
Модуль горячих клавиш
"""

import threading
from pynput import keyboard

class HotkeyManager:
    """Менеджер горячих клавиш"""
    
    def __init__(self):
        self.hotkeys = {}
        self.listener = None
        
    def register(self, key, callback):
        """Регистрация горячей клавиши"""
        self.hotkeys[key.lower()] = callback
        
    def on_press(self, key):
        """Обработка нажатия клавиши"""
        try:
            # Получаем имя клавиши
            key_name = None
            if hasattr(key, 'name'):
                key_name = key.name.lower()
            elif hasattr(key, 'char'):
                key_name = key.char.lower() if key.char else None
                
            # Вызываем callback
            if key_name and key_name in self.hotkeys:
                self.hotkeys[key_name]()
        except Exception as e:
            print(f"Ошибка обработки клавиши: {e}")
            
    def start(self):
        """Запуск прослушивания"""
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        
    def stop(self):
        """Остановка прослушивания"""
        if self.listener:
            self.listener.stop()
