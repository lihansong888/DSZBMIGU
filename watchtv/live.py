import requests
import re
import os
# ========== 填写源的地址 ==========
URL_LIST = [
    "https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.txt",
    "https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/others.txt"
]
# ========== 分组映射：左边是源里的分组名，右边是输出时改后的分组名 ==========
GROUP_MAP = {
    "港澳台": "HS港澳台直播",
    "https://raw.githubusercontent.com/kimwang1978/collect-txt/refs/heads/main/others_output.txt": "HS港澳台直播",
}

def parse_any(text: str):
    res = []
    extinf_line = None
    current_group = None
    for raw_line in text.splitlines():
        ln = raw_line.strip()
        if not ln:
            continue
        if ln.startswith("#EXTINF:"):
            extinf_line = ln
            continue
        if extinf_line is not None and not ln.startswith("#"):
            res.append((extinf_line, ln))
            extinf_line = None
            continue
        if ',' in ln and not ln.startswith("#"):
            sp = ln.split(',',1)
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

def get_channel_name(extinf):
    if "," in extinf:
        return extinf.split(",")[-1].strip()
    return ""

def get_group_title(extinf):
    m = re.search(r'group-title="([^"]+)"', extinf)
    if m:
        return m.group(1).strip()
    return ""

def main():
    # 用改后的分组名初始化空列表
    group_bucket = {v: [] for v in GROUP_MAP.values()}
    seen = set()
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for url in URL_LIST:
        try:
            print(f"正在拉取：{url}")
            resp = requests.get(url, timeout=15, headers=HEADERS)
            resp.raise_for_status()
            channels = parse_any(resp.text)
            print(f"解析到频道数：{len(channels)}")
            for extinf, play_url in channels:
                ch_name = get_channel_name(extinf)
                ch_group = get_group_title(extinf)
                # 只保留GROUP_MAP里面定义的两个分组
                if ch_group not in GROUP_MAP:
                    continue
                output_group = GROUP_MAP[ch_group]
                item_key = (ch_name, play_url)
                if item_key not in seen:
                    seen.add(item_key)
                    group_bucket[output_group].append((ch_name, play_url))
        except Exception as e:
            print(f"拉取失败 {url}：{e}")

    # 输出m3u8
    output_m3u = ["#EXTM3U"]
    for gname, ch_list in group_bucket.items():
        for cname, curl in ch_list:
            fake_ext = f'#EXTINF:-1 group-title="{gname}",{cname}'
            output_m3u.append(fake_ext)
            output_m3u.append(curl)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live.m3u8")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_m3u))
    print(f"\n✅完成，已输出 {out_path}，共采集 {len(seen)} 个频道")

if __name__ == "__main__":
    main()

