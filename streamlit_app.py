import streamlit as st
import moviepy.editor as mp
import os
import random
import tempfile

# Cấu hình trang (Marketing friendly)
st.set_page_config(page_title="Tool Cắt Ghép Video KOC", layout="centered")
st.title("🎬 Tool Cắt Ghép Video KOC Tự Động")
st.subheader("Dành cho Marketing - Tối giản thao tác")
st.markdown("---")

# Hàm hỗ trợ lưu file tạm
def save_uploaded_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name
    except Exception as e:
        return None

# ==========================================
# STEP 1: UPLOAD VIDEO & CẤU HÌNH
# ==========================================
st.header("1. Tải lên Video Source")

# Upload Video A
video_a_file = st.file_uploader("Chọn Video A (Chỉ lấy VOICE từ video này)", type=["mp4", "mov"])

# Upload Video B
video_b_files = st.file_uploader(
    "Chọn các Video B (Lấy HÌNH, tối đa 10 clips. Tự động cắt 10-15s/clip)", 
    type=["mp4", "mov"], accept_multiple_files=True
)

st.header("2. Tùy chọn chèn Text")
text_content = st.text_input("Nhập nội dung Text muốn chèn (Để trống nếu không cần):", "")

# 5 Options Text
text_options = {
    "1. Chữ trắng viền xanh lá": {"color": "white", "stroke_color": "green", "bg_color": "transparent"},
    "2. Chữ đỏ viền trắng": {"color": "red", "stroke_color": "white", "bg_color": "transparent"},
    "3. Chữ trắng nền xanh lá": {"color": "white", "stroke_color": None, "bg_color": "green"},
    "4. Chữ trắng nền đỏ": {"color": "white", "stroke_color": None, "bg_color": "red"},
    "5. Chữ đen nền trắng": {"color": "black", "stroke_color": None, "bg_color": "white"} # Option bổ sung cho đủ 5
}
selected_text_style = st.selectbox("Chọn style chữ (Font: Montserrat mặc định):", list(text_options.keys()))

# ==========================================
# STEP 2: XỬ LÝ VIDEO
# ==========================================
st.markdown("---")
if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True):
    if not video_a_file:
        st.error("Vui lòng tải lên Video A để lấy voice!")
    elif not video_b_files or len(video_b_files) > 10:
        st.error("Vui lòng tải lên từ 1 đến 10 Video B!")
    else:
        # Vòng tròn tiến độ hiển thị ở đây
        with st.spinner('Đang AI xử lý cắt ghép video... Vui lòng đợi nhé!'):
            try:
                # 1. Lưu file tạm
                path_a = save_uploaded_file(video_a_file)
                paths_b = [save_uploaded_file(f) for f in video_b_files]

                # 2. Xử lý Video A (Lấy Audio)
                clip_a = mp.VideoFileClip(path_a)
                audio_a = clip_a.audio
                total_audio_duration = audio_a.duration

                # 3. Xử lý Video B (Cắt ngẫu nhiên 10-15s)
                clips_to_concat = []
                current_duration = 0

                for path_b in paths_b:
                    if current_duration >= total_audio_duration:
                        break # Dừng nếu hình đã dài bằng tiếng
                    
                    clip_b = mp.VideoFileClip(path_b)
                    
                    # Cắt random 10 đến 15s
                    clip_duration = clip_b.duration
                    target_duration = random.uniform(10, 15)
                    
                    if clip_duration > target_duration:
                        start_time = random.uniform(0, clip_duration - target_duration)
                        sub_clip = clip_b.subclip(start_time, start_time + target_duration)
                    else:
                        sub_clip = clip_b
                        
                    clips_to_concat.append(sub_clip)
                    current_duration += sub_clip.duration

                # 4. Ghép Video B lại với nhau
                final_visual = mp.concatenate_videoclips(clips_to_concat, method="compose")
                
                # Cắt/Ép độ dài hình bằng đúng độ dài tiếng của Video A
                final_visual = final_visual.set_duration(total_audio_duration)
                
                # Chèn tiếng Video A vào Hình Video B
                final_video = final_visual.set_audio(audio_a)

                # 5. Chèn Text (Nếu có nhập)
                if text_content:
                    style = text_options[selected_text_style]
                    
                    # Lưu ý: Font Montserrat cần cài đặt trong hệ thống máy. Nếu không có máy sẽ lấy font mặc định.
                    txt_clip = mp.TextClip(
                        text_content, 
                        fontsize=70, 
                        color=style["color"],
                        font="Montserrat", # Yêu cầu có font trong máy
                        stroke_color=style["stroke_color"],
                        stroke_width=2 if style["stroke_color"] else 0,
                        bg_color=style["bg_color"]
                    )
                    txt_clip = txt_clip.set_position('center').set_duration(final_video.duration)
                    final_video = mp.CompositeVideoClip([final_video, txt_clip])

                # 6. Xuất File
                output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
                final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30)
                
                # Đóng file giải phóng bộ nhớ
                clip_a.close()
                for c in clips_to_concat:
                    c.close()

                # ==========================================
                # STEP 3: PREVIEW & DOWNLOAD
                # ==========================================
                st.success("🎉 Đã hoàn thành Video!")
                
                # Preview Video
                st.video(output_path)
                
                # Nút tải về
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Tải Video Về Máy",
                        data=file,
                        file_name="KOC_Video_Final.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")