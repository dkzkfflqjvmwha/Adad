import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageOps
import concurrent.futures
import zipfile
import io

# 1. 페이지 설정
st.set_page_config(page_title="Gemini Image Studio", layout="wide")

# 사이드바 설정
st.sidebar.title("⚙️ Configuration")
api_key = st.sidebar.text_input("Google API Key", type="password", help="Google AI Studio에서 발급받은 키를 입력하세요.")
# 기본 모델명을 가장 안정적인 gemini-1.5-flash로 설정
model_name = st.sidebar.text_input("Model Name", value="gemini-1.5-flash", help="예: gemini-1.5-flash, gemini-1.5-pro")

if not api_key:
    st.info("👈 왼쪽 사이드바에서 API 키를 입력하면 시작할 수 있습니다.")
    st.stop()

# Gemini API 구성
genai.configure(api_key=api_key)

# 2. 메인 화면 UI
st.title("🎨 Gemini 만화 번역 & 이미지 분석기")

prompt = st.text_area(
    "명령어(프롬프트)를 입력하세요", 
    placeholder="예: 이 만화 페이지의 대사를 한국어로 번역해줘. 말풍선 순서대로 자연스럽게 번역해줘.",
    height=150
)

uploaded_files = st.file_uploader(
    "이미지 또는 ZIP 파일을 선택하세요", 
    type=['png', 'jpg', 'jpeg', 'zip'], 
    accept_multiple_files=True
)

manga_mode = st.toggle("만화 번역 모드 (병렬 처리)", value=True)

# 3. 핵심 기능 함수
def generate_content(input_image, user_prompt, target_model):
    """Gemini API에 요청을 보내고 결과를 반환합니다. 404 에러 시 재시도 로직 포함."""
    # 모델명 정규화
    clean_name = target_model.replace('models/', '')
    model_path = f"models/{clean_name}"
    
    try:
        model = genai.GenerativeModel(model_path)
        response = model.generate_content([user_prompt, input_image])
        return response.text
    except Exception as e:
        # 404 에러 발생 시 가장 기본 모델명으로 자동 재시도
        if "404" in str(e):
            try:
                fallback_model = genai.GenerativeModel("models/gemini-1.5-flash")
                response = fallback_model.generate_content([user_prompt, input_image])
                return response.text
            except Exception as e2:
                return f"❌ 모델을 찾을 수 없습니다: {str(e2)}"
        return f"❌ 오류 발생: {str(e)}"

def process_image_data(raw_bytes):
    """이미지 데이터를 전처리합니다."""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img = ImageOps.exif_transpose(img) # 회전 보정
        return img.convert("RGB")
    except:
        return None

# 4. 실행 로직
if st.button("🚀 실행하기", use_container_width=True):
    if not prompt or not uploaded_files:
        st.error("프롬프트와 파일을 모두 입력해주세요.")
    else:
        all_images = []
        
        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.read()
            # ZIP 파일 처리
            if uploaded_file.name.lower().endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    img_files = sorted([
                        f for f in z.namelist() 
                        if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('__')
                    ])
                    for img_path in img_files:
                        with z.open(img_path) as f:
                            p_img = process_image_data(f.read())
                            if p_img: all_images.append(p_img)
            # 일반 이미지 처리
            else:
                p_img = process_image_data(file_bytes)
                if p_img: all_images.append(p_img)

        if not all_images:
            st.error("이미지를 불러올 수 없습니다.")
            st.stop()

        st.success(f"총 {len(all_images)}장의 이미지를 처리 중입니다...")
        
        # 결과 표시
        if manga_mode:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(generate_content, img, prompt, model_name) for img in all_images]
                for i, future in enumerate(futures):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.image(all_images[i], caption=f"원본 {i+1}", use_container_width=True)
                    with col2:
                        st.markdown(f"### 📄 결과 {i+1}")
                        st.write(future.result())
                    st.divider()
        else:
            for i, img in enumerate(all_images):
                res = generate_content(img, prompt, model_name)
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.image(img, caption=f"원본 {i+1}", use_container_width=True)
                with col2:
                    st.markdown(f"### 📄 결과 {i+1}")
                    st.write(res)
                st.divider()
        
        st.balloons()
