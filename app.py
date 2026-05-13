import streamlit as st
import pandas as pd
import math

# =====================================================
# 페이지 설정
# =====================================================
st.set_page_config(
    page_title="비닐하우스 하중계산 및 예비설계",
    layout="wide"
)

st.title("비닐하우스 하중계산 및 예비설계 Agent")
st.write("하중계산과 GHModeler형 워크시트 예비설계 기능을 수행하는 예시 프로그램입니다.")


# =====================================================
# 기본값 설정
# =====================================================
DEFAULTS = {
    # 하중계산 기본값
    "house_type": "10-단동-1형",
    "wind_speed": 30.0,
    "external_cp": -0.70,
    "internal_cp": -0.20,
    "rafter_spacing": 0.60,

    # 예비설계 기본값
    "crop": "딸기",
    "area_m2": 1000.0,
    "house_width": 8.0,
    "house_length": 125.0,
    "house_height": 4.0,
    "bed_count": 6,
    "bed_width": 1.2,
    "side_purlin_count": 3,
    "roof_purlin_count": 4,
    "rafter_diameter": 31.8,
    "rafter_thickness": 1.5,
    "purlin_diameter": 25.4,
    "purlin_thickness": 1.5,
    "pipe_unit_price": 1800.0,
    "vinyl_unit_price": 2500.0,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =====================================================
# 함수 1. 풍하중 계산
# =====================================================
def calculate_wind_load(wind_speed, external_cp, internal_cp, rafter_spacing):
    """
    풍하중 계산
    q = 1/2 * rho * V^2
    p = q * (Cpe - Cpi)
    w = p * 서까래 간격
    """
    rho = 1.225  # kg/m3, 공기밀도

    q = 0.5 * rho * wind_speed ** 2
    net_cp = external_cp - internal_cp
    wind_pressure = q * net_cp
    line_load = wind_pressure * rafter_spacing

    return {
        "속도압 q [Pa]": q,
        "외압계수 Cpe": external_cp,
        "내압계수 Cpi": internal_cp,
        "순압계수 Cpe-Cpi": net_cp,
        "풍압 p [Pa]": wind_pressure,
        "서까래 간격 [m]": rafter_spacing,
        "선하중 w [N/m]": line_load,
        "선하중 w [kN/m]": line_load / 1000,
    }


# =====================================================
# 함수 2. 파이프 단면적 계산
# =====================================================
def pipe_area_m2(diameter_mm, thickness_mm):
    """
    원형 강관 단면적 계산
    diameter_mm: 외경(mm)
    thickness_mm: 두께(mm)
    """
    D = diameter_mm / 1000
    t = thickness_mm / 1000
    d = D - 2 * t

    if d <= 0:
        return 0

    area = math.pi / 4 * (D**2 - d**2)
    return area


# =====================================================
# 함수 3. GHModeler형 워크시트 예비설계 계산
# =====================================================
def calculate_preliminary_design(
    house_width,
    house_length,
    house_height,
    bed_count,
    bed_width,
    rafter_spacing,
    side_purlin_count,
    roof_purlin_count,
    rafter_diameter,
    rafter_thickness,
    purlin_diameter,
    purlin_thickness,
    pipe_unit_price,
    vinyl_unit_price,
):
    # 1) 온실 크기
    floor_area = house_width * house_length
    volume = floor_area * house_height

    # 2) 재배 면적
    cultivation_width = bed_width * max(bed_count - 1, 0)
    cultivation_area = cultivation_width * house_length
    land_use_ratio = cultivation_area / floor_area * 100 if floor_area > 0 else 0

    # 3) 시설 구조
    rafter_count = int(round(house_length / rafter_spacing)) + 1
    model_length = (rafter_count - 1) * rafter_spacing
    length_error = model_length - house_length

    total_purlin_count = 2 * (side_purlin_count + roof_purlin_count + 1) + 1

    # 4) 파이프 길이 개략 계산
    # 단순 아치형 가정: 서까래 1개 길이 = 폭 × π / 2
    rafter_one_length = house_width * math.pi / 2
    total_rafter_length = rafter_one_length * rafter_count
    total_purlin_length = total_purlin_count * model_length

    # 5) 파이프 중량 계산
    steel_density = 7850  # kg/m3

    rafter_area = pipe_area_m2(rafter_diameter, rafter_thickness)
    purlin_area = pipe_area_m2(purlin_diameter, purlin_thickness)

    rafter_weight = rafter_area * total_rafter_length * steel_density
    purlin_weight = purlin_area * total_purlin_length * steel_density
    total_pipe_weight = rafter_weight + purlin_weight

    # 6) 비닐 면적 개략 계산
    roof_side_vinyl_area = rafter_one_length * model_length
    front_back_vinyl_area = house_width * house_height * 0.8 * 2
    total_vinyl_area = roof_side_vinyl_area + front_back_vinyl_area

    # 7) 비용 계산
    pipe_cost = total_pipe_weight * pipe_unit_price
    vinyl_cost = total_vinyl_area * vinyl_unit_price
    total_cost = pipe_cost + vinyl_cost

    return {
        "floor_area": floor_area,
        "volume": volume,
        "cultivation_area": cultivation_area,
        "land_use_ratio": land_use_ratio,
        "rafter_count": rafter_count,
        "model_length": model_length,
        "length_error": length_error,
        "total_purlin_count": total_purlin_count,
        "rafter_one_length": rafter_one_length,
        "total_rafter_length": total_rafter_length,
        "total_purlin_length": total_purlin_length,
        "rafter_weight": rafter_weight,
        "purlin_weight": purlin_weight,
        "total_pipe_weight": total_pipe_weight,
        "roof_side_vinyl_area": roof_side_vinyl_area,
        "front_back_vinyl_area": front_back_vinyl_area,
        "total_vinyl_area": total_vinyl_area,
        "pipe_cost": pipe_cost,
        "vinyl_cost": vinyl_cost,
        "total_cost": total_cost,
    }


# =====================================================
# 탭 구성
# =====================================================
tab_load, tab_worksheet = st.tabs([
    "1. 하중계산",
    "2. 예비설계 워크시트"
])


# =====================================================
# 탭 1. 하중계산
# =====================================================
with tab_load:
    st.header("하중계산")
    st.write("기본풍속, 외압계수, 내압계수, 서까래 간격을 이용하여 풍압과 서까래 선하중을 계산합니다.")

    col1, col2 = st.columns(2)

    with col1:
        house_type = st.selectbox(
            "온실 형식",
            ["10-단동-1형", "보강아치형", "연동형", "기타"],
            key="house_type"
        )

        wind_speed = st.number_input(
            "기본풍속 V (m/s)",
            min_value=0.0,
            step=1.0,
            key="wind_speed"
        )

        rafter_spacing = st.number_input(
            "서까래 간격 (m)",
            min_value=0.1,
            step=0.05,
            key="rafter_spacing"
        )

    with col2:
        external_cp = st.number_input(
            "외압계수 Cpe",
            step=0.05,
            key="external_cp"
        )

        internal_cp = st.number_input(
            "내압계수 Cpi",
            step=0.05,
            key="internal_cp"
        )

    if st.button("풍하중 계산 실행"):
        if wind_speed <= 0:
            st.error("기본풍속은 0보다 커야 합니다.")
        elif rafter_spacing <= 0:
            st.error("서까래 간격은 0보다 커야 합니다.")
        else:
            wind_result = calculate_wind_load(
                wind_speed=wind_speed,
                external_cp=external_cp,
                internal_cp=internal_cp,
                rafter_spacing=rafter_spacing
            )

            st.session_state["wind_result"] = wind_result

    if "wind_result" in st.session_state:
        wind_result = st.session_state["wind_result"]

        st.subheader("풍하중 계산 결과")

        wind_df = pd.DataFrame({
            "항목": list(wind_result.keys()),
            "값": [
                f"{v:.3f}" if isinstance(v, float) else v
                for v in wind_result.values()
            ]
        })

        st.table(wind_df)

        st.subheader("결과 요약")
        st.write(
            f"{house_type}에 대해 기본풍속 {wind_speed:.1f} m/s, "
            f"외압계수 {external_cp:.2f}, 내압계수 {internal_cp:.2f}를 적용하면 "
            f"순압계수는 {wind_result['순압계수 Cpe-Cpi']:.2f}, "
            f"풍압은 {wind_result['풍압 p [Pa]']:.2f} Pa, "
            f"서까래 1개당 선하중은 {wind_result['선하중 w [kN/m]']:.4f} kN/m입니다."
        )


# =====================================================
# 탭 2. 예비설계 워크시트
# =====================================================
with tab_worksheet:
    st.header("예비설계 워크시트")
    st.write("온실 규모, 재배면적, 서까래/도리 개수, 파이프 및 비닐 물량, 개략 비용을 산정합니다.")

    st.subheader("1. 비닐온실 크기")

    col1, col2, col3 = st.columns(3)

    with col1:
        house_width = st.number_input(
            "온실 폭 (m)",
            min_value=1.0,
            step=0.5,
            key="house_width"
        )

    with col2:
        house_length = st.number_input(
            "온실 길이 (m)",
            min_value=1.0,
            step=1.0,
            key="house_length"
        )

    with col3:
        house_height = st.number_input(
            "온실 높이 (m)",
            min_value=1.0,
            step=0.1,
            key="house_height"
        )

    st.subheader("2. 재배 면적")

    col1, col2, col3 = st.columns(3)

    with col1:
        crop = st.text_input(
            "작물",
            key="crop"
        )

    with col2:
        bed_count = st.number_input(
            "이랑 개수",
            min_value=1,
            step=1,
            key="bed_count"
        )

    with col3:
        bed_width = st.number_input(
            "이랑 폭 (m)",
            min_value=0.1,
            step=0.1,
            key="bed_width"
        )

    st.subheader("3. 시설 구조")

    col1, col2, col3 = st.columns(3)

    with col1:
        ws_rafter_spacing = st.number_input(
            "워크시트용 서까래 간격 (m)",
            min_value=0.1,
            step=0.05,
            value=st.session_state["rafter_spacing"],
            key="ws_rafter_spacing"
        )

    with col2:
        side_purlin_count = st.number_input(
            "측면 도리 개수",
            min_value=0,
            step=1,
            key="side_purlin_count"
        )

    with col3:
        roof_purlin_count = st.number_input(
            "지붕 도리 개수",
            min_value=0,
            step=1,
            key="roof_purlin_count"
        )

    st.subheader("4. 부재 규격")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rafter_diameter = st.number_input(
            "서까래 외경 (mm)",
            min_value=1.0,
            step=0.1,
            key="rafter_diameter"
        )

    with col2:
        rafter_thickness = st.number_input(
            "서까래 두께 (mm)",
            min_value=0.1,
            step=0.1,
            key="rafter_thickness"
        )

    with col3:
        purlin_diameter = st.number_input(
            "도리 외경 (mm)",
            min_value=1.0,
            step=0.1,
            key="purlin_diameter"
        )

    with col4:
        purlin_thickness = st.number_input(
            "도리 두께 (mm)",
            min_value=0.1,
            step=0.1,
            key="purlin_thickness"
        )

    st.subheader("5. 단가 입력")

    col1, col2 = st.columns(2)

    with col1:
        pipe_unit_price = st.number_input(
            "파이프 단가 (원/kg)",
            min_value=0.0,
            step=100.0,
            key="pipe_unit_price"
        )

    with col2:
        vinyl_unit_price = st.number_input(
            "비닐 단가 (원/m²)",
            min_value=0.0,
            step=100.0,
            key="vinyl_unit_price"
        )

    if st.button("예비설계 계산 실행"):
        worksheet_result = calculate_preliminary_design(
            house_width=house_width,
            house_length=house_length,
            house_height=house_height,
            bed_count=bed_count,
            bed_width=bed_width,
            rafter_spacing=ws_rafter_spacing,
            side_purlin_count=side_purlin_count,
            roof_purlin_count=roof_purlin_count,
            rafter_diameter=rafter_diameter,
            rafter_thickness=rafter_thickness,
            purlin_diameter=purlin_diameter,
            purlin_thickness=purlin_thickness,
            pipe_unit_price=pipe_unit_price,
            vinyl_unit_price=vinyl_unit_price,
        )

        st.session_state["worksheet_result"] = worksheet_result

    if "worksheet_result" in st.session_state:
        result = st.session_state["worksheet_result"]

        st.success("예비설계 계산이 완료되었습니다.")

        st.subheader("계산 결과 요약")

        summary_df = pd.DataFrame({
            "항목": [
                "작물",
                "온실 바닥면적",
                "온실 체적",
                "재배면적",
                "토지이용률",
                "서까래 개수",
                "계산상 온실 길이",
                "입력 길이와 차이",
                "전체 도리 개수",
                "서까래 1개 길이",
                "서까래 총길이",
                "도리 총길이",
                "총 파이프 중량",
                "총 비닐 면적",
                "파이프 비용",
                "비닐 비용",
                "개략 총비용",
            ],
            "값": [
                crop,
                f'{result["floor_area"]:.1f} m²',
                f'{result["volume"]:.1f} m³',
                f'{result["cultivation_area"]:.1f} m²',
                f'{result["land_use_ratio"]:.1f} %',
                f'{result["rafter_count"]} 개',
                f'{result["model_length"]:.2f} m',
                f'{result["length_error"]:.2f} m',
                f'{result["total_purlin_count"]} 개',
                f'{result["rafter_one_length"]:.2f} m',
                f'{result["total_rafter_length"]:.1f} m',
                f'{result["total_purlin_length"]:.1f} m',
                f'{result["total_pipe_weight"]:.1f} kg',
                f'{result["total_vinyl_area"]:.1f} m²',
                f'{result["pipe_cost"]:,.0f} 원',
                f'{result["vinyl_cost"]:,.0f} 원',
                f'{result["total_cost"]:,.0f} 원',
            ]
        })

        st.table(summary_df)

        if result["land_use_ratio"] > 100:
            st.error("재배면적이 온실 전체면적을 초과합니다. 이랑 개수 또는 이랑 폭을 줄여야 합니다.")

        if abs(result["length_error"]) > 0.05:
            st.warning("서까래 간격으로 계산된 온실 길이가 입력한 온실 길이와 다릅니다.")

        st.subheader("자재별 상세 결과")

        material_df = pd.DataFrame({
            "구분": ["서까래 파이프", "도리 파이프", "비닐"],
            "수량/면적": [
                f'{result["total_rafter_length"]:.1f} m',
                f'{result["total_purlin_length"]:.1f} m',
                f'{result["total_vinyl_area"]:.1f} m²',
            ],
            "중량": [
                f'{result["rafter_weight"]:.1f} kg',
                f'{result["purlin_weight"]:.1f} kg',
                "-",
            ],
            "개략 비용": [
                f'{result["rafter_weight"] * pipe_unit_price:,.0f} 원',
                f'{result["purlin_weight"] * pipe_unit_price:,.0f} 원',
                f'{result["vinyl_cost"]:,.0f} 원',
            ]
        })

        st.table(material_df)

        if st.button("예비설계 서까래 간격을 하중계산에 적용"):
            st.session_state["rafter_spacing"] = ws_rafter_spacing
            st.success("서까래 간격이 하중계산 탭에 적용되었습니다.")
            st.rerun()
