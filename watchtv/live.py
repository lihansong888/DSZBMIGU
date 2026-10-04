import requests
import re
import os

# ========== 配置区 ==========
# 上游源地址
URL_LIST = [
    "https://raw.githubusercontent.com/jia070310/lemonTV/refs/heads/main/iptv-fe.m3u"
]

# 分组映射：源内分组名 -> 输出m3u8的分组名
# 不在KEY里的分组会直接丢弃
GROUP_MAP = {
    "央视": "HS咪咕直播柠檬线",
    "卫视": "HS咪咕直播柠檬线",
    "其他": "HS咪咕直播柠檬线",
    "央视专版": "HS咪咕直播柠檬线",
}

# 请求头，模拟浏览器，防止github raw被拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
# ============================

def parse_any(text: str):
    """
    解析m3u文本，支持标准#EXTINF格式 和 #genre#简易文本格式
    返回列表 [(extinf字符串, 播放url), ...]
    """
    res = []
    extinf_line = None
    current_group = None
    for raw_line in text.splitlines():
        ln = raw_line.strip()
        if not ln:
            continue
        # 捕获EXTINF行，下一行就是播放地址
        if ln.startswith("#EXTINF:"):
            extinf_line = ln
            continue
        # EXTINF后一行是播放链接
        if extinf_line is not None and not ln.startswith("#"):
            res.append((extinf_line, ln))
            extinf_line = None
            continue
        # #genre# 简易格式解析
        if ',' in ln and not ln.startswith("#"):
            sp = ln.split(',', 1)
            name_part = sp[0].strip()
            url_part = sp[1].strip()
            if url_part == "#genre#":
                current_group = name_part
                continue
            if current_group:
                fake_ext = f'#EXTINF:-1 group-title="{current_group}",{name_part}'
            else:
                fake_ext = f'#EXTINF:-1,{name_part}'
            res.append((fake_ext, url_part))
    return res

def get_channel_name(extinf: str) -> str:
    """从EXTINF行提取频道名称"""
    if "," in extinf:
        return extinf.split(",")[-1].strip()
    return ""

def get_group_title(extinf: str) -> str:
    """正则提取 group-title 分组名称"""
    m = re.search(r'group-title="([^"]+)"', extinf)
    if m:
        return m.group(1).strip()
    return ""

def main():
    # 初始化分组桶
    group_bucket = {v: [] for v in GROUP_MAP.values()}
    seen = set()

    for url in URL_LIST:
        try:
            print(f"🔍 正在拉取源: {url}")
            resp = requests.get(url, timeout=15, headers=HEADERS)
            resp.raise_for_status()
            channels = parse_any(resp.text)
            print(f"📥 源原始解析频道数量：{len(channels)}")

            for extinf, play_url in channels:
                ch_name = get_channel_name(extinf)
                ch_group = get_group_title(extinf)

                # 过滤：不在映射表内的分组直接跳过
                if ch_group not in GROUP_MAP:
                    continue

                output_group = GROUP_MAP[ch_group]
                item_key = (ch_name, play_url)
                if item_key not in seen:
                    seen.add(item_key)
                    group_bucket[output_group].append((ch_name, play_url))

        except requests.exceptions.RequestException as e:
            print(f"⚠️ 网络请求异常，拉取 {url} 失败：{e}")
        except Exception as e:
            print(f"⚠️ 未知异常，处理 {url} 失败：{e}")

    total_cnt = sum(len(v) for v in group_bucket.values())
    print(f"\n✅采集完成，共提取 {total_cnt} 个频道（跳过存活检测，全量输出）")
    for gname, ch_list in group_bucket.items():
        print(f"  - {gname}: {len(ch_list)} 个频道")

    # 构建输出m3u8内容
    output_m3u = ["#EXTM3U"]
    for gname, ch_list in group_bucket.items():
        for cname, curl in ch_list:
            fake_ext = f'#EXTINF:-1 group-title="{gname}",{cname}'
            output_m3u.append(fake_ext)
            output_m3u.append(curl)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    m3u8_path = os.path.join(out_dir, "live.m3u8")
    with open(m3u8_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_m3u))
    print(f"\n✅已输出 m3u8 文件：{m3u8_path}")

if __name__ == "__main__":
    main()
