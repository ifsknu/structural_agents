import re
import math
import streamlit as st
import plotly.graph_objects as go
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

    greenhouse_type: str
    total_width: float
    design_length: float
    eave_height: float
    ridge_height: float
    frame_spacing: float
    span_count: int
    frame_count: int
    member: str
    covering: str

    parsed_result: Dict[str, Any]
    recommendation_result: Dict[str, Any]
    drawing_fig: Any
    response_text: str


# =========================================================
# 3. 자연어 조건해석 Agent
# =========================================================
def parse_request_agent(state: DesignState):
    text = state["user_prompt"]

    # 시군구를 광역 단위보다 앞에 배치
    regions = [
        "포항", "경주", "김천", "안동", "구미", "영주", "영천", "상주", "문경", "경산",
        "평창", "대관령", "강릉", "원주", "춘천",
        "수원", "화성", "평택", "이천", "안성", "용인",
        "천안", "아산", "논산", "부여", "공주",
        "청주", "충주", "제천", "음성", "진천",
        "전주", "익산", "김제", "정읍", "남원",
        "나주", "순천", "여수", "담양", "해남", "무안",
        "창원", "진주", "밀양", "김해", "거창", "합천",
        "서귀포", "제주시",
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충청북도", "충남", "충청남도",
        "전북", "전라북도", "전남", "전라남도",
        "경북", "경상북도", "경남", "경상남도", "제주"
    ]

    crop_alias = {
        "방울토마토": "토마토",
        "딸기": "딸기",
        "토마토": "토마토",
        "파프리카": "파프리카",
        "상추": "상추",
        "오이": "오이",
        "고추": "고추",
        "멜론": "멜론",
        "참외": "참외",
        "화훼": "화훼",
        "엽채류": "엽채류",
    }

    # -----------------------------
    # 지역 추출
    # -----------------------------
    region = ""
    for r in regions:
        if r in text:
            region = r
            break

    # 리스트에 없는 지역도 보조 추출
    if not region:
        region_match = re.search(r"([가-힣]{2,10})(?:에서|에|지역에서|지역에)", text)
        if region_match:
            region = region_match.group(1)

    # -----------------------------
    # 작물 추출
    # -----------------------------
    crop = ""
    for key, value in crop_alias.items():
        if key in text:
            crop = value
            break

    # -----------------------------
    # 규모 추출
    # 예: 100평, 100 평, 330m2, 330㎡, 330제곱미터
    # -----------------------------
    area_value = 0.0
    area_unit = ""
    area_m2 = 0.0

    area_pattern = r"(\d+(?:\.\d+)?)\s*(평|평형|m2|㎡|제곱미터|m²)"
    match = re.search(area_pattern, text, re.IGNORECASE)

    if match:
        area_value = float(match.group(1))
        area_unit = match.group(2)

        if area_unit in ["평", "평형"]:
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
        state["drawing_fig"] = None
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
        base_type_single = "단동 아치형 온실"
        base_type_multi = "연동 아치형 온실"
        width_per_span = 8.0
        eave_height = 2.8
        ridge_height = 4.2
        frame_spacing = 0.6
        member = "Ø31.8 × 1.5t"
        covering = "PO 필름 또는 장기성 필름"
        reason_crop = "저상 재배 및 비교적 낮은 내부 공간 요구 조건에 적합합니다."

    elif crop in ["토마토", "파프리카", "오이"]:
        base_type_single = "고측고 단동 온실"
        base_type_multi = "고측고 연동형 온실"
        width_per_span = 8.0
        eave_height = 4.0
        ridge_height = 5.8
        frame_spacing = 0.6
        member = "Ø42.7 × 2.1t"
        covering = "PO 필름 또는 경질 피복재 검토"
        reason_crop = "작물 높이와 작업 공간을 고려하여 높은 측고가 유리합니다."

    elif crop in ["고추", "멜론", "참외"]:
        base_type_single = "단동 아치형 온실"
        base_type_multi = "연동 아치형 온실"
        width_per_span = 8.0
        eave_height = 3.0
        ridge_height = 4.6
        frame_spacing = 0.6
        member = "Ø31.8 × 1.5t 또는 Ø42.7 × 2.1t"
        covering = "PO 필름"
        reason_crop = "중간 높이 작물로 단동형과 연동형 모두 적용 가능합니다."

    else:
        base_type_single = "검토형 단동 온실"
        base_type_multi = "검토형 연동 온실"
        width_per_span = 8.0
        eave_height = 3.0
        ridge_height = 4.5
        frame_spacing = 0.6
        member = "검토 필요"
        covering = "작물 특성에 따라 검토"
        reason_crop = "작물별 생육 조건을 추가 검토해야 합니다."

    # -----------------------------------------------------
    # 규모에 따른 연동 수 및 길이 산정
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
    design_length = area_m2 / total_width

    # 길이가 너무 짧을 때 보정
    if design_length < 20:
        design_length = 20
        span_count = max(1, math.ceil(area_m2 / (design_length * width_per_span)))
        total_width = span_count * width_per_span

    # 길이가 너무 길 때 보정
    if design_length > 80:
        design_length = 60
        span_count = max(1, math.ceil(area_m2 / (design_length * width_per_span)))
        total_width = span_count * width_per_span

    frame_count = int(design_length / frame_spacing) + 1
    estimated_area = total_width * design_length

    # -----------------------------------------------------
    # 지역별 주의사항
    # -----------------------------------------------------
    if region in ["포항", "부산", "울산", "제주", "서귀포", "제주시"]:
        region_note = "해안 또는 강풍 영향 가능성이 있어 풍하중 검토를 우선 고려하는 것이 좋습니다."
    elif region in ["강원", "평창", "대관령"]:
        region_note = "적설 영향이 큰 지역일 수 있으므로 적설하중 검토를 우선 고려하는 것이 좋습니다."
    elif region in ["대구", "경북", "영천", "경주", "구미", "안동"]:
        region_note = "내륙 지역 특성을 고려하여 풍하중과 적설하중을 함께 검토하는 것이 좋습니다."
    else:
        region_note = "지역별 기본풍속 및 적설하중 기준값을 확인하여 구조검토가 필요합니다."

    if span_count == 1:
        greenhouse_type = base_type_single
    else:
        greenhouse_type = f"{span_count}연동 {base_type_multi}"

    state["greenhouse_type"] = greenhouse_type
    state["total_width"] = total_width
    state["design_length"] = design_length
    state["eave_height"] = eave_height
    state["ridge_height"] = ridge_height
    state["frame_spacing"] = frame_spacing
    state["span_count"] = span_count
    state["frame_count"] = frame_count
    state["member"] = member
    state["covering"] = covering

    state["recommendation_result"] = {
        "추천 온실 형식": greenhouse_type,
        "지역": region,
        "작물": crop,
        "요구 규모": f"약 {area_pyung:.1f}평",
        "요구 면적 [m²]": round(area_m2, 2),
        "추천 폭 [m]": round(total_width, 2),
        "추천 길이 [m]": round(design_length, 2),
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
        f"예비 치수는 폭 {total_width:.2f} m, 길이 {design_length:.2f} m, "
        f"처마높이 {eave_height:.2f} m, 동고 {ridge_height:.2f} m입니다."
    )

    return state


# =========================================================
# 5. 3D 설계모델 생성 Agent
# =========================================================
def drawing_agent(state: DesignState):
    if state["missing_fields"]:
        state["drawing_fig"] = None
        return state

    total_width = state["total_width"]
    design_length = state["design_length"]
    eave_height = state["eave_height"]
    ridge_height = state["ridge_height"]
    frame_spacing = state["frame_spacing"]
    span_count = state["span_count"]
    frame_count = state["frame_count"]
    greenhouse_type = state["greenhouse_type"]
    crop = state["crop"]
    region = state["region"]

    fig = go.Figure()

    roof_rise = ridge_height - eave_height
    bay_width = total_width / span_count

    def add_line(xs, ys, zs, name="부재", width=4, dash=None):
        line_style = dict(width=width)
        if dash:
            line_style["dash"] = dash

        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                name=name,
                showlegend=False,
                line=line_style
            )
        )

    def add_text(x, y, z, text):
        fig.add_trace(
            go.Scatter3d(
                x=[x],
                y=[y],
                z=[z],
                mode="markers+text",
                text=[text],
                textposition="top center",
                showlegend=False,
                marker=dict(size=3)
            )
        )

    def arch_z(y, y0, y1):
        center = (y0 + y1) / 2
        half = (y1 - y0) / 2

        if half == 0:
            return eave_height

        ratio = (y - center) / half
        return eave_height + roof_rise * (1 - ratio ** 2)

    # -----------------------------------------------------
    # 표시할 프레임 위치
    # 실제 프레임 수가 많으면 일부만 표시
    # -----------------------------------------------------
    visible_frames = min(frame_count, 30)

    if visible_frames <= 1:
        x_positions = [0, design_length]
    else:
        x_positions = [
            design_length * i / (visible_frames - 1)
            for i in range(visible_frames)
        ]

    # -----------------------------------------------------
    # 프레임 아치 생성
    # -----------------------------------------------------
    for x in x_positions:
        for s in range(span_count):
            y0 = s * bay_width
            y1 = (s + 1) * bay_width

            # 좌측 기둥
            add_line(
                [x, x],
                [y0, y0],
                [0, eave_height],
                "기둥",
                width=4
            )

            # 우측 기둥
            add_line(
                [x, x],
                [y1, y1],
                [0, eave_height],
                "기둥",
                width=4
            )

            # 아치 프레임
            ys = [y0 + (y1 - y0) * i / 30 for i in range(31)]
            xs = [x for _ in ys]
            zs = [arch_z(y, y0, y1) for y in ys]

            add_line(
                xs,
                ys,
                zs,
                "아치 프레임",
                width=4
            )

    # -----------------------------------------------------
    # 길이 방향 도리 / 연결재
    # -----------------------------------------------------
    for s in range(span_count):
        y0 = s * bay_width
        y1 = (s + 1) * bay_width

        # 측면 처마 도리
        for y in [y0, y1]:
            add_line(
                [0, design_length],
                [y, y],
                [eave_height, eave_height],
                "처마 도리",
                width=3
            )

        # 지붕 도리 3줄
        for frac in [0.25, 0.5, 0.75]:
            y = y0 + bay_width * frac
            z = arch_z(y, y0, y1)

            add_line(
                [0, design_length],
                [y, y],
                [z, z],
                "지붕 도리",
                width=3
            )

    # -----------------------------------------------------
    # 바닥 외곽선
    # -----------------------------------------------------
    add_line(
        [0, design_length, design_length, 0, 0],
        [0, 0, total_width, total_width, 0],
        [0, 0, 0, 0, 0],
        "바닥 외곽",
        width=3,
        dash="dash"
    )

    # -----------------------------------------------------
    # 연동 구분선
    # -----------------------------------------------------
    if span_count > 1:
        for s in range(1, span_count):
            y = s * bay_width
            add_line(
                [0, design_length],
                [y, y],
                [0, 0],
                "연동 구분선",
                width=2,
                dash="dash"
            )

    # -----------------------------------------------------
    # 치수 텍스트
    # -----------------------------------------------------
    add_text(
        design_length / 2,
        total_width / 2,
        ridge_height + 0.5,
        f"동고 {ridge_height:.2f} m"
    )

    add_text(
        design_length / 2,
        -total_width * 0.08,
        0,
        f"길이 {design_length:.2f} m"
    )

    add_text(
        design_length + design_length * 0.05,
        total_width / 2,
        0,
        f"폭 {total_width:.2f} m"
    )

    add_text(
        0,
        total_width + total_width * 0.05,
        eave_height,
        f"처마높이 {eave_height:.2f} m"
    )

    # -----------------------------------------------------
    # Layout 설정
    # -----------------------------------------------------
    fig.update_layout(
        title=f"3D 온실 와이어프레임 모델 - {greenhouse_type}",
        height=720,
        margin=dict(l=0, r=0, t=50, b=0),
        scene=dict(
            xaxis_title="길이 X [m]",
            yaxis_title="폭 Y [m]",
            zaxis_title="높이 Z [m]",
            aspectmode="data",
            camera=dict(
                eye=dict(x=1.6, y=1.4, z=0.9)
            )
        ),
        annotations=[
            dict(
                text=(
                    f"지역: {region} | 작물: {crop} | 연동 수: {span_count} | "
                    f"프레임 간격: {frame_spacing:.2f} m | 전체 프레임 수: {frame_count}개"
                ),
                showarrow=False,
                x=0,
                y=1.04,
                xref="paper",
                yref="paper",
                align="left",
                font=dict(size=13)
            )
        ]
    )

    state["drawing_fig"] = fig
    return state


# =========================================================
# 6. LangGraph 구성
# =========================================================
def build_graph():
    graph = StateGraph(DesignState)

    graph.add_node("parse_request_agent", parse_request_agent)
    graph.add_node("recommendation_agent", recommendation_agent)
    graph.add_node("drawing_agent", drawing_agent)

    graph.set_entry_point("parse_request_agent")

    graph.add_edge("parse_request_agent", "recommendation_agent")
    graph.add_edge("recommendation_agent", "drawing_agent")
    graph.add_edge("drawing_agent", END)

    return graph.compile()


# =========================================================
# 7. Streamlit 화면 구성
# =========================================================
st.title("자연어 기반 온실 예비설계 추천 시스템")

st.caption(
    "사용자가 자연어로 지역, 작물, 규모를 입력하면 조건을 자동 추출하고, 온실 추천안과 3D 예비 설계모델을 생성합니다."
)

with st.expander("입력 예시 보기"):
    st.markdown(
        """
        아래처럼 입력할 수 있습니다.

        - `포항에서 딸기 재배용으로 100평 규모 온실 추천해줘`
        - `대구에 토마토 200평 정도 재배할 온실 추천해줘`
        - `강원 평창에서 파프리카 300평 규모로 하고 싶어`
        - `경북에서 상추 150평 온실 추천해줘`
        - `익산에서 방울토마토 250평형 온실 추천해줘`
        """
    )


# =========================================================
# 8. 세션 상태 초기화
# =========================================================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None


# =========================================================
# 9. 기존 채팅 출력
# =========================================================
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# =========================================================
# 10. 사용자 자연어 입력
# =========================================================
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

        "greenhouse_type": "",
        "total_width": 0.0,
        "design_length": 0.0,
        "eave_height": 0.0,
        "ridge_height": 0.0,
        "frame_spacing": 0.0,
        "span_count": 0,
        "frame_count": 0,
        "member": "",
        "covering": "",

        "parsed_result": {},
        "recommendation_result": {},
        "drawing_fig": None,
        "response_text": "",
    }

    result = app.invoke(input_state)

    st.session_state["last_result"] = result

    st.session_state["messages"].append(
        {"role": "assistant", "content": result["response_text"]}
    )

    with st.chat_message("assistant"):
        st.write(result["response_text"])


# =========================================================
# 11. 상세 결과 출력
# =========================================================
if st.session_state["last_result"] is not None:
    result = st.session_state["last_result"]

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "① 조건 추출 결과",
        "② 추천안",
        "③ 3D 설계모델"
    ])

    with tab1:
        st.subheader("자연어 입력 조건 추출 결과")
        st.table([result["parsed_result"]])

    with tab2:
        st.subheader("온실 예비설계 추천안")

        if result["recommendation_result"]:
            st.table([result["recommendation_result"]])

            st.info(
                "현재 추천안은 예비설계 단계의 자동 추천 결과입니다. "
                "최종 설계에는 지역별 기본풍속, 적설하중, 하중조합, 부재 안정성 검토가 추가로 필요합니다."
            )
        else:
            st.warning(result["response_text"])

    with tab3:
        st.subheader("3D 온실 와이어프레임 모델")

        if result["drawing_fig"] is not None:
            st.plotly_chart(
                result["drawing_fig"],
                use_container_width=True
            )

            st.caption(
                "마우스로 회전, 확대, 축소할 수 있습니다. "
                "프레임 수가 많을 경우 화면에는 일부 프레임만 대표로 표시됩니다."
            )
        else:
            st.info("추천안이 생성되면 3D 설계모델이 표시됩니다.")
