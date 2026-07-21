import json
import os
import re
import subprocess
from pathlib import Path

from .base import BaseLLM


LOCAL_CORRECTION_PROMPT = (
    "你是繁體中文語音輸入校正器。只修正錯字、標點、斷句與台灣用語。"
    "不要改寫語氣，不要新增內容。"
)

_S2T_FALLBACK = str.maketrans({
    "协": "協", "发": "發", "开": "開", "者": "者", "还": "還", "这": "這",
    "些": "些", "进": "進", "来": "來", "软": "軟", "体": "體", "号": "號",
    "测": "測", "试": "試", "设": "設", "计": "計", "师": "師", "录": "錄",
    "音": "音", "启": "啟", "显": "顯", "示": "示", "蓝": "藍", "红": "紅",
    "写": "寫", "点": "點", "应": "應", "该": "該", "实": "實", "现": "現",
    "题": "題", "问": "問", "间": "間", "后": "後", "个": "個", "与": "與",
    "语": "語", "输": "輸", "入": "入", "检": "檢", "查": "查", "数": "數",
    "据": "據", "户": "戶", "门": "門", "会": "會", "为": "為", "码": "碼",
    "层": "層", "灵": "靈", "话": "話", "长": "長", "简": "簡", "国": "國",
    "台": "台", "湾": "灣", "机": "機", "内": "內", "边": "邊", "栏": "欄",
    "位": "位", "则": "則", "处": "處", "线": "線", "复": "複", "杂": "雜",
    "连": "連", "接": "接", "买": "買", "卖": "賣", "东": "東", "义": "義",
})


class AppleLocalLLM(BaseLLM):
    """Apple Foundation Models local correction provider."""

    def __init__(self, config: dict):
        self.config = config
        self.timeout = float(config.get("apple_local_timeout", 5.0))
        self.max_tokens = int(config.get("apple_local_max_tokens", 700))
        self.helper_path = self._find_helper()

    def _find_helper(self) -> Path:
        candidates = []
        res_path = os.environ.get("RESOURCEPATH")
        if res_path:
            candidates.append(Path(res_path) / "helpers" / "apple_local_llm")
        candidates.append(Path(__file__).resolve().parent.parent / "helpers" / "apple_local_llm")
        for path in candidates:
            if path.exists() and os.access(path, os.X_OK):
                return path
        return candidates[0]

    def _to_traditional(self, text: str) -> str:
        try:
            from opencc import OpenCC
            return OpenCC("s2tw").convert(text)
        except Exception:
            return text.translate(_S2T_FALLBACK)

    def _restore_sentence_tail(self, original: str, output: str) -> str:
        original_tail = original.rstrip()[-1:]
        output_tail = output.rstrip()[-1:]
        if original_tail in "。？！?!" and output_tail not in "。？！?!":
            tail = {"?": "？", "!": "！"}.get(original_tail, original_tail)
            return output.rstrip() + tail
        if original_tail not in "。？！?!" and output_tail not in "。？！?!":
            if re.search(r"(好不好|對不對|是不是|可不可以|行不行)$", output.rstrip()):
                return output.rstrip() + "？"
            if re.search(r"(吧|嗎|呢|啊|啦|喔|唷|嘛)$", output.rstrip()):
                return output.rstrip() + "？" if output.rstrip().endswith(("嗎", "呢")) else output.rstrip() + "。"
        return output

    def warmup(self):
        if not self.helper_path.exists():
            return
        try:
            subprocess.run(
                [str(self.helper_path), "--check"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=min(self.timeout, 2.0),
                check=False,
            )
        except Exception:
            pass

    def _looks_worse_than_input(self, original: str, output: str) -> bool:
        sentence_marks = set("。？！?!")
        for mark in "。？！":
            if output.count(mark) < original.count(mark):
                return True
        original_marks = sum(1 for ch in original if ch in sentence_marks)
        output_marks = sum(1 for ch in output if ch in sentence_marks)
        if original.rstrip()[-1:] in sentence_marks and output.rstrip()[-1:] not in sentence_marks:
            return True
        if original_marks >= 2 and output_marks < original_marks - 1:
            return True
        if len(output) < max(1, int(len(original) * 0.75)):
            return True
        return False

    def refine(self, text: str, prompt: str) -> str:
        if not text.strip():
            return text
        fallback_text = self._restore_sentence_tail(text, self._to_traditional(text))
        if not self.helper_path.exists():
            print(f"[AppleLocalLLM] Helper not found: {self.helper_path}")
            return fallback_text

        payload = {
            "text": text,
            "prompt": prompt or LOCAL_CORRECTION_PROMPT,
            "maxTokens": self.max_tokens,
        }

        try:
            proc = subprocess.run(
                [str(self.helper_path)],
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                check=False,
            )
            if proc.returncode != 0:
                err = proc.stderr.decode("utf-8", errors="replace")[:300]
                print(f"[AppleLocalLLM] Helper failed rc={proc.returncode}: {err}")
                return fallback_text

            data = json.loads(proc.stdout.decode("utf-8"))
            if not data.get("ok"):
                print(f"[AppleLocalLLM] Unavailable: {data.get('error')} ({data.get('availability')})")
                return fallback_text

            output = self._restore_sentence_tail(text, self._to_traditional((data.get("output") or "").strip()))
            if output and self._looks_worse_than_input(text, output):
                print("[AppleLocalLLM] Output looked worse than input; fallback to input")
                return fallback_text
            elapsed = data.get("elapsed")
            if elapsed is not None:
                print(f"[AppleLocalLLM] Response received. ({elapsed:.2f}s)")
            return output or fallback_text
        except subprocess.TimeoutExpired:
            print(f"[AppleLocalLLM] Timeout ({self.timeout:.1f}s) - fallback to raw text")
            return fallback_text
        except Exception as e:
            print(f"[AppleLocalLLM] Failed: {e}")
            return fallback_text
