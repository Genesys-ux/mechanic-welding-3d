"""
short_75s/generate_narration_audio.py — ElevenLabs Indonesian Voiceover + 100% Free
Procedural Cinematic BGM & Welding SFX Mixer + Timed YouTube Shorts Captions (`captions.srt`).
  - Voiceover ONLY via ElevenLabs Python SDK (`ELEVENLABS_API_KEY` loaded from `.env.local`)
  - BGM & SFX are 100% FREE procedural audio (ZERO ElevenLabs credits spent on BGM/SFX!)
  - Outputs `assets/short_75s_voiceover_mix.wav` (and `.mp3` if FFmpeg is installed) so GitHub
    Actions muxes the real ElevenLabs voiceover without exposing any API key!
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None  # Fallback to direct ElevenLabs REST API on Windows 260-char path systems

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from short_75s.config_short import (  # noqa: E402
    AUDIO_WAV_PATH,
    CAPTIONS_SRT_PATH,
    CLIMAX_ARC_END,
    CLIMAX_ARC_START,
    DURATION_SEC,
    FPS,
    HOOK_ARC_END,
    HOOK_ARC_START,
    OUTPUT_DIR,
)
from short_75s.story_beats import NARRATION_BEATS  # noqa: E402

PREBUILT_AUDIO_WAV: Path = PROJECT_ROOT / "assets" / "short_75s_voiceover_mix.wav"
PREBUILT_AUDIO_MP3: Path = PROJECT_ROOT / "assets" / "short_75s_voiceover_mix.mp3"

# Crisp energetic male voice (Adam / Antoni / Brian multilingual v2 works great for Indonesian!)
DEFAULT_VOICE_ID: str = "pNInz6obpgDQGcFmaJgB"  # Adam (clear, punchy YouTube Shorts storytelling)
SAMPLE_RATE: int = 24000


def _fmt_srt_time(sec: float) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    rem = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{rem:03d}"


def write_captions_srt(out_path: Path) -> None:
    lines: List[str] = []
    for idx, beat in enumerate(NARRATION_BEATS, start=1):
        t0 = (beat["start_f"] - 1) / float(FPS)
        t1 = beat["end_f"] / float(FPS)
        lines.append(f"{idx}\n{_fmt_srt_time(t0)} --> {_fmt_srt_time(t1)}\n{beat['caption']}\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[Audio] Wrote {len(NARRATION_BEATS)} timed Shorts captions -> {out_path}")


def _synth_free_bgm_and_sfx(total_samples: int, sr: int = SAMPLE_RATE) -> List[float]:
    """
    100% FREE procedural royalty-free cinematic BGM + workshop/welding SFX (ZERO ElevenLabs credits!).
    Adapts musical mood across all 5 Acts:
      - Hook (0..2s): Dramatic sub impact + welding crackle
      - Act 1-2 (2..29s): Warm upbeat acoustic/synth chord progression (A minor -> F -> C -> G)
      - Act 3 (29..43s): Moody twilight low-pass tension pulse
      - Act 4 (43..60s): Energetic rhythmic bass + MIG transformer buzz & spark crackle SFX
      - Act 5 (60..75s): Uplifting warm major sunset chord swell (C major -> G -> Am -> F -> C)
    """
    rng = random.Random(75)
    hook_s0, hook_s1 = int(((HOOK_ARC_START - 1) / FPS) * sr), int((HOOK_ARC_END / FPS) * sr)
    clim_s0, clim_s1 = int(((CLIMAX_ARC_START - 1) / FPS) * sr), int((CLIMAX_ARC_END / FPS) * sr)

    # Chord roots (Hz) per 2-second bar
    chords_warm = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
    chords_tense = [(146.83, 174.61, 220.0), (130.81, 164.81, 196.0)]
    chords_hero = [(261.63, 329.63, 392.0), (196.0, 246.94, 392.0), (220.0, 261.63, 329.63), (174.61, 220.0, 349.23)]

    out = [0.0] * total_samples
    for i in range(total_samples):
        t = i / float(sr)
        beat_pos = (t * 2.0) % 1.0  # 120 BPM quarter-note pulse
        bar_idx = int(t / 2.0)

        if t < 2.0:
            # Hook tension hit
            bgm = 0.08 * math.sin(2.0 * math.pi * 65.4 * t) * math.exp(-t * 1.4)
        elif t < 29.0:
            c0, c1, c2 = chords_warm[bar_idx % len(chords_warm)]
            pad = 0.032 * math.sin(2.0 * math.pi * c0 * t) + 0.022 * math.sin(2.0 * math.pi * c1 * t) + 0.018 * math.sin(2.0 * math.pi * c2 * t)
            pluck = 0.035 * math.sin(2.0 * math.pi * (c0 * 0.5) * t) * math.exp(-beat_pos * 5.5)
            bgm = pad + pluck
        elif t < 43.0:
            c0, c1, c2 = chords_tense[bar_idx % len(chords_tense)]
            pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * 1.0 * t)
            bgm = (0.040 * math.sin(2.0 * math.pi * c0 * 0.5 * t) + 0.022 * math.sin(2.0 * math.pi * c1 * t)) * (0.6 + 0.4 * pulse)
        elif t < 60.0:
            c0, c1, c2 = chords_warm[bar_idx % len(chords_warm)]
            drive = 0.048 * math.sin(2.0 * math.pi * c0 * 0.5 * t) * math.exp(-((t * 4.0) % 1.0) * 4.5)
            pad = 0.024 * math.sin(2.0 * math.pi * c2 * t)
            bgm = drive + pad
        else:
            c0, c1, c2 = chords_hero[bar_idx % len(chords_hero)]
            fade = min(1.0, (DURATION_SEC - t) / 2.0) if t > DURATION_SEC - 2.0 else 1.0
            bgm = fade * (
                0.038 * math.sin(2.0 * math.pi * c0 * t)
                + 0.030 * math.sin(2.0 * math.pi * c1 * t)
                + 0.026 * math.sin(2.0 * math.pi * c2 * t)
                + 0.030 * math.sin(2.0 * math.pi * c0 * 0.5 * t) * math.exp(-beat_pos * 4.0)
            )

        # Free Procedural Welding Arc Crackle SFX (Hook & Climax)
        sfx = 0.0
        if (hook_s0 <= i <= hook_s1) or (clim_s0 <= i <= clim_s1):
            buzz = 0.065 * math.sin(2.0 * math.pi * 120.0 * t) + 0.030 * math.sin(2.0 * math.pi * 240.0 * t)
            crackle = (rng.uniform(-1.0, 1.0) ** 3) * 0.16
            sfx = buzz + crackle

        out[i] = bgm + sfx
    return out


def _generate_elevenlabs_voiceover_pcm() -> List[Tuple[int, bytes]]:
    """
    Generate Indonesian voiceover ONLY via ElevenLabs `text_to_speech.convert` (PCM 24kHz 16-bit).
    Loads `ELEVENLABS_API_KEY` automatically from `.env.local` (never hardcoded!).
    """
    load_dotenv(PROJECT_ROOT / ".env.local")
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not found in environment or .env.local")

    client = ElevenLabs() if ElevenLabs is not None else None
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    v_settings = {
        "stability": 0.45,
        "similarity_boost": 0.78,
        "style": 0.35,
        "use_speaker_boost": True,
        "speed": 1.15,
    }

    clips: List[Tuple[int, bytes]] = []
    for idx, beat in enumerate(NARRATION_BEATS, start=1):
        print(f"[ElevenLabs VO {idx:2d}/{len(NARRATION_BEATS)}] Generating '{beat['id']}'...", flush=True)
        if client is not None:
            audio_iter = client.text_to_speech.convert(
                voice_id=voice_id,
                text=beat["text"],
                model_id="eleven_multilingual_v2",
                output_format="pcm_24000",
                voice_settings=v_settings,
            )
            pcm_bytes = b"".join(audio_iter)
        else:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
            payload = json.dumps({
                "text": beat["text"],
                "model_id": "eleven_multilingual_v2",
                "voice_settings": v_settings,
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/octet-stream",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                pcm_bytes = resp.read()
        start_sample = int(((beat["start_f"] - 1) / float(FPS)) * SAMPLE_RATE)
        clips.append((start_sample, pcm_bytes))
    return clips


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_captions_srt(CAPTIONS_SRT_PATH)

    # If running on GitHub Actions where prebuilt ElevenLabs audio is already in assets/, reuse it!
    if "--use-prebuilt" in sys.argv:
        if PREBUILT_AUDIO_WAV.exists():
            AUDIO_WAV_PATH.write_bytes(PREBUILT_AUDIO_WAV.read_bytes())
            print(f"[Audio] Reused prebuilt ElevenLabs VO + Free BGM/SFX -> {AUDIO_WAV_PATH}")
            return

    total_samples = int(DURATION_SEC * SAMPLE_RATE)
    print("[Audio] Synthesizing 100% FREE procedural BGM & welding SFX bed...")
    bed = _synth_free_bgm_and_sfx(total_samples, sr=SAMPLE_RATE)

    vo_clips = _generate_elevenlabs_voiceover_pcm()
    vo_track = [0.0] * total_samples
    vo_active = [False] * total_samples

    for start_s, pcm_bytes in vo_clips:
        n_samp = len(pcm_bytes) // 2
        if n_samp == 0:
            continue
        samples = struct.unpack(f"<{n_samp}h", pcm_bytes[: n_samp * 2])
        for k, sv in enumerate(samples):
            pos = start_s + k
            if pos >= total_samples:
                break
            vo_track[pos] += sv / 32768.0
            vo_active[pos] = True

    # Auto-duck free BGM/SFX slightly when ElevenLabs narrator speaks, then normalize cleanly
    pcm_out = bytearray(total_samples * 2)
    for i in range(total_samples):
        duck = 0.45 if vo_active[i] else 0.90
        mixed = bed[i] * duck + vo_track[i] * 1.12
        # Soft tanh limiter to prevent any digital clipping
        mixed = math.tanh(mixed * 1.05) * 0.96
        struct.pack_into("<h", pcm_out, i * 2, max(-32767, min(32767, int(mixed * 32767))))

    for out_p in (AUDIO_WAV_PATH, PREBUILT_AUDIO_WAV):
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_p), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(bytes(pcm_out))
    print(f"[Audio] Saved 75s ElevenLabs Voiceover + Free BGM/SFX -> {PREBUILT_AUDIO_WAV}")

    if shutil.which("ffmpeg"):
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(PREBUILT_AUDIO_WAV), "-c:a", "libmp3lame", "-b:a", "128k", str(PREBUILT_AUDIO_MP3)],
            check=True,
        )
        print(f"[Audio] Compressed MP3 copy -> {PREBUILT_AUDIO_MP3}")


if __name__ == "__main__":
    main()
