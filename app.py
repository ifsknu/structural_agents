import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END

class DesignState(TypedDict):
    house_type: str
    wind_speed: float
    external_cp: float
    internal_cp: float
    rafter_spacing: float

    input_check_result: str
    wind_result: dict
    summary_text: str


def input_check_agent(state: DesignState):
    errors = []

    if state["wind_speed"] <= 0:
        errors.append("기본풍속은 0보다 커야 합니다.")

    if state["rafter_spacing"] <= 0:
        errors.append("서까래 간격은 0보다 커야 합니다.")

    if state["external_cp"] == 0:
        errors.append("외압계수가 0입니다. 외압계수를 다시 확인하세요.")

    if errors:
        state["input_check_result"] = "\n".join(errors)
    else:
        state["input_check_result"] = "입력값 검토 완료"

    return state


def wind_load_agent(state: DesignState):
    V = state["wind_speed"]
    Cpe = state["external_cp"]
    Cpi = state["internal_cp"]
    spacing = state["rafter_spacing"]

    rho = 1.225

    # 속도압 q = 1/2 * rho * V^2
    q = 0.5 * rho * V ** 2

    # 순압계수
    net_cp = Cpe - Cpi

    # 풍압, 단위: N/m2 = Pa
    wind_pressure = q * net_cp

    # 서까래 간격을 고려한 선하중, 단위: N/m
    line_load = wind_pressure * spacing

    state["wind_result"] = {
        "속도압 q [Pa]": round(q, 3),
        "외압계수 Cpe": Cpe,
        "내압계수 Cpi": Cpi,
        "순압계수 Cpe-Cpi": round(net_cp, 3),
        "풍압 p [Pa]": round(wind_pressure, 3),
        "서까래 간격 [m]": spacing,
        "선하중 w [N/m]": round(line_load, 3),
        "선하중 w [kN/m]": round(line_load / 1000, 6),
    }

    return state


def summary_agent(state: DesignState):
    result = state["wind_result"]

    state["summary_text"] = (
        f"{state['house_type']}에 대해 입력된 기본풍속 {state['wind_speed']} m/s, "
        f"외압계수 {state['external_cp']}, 내압계수 {state['internal_cp']}를 적용하여 "
        f"풍압은 {result['풍압 p [Pa]']} Pa, "
        f"서까래 1개당 선하중은 {result['선하중 w [kN/m]']} kN/m로 산정되었습니다."
    )

    return state


def build_graph():
    graph = StateGraph(DesignState)

    graph.add_node("input_check_agent", input_check_agent)
    graph.add_node("wind_load_agent", wind_load_agent)
    graph.add_node("summary_agent", summary_agent)

    graph.set_entry_point("input_check_agent")
    graph.add_edge("input_check_agent", "wind_load_agent")
    graph.add_edge("wind_load_agent", "summary_agent")
    graph.add_edge("summary_agent", END)

    return graph.compile()

st.subheader("비닐하우스 풍하중 계산 Agent")

house_type = st.selectbox(
    "온실 형식",
    ["10-단동-1형", "기타"]
)

wind_speed = st.number_input(
    "기본풍속 V (m/s)",
    value=30.0
)

external_cp = st.number_input(
    "외압계수 Cpe",
    value=-0.7
)

internal_cp = st.number_input(
    "내압계수 Cpi",
    value=-0.2
)

rafter_spacing = st.number_input(
    "서까래 간격 (m)",
    value=0.6
)

if st.button("풍하중 Agent 실행"):
    app = build_graph()

    input_state = {
        "house_type": house_type,
        "wind_speed": wind_speed,
        "external_cp": external_cp,
        "internal_cp": internal_cp,
        "rafter_spacing": rafter_spacing,
        "input_check_result": "",
        "wind_result": {},
        "summary_text": ""
    }

    result = app.invoke(input_state)

    st.success(result["input_check_result"])

    st.subheader("풍하중 계산 결과")
    st.write(result["wind_result"])

    st.subheader("결과 요약")
    st.write(result["summary_text"])

st.set_page_config(page_title="구조설계 도우미", layout="wide")

st.title("구조설계 다중 에이전트 예시")
st.write("버튼과 입력값으로 간단한 구조설계 흐름을 시험하는 웹 예시입니다.")

st.sidebar.header("설계 조건 입력")

structure_type = st.sidebar.selectbox(
    "구조 형식 선택",
    ["철골보", "철근콘크리트보", "기둥"]
)

span = st.sidebar.number_input("경간 L (m)", min_value=1.0, value=8.0, step=0.5)
dead_load = st.sidebar.number_input("고정하중 DL (kN/m)", min_value=0.0, value=5.0, step=0.5)
live_load = st.sidebar.number_input("활하중 LL (kN/m)", min_value=0.0, value=3.0, step=0.5)
fy = st.sidebar.number_input("재료 강도 fy (MPa)", min_value=100, value=275, step=5)

def organize_conditions(structure_type, span, dead_load, live_load, fy):
    return {
        "구조형식": structure_type,
        "경간(m)": span,
        "고정하중(kN/m)": dead_load,
        "활하중(kN/m)": live_load,
        "재료강도(MPa)": fy,
    }

def simple_calculation(span, dead_load, live_load):
    w = dead_load + live_load
    moment = w * (span ** 2) / 8
    shear = w * span / 2
    return w, moment, shear

def simple_check(moment, fy):
    if moment < fy:
        return "예시 판정: 안전 측으로 보임"
    else:
        return "예시 판정: 추가 검토 필요"

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("1. 조건 정리"):
        conditions = organize_conditions(structure_type, span, dead_load, live_load, fy)
        st.subheader("정리된 조건")
        st.json(conditions)

with col2:
    if st.button("2. 구조 계산"):
        w, moment, shear = simple_calculation(span, dead_load, live_load)
        st.subheader("계산 결과")
        st.write(f"총 등분포하중 w = {w:.2f} kN/m")
        st.write(f"최대 휨모멘트 M = {moment:.2f} kN·m")
        st.write(f"최대 전단력 V = {shear:.2f} kN")

with col3:
    if st.button("3. 기준 검토"):
        w, moment, shear = simple_calculation(span, dead_load, live_load)
        result = simple_check(moment, fy)
        st.subheader("검토 결과")
        st.write(result)

st.markdown("---")

if st.button("전체 실행"):
    conditions = organize_conditions(structure_type, span, dead_load, live_load, fy)
    w, moment, shear = simple_calculation(span, dead_load, live_load)
    result = simple_check(moment, fy)

    st.subheader("최종 요약")
    st.write("### 1) 입력 조건")
    st.json(conditions)

    st.write("### 2) 계산 결과")
    st.write(f"- 총 하중: {w:.2f} kN/m")
    st.write(f"- 최대 휨모멘트: {moment:.2f} kN·m")
    st.write(f"- 최대 전단력: {shear:.2f} kN")

    st.write("### 3) 검토 결과")
    st.write(result)
