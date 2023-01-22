import os
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple, Tuple, TypeGuard

import yaml


def escape_path(path: Path):
    return str(path).replace("\\", "\\\\")


def main():
    if len(sys.argv) == 1:
        print("please specify the yaml file", file=sys.stderr)
        return

    with open(sys.argv[1]) as filelist:
        config = Config(yaml.safe_load(filelist))

    for video in config.videos:
        path = video.path
        index_width = len(str(len(video.spans)))

        def temp_path_for(index: int) -> Path:
            tmp_path = path.with_stem(
                "{}_{}".format(path.stem, str(index).zfill(index_width))
            )
            return tmp_path

        for index, span in enumerate(video.spans):
            tmp_path = temp_path_for(index)
            if tmp_path.exists():
                os.remove(tmp_path)

            start = span[0]
            duration = span[1] - start
            if duration < 0:
                raise RuntimeError("duration must be positive")

            subprocess.check_call(
                [
                    "ffmpeg",
                    "-ss",
                    str(start),
                    "-i",
                    str(path),
                    "-t",
                    str(duration),
                    "-c:v",
                    "h264_nvenc",
                    str(tmp_path),
                ]
            )

        with open("filelist.txt", "w") as filelist:
            for index in range(len(video.spans)):
                print(
                    "file",
                    f"'{escape_path(temp_path_for(index))}'",
                    file=filelist,
                )

        # 結合
        subprocess.check_call(
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "filelist.txt",
                "-c",
                "copy",
                config.output,
            ]
        )


# Example config style:
#
# output: <path-for-output>
# videos:
# - path: <path-to-video>
#   spans:
#   - ["0:00", "0:12"]
#   - ["1:23", "1:25"]
#   - ["1:23:22", "1:23:25"]
class Config:
    output: Path
    videos: list["VideoConfig"]

    def __init__(self, config: Any):
        if not is_dict(config):
            raise RuntimeError(
                "Config must be an dict, containing output path and video configs"
            )

        if "output" not in config or not isinstance(config["output"], str):
            raise RuntimeError("Config must contain string key `output`")

        if "videos" not in config or not is_list(config["videos"]):
            raise RuntimeError("Config must contain list key `videos`")

        self.output = Path(config["output"])
        self.videos = []
        for video in config["videos"]:
            if not is_dict(video):
                raise RuntimeError(
                    "VideoConfig for a video must be a dictionary"
                )
            if "path" not in video or not isinstance(video["path"], str):
                raise RuntimeError("VideoConfig must contain key `path`")
            if "spans" not in video or not is_list(video["spans"]):
                raise RuntimeError("VideoConfig must contain key `spans`")

            self.videos.append(
                VideoConfig(
                    Path(video["path"]),
                    list(map(parse_span, video["spans"])),
                )
            )


def is_list(obj: Any) -> TypeGuard[list[object]]:
    return isinstance(obj, list)


def is_dict(obj: Any) -> TypeGuard[dict[object, object]]:
    return isinstance(obj, dict)


def is_string_dict(obj: Any) -> TypeGuard[dict[str, object]]:
    return is_dict(obj) and all(isinstance(key, str) for key in obj.keys())


def parse_span(span: object) -> Tuple[int, int]:
    if not is_list(span) or len(span) != 2:
        raise RuntimeError("Span must be list of length 2")

    return parse_time(span[0]), parse_time(span[1])


def parse_time(time: object) -> int:
    if not isinstance(time, str):
        raise RuntimeError("time must be str")

    parts = time.split(":")

    res = 0
    for part in parts:
        res *= 60
        res += int(part)

    return res


class VideoConfig(NamedTuple):
    path: Path
    spans: list[Tuple[int, int]]


if __name__ == "__main__":
    main()
