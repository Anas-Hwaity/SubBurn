from __future__ import annotations

import argparse
import gzip
import io
import os
from pathlib import Path
import tarfile
import tempfile


def canonicalize(source: Path, destination: Path, epoch: int) -> None:
    source = source.resolve()
    destination = destination.resolve()
    rows: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            payload = None
            if member.isfile():
                stream = archive.extractfile(member)
                if stream is None:
                    raise RuntimeError(f"Could not read sdist member: {member.name}")
                payload = stream.read()
                if len(payload) != member.size:
                    raise RuntimeError(f"Short read for sdist member: {member.name}")
            rows.append((member, payload))

    rows.sort(key=lambda pair: pair[0].name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with temp.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch, compresslevel=9) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as out:
                    for original, payload in rows:
                        member = tarfile.TarInfo(original.name)
                        member.mode = original.mode
                        member.type = original.type
                        member.linkname = original.linkname
                        member.size = len(payload) if payload is not None else 0
                        member.mtime = int(epoch)
                        member.uid = 0
                        member.gid = 0
                        member.uname = ""
                        member.gname = ""
                        member.devmajor = original.devmajor
                        member.devminor = original.devminor
                        member.pax_headers = {}
                        out.addfile(member, io.BytesIO(payload) if payload is not None else None)
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a Python .tar.gz sdist for byte-reproducible release artifacts.")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument("--epoch", type=int, default=None)
    args = parser.parse_args()
    epoch = args.epoch
    if epoch is None:
        raw = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
        if not raw:
            parser.error("set SOURCE_DATE_EPOCH or pass --epoch")
        try:
            epoch = int(raw)
        except ValueError:
            parser.error("SOURCE_DATE_EPOCH must be an integer Unix timestamp")
    if epoch < 0:
        parser.error("epoch must be non-negative")
    destination = args.destination or args.source
    canonicalize(args.source, destination, epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
