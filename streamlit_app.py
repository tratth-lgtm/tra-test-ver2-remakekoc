import streamlit as st
import moviepy.editor as mp
from moviepy.config import change_settings
import os
import random
import tempfile
import urllib.request

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG (SỬA LỖI IMAGEMAGICK)
# ==========================================
# Đường dẫn chuẩn của ImageMagick trên Streamlit Cloud
IM_PATH = "/usr/bin/convert"
change_settings({"IMAGEMAGICK_BINARY": IM_PATH})

# Tự động tải Font Roboto-Bold để gõ Tiếng Việt không lỗi
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
FONT_PATH = "Roboto-Bold.ttf"

@st.cache_resource
def load_vietnamese_font():
    if not os.path.exists(FONT_PATH):
        try:
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        except:
            pass
load_vietnamese_font()

# ==========================================
# 2. GIAO DIỆN WEB (CHIA CỘT)
# ==========================================
st.set_page_config(page_title="Tool KOC LazyChef", layout="wide")
st.title("🎬 AI Video KOC Editor")
st.markdown("---")

# CHIA 2 CỘT NGANG NHAU
col_left, col_right = st.columns(2)

with col_left:
    st.header("🎙️ Video A (Lấy Tiếng)")
    video_a_file = st.file_uploader("Tải video voice chủ đạo", type=["mp4", "mov"], key="a")

with col_right:
    st.header("🎞️ Video B (Lấy Hình Trám)")
    video_b_files = st.file_uploader("Tải các clip trám (Max 10)", type=["mp4", "mov"], accept_multiple_files=True, key="b")

# ==========================================
# 3. CẤU HÌNH TEXT (3 LẦN - 5 OPTION)
# ==========================================
st.markdown("---")
st.header("✍️ Cấu hình Text xuất hiện")

text_styles = {
    "Trắng - Viền Xanh Dương": {"color": "white", "stroke": "blue", "bg": None},
    "Đỏ - Viền Trắng": {"color": "red", "stroke": "white", "bg": None},
    "Trắng - Nền Xanh Lá": {"color": "white", "stroke": None, "bg": "green"},
    "Trắng - Nền Đỏ": {"color": "white", "stroke": None, "bg": "red"},
    "Vàng - Viền Đen": {"color": "yellow", "stroke": "black", "bg": None}
}

texts_config = []
t_col1, t_col2, t_col3 = st.columns(3)

for i, col in enumerate([t_col1, t_col2, t_col3]):
    with col:
        with st.expander(f"Đoạn Text {i+1}", expanded=True):
            content = st.text_input(f"Nội dung {i+1}", key=f"c{i}")
            start_t = st.number_input(f"Giây bắt đầu", min_value=0, value=i*5, key=f"s{i}")
            end_t = st.number_input(f"Giây kết thúc", min_value=1, value=(i+1)*5, key=f"e{i}")
            style_name = st.selectbox(f"Kiểu dáng", list(text_styles.keys()), key=f"st{i}")
            if content:
                texts_config.append({
                    "content": content, "start": start_t, "end": end_t, "style": text_styles[style_name]
                })

# ==========================================
# 4. XỬ LÝ AI & LOADING
# ==========================================
def save_temp(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(file.getvalue())
        return tmp.name

st.markdown("---")
if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True):
    if not video_a_file or not video_b_files:
        st.error("Vui lòng tải đủ Video A và Video B!")
    else:
        # Vòng tròn loading
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Bước 1: Đang nạp dữ liệu video...")
            path_a = save_temp(video_a_file)
            paths_b = [save_temp(f) for f in video_b_files]
            progress_bar.progress(20)

            status_text.text("🎙️ Bước 2: Đang tách giọng từ Video A...")
            clip_a = mp.VideoFileClip(path_a)
            audio_main = clip_a.audio
            duration_limit = audio_main.duration
            progress_bar.progress(40)

            status_text.text("🎞️ Bước 3: AI đang cắt ghép hình trám B...")
            b_clips = []
            current_d = 0
            while current_d < duration_limit:
                random.shuffle(paths_b)
                for p in paths_b:
                    if current_d >= duration_limit: break
                    c_b = mp.VideoFileClip(p)
                    cut_d = random.uniform(10, 15)
                    start_cut = random.uniform(0, max(0, c_b.duration - cut_d))
                    sub = c_b.subclip(start_cut, min(start_cut + cut_d, c_b.duration)).without_audio()
                    b_clips.append(sub)
                    current_d += sub.duration
            
            final_visual = mp.concatenate_videoclips(b_clips, method="compose").set_duration(duration_limit)
            final_video = final_visual.set_audio(audio_main)
            progress_bar.progress(60)

            status_text.text("✍️ Bước 4: Đang chèn Text Tiếng Việt...")
            layers = [final_video]
            for t in texts_config:
                txt = mp.TextClip(
                    t["content"], fontsize=60, color=t["style"]["color"],
                    font=FONT_PATH, stroke_color=t["style"]["stroke"],
                    stroke_width=2 if t["style"]["stroke"] else 0,
                    bg_color=t["style"]["bg"], method='caption', size=(final_video.w*0.8, None)
                ).set_start(t["start"]).set_end(min(t["end"], duration_limit)).set_position('center')
                layers.append(txt)
            
            result_video = mp.CompositeVideoClip(layers)
            progress_bar.progress(80)

            status_text.text("⏳ Bước 5: Đang xuất video thành phẩm (Có thể mất 1-2 phút)...")
            out_p = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            result_video.write_videofile(out_p, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
            
            progress_bar.progress(100)
            status_text.text("✅ Hoàn thành!")
            
            st.success("🎉 Video của bạn đã sẵn sàng!")
            st.video(out_p)
            
            with open(out_p, "rb") as f:
                st.download_button("⬇️ TẢI VIDEO XUỐNG", f, "koc_final.mp4", "video/mp4", use_container_width=True)

        except Exception as e:
            st.error(f"Lỗi AI: {e}")