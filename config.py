import json
import os
from pathlib import Path

_ROOT = Path(__file__).parent
_DEFAULTS_PATH = _ROOT / "config.defaults.json"
_CONFIG_PATH = _ROOT / "config.json"
_CHANNEL_CONFIGS_DIR = _ROOT / "channel_configs"


def _load(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _merged_config() -> dict:
    defaults = _load(_DEFAULTS_PATH)
    try:
        user = _load(_CONFIG_PATH)
    except FileNotFoundError:
        return defaults
    return {**defaults, **user}


def _get(key: str):
    return _merged_config()[key]


class DBConfig:
    @property
    def prodname(self) -> str:
        return _get("prodname")

    @property
    def db_beats(self) -> Path:
        return Path(_get("db_beats"))

    @property
    def db_loops(self) -> Path:
        return Path(_get("db_loops"))


class ProcessConfig:
    @property
    def prodname(self) -> str:
        return _get("prodname")

    @property
    def pics_path(self) -> Path:
        return Path(_get("pics_path"))

    @property
    def vids_path(self) -> Path:
        return Path(_get("vids_path"))

    @property
    def export_dir(self) -> Path:
        return Path(_get("export_dir"))

    @property
    def mp3_dir(self) -> Path:
        return Path(_get("mp3_dir"))

    @property
    def ffargs(self) -> str:
        return _get("ffargs")

    @property
    def artists(self) -> list[str]:
        cfg = _merged_config()
        artists = []
        for f in _CHANNEL_CONFIGS_DIR.glob("*.json"):
            ch = _load(f)
            artists.extend(ch.get("artists", []))
        return artists


class UploadCFG:
    @property
    def subtitle3(self) -> str:
        return _get("subtitle3")

    @property
    def ig(self) -> str:
        return _get("ig")

    @property
    def email(self) -> str:
        return _get("email")

    @property
    def store(self) -> str:
        return _get("store")

    @property
    def prodname(self) -> str:
        return _get("prodname")

    @property
    def dropbox_token(self) -> str:
        token = os.getenv("DROPBOX_TOKEN")
        if not token:
            raise EnvironmentError("DROPBOX_TOKEN not set in environment")
        return token


class ChannelCFG:
    def __init__(self, channel_name: str):
        path = _CHANNEL_CONFIGS_DIR / f"{channel_name}.json"
        if not path.exists():
            raise FileNotFoundError(f"No config found for channel '{channel_name}'")
        self._data = _load(path)

    @property
    def title(self) -> str:
        return self._data.get("title", "")

    @property
    def title_suffix(self) -> str | None:
        return self._data.get("title_suffix")

    @property
    def playlist(self) -> str:
        return self._data.get("playlist", "")

    @property
    def tags(self) -> str:
        return self._data.get("tags", "")

    @property
    def gpt_tags(self) -> str:
        return self._data.get("gpt_tags", "")

    @property
    def artists(self) -> list[str]:
        return self._data.get("artists", [])
