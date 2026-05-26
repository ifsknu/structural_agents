import streamlit as st
import streamlit.components.v1 as components
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
import math


# =========================================================
# 1. 페이지 기본 설정
# =========================================================
st.set_page_config(
    page_title="비닐하우스 구조설계 다중에이전트 시스템",
    layout="wide"
)


# =========================================================
# 2. LangGraph State 정의
# =========================================================
class DesignState(TypedDict):
    region: str
    crop: str
    house_type: str

    width: float
    length: float
    eave_height: float
    ridge_height: float
    frame_spacing: float

    basic_wind_speed: float
    wind_direction: str
    opening_type: str
    ground_snow_load: float

    external_cp: float
    internal_cp: float
    net_cp: float

    preliminary_result: Dict[str, Any]
    drawing_svg: str
    coeff_result: Dict[str, Any]
    load_result: Dict[str, Any]
    analysis_result: Dict[str, Any]
    safety_result: Dict[str, Any]
    summary_text: str

# =========================================================
# 3. 예비설계 Agent
# =========================================================
def preliminary_design_agent(state: DesignState):
    width = state["width"]
    length = state["length"]
    eave_height = state["eave_height"]
    ridge_height = state["ridge_height"]
    frame_spacing = state["frame_spacing"]

    frame_count = int(length / frame_spacing) + 1
    floor_area = width * length

    # 간단 추천 로직
    if state["crop"] in ["딸기", "상추"]:
        recommended_member = "Ø31.8 × 1.5t"
    elif state["crop"] in ["토마토", "파프리카"]:
        recommended_member = "Ø42.7 × 2.1t"
    else:
        recommended_member = "검토 필요"

    state["preliminary_result"] = {
        "지역": state["region"],
        "작물": state["crop"],
        "온실 형식": state["house_type"],
        "폭 B [m]": width,
        "길이 L [m]": length,
        "처마높이 [m]": eave_height,
        "동고 [m]": ridge_height,
        "프레임 간격 [m]": frame_spacing,
        "예상 프레임 수": frame_count,
        "바닥면적 [m²]": round(floor_area, 2),
        "추천 부재": recommended_member,
    }

    return state


# =========================================================
# 4. 설계도면 시각화 Agent
# =========================================================
def drawing_agent(state: DesignState):
    width = state["width"]
    length = state["length"]
    eave_height = state["eave_height"]
    ridge_height = state["ridge_height"]
    frame_spacing = state["frame_spacing"]

    # -----------------------------
    # 3D 등각투영 좌표 변환 함수
    # -----------------------------
    ox = 100
    oy = 280
    sx = 10
    sy = 18
    sz = 45

    def proj(x, y, z):
        X = ox + x * sx + y * sy
        Y = oy + x * 0.35 * sx - y * 0.35 * sy - z * sz
        return X, Y

    def arch_z(y):
        # 포물선형 아치 지붕
        half = width / 2
        center = width / 2
        roof_rise = ridge_height - eave_height
        ratio = (y - center) / half
        return eave_height + roof_rise * (1 - ratio ** 2)

    # 표시할 프레임 위치
    frame_count = int(length / frame_spacing) + 1
    max_frames = min(frame_count, 16)

    if max_frames <= 1:
        x_positions = [0, length]
    else:
        x_positions = [
            length * i / (max_frames - 1)
            for i in range(max_frames)
        ]

    y_positions = [
        width * i / 12
        for i in range(13)
    ]

    # 3D 아치 프레임
    frame_svg = ""

    for x in x_positions:
        pts = []

        # 좌측 기둥
        X0, Y0 = proj(x, 0, 0)
        X1, Y1 = proj(x, 0, eave_height)
        frame_svg += f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y1}" class="model-line"/>'

        # 지붕 아치
        for y in y_positions:
            z = arch_z(y)
            X, Y = proj(x, y, z)
            pts.append(f"{X},{Y}")

        frame_svg += f'<polyline points="{" ".join(pts)}" class="model-line"/>'

        # 우측 기둥
        X2, Y2 = proj(x, width, eave_height)
        X3, Y3 = proj(x, width, 0)
        frame_svg += f'<line x1="{X2}" y1="{Y2}" x2="{X3}" y2="{Y3}" class="model-line"/>'

    # 길이 방향 연결선
    longitudinal_svg = ""

    for y in [0, width / 2, width]:
        pts = []
        for x in x_positions:
            z = arch_z(y)
            X, Y = proj(x, y, z)
            pts.append(f"{X},{Y}")
        longitudinal_svg += f'<polyline points="{" ".join(pts)}" class="long-line"/>'

    # 바닥 외곽선
    floor_pts = [
        proj(0, 0, 0),
        proj(length, 0, 0),
        proj(length, width, 0),
        proj(0, width, 0),
        proj(0, 0, 0),
    ]

    floor_svg = ""
    for i in range(len(floor_pts) - 1):
        x1, y1 = floor_pts[i]
        x2, y2 = floor_pts[i + 1]
        floor_svg += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="floor-line"/>'

    # -----------------------------
    # 2D 도면 좌표
    # -----------------------------
    scale_front = 38
    scale_side = 7
    scale_plan = 7

    W = width * scale_front
    EH = eave_height * scale_front
    RH = ridge_height * scale_front
    L_side = length * scale_side
    L_plan = length * scale_plan
    W_plan = width * 22

    fx = 80
    fy = 560

    tx = 520
    ty = 560

    px = 80
    py = 760

    # 평면도 프레임선
    plan_frame_svg = ""
    visible_frames = min(frame_count, 20)

    if visible_frames > 1:
        for i in range(visible_frames):
            x = px + (L_plan / (visible_frames - 1)) * i
            plan_frame_svg += f"""
            <line x1="{x}" y1="{py}" x2="{x}" y2="{py + W_plan}" class="frame-line"/>
            """

    svg = f"""
    <svg width="1050" height="960" xmlns="http://www.w3.org/2000/svg">
        <style>
            .bg {{
                fill: #f9fafb;
                stroke: #d1d5db;
                stroke-width: 1.5;
                rx: 16;
            }}
            .title {{
                font: bold 18px sans-serif;
                fill: #111827;
            }}
            .subtitle {{
                font: bold 14px sans-serif;
                fill: #374151;
            }}
            .label {{
                font: 13px sans-serif;
                fill: #374151;
            }}
            .small {{
                font: 12px sans-serif;
                fill: #6b7280;
            }}
            .model-line {{
                stroke: #111827;
                stroke-width: 1.8;
                fill: none;
            }}
            .long-line {{
                stroke: #2563eb;
                stroke-width: 1.5;
                fill: none;
                opacity: 0.85;
            }}
            .floor-line {{
                stroke: #4b5563;
                stroke-width: 1.5;
                fill: none;
                stroke-dasharray: 5 3;
            }}
            .drawing-line {{
                stroke: #111827;
                stroke-width: 2;
                fill: none;
            }}
            .dim-line {{
                stroke: #6b7280;
                stroke-width: 1;
                stroke-dasharray: 4 3;
            }}
            .frame-line {{
                stroke: #9ca3af;
                stroke-width: 1;
                stroke-dasharray: 4 3;
            }}
        </style>

        <rect x="20" y="20" width="1010" height="900" class="bg"/>

        <!-- ===================== 3D 와이어프레임 ===================== -->
        <text x="60" y="60" class="title">GH Modeler형 3D 와이어프레임 개념도</text>
        <text x="60" y="85" class="small">
            입력된 폭, 길이, 처마높이, 동고, 프레임 간격에 따라 자동 생성되는 파라메트릭 형상입니다.
        </text>

        {floor_svg}
        {frame_svg}
        {longitudinal_svg}

        <text x="690" y="110" class="subtitle">입력 형상 정보</text>
        <text x="690" y="140" class="label">폭 B = {width:.2f} m</text>
        <text x="690" y="165" class="label">길이 L = {length:.2f} m</text>
        <text x="690" y="190" class="label">처마높이 = {eave_height:.2f} m</text>
        <text x="690" y="215" class="label">동고 = {ridge_height:.2f} m</text>
        <text x="690" y="240" class="label">프레임 간격 = {frame_spacing:.2f} m</text>
        <text x="690" y="265" class="label">예상 프레임 수 = {frame_count} 개</text>

        <!-- ===================== 정면도 ===================== -->
        <text x="80" y="430" class="title">정면도</text>

        <line x1="{fx - 20}" y1="{fy}" x2="{fx + W + 20}" y2="{fy}" class="drawing-line"/>
        <line x1="{fx}" y1="{fy}" x2="{fx}" y2="{fy - EH}" class="drawing-line"/>
        <line x1="{fx + W}" y1="{fy}" x2="{fx + W}" y2="{fy - EH}" class="drawing-line"/>
        <path d="M {fx} {fy - EH} Q {fx + W / 2} {fy - RH} {fx + W} {fy - EH}" class="drawing-line"/>

        <line x1="{fx + W / 2}" y1="{fy}" x2="{fx + W / 2}" y2="{fy - RH}" class="dim-line"/>
        <text x="{fx + W / 2 - 40}" y="{fy + 35}" class="label">폭 = {width:.2f} m</text>
        <text x="{fx + W + 15}" y="{fy - EH / 2}" class="label">처마높이 = {eave_height:.2f} m</text>
        <text x="{fx + W / 2 - 40}" y="{fy - RH - 12}" class="label">동고 = {ridge_height:.2f} m</text>

        <!-- ===================== 측면도 ===================== -->
        <text x="520" y="430" class="title">측면도</text>

        <line x1="{tx - 20}" y1="{ty}" x2="{tx + L_side + 20}" y2="{ty}" class="drawing-line"/>
        <line x1="{tx}" y1="{ty}" x2="{tx}" y2="{ty - EH}" class="drawing-line"/>
        <line x1="{tx + L_side}" y1="{ty}" x2="{tx + L_side}" y2="{ty - EH}" class="drawing-line"/>
        <line x1="{tx}" y1="{ty - EH}" x2="{tx + L_side}" y2="{ty - EH}" class="drawing-line"/>

        <line x1="{tx + L_side * 0.25}" y1="{ty}" x2="{tx + L_side * 0.25}" y2="{ty - EH}" class="frame-line"/>
        <line x1="{tx + L_side * 0.50}" y1="{ty}" x2="{tx + L_side * 0.50}" y2="{ty - EH}" class="frame-line"/>
        <line x1="{tx + L_side * 0.75}" y1="{ty}" x2="{tx + L_side * 0.75}" y2="{ty - EH}" class="frame-line"/>

        <text x="{tx + L_side / 2 - 45}" y="{ty + 35}" class="label">길이 = {length:.2f} m</text>
        <text x="{tx + 10}" y="{ty - EH - 15}" class="label">프레임 간격 = {frame_spacing:.2f} m</text>

        <!-- ===================== 평면도 ===================== -->
        <text x="80" y="700" class="title">평면도 / 프레임 배치도</text>

        <rect x="{px}" y="{py}" width="{L_plan}" height="{W_plan}" class="drawing-line"/>
        {plan_frame_svg}

        <text x="{px + L_plan / 2 - 45}" y="{py + W_plan + 35}" class="label">길이 = {length:.2f} m</text>
        <text x="{px + L_plan + 20}" y="{py + W_plan / 2}" class="label">폭 = {width:.2f} m</text>

        <text x="80" y="900" class="small">
            ※ 본 도면은 예비설계 단계의 파라메트릭 개념도이며, 실제 시공도면 및 구조도면은 상세 검토가 필요합니다.
        </text>
    </svg>
    """

    state["drawing_svg"] = svg
    return state

def coefficient_agent(state: DesignState):
    house_type = state["house_type"]
    wind_direction = state["wind_direction"]
    opening_type = state["opening_type"]

    # 예비설계용 자동 풍압계수표
    # 실제 기준표 값이 확정되면 이 표의 숫자만 교체하면 됨
    external_cp_table = {
        "10-단동-1형": {
            "정면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "지붕 풍상측": -0.7,
                "지붕 중앙부": -0.6,
                "지붕 풍하측": -0.4,
            },
            "측면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "측면 지붕부": -0.6,
            },
        },
        "아치형 단동": {
            "정면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "지붕 풍상측": -0.8,
                "지붕 중앙부": -0.7,
                "지붕 풍하측": -0.5,
            },
            "측면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "측면 지붕부": -0.7,
            },
        },
        "연동형": {
            "정면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "지붕 풍상측": -0.9,
                "지붕 중앙부": -0.7,
                "지붕 풍하측": -0.5,
            },
            "측면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "측면 지붕부": -0.7,
            },
        },
        "기타": {
            "정면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "지붕부": -0.7,
            },
            "측면 풍향": {
                "풍상측 벽면": 0.7,
                "풍하측 벽면": -0.5,
                "지붕부": -0.7,
            },
        },
    }

    # 예비설계용 내압계수 후보
    # 흡상하중이 불리해지는 경우를 자동으로 선택하도록 후보값으로 둠
    internal_cp_candidates = {
        "일반 밀폐형": [-0.2, 0.2],
        "부분개방형": [-0.5, 0.5],
        "개방형": [0.0],
    }

    zone_coeffs = external_cp_table[house_type][wind_direction]
    cpi_list = internal_cp_candidates[opening_type]

    # 지붕부 중 가장 불리한 외압계수 우선 선택
    roof_coeffs = {
        zone: cp
        for zone, cp in zone_coeffs.items()
        if "지붕" in zone
    }

    if roof_coeffs:
        governing_zone = min(roof_coeffs, key=roof_coeffs.get)
        Cpe = roof_coeffs[governing_zone]
    else:
        governing_zone = min(zone_coeffs, key=zone_coeffs.get)
        Cpe = zone_coeffs[governing_zone]

    # Cpe - Cpi의 절댓값이 가장 큰 내압계수 자동 선택
    governing_Cpi = cpi_list[0]
    governing_net_cp = Cpe - governing_Cpi

    for Cpi in cpi_list:
        net_cp = Cpe - Cpi
        if abs(net_cp) > abs(governing_net_cp):
            governing_Cpi = Cpi
            governing_net_cp = net_cp

    state["external_cp"] = Cpe
    state["internal_cp"] = governing_Cpi
    state["net_cp"] = governing_net_cp

    state["coeff_result"] = {
        "온실 형식": house_type,
        "풍향 조건": wind_direction,
        "개방 조건": opening_type,
        "대표 검토 구간": governing_zone,
        "자동 선정 외압계수 Cpe": Cpe,
        "자동 선정 내압계수 Cpi": governing_Cpi,
        "순압계수 Cpe-Cpi": round(governing_net_cp, 3),
        "구간별 외압계수": zone_coeffs,
        "내압계수 후보": cpi_list,
        "선정 방식": "대표 지붕부에서 |Cpe-Cpi|가 가장 큰 조합을 자동 선정",
        "주의": "현재 계수표는 예비설계용입니다. 최종 적용 시 구조설계 기준표 값으로 교체해야 합니다.",
    }

    return state
# =========================================================
# 5. 하중 산정 Agent
# =========================================================
def load_agent(state: DesignState):
    V = state["basic_wind_speed"]
    rho = 1.225

    Cpe = state["external_cp"]
    Cpi = state["internal_cp"]
    net_cp = state["net_cp"]

    spacing = state["frame_spacing"]

    # 속도압 q = 1/2 rho V^2
    q = 0.5 * rho * V ** 2

    # 풍압 [Pa = N/m²]
    wind_pressure = q * net_cp

    # 서까래 1개당 풍하중 선하중 [N/m]
    wind_line_load = wind_pressure * spacing

    # 적설하중
    ground_snow_load = state["ground_snow_load"]

    # 예비 지붕형상계수
    snow_shape_factor = 0.8

    roof_snow_load = ground_snow_load * snow_shape_factor

    # 적설 선하중 [kN/m]
    snow_line_load = roof_snow_load * spacing

    state["load_result"] = {
        "기본풍속 V [m/s]": V,
        "공기밀도 ρ [kg/m³]": rho,
        "속도압 q [Pa]": round(q, 3),
        "자동 선정 외압계수 Cpe": Cpe,
        "자동 선정 내압계수 Cpi": Cpi,
        "순압계수 Cpe-Cpi": round(net_cp, 3),
        "풍압 p [Pa]": round(wind_pressure, 3),
        "풍하중 선하중 [N/m]": round(wind_line_load, 3),
        "풍하중 선하중 [kN/m]": round(wind_line_load / 1000, 6),
        "지상적설하중 [kN/m²]": ground_snow_load,
        "지붕형상계수": snow_shape_factor,
        "지붕적설하중 [kN/m²]": round(roof_snow_load, 3),
        "적설 선하중 [kN/m]": round(snow_line_load, 3),
    }

    return state


# =========================================================
# 6. 구조해석 Agent - 현재는 예비 버전
# =========================================================
def analysis_agent(state: DesignState):
    load = state["load_result"]
    width = state["width"]

    # 매우 단순한 예비 계산용 값
    # 실제 구조해석은 추후 MIDAS, OpenSees, PyNite 등과 연계 가능
    wind_w = abs(load["풍하중 선하중 [kN/m]"])
    snow_w = abs(load["적설 선하중 [kN/m]"])

    total_w = wind_w + snow_w

    # 단순보 예비 최대모멘트 wL²/8 형태의 개념값
    estimated_moment = total_w * width ** 2 / 8

    # 임시 처짐 지표
    estimated_deflection_index = total_w * width ** 4 / 1000

    state["analysis_result"] = {
        "해석 방식": "예비 단순 계산",
        "총 선하중 [kN/m]": round(total_w, 4),
        "예비 최대모멘트 [kN·m]": round(estimated_moment, 4),
        "예비 처짐 지표": round(estimated_deflection_index, 4),
        "비고": "현재는 개념 검토용 결과이며, 실제 구조해석 모듈은 추후 연계 필요",
    }

    return state


# =========================================================
# 7. 구조설계/안정성 검토 Agent - 현재는 예비 버전
# =========================================================
def safety_check_agent(state: DesignState):
    analysis = state["analysis_result"]

    moment = analysis["예비 최대모멘트 [kN·m]"]

    # 임시 기준값
    allowable_moment = 3.0

    utilization = moment / allowable_moment

    if utilization <= 1.0:
        status = "OK"
        comment = "예비 기준상 안정한 것으로 판단됩니다."
    else:
        status = "NG"
        comment = "예비 기준상 부재 증대 또는 간격 조정이 필요합니다."

    state["safety_result"] = {
        "검토 항목": "예비 휨 안정성 검토",
        "예비 최대모멘트 [kN·m]": round(moment, 4),
        "가정 허용모멘트 [kN·m]": allowable_moment,
        "활용률": round(utilization, 3),
        "판정": status,
        "검토 의견": comment,
        "주의": "본 결과는 예비 검토용이며, 최종 구조설계에는 기준식 및 상세 구조해석이 필요합니다.",
    }

    state["summary_text"] = (
        f"{state['region']} 지역의 {state['crop']} 재배용 {state['house_type']}에 대해 "
        f"예비설계, 도면 시각화, 하중 산정, 예비 구조해석 및 안정성 검토를 수행했습니다. "
        f"현재 예비 안정성 판정은 {status}입니다."
    )

    return state


# =========================================================
# 8. LangGraph Workflow 구성
# =========================================================
def build_graph():
    graph = StateGraph(DesignState)

    graph.add_node("preliminary_design_agent", preliminary_design_agent)
    graph.add_node("drawing_agent", drawing_agent)
    graph.add_node("coefficient_agent", coefficient_agent)
    graph.add_node("load_agent", load_agent)
    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("safety_check_agent", safety_check_agent)

    graph.set_entry_point("preliminary_design_agent")

    graph.add_edge("preliminary_design_agent", "drawing_agent")
    graph.add_edge("drawing_agent", "coefficient_agent")
    graph.add_edge("coefficient_agent", "load_agent")
    graph.add_edge("load_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "safety_check_agent")
    graph.add_edge("safety_check_agent", END)

    return graph.compile()


# =========================================================
# 9. Streamlit 화면 구성
# =========================================================
st.title("비닐하우스 구조설계 다중에이전트 시스템")

st.caption(
    "예비설계 → 설계도면 시각화 → 하중 산정 → 구조해석 → 구조설계/안정성 검토 흐름으로 구성된 웹 기반 구조설계 지원 시스템"
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "① 예비설계",
    "② 설계도면",
    "③ 하중",
    "④ 구조해석",
    "⑤ 구조설계"
])


# =========================================================
# 10. 예비설계 탭
# =========================================================
with tab1:
    st.subheader("① 예비설계 입력")

    col1, col2, col3 = st.columns(3)

    with col1:
        region = st.selectbox(
            "지역",
            ["대구", "경북", "강원", "전남", "경기", "충남", "기타"]
        )

        crop = st.selectbox(
            "작물",
            ["딸기", "토마토", "파프리카", "상추", "오이", "기타"]
        )

        house_type = st.selectbox(
            "온실 형식",
            ["10-단동-1형", "아치형 단동", "연동형", "기타"]
        )

    with col2:
        width = st.number_input("폭 B [m]", min_value=1.0, value=8.0, step=0.1)
        length = st.number_input("길이 L [m]", min_value=1.0, value=30.0, step=0.5)
        frame_spacing = st.number_input("프레임 간격 [m]", min_value=0.1, value=0.6, step=0.1)

    with col3:
        eave_height = st.number_input("처마높이 [m]", min_value=1.0, value=3.0, step=0.1)
        ridge_height = st.number_input("동고 [m]", min_value=1.0, value=4.5, step=0.1)

        if ridge_height <= eave_height:
            st.warning("동고는 처마높이보다 크게 입력하는 것이 일반적입니다.")

    st.divider()

    st.subheader("하중 조건 입력")

    col4, col5, col6, col7 = st.columns(4)

    with col4:
        basic_wind_speed = st.number_input(
            "기본풍속 V [m/s]",
            min_value=1.0,
            value=30.0,
            step=1.0
        )

    with col5:
        wind_direction = st.selectbox(
    "풍향 조건",
    ["정면 풍향", "측면 풍향"]
)

    with col6:
        opening_type = st.selectbox(
    "개방 조건",
    ["일반 밀폐형", "부분개방형", "개방형"]
)

     with col7:
        ground_snow_load = st.number_input(
            "지상적설하중 [kN/m²]",
            min_value=0.0,
            value=0.5,
            step=0.1
        )

    st.info(
        "현재 버전은 예비설계용입니다. 외압계수, 내압계수, 적설하중은 사용자가 직접 입력하는 방식으로 구성했습니다."
    )

    if st.button("다중에이전트 설계 실행", type="primary"):
        app = build_graph()

        input_state = {
            "region": region,
            "crop": crop,
            "house_type": house_type,

            "width": width,
            "length": length,
            "eave_height": eave_height,
            "ridge_height": ridge_height,
            "frame_spacing": frame_spacing,

            "basic_wind_speed": basic_wind_speed,
            "wind_direction": wind_direction,
"opening_type": opening_type,

"external_cp": 0.0,
"internal_cp": 0.0,
"net_cp": 0.0,
"coeff_result": {},
            "ground_snow_load": ground_snow_load,

            "preliminary_result": {},
            "drawing_svg": "",
            "load_result": {},
            "analysis_result": {},
            "safety_result": {},
            "summary_text": "",
        }

        result = app.invoke(input_state)
        st.session_state["design_result"] = result

        st.success("다중에이전트 설계 실행 완료")

    if "design_result" in st.session_state:
        st.subheader("예비설계 결과")
        st.table([st.session_state["design_result"]["preliminary_result"]])

        st.subheader("최종 요약")
        st.write(st.session_state["design_result"]["summary_text"])


# =========================================================
# 11. 설계도면 탭
# =========================================================
with tab2:
    st.subheader("② 설계도면 시각화")

    if "design_result" in st.session_state:
        st.write("입력된 형상 조건을 바탕으로 정면도, 측면도, 평면도 개념도를 생성합니다.")

        components.html(
            st.session_state["design_result"]["drawing_svg"],
            height=700,
            scrolling=True
        )
    else:
        st.info("먼저 ① 예비설계 탭에서 다중에이전트 설계를 실행하세요.")


# =========================================================
# 12. 하중 탭
# =========================================================
with tab3:
    st.subheader("풍압계수 자동 선정 결과")
    st.write(st.session_state["design_result"]["coeff_result"])
    st.subheader("③ 하중 산정 결과")

    if "design_result" in st.session_state:
        load_result = st.session_state["design_result"]["load_result"]

        st.table([load_result])

        st.markdown(
            """
            **현재 적용된 하중 산정 개념**

            - 속도압: `q = 1/2 × ρ × V²`
            - 순압계수: `Cpe - Cpi`
            - 풍압: `p = q × (Cpe - Cpi)`
            - 풍하중 선하중: `p × 프레임 간격`
            - 지붕적설하중: `지상적설하중 × 지붕형상계수`
            """
        )
    else:
        st.info("먼저 ① 예비설계 탭에서 다중에이전트 설계를 실행하세요.")


# =========================================================
# 13. 구조해석 탭
# =========================================================
with tab4:
    st.subheader("④ 구조해석 결과")

    if "design_result" in st.session_state:
        analysis_result = st.session_state["design_result"]["analysis_result"]

        st.table([analysis_result])

        st.warning(
            "현재 구조해석 Agent는 예비 단순 계산 버전입니다. "
            "추후 MIDAS Gen, OpenSees, PyNite 등의 구조해석 모듈과 연계하여 확장할 수 있습니다."
        )
    else:
        st.info("먼저 ① 예비설계 탭에서 다중에이전트 설계를 실행하세요.")


# =========================================================
# 14. 구조설계 탭
# =========================================================
with tab5:
    st.subheader("⑤ 구조설계 및 안정성 검토")

    if "design_result" in st.session_state:
        safety_result = st.session_state["design_result"]["safety_result"]

        st.table([safety_result])

        판정 = safety_result["판정"]

        if 판정 == "OK":
            st.success("예비 검토 결과: OK")
        else:
            st.error("예비 검토 결과: NG")

        st.subheader("시스템 설명")
        st.write(
            "본 시스템은 Streamlit 기반 사용자 인터페이스와 LangGraph 기반 다중에이전트 workflow를 결합하여, "
            "예비설계, 설계도면 시각화, 하중 산정, 구조해석, 안정성 검토 과정을 순차적으로 수행하는 "
            "비닐하우스 구조설계 지원 시스템입니다."
        )
    else:
        st.info("먼저 ① 예비설계 탭에서 다중에이전트 설계를 실행하세요.")
