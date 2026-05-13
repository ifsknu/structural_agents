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
st.write("하중계산과 GHModeler형 예비설계 워크시트 기능을 수행하는 예시 프로그램입니다.")


# =====================================================
# 기본값 설정
# =====================================================
DEFAULTS = {
    "load_house_type": "10-단동-1형",
    "load_wind_speed": 30.0,
    "load_external_cp": -0.70,
    "load_internal_cp": -0.20,
    "load_rafter_spacing": 0.60,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =====================================================
# 함수 1. 풍하중 계산
# =====================================================
def calculate_wind_load(wind_speed, external_cp, internal_cp, rafter_spacing):
    rho = 1.225  # kg/m3

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
# 작물별 기본 설계 추천 DB
# =====================================================
CROP_DESIGN_DB = {
    "딸기": {
        "default_area_m2": 1000.0,
        "house_height": 4.0,
        "bed_count": 6,
        "bed_width": 1.2,
        "greenhouse_type": "10-단동-1형",
        "rafter_spacing": 0.60,
        "side_purlin_count": 3,
        "roof_purlin_count": 4,
        "rafter_diameter": 31.8,
        "rafter_thickness": 1.5,
        "purlin_diameter": 25.4,
        "purlin_thickness": 1.5,
    },
    "토마토": {
        "default_area_m2": 1200.0,
        "house_height": 4.5,
        "bed_count": 5,
        "bed_width": 1.5,
        "greenhouse_type": "보강아치형",
        "rafter_spacing": 0.50,
        "side_purlin_count": 4,
        "roof_purlin_count": 4,
        "rafter_diameter": 31.8,
        "rafter_thickness": 1.7,
        "purlin_diameter": 25.4,
        "purlin_thickness": 1.5,
    },
    "오이": {
        "default_area_m2": 1000.0,
        "house_height": 4.5,
        "bed_count": 5,
        "bed_width": 1.4,
        "greenhouse_type": "보강아치형",
        "rafter_spacing": 0.50,
        "side_purlin_count": 4,
        "roof_purlin_count": 4,
        "rafter_diameter": 31.8,
        "rafter_thickness": 1.7,
        "purlin_diameter": 25.4,
        "purlin_thickness": 1.5,
    },
    "상추": {
        "default_area_m2": 800.0,
        "house_height": 3.8,
        "bed_count": 7,
        "bed_width": 1.0,
        "greenhouse_type": "10-단동-1형",
        "rafter_spacing": 0.60,
        "side_purlin_count": 3,
        "roof_purlin_count": 3,
        "rafter_diameter": 25.4,
        "rafter_thickness": 1.5,
        "purlin_diameter": 22.2,
        "purlin_thickness": 1.5,
    },
    "파프리카": {
        "default_area_m2": 1500.0,
        "house_height": 5.0,
        "bed_count": 5,
        "bed_width": 1.5,
        "greenhouse_type": "보강아치형",
        "rafter_spacing": 0.50,
        "side_purlin_count": 4,
        "roof_purlin_count": 5,
        "rafter_diameter": 31.8,
        "rafter_thickness": 1.7,
        "purlin_diameter": 25.4,
        "purlin_thickness": 1.5,
    },
}


# =====================================================
# 지역별 하중 추천 DB
# 현재는 예시값. 나중에 실제 기준풍속/적설하중 DB로 교체 가능
# =====================================================
REGION_LOAD_DB = {
    "대구": {
        "basic_wind_speed": 30.0,
        "snow_load": 0.30,
        "region_note": "일반 내륙 조건",
    },
    "부산": {
        "basic_wind_speed": 34.0,
        "snow_load": 0.20,
        "region_note": "해안 인접, 풍하중 주의",
    },
    "울산": {
        "basic_wind_speed": 34.0,
        "snow_load": 0.20,
        "region_note": "해안 인접, 풍하중 주의",
    },
    "강릉": {
        "basic_wind_speed": 36.0,
        "snow_load": 0.40,
        "region_note": "강풍 및 적설 검토 필요",
    },
    "제주": {
        "basic_wind_speed": 40.0,
        "snow_load": 0.10,
        "region_note": "강풍 지역 가정",
    },
    "기본": {
        "basic_wind_speed": 30.0,
        "snow_load": 0.30,
        "region_note": "기본 일반 지역 조건",
    },
}


# =====================================================
# 함수 4. 작물 기준 찾기
# =====================================================
def find_crop_design(crop):
    for key in CROP_DESIGN_DB.keys():
        if key in crop:
            return CROP_DESIGN_DB[key], key

    return CROP_DESIGN_DB["딸기"], "딸기"


# =====================================================
# 함수 5. 지역 기준 찾기
# =====================================================
def find_region_load(region):
    for key in REGION_LOAD_DB.keys():
        if key in region:
            return REGION_LOAD_DB[key], key

    return REGION_LOAD_DB["기본"], "기본"


# =====================================================
# 함수 6. 지역 + 작물 + 폭 기반 자동 추천
# =====================================================
def recommend_design_from_basic_inputs(region, crop, house_width):
    crop_data, crop_key = find_crop_design(crop)
    region_data, region_key = find_region_load(region)

    target_area = crop_data["default_area_m2"]
    house_length = round(target_area / house_width, 1)

    greenhouse_type = crop_data["greenhouse_type"]
    rafter_spacing = crop_data["rafter_spacing"]

    rafter_diameter = crop_data["rafter_diameter"]
    rafter_thickness = crop_data["rafter_thickness"]
    purlin_diameter = crop_data["purlin_diameter"]
    purlin_thickness = crop_data["purlin_thickness"]

    basic_wind_speed = region_data["basic_wind_speed"]
    snow_load = region_data["snow_load"]

    # 강풍 또는 적설 조건이면 보수적으로 자동 보강
    if basic_wind_speed >= 35 or snow_load >= 0.40:
        greenhouse_type = "보강아치형"
        rafter_spacing = min(rafter_spacing, 0.50)
        rafter_diameter = max(rafter_diameter, 31.8)
        rafter_thickness = max(rafter_thickness, 1.7)

    # 풍압계수 임시 추천
    if greenhouse_type == "연동형":
        external_cp = -0.80
        internal_cp = -0.20
    else:
        external_cp = -0.70
        internal_cp = -0.20

    return {
        "input_region": region,
        "matched_region": region_key,
        "region_note": region_data["region_note"],
        "input_crop": crop,
        "matched_crop": crop_key,
        "target_area": target_area,
        "house_width": house_width,
        "house_length": house_length,
        "house_height": crop_data["house_height"],
        "greenhouse_type": greenhouse_type,
        "bed_count": crop_data["bed_count"],
        "bed_width": crop_data["bed_width"],
        "rafter_spacing": rafter_spacing,
        "side_purlin_count": crop_data["side_purlin_count"],
        "roof_purlin_count": crop_data["roof_purlin_count"],
        "rafter_diameter": rafter_diameter,
        "rafter_thickness": rafter_thickness,
        "purlin_diameter": purlin_diameter,
        "purlin_thickness": purlin_thickness,
        "basic_wind_speed": basic_wind_speed,
        "snow_load": snow_load,
        "external_cp": external_cp,
        "internal_cp": internal_cp,
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
            key="load_house_type"
        )

        wind_speed = st.number_input(
            "기본풍속 V (m/s)",
            min_value=0.0,
            step=1.0,
            key="load_wind_speed"
        )

        rafter_spacing = st.number_input(
            "서까래 간격 (m)",
            min_value=0.1,
            step=0.05,
            key="load_rafter_spacing"
        )

    with col2:
        external_cp = st.number_input(
            "외압계수 Cpe",
            step=0.05,
            key="load_external_cp"
        )

        internal_cp = st.number_input(
            "내압계수 Cpi",
            step=0.05,
            key="load_internal_cp"
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
    st.write("지역, 작물, 온실 폭만 입력하면 온실 크기, 부재 규격, 하중조건, 개략 물량과 비용을 자동 추천합니다.")

    st.subheader("1. 기본 입력")

    col1, col2, col3 = st.columns(3)

    with col1:
        input_region = st.text_input(
            "지역",
            value="대구 북구",
            placeholder="예: 대구 북구, 부산 강서구, 제주 서귀포"
        )

    with col2:
        input_crop = st.text_input(
            "작물",
            value="딸기",
            placeholder="예: 딸기, 토마토, 오이, 상추, 파프리카"
        )

    with col3:
        input_width = st.number_input(
            "온실 폭 (m)",
            min_value=3.0,
            max_value=20.0,
            value=8.0,
            step=0.5
        )

    st.subheader("2. 단가 입력")

    col1, col2 = st.columns(2)

    with col1:
        pipe_unit_price = st.number_input(
            "파이프 단가 (원/kg)",
            min_value=0.0,
            value=1800.0,
            step=100.0
        )

    with col2:
        vinyl_unit_price = st.number_input(
            "비닐 단가 (원/m²)",
            min_value=0.0,
            value=2500.0,
            step=100.0
        )

    if st.button("설계안 자동 추천"):
        recommended = recommend_design_from_basic_inputs(
            region=input_region,
            crop=input_crop,
            house_width=input_width
        )

        worksheet_result = calculate_preliminary_design(
            house_width=recommended["house_width"],
            house_length=recommended["house_length"],
            house_height=recommended["house_height"],
            bed_count=recommended["bed_count"],
            bed_width=recommended["bed_width"],
            rafter_spacing=recommended["rafter_spacing"],
            side_purlin_count=recommended["side_purlin_count"],
            roof_purlin_count=recommended["roof_purlin_count"],
            rafter_diameter=recommended["rafter_diameter"],
            rafter_thickness=recommended["rafter_thickness"],
            purlin_diameter=recommended["purlin_diameter"],
            purlin_thickness=recommended["purlin_thickness"],
            pipe_unit_price=pipe_unit_price,
            vinyl_unit_price=vinyl_unit_price,
        )

        st.session_state["recommended_design"] = recommended
        st.session_state["worksheet_result"] = worksheet_result

    if "recommended_design" in st.session_state and "worksheet_result" in st.session_state:
        rec = st.session_state["recommended_design"]
        result = st.session_state["worksheet_result"]

        st.success("설계안 자동 추천이 완료되었습니다.")

        st.subheader("추천 설계안")

        design_df = pd.DataFrame({
            "항목": [
                "입력 지역",
                "적용 지역 조건",
                "지역 조건 설명",
                "입력 작물",
                "적용 작물 기준",
                "추천 온실 형식",
                "목표 재배 규모",
                "추천 온실 폭",
                "추천 온실 길이",
                "추천 온실 높이",
                "추천 서까래 간격",
                "측면 도리 개수",
                "지붕 도리 개수",
                "서까래 규격",
                "도리 규격",
                "기본풍속",
                "적설하중",
                "외압계수 Cpe",
                "내압계수 Cpi",
            ],
            "추천값": [
                rec["input_region"],
                rec["matched_region"],
                rec["region_note"],
                rec["input_crop"],
                rec["matched_crop"],
                rec["greenhouse_type"],
                f'{rec["target_area"]:.1f} m²',
                f'{rec["house_width"]:.1f} m',
                f'{rec["house_length"]:.1f} m',
                f'{rec["house_height"]:.1f} m',
                f'{rec["rafter_spacing"]:.2f} m',
                f'{rec["side_purlin_count"]} 개',
                f'{rec["roof_purlin_count"]} 개',
                f'Ø{rec["rafter_diameter"]} × {rec["rafter_thickness"]} mm',
                f'Ø{rec["purlin_diameter"]} × {rec["purlin_thickness"]} mm',
                f'{rec["basic_wind_speed"]:.1f} m/s',
                f'{rec["snow_load"]:.2f} kN/m²',
                rec["external_cp"],
                rec["internal_cp"],
            ]
        })

        st.table(design_df)

        st.subheader("예비설계 계산 결과")

        summary_df = pd.DataFrame({
            "항목": [
                "온실 바닥면적",
                "온실 체적",
                "재배면적",
                "토지이용률",
                "서까래 개수",
                "계산상 온실 길이",
                "추천 길이와 차이",
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
            st.error("재배면적이 온실 전체면적을 초과합니다. 작물별 이랑 조건을 수정해야 합니다.")

        if abs(result["length_error"]) > 0.05:
            st.warning("서까래 간격으로 계산된 온실 길이가 추천 온실 길이와 약간 다릅니다.")

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

        st.subheader("하중계산 탭으로 적용")

        if st.button("추천 하중조건을 하중계산에 적용"):
            st.session_state["load_house_type"] = rec["greenhouse_type"]
            st.session_state["load_wind_speed"] = rec["basic_wind_speed"]
            st.session_state["load_external_cp"] = rec["external_cp"]
            st.session_state["load_internal_cp"] = rec["internal_cp"]
            st.session_state["load_rafter_spacing"] = rec["rafter_spacing"]

            st.success("추천값이 하중계산 탭에 적용되었습니다.")
            st.rerun()
