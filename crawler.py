import asyncio
from bilibili_api import user, sync
import pandas as pd
import os

# --- 在这里修改你要抓取的 UID ---
UID = 25876945  # 影视飓风: 946974 | 何同学: 25876945

async def get_mediastorm_data():
    st_user = user.User(uid=UID)
    
    # 这里的逻辑是为了获取 UP 主的名字，用来给文件命名
    info = await st_user.get_user_info()
    up_name = info['name']
    print(f"🚀 正在接入 B 站 API，调取【{up_name}】的最新视频数据...")
    
    res = await st_user.get_videos(pn=1)
    v_list = res['list']['vlist']
    
    data = []
    for v in v_list:
        data.append({
            '标题': v['title'],
            '播放量': v['play'],
            '评论数': v['comment'],
            '时长': v['length'],
            '发布时间': pd.to_datetime(v['created'], unit='s'),
            'BVID': v['bvid']
        })
    
    df = pd.DataFrame(data)
    
    # --- 核心修正：动态路径 ---
    # 使用 f-string，根据 UP 主的名字生成文件名，存入你的 512G 固态 U 盘
    file_name = f"{up_name}_videos.csv"
    save_path = os.path.join(r'M:\My_DS_Lab\data', file_name)
    
    if not os.path.exists(r'M:\My_DS_Lab\data'):
        os.makedirs(r'M:\My_DS_Lab\data')
        
    df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"✅ 采集完成！共抓取 {len(df)} 条数据。")
    print(f"📁 数据已存入: {save_path}")

if __name__ == "__main__":
    sync(get_mediastorm_data())
