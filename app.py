import re
import math
import streamlit as st
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END


# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(
    page_title="자연어 기반 온실 예비설계 추천 시스템",
    layout="wide"
)


# =========================================================
# 2. LangGraph State 정의
# =========================================================
class DesignState(TypedDict):
    user_prompt: str

    region: str
    crop: str
    area_value: float
    area_unit: str
    area_m2: float
    missing_fields: List[str]

    parsed_result: Dict[str, Any]
    recommendation_result: Dict[str, Any]
    response_text: str


# =========================================================
# 3. 자연어 조건해석 Agent
# =========================================================
def parse_request_agent(state: DesignState):
    text = state["user_prompt"]

    regions = [
        "포항", "대구", "경북", "경주", "영천", "구미", "안동",
        "강원", "평창", "대관령", "전남", "나주", "광주",
        "경기", "수원", "충남", "천안", "제주", "부산", "울산"
    ]

    crops = [
        "딸기", "토마토", "파프리카", "상추", "오이",
        "고추", "멜론", "참외", "화훼", "엽채류"
    ]

    # 지역 추출
    region = ""
    for r in regions:
        if r in text:
            region = r
            break

    # 작물 추출
    crop = ""
    for c in crops:
        if c in text:
            crop = c
            break

    # 규모 추출: 100평, 330m2, 330㎡, 330제곱미터 등
    area_value = 0.0
    area_unit = ""
    area_m2 = 0.0

    area_pattern = r"(\d+(?:\.\d+)?)\s*(평|m2|㎡|제곱미터|m²)"
    match = re.search(area_pattern, text, re.IGNORECASE)

    if match:
        area_value = float(match.group(1))
        area_unit = match.group(2)

        if area_unit == "평":
            area_m2 = area_value * 3.3058
        else:
            area_m2 = area_value

    missing_fields = []

    if not region:
        missing_fields.append("지역")

    if not crop:
        missing_fields.append("작물")

    if area_m2 <= 0:
        missing_fields.append("규모")

    state["region"] = region
    state["crop"] = crop
    state["area_value"] = area_value
    state["area_unit"] = area_unit
    state["area_m2"] = area_m2
    state["missing_fields"] = missing_fields

    state["parsed_result"] = {
        "입력 문장": text,
        "추출 지역": region if region else "미입력",
        "추출 작물": crop if crop else "미입력",
        "추출 규모": f"{area_value:g} {area_unit}" if area_value > 0 else "미입력",
        "환산 면적 [m²]": round(area_m2, 2) if area_m2 > 0 else "미입력",
        "부족한 조건": ", ".join(missing_fields) if missing_fields else "없음"
    }

    return state


# =========================================================
# 4. 온실 추천안 생성 Agent
# =========================================================
def recommendation_agent(state: DesignState):
    missing = state["missing_fields"]

    if missing:
        state["recommendation_result"] = {}
        state["response_text"] = (
            "추천안을 생성하려면 다음 조건이 더 필요합니다: "
            + ", ".join(missing)
            + "\n\n예시: `포항에서 딸기 재배용으로 100평 규모 온실 추천해줘`"
        )
        return state

    region = state["region"]
    crop = state["crop"]
    area_m2 = state["area_m2"]
    area_pyung = area_m2 / 3.3058

    # -----------------------------------------------------
    # 작물별 기본 추천 로직
    # -----------------------------------------------------
    if crop in ["딸기", "상추", "엽채류"]:
        base_type = "단동 아치형 온실"
        width_per_span = 8.0
        eave_height = 2.8
        ridge_height = 4.2
        frame_spacing = 0.6
        member = "Ø31.8 × 1.5t"
        covering = "PO 필름 또는 장기성 필름"
        reason_crop = "저상 재배 및 비교적 낮은 내부 공간 요구 조건에 적합합니다."

    elif crop in ["토마토", "파프리카", "오이"]:
        base_type = "고측고 연동형 온실"
        width_per_span = 8.0
        eave_height = 4.0
        ridge_height = 5.8
        frame_spacing = 0.6
        member = "Ø42.7 × 2.1t"
        covering = "PO 필름 또는 경질 피복재 검토"
        reason_crop = "작물 높이와 작업 공간을 고려하여 높은 측고가 유리합니다."

    elif crop in ["고추", "멜론", "참외"]:
        base_type = "단동 또는 2연동 아치형 온실"
        width_per_span = 8.0
        eave_height = 3.0
        ridge_height = 4.6
        frame_spacing = 0.6
        member = "Ø31.8 × 1.5t 또는 Ø42.7 × 2.1t"
        covering = "PO 필름"
        reason_crop = "중간 높이 작물로 단동형과 연동형 모두 적용 가능합니다."

    else:
        base_type = "검토형 온실"
        width_per_span = 8.0
        eave_height = 3.0
        ridge_height = 4.5
        frame_spacing = 0.6
        member = "검토 필요"
        covering = "작물 특성에 따라 검토"
        reason_crop = "작물별 생육 조건을 추가 검토해야 합니다."

    # -----------------------------------------------------
    # 규모에 따른 동수 및 길이 산정
    # -----------------------------------------------------
    if area_m2 <= 400:
        span_count = 1
    elif area_m2 <= 800:
        span_count = 2
    elif area_m2 <= 1200:
        span_count = 3
    else:
        span_count = math.ceil(area_m2 / 400)

    total_width = width_per_span * span_count
    length = area_m2 / total_width

    # 길이가 너무 짧거나 길 경우 간단 보정
    if length < 20:
        length = 20
        total_width = area_m2 / length
        span_count = max(1, round(total_width / width_per_span))

    if length > 80:
        length = 60
        total_width = area_m2 / length
        span_count = max(1, math.ceil(total_width / width_per_span))
        total_width = span_count * width_per_span

    frame_count = int(length / frame_spacing) + 1
    estimated_area = total_width * length

    # -----------------------------------------------------
    # 지역별 간단 설계 주의사항
    # -----------------------------------------------------
    region_note = "일반적인 풍하중 및 적설하중 검토가 필요합니다."

    if region in ["포항", "부산", "울산", "제주"]:
        region_note = "해안 또는 강풍 영향 가능성이 있어 풍하중 검토를 우선적으로 고려하는 것이 좋습니다."

    if region in ["강원", "평창", "대관령"]:
        region_note = "적설 영향이 큰 지역일 수 있으므로 적설하중 검토를 우선적으로 고려하는 것이 좋습니다."

    if region in ["대구", "경북", "영천", "경주", "구미", "안동"]:
        region_note = "내륙 지역 특성을 고려하여 풍하중과 적설하중을 함께 검토하는 것이 좋습니다."

    # -----------------------------------------------------
    # 추천안 정리
    # -----------------------------------------------------
    if span_count == 1:
        greenhouse_type = base_type
    else:
        greenhouse_type = f"{span_count}연동 {base_type}"

    state["recommendation_result"] = {
        "추천 온실 형식": greenhouse_type,
        "지역": region,
        "작물": crop,
        "요구 규모": f"약 {area_pyung:.1f}평",
        "요구 면적 [m²]": round(area_m2, 2),
        "추천 폭 [m]": round(total_width, 2),
        "추천 길이 [m]": round(length, 2),
        "예상 설계면적 [m²]": round(estimated_area, 2),
        "단위 동폭 [m]": width_per_span,
        "연동 수": span_count,
        "처마높이 [m]": eave_height,
        "동고 [m]": ridge_height,
        "프레임 간격 [m]": frame_spacing,
        "예상 프레임 수": frame_count,
        "추천 주요 부재": member,
        "추천 피복재": covering,
        "작물 기준 추천 이유": reason_crop,
        "지역 기준 검토사항": region_note,
        "주의": "본 결과는 예비설계 추천안이며, 최종 설계에는 구조기준에 따른 하중 및 안정성 검토가 필요합니다."
    }

    state["response_text"] = (
        f"{region} 지역에서 {crop} 재배를 위한 약 {area_pyung:.1f}평 규모의 온실로 "
        f"`{greenhouse_type}`을 추천합니다. "
        f"예비 치수는 폭 {total_width:.2f} m, 길이 {length:.2f} m, "
        f"처마높이 {eave_height:.2f} m, 동고 {ridge_height:.2f} m입니다."
    )

    return state


# =========================================================
# 5. LangGraph 구성
# =========================================================
def build_graph():
    graph = StateGraph(DesignState)

    graph.add_node("parse_request_agent", parse_request_agent)
    graph.add_node("recommendation_agent", recommendation_agent)

    graph.set_entry_point("parse_request_agent")
    graph.add_edge("parse_request_agent", "recommendation_agent")
    graph.add_edge("recommendation_agent", END)

    return graph.compile()


# =========================================================
# 6. Streamlit 화면 구성
# =========================================================
st.title("자연어 기반 온실 예비설계 추천 시스템")

st.caption(
    "사용자가 자연어로 지역, 작물, 규모를 입력하면 조건을 자동 추출하고 예비 온실 추천안을 생성합니다."
)

with st.expander("입력 예시 보기"):
    st.markdown(
        """
        아래처럼 입력할 수 있습니다.

        - `포항에서 딸기 재배용으로 100평 규모 온실 추천해줘`
        - `대구에 토마토 200평 정도 재배할 온실 추천해줘`
        - `강원 평창에서 파프리카 300평 규모로 하고 싶어`
        - `경북에서 상추 150평 온실 추천해줘`
        """
    )


# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None


# 기존 메시지 출력
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# 사용자 자연어 입력
user_prompt = st.chat_input("예: 포항에서 딸기 재배용으로 100평 규모 온실 추천해줘")

if user_prompt:
    st.session_state["messages"].append(
        {"role": "user", "content": user_prompt}
    )

    with st.chat_message("user"):
        st.write(user_prompt)

    app = build_graph()

    input_state = {
        "user_prompt": user_prompt,

        "region": "",
        "crop": "",
        "area_value": 0.0,
        "area_unit": "",
        "area_m2": 0.0,
        "missing_fields": [],

        "parsed_result": {},
        "recommendation_result": {},
        "response_text": "",
    }

    result = app.invoke(input_state)

    st.session_state["last_result"] = result
    st.session_state["messages"].append(
        {"role": "assistant", "content": result["response_text"]}
    )

    with st.chat_message("assistant"):
        st.write(result["response_text"])


# 결과 상세 출력
if st.session_state["last_result"] is not None:
    result = st.session_state["last_result"]

    st.divider()

    tab1, tab2 = st.tabs(["① 조건 추출 결과", "② 추천안"])

    with tab1:
        st.subheader("자연어 입력 조건 추출 결과")
        st.table([result["parsed_result"]])

    with tab2:
        st.subheader("온실 예비설계 추천안")

        if result["recommendation_result"]:
            st.table([result["recommendation_result"]])

            st.info(
                "현재 단계는 자연어 입력 → 조건 추출 → 추천안 생성까지만 구현한 버전입니다. "
                "다음 단계에서 설계도면 시각화, 자재내역, 하중계산, 구조해석, 안정성 검토를 순차적으로 추가할 수 있습니다."
            )
        else:
            st.warning(result["response_text"])
