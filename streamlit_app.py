import streamlit as st
import moviepy.editor as mp
import os
import random
import tempfile
import urllib.request
import numpy as np  # <-- DÒNG NÀY ĐÃ ĐƯỢC THÊM ĐỂ FIX LỖI 'np'
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. TỰ ĐỘNG TẢI FONT CHỮ TIẾNG VIỆT DỰ PHÒNG
# ==========================================
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
FONT_PATH = "Roboto-Bold.ttf"

@st.cache_resource
def load_vietnamese_font():
    if not os.path.exists(FONT_PATH):
        try:
            # Thiết lập timeout để nếu mạng lỗi không bị treo web
            urllib.request.urlretrieve(FONT_URL, FONT_PATH, timeout=10)
        except:
            pass
load_vietnamese_font()

# ==========================================
# GIAO DIỆN WEB (CHIA 2 CỘT NGANG NHAU)
# ==========================================
st.set_page_config(page_title="Tool KOC LazyChef", layout="wide")
st.title("🎬 AI Video KOC Editor")
st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.info("🎙️ Video A (Lấy Tiếng)")
    video_a_file = st.file_uploader("Tải video voice chủ đạo", type=["mp4", "mov"], key="a")

with col_right:
    st.info("🎞️ Video B (Lấy Hình Trám)")
    video_b_files = st.file_uploader("Tải các clip trám (Max 10)", type=["mp4", "mov"], accept_multiple_files=True, key="b")

# ==========================================
# 2. CẤU HÌNH TEXT (3 LẦN - 4 OPTION)
# ==========================================
st.markdown("---")
st.header("✍️ Cấu hình Text xuất hiện")

text_styles = {
    "1. Chữ Trắng - Nền Xanh Lá": {"text_color": (255, 255, 255), "bg_color": (0, 128, 0)},
    "2. Chữ Trắng - Nền Đỏ": {"text_color": (255, 255, 255), "bg_color": (255, 0, 0)},
    "3. Chữ Đen - Nền Vàng": {"text_color": (0, 0, 0), "bg_color": (255, 255, 0)},
    "4. Chữ Đen - Nền Trắng": {"text_color": (0, 0, 0), "bg_color": (255, 255, 255)}
}

texts_config = []
t_col1, t_col2, t_col3 = st.columns(3)

for i, col in enumerate([t_col1, t_col2, t_col3]):
    with col:
        with st.expander(f"Đoạn Text {i+1}", expanded=True):
            content = st.text_input(f"Nội dung {i+1}", key=f"c{i}")
            col_t1, col_t2 = st.columns(2)
            start_t = col_t1.number_input(f"Giây bắt đầu", min_value=0, value=i*5, key=f"s{i}")
            end_t = col_t2.number_input(f"Giây kết thúc", min_value=1, value=(i+1)*5, key=f"e{i}")
            style_name = st.selectbox(f"Kiểu dáng", list(text_styles.keys()), key=f"st{i}")
            if content:
                texts_config.append({
                    "content": content, "start": start_t, "end": end_t, "style": text_styles[style_name]
                })

# ==========================================
# HÀM XỬ LÝ VẼ CHỮ AN TOÀN (KHÔNG LO CRASH)
# ==========================================
def make_text_frame(gf, t, text_list, video_w, video_h):
    frame = gf(t)
    
    active_text = None
    for txt in text_list:
        if txt["start"] <= t <= txt["end"]:
            active_text = txt
            break
            
    if not active_text:
        return frame
        
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    
    font_size = max(20, int(video_w * 0.045)) # Tính toán kích thước chữ theo khung hình
    
    font = None
    if os.path.exists(FONT_PATH) and os.path.getsize(FONT_PATH) > 0:
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
        
    text = active_text["content"]
    
    # Đo kích thước chữ để tạo khung nền đổ bóng ôm sát chữ
    if hasattr(draw, 'textbbox'):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    else:
        text_w = draw.textlength(text, font=font)
        text_h = font_size

    # Vị trí đặt chữ (Chính giữa bên dưới màn hình KOC)
    x = int((video_w - text_w) // 2)
    y = int(video_h * 0.8)
    
    # Vẽ hộp nền màu
    pad = 12
    draw.rectangle([x - pad, y - pad, x + text_w + pad, y + text_h + pad], fill=active_text["style"]["bg_color"])
    
    # Đè chữ lên nền
    draw.text((x, y - 2), text, fill=active_text["style"]["text_color"], font=font)
    
    return np.array(img)

# ==========================================
# 3. LUỒNG XỬ LÝ AI & LOADING TIẾN TRÌNH
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Bước 1: Đang nạp dữ liệu video từ máy...")
            path_a = save_temp(video_a_file)
            paths_b = [save_temp(f) for f in video_b_files]
            progress_bar.progress(20)

            status_text.text("🎙️ Bước 2: Đang tách giọng độc lập từ Video A...")
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

            status_text.text("✍️ Bước 4: Đang đồng bộ hóa chèn Text Tiếng Việt...")
            if texts_config:
                final_video = final_video.fl_image(
                    lambda gf, t: make_text_frame(gf, t, texts_config, final_video.w, final_video.h), 
                    keep_duration=True
                )
            progress_bar.progress(80)

            status_text.text("⏳ Bước 5: Đang đóng gói xuất video (Có thể mất 1-2 phút)...")
            out_p = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            final_video.write_videofile(out_p, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
            
            progress_bar.progress(100)
            status_text.text("✅ Hoàn thành!")
            
            st.success("🎉 Video của bạn đã sẵn sàng!")
            st.video(out_p)
            
            with open(out_p, "rb") as f:
                st.download_button("⬇️ TẢI VIDEO XUỐNG", f, "koc_final.mp4", "video/mp4", use_container_width=True)

        except Exception as e:
            st.error(f"Lỗi hệ thống: {e}")