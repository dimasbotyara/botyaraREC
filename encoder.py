"""
Модуль кодирования видео
"""

import subprocess
from pathlib import Path
import shutil

class VideoEncoder:
    """Кодирование RAW видео в MP4"""

    def __init__(self, temp_dir, output_path, fps=30,
                 resolution=(1440, 900), apply_denoise_mic=True):
        self.temp_dir = Path(temp_dir)
        self.output_path = Path(output_path)
        self.fps = fps
        self.resolution = resolution
        self.apply_denoise_mic = apply_denoise_mic

        self.video_file = self.temp_dir / "video.yuv"
        self.mic_file = self.temp_dir / "mic.wav"
        self.system_file = self.temp_dir / "system.wav"

    def encode(self):
        """Кодирование"""
        # Проверяем наличие файлов
        has_video = self.video_file.exists()
        has_mic = self.mic_file.exists()
        has_system = self.system_file.exists()

        if not has_video:
            raise Exception("Видео файл не найден!")

        # Создаем директорию для выходного файла
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Собираем команду ffmpeg
        cmd = ['ffmpeg', '-y']

        # Входное видео (RAW YUV)
        cmd.extend([
            '-f', 'rawvideo',
            '-pix_fmt', 'yuv420p',
            '-video_size', f'{self.resolution[0]}x{self.resolution[1]}',
            '-framerate', str(self.fps),
            '-i', str(self.video_file)
        ])

        # Обработка аудио
        if has_mic and has_system:
            # Оба источника: микрофон + система
            cmd.extend(['-i', str(self.mic_file)])
            cmd.extend(['-i', str(self.system_file)])

            if self.apply_denoise_mic:
                # Шумоподавление на микрофоне, потом микс
                filter_complex = '[1:a]afftdn=nf=-25[mic];[mic][2:a]amix=inputs=2:duration=longest[aout]'
            else:
                # Просто микс без обработки
                filter_complex = '[1:a][2:a]amix=inputs=2:duration=longest[aout]'

            cmd.extend(['-filter_complex', filter_complex])
            cmd.extend(['-map', '0:v', '-map', '[aout]'])

        elif has_mic:
            # Только микрофон
            cmd.extend(['-i', str(self.mic_file)])

            if self.apply_denoise_mic:
                # С шумоподавлением
                cmd.extend(['-filter_complex', '[1:a]afftdn=nf=-25[aout]'])
                cmd.extend(['-map', '0:v', '-map', '[aout]'])
            else:
                # Без обработки
                cmd.extend(['-map', '0:v', '-map', '1:a'])

        elif has_system:
            # Только система
            cmd.extend(['-i', str(self.system_file)])
            cmd.extend(['-map', '0:v', '-map', '1:a'])

        else:
            # Только видео, без аудио
            cmd.extend(['-map', '0:v'])

        # Кодеки и параметры
        # H.264 с CRF (качество), битрейт автоматический
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'medium',  # Баланс скорость/качество
            '-crf', '23',  # Качество (18-28, меньше = лучше)
            '-pix_fmt', 'yuv420p',  # Совместимость
        ])

        # Аудио кодек (только если есть аудио)
        if has_mic or has_system:
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '192k',  # Битрейт аудио
                '-ar', '48000'
            ])

        cmd.append(str(self.output_path))

        # Запускаем кодирование
        print(f"Команда кодирования: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Выводим прогресс
        for line in process.stdout:
            print(line.strip())

        process.wait()

        if process.returncode != 0:
            raise Exception(f"Ошибка кодирования (код {process.returncode})")

    def cleanup(self):
        """Удаление временных файлов"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
