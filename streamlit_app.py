import streamlit as st
import moviepy.editor as mp
import os
import random
import tempfile
import urllib.request
import numpy as np
import textwrap
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
    st.info("🎙️ Video A (Nguồn lấy tiếng)")
    video_a_file = st.file_uploader("Tải video voice chủ đạo", type=["mp4", "mov"], key="a")

with col_right:
    st.info("🎞️ Video B (Nguồn lấy hình trám)")
    video_b_files = st.file_uploader("Tải các clip trám (Tối đa 10)", type=["mp4", "mov"], accept_multiple_files=True, key="b")

# ==========================================
# 2. CẤU HÌNH TEXT XUẤT HIỆN
# ==========================================
st.markdown("---")
st.header("✍️ Cấu hình Text xuất hiện (Dùng dấu | để chủ động xuống dòng nếu dùng Style 3)")

text_styles = {
    "1. Chữ Trắng - Nền Đỏ": "style_1",
    "2. Chữ Đỏ - Nền Trắng": "style_2",
    "3. [Đặc biệt] 2 Dòng (Dòng 1: Đỏ Nền Trắng / Dòng 2: Trắng Nền Đỏ)": "style_3"
}

texts_config = []
t_col1, t_col2, t_col3 = st.columns(3)

for i, col in enumerate([t_col1, t_col2, t_col3]):
    with col:
        with st.expander(f"Đoạn Chữ {i+1} (Để trống nếu không dùng)", expanded=True):
            content = st.text_input(f"Nội dung chữ {i+1}", placeholder="Dòng 1 | Dòng 2 (Nếu dùng Style 3)", key=f"c{i}")
            col_t1, col_t2 = st.columns(2)
            start_t = col_t1.number_input(f"Giây bắt đầu", min_value=0, value=i*5, key=f"s{i}")
            end_t = col_t2.number_input(f"Giây kết thúc", min_value=1, value=(i+1)*5, key=f"e{i}")
            style_name = st.selectbox(f"Kiểu dáng chữ", list(text_styles.keys()), key=f"st{i}")
            
            if content.strip():
                texts_config.append({
                    "content": content.strip(),
                    "start": start_t,
                    "end": end_t,
                    "style_type": text_styles[style_name]
                })

# ==========================================
# THUẬT TOÁN ĐO CHỮ, TỰ ĐỘNG THU NHỎ & NGẮT DÒNG CHỐNG MỒ CÔI (ÍT NHẤT 2 TỪ)
# ==========================================
def smart_wrap_text(draw, text, font_path, initial_font_size, max_width):
    current_size = initial_font_size
    font = ImageFont.truetype(font_path, current_size) if os.path.exists(font_path) else ImageFont.load_default()
    
    if len(text) > 30 and initial_font_size > 32:
        current_size = int(initial_font_size * 0.82)
        font = ImageFont.truetype(font_path, current_size)
    elif len(text) > 50 and initial_font_size > 32:
        current_size = int(initial_font_size * 0.70)
        font = ImageFont.truetype(font_path, current_size)

    if '|' not in text:
        try:
            # Đo kích thước ký tự linh hoạt hỗ trợ Pillow mới
            if hasattr(draw, 'textbbox'):
                char_w = draw.textbbox((0, 0), 'x', font=font)[2]
            else:
                char_w = draw.textsize('x', font=font)[0]
        except:
            char_w = current_size * 0.5
            
        chars_per_line = max(10, int(max_width / char_w))
        raw_lines = textwrap.wrap(text, width=chars_per_line)
    else:
        raw_lines = [line.strip() for line in text.split('|')]

    final_lines = [l for l in raw_lines if l.strip()]
        
    if len(final_lines) > 1 and '|' not in text:
        last_line_words = final_lines[-1].split()
        if len(last_line_words) == 1 and len(final_lines[-2].split()) > 1:
            prev_line_words = final_lines[-2].split()
            moved_word = prev_line_words.pop()
            final_lines[-2] = " ".join(prev_line_words)
            final_lines[-1] = moved_word + " " + final_lines[-1]

    final_lines = [l for l in final_lines if l.strip()]

    max_w = 0
    total_h = 0
    line_dims = []
    
    for line in final_lines:
        try:
            if hasattr(draw, 'textbbox'):
                bbox = draw.textbbox((0, 0), line, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            else:
                w, h = draw.textsize(line, font=font)
        except:
            w, h = current_size * len(line) * 0.6, current_size
        max_w = max(max_w, w)
        total_h += h
        line_dims.append((w, h))
        
    total_h += int(current_size * 0.15) * (len(final_lines) - 1)

    return max_w, total_h, list(zip(final_lines, line_dims)), font, current_size

# ==========================================
# HÀM XỬ LÝ VẼ CHỮ VÀO KHUNG HÌNH VIDEO
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
    
    initial_font_size = max(28, int(video_w * 0.055))
    max_text_width = int(video_w * 0.85) 
    base_y = int(video_h * 0.70) 
    
    text = active_text["content"]
    style = active_text["style_type"]
    pad_h = 25  
    pad_v = 15  

    if style in ["style_1", "style_2"]:
        max_w, total_h, wrapped_lines, font, current_size = smart_wrap_text(
            draw, text, FONT_PATH, initial_font_size, max_text_width
        )
        
        if not wrapped_lines:
            return frame
            
        bg_color = (220, 20, 60) if style == "style_1" else (255, 255, 255) 
        txt_color = (255, 255, 255) if style == "style_1" else (220, 20, 60) 
        
        rect_x1 = int((video_w - (max_w + pad_h * 2)) // 2)
        rect_y1 = int(base_y - (total_h // 2) - pad_v)
        rect_x2 = rect_x1 + max_w + pad_h * 2
        rect_y2 = rect_y1 + total_h + pad_v * 2
        
        draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=bg_color)
        
        current_y = rect_y1 + pad_v
        for line_text, (line_w, line_h) in wrapped_lines:
            line_x = int(rect_x1 + pad_h + (max_w - line_w) // 2)
            draw.text((line_x, current_y), line_text, fill=txt_color, font=font)
            current_y += line_h + int(current_size * 0.15)
        
    elif style == "style_3":
        if '|' in text:
            parts = text.split('|', 1)
            line1_raw = parts[0].strip()
            line2_raw = parts[1].strip()
        else:
            words = text.split()
            mid = len(words) // 2
            line1_raw = " ".join(words[:mid]) if mid > 0 else text
            line2_raw = " ".join(words[mid:]) if mid > 0 else ""
            
        max_w1, total_h1, lines1, font1, size1 = smart_wrap_text(draw, line1_raw, FONT_PATH, initial_font_size, max_text_width)
        max_w2, total_h2, lines2, font2, size2 = smart_wrap_text(draw, line2_raw, FONT_PATH, initial_font_size, max_text_width)
        
        block_gap = int(initial_font_size * 0.5)
        
        if lines1:
            rect1_x1 = int((video_w - (max_w1 + pad_h * 2)) // 2)
            rect1_y1 = int(base_y - total_h1 - block_gap)
            rect1_x2 = rect1_x1 + max_w1 + pad_h * 2
            rect1_y2 = rect1_y1 + total_h1 + pad_v * 2

            draw.rectangle([rect1_x1, rect1_y1, rect1_x2, rect1_y2], fill=(255, 255, 255))
            current_y = rect1_y1 + pad_v
            for line_text, (line_w, line_h) in lines1:
                line_x = int(rect1_x1 + pad_h + (max_w1 - line_w) // 2)
                draw.text((line_x, current_y), line_text, fill=(220, 20, 60), font=font1)
                current_y += line_h + int(size1 * 0.15)
            
        if lines2:
            rect2_x1 = int((video_w - (max_w2 + pad_h * 2)) // 2)
            rect2_y1 = int(base_y + block_gap)
            rect2_x2 = rect2_x1 + max_w2 + pad_h * 2
            rect2_y2 = rect2_y1 + total_h2 + pad_v * 2

            draw.rectangle([rect2_x1, rect2_y1, rect2_x2, rect2_y2], fill=(220, 20, 60))
            current_y = rect2_y1 + pad_v
            for line_text, (line_w, line_h) in lines2:
                line_x = int(rect2_x1 + pad_h + (max_w2 - line_w) // 2)
                draw.text((line_x, current_y), line_text, fill=(255, 255, 255), font=font2)
                current_y += line_h + int(size2 * 0.15)
            
    return np.array(img)

# ==========================================
# HÀM FIX LỖI ANTIALIAS: THU PHÓNG BẰNG PILLOW MỚI
# ==========================================
def resize_frame_safe(frame, target_w, target_h):
    # Chuyển đổi khung hình sang dạng ảnh để dùng bộ lọc Resampling.LANCZOS chuẩn mới
    img = Image.fromarray(frame)
    img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return np.array(img_resized)

# ==========================================
# 3. LUỒNG XỬ LÝ CHÍNH & KÉO THẢ VIDEO FULL KHUNG
# ==========================================
def save_temp(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(file.getvalue())
        return tmp.name

st.markdown("---")
if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True):
    if not video_a_file or not video_b_files:
        st.error("Vui lòng tải lên đầy đủ Video A và các clip Video B!")
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

            status_text.text("🎞️ Bước 3: AI đang ép khung chiếm trọn 100% màn hình kích thước 9:16...")
            b_clips = []
            current_d = 0
            
            loaded_b_clips = [mp.VideoFileClip(p).without_audio() for p in paths_b]
            
            # KÍCH THƯỚC ĐỨNG 9:16 CỐ ĐỊNH (FULL HD VERTICAL)
            target_w = 1080
            target_h = 1920
            target_ratio = target_w / target_h
            
            while current_d < duration_limit:
                random.shuffle(loaded_b_clips)
                for c_b in loaded_b_clips:
                    if current_d >= duration_limit: 
                        break
                    
                    cut_d = random.uniform(5, 12)
                    st_cut = random.uniform(0, max(0, c_b.duration - cut_d))
                    sub = c_b.subclip(st_cut, min(st_cut + cut_d, c_b.duration))
                    
                    # THUẬT TOÁN TỰ ĐỘNG CẮT CÂN TÂM (CROP)
                    clip_ratio = sub.w / sub.h
                    if clip_ratio > target_ratio:
                        new_w = sub.h * target_ratio
                        sub = sub.crop(x1=(sub.w - new_w)/2, y1=0, width=new_w, height=sub.h)
                    elif clip_ratio < target_ratio:
                        new_h = sub.w / target_ratio
                        sub = sub.crop(x1=0, y1=(sub.h - new_h)/2, width=sub.w, height=new_h)
                    
                    # SỬA LỖI TẠI ĐÂY: Dùng hàm fl_image kết hợp Pillow Resampling để không gọi ANTIALIAS
                    sub = sub.fl_image(lambda frame: resize_frame_safe(frame, target_w, target_h))
                    
                    b_clips.append(sub)
                    current_d += sub.duration
            
            final_visual = mp.concatenate_videoclips(b_clips, method="compose").set_duration(duration_limit)
            final_video = final_visual.set_audio(audio_main)
            progress_bar.progress(60)

            status_text.text("✍️ Bước 4: Đang đồng bộ hóa chèn chữ Tiếng Việt vào vùng an toàn...")
            if texts_config:
                final_video = final_video.fl(process_text_frame)
            progress_bar.progress(80)

            status_text.text("⏳ Bước 5: Đang đóng gói xuất video chất lượng cao...")
            out_p = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            final_video.write_videofile(out_p, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", logger=None)
            
            for c in loaded_b_clips: 
                c.close()
            clip_a.close()
            
            progress_bar.progress(100)
            status_text.text("✅ Hoàn thành!")
            
            st.success("🎉 Video KOC chuẩn dọc 9:16 của bạn đã sẵn sàng!")
            st.video(out_p)
            
            with open(out_p, "rb") as f:
                st.download_button("⬇️ TẢI VIDEO XUỐNG", f, "koc_final.mp4", "video/mp4", use_container_width=True)

        except Exception as e:
            st.error(f"Lỗi hệ thống: {e}")