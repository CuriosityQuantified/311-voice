#!/usr/bin/env python3
"""Generate 200 synthetic voice files using edge-tts."""

import asyncio
import json
import os

import edge_tts

VOICES = [
    "en-US-AvaNeural",      # Female
    "en-US-AndrewNeural",   # Male
    "en-US-EmmaNeural",     # Female
    "en-US-BrianNeural",    # Male
    "en-GB-SoniaNeural",    # Female British
    "en-GB-RyanNeural",     # Male British
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


async def generate_one(idx: int, text: str, voice: str) -> None:
    """Generate a single MP3 file."""
    out_path = os.path.join(OUTPUT_DIR, f"sample_{idx:03d}.mp3")
    if os.path.exists(out_path):
        print(f"Skipping {out_path} (exists)")
        return
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)
    print(f"Generated {out_path}")


async def main():
    with open(os.path.join(OUTPUT_DIR, "transcripts.json")) as f:
        transcripts = json.load(f)

    # Generate with a few voices for variety
    tasks = []
    for i, text in enumerate(transcripts, 1):
        voice = VOICES[i % len(VOICES)]
        tasks.append(generate_one(i, text, voice))

    # Run in batches to avoid overwhelming the network
    batch_size = 10
    for batch_start in range(0, len(tasks), batch_size):
        batch = tasks[batch_start:batch_start + batch_size]
        await asyncio.gather(*batch)
        print(f"Batch {batch_start // batch_size + 1} done ({batch_start + len(batch)} / {len(tasks)})")

    print(f"\nAll {len(transcripts)} audio files generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
