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
    page_title="자연어 기반 온실 예비설계 시스템",
    layout="wide"
)


# =========================================================
# 2. CSS 스타일
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    .app-header {
        background: linear-gradient(135deg, #0f172a, #1d4ed8);
        color: white;
        padding: 24px 30px;
        border-radius: 18px;
        margin-bottom: 18px;
        border-bottom: 4px solid #93c5fd;
    }

    .app-header h1 {
        margin: 0;
        font-size: 30px;
        font-weight: 900;
        line-height: 1.25;
    }

    .app-header p {
        margin: 8px 0 0;
        color: #dbeafe;
        font-size: 15px;
        font-weight: 500;
    }

    .section-title {
        font-size: 22px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 10px;
    }

    .sub-title {
        font-size: 17px;
        font-weight: 800;
        color: #111827;
        margin-top: 8px;
        margin-bottom: 8px;
    }

    .desc {
        font-size: 14px;
        color: #64748b;
        line-height: 1.55;
    }

    .hint-box {
        background: #eef2ff;
        border-left: 5px solid #2563eb;
        padding: 12px 14px;
        border-radius: 10px;
        margin: 10px 0 16px 0;
        font-size: 14px;
        line-height: 1.6;
        color: #1f2937;
    }

    .warn-box {
        background: #fef3c7;
        border-left: 5px solid #d97706;
        padding: 12px 14px;
        border-radius: 10px;
        margin: 10px 0 16px 0;
        font-size: 14px;
        line-height: 1.6;
        color: #1f2937;
    }

    .ok-box {
        background: #d1fae5;
        border-left: 5px solid #059669;
        padding: 12px 14px;
        border-radius: 10px;
        margin: 10px 0 16px 0;
        font-size: 14px;
        line-height: 1.6;
        color: #064e3b;
    }

    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
        min-height: 96px;
        margin-bottom: 10px;
    }

    .metric-card span {
        display: block;
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .metric-card b {
        display: block;
        font-size: 22px;
        color: #0f172a;
        font-weight: 900;
        line-height: 1.25;
    }

    .metric-card small {
        display: block;
        margin-top: 6px;
        color: #64748b;
        font-size: 12px;
        line-height: 1.45;
    }

    .info-card {
        background: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
        margin-bottom: 14px;
    }

    .info-card h3 {
        margin: 0 0 12px 0;
        font-size: 20px;
        font-weight: 900;
        color: #111827;
    }

    .pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #dbeafe;
        color: #1e40af;
        font-size: 13px;
        font-weight: 800;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    .big-result {
        background: linear-gradient(135deg, #eff6ff, #ffffff);
        border: 1px solid #bfdbfe;
        border-radius: 18px;
        padding: 20px 22px;
        margin-bottom: 16px;
    }

    .big-result h2 {
        font-size: 25px;
        font-weight: 900;
        color: #0f172a;
        margin: 0 0 8px 0;
    }

    .big-result p {
        font-size: 15px;
        color: #334155;
        line-height: 1.6;
        margin: 0;
    }

    div[data-testid="stButton"] > button {
        font-weight: 800;
        border-radius: 12px;
        min-height: 48px;
    }

    label {
        font-weight: 800 !important;
        color: #111827 !important;
        font-size: 14px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. State 정의
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

    external_cp: float
    internal_cp: float
    net_cp: float
    coeff_result: Dict[str, Any]
    load_result: Dict[str, Any]
    
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
        "지역": region if region else "미입력",
        "작물": crop if crop else "미입력",
        "규모": f"{area_value:g} {area_unit}" if area_value > 0 else "미입력",
        "환산 면적 [m²]": round(area_m2, 2) if area_m2 > 0 else "미입력",
        "부족한 조건": ", ".join(missing_fields) if missing_fields else "없음"
    }

    return state


# =========================================================
# 5. 온실 추천안 Agent
# =========================================================
def recommendation_agent(state: DesignState):
    if state["missing_fields"]:
        state["recommendation_result"] = {}
        state["analysis_result"] = {}
        state["drawing_fig"] = None
        state["response_text"] = (
            "추천안을 생성하려면 다음 조건이 더 필요합니다: "
            + ", ".join(state["missing_fields"])
            + "\n\n예시: 포항에서 딸기 재배용으로 100평 규모 온실 추천해줘"
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
        reason_crop = "저상 재배 및 비교적 낮은 내부 공간 조건에 적합합니다."

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

        # -----------------------------------------------------
    # 온실 형식별 예비 풍압계수 자동 추천
    # -----------------------------------------------------
    opening_type = "일반 밀폐형"

    if crop in ["토마토", "파프리카", "오이"]:
        cpe_roof = -0.8
        cpe_wall_windward = 0.7
        cpe_wall_leeward = -0.5
        coeff_note = "고측고 온실은 지붕부 흡입압 영향이 커질 수 있어 지붕부 외압계수를 다소 보수적으로 적용했습니다."
    elif span_count >= 2:
        cpe_roof = -0.8
        cpe_wall_windward = 0.7
        cpe_wall_leeward = -0.5
        coeff_note = "연동형 온실은 지붕부와 연동부 주변의 풍압 검토가 중요하므로 지붕부 흡입압 기준으로 선정했습니다."
    else:
        cpe_roof = -0.7
        cpe_wall_windward = 0.7
        cpe_wall_leeward = -0.5
        coeff_note = "단동 아치형 온실의 예비검토용 대표 지붕부 외압계수로 선정했습니다."

    # 일반 밀폐형 기준 예비 내압계수
    cpi_candidates = [-0.2, 0.2]

    # 지붕 흡입압 검토에서는 Cpe - Cpi의 절댓값이 큰 조합 사용
    governing_cpi = 0.2
    net_cp = cpe_roof - governing_cpi

    for cpi in cpi_candidates:
        temp_net = cpe_roof - cpi
        if abs(temp_net) > abs(net_cp):
            governing_cpi = cpi
            net_cp = temp_net

    state["external_cp"] = cpe_roof
    state["internal_cp"] = governing_cpi
    state["net_cp"] = net_cp

    state["coeff_result"] = {
        "개방 조건": opening_type,
        "풍상측 벽면 외압계수": cpe_wall_windward,
        "풍하측 벽면 외압계수": cpe_wall_leeward,
        "대표 지붕부 외압계수 Cpe": cpe_roof,
        "내압계수 Cpi": governing_cpi,
        "순압계수 Cpe-Cpi": round(net_cp, 3),
        "선정 기준": coeff_note,
        "주의": "현재 풍압계수는 예비설계용 자동 추천값입니다. 최종 구조설계 시 적용 기준표 값으로 교체해야 합니다."
    }

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
        "연동 수": span_count,
        "처마높이 [m]": eave_height,
        "동고 [m]": ridge_height,
        "프레임 간격 [m]": frame_spacing,
        "예상 프레임 수": frame_count,
        "추천 주요 부재": member,
        "추천 피복재": covering,
        "대표 지붕부 외압계수 Cpe": cpe_roof,
        "내압계수 Cpi": governing_cpi,
        "순압계수 Cpe-Cpi": round(net_cp, 3),
        "풍압계수 선정 기준": coeff_note,
        "작물 기준 추천 이유": reason_crop,
        "지역 기준 검토사항": region_note,
    }

    state["response_text"] = (
        f"{region} 지역 {crop} 재배용 약 {area_pyung:.1f}평 규모의 "
        f"{greenhouse_type} 추천안입니다."
    )

    return state


# =========================================================
# 6. 3D 설계모델 Agent
# =========================================================
def drawing_agent(state: DesignState):
    if state["missing_fields"]:
        state["drawing_fig"] = None
        return state

    total_width = state["total_width"]
    design_length = state["design_length"]
    eave_height = state["eave_height"]
    ridge_height = state["ridge_height"]
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
    add_text(0, total_width + total_width * 0.05, eave_height, f"처마 {eave_height:.2f} m")

    fig.update_layout(
        title=f"3D 온실 설계 모델 - {greenhouse_type}",
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
# 7. 하중계산 및 예비 구조해석 Agent
# =========================================================
def analysis_agent(state: DesignState):
    if state["missing_fields"]:
        state["analysis_result"] = {}
        state["load_result"] = {}
        return state

    region = state["region"]
    total_width = state["total_width"]
    design_length = state["design_length"]
    eave_height = state["eave_height"]
    ridge_height = state["ridge_height"]
    frame_spacing = state["frame_spacing"]
    span_count = state["span_count"]
    frame_count = state["frame_count"]
    member = state["member"]

    # -----------------------------------------------------
    # 1. 기본 설계값 가정
    # -----------------------------------------------------
    V = 30.0
    ground_snow_load = 0.5

    if region in ["포항", "부산", "울산", "제주", "서귀포", "제주시"]:
        V = 35.0

    if region in ["강원", "평창", "대관령"]:
        ground_snow_load = 1.2
    elif region in ["제주", "서귀포", "제주시"]:
        ground_snow_load = 0.3

    rho = 1.225
    q_velocity_pa = 0.5 * rho * V ** 2
    q_velocity_kn = q_velocity_pa / 1000

    Cpe = state["external_cp"]
    Cpi = state["internal_cp"]
    net_cp = state["net_cp"]

    # -----------------------------------------------------
    # 2. 하중 산정
    # -----------------------------------------------------
    dead_load = 0.15  # kN/m², 피복재+파이프 자중 예비값
    snow_shape_factor = 0.8
    roof_snow_load = ground_snow_load * snow_shape_factor

    wind_pressure = q_velocity_kn * net_cp
    wind_pressure_abs = abs(wind_pressure)

    dead_line_load = dead_load * frame_spacing
    snow_line_load = roof_snow_load * frame_spacing
    wind_line_load = wind_pressure_abs * frame_spacing

    lc_dead = dead_line_load
    lc_dead_snow = dead_line_load + snow_line_load
    lc_wind_uplift = wind_line_load - dead_line_load
    lc_dead_snow_wind = dead_line_load + snow_line_load + wind_line_load

    # -----------------------------------------------------
    # 3. 단순 등가 구조해석
    #    1개 연동 폭을 단순보 등가 경간으로 보고 예비 모멘트 산정
    # -----------------------------------------------------
    span_width = total_width / span_count
    h = ridge_height

    # 지배 수직하중: D + S
    w_vertical = lc_dead_snow
    max_shear = w_vertical * span_width / 2
    max_moment = w_vertical * span_width ** 2 / 8

    # 풍하중에 의한 수평 전단 및 전도 모멘트 예비값
    lateral_shear = wind_line_load * h
    overturning_moment = wind_line_load * h ** 2 / 2

    # -----------------------------------------------------
    # 4. 부재 단면 예비 검토
    # -----------------------------------------------------
    def pipe_properties(member_text):
        if "42.7" in member_text:
            D = 0.0427
            t = 0.0021
        elif "31.8" in member_text:
            D = 0.0318
            t = 0.0015
        else:
            D = 0.0318
            t = 0.0015

        d = D - 2 * t
        A = math.pi / 4 * (D ** 2 - d ** 2)
        I = math.pi / 64 * (D ** 4 - d ** 4)
        Z = I / (D / 2)
        return D, t, A, I, Z

    D, t, A, I, Z = pipe_properties(member)

    sigma_allow = 150000  # kN/m² = 150 MPa
    moment_capacity = sigma_allow * Z
    moment_ratio = max_moment / moment_capacity if moment_capacity > 0 else 999

    E = 200_000_000  # kN/m²
    K = 1.0
    effective_length = max(span_width / 2, 1.0)
    p_cr = math.pi ** 2 * E * I / (K * effective_length) ** 2

    # 단순 압축력 추정
    estimated_compression = max_shear
    buckling_ratio = estimated_compression / p_cr if p_cr > 0 else 999

    utilization = max(moment_ratio, buckling_ratio)

    if utilization <= 0.7:
        safety_status = "OK"
        safety_note = "예비 검토상 여유가 있는 설계안입니다."
    elif utilization <= 1.0:
        safety_status = "주의"
        safety_note = "예비 검토상 한계에 가까운 설계안입니다. 최종 구조해석이 필요합니다."
    else:
        safety_status = "검토 필요"
        safety_note = "예비 검토상 부재 보강 또는 프레임 간격 조정이 필요할 수 있습니다."

    # -----------------------------------------------------
    # 5. 자재 길이 산정
    # -----------------------------------------------------
    roof_rise = ridge_height - eave_height
    bay_width = span_width

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

    state["load_result"] = {
        "기본풍속 V [m/s]": V,
        "속도압 q [kN/m²]": round(q_velocity_kn, 3),
        "대표 지붕부 외압계수 Cpe": Cpe,
        "내압계수 Cpi": Cpi,
        "순압계수 Cpe-Cpi": round(net_cp, 3),
        "설계 풍압 p [kN/m²]": round(wind_pressure, 3),
        "풍하중 선하중 [kN/m]": round(wind_line_load, 3),
        "고정하중 [kN/m²]": dead_load,
        "고정하중 선하중 [kN/m]": round(dead_line_load, 3),
        "지상적설하중 [kN/m²]": ground_snow_load,
        "지붕형상계수": snow_shape_factor,
        "지붕적설하중 [kN/m²]": round(roof_snow_load, 3),
        "적설하중 선하중 [kN/m]": round(snow_line_load, 3),
        "LC1 D [kN/m]": round(lc_dead, 3),
        "LC2 D+S [kN/m]": round(lc_dead_snow, 3),
        "LC3 W-D 상향 [kN/m]": round(lc_wind_uplift, 3),
        "LC4 D+S+W [kN/m]": round(lc_dead_snow_wind, 3),
    }

    state["analysis_result"] = {
        "검토 경간 [m]": round(span_width, 3),
        "지배 수직하중 D+S [kN/m]": round(w_vertical, 3),
        "최대 전단력 Vmax [kN]": round(max_shear, 3),
        "최대 휨모멘트 Mmax [kN·m]": round(max_moment, 3),
        "풍하중 수평전단 예비값 [kN]": round(lateral_shear, 3),
        "풍하중 전도모멘트 예비값 [kN·m]": round(overturning_moment, 3),
        "추천 부재": member,
        "파이프 외경 [mm]": round(D * 1000, 1),
        "파이프 두께 [mm]": round(t * 1000, 2),
        "단면적 A [m²]": round(A, 8),
        "단면2차모멘트 I [m⁴]": round(I, 12),
        "단면계수 Z [m³]": round(Z, 10),
        "예비 휨내력 [kN·m]": round(moment_capacity, 3),
        "휨 검토비 M/Ma": round(moment_ratio, 3),
        "Euler 좌굴하중 Pcr [kN]": round(p_cr, 3),
        "좌굴 검토비 N/Pcr": round(buckling_ratio, 3),
        "최대 활용률": round(utilization, 3),
        "예비 판정": safety_status,
        "예비 구조검토 의견": safety_note,
        "예상 총 파이프 길이 [m]": round(total_pipe_length, 2),
        "예상 프레임 파이프 길이 [m]": round(frame_pipe_length, 2),
        "예상 도리 길이 [m]": round(purlin_length, 2),
        "주의": "현재 구조해석은 예비 단순해석입니다. 최종 설계에는 실제 프레임 구조해석, 하중조합, 좌굴길이, 접합부 검토가 필요합니다."
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

        "external_cp": 0.0,
        "internal_cp": 0.0,
        "net_cp": 0.0,
        "coeff_result": {},
        "load_result": {},

        "parsed_result": {},
        "recommendation_result": {},
        "analysis_result": {},
        "drawing_fig": None,
        "response_text": "",
    }

    return app.invoke(input_state)


# =========================================================
# 9. 유틸 출력 함수
# =========================================================
def metric_card(title, value, note=""):
    note_html = f"<small>{note}</small>" if note else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <span>{title}</span>
            <b>{value}</b>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def info_card(title, body):
    st.markdown(
        f"""
        <div class="info-card">
            <h3>{title}</h3>
            <div class="desc">{body}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 10. 화면 헤더
# =========================================================
st.markdown(
    """
    <div class="app-header">
        <h1>자연어 기반 온실 예비설계 시스템</h1>
        <p>지역·작물·규모를 자연어로 입력하면 조건을 추출하고, 온실 추천안과 3D 설계 모델을 생성합니다.</p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 11. 세션 상태
# =========================================================
if "screen" not in st.session_state:
    st.session_state["screen"] = "design"

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if "user_prompt" not in st.session_state:
    st.session_state["user_prompt"] = "포항에서 딸기 재배용으로 100평 규모 온실 추천해줘"


# =========================================================
# 12. 상단 화면 버튼
# =========================================================
nav1, nav2, nav3 = st.columns(3)

with nav1:
    if st.button("1. 설계 조건", use_container_width=True):
        st.session_state["screen"] = "design"

with nav2:
    if st.button("2. 추천안 · 3D 모델", use_container_width=True):
        st.session_state["screen"] = "recommend"

with nav3:
    if st.button("3. 예비 검토 결과", use_container_width=True):
        st.session_state["screen"] = "results"


# =========================================================
# 13. 1번 화면: 설계 조건
# =========================================================
if st.session_state["screen"] == "design":
    left, right = st.columns([0.36, 0.64], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="section-title">1. 설계 조건</div>', unsafe_allow_html=True)

            st.markdown(
                """
                <div class="hint-box">
                <b>입력 예시</b><br>
                포항에서 딸기 재배용으로 100평 규모 온실 추천해줘
                </div>
                """,
                unsafe_allow_html=True
            )

            prompt = st.text_area(
                "자연어 입력",
                value=st.session_state["user_prompt"],
                height=140,
                placeholder="예: 대구에서 토마토 200평 규모 온실 추천해줘"
            )

            run_btn = st.button("AI 추천안 생성", type="primary", use_container_width=True)

            if run_btn:
                st.session_state["user_prompt"] = prompt
                st.session_state["last_result"] = run_design(prompt)
                st.session_state["screen"] = "recommend"
                st.rerun()

    with right:
        with st.container(border=True):
            st.markdown('<div class="section-title">조건 추출 결과</div>', unsafe_allow_html=True)

            if st.session_state["last_result"] is None:
                st.info("왼쪽에 자연어 조건을 입력하고 `AI 추천안 생성`을 눌러주세요.")
            else:
                result = st.session_state["last_result"]
                parsed = result["parsed_result"]

                c1, c2, c3, c4 = st.columns(4)

                with c1:
                    metric_card("지역", parsed["지역"])

                with c2:
                    metric_card("작물", parsed["작물"])

                with c3:
                    metric_card("입력 규모", parsed["규모"])

                with c4:
                    metric_card("환산 면적", f'{parsed["환산 면적 [m²]"]} m²')

                if parsed["부족한 조건"] != "없음":
                    st.warning(f'부족한 조건: {parsed["부족한 조건"]}')
                else:
                    st.success("지역, 작물, 규모가 모두 추출되었습니다.")

                st.markdown("#### 입력 문장")
                st.write(parsed["입력 문장"])


# =========================================================
# 14. 2번 화면: 추천안 · 3D 모델
# =========================================================
elif st.session_state["screen"] == "recommend":
    if st.session_state["last_result"] is None:
        st.warning("아직 추천안이 생성되지 않았습니다. 1번 화면에서 자연어 입력 후 추천안을 생성하세요.")
    else:
        result = st.session_state["last_result"]

        if not result["recommendation_result"]:
            st.warning(result["response_text"])
        else:
            rec = result["recommendation_result"]

            st.markdown(
                f"""
                <div class="big-result">
                    <h2>{rec["추천 온실 형식"]}</h2>
                    <p>
                    {rec["지역"]} 지역에서 {rec["작물"]} 재배를 위한 
                    {rec["요구 규모"]} 규모의 예비 온실 추천안입니다.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                metric_card("추천 폭", f'{rec["추천 폭 [m]"]} m')

            with c2:
                metric_card("추천 길이", f'{rec["추천 길이 [m]"]} m')

            with c3:
                metric_card("동고", f'{rec["동고 [m]"]} m')

            with c4:
                metric_card("프레임 수", f'{rec["예상 프레임 수"]} 개')

            left, right = st.columns([0.38, 0.62], gap="large")

            with left:
                with st.container(border=True):
                    st.markdown('<div class="section-title">온실 예비설계 추천안</div>', unsafe_allow_html=True)

                    st.markdown(
                        f"""
                        <span class="pill">지역: {rec["지역"]}</span>
                        <span class="pill">작물: {rec["작물"]}</span>
                        <span class="pill">연동 수: {rec["연동 수"]}</span>
                        """,
                        unsafe_allow_html=True
                    )

                    st.divider()

                    st.markdown("#### 주요 규격")
                    st.write(f'**요구 면적:** {rec["요구 면적 [m²]"]} m²')
                    st.write(f'**예상 설계면적:** {rec["예상 설계면적 [m²]"]} m²')
                    st.write(f'**처마높이:** {rec["처마높이 [m]"]} m')
                    st.write(f'**프레임 간격:** {rec["프레임 간격 [m]"]} m')

                    st.divider()

                    st.markdown("#### 풍압계수 자동 추천")
                    st.write(f'**대표 지붕부 외압계수 Cpe:** {rec["대표 지붕부 외압계수 Cpe"]}')
                    st.write(f'**내압계수 Cpi:** {rec["내압계수 Cpi"]}')
                    st.write(f'**순압계수 Cpe-Cpi:** {rec["순압계수 Cpe-Cpi"]}')
                    st.caption(rec["풍압계수 선정 기준"])
                    
                    st.markdown("#### 자재 방향")
                    st.write(f'**추천 주요 부재:** {rec["추천 주요 부재"]}')
                    st.write(f'**추천 피복재:** {rec["추천 피복재"]}')

                    st.divider()

                    st.markdown("#### 추천 근거")
                    st.write(f'**작물 기준:** {rec["작물 기준 추천 이유"]}')
                    st.write(f'**지역 기준:** {rec["지역 기준 검토사항"]}')

            with right:
                with st.container(border=True):
                    st.markdown('<div class="section-title">3D 설계 모델</div>', unsafe_allow_html=True)

                    if result["drawing_fig"] is not None:
                        st.plotly_chart(result["drawing_fig"], use_container_width=True)
                        st.caption("마우스로 회전, 확대, 축소할 수 있습니다.")
                    else:
                        st.info("추천안이 생성되면 3D 모델이 표시됩니다.")


# =========================================================
# 15. 3번 화면: 하중계산 및 구조해석 결과
# =========================================================
elif st.session_state["screen"] == "results":
    if st.session_state["last_result"] is None:
        st.warning("아직 추천안이 생성되지 않았습니다. 1번 화면에서 자연어 입력 후 추천안을 생성하세요.")
    else:
        result = st.session_state["last_result"]

        if not result["analysis_result"]:
            st.warning(result["response_text"])
        else:
            load = result["load_result"]
            analysis = result["analysis_result"]

            st.markdown('<div class="section-title">하중계산 및 예비 구조해석 결과</div>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                metric_card(
                    "풍하중 선하중",
                    f'{load["풍하중 선하중 [kN/m]"]} kN/m',
                    f'Cpe-Cpi = {load["순압계수 Cpe-Cpi"]}'
                )

            with c2:
                metric_card(
                    "적설하중 선하중",
                    f'{load["적설하중 선하중 [kN/m]"]} kN/m',
                    f'지붕적설하중 = {load["지붕적설하중 [kN/m²]"]} kN/m²'
                )

            with c3:
                metric_card(
                    "고정하중 선하중",
                    f'{load["고정하중 선하중 [kN/m]"]} kN/m',
                    f'고정하중 = {load["고정하중 [kN/m²]"]} kN/m²'
                )

            with c4:
                metric_card(
                    "예비 판정",
                    analysis["예비 판정"],
                    f'최대 활용률 = {analysis["최대 활용률"]}'
                )

            left, right = st.columns([0.58, 0.42], gap="large")

            with left:
                with st.container(border=True):
                    st.markdown('<div class="section-title">하중 산정 결과</div>', unsafe_allow_html=True)

                    st.markdown("#### 풍하중 계산")
                    st.write(f'**기본풍속 V:** {load["기본풍속 V [m/s]"]} m/s')
                    st.write(f'**속도압 q:** {load["속도압 q [kN/m²]"]} kN/m²')
                    st.write(f'**외압계수 Cpe:** {load["대표 지붕부 외압계수 Cpe"]}')
                    st.write(f'**내압계수 Cpi:** {load["내압계수 Cpi"]}')
                    st.write(f'**설계 풍압 p = q × (Cpe-Cpi):** {load["설계 풍압 p [kN/m²]"]} kN/m²')
                    st.write(f'**풍하중 선하중:** {load["풍하중 선하중 [kN/m]"]} kN/m')

                    st.divider()

                    st.markdown("#### 고정하중 · 적설하중 계산")
                    st.write(f'**고정하중:** {load["고정하중 [kN/m²]"]} kN/m²')
                    st.write(f'**고정하중 선하중:** {load["고정하중 선하중 [kN/m]"]} kN/m')
                    st.write(f'**지상적설하중:** {load["지상적설하중 [kN/m²]"]} kN/m²')
                    st.write(f'**지붕형상계수:** {load["지붕형상계수"]}')
                    st.write(f'**지붕적설하중:** {load["지붕적설하중 [kN/m²]"]} kN/m²')
                    st.write(f'**적설하중 선하중:** {load["적설하중 선하중 [kN/m]"]} kN/m')

                    st.divider()

                    st.markdown("#### 하중조합")
                    st.table([{
                        "LC1 D": load["LC1 D [kN/m]"],
                        "LC2 D+S": load["LC2 D+S [kN/m]"],
                        "LC3 W-D 상향": load["LC3 W-D 상향 [kN/m]"],
                        "LC4 D+S+W": load["LC4 D+S+W [kN/m]"],
                    }])

            with right:
                with st.container(border=True):
                    st.markdown('<div class="section-title">예비 구조해석</div>', unsafe_allow_html=True)

                    if analysis["예비 판정"] == "OK":
                        st.success(analysis["예비 구조검토 의견"])
                    elif analysis["예비 판정"] == "주의":
                        st.warning(analysis["예비 구조검토 의견"])
                    else:
                        st.error(analysis["예비 구조검토 의견"])

                    st.markdown("#### 부재 검토")
                    st.write(f'**추천 부재:** {analysis["추천 부재"]}')
                    st.write(f'**파이프 외경:** {analysis["파이프 외경 [mm]"]} mm')
                    st.write(f'**파이프 두께:** {analysis["파이프 두께 [mm]"]} mm')
                    st.write(f'**검토 경간:** {analysis["검토 경간 [m]"]} m')

                    st.divider()

                    st.markdown("#### 구조해석 지표")
                    st.write(f'**최대 전단력 Vmax:** {analysis["최대 전단력 Vmax [kN]"]} kN')
                    st.write(f'**최대 휨모멘트 Mmax:** {analysis["최대 휨모멘트 Mmax [kN·m]"]} kN·m')
                    st.write(f'**예비 휨내력:** {analysis["예비 휨내력 [kN·m]"]} kN·m')
                    st.write(f'**휨 검토비 M/Ma:** {analysis["휨 검토비 M/Ma"]}')
                    st.write(f'**Euler 좌굴하중 Pcr:** {analysis["Euler 좌굴하중 Pcr [kN]"]} kN')
                    st.write(f'**좌굴 검토비 N/Pcr:** {analysis["좌굴 검토비 N/Pcr"]}')
                    st.write(f'**최대 활용률:** {analysis["최대 활용률"]}')

            with st.expander("전체 하중계산 결과 보기"):
                st.table([load])

            with st.expander("전체 구조해석 결과 보기"):
                st.table([analysis])
