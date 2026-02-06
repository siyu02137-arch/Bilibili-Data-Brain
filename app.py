import streamlit as st
import pandas as pd
import os
import requests
import re
import datetime

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(page_title="B站内容决策看板 V2.0", layout="wide")
st.title("🎬 B站数据大脑 V2.0：RTX 4060 算力增强版")

# --- V2.0 新增：去 AI 化的人设指令 ---
SYSTEM_PROMPT = """
你现在是一个硬核 B 站内容架构师。你的合作伙伴是一名身高 180cm、主修数据科学的大学生。
写作限制：
1. 绝对禁止使用：'在这个数字化时代'、'总之'、'综上所述'、'不仅...而且'等典型 AI 套话。
2. 语气风格：极客、冷幽默、专业、直给。
3. 术语要求：必须穿插数据科学专业词汇（如：维度拆解、异常值、权重、样本量），显得很内行。
4. 视角：保持 180cm 的第一人称视角，不要有说教感。
"""

# --- 核心工具函数 ---
def call_ollama(model_name, prompt):
    url = "http://localhost:11434/api/generate"
    full_prompt = f"{SYSTEM_PROMPT}\n\n任务内容：\n{prompt}"
    
    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "stream": False
    }
    try:
        response = requests.post(url, json=payload, timeout=300)
        return response.json().get('response', "AI 思考超时，未返回结果...")
    except requests.exceptions.ReadTimeout:
        return "❌ RTX 4060 显存高负载，思考超时 (超过5分钟)。"
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

    if not v_col: return None

    df['播放量'] = df[v_col].apply(clean_num)
    likes = df[l_col].apply(clean_num) if l_col else 0
    comms = df[c_col].apply(clean_num) if c_col else 0
    
    df['互动率'] = ((likes + comms) / df['播放量'].replace(0, 1)) * 100
    df['总秒数'] = df[d_col].apply(convert_time) if d_col else 0
    df['标题'] = df[t_col] if t_col else "未知标题"
    
    return df

# ==========================================
# 2. 侧边栏
# ==========================================
st.sidebar.header("🥊 擂台控制台")
data_dir = r'M:\My_DS_Lab\data'

if os.path.exists(data_dir):
    all_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    selected_files = st.sidebar.multiselect("选择对比博主", all_files, default=all_files[:2] if len(all_files)>=2 else all_files)
else:
    st.error("无法访问 M 盘，请确认 U 盘已插入！")
    selected_files = []

st.sidebar.divider()
st.sidebar.subheader("🧠 创作上下文")
default_insight = "发现长视频的互动率普遍偏低（约0.15%），需要开头设置强悬念。"
user_insight = st.sidebar.text_area("输入数据洞察", default_insight, height=100)

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
        
        # --- 补全：爆款雷达与数据指标 ---
        st.subheader("🔥 爆款雷达")
        min_play = st.slider("最小播放量 (万)", 0, 1000, 10) * 10000
        filtered_df = all_df[all_df['播放量'] >= min_play]
        
        cols = st.columns(len(selected_files))
        for i, f in enumerate(selected_files):
            name = f.replace('.csv', '').replace('_videos', '')
            stats = all_df[all_df['博主'] == name]
            if not stats.empty:
                cols[i].metric(f"{name} 平均播放", f"{int(stats['播放量'].mean()):,}")
                cols[i].metric(f"{name} 互动率", f"{stats['互动率'].mean():.2f}%")

        if not filtered_df.empty:
            st.scatter_chart(data=filtered_df, x='总秒数', y='互动率', color='博主')
            
            # --- V2.1 词频挖掘机 ---
            st.divider()
            st.subheader("🔍 爆款标题流量密码")
            all_titles = " ".join(filtered_df['标题'].astype(str).tolist())
            found_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_titles)
            
            if found_words:
                from collections import Counter
                stop_words = ['视频', '我们', '一个', '这个', '什么']
                valid_words = [w for w in found_words if w not in stop_words]
                common_tags = Counter(valid_words).most_common(12)
                tag_cols = st.columns(6)
                for idx, (word, count) in enumerate(common_tags):
                    tag_cols[idx % 6].button(f"{word}\n({count})", key=f"btn_{word}")
            else:
                st.info("💡 正在等待更多数据以开启词频分析...")

            # --- Stage 2: DeepSeek 剧本工坊 ---
            st.divider()
            st.header("🤖 Stage 2: DeepSeek 剧本工坊")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                top_title = filtered_df.sort_values('播放量', ascending=False).iloc[0]['标题']
                target_topic = st.text_input("想拍什么主题？", value=f"对标爆款：{top_title}")
            with col2:
                st.write("")
                st.write("")
                start_btn = st.button("🚀 启动 4060 生成剧本", use_container_width=True)

            if start_btn:
                with st.spinner("DeepSeek-R1 正在推导中..."):
                    script_prompt = f"基于洞察：{user_insight}\n视频主题：{target_topic}\n请产出【分镜级】剧本大纲。"
                    result = call_ollama("deepseek-r1:7b", script_prompt)
                    st.session_state['generated_script'] = result
                    st.session_state['script_topic'] = target_topic

            if 'generated_script' in st.session_state:
                st.markdown("### 📝 剧本预览")
                st.markdown(st.session_state['generated_script'])
                
                # 自动保存备份逻辑
                script_content = st.session_state['generated_script']
                script_name = f"Script_{st.session_state.get('script_topic', 'idea')[:10]}.md"
                save_path = os.path.join(r'M:\My_DS_Lab\scripts', script_name)
                
                try:
                    if not os.path.exists(r'M:\My_DS_Lab\scripts'): os.makedirs(r'M:\My_DS_Lab\scripts')
                    with open(save_path, "w", encoding="utf-8") as f: f.write(script_content)
                    st.sidebar.success(f"📂 已备份至：{save_path}")
                except: pass

                st.download_button("📥 点击下载剧本", data=script_content, file_name=script_name)
        else:
            st.warning("⚠️ 筛选结果为空，请调低播放量滑块。")
else:
    st.info("👈 请在左侧选择博主数据开始分析")
