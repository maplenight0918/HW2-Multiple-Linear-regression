"""集中設定與輸出工具。"""
import json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text())
RAW = ROOT / 'data/raw/playground-series-s4e5'
TABLES = ROOT / 'outputs/tables'
FIGURES = ROOT / 'outputs/figures'

def save_json(path, data):
    def convert(value):
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, Path):
            return str(value)
        raise TypeError(type(value).__name__)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=convert), encoding='utf-8')
