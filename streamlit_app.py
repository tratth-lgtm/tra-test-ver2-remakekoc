import streamlit as st
import moviepy.editor as mp
import os
import random

# Cấu hình trang ứng dụng
st.set_page_config(page_title="Tool Cắt Ghép Video KOC", layout="centered")

st.title("🎬 Tool Cắt Ghép Video KOC Tự Động")
st.subheader("Dành cho Marketing - Tối giản thao tác")

st.markdown("---")

# ==========================================
# STEP 1: UPLOAD VIDEO
# ==========================================
st.header("1. Tải lên Video Source")

# Upload Video A (Lấy Voice)
video_a_file = st.file_uploader("Chọn Video A (Sử dụng VOICE của video này)", type=["mp4", "mov", "avi"])

# Upload Video B (Lấy Hình, tối đa 10 clip)
video_b_files = st.file_uploader(
    "Chọn các Video B (Lấy HÌNH, tối đa 10 clips. Mỗi clip tự động lấy ngẫu nhiên 10-15s)", 
    type=["mp4", "mov", "avi"], 
    accept_multiple_files=True
)

if video_b_files and len(video_b_files) > 10:
    st.warning("⚠️ Bạn đã chọn quá 10 video. Hệ thống sẽ chỉ xử lý 10 video đầu tiên.")
    video_b_files = video_b_files[:10]

# ==========================================
# STEP 2: CHỌN ĐỊNH DẠNG TEXT (5 OPTIONS)
# ==========================================
st.header("2. Cấu hình Subtitle / Text")
text_input = st.text_input("Nhập nội dung chữ muốn chèn lên video:", placeholder="Ví dụ: Giảm giá sốc 50%!")

# 5 Option thiết kế theo yêu cầu
style_options = {
    "Option 1: Chữ Trắng - Bold Xanh Dương": {"color": "white", "bg_color": "blue"},
    "Option 2: Chữ Đỏ - Bold Trắng": {"color": "red", "bg_color": "white"},
    "Option 3: Chữ Trắng - Nền Xanh Lá": {"color": "white", "bg_color": "green"},
    "Option 4: Chữ Trắng - Nền Đỏ": {"color": "white", "bg_color": "red"},
    "Option 5: Chữ Vàng - Nền Đen (Bonus)": {"color": "yellow", "bg_color": "black"}
}

selected_style_name = st.selectbox("Chọn kiểu hiển thị chữ:", list(style_options.keys()))
style_config = style_options[selected_style_name]

st.markdown("---")

# ==========================================
# STEP 3 & 4: XỬ LÝ VIDEO & TIẾN ĐỘ
# ==========================================
if st.button("🚀 BẮT ĐẦU XỬ LÝ VIDEO", type="primary"):
    
    if not video_a_file or not video_b_files:
        st.error("❌ Vui lòng upload đầy đủ Video A và ít nhất 1 Video B!")
    else:
        # Tạo vòng tròn tiến độ (Progress bar)
        progress_text = "Đang xử lý video... Vui lòng đợi trong giây lát."
        my_bar = st.progress(0, text=progress_text)
        
        try:
            # Lưu tạm file upload ra ổ đĩa
            with open("temp_a.mp4", "wb") as f:
                f.write(video_a_file.read())
            
            my_bar.progress(10, text="Đang trích xuất âm thanh từ Video A...")
            video_a = mp.VideoFileClip("temp_a.mp4")
            audio_a = video_a.audio
            
            my_bar.progress(30, text="Đang cắt và ghép các Video B...")
            
            b_clips = []
            for idx, b_file in enumerate(video_b_files):
                temp_b_path = f"temp_b_{idx}.mp4"
                with open(temp_b_path, "wb") as f:
                    f.write(b_file.read())
                
                clip_b = mp.VideoFileClip(temp_b_path)
                
                # Logic: Lấy ngẫu nhiên thời gian từ 10-15s
                duration_to_cut = random.randint(10, 15)
                if clip_b.duration > duration_to_cut:
                    start_time = random.uniform(0, clip_b.duration - duration_to_cut)
                    clip_b = clip_b.subclip(start_time, start_time + duration_to_cut)
                
                b_clips.append(clip_b)
            
            # Ghép nối các đoạn clip B
            final_video_brut = mp.concatenate_videoclips(b_clips, method="compose")
            
            my_bar.progress(60, text="Đang mix âm thanh và hình ảnh...")
            final_video_with_audio = final_video_brut.set_audio(audio_a.set_duration(final_video_brut.duration))
            
            my_bar.progress(80, text="Đang chèn chữ và Render...")
            
            if text_input:
                txt_clip = mp.TextClip(
                    text_input, 
                    fontsize=40, 
                    color=style_config["color"], 
                    bg_color=style_config["bg_color"],
                    font="Courier"  # Sử dụng font tiêu chuẩn để tránh lỗi hệ thống Cloud
                )
                txt_clip = txt_clip.set_pos(('center', 'bottom')).set_duration(final_video_with_audio.duration)
                final_output = mp.CompositeVideoClip([final_video_with_audio, txt_clip])
            else:
                final_output = final_video_with_audio

            # Xuất video thành phẩm
            output_filename = "video_thanh_pham_koc.mp4"
            final_output.write_videofile(output_filename, codec="libx264", audio_codec="aac")
            
            my_bar.progress(100, text="Hoàn thành xuất sắc!")
            st.success("🎉 Video của bạn đã sẵn sàng!")
            
            # ==========================================
            # STEP 5 & 6: HIỂN THỊ VIDEO & NÚT DOWNLOAD
            # ==========================================
            st.header("3. Kết quả & Tải về")
            st.video(output_filename)
            
            with open(output_filename, "rb") as file:
                st.download_button(
                    label="📥 TẢI VIDEO VỀ MÁY",
                    data=file,
                    file_name="KOC_Final_Video.mp4",
                    mime="video/mp4"
                )
                
            # Dọn dẹp file tạm
            video_a.close()
            for c in b_clips: c.close()
            if os.path.exists("temp_a.mp4"): os.remove("temp_a.mp4")
            for idx in range(len(video_b_files)):
                if os.path.exists(f"temp_b_{idx}.mp4"): os.remove(f"temp_b_{idx}.mp4")

        except Exception as e:
            st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")