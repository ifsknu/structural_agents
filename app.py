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
    page_title="자연어 기반 온실 예비설계 및 구조검토 시스템",
    layout="wide"
)


# =========================================================
# 2. CSS 스타일
# =========================================================
st.markdown(
    """
    <style>
    .main {
        background-color: #f6f8fb;
    }

    .app-header {
        background: linear-gradient(135deg, #0f172a, #1d4ed8);
        color: white;
        padding: 24px 30px;
        border-radius: 0 0 18px 18px;
        margin-bottom: 18px;
        border-bottom: 4px solid #93c5fd;
    }

    .app-header h1 {
        margin: 0;
        font-size: 27px;
        line-height: 1.25;
    }

    .app-header p {
        margin: 8px 0 0;
        color: #dbeafe;
        font-size: 15px;
    }

    .card {
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
        margin-bottom: 14px;
    }

    .card-title {
        font-size: 18px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e5e7eb;
    }

    .hint-box {
        background: #eef2ff;
        border-left: 4px solid #2563eb;
        padding: 10px 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 13px;
        line-height: 1.55;
        color: #1f2937;
    }

    .warn-box {
        background: #fef3c7;
        border-left: 4px solid #d97706;
        padding: 10px 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 13px;
        line-height: 1.55;
        color: #1f2937;
    }

    .ok-box {
        background: #d1fae5;
        border-left: 4px solid #059669;
        padding: 10px 12px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 13px;
        line-height: 1.55;
        color: #064e3b;
    }

    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04);
    }

    .metric-card span {
        display: block;
        color: #64748b;
        font-size: 12px;
        margin-bottom: 4px;
    }

    .metric-card b {
        display: block;
        font-size: 21px;
        color: #0f172a;
    }

    .section-card {
        border: 1px solid #dbe3ee;
        border-radius: 16px;
        background: linear-gradient(180deg, #ffffff, #f8fafc);
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.06);
        padding: 14px;
        margin-bottom: 12px;
    }

    .section-card h3 {
        margin: 0 0 8px;
        font-size: 18px;
        color: #0f172a;
    }

    .section-note {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 10px;
        padding: 10px 12px;
        margin: 8px 0;
        font-size: 13px;
        line-height: 1.55;
        color: #334155;
    }

    .top-help {
        font-size: 13px;
        color: #64748b;
        margin-top: -6px;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. LangGraph State 정의
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
    analysis_result: Dict[str, Any]
    drawing_fig: Any
    response_text: str


# =========================================================
# 4. 자연어 조건해석 Agent
# =========================================================
def parse_request_agent(state: DesignState):
    text = state["user_prompt"]

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

    region = ""
    for r in regions:
        if r in text:
            region = r
            break

    if not region:
        region_match = re.search(r"([가-힣]{2,10})(?:에서|에|지역에서|지역에)", text)
        if region_match:
            region = region_match.group(1)

    crop = ""
    for key, value in crop_alias.items():
        if key in text:
            crop = value
            break

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
# 5. 온실 추천안 생성 Agent
# =========================================================
def recommendation_agent(state: DesignState):
    if state["missing_fields"]:
        state["recommendation_result"] = {}
        state["analysis_result"] = {}
        state["drawing_fig"] = None
        state["response_text"] = (
            "추천안을 생성하려면 다음 조건이 더 필요합니다: "
            + ", ".join(state["missing_fields"])
            + "\n\n예시: `포항에서 딸기 재배용으로 100평 규모 온실 추천해줘`"
        )
        return state

    region = state["region"]
    crop = state["crop"]
    area_m2 = state["area_m2"]
    area_pyung = area_m2 / 3.3058

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

    if design_length < 20:
        design_length = 20
        span_count = max(1, math.ceil(area_m2 / (design_length * width_per_span)))
        total_width = span_count * width_per_span

    if design_length > 80:
        design_length = 60
        span_count = max(1, math.ceil(area_m2 / (design_length * width_per_span)))
        total_width = span_count * width_per_span

    frame_count = int(design_length / frame_spacing) + 1
    estimated_area = total_width * design_length

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
# 6. 3D 설계모델 생성 Agent
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

    fig = go.Figure()

    roof_rise = ridge_height - eave_height
    bay_width = total_width / span_count

    def add_line(xs, ys, zs, width=4):
        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                showlegend=False,
                line=dict(width=width)
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

    visible_frames = min(frame_count, 30)

    if visible_frames <= 1:
        x_positions = [0, design_length]
    else:
        x_positions = [
            design_length * i / (visible_frames - 1)
            for i in range(visible_frames)
        ]

    for x in x_positions:
        for s in range(span_count):
            y0 = s * bay_width
            y1 = (s + 1) * bay_width

            add_line([x, x], [y0, y0], [0, eave_height], width=4)
            add_line([x, x], [y1, y1], [0, eave_height], width=4)

            ys = [y0 + (y1 - y0) * i / 30 for i in range(31)]
            xs = [x for _ in ys]
            zs = [arch_z(y, y0, y1) for y in ys]
            add_line(xs, ys, zs, width=4)

    for s in range(span_count):
        y0 = s * bay_width
        y1 = (s + 1) * bay_width

        for y in [y0, y1]:
            add_line([0, design_length], [y, y], [eave_height, eave_height], width=3)

        for frac in [0.25, 0.5, 0.75]:
            y = y0 + bay_width * frac
            z = arch_z(y, y0, y1)
            add_line([0, design_length], [y, y], [z, z], width=3)

    add_line(
        [0, design_length, design_length, 0, 0],
        [0, 0, total_width, total_width, 0],
        [0, 0, 0, 0, 0],
        width=2
    )

    if span_count > 1:
        for s in range(1, span_count):
            y = s * bay_width
            add_line([0, design_length], [y, y], [0, 0], width=2)

    add_text(design_length / 2, total_width / 2, ridge_height + 0.5, f"동고 {ridge_height:.2f} m")
    add_text(design_length / 2, -total_width * 0.08, 0, f"길이 {design_length:.2f} m")
    add_text(design_length + design_length * 0.05, total_width / 2, 0, f"폭 {total_width:.2f} m")
    add_text(0, total_width + total_width * 0.05, eave_height, f"처마높이 {eave_height:.2f} m")

    fig.update_layout(
        title=f"3D 온실 와이어프레임 모델 - {greenhouse_type}",
        height=720,
        margin=dict(l=0, r=0, t=50, b=0),
        scene=dict(
            xaxis_title="길이 X [m]",
            yaxis_title="폭 Y [m]",
            zaxis_title="높이 Z [m]",
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=1.4, z=0.9))
        )
    )

    state["drawing_fig"] = fig
    return state


# =========================================================
# 7. 예비 해석 결과 Agent
# =========================================================
def analysis_agent(state: DesignState):
    if state["missing_fields"]:
        state["analysis_result"] = {}
        return state

    total_width = state["total_width"]
    design_length = state["design_length"]
    eave_height = state["eave_height"]
    ridge_height = state["ridge_height"]
    frame_spacing = state["frame_spacing"]
    span_count = state["span_count"]
    frame_count = state["frame_count"]

    roof_rise = ridge_height - eave_height
    bay_width = total_width / span_count

    # 아치 길이 근사
    samples = 80
    arch_len_per_span = 0.0

    def arch_z_local(y):
        center = bay_width / 2
        half = bay_width / 2
        ratio = (y - center) / half
        return eave_height + roof_rise * (1 - ratio ** 2)

    prev_y = 0
    prev_z = arch_z_local(prev_y)

    for i in range(1, samples + 1):
        y = bay_width * i / samples
        z = arch_z_local(y)
        arch_len_per_span += math.sqrt((y - prev_y) ** 2 + (z - prev_z) ** 2)
        prev_y = y
        prev_z = z

    frame_pipe_length = frame_count * span_count * (arch_len_per_span + 2 * eave_height)
    purlin_count_per_span = 5
    purlin_length = design_length * purlin_count_per_span * span_count
    total_pipe_length = frame_pipe_length + purlin_length

    # 아주 간단한 예비 하중 산정
    q_snow = 0.5
    if state["region"] in ["강원", "평창", "대관령"]:
        q_snow = 1.2
    elif state["region"] in ["제주", "서귀포", "제주시"]:
        q_snow = 0.3

    V = 30.0
    if state["region"] in ["포항", "부산", "울산", "제주", "서귀포", "제주시"]:
        V = 35.0

    rho = 1.225
    q_wind_pa = 0.5 * rho * V ** 2
    q_wind_kn = q_wind_pa / 1000

    snow_line_load = q_snow * frame_spacing
    wind_line_load = q_wind_kn * 0.9 * frame_spacing

    rough_cost = total_pipe_length * 13

    if state["span_count"] >= 3 or state["design_length"] > 60:
        structural_note = "규모가 큰 편이므로 연동부, 기초, 풍하중 검토가 중요합니다."
    else:
        structural_note = "예비 규모상 일반적인 단동·소규모 연동 온실 검토 단계에 해당합니다."

    state["analysis_result"] = {
        "예상 총 파이프 길이 [m]": round(total_pipe_length, 2),
        "예상 프레임 파이프 길이 [m]": round(frame_pipe_length, 2),
        "예상 도리 길이 [m]": round(purlin_length, 2),
        "기본풍속 가정 [m/s]": V,
        "속도압 q [kN/m²]": round(q_wind_kn, 3),
        "예비 풍하중 선하중 [kN/m]": round(wind_line_load, 3),
        "지상적설하중 가정 [kN/m²]": q_snow,
        "예비 적설 선하중 [kN/m]": round(snow_line_load, 3),
        "예상 자재비 지표 [CP]": round(rough_cost, 1),
        "예비 구조검토 의견": structural_note,
        "주의": "현재 해석 결과는 예비 지표입니다. 실제 구조해석은 부재, 절점, 하중조합, 좌굴 검토를 별도 계산해야 합니다."
    }

    return state


# =========================================================
# 8. LangGraph 구성
# =========================================================
def build_graph():
    graph = StateGraph(DesignState)

    graph.add_node("parse_request_agent", parse_request_agent)
    graph.add_node("recommendation_agent", recommendation_agent)
    graph.add_node("drawing_agent", drawing_agent)
    graph.add_node("analysis_agent", analysis_agent)

    graph.set_entry_point("parse_request_agent")

    graph.add_edge("parse_request_agent", "recommendation_agent")
    graph.add_edge("recommendation_agent", "drawing_agent")
    graph.add_edge("drawing_agent", "analysis_agent")
    graph.add_edge("analysis_agent", END)

    return graph.compile()


def run_design(user_prompt: str):
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
        "analysis_result": {},
        "drawing_fig": None,
        "response_text": "",
    }

    return app.invoke(input_state)


# =========================================================
# 9. 화면 헤더
# =========================================================
st.markdown(
    """
    <div class="app-header">
        <h1>자연어 기반 온실 예비설계 및 구조검토 시스템</h1>
        <p>지역·작물·규모를 자연어로 입력하면 조건을 추출하고, 온실 추천안과 3D 설계 모델을 생성합니다.</p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 10. 세션 상태
# =========================================================
if "screen" not in st.session_state:
    st.session_state["screen"] = "design"

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if "user_prompt" not in st.session_state:
    st.session_state["user_prompt"] = "포항에서 딸기 재배용으로 100평 규모 온실 추천해줘"


# =========================================================
# 11. 상단 버튼형 화면 이동
# =========================================================
nav1, nav2, nav3 = st.columns(3)

with nav1:
    if st.button("1  설계·부재 선택\n\n자연어 입력, 추천안, 3D 모델", use_container_width=True):
        st.session_state["screen"] = "design"

with nav2:
    if st.button("2  재료·비용\n\nS1~S5 단면과 비용식 확인", use_container_width=True):
        st.session_state["screen"] = "materials"

with nav3:
    if st.button("3  해석 결과\n\n예비 하중·비용·구조검토 지표", use_container_width=True):
        st.session_state["screen"] = "results"

st.markdown('<div class="top-help">※ index.html의 4단계 화면 중 비교·제출 단계는 제외하고 3단계 구성으로 재배치했습니다.</div>', unsafe_allow_html=True)


# =========================================================
# 12. 1번 화면: 설계·부재 선택
# =========================================================
if st.session_state["screen"] == "design":
    left, right = st.columns([0.38, 0.62], gap="large")

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">1. 자연어 설계 조건</div>', unsafe_allow_html=True)

        st.markdown(
            """
            <div class="hint-box">
            예: <b>포항에서 딸기 재배용으로 100평 규모 온실 추천해줘</b><br>
            사용자의 문장에서 지역, 작물, 규모를 자동 추출합니다.
            </div>
            """,
            unsafe_allow_html=True
        )

        prompt = st.text_area(
            "자연어 입력",
            value=st.session_state["user_prompt"],
            height=120
        )

        if st.button("AI 추천안 생성", type="primary", use_container_width=True):
            st.session_state["user_prompt"] = prompt
            result = run_design(prompt)
            st.session_state["last_result"] = result

        if st.session_state["last_result"] is not None:
            result = st.session_state["last_result"]

            st.markdown("#### 조건 추출 결과")
            st.table([result["parsed_result"]])

            if result["recommendation_result"]:
                st.markdown("#### 추천 요약")
                st.success(result["response_text"])
            else:
                st.warning(result["response_text"])

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">2. 예비 하중 조건</div>', unsafe_allow_html=True)

        st.number_input("기본풍속 V [m/s]", value=30.0, step=1.0)
        st.number_input("지상적설하중 [kN/m²]", value=0.5, step=0.1)
        st.number_input("골조 간격 s [m]", value=0.6, step=0.1)

        st.markdown(
            """
            <div class="warn-box">
            현재 입력값은 예비 검토용입니다. 이후 지역별 기준 데이터베이스와 연결하면 자동 산정 방식으로 바꿀 수 있습니다.
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">3. 3D 구조 모델링 화면</div>', unsafe_allow_html=True)

        if st.session_state["last_result"] is not None and st.session_state["last_result"]["drawing_fig"] is not None:
            st.plotly_chart(
                st.session_state["last_result"]["drawing_fig"],
                use_container_width=True
            )
            st.caption("마우스로 회전, 확대, 축소할 수 있습니다. 프레임 수가 많을 경우 대표 프레임만 표시됩니다.")
        else:
            st.info("왼쪽에서 자연어 입력 후 `AI 추천안 생성`을 누르면 3D 설계 모델이 표시됩니다.")

        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state["last_result"] is not None and st.session_state["last_result"]["recommendation_result"]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">4. 온실 예비설계 추천안</div>', unsafe_allow_html=True)
            st.table([st.session_state["last_result"]["recommendation_result"]])
            st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 13. 2번 화면: 재료·비용
# =========================================================
elif st.session_state["screen"] == "materials":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">재료·비용 설정</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-note">
        <b>S1~S5는 예비 구조설계용 강관 단면 후보입니다.</b><br>
        단면적 A가 클수록 축응력은 작아지고, 단면2차모멘트 I가 클수록 좌굴 저항이 커집니다.
        단가가 높을수록 총비용은 증가합니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    sections = [
        ("S1", "경량", 2.5e-4, 1.5e-8, 9),
        ("S2", "보통", 4.0e-4, 4.0e-8, 13),
        ("S3", "중간강성", 6.0e-4, 9.0e-8, 18),
        ("S4", "고강성", 9.0e-4, 2.0e-7, 26),
        ("S5", "매우 고강성", 1.2e-3, 3.6e-7, 34),
    ]

    for col, (sid, desc, A, I, cost) in zip([c1, c2, c3, c4, c5], sections):
        with col:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(f"### {sid}")
            st.caption(desc)

            st.number_input(f"{sid} A [m²]", value=A, format="%.6f", key=f"{sid}_A")
            st.number_input(f"{sid} I [m⁴]", value=I, format="%.10f", key=f"{sid}_I")
            st.number_input(f"{sid} 단가 [CP/m]", value=float(cost), key=f"{sid}_cost")

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">공통 재료·판정값</div>', unsafe_allow_html=True)
        st.number_input("탄성계수 E [GPa]", value=200.0, step=10.0)
        st.number_input("허용응력 σallow [MPa]", value=150.0, step=10.0)
        st.number_input("좌굴 유효길이계수 K", value=1.0, step=0.1)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">비용식</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="section-note">
            C<sub>total</sub> = Σ c<sub>s(i)</sub>L<sub>i</sub> 
            + C<sub>m</sub>n<sub>m</sub> 
            + C<sub>j</sub>n<sub>j</sub> 
            + C<sub>R</sub>R
            </div>
            """,
            unsafe_allow_html=True
        )
        st.number_input("부재 제작비 Cm [CP/개]", value=3.0)
        st.number_input("접합부 비용 Cj [CP/절점]", value=5.0)
        st.number_input("수평반력 비용 CR [CP/kN]", value=0.2)
        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 14. 3번 화면: 해석 결과
# =========================================================
elif st.session_state["screen"] == "results":
    if st.session_state["last_result"] is None:
        st.warning("아직 추천안이 생성되지 않았습니다. 1번 화면에서 자연어 입력 후 추천안을 먼저 생성하세요.")
    else:
        result = st.session_state["last_result"]

        if not result["analysis_result"]:
            st.warning(result["response_text"])
        else:
            analysis = result["analysis_result"]
            rec = result["recommendation_result"]

            m1, m2, m3 = st.columns(3)

            with m1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                    <span>예상 총 파이프 길이</span>
                    <b>{analysis["예상 총 파이프 길이 [m]"]} m</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with m2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                    <span>예비 풍하중 선하중</span>
                    <b>{analysis["예비 풍하중 선하중 [kN/m]"]} kN/m</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with m3:
                st.markdown(
                    f"""
                    <div class="metric-card">
                    <span>예상 자재비 지표</span>
                    <b>{analysis["예상 자재비 지표 [CP]"]} CP</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            left, right = st.columns([0.62, 0.38], gap="large")

            with left:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">해석 결과 시각화</div>', unsafe_allow_html=True)

                if result["drawing_fig"] is not None:
                    st.plotly_chart(result["drawing_fig"], use_container_width=True)

                st.markdown(
                    """
                    <div class="hint-box">
                    현재는 예비 구조검토 단계입니다. 이후 이 화면에 LC1~LC5 하중조합, 축력, 응력비, 좌굴비, 변형 형상을 추가하면 됩니다.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

            with right:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-title">종합 판정</div>', unsafe_allow_html=True)

                st.markdown(
                    f"""
                    <div class="ok-box">
                    <b>예비 추천안 생성 완료</b><br>
                    {analysis["예비 구조검토 의견"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("#### 주요 추천 조건")
                st.table([{
                    "온실 형식": rec["추천 온실 형식"],
                    "폭 [m]": rec["추천 폭 [m]"],
                    "길이 [m]": rec["추천 길이 [m]"],
                    "동고 [m]": rec["동고 [m]"],
                    "프레임 수": rec["예상 프레임 수"],
                }])

                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">예비 하중·비용 산정 결과</div>', unsafe_allow_html=True)
            st.table([analysis])
            st.markdown('</div>', unsafe_allow_html=True)
