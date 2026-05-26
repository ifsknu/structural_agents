import re
import math
import streamlit as st
import streamlit.components.v1 as components
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
    drawing_svg: str
    response_text: str


# =========================================================
# 3. 자연어 조건해석 Agent
# =========================================================
def parse_request_agent(state: DesignState):
    text = state["user_prompt"]

    regions = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
        "포항", "경주", "김천", "안동", "구미", "영주", "영천", "상주", "문경", "경산",
        "평창", "대관령", "강릉", "원주", "춘천",
        "수원", "화성", "평택", "이천", "안성", "용인",
        "천안", "아산", "논산", "부여", "공주",
        "청주", "충주", "제천", "음성", "진천",
        "전주", "익산", "김제", "정읍", "남원",
        "나주", "순천", "여수", "담양", "해남", "무안",
        "창원", "진주", "밀양", "김해", "거창", "합천",
        "서귀포", "제주시"
    ]

    crop_alias = {
        "딸기": "딸기",
        "토마토": "토마토",
        "방울토마토": "토마토",
        "파프리카": "파프리카",
        "상추": "상추",
        "오이": "오이",
        "고추": "고추",
        "멜론": "멜론",
        "참외": "참외",
        "화훼": "화훼",
        "엽채류": "엽채류",
    }

    # 지역 추출
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

    # 작물 추출
    crop = ""
    for key, value in crop_alias.items():
        if key in text:
            crop = value
            break

    # 규모 추출
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
        state["drawing_svg"] = ""
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

    # 작물별 기본 추천 로직
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

    # 규모에 따른 연동 수 및 길이 산정
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

    # 길이 보정
    if design_length < 20:
        design_length = 20
        total_width = area_m2 / design_length
        span_count = max(1, round(total_width / width_per_span))
        total_width = span_count * width_per_span

    if design_length > 80:
        design_length = 60
        total_width = area_m2 / design_length
        span_count = max(1, math.ceil(total_width / width_per_span))
        total_width = span_count * width_per_span

    frame_count = int(design_length / frame_spacing) + 1
    estimated_area = total_width * design_length

    # 지역별 주의사항
    if region in ["포항", "부산", "울산", "제주", "서귀포", "제주시"]:
        region_note = "해안 또는 강풍 영향 가능성이 있어 풍하중 검토를 우선 고려하는 것이 좋습니다."
    elif region in ["강원", "평창", "대관령"]:
        region_note = "적설 영향이 큰 지역일 수 있으므로 적설하중 검토를 우선 고려하는 것이 좋습니다."
    elif region in ["대구", "경북", "영천", "경주", "구미", "안동"]:
        region_note = "내륙 지역 특성을 고려하여 풍하중과 적설하중을 함께 검토하는 것이 좋습니다."
    else:
        region_note = "지역별 기본풍속 및 적설하중 기준값을 확인하여 구조검토가 필요합니다."

    greenhouse_type = base_type if span_count == 1 else f"{span_count}연동 {base_type}"

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
# 5. 설계도면 시각화 Agent
# =========================================================
def drawing_agent(state: DesignState):
    if state["missing_fields"]:
        state["drawing_svg"] = ""
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

    # -------------------------------
    # 정면도 배율
    # -------------------------------
    front_x = 70
    front_y = 310
    front_max_w = 430
    front_max_h = 220
    front_scale = min(front_max_w / total_width, front_max_h / ridge_height)

    fw = total_width * front_scale
    feh = eave_height * front_scale
    frh = ridge_height * front_scale
    span_w = fw / span_count

    front_svg = ""
    for i in range(span_count):
        x0 = front_x + i * span_w
        x1 = x0 + span_w
        xm = (x0 + x1) / 2

        front_svg += f"""
        <line x1="{x0}" y1="{front_y}" x2="{x0}" y2="{front_y - feh}" class="main-line"/>
        <line x1="{x1}" y1="{front_y}" x2="{x1}" y2="{front_y - feh}" class="main-line"/>
        <path d="M {x0} {front_y - feh} Q {xm} {front_y - frh} {x1} {front_y - feh}" class="main-line"/>
        """

    front_svg += f"""
    <line x1="{front_x - 20}" y1="{front_y}" x2="{front_x + fw + 20}" y2="{front_y}" class="ground-line"/>
    <line x1="{front_x}" y1="{front_y + 28}" x2="{front_x + fw}" y2="{front_y + 28}" class="dim-line"/>
    <text x="{front_x + fw / 2 - 45}" y="{front_y + 50}" class="label">폭 {total_width:.2f} m</text>
    <text x="{front_x + fw + 15}" y="{front_y - feh / 2}" class="label">처마 {eave_height:.2f} m</text>
    <text x="{front_x + fw / 2 - 45}" y="{front_y - frh - 12}" class="label">동고 {ridge_height:.2f} m</text>
    """

    # -------------------------------
    # 측면도 배율
    # -------------------------------
    side_x = 600
    side_y = 310
    side_max_w = 390
    side_max_h = 220
    side_scale = min(side_max_w / design_length, side_max_h / ridge_height)

    sl = design_length * side_scale
    seh = eave_height * side_scale

    visible_side_frames = min(frame_count, 18)
    side_frame_svg = ""

    if visible_side_frames > 1:
        for i in range(visible_side_frames):
            x = side_x + sl * i / (visible_side_frames - 1)
            side_frame_svg += f"""
            <line x1="{x}" y1="{side_y}" x2="{x}" y2="{side_y - seh}" class="frame-line"/>
            """

    side_svg = f"""
    <line x1="{side_x - 20}" y1="{side_y}" x2="{side_x + sl + 20}" y2="{side_y}" class="ground-line"/>
    <rect x="{side_x}" y="{side_y - seh}" width="{sl}" height="{seh}" class="outline-rect"/>
    {side_frame_svg}
    <line x1="{side_x}" y1="{side_y + 28}" x2="{side_x + sl}" y2="{side_y + 28}" class="dim-line"/>
    <text x="{side_x + sl / 2 - 50}" y="{side_y + 50}" class="label">길이 {design_length:.2f} m</text>
    <text x="{side_x + 10}" y="{side_y - seh - 15}" class="label">프레임 간격 {frame_spacing:.2f} m</text>
    """

    # -------------------------------
    # 평면도 배율
    # -------------------------------
    plan_x = 70
    plan_y = 520
    plan_max_w = 900
    plan_max_h = 150
    plan_scale = min(plan_max_w / design_length, plan_max_h / total_width)

    pl = design_length * plan_scale
    pw = total_width * plan_scale

    plan_frame_svg = ""
    visible_plan_frames = min(frame_count, 26)

    if visible_plan_frames > 1:
        for i in range(visible_plan_frames):
            x = plan_x + pl * i / (visible_plan_frames - 1)
            plan_frame_svg += f"""
            <line x1="{x}" y1="{plan_y}" x2="{x}" y2="{plan_y + pw}" class="frame-line"/>
            """

    # 연동 구분선
    span_line_svg = ""
    if span_count > 1:
        for i in range(1, span_count):
            y = plan_y + pw * i / span_count
            span_line_svg += f"""
            <line x1="{plan_x}" y1="{y}" x2="{plan_x + pl}" y2="{y}" class="span-line"/>
            """

    plan_svg = f"""
    <rect x="{plan_x}" y="{plan_y}" width="{pl}" height="{pw}" class="outline-rect"/>
    {plan_frame_svg}
    {span_line_svg}
    <line x1="{plan_x}" y1="{plan_y + pw + 28}" x2="{plan_x + pl}" y2="{plan_y + pw + 28}" class="dim-line"/>
    <text x="{plan_x + pl / 2 - 50}" y="{plan_y + pw + 50}" class="label">길이 {design_length:.2f} m</text>
    <text x="{plan_x + pl + 18}" y="{plan_y + pw / 2}" class="label">폭 {total_width:.2f} m</text>
    """

    svg = f"""
    <svg width="1100" height="760" viewBox="0 0 1100 760" xmlns="http://www.w3.org/2000/svg">
        <style>
            .bg {{
                fill: #f9fafb;
                stroke: #d1d5db;
                stroke-width: 1.5;
            }}
            .panel {{
                fill: white;
                stroke: #e5e7eb;
                stroke-width: 1.3;
            }}
            .title {{
                font: bold 20px sans-serif;
                fill: #111827;
            }}
            .subtitle {{
                font: bold 15px sans-serif;
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
            .main-line {{
                stroke: #111827;
                stroke-width: 2.2;
                fill: none;
            }}
            .ground-line {{
                stroke: #4b5563;
                stroke-width: 2;
            }}
            .frame-line {{
                stroke: #9ca3af;
                stroke-width: 1;
                stroke-dasharray: 4 3;
            }}
            .span-line {{
                stroke: #2563eb;
                stroke-width: 1.4;
                stroke-dasharray: 6 4;
            }}
            .dim-line {{
                stroke: #6b7280;
                stroke-width: 1;
                stroke-dasharray: 4 3;
            }}
            .outline-rect {{
                stroke: #111827;
                stroke-width: 2;
                fill: none;
            }}
            .badge {{
                fill: #eff6ff;
                stroke: #bfdbfe;
                stroke-width: 1;
            }}
        </style>

        <rect x="20" y="20" width="1060" height="700" rx="18" class="bg"/>

        <text x="55" y="60" class="title">추천 온실 예비설계 도면</text>
        <text x="55" y="88" class="small">
            자연어 입력으로 생성된 추천안을 바탕으로 정면도, 측면도, 평면도를 자동 시각화한 개념도입니다.
        </text>

        <rect x="55" y="110" width="990" height="75" rx="12" class="panel"/>
        <text x="80" y="142" class="subtitle">{greenhouse_type}</text>
        <text x="80" y="168" class="label">지역: {region}  |  작물: {crop}  |  연동 수: {span_count}  |  프레임 수: {frame_count}</text>

        <text x="70" y="225" class="subtitle">정면도</text>
        {front_svg}

        <text x="600" y="225" class="subtitle">측면도</text>
        {side_svg}

        <text x="70" y="480" class="subtitle">평면도 / 프레임 배치도</text>
        {plan_svg}

        <rect x="70" y="690" width="950" height="35" rx="8" class="badge"/>
        <text x="90" y="713" class="small">
            ※ 본 도면은 예비설계 단계의 개념도입니다. 실제 구조설계 및 시공도면에는 기준하중, 부재검토, 접합부 검토가 추가로 필요합니다.
        </text>
    </svg>
    """

    state["drawing_svg"] = svg
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
    "사용자가 자연어로 지역, 작물, 규모를 입력하면 조건을 자동 추출하고, 온실 추천안과 예비 설계도면을 생성합니다."
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


# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None


# 기존 채팅 출력
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# 사용자 입력
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
        "drawing_svg": "",
        "response_text": "",
    }

    result = app.invoke(input_state)

    st.session_state["last_result"] = result
    st.session_state["messages"].append(
        {"role": "assistant", "content": result["response_text"]}
    )

    with st.chat_message("assistant"):
        st.write(result["response_text"])


# 상세 결과 출력
if st.session_state["last_result"] is not None:
    result = st.session_state["last_result"]

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "① 조건 추출 결과",
        "② 추천안",
        "③ 설계도면"
    ])

    with tab1:
        st.subheader("자연어 입력 조건 추출 결과")
        st.table([result["parsed_result"]])

    with tab2:
        st.subheader("온실 예비설계 추천안")

        if result["recommendation_result"]:
            st.table([result["recommendation_result"]])
        else:
            st.warning(result["response_text"])

    with tab3:
        st.subheader("예비 설계도면 시각화")

        if result["drawing_svg"]:
            components.html(
                result["drawing_svg"],
                height=780,
                scrolling=True
            )
        else:
            st.info("추천안이 생성되면 설계도면이 표시됩니다.")
