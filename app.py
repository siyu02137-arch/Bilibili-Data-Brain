import streamlit as st
import pandas as pd
import os
from engine_ai import AIEngine
from data_tool import DataTool

# 基础配置
st.set_page_config(page_title="B站数据大脑 V4.0", layout="wide")
ai = AIEngine()
tool = DataTool()

st.title("🎬 B站数据大脑 V4.0：真实情报版")

# 侧边栏
st.sidebar.header("🥊 选手控制台")
if os.path.exists(tool.data_dir):
    all_files = [f for f in os.listdir(tool.data_dir) if f.endswith('.csv')]
    selected_files = st.sidebar.multiselect("选择加载博主数据", all_files)
else:
    st.error("无法访问 M 盘！")
    selected_files = []

# 主程序
if selected_files:
    dfs = [tool.load_and_clean(f) for f in selected_files if tool.load_and_clean(f) is not None]
    if dfs:
        all_df = pd.concat(dfs)
        st.subheader("🔥 爆款雷达")
        min_play = st.slider("最低播放量 (万)", 0, 1000, 10) * 10000
        filtered_df = all_df[all_df['播放量'] >= min_play]

        if not filtered_df.empty:
            st.scatter_chart(data=filtered_df, x='标题', y='互动率')

            # --- Stage 4：真实评论侦察站 ---
            st.divider()
            st.subheader("📡 真实观众情报站")
            col_bv, col_btn = st.columns([3, 1])
            
            with col_bv:
                # 默认填入刚才分析出的第一名视频 BVID（如果有的话）
                bv_input = st.text_input("输入要侦察的视频 BVID", value="BV1Px411Z79n")
            
            with col_btn:
                st.write("") # 对齐
                st.write("")
                if st.button("🔍 抓取真实评论并分析"):
                    with st.spinner("正在黑进 B 站评论区..."):
                        real_comments = tool.fetch_real_comments(bv_input)
                        st.session_state['real_report'] = tool.analyze_sentiment(real_comments)
                        st.session_state['raw_comments'] = real_comments

            if 'real_report' in st.session_state:
                st.info(st.session_state['real_report'])
                with st.expander("查看原始评论"):
                    for c in st.session_state['raw_comments']:
                        st.write(f"- {c}")

            # 剧本生成（引用真实情报）
            st.divider()
            st.header("🤖 DeepSeek 剧本工坊")
            if st.button("🚀 启动 4060：基于真实情报生成脚本"):
                context = st.session_state.get('real_report', "暂无真实情报")
                prompt = f"参考真实观众反馈：{context}\n请为选题写一份能突破互动率瓶颈的脚本。"
                with st.spinner("正在进行深度逻辑推演..."):
                    res = ai.generate(prompt)
                    st.markdown(res)
