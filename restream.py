#!/usr/bin/env python3
"""
Restream a YouTube-LIVE broadcast to any RTMP server.

Usage:
    python restream.py  '<youtube-live-url>'  'rtmp://ingest.example.com/live/streamkey'
"""
import argparse
import asyncio
import subprocess
import sys
from stream import stream_from_yt   # the file you already have

FFMPEG = "ffmpeg"          # or full path if not in $PATH
CHUNK_SIZE = 131_072       # keep same size as stream.py

async def restream(yt_url: str, rtmp_url: str, quality: str = "best"):
    """
    yt_url   – full YouTube live URL (https://www.youtube.com/watch?v=….)
    rtmp_url – destination RTMP url (rtmp://… or rtmps://…)
    quality  – yt-dlp format selector (best, 720p, etc.)
    """
    # ------------------------------------------------------------------ ffmpeg
    # -re  is NOT used: we push as fast as we receive (live edge).
    # -c:v copy -c:a copy  →  no re-encoding, just re-mux to FLV.
    ffmpeg_cmd = [
        FFMPEG,
        "-hide_banner", "-loglevel", "error",
        "-i", "-",                      # read mkv from stdin
        "-c:v", "copy",
        "-c:a", "copy",
        "-f", "flv",
        rtmp_url
    ]

    ffmpeg = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=sys.stderr,   # redirect ffmpeg banner to stderr
        stderr=sys.stderr
    )

    # -------------------------------------------------------------- streaming
    try:
        async for chunk in stream_from_yt(yt_url, format=quality, sl=None):
            ffmpeg.stdin.write(chunk)
            ffmpeg.stdin.flush()
    except (BrokenPipeError, KeyboardInterrupt):
        print("\n[restream] interrupted by user or broken pipe – shutting down…")
    finally:
        # ---------------------------------------------------------- cleanup
        if ffmpeg.stdin:
            ffmpeg.stdin.close()
        ffmpeg.wait(timeout=5)
        print("[restream] ffmpeg exited with code", ffmpeg.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube-LIVE → RTMP restreamer")
    parser.add_argument("youtube_url", help="YouTube live video URL")
    parser.add_argument("rtmp_url", help="Target RTMP push URL")
    parser.add_argument("-q", "--quality", default="best",
                        help="yt-dlp format selector (default: best)")
    args = parser.parse_args()

    try:
        asyncio.run(restream(args.youtube_url, args.rtmp_url, args.quality))
    except KeyboardInterrupt:
        pass
