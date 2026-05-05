import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageOps
import concurrent.futures
import zipfile
import io

# 페이지 설정
st.set_page_config(page_title="Gemini Image Studio", layout="wide")

# 1. 사이드바 설정
st.sidebar.title("⚙️ Configuration")
api_key = st.sidebar.text_input("Google API Key", type="password")
model_name = st.sidebar.text_input("Model Name", value="gemini-1.5-flash")

if not api_key:
    st.sidebar.warning("API 키를 입력해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 2. 메인 화면 UI
st.title("🎨 Gemini Image Generator")

prompt = st.text_area("프롬프트를 입력하세요", placeholder="예: 이 만화 페이지를 한국어로 번역해줘.")
uploaded_files = st.file_uploader("이미지 또는 ZIP 파일 (여러 개 가능)", type=['png', 'jpg', 'jpeg', 'zip'], accept_multiple_files=True)

manga_mode = st.toggle("만화 번역 모드 (병렬 요청)", value=True)

def generate_image(input_image, prompt, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([prompt, input_image])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# 이미지 전처리 함수 (에러 방지)
def process_image(file_data):
    try:
        img = Image.open(io.BytesIO(file_data))
        img = ImageOps.exif_transpose(img) # 사진 회전 정보 자동 수정
        return img.convert("RGB") # 형식 통일
    except:
        return None

if st.button("실행하기"):
    if not prompt or not uploaded_files:
        st.error("프롬프트와 파일을 확인해주세요.")
    else:
        all_images = []
        
        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.read()
            if uploaded_file.name.lower().endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    # 실제 이미지 파일만 필터링 (시스템 파일 제외)
                    img_list = sorted([f for f in z.namelist() if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('__')])
                    for img_path in img_list:
                        with z.open(img_path) as f:
                            processed_img = process_image(f.read())
                            if processed_img:
                                all_images.append(processed_img)
            else:
                processed_img = process_image(file_bytes)
                if processed_img:
                    all_images.append(processed_img)

        if not all_images:
            st.error("이미지를 불러오지 못했습니다. 파일 형식을 확인하세요.")
            st.stop()

        st.info(f"총 {len(all_images)}장의 이미지를 처리합니다.")
        
        # 결과 표시 부분
        if manga_mode:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(generate_image, img, prompt, model_name) for img in all_images]
                for i, future in enumerate(futures):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.image(all_images[i], use_container_width=True, caption=f"Page {i+1}")
                    with col2:
                        st.markdown(f"### 번역 결과 {i+1}")
                        st.write(future.result())
                    st.divider()
        else:
            for i, img in enumerate(all_images):
                res = generate_image(img, prompt, model_name)
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.image(img, use_container_width=True)
                with col2:
                    st.write(res)
                st.divider()
