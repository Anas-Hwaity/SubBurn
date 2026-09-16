from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True); (out / 'out').mkdir(exist_ok=True)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('ffmpeg is required to generate the smoke-test fixture')
    run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
         '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=25:duration=3',
         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=3',
         '-shortest', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(out / 'input.mp4')])
    (out / 'input.srt').write_text(
        '1\n00:00:00,250 --> 00:00:01,300\nHello SubBurn\n\n'
        '2\n00:00:01,500 --> 00:00:02,700\nمرحبا · שלום · Test\n', encoding='utf-8')
    run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
         'color=c=white@0.8:s=96x48:d=0.1', '-frames:v', '1', str(out / 'wm.png')])
    print(out)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
