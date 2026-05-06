import streamlit as st
from typing import TypedDict
from langgraph.graph import StateGraph, END

class DesignState(TypedDict):
    house_type: str
    wind_speed: float
    internal_cp: float
    result_text: str


def input_check_agent(state: DesignState):
    house_type = state["house_type"]
    wind_speed = state["wind_speed"]

    if wind_speed <= 0:
        state["result_text"] = "입력 오류: 풍속은 0보다 커야 합니다."
    else:
        state["result_text"] = f"{house_type} 입력값 검토 완료"

    return state


def wind_load_agent(state: DesignState):
    wind_speed = state["wind_speed"]
    internal_cp = state["internal_cp"]

    rho = 1.225
    q = 0.5 * rho * wind_speed ** 2

    state["result_text"] += f"\n속도압 q = {q:.2f} Pa"
    state["result_text"] += f"\n내압계수 Cpi = {internal_cp}"

    return state


def build_graph():
    graph = StateGraph(DesignState)

    graph.add_node("input_check_agent", input_check_agent)
    graph.add_node("wind_load_agent", wind_load_agent)

    graph.set_entry_point("input_check_agent")
    graph.add_edge("input_check_agent", "wind_load_agent")
    graph.add_edge("wind_load_agent", END)

    return graph.compile()

st.subheader("LangGraph 다중에이전트 테스트")

house_type = st.selectbox(
    "온실 형식",
    ["10-단동-1형", "기타"]
)

wind_speed = st.number_input(
    "기본풍속 V (m/s)",
    value=30.0
)

internal_cp = st.number_input(
    "내압계수 Cpi",
    value=-0.2
)

if st.button("LangGraph 실행"):
    app = build_graph()

    input_state = {
        "house_type": house_type,
        "wind_speed": wind_speed,
        "internal_cp": internal_cp,
        "result_text": ""
    }

    result = app.invoke(input_state)

    st.success("LangGraph 실행 완료")
    st.text(result["result_text"])

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
