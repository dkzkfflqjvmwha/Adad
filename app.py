import streamlit as st
import google.generativeai as genai
from PIL import Image
import concurrent.futures

# 페이지 설정
st.set_page_config(page_title="Gemini Image Studio", layout="wide")

# 1. 초기 화면: 설정 사이드바
st.sidebar.title("⚙️ Configuration")
api_key = st.sidebar.text_input("Google API Key", type="password")
model_name = st.sidebar.text_input("Model Name", value="gemini-3-flash-image")

if not api_key:
    st.warning("계속하려면 API 키를 입력해주세요.")
    st.stop()

# API 설정
genai.configure(api_key=api_key)

# 2. 메인 화면 UI
st.title("🎨 Gemini Image Generator")

prompt = st.text_area("프롬프트를 입력하세요", placeholder="이미지에 적용할 설명을 입력하세요...")
uploaded_files = st.file_uploader("이미지를 선택하세요 (다중 선택 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

col1, col2 = st.columns([1, 4])
with col1:
    manga_mode = st.toggle("만화 번역 모드")

# 이미지 생성 함수 (단일)
def generate_image(input_image, prompt, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        # 이미지와 프롬프트를 함께 전송 (Gemini의 멀티모달 능력 활용)
        response = model.generate_content([prompt, input_image])
        
        # 참고: Gemini 3 Flash Image 모델의 실제 리턴 형식이 
        # 이미지 파일인 경우를 가정하여 처리 (API 사양에 따라 조정 필요)
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception as e:
        return f"Error: {str(e)}"

# 3 & 4. 로직 실행 및 결과 나열
if st.button("실행하기"):
    if not prompt:
        st.error("프롬프트를 입력해주세요.")
    elif not uploaded_files:
        st.error("최소 한 장 이상의 이미지를 업로드해주세요.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        # 이미지 로드 (업로드 순서 유지)
        images = [Image.open(file) for file in uploaded_files]
        
        st.divider()
        st.subheader("결과물")

        if manga_mode:
            st.info("만화 번역 모드: 병렬 요청을 시작합니다.")
            
            # 병렬 처리 (Thread Poool 사용)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 프롬프트와 각 이미지를 세트로 묶어 개별 요청
                future_to_img = {executor.submit(generate_image, img, prompt, model_name): i for i, img in enumerate(images)}
                
                # 순서대로 결과를 출력하기 위해 인덱스로 관리
                output_placeholders = [st.empty() for _ in range(len(images))]
                
                for future in concurrent.futures.as_completed(future_to_img):
                    idx = future_to_img[future]
                    try:
                        res = future.result()
                        # 결과물을 순서대로 나열
                        with output_placeholders[idx]:
                            st.image(res, caption=f"결과물 #{idx + 1}")
                    except Exception as e:
                        st.error(f"이미지 #{idx + 1} 생성 실패: {e}")
        else:
            # 일반 모드 (첫 번째 이미지에 대해서만 혹은 순차적 처리)
            for i, img in enumerate(images):
                res = generate_image(img, prompt, model_name)
                st.image(res, caption=f"결과물 #{i + 1}")

        progress_bar.progress(100)
