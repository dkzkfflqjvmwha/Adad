import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageOps
import concurrent.futures
import zipfile
import io

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="Gemini Image Studio", layout="wide")

# 사이드바 설정
st.sidebar.title("⚙️ Configuration")
# 사용자가 직접 입력할 수 있도록 설정
api_key = st.sidebar.text_input("Google API Key", type="password", help="Google AI Studio에서 발급받은 키를 입력하세요.")
model_name = st.sidebar.text_input("Model Name", value="gemini-1.5-flash-latest", help="예: gemini-1.5-flash-latest 또는 gemini-1.5-pro")

# API 키가 없을 경우 안내 문구만 표시하고 중단
if not api_key:
    st.info("👈 왼쪽 사이드바에서 API 키를 입력하면 시작할 수 있습니다.")
    st.stop()

# Gemini API 구성
genai.configure(api_key=api_key)

# 2. 메인 화면 UI
st.title("🎨 Gemini Image Generator & Translator")

# 프롬프트 입력창
prompt = st.text_area(
    "프롬프트를 입력하세요", 
    placeholder="예: 이 만화 페이지의 모든 대사를 한국어로 번역해서 자연스럽게 적어줘. 인물 말투를 살려줘.",
    height=150
)

# 파일 업로드 (이미지 및 ZIP 지원)
uploaded_files = st.file_uploader(
    "이미지 또는 ZIP 파일을 선택하세요 (다중 선택 가능)", 
    type=['png', 'jpg', 'jpeg', 'zip'], 
    accept_multiple_files=True
)

# 옵션 설정
col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    manga_mode = st.toggle("만화 번역 모드 (병렬 요청)", value=True, help="켜짐: 여러 장을 동시에 처리 / 꺼짐: 한 장씩 순서대로 처리")

# 3. 핵심 기능 함수
def generate_content(input_image, user_prompt, target_model):
    """Gemini API에 이미지와 프롬프트를 전달하여 결과를 가져옵니다."""
    try:
        # 모델명 경로 정규화 (404 에러 방지)
        if not target_model.startswith('models/'):
            full_model_path = f"models/{target_model}"
        else:
            full_model_path = target_model
            
        model = genai.GenerativeModel(full_model_path)
        # 이미지와 텍스트를 리스트로 전달하여 멀티모달 요청
        response = model.generate_content([user_prompt, input_image])
        return response.text
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"

def process_image_data(raw_bytes):
    """이미지 바이트 데이터를 PIL 객체로 변환하고 전처리합니다."""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        # 스마트폰 사진의 회전 정보(EXIF)를 자동으로 바로잡음
        img = ImageOps.exif_transpose(img)
        # RGB 모드로 통일 (RGBA 등에서 발생할 수 있는 오류 방지)
        return img.convert("RGB")
    except:
        return None

# 4. 실행 로직
if st.button("🚀 실행하기", use_container_width=True):
    if not prompt:
        st.error("명령(프롬프트)을 입력해주세요.")
    elif not uploaded_files:
        st.error("처리할 파일을 업로드해주세요.")
    else:
        all_images = []
        
        # 파일 리스트 처리
        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.read()
            # ZIP 파일인 경우
            if uploaded_file.name.lower().endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    # 시스템 파일(__MACOSX 등) 제외하고 이미지 파일만 추출 및 정렬
                    img_files = sorted([
                        f for f in z.namelist() 
                        if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('__')
                    ])
                    for img_path in img_files:
                        with z.open(img_path) as f:
                            p_img = process_image_data(f.read())
                            if p_img:
                                all_images.append(p_img)
            # 일반 이미지 파일인 경우
            else:
                p_img = process_image_data(file_bytes)
                if p_img:
                    all_images.append(p_img)

        if not all_images:
            st.error("이미지를 찾을 수 없습니다. 올바른 형식의 이미지나 ZIP 파일을 올려주세요.")
            st.stop()

        st.success(f"총 {len(all_images)}장의 이미지를 분석 중입니다...")
        
        # 결과 화면 나열
        if manga_mode:
            # 병렬 요청 처리 (속도 최적화)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 이미지를 업로드 순서대로 유지하며 요청 전송
                futures = [executor.submit(generate_content, img, prompt, model_name) for img in all_images]
                
                for i, future in enumerate(futures):
                    res_col1, res_col2 = st.columns([1, 1])
                    with res_col1:
                        st.image(all_images[i], caption=f"원본 페이지 {i+1}", use_container_width=True)
                    with res_col2:
                        st.info(f"📄 분석 결과 {i+1}")
                        st.write(future.result())
                    st.divider()
        else:
            # 순차 요청 처리
            for i, img in enumerate(all_images):
                result_text = generate_content(img, prompt, model_name)
                res_col1, res_col2 = st.columns([1, 1])
                with res_col1:
                    st.image(img, caption=f"원본 페이지 {i+1}", use_container_width=True)
                with res_col2:
                    st.info(f"📄 분석 결과 {i+1}")
                    st.write(result_text)
                st.divider()

        st.balloons() # 성공 축하 풍선
