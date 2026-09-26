# 🎥 botyaraREC

> **A lightweight screen recorder for weak hardware — record raw, encode later.**

`botyaraREC` captures your screen and audio to **uncompressed RAW files first**, then encodes to MP4 after you hit stop. This means zero frame drops during recording, even on low-end machines — the CPU only has to write to disk, not encode video in real time.

**⚠️ Linux-only. Requires X11 (uses `x11grab`) and PulseAudio/PipeWire-Pulse for audio capture.**

---

## ✨ Features

### 🎬 Raw-first Recording Strategy
Unlike OBS or other screen recorders, `botyaraREC` doesn't encode during capture. Instead:

1. **Capture phase** — ffmpeg dumps raw YUV video and PCM WAV audio straight to disk. Zero encoding overhead → no dropped frames, no stutter, even on a potato.
2. **Encode phase** — after you stop, ffmpeg encodes everything to H.264 MP4 with sensible defaults. The computer gets to be slow *now* instead of ruining your recording.

This is exactly what you want when your CPU is already busy running a game or VM.

### 🎤 Multi-Source Audio
- **Microphone** — pick any PulseAudio/PipeWire source from a dropdown
- **System audio** — captured via the default sink's monitor
- **EasyEffects-aware** — if you have EasyEffects running, its virtual source is auto-detected and preferred (perfect for noise-suppressed recordings)
- Both sources are **mixed in post** with `amix`, so they're perfectly aligned

### 🎚️ Live Controls During Recording
- ⏸ **Pause / Resume** — kills both ffmpeg processes with `SIGSTOP`, resumes with `SIGCONT`. The pause shows up as a frozen frame in the output — no silence gaps, no dropped timeline
- 🎤 **Toggle mic mid-recording** — silence just the mic while keeping the screen and system audio going
- 🔊 **Toggle system audio mid-recording** — same, for system sound

### ⌨️ Global Hotkeys
| Key | Action |
|-----|--------|
| **F8** | Start / stop recording |
| **F9** | Pause / resume |
| **F10** | Mute / unmute microphone |

Works system-wide via `pynput` — you can trigger them from inside a game or fullscreen app.

### 🧠 Smart Microphone Detection
On startup, `botyaraREC` scans all available PulseAudio sources and presents them with **human-readable names**:

- 🎧 "EasyEffects (recommended)" — auto-preferred if present
- 🎙️ "Built-in microphone" — for `analog-stereo` inputs
- 🔊 "Monitor: <device>" — for capturing a specific sink's output
- Plain source name for anything else

Monitor sources are filtered out by default (except EasyEffects', which is genuinely useful).

### 💾 Two-Stage Encoding Pipeline
The encoder is smart about which streams exist:
- **Video + mic + system** → mixes both audio tracks with `amix`, encodes to H.264 + AAC
- **Video + mic only** → single audio track
- **Video + system only** → same
- **Video only** → no audio track at all, no dummy silent audio

Audio denoising (`afftdn`) is **optional** and disabled by default — because if you're running EasyEffects, you've already handled noise on the source side, and double-denoising makes voices sound weird.

### 🖥️ Simple, Focused UI
- Big `Tkinter` window, dark theme, no clutter
- Giant monospace timer (`HH:MM:SS`)
- One **● REC** button that becomes **⬛ STOP**
- One **⏸ PAUSE** button
- Audio source pickers, path picker, done

### 🧹 Self-Cleaning
- All RAW intermediate files go into a `temp_recording/` folder
- On successful encode, the temp folder is **deleted automatically**
- If encoding fails, temp files stay so you can try again manually

### 📁 Output
- Default location: `~/Videos/recording_YYYYMMDD_HHMMSS.mp4`
- Or pick any path via the **Обзор...** button
- H.264 (`libx264`), CRF 23, `yuv420p` pixel format → plays everywhere, including Discord, phones, and browsers

### 🛡️ Zero Cloud, Zero Telemetry
- No accounts, no uploads, no analytics
- Everything is local, offline, yours

---

## 🚀 Quick Start

### Prerequisites

You need `ffmpeg` with `x11grab` support and `pactl` (from `pipewire-pulse` or `pulseaudio-utils`):

```bash
# Arch / CachyOS
sudo pacman -S ffmpeg pipewire-pulse tk python-pynput

# Debian / Ubuntu
sudo apt install ffmpeg pipewire-pulse python3-tk python3-pynput

# Fedora
sudo dnf install ffmpeg pipewire-pulseaudio python3-tkinter python3-pynput
```

### Install

```bash
git clone https://github.com/dimasbotyara/botyaraREC.git
cd botyaraREC

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Run

```bash
python botyaraREC.py
```

### Use

1. Pick your **microphone source** (EasyEffects is auto-selected if available)
2. Choose what to record: **🎤 Микрофон** and/or **🔊 Звуки системы**
3. Pick an **output path** (or leave the default `~/Videos/...`)
4. Hit **● REC** (or **F8**)
5. **F9** to pause, **F10** to mute mic on the fly
6. Hit **⬛ STOP** — encoding starts automatically
7. Wait for **"Готово!"** — your MP4 is ready

---

## ⚙️ How It Works

```
┌─────────────────┐
│  X11 screen     │──┐
└─────────────────┘  │
                     │    ┌────────────────────┐
┌─────────────────┐  ├───▶│  ffmpeg (capture)  │──▶ temp/video.yuv  (RAW YUV)
│  Pulse mic      │──┤    └────────────────────┘    temp/mic.wav   (PCM)
└─────────────────┘  │    ┌────────────────────┐
                     ├───▶│  ffmpeg (capture)  │──▶ temp/system.wav (PCM)
┌─────────────────┐  │    └────────────────────┘
│  Sink monitor   │──┘
└─────────────────┘

       ⬇ [STOP pressed]

┌───────────────────────────────────────────────┐
│  ffmpeg (encode)                              │
│  • mix mic + system with amix                 │
│  • optional afftdn denoise (off by default)   │
│  • H.264 + AAC → output.mp4                   │
└───────────────────────────────────────────────┘
```

**Pause mechanism:** both capture ffmpeg processes are in their own process group. `SIGSTOP` / `SIGCONT` are sent to the *entire group* → video and audio freeze/unfreeze in lockstep.

---

## 📁 Project Structure

```
botyaraREC/
├── botyaraREC.py        # 🎯 Main app — Tkinter GUI, state machine, hotkey wiring
├── capture.py           # 🎥 VideoCapture + AudioCapture (ffmpeg subprocesses)
├── encoder.py           # 🎞️ VideoEncoder — RAW → MP4, mixing, cleanup
├── hotkeys.py           # ⌨️ HotkeyManager — pynput listener
├── requirements.txt
└── LICENSE
```

Four files, ~750 lines of code, zero external Python dependencies except `pynput`. The heavy lifting is all `ffmpeg`.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **GUI** | Tkinter (standard library) |
| **Capture** | ffmpeg (`x11grab`, `pulse`) |
| **Encoding** | ffmpeg (`libx264`, `aac`, `amix`, `afftdn`) |
| **Hotkeys** | pynput |
| **Audio probing** | `pactl` |
| **Process control** | POSIX signals (`SIGSTOP`, `SIGCONT`, `SIGINT`, `SIGKILL`) |

---

## 🔧 Advanced

### Recording a specific area of the screen
Edit the `VideoCapture` constructor in `botyaraREC.py`:

```python
self.video_capture = VideoCapture(
    resolution=(1440, 900),   # ← change to your target size
    fps=30,
    output_dir=self.temp_dir
)
```

For a full-screen capture, set it to your monitor's native resolution.

### Recording a specific monitor
Change the `-i ':0.0'` argument in `capture.py` → `:0.1`, `:0.2`, etc., for multi-monitor setups.

### Enabling mic denoising
In `botyaraREC.py`, find the `VideoEncoder(...)` call and flip:

```python
apply_denoise_mic=False   # ← set to True
```

This adds `afftdn` to the mic chain. Leave it off if EasyEffects is already cleaning your mic.

### Changing encoder quality / speed
In `encoder.py`:

```python
'-preset', 'medium',   # ← 'fast', 'veryfast', 'slow'...
'-crf', '23',          # ← lower = better quality, larger file
```

### Auto-start recording on launch
Not built in — but you can call `self.toggle_recording_threaded()` from `__init__` if you're scripting it.

---

## 🐛 Troubleshooting

**"ffmpeg: command not found"**
- Install ffmpeg. This app has zero chance of working without it.

**Black screen / no video in the output**
- You're probably on Wayland. `x11grab` needs a real X11 session (or XWayland with a *real* X root window, which isn't always the case). Log into an X11 session, or use a Wayland-native tool.

**No mic audio**
- Check `pactl list short sources` — is your mic actually there?
- The dropdown shows human-readable names; make sure you picked the right one.

**No system audio**
- System audio is captured from the **default sink's monitor**. If nothing plays through your default output, there's nothing to capture.
- If you want to capture a *specific* app, route it to a sink and then record that sink's monitor manually.

**"Video file not found!" after stop**
- The capture process crashed. Usually a resolution mismatch: `x11grab` requires your desktop resolution to be *at least* what you passed. Try lowering it.

**Huge temp files / disk fills up**
- This is the tradeoff of RAW recording. A 1440×900 @ 30fps RAW YUV stream is ~55 MB/s. For long recordings, use a bigger `~/.temp_recording` volume, or lower the resolution.

**Hotkeys don't work in fullscreen games**
- Wayland compositors can block global hotkeys from other apps. On X11 they should work fine. If Wayland is blocking you, `ydotool` or compositor-level binds are the workaround.

---

## ⚠️ Disclaimer

`botyaraREC` is for recording your own screen and audio. Don't use it to record other people without consent, and check your local laws about audio recording. You are responsible for how you use it.

---

## 📜 License

MIT — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**dimasbotyara** — [@dimasbotyara](https://github.com/dimasbotyara)

Made with 🎥, ☕, and a stubborn refusal to buy a better CPU.

---

<div align="center">

**If this saved you from a dropped-frames disaster, drop a ⭐**

</div>
