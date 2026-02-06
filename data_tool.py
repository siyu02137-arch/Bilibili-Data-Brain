import pandas as pd
import os
import re
import requests
from collections import Counter

class DataTool:
    def __init__(self, data_dir=r'M:\My_DS_Lab\data'):
        self.data_dir = data_dir
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com"
        }

    # ... (保留 clean_num, load_and_clean, get_keywords 逻辑)
    def clean_num(self, val):
        try:
            s = str(val).strip()
            if '万' in s: return float(re.findall(r'\d+\.?\d*', s)[0]) * 10000
            res = re.sub(r'[^\d.]', '', s)
            return float(res) if res else 0
        except: return 0

    def load_and_clean(self, file_name):
        file_path = os.path.join(self.data_dir, file_name)
        if not os.path.exists(file_path): return None
        try: df = pd.read_csv(file_path, encoding='utf-8-sig')
        except: df = pd.read_csv(file_path, encoding='gbk')
        df.columns = [str(c).strip() for c in df.columns]
        v_col = next((c for c in df.columns if '播放' in c or 'view' in c), None)
        l_col = next((c for c in df.columns if '点赞' in c or 'like' in c), None)
        c_col = next((c for c in df.columns if '评论' in c or 'reply' in c), None)
        t_col = next((c for c in df.columns if '标题' in c or 'title' in c), None)
        if not v_col: return None
        df['播放量'] = df[v_col].apply(self.clean_num)
        likes = df[l_col].apply(self.clean_num) if l_col else 0
        comms = df[c_col].apply(self.clean_num) if c_col else 0
        df['互动率'] = ((likes + comms) / df['播放量'].replace(0, 1)) * 100
        df['标题'] = df[t_col] if t_col else '未知标题'
        return df

    def get_keywords(self, df, top_n=12):
        all_titles = " ".join(df['标题'].astype(str).tolist())
        found_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
        stop_words = ['视频', '我们', '一个', '这个', '什么', '如何', '真的', '没有', '就是', '可以']
        valid_words = [w for w in found_words if w not in stop_words]
        return Counter(valid_words).most_common(top_n)

    # --- Stage 4 新增：真实评论抓取逻辑 ---
    def fetch_real_comments(self, bvid):
        """通过 BVID 获取前 20 条真实评论"""
        try:
            # 1. 转换 BVID 为 AID
            api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            resp = requests.get(api_url, headers=self.headers, timeout=5).json()
            aid = resp['data']['aid']
            
            # 2. 获取评论
            reply_url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&pn=1&ps=20&sort=2"
            reply_resp = requests.get(reply_url, headers=self.headers, timeout=5).json()
            replies = reply_resp['data']['replies']
            
            return [r['content']['message'] for r in replies]
        except Exception as e:
            return [f"抓取失败: {str(e)}"]

    def analyze_sentiment(self, text_list):
        """升级版分析：处理真实评论列表"""
        raw_text = " ".join(text_list)
        emotions = re.findall(r'[\u4e00-\u9fa5]{1,4}[！!]|太[\u4e00-\u9fa5]{1,2}了', raw_text)
        questions = re.findall(r'[\u4e00-\u9fa5]{2,5}[？?]', raw_text)
        report = []
        if emotions:
            top_emo = Counter(emotions).most_common(3)
            report.append(f"🔥 观众高频情绪：{' '.join([x[0] for x in top_emo])}")
        if questions:
            top_que = Counter(questions).most_common(2)
            report.append(f"❓ 核心疑惑点：{' '.join([x[0] for x in top_que])}")
        return "\n".join(report) if report else "😐 情绪反馈较少，建议增强内容冲击力。"
