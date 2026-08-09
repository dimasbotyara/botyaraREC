#!/usr/bin/env python3
"""
botyaraREC - Screen Recorder для слабого железа
Записывает RAW видео/аудио, потом кодирует в MP4
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
from pathlib import Path
from capture import VideoCapture, AudioCapture
from encoder import VideoEncoder
from hotkeys import HotkeyManager
import json
from datetime import datetime
import time
import subprocess

class botyaraREC:
    def __init__(self, root):
        self.root = root
        self.root.title("botyaraREC")
        self.root.geometry("500x480")
        self.root.resizable(False, False)

        # Темная тема
        self.setup_dark_theme()

        # Переменные состояния
        self.recording = False
        self.paused = False
        self.mic_enabled = True
        self.system_audio_enabled = True
        self.record_time = 0
        self.timer_running = False
        self.encoding = False

        # Пути
        self.script_dir = Path(__file__).parent
        self.temp_dir = self.script_dir / "temp_recording"
        self.output_path = str(Path.home() / "Videos" / f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

        # Аудио источники
        self.audio_sources = []
        self.selected_mic_source = None

        # Захватчики
        self.video_capture = None
        self.audio_capture = None
        self.encoder = None
        self.hotkey_manager = None

        # Загружаем список микрофонов
        self.load_audio_sources()

        # Создаем GUI
        self.create_widgets()

        # Горячие клавиши
        self.setup_hotkeys()

        # Обработка закрытия
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_audio_sources(self):
        """Загрузка списка аудио источников"""
        try:
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sources'],
                capture_output=True, text=True, check=True, timeout=3
            )

            lines = result.stdout.strip().split('\n')
            self.audio_sources = []

            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        source_name = parts[1].strip()
                        # Пропускаем мониторы (кроме easyeffects)
                        if '.monitor' in source_name and 'easyeffects' not in source_name:
                            continue
                        self.audio_sources.append(source_name)

            # Приоритет: easyeffects_source > default
            self.selected_mic_source = None
            for source in self.audio_sources:
                if 'easyeffects_source' in source:
                    self.selected_mic_source = source
                    break

            # Если не нашли easyeffects, берём дефолтный
            if not self.selected_mic_source:
                try:
                    result = subprocess.run(
                        ['pactl', 'get-default-source'],
                        capture_output=True, text=True, check=True, timeout=2
                    )
                    self.selected_mic_source = result.stdout.strip()
                except:
                    self.selected_mic_source = 'default'

        except Exception as e:
            print(f"Ошибка загрузки источников: {e}")
            self.audio_sources = ['default']
            self.selected_mic_source = 'default'

    def setup_dark_theme(self):
        """Настройка темной темы"""
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        button_bg = "#3c3c3c"
        button_active = "#4c4c4c"

        self.root.configure(bg=bg_color)

        style = ttk.Style()
        style.theme_use('clam')

        style.configure(".", background=bg_color, foreground=fg_color,
                       fieldbackground=bg_color, borderwidth=0)
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TButton", background=button_bg, foreground=fg_color,
                       borderwidth=1, focuscolor='none', padding=6)
        style.map("TButton", background=[('active', button_active)])

        # Стиль для Combobox
        style.configure("TCombobox",
                       fieldbackground=button_bg,
                       background=button_bg,
                       foreground=fg_color,
                       arrowcolor=fg_color,
                       borderwidth=1,
                       relief=tk.FLAT)
        style.map('TCombobox',
                 fieldbackground=[('readonly', button_bg)],
                 selectbackground=[('readonly', button_bg)],
                 selectforeground=[('readonly', fg_color)])

        # Кастомные цвета для кнопок
        self.colors = {
            'bg': bg_color,
            'fg': fg_color,
            'button': button_bg,
            'button_active': button_active,
            'rec': '#dc3545',
            'rec_active': '#c82333',
            'pause': '#ffc107',
            'pause_active': '#e0a800',
            'stop': '#6c757d',
            'stop_active': '#5a6268'
        }

    def create_widgets(self):
        """Создание интерфейса"""
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title = ttk.Label(main_frame, text="botyaraREC",
                         font=("Arial", 24, "bold"))
        title.pack(pady=(0, 20))

        # Таймер
        self.timer_label = tk.Label(main_frame, text="00:00:00",
                                    font=("Courier", 32, "bold"),
                                    bg=self.colors['bg'], fg=self.colors['fg'])
        self.timer_label.pack(pady=10)

        # Статус
        self.status_label = ttk.Label(main_frame, text="Готов к записи",
                                     font=("Arial", 11))
        self.status_label.pack(pady=5)

        # Фрейм для кнопок записи
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(pady=20)

        # Кнопка записи/стоп
        self.rec_button = tk.Button(controls_frame, text="● REC",
                                    font=("Arial", 14, "bold"),
                                    bg=self.colors['rec'],
                                    fg="white",
                                    activebackground=self.colors['rec_active'],
                                    activeforeground="white",
                                    relief=tk.FLAT,
                                    padx=30, pady=10,
                                    cursor="hand2",
                                    command=self.toggle_recording_threaded)
        self.rec_button.pack(side=tk.LEFT, padx=5)

        # Кнопка паузы
        self.pause_button = tk.Button(controls_frame, text="⏸ PAUSE",
                                      font=("Arial", 12),
                                      bg=self.colors['pause'],
                                      fg="black",
                                      activebackground=self.colors['pause_active'],
                                      activeforeground="black",
                                      relief=tk.FLAT,
                                      padx=20, pady=10,
                                      cursor="hand2",
                                      state=tk.DISABLED,
                                      command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        # Фрейм для настроек аудио
        audio_frame = ttk.Frame(main_frame)
        audio_frame.pack(pady=15, fill=tk.X)

        # Чекбоксы
        self.mic_var = tk.BooleanVar(value=True)
        self.system_var = tk.BooleanVar(value=True)

        mic_check = ttk.Checkbutton(audio_frame, text="🎤 Микрофон",
                                   variable=self.mic_var,
                                   command=self.toggle_mic)
        mic_check.pack(anchor=tk.W, pady=3)

        # Выбор микрофона
        mic_select_frame = ttk.Frame(audio_frame)
        mic_select_frame.pack(fill=tk.X, pady=(0, 8), padx=(25, 0))

        ttk.Label(mic_select_frame, text="Источник:",
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))

        # Красивые имена для источников
        self.mic_display_names = {}
        self.mic_actual_names = {}

        for source in self.audio_sources:
            if 'easyeffects_source' in source:
                display = "EasyEffects (рекомендуется) 🎧"
            elif 'easyeffects' in source and 'monitor' in source:
                display = "EasyEffects Monitor"
            elif 'analog-stereo' in source and 'input' in source:
                display = "Встроенный микрофон"
            elif 'monitor' in source:
                display = f"Monitor: {source.split('.')[0]}"
            else:
                display = source

            self.mic_display_names[source] = display
            self.mic_actual_names[display] = source

        display_list = [self.mic_display_names[s] for s in self.audio_sources]

        self.mic_combo_var = tk.StringVar(value=self.mic_display_names.get(self.selected_mic_source, 'default'))
        self.mic_combo = ttk.Combobox(mic_select_frame,
                                     textvariable=self.mic_combo_var,
                                     values=display_list,
                                     state='readonly',
                                     width=30,
                                     font=("Arial", 9))
        self.mic_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.mic_combo.bind('<<ComboboxSelected>>', self.on_mic_selected)

        system_check = ttk.Checkbutton(audio_frame, text="🔊 Звуки системы",
                                      variable=self.system_var,
                                      command=self.toggle_system_audio)
        system_check.pack(anchor=tk.W, pady=3)

        # Выбор пути сохранения
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(pady=10, fill=tk.X)

        ttk.Label(path_frame, text="Сохранить в:", font=("Arial", 9)).pack(anchor=tk.W)

        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill=tk.X, pady=5)

        self.path_var = tk.StringVar(value=self.output_path)
        path_entry = ttk.Entry(path_entry_frame, textvariable=self.path_var,
                              font=("Arial", 9))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(path_entry_frame, text="Обзор...",
                               command=self.browse_output)
        browse_btn.pack(side=tk.LEFT)

        # Горячие клавиши
        hotkeys_frame = ttk.Frame(main_frame)
        hotkeys_frame.pack(pady=10)

        ttk.Label(hotkeys_frame, text="Горячие клавиши: F8 - Старт/Стоп | F9 - Пауза | F10 - Мут микро",
                 font=("Arial", 8), foreground="#888888").pack()

    def on_mic_selected(self, event=None):
        """Обработка выбора микрофона"""
        display_name = self.mic_combo_var.get()
        self.selected_mic_source = self.mic_actual_names.get(display_name, 'default')
        print(f"Выбран микрофон: {self.selected_mic_source}")

    def setup_hotkeys(self):
        """Настройка горячих клавиш"""
        self.hotkey_manager = HotkeyManager()
        self.hotkey_manager.register('f8', self.toggle_recording_threaded)
        self.hotkey_manager.register('f9', self.toggle_pause)
        self.hotkey_manager.register('f10', self.toggle_mic_hotkey)
        self.hotkey_manager.start()

    def toggle_recording_threaded(self):
        """Старт/стоп записи в отдельном потоке"""
        if not self.recording and not self.encoding:
            threading.Thread(target=self.start_recording, daemon=True).start()
        elif self.recording:
            threading.Thread(target=self.stop_recording, daemon=True).start()

    def start_recording(self):
        """Начать запись"""
        try:
            # Создаем временную директорию
            self.temp_dir.mkdir(exist_ok=True)

            # Обновляем путь вывода
            self.output_path = self.path_var.get()

            # Создаем захватчики
            self.video_capture = VideoCapture(
                resolution=(1440, 900),
                fps=30,
                output_dir=self.temp_dir
            )

            self.audio_capture = AudioCapture(
                output_dir=self.temp_dir,
                record_mic=self.mic_var.get(),
                record_system=self.system_var.get(),
                mic_source=self.selected_mic_source  # Передаём выбранный источник
            )

            # Запускаем захват
            self.video_capture.start()
            self.audio_capture.start()

            # Обновляем состояние
            self.recording = True
            self.paused = False
            self.record_time = 0

            # Обновляем GUI (через root.after для безопасности)
            self.root.after(0, self._update_gui_recording)

            # Запускаем таймер
            self.timer_running = True
            self.root.after(0, self.update_timer)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось начать запись:\n{str(e)}"))

    def _update_gui_recording(self):
        """Обновление GUI при старте записи"""
        self.rec_button.config(text="⬛ STOP", bg=self.colors['stop'],
                              activebackground=self.colors['stop_active'])
        self.pause_button.config(state=tk.NORMAL)
        self.status_label.config(text="● Идет запись...")
        # Блокируем выбор микрофона во время записи
        self.mic_combo.config(state=tk.DISABLED)

    def stop_recording(self):
        """Остановить запись"""
        if not self.recording:
            return

        # Обновляем статус
        self.root.after(0, lambda: self.status_label.config(text="Останавливаем запись..."))

        # Останавливаем захват
        if self.video_capture:
            self.video_capture.stop()
        if self.audio_capture:
            self.audio_capture.stop()

        # Даём время на корректное закрытие файлов
        time.sleep(1)

        # Обновляем GUI
        self.recording = False
        self.timer_running = False
        self.root.after(0, lambda: self.rec_button.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.pause_button.config(state=tk.DISABLED))

        # Запускаем кодирование
        self.encode_video()

    def encode_video(self):
        """Кодирование видео (уже в отдельном потоке)"""
        try:
            self.encoding = True
            self.root.after(0, lambda: self.status_label.config(text="⚙️ Кодирование видео (это займёт время, комп будет тормозить)..."))

            encoder = VideoEncoder(
                temp_dir=self.temp_dir,
                output_path=self.output_path,
                fps=30,
                resolution=(1440, 900),
                apply_denoise_mic=False  # Шумодав отключён, т.к. используется EasyEffects
            )

            encoder.encode()

            # Очистка временных файлов
            self.root.after(0, lambda: self.status_label.config(text="🧹 Очистка временных файлов..."))
            encoder.cleanup()

            # Готово
            self.encoding = False
            self.root.after(0, self.encoding_complete)

        except Exception as e:
            self.encoding = False
            self.root.after(0, lambda: messagebox.showerror("Ошибка кодирования", str(e)))
            self.root.after(0, self.reset_gui)

    def encoding_complete(self):
        """Кодирование завершено"""
        messagebox.showinfo("Готово!", f"Видео сохранено:\n{self.output_path}")
        self.reset_gui()

    def reset_gui(self):
        """Сброс GUI"""
        self.rec_button.config(text="● REC", bg=self.colors['rec'],
                              activebackground=self.colors['rec_active'],
                              state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.mic_combo.config(state='readonly')  # Разблокируем выбор микрофона
        self.status_label.config(text="Готов к записи")
        self.timer_label.config(text="00:00:00")

        # Генерируем новое имя файла
        self.output_path = str(Path.home() / "Videos" / f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        self.path_var.set(self.output_path)

    def toggle_pause(self):
        """Пауза/продолжить"""
        if not self.recording:
            return

        self.paused = not self.paused

        if self.paused:
            if self.video_capture:
                self.video_capture.pause()
            if self.audio_capture:
                self.audio_capture.pause()
            self.pause_button.config(text="▶ RESUME")
            self.status_label.config(text="⏸ Пауза")
        else:
            if self.video_capture:
                self.video_capture.resume()
            if self.audio_capture:
                self.audio_capture.resume()
            self.pause_button.config(text="⏸ PAUSE")
            self.status_label.config(text="● Идет запись...")

    def toggle_mic(self):
        """Переключить микрофон"""
        self.mic_enabled = self.mic_var.get()
        if self.audio_capture and self.recording:
            self.audio_capture.toggle_mic(self.mic_enabled)

    def toggle_mic_hotkey(self):
        """Переключить микрофон через горячую клавишу"""
        self.mic_var.set(not self.mic_var.get())
        self.toggle_mic()

    def toggle_system_audio(self):
        """Переключить системный звук"""
        self.system_audio_enabled = self.system_var.get()
        if self.audio_capture and self.recording:
            self.audio_capture.toggle_system(self.system_audio_enabled)

    def browse_output(self):
        """Выбрать путь сохранения"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")],
            initialfile=Path(self.output_path).name,
            initialdir=Path(self.output_path).parent
        )
        if filename:
            self.path_var.set(filename)
            self.output_path = filename

    def update_timer(self):
        """Обновление таймера"""
        if self.timer_running and not self.paused:
            self.record_time += 1

        hours = self.record_time // 3600
        minutes = (self.record_time % 3600) // 60
        seconds = self.record_time % 60

        self.timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        if self.timer_running:
            self.root.after(1000, self.update_timer)

    def on_closing(self):
        """Обработка закрытия окна"""
        if self.recording or self.encoding:
            if messagebox.askokcancel("Выход", "Программа работает! Всё равно выйти?\n(Запись будет потеряна!)"):
                self.cleanup_and_exit()
        else:
            self.cleanup_and_exit()

    def cleanup_and_exit(self):
        """Очистка и выход"""
        if self.hotkey_manager:
            self.hotkey_manager.stop()

        # Убиваем процессы если они ещё живы
        if self.video_capture:
            try:
                self.video_capture.stop()
            except:
                pass
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except:
                pass

        self.root.destroy()
        sys.exit(0)

def main():
    root = tk.Tk()
    app = botyaraREC(root)
    root.mainloop()

if __name__ == "__main__":
    main()
