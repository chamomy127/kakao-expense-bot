"""홈 화면 앱 아이콘을 서버에서 그려서 PNG로 제공 (이미지 파일 없이)"""
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw

BG = "#2f6fdb"
BAR = "#ffffff"
GOLD = "#ffd24a"


@lru_cache(maxsize=8)
def icon_png(size: int) -> bytes:
    """시상대(2·1·3등) 모양 아이콘. iOS가 모서리를 알아서 둥글게 깎으므로 꽉 찬 정사각형."""
    s = size * 4  # 크게 그린 뒤 줄여서 계단 현상 제거
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)

    base = s * 0.76            # 시상대 바닥선
    bw = s * 0.17              # 막대 너비
    gap = s * 0.035
    cx = s / 2
    r = s * 0.035              # 막대 위 모서리 둥글기
    bars = [                   # (x 중심, 높이)
        (cx - bw - gap, s * 0.30),   # 2등
        (cx,            s * 0.44),   # 1등
        (cx + bw + gap, s * 0.20),   # 3등
    ]
    for x, h in bars:
        d.rounded_rectangle([x - bw / 2, base - h, x + bw / 2, base], r, fill=BAR)

    # 1등 위 금메달
    mr = s * 0.075
    my = base - bars[1][1] - gap - mr
    d.ellipse([cx - mr, my - mr, cx + mr, my + mr], fill=GOLD)

    out = img.resize((size, size), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()
