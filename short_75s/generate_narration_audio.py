"""
short_75s/generate_narration_audio.py — Fast-Paced Indonesian Voiceover Narration,
Procedural Welding/Workshop SFX & Timed YouTube Shorts Captions (`captions.srt`).
Uses `edge-tts` (`id-ID-ArdiNeural`, fallback `gTTS` or clean SFX track) + FFmpeg!
"""

from __future__ import annotations

import asyncio
import math
import random
import struct
import subprocess
import sys
import wave
from pathlib import Path
from typing import List, Tuple

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


def generate_sfx_bed_wav(out_wav: Path, sample_rate: int = 44100) -> None:
    """Synthesize subtle workshop hum + crisp electric welding arc crackle during Hook & Climax."""
    total_samples = int(DURATION_SEC * sample_rate)
    rng = random.Random(75)
    hook_s0, hook_s1 = int(((HOOK_ARC_START - 1) / FPS) * sample_rate), int((HOOK_ARC_END / FPS) * sample_rate)
    clim_s0, clim_s1 = int(((CLIMAX_ARC_START - 1) / FPS) * sample_rate), int((CLIMAX_ARC_END / FPS) * sample_rate)

    buf = bytearray(total_samples * 2)
    for i in range(total_samples):
        t = i / float(sample_rate)
        # Subtle warm workshop room tone
        val = 0.015 * math.sin(2.0 * math.pi * 55.0 * t) + 0.008 * math.sin(2.0 * math.pi * 110.0 * t)
        in_arc = (hook_s0 <= i <= hook_s1) or (clim_s0 <= i <= clim_s1)
        if in_arc:
            # 120Hz MIG transformer buzz + sizzling high-frequency spark crackle
            buzz = 0.14 * math.sin(2.0 * math.pi * 120.0 * t) + 0.07 * math.sin(2.0 * math.pi * 240.0 * t)
            crackle = (rng.uniform(-1.0, 1.0) ** 3) * 0.32
            val += buzz + crackle
        sample_i16 = max(-32767, min(32767, int(val * 32767)))
        struct.pack_into("<h", buf, i * 2, sample_i16)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(buf))
    print(f"[Audio] Synthesized 75s workshop & welding SFX bed -> {out_wav}")


async def _synth_edge_tts_clips(clips_dir: Path) -> List[Tuple[float, Path]]:
    import edge_tts

    clips: List[Tuple[float, Path]] = []
    for beat in NARRATION_BEATS:
        out_mp3 = clips_dir / f"{beat['id']}.mp3"
        comm = edge_tts.Communicate(beat["text"], voice="id-ID-ArdiNeural", rate="+18%", pitch="+2Hz")
        await comm.save(str(out_mp3))
        start_sec = (beat["start_f"] - 1) / float(FPS)
        clips.append((start_sec, out_mp3))
    return clips


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_captions_srt(CAPTIONS_SRT_PATH)

    sfx_wav = OUTPUT_DIR / "_sfx_bed.wav"
    generate_sfx_bed_wav(sfx_wav)

    clips_dir = OUTPUT_DIR / "_tts_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clips: List[Tuple[float, Path]] = []

    try:
        clips = asyncio.run(_synth_edge_tts_clips(clips_dir))
        print(f"[Audio] Synthesized {len(clips)} Indonesian neural TTS narration clips via edge-tts!")
    except Exception as exc:
        print(f"[Audio] edge-tts unavailable ({exc}); falling back to SFX-only bed.", flush=True)
        AUDIO_WAV_PATH.write_bytes(sfx_wav.read_bytes())
        return

    # Mix all timed TTS clips onto the 75s SFX bed using FFmpeg `adelay` + `amix`
    cmd = ["ffmpeg", "-y", "-i", str(sfx_wav)]
    filter_parts: List[str] = ["[0:a]volume=0.85[bed]"]
    mix_inputs = ["[bed]"]

    for idx, (start_sec, clip_path) in enumerate(clips, start=1):
        cmd.extend(["-i", str(clip_path)])
        delay_ms = int(round(start_sec * 1000))
        filter_parts.append(f"[{idx}:a]aresample=44100,adelay={delay_ms}|{delay_ms},volume=1.35[v{idx}]")
        mix_inputs.append(f"[v{idx}]")

    filter_parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95[outa]"
    )
    cmd.extend([
        "-filter_complex", ";".join(filter_parts),
        "-map", "[outa]",
        "-t", f"{DURATION_SEC:.2f}",
        "-ar", "44100", "-ac", "2",
        str(AUDIO_WAV_PATH),
    ])
    subprocess.run(cmd, check=True)
    print(f"[Audio] Mixed final 75s Indonesian narration + SFX -> {AUDIO_WAV_PATH}")


if __name__ == "__main__":
    main()
