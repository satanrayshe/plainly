"""One real Bedrock call per model, before anything else runs live: image + forced record_letter tool.

    python scripts/smoke_bedrock.py                        # every model in MODEL_IDS (or the default chain)
    python scripts/smoke_bedrock.py us.amazon.nova-2-lite-v1:0

Uses the Lambda's own code path (pipeline.extract -> bedrock.call_tool) with your local AWS credentials,
region us-east-1. For each model it prints whether the forced toolChoice was accepted ("tool"), downgraded
to {"any": {}} ("any") or fell back to JSON in text ("text"), plus latency and tokens. Costs well under a cent.
"""
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.pop("PLAINLY_MOCK", None)

import agencies  # noqa: E402
import bedrock  # noqa: E402
import pipeline  # noqa: E402

LETTER = ROOT / "samples" / "letters" / "irs-balance-due.png"


class Budget:
    def remaining_ms(self):
        return 25_000


def jpeg_bytes(path):
    image = Image.open(path).convert("RGB")
    image.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


def main():
    models = sys.argv[1:] or bedrock.model_ids()
    image = jpeg_bytes(LETTER)
    keys = [a["key"] for a in agencies.load_registry()["agencies"]]
    failures = 0
    for model in models:
        os.environ["MODEL_IDS"] = model
        bedrock.reset_client()
        started = time.perf_counter()
        try:
            result = pipeline.extract(image, "jpeg", "", agency_keys=keys, need_transcript=False, budget=Budget())
        except bedrock.BedrockUnavailable as exc:
            failures += 1
            print(f"FAIL {model}: {exc}")
            continue
        wall = int((time.perf_counter() - started) * 1000)
        data = result.data
        print(f"OK   {model}: mode={result.mode} {wall} ms, {result.input_tokens} in / {result.output_tokens} out; "
              f"sender={data.get('claimed_sender')!r} agency={data.get('claimed_agency_key')!r} "
              f"deadlines={len(data.get('deadlines') or [])}")
    return 1 if failures == len(models) else 0


if __name__ == "__main__":
    sys.exit(main())
