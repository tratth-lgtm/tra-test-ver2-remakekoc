import streamlit as st
import moviepy.editor as mp
import os
import random
import tempfile
import urllib.request
import numpy as np
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
# 2. CẤU HÌNH TEXT MỚI (LỰA CHỌN LINH HOẠT)
# ==========================================
st.markdown("---")
st.header("✍️ Cấu hình Text xuất hiện (Không bắt buộc điền hết cả 3)")

# Định nghĩa các style màu sắc theo yêu cầu mới
text_styles = {
    "1. Chữ Trắng - Nền Đỏ": "style_1",
    "2. Chữ Đỏ - Nền Trắng": "style_2",
    "3. [Đặc biệt] 2 Dòng (Dòng 1: Trắng Nền Đỏ / Dòng 2: Đỏ Nền Trắng)": "style_3"
}

texts_config = []
t_col1, t_col2, t_col3 = st.columns(3)

for i, col in enumerate([t_col1, t_col2, t_col3]):
    with col:
        with st.expander(f"Đoạn Text {i+1} (Để trống nếu không dùng)", expanded=True):
            content = st.text_input(f"Nội dung Text {i+1}", key=f"c{i}")
            col_t1, col_t2 = st.columns(2)
            start_t = col_t1.number_input(f"Giây bắt đầu", min_value=0, value=i*5, key=f"s{i}")
            end_t = col_t2.number_input(f"Giây kết thúc", min_value=1, value=(i+1)*5, key=f"e{i}")
            style_name = st.selectbox(f"Kiểu dáng", list(text_styles.keys()), key=f"st{i}")
            
            # Chỉ thêm vào cấu hình xử lý nếu ô nhập nội dung có chữ
            if content.strip():
                texts_config.append({
                    "content": content.strip(),
                    "start": start_t,
                    "end": end_t,
                    "style_type": text_styles[style_name]
                })

# ==========================================
# HÀM XỬ LÝ VẼ CHỮ 1 DÒNG & 2 DÒNG AN TOÀN
# ==========================================
def process_text_frame(get_frame, t):
    frame = get_frame(t)
    
    active_text = None
    for txt in texts_config:
        if txt["start"] <= t <= txt["end"]:
            active_text = txt
            break
            
    if not active_text:
        return frame
        
    video_h, video_w, _ = frame.shape
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    
    # Tính toán cỡ chữ tỷ lệ theo độ rộng video
    font_size = max(18, int(video_w * 0.042))
    font = ImageFont.truetype(FONT_PATH, font_size) if os.path.exists(FONT_PATH) else ImageFont.load_default()
    
    text = active_text["content"]
    style = active_text["style_type"]
    pad = 12  # Độ rộng lề của khối nền chữ nhật
    
    # Tọa độ Y cơ sở (đặt khối chữ ở phần dưới màn hình video)
    base_y = int(video_h * 0.75)
    
    # ------------------------------------------
    # XỬ LÝ STYLE 1 HOẶC STYLE 2 (1 DÒNG)
    # ------------------------------------------
    if style in ["style_1", "style_2"]:
        text_w = draw.textlength(text, font=font) if hasattr(draw, 'textlength') else font_size * len(text) * 0.6
        text_h = font_size
        
        x = int((video_w - text_w) // 2)
        y = base_y
        
        bg_color = (255, 0, 0) if style == "style_1" else (255, 255, 255)
        txt_color = (255, 255, 255) if style == "style_1" else (255, 0, 0)
        
        # Vẽ nền và đè chữ lên
        draw.rectangle([x - pad, y - pad, x + text_w + pad, y + text_h + pad], fill=bg_color)
        draw.text((x, y - 2), text, fill=txt_color, font=font)
        
    # ------------------------------------------
    # XỬ LÝ STYLE 3 (2 DÒNG KHÁC NHAU)
    # ------------------------------------------
    elif style == "style_3":
        # Tự động cắt đôi chuỗi chữ dựa trên khoảng trắng ở giữa để chia làm 2 dòng bằng nhau
        words = text.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid]) if mid > 0 else text
        line2 = " ".join(words[mid:]) if mid > 0 else ""
        
        # Tính toán kích thước dòng 1
        w1 = draw.textlength(line1, font=font) if hasattr(draw, 'textlength') else font_size * len(line1) * 0.6
        x1 = int((video_w - w1) // 2)
        y1 = base_y - font_size - (pad * 2)  # Dòng 1 đẩy lên trên
        
        # Vẽ Dòng 1: Chữ Trắng - Nền Đỏ
        draw.rectangle([x1 - pad, y1 - pad, x1 + w1 + pad, y1 + font_size + pad], fill=(255, 0, 0))
        draw.text((x1, y1 - 2), line1, fill=(255, 255, 255), font=font)
        
        # Vẽ Dòng 2 (Nếu có): Chữ Đỏ - Nền Trắng
        if line2:
            w2 = draw.textlength(line2, font=font) if hasattr(draw, 'textlength') else font_size * len(line2) * 0.6
            x2 = int((video_w - w2) // 2)
            y2 = base_y + pad
            
            draw.rectangle([x2 - pad, y2 - pad, x2 + w2 + pad, y2 + font_size + pad], fill=(255, 255, 255))
            draw.text((x2, y2 - 2), line2, fill=(255, 0, 0), font=font)
            
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

            status_text.text("🎞️ Bước 3: AI đang cắt ghép hình trám B khớp độ dài...")
            b_clips = []
            current_d = 0
            
            loaded_b_clips = [mp.VideoFileClip(p).without_audio() for p in paths_b]
            
            while current_d < duration_limit:
                random.shuffle(loaded_b_clips)
                for c_b in loaded_b_clips:
                    if current_d >= duration_limit: break
                    
                    cut_d = random.uniform(5, 12)
                    start_cut = random.uniform(0, max(0, c_b.duration - cut_d))
                    sub = c_b.subclip(start_cut, min(start_cut + cut_d, c_b.duration))
                    
                    b_clips.append(sub)
                    current_d += sub.duration
            
            final_visual = mp.concatenate_videoclips(b_clips, method="compose").set_duration(duration_limit)
            final_video = final_visual.set_audio(audio_main)
            progress_bar.progress(60)

            status_text.text("✍️ Bước 4: Đang đồng bộ hóa chèn Text Tiếng Việt nâng cao...")
            if texts_config:
                final_video = final_video.fl(process_text_frame)
            progress_bar.progress(80)

            status_text.text("⏳ Bước 5: Đang đóng gói xuất video (Có thể mất 1-2 phút)...")
            out_p = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            final_video.write_videofile(out_p, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
            
            for c in loaded_b_clips: c.close()
            clip_a.close()
            
            progress_bar.progress(100)
            status_text.text("✅ Hoàn thành!")
            
            st.success("🎉 Video của bạn đã sẵn sàng!")
            st.video(out_p)
            
            with open(out_p, "rb") as f:
                st.download_button("⬇️ TẢI VIDEO XUỐNG", f, "koc_final.mp4", "video/mp4", use_container_width=True)

        except Exception as e:
            st.error(f"Lỗi hệ thống: {e}")