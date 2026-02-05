import streamlit as st
import pandas as pd
import os
import requests
import re

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(page_title="B站内容决策看板", layout="wide")
st.title("🎬 博主数据 PK 擂台：内容规律深度洞察")

# --- 修复 1：Ollama 超时时间延长至 300秒 ---
def call_ollama(model_name, prompt):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    try:
        # 设置 300秒 (5分钟) 超时，防止 4060 思考太久报错
        response = requests.post(url, json=payload, timeout=300)
        return response.json().get('response', "AI 思考超时，未返回结果...")
    except requests.exceptions.ReadTimeout:
        return "❌ AI 思考超时 (超过5分钟)，建议检查显卡显存占用。"
    except Exception as e:
        return f"❌ 连接 Ollama 失败: {str(e)}"

def convert_time(time_str):
    try:
        if pd.isna(time_str): return 0
        parts = str(time_str).strip().split(':')
        if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    except: return 0

def clean_num(val):
    try:
        s = str(val).strip()
        if '万' in s:
            return float(re.findall(r'\d+\.?\d*', s)[0]) * 10000
        res = re.sub(r'[^\d.]', '', s)
        return float(res) if res else 0
    except: return 0

# --- 修复 2：缺数据也能算的“强力加载器” ---
@st.cache_data
def load_data(file_name):
    file_path = os.path.join(r'M:\My_DS_Lab\data', file_name)
    if not os.path.exists(file_path): return None
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_path, encoding='gbk')

    df.columns = [str(c).strip() for c in df.columns]
    
    def find_col(keys):
        return next((c for c in df.columns if any(k in c.lower() for k in keys)), None)

    v_col = find_col(['播放', 'view', '观看'])
    l_col = find_col(['点赞', 'like', '赞'])
    c_col = find_col(['评论', 'reply', 'comment', '复'])
    t_col = find_col(['标题', 'title'])
    d_col = find_col(['时长', 'time', 'duration'])

    # 1. 只有找不到播放量时才算失败
    if not v_col:
        st.sidebar.error(f"❌ 文件 {file_name} 严重损坏：找不到播放量！")
        return None

    # 2. 数据清洗
    df['播放量'] = df[v_col].apply(clean_num)

    # 3. 【核心修复】智能互动率计算（有点赞用点赞，没点赞只用评论）
    likes = df[l_col].apply(clean_num) if l_col else 0
    comms = df[c_col].apply(clean_num) if c_col else 0
    
    # 诊断提示：如果缺失点赞，给用户一个提示，但不要报错
    if l_col is None:
        st.sidebar.warning(f"⚠️ {file_name} 缺失点赞数据，互动率将仅基于评论计算。")

    # 计算公式：(点赞+评论)/播放量。如果点赞是0，就变成了 评论/播放量
    df['互动率'] = ((likes + comms) / df['播放量'].replace(0, 1)) * 100

    df['总秒数'] = df[d_col].apply(convert_time) if d_col else 0
    df['标题'] = df[t_col] if t_col else "未知标题"
    
    return df

# ==========================================
# 2. 侧边栏
# ==========================================
st.sidebar.header("🥊 擂台选手选择")
data_dir = r'M:\My_DS_Lab\data'

if os.path.exists(data_dir):
    all_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    selected_files = st.sidebar.multiselect("选择对比博主", all_files, default=all_files[:2] if len(all_files)>=2 else all_files)
else:
    st.error("无法访问 M 盘，请确认 U 盘已插入！")
    selected_files = []

# ==========================================
# 3. 主逻辑
# ==========================================
if selected_files:
    combined_data = []
    for f in selected_files:
        temp_df = load_data(f)
        if temp_df is not None:
            temp_df['博主'] = f.replace('.csv', '').replace('_videos', '')
            combined_data.append(temp_df)
    
    if combined_data:
        all_df = pd.concat(combined_data)
        
        # 筛选器
        st.sidebar.divider()
        st.sidebar.subheader("🔥 爆款雷达设定")
        min_play = st.sidebar.slider("最小播放量 (万)", 0, 1000, 10, key="play_filter") * 10000
        
        filtered_df = all_df[all_df['播放量'] >= min_play]
        st.info(f"🔎 已为您发现 {len(filtered_df)} 条‘高曝光’视频。")

        # 核心指标看板
        st.subheader("📊 核心数据概览")
        cols = st.columns(len(selected_files))
        for i, f in enumerate(selected_files):
            name = f.replace('.csv', '').replace('_videos', '')
            stats = all_df[all_df['博主'] == name]
            
            if not stats.empty:
                avg_play = int(stats['播放量'].mean())
                avg_rate = stats['互动率'].mean()
                cols[i].metric(f"{name} 平均播放", f"{avg_play:,}")
                # 提示用户如果数值偏低是因为只有评论
                cols[i].metric(f"{name} 平均互动率", f"{avg_rate:.2f}%")
            else:
                cols[i].warning(f"⚠️ {name} 无数据")

        # 图表区
        st.subheader("🎯 筛选后的分布对比")
        if not filtered_df.empty:
            st.scatter_chart(data=filtered_df, x='总秒数', y='互动率', color='博主')
            
            st.subheader("📜 爆款视频明细")
            st.dataframe(filtered_df[['标题', '播放量', '互动率', '时长']], use_container_width=True)
            
            # 导出按钮
            st.sidebar.divider()
            if st.sidebar.button("📦 导出本次爆款报告"):
                output_path = r'M:\My_DS_Lab\output\hot_videos_report.csv'
                if not os.path.exists(r'M:\My_DS_Lab\output'):
                    os.makedirs(r'M:\My_DS_Lab\output')
                filtered_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                st.sidebar.success(f"✅ 报告已存入 U 盘：\n{output_path}")

            # AI 分析
            st.divider()
            st.header("🤖 AI 爆款剧本策略分析")
            
            top_5_titles = filtered_df.sort_values('播放量', ascending=False)['标题'].head(5).tolist()

            if st.button("✨ 召唤本地 DeepSeek 深度拆解"):
                if top_5_titles:
                    with st.spinner("RTX 4060 正在分析中，本次超时上限已调至 5 分钟，请耐心等待..."):
                        my_prompt = f"""
                        你是一位高级新媒体导演。基于以下爆款标题列表：
                        {top_5_titles}
                        请为我策划一个20分钟视频的脚本大纲。
                        要求：
                        1. 风格对标影视飓风，包含数据分析的硬核感。
                        2. 总结这几个标题的共同爆点逻辑。
                        """
                        result = call_ollama("deepseek-r1:7b", my_prompt)
                        st.markdown(result)
                else:
                    st.warning("⚠️ 筛选结果为空，无法分析。")
        else:
            st.warning("⚠️ 当前筛选条件下没有视频，请调低滑块。")
else:
    st.info("请在左侧选择 CSV 文件开始分析。")
