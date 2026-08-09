"""
Модуль захвата видео и аудио
"""

import subprocess
import threading
import time
from pathlib import Path
import signal
import os

class VideoCapture:
    """Захват видео с экрана"""

    def __init__(self, resolution=(1440, 900), fps=30, output_dir=Path("temp_recording")):
        self.resolution = resolution
        self.fps = fps
        self.output_dir = Path(output_dir)
        self.video_file = self.output_dir / "video.yuv"
        self.process = None
        self.paused = False
        self.frame_count = 0
        self.running = False

    def start(self):
        """Запуск захвата"""
        # Формат: RAW YUV (несжатый)
        cmd = [
            'ffmpeg',
            '-f', 'x11grab',
            '-video_size', f'{self.resolution[0]}x{self.resolution[1]}',
            '-framerate', str(self.fps),
            '-i', ':0.0',  # Display 0
            '-f', 'rawvideo',
            '-pix_fmt', 'yuv420p',
            '-y',  # Перезаписать
            str(self.video_file)
        ]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            preexec_fn=os.setsid  # Создаём новую группу процессов
        )
        self.running = True

    def pause(self):
        """Пауза (посылаем SIGSTOP)"""
        if self.process and self.running:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
                self.paused = True
            except:
                pass

    def resume(self):
        """Продолжить (посылаем SIGCONT)"""
        if self.process and self.running:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
                self.paused = False
            except:
                pass

    def stop(self):
        """Остановка захвата"""
        if self.process and self.running:
            self.running = False
            try:
                # Посылаем SIGINT (Ctrl+C) всей группе процессов
                os.killpg(os.getpgid(self.process.pid), signal.SIGINT)

                # Ждём завершения
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Если не остановился - убиваем
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait()
            except Exception as e:
                print(f"Ошибка остановки видео: {e}")
                try:
                    self.process.kill()
                    self.process.wait()
                except:
                    pass

class AudioCapture:
    """Захват аудио (микрофон и системные звуки)"""

    def __init__(self, output_dir=Path("temp_recording"),
                 record_mic=True, record_system=True, mic_source=None):
        self.output_dir = Path(output_dir)
        self.record_mic = record_mic
        self.record_system = record_system
        self.mic_source = mic_source  # Пользовательский источник

        self.mic_file = self.output_dir / "mic.wav"
        self.system_file = self.output_dir / "system.wav"

        self.mic_process = None
        self.system_process = None

        self.mic_enabled = record_mic
        self.system_enabled = record_system
        self.running = False

    def get_default_source(self):
        """Получить источник микрофона по умолчанию"""
        # Если указан пользовательский источник, используем его
        if self.mic_source:
            return self.mic_source

        try:
            result = subprocess.run(
                ['pactl', 'get-default-source'],
                capture_output=True, text=True, check=True, timeout=2
            )
            return result.stdout.strip()
        except:
            return 'default'

    def get_default_sink_monitor(self):
        """Получить монитор sink'а (для системных звуков)"""
        try:
            # Получаем default sink
            result = subprocess.run(
                ['pactl', 'get-default-sink'],
                capture_output=True, text=True, check=True, timeout=2
            )
            sink = result.stdout.strip()
            return f"{sink}.monitor"
        except:
            return 'default'

    def start(self):
        """Запуск захвата аудио"""
        self.running = True

        # Микрофон (несжатый WAV, PCM)
        if self.record_mic:
            mic_source = self.get_default_source()
            print(f"Используется микрофон: {mic_source}")

            cmd_mic = [
                'ffmpeg',
                '-f', 'pulse',
                '-i', mic_source,
                '-acodec', 'pcm_s16le',
                '-ar', '48000',
                '-ac', '2',
                '-y',
                str(self.mic_file)
            ]
            self.mic_process = subprocess.Popen(
                cmd_mic,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                preexec_fn=os.setsid
            )

        # Системные звуки
        if self.record_system:
            system_source = self.get_default_sink_monitor()
            print(f"Используется системный звук: {system_source}")

            cmd_system = [
                'ffmpeg',
                '-f', 'pulse',
                '-i', system_source,
                '-acodec', 'pcm_s16le',
                '-ar', '48000',
                '-ac', '2',
                '-y',
                str(self.system_file)
            ]
            self.system_process = subprocess.Popen(
                cmd_system,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                preexec_fn=os.setsid
            )

    def pause(self):
        """Пауза"""
        if self.mic_process and self.running:
            try:
                os.killpg(os.getpgid(self.mic_process.pid), signal.SIGSTOP)
            except:
                pass
        if self.system_process and self.running:
            try:
                os.killpg(os.getpgid(self.system_process.pid), signal.SIGSTOP)
            except:
                pass

    def resume(self):
        """Продолжить"""
        if self.mic_process and self.running:
            try:
                os.killpg(os.getpgid(self.mic_process.pid), signal.SIGCONT)
            except:
                pass
        if self.system_process and self.running:
            try:
                os.killpg(os.getpgid(self.system_process.pid), signal.SIGCONT)
            except:
                pass

    def toggle_mic(self, enabled):
        """Включить/выключить микрофон"""
        if self.mic_process and self.running:
            try:
                if enabled:
                    os.killpg(os.getpgid(self.mic_process.pid), signal.SIGCONT)
                else:
                    os.killpg(os.getpgid(self.mic_process.pid), signal.SIGSTOP)
            except:
                pass

    def toggle_system(self, enabled):
        """Включить/выключить системный звук"""
        if self.system_process and self.running:
            try:
                if enabled:
                    os.killpg(os.getpgid(self.system_process.pid), signal.SIGCONT)
                else:
                    os.killpg(os.getpgid(self.system_process.pid), signal.SIGSTOP)
            except:
                pass

    def stop(self):
        """Остановка захвата"""
        self.running = False

        if self.mic_process:
            try:
                os.killpg(os.getpgid(self.mic_process.pid), signal.SIGINT)
                try:
                    self.mic_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self.mic_process.pid), signal.SIGKILL)
                    self.mic_process.wait()
            except Exception as e:
                print(f"Ошибка остановки микрофона: {e}")
                try:
                    self.mic_process.kill()
                    self.mic_process.wait()
                except:
                    pass

        if self.system_process:
            try:
                os.killpg(os.getpgid(self.system_process.pid), signal.SIGINT)
                try:
                    self.system_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self.system_process.pid), signal.SIGKILL)
                    self.system_process.wait()
            except Exception as e:
                print(f"Ошибка остановки системного звука: {e}")
                try:
                    self.system_process.kill()
                    self.system_process.wait()
                except:
                    pass
