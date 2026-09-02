#!/usr/bin/env python3
"""八字四柱基础计算器。默认公历、东八区和节气日期近似。"""

import argparse
import json
from datetime import date, timedelta
from typing import Dict, List, Tuple

TIANGAN = list("甲乙丙丁戊己庚辛壬癸")
DIZHI = list("子丑寅卯辰巳午未申酉戌亥")
GAN_WUXING = dict(zip(TIANGAN, "木木火火土土金金水水"))
GAN_YINYANG = dict(zip(TIANGAN, "阳阴阳阴阳阴阳阴阳阴"))
ZHI_WUXING = dict(zip(DIZHI, "水土木木土火火土金金土水"))
ZHI_SHENGXIAO = dict(zip(DIZHI, "鼠牛虎兔龙蛇马羊猴鸡狗猪"))
CANGGAN = {"子": "癸", "丑": "己癸辛", "寅": "甲丙戊", "卯": "乙", "辰": "戊乙癸", "巳": "丙戊庚", "午": "丁己", "未": "己丁乙", "申": "庚壬戊", "酉": "辛", "戌": "戊辛丁", "亥": "壬甲"}
WUXING = list("木火土金水")
MONTH_STARTS = [(2, 4, 2), (3, 6, 3), (4, 5, 4), (5, 6, 5), (6, 6, 6), (7, 7, 7), (8, 8, 8), (9, 8, 9), (10, 8, 10), (11, 8, 11), (12, 7, 12), (1, 6, 1)]
MONTH_GAN_START = {"甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚", "辛": "庚", "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲"}
HOUR_GAN_START = {"甲": "甲", "己": "甲", "乙": "丙", "庚": "丙", "丙": "戊", "辛": "戊", "丁": "庚", "壬": "庚", "戊": "壬", "癸": "壬"}

def cyc_index(value: str, seq: List[str]) -> int:
    return seq.index(value)

def hour_branch(hour: int) -> int:
    if hour == 23 or hour == 0: return 0
    return (hour + 1) // 2

def year_pillar(year: int, month: int, day: int) -> Tuple[str, str]:
    effective_year = year - 1 if (month < 2 or (month == 2 and day < 4)) else year
    offset = effective_year - 1984
    return TIANGAN[offset % 10], DIZHI[offset % 12]

def month_branch(month: int, day: int) -> Tuple[str, bool]:
    current = date(2000, month, day)
    candidates = []
    for m, boundary, branch in MONTH_STARTS:
        y = 2000 if m != 1 or month != 1 else 1999
        boundary_date = date(y, m, boundary)
        if (month == 1 and y == 1999): boundary_date = date(2000, 1, boundary)
        candidates.append((boundary_date, branch))
    # 月份边界按同一公历年的近似日期处理；一月归丑，二月立春前仍归丑。
    if month == 1 or (month == 2 and day < 4): return "丑", True
    boundaries = [(2, 4, "寅"), (3, 6, "卯"), (4, 5, "辰"), (5, 6, "巳"), (6, 6, "午"), (7, 7, "未"), (8, 8, "申"), (9, 8, "酉"), (10, 8, "戌"), (11, 8, "亥"), (12, 7, "子")]
    branch = "丑"
    for m, boundary, candidate in boundaries:
        if month > m or (month == m and day >= boundary): branch = candidate
    return branch, False

def month_pillar(year_gan: str, branch: str) -> Tuple[str, str]:
    branch_index = DIZHI.index(branch)
    month_number = ((branch_index - 2) % 12) + 1
    start_gan = MONTH_GAN_START[year_gan]
    gan = TIANGAN[(TIANGAN.index(start_gan) + month_number - 1) % 10]
    return gan, branch

def julian_day(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12; y = year + 4800 - a; m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

def day_pillar(year: int, month: int, day: int) -> Tuple[str, str]:
    # 2000-01-01 为戊午日；JDN + 49 将其映射到六十甲子索引 54。
    index = (julian_day(year, month, day) + 49) % 60
    return TIANGAN[index % 10], DIZHI[index % 12]

def hour_pillar(day_gan: str, hour: int) -> Tuple[str, str]:
    zhi_index = hour_branch(hour)
    start = HOUR_GAN_START[day_gan]
    return TIANGAN[(TIANGAN.index(start) + zhi_index) % 10], DIZHI[zhi_index]

def shishen(day_gan: str, target_gan: str) -> str:
    relation = (WUXING.index(GAN_WUXING[target_gan]) - WUXING.index(GAN_WUXING[day_gan])) % 5
    polarity = 0 if GAN_YINYANG[day_gan] == GAN_YINYANG[target_gan] else 1
    names = {(0, 0): "比肩", (0, 1): "劫财", (1, 0): "食神", (1, 1): "伤官", (2, 0): "偏财", (2, 1): "正财", (3, 0): "七杀", (3, 1): "正官", (4, 0): "偏印", (4, 1): "正印"}
    return names[(relation, polarity)]

def wuxing_count(pillars: List[Tuple[str, str]]) -> Dict[str, float]:
    count = {key: 0.0 for key in WUXING}
    for gan, zhi in pillars:
        count[GAN_WUXING[gan]] += 1.0; count[ZHI_WUXING[zhi]] += 1.0
        for hidden in CANGGAN[zhi]: count[GAN_WUXING[hidden]] += 0.35
    return count

def strength(day_gan: str, month_zhi: str, pillars: List[Tuple[str, str]]) -> Dict:
    me = GAN_WUXING[day_gan]; month_element = ZHI_WUXING[month_zhi]
    season_state = {"旺": me, "相": WUXING[(WUXING.index(me) - 1) % 5], "休": WUXING[(WUXING.index(me) + 1) % 5], "囚": WUXING[(WUXING.index(me) + 2) % 5], "死": WUXING[(WUXING.index(me) + 3) % 5]}
    state = next((label for label, element in season_state.items() if element == month_element), "未知")
    roots = sum(1 for _, zhi in pillars if me in [GAN_WUXING[x] for x in CANGGAN[zhi]])
    helpers = sum(1 for gan, _ in pillars if GAN_WUXING[gan] in (me, WUXING[(WUXING.index(me) - 1) % 5]))
    score = (2 if state in ("旺", "相") else 0) + (2 if roots >= 2 else 1 if roots == 1 else 0) + (1 if helpers >= 2 else 0)
    overall = "身强" if score >= 4 else "中和" if score >= 2 else "身弱"
    return {"日主": f"{day_gan}（{me}）", "月令": f"{month_zhi}（{month_element}）", "月令状态": state, "通根数": roots, "生扶天干数": helpers, "综合判断": overall, "评分": score}

def yongshen(day_gan: str, overall: str) -> Dict:
    idx = WUXING.index(GAN_WUXING[day_gan])
    if overall == "身强":
        favorable = [WUXING[(idx + 1) % 5], WUXING[(idx + 2) % 5], WUXING[(idx + 3) % 5]]
        avoid = [WUXING[(idx + 4) % 5], WUXING[idx]]
    else:
        favorable = [WUXING[(idx + 4) % 5], WUXING[idx]]
        avoid = [WUXING[(idx + 1) % 5], WUXING[(idx + 2) % 5], WUXING[(idx + 3) % 5]]
    return {"喜用方向": favorable, "需谨慎方向": avoid, "说明": "仅为身强弱初筛；调候、格局和实际处境可能修正结论"}

def dayun(year_gan: str, month_gan: str, month_zhi: str, gender: str, birth: date) -> List[Dict]:
    forward = (GAN_YINYANG[year_gan] == "阳" and gender == "男") or (GAN_YINYANG[year_gan] == "阴" and gender == "女")
    direction = 1 if forward else -1
    next_boundary = date(birth.year + (1 if birth.month >= 12 else 0), 1, 6) if birth.month == 12 else date(birth.year, birth.month + 1, 6)
    days = max(1, (next_boundary - birth).days) if forward else max(1, (birth - date(birth.year, max(1, birth.month - 1), 6)).days)
    start_age = max(1, round(days / 3))
    result = []
    for index in range(8):
        gan = TIANGAN[(TIANGAN.index(month_gan) + (index + 1) * direction) % 10]
        zhi = DIZHI[(DIZHI.index(month_zhi) + (index + 1) * direction) % 12]
        result.append({"序": index + 1, "年龄范围": f"{start_age + index * 10}-{start_age + index * 10 + 9}岁", "干支": gan + zhi, "天干五行": GAN_WUXING[gan], "地支五行": ZHI_WUXING[zhi]})
    return result

def paipan(year: int, month: int, day: int, hour: int, gender: str = "男") -> Dict:
    birth = date(year, month, day)
    yg, yz = year_pillar(year, month, day); mb, _ = month_branch(month, day); mg, mz = month_pillar(yg, mb); dg, dz = day_pillar(year, month, day); hg, hz = hour_pillar(dg, hour)
    pillars = [(yg, yz), (mg, mz), (dg, dz), (hg, hz)]
    names = ["年柱", "月柱", "日柱", "时柱"]
    pillar_data = {}
    for index, (label, (gan, zhi)) in enumerate(zip(names, pillars)):
        pillar_data[label] = {"干支": gan + zhi, "天干": gan, "天干五行": GAN_WUXING[gan], "天干阴阳": GAN_YINYANG[gan], "地支": zhi, "地支五行": ZHI_WUXING[zhi], "藏干": list(CANGGAN[zhi]), "十神": "日主" if index == 2 else shishen(dg, gan)}
    strength_data = strength(dg, mz, pillars)
    return {"基本信息": {"公历": f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:00", "性别": gender, "生肖": ZHI_SHENGXIAO[yz], "历法假设": "公历、节气日期近似、东八区、23:00 归子时"}, "四柱": pillar_data, "五行统计": wuxing_count(pillars), "日主分析": strength_data, "喜用初筛": yongshen(dg, strength_data["综合判断"]), "大运": dayun(yg, mg, mz, gender, birth)}

def main() -> None:
    parser = argparse.ArgumentParser(description="八字四柱基础计算")
    parser.add_argument("year", type=int); parser.add_argument("month", type=int); parser.add_argument("day", type=int); parser.add_argument("hour", type=int); parser.add_argument("gender", nargs="?", default="男")
    args = parser.parse_args(); print(json.dumps(paipan(args.year, args.month, args.day, args.hour, args.gender), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
