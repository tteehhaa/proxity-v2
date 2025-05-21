import streamlit as st
import pandas as pd
import os

# Streamlit 페이지 설정
st.set_page_config(page_title="잠원동 아파트 단지 추천기 (2025년 5월 v0.1)", layout="centered")

# 앱 제목 및 설명
st.markdown("""
# 잠원동 아파트 단지 추천기  
**2025년 5월 버전 v0.1**

입력하신 조건에 따라 예산, 평형, 건물 컨디션, 선호 노선 등을 종합해  
지금 고려해볼 만한 잠원동 단지를 제안드립니다.
""")

# --- 입력 폼 ---
with st.form("user_input_form"):
    st.markdown("### 조건을 입력해주세요")
    col1, col2 = st.columns(2)
    with col1:
        cash = st.number_input("현금 (예: 16.0억)", min_value=0.0, max_value=100.0, value=16.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액 (예: 12.0억)", min_value=0.0, max_value=30.0, value=12.0, step=0.5)
        area_group = st.selectbox("원하는 평형대", ["상관없음", "10평 이하", "20평대", "30평대", "40평 이상"])
        condition = st.selectbox("건물 컨디션", ["상관없음", "신축", "기축", "리모델링", "재건축"])
    with col2:
        lines = st.multiselect("선호 지하철 노선", ["상관없음", "3호선", "7호선", "9호선", "신분당선"])
        household = st.selectbox("단지 규모", ["상관없음", "대단지", "소단지"])

    # 예산 계산
    total_budget = cash + loan
    flexible_budget = min(2.0, total_budget * 0.2)
    budget_upper = total_budget + flexible_budget
    budget_cap = total_budget * 1.3

    submitted = st.form_submit_button("지금 추천 받기")

# --- 함수 정의 ---
def get_area_range(area_group):
    """평형대(㎡) 범위 반환"""
    if area_group == "10평 이하": return (0, 19 * 3.3)
    elif area_group == "20평대": return (20 * 3.3, 29 * 3.3)
    elif area_group == "30평대": return (30 * 3.3, 39 * 3.3)
    elif area_group == "40평 이상": return (40 * 3.3, 1000)
    return (0, 1000)

def get_pyeong(area):
    """전용면적(㎡)을 평으로 변환"""
    return round(area / 3.3, 1)

def score_complex(row, cash, loan, area_group, condition, lines, household):
    """단지 점수 계산: 사용자 조건과 데이터 일치도 기반"""
    score = 0
    pyeong = get_pyeong(row["전용면적"])
    p_min, p_max = get_area_range(area_group)
    if p_min <= row["전용면적"] <= p_max:
        score += 1.5
    elif area_group == "상관없음":
        score += 1
    building_type = str(row.get("건축유형", "")).strip()
    if condition == "상관없음" or condition in building_type:
        score += 1.5
    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines):
            score += 1.5
    else:
        score += 1
    if household == "대단지" and row['세대수'] >= 1000:
        score += 1
    elif household == "소단지" and row['세대수'] < 1000:
        score += 1
    elif household == "상관없음":
        score += 1
    return score

def round_price(val):
    """가격을 억 단위로 반올림"""
    return f"{round(val, 2):.2f}억" if not pd.isna(val) and val >= 1.0 else "정보 없음"

def get_condition_note(cash, loan, area_group, condition, lines, household, row):
    """사용자 조건과 단지 데이터 간 일치성 설명"""
    notes = []
    if cash > 0:
        notes.append(f"현금 {cash}억")
    if loan > 0:
        notes.append(f"대출 {loan}억")
    actual_area = row["전용면적"]
    area_min, area_max = get_area_range(area_group)
    if area_group != "상관없음" and area_min <= actual_area <= area_max:
        notes.append(f"{area_group}")
    if condition != "상관없음" and condition in str(row.get("건축유형", "")):
        notes.append(f"{condition}")
    if "상관없음" not in lines and row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines):
        notes.append(f"{', '.join(lines)} 노선")
    if household != "상관없음":
        if household == "대단지" and row['세대수'] >= 1000:
            notes.append("대단지")
        elif household == "소단지" and row['세대수'] < 1000:
            notes.append("소단지")
    return "입력하신 조건(" + ", ".join(notes) + ")에 따라 우선순위를 적용해 추천했습니다." if notes else "입력하신 조건을 기반으로 추천했습니다."

def classify_recommendation(row, budget_upper):
    """추천 단지 분류"""
    if row['점수'] >= 4 and row['실사용가격'] <= budget_upper:
        return "예산과 조건을 모두 충족한 단지입니다."
    elif row['실사용가격'] <= budget_upper:
        return "조건 일부가 부합하지 않지만, 예산에 맞춰 추천된 단지입니다."
    else:
        return "예산과 부합하지 않지만, 일부 조건을 충족하여 추천된 단지입니다."

# --- 데이터 처리 및 출력 ---
if submitted:
    # 데이터 로드
    data_file = "data/jw_v0.13_streamlit_ready.csv"
    try:
        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
        else:
            st.error(f"'{data_file}' 파일을 찾을 수 없습니다. 관리자에게 문의해주세요.")
            st.stop()
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {str(e)}")
        st.stop()

    # 데이터 전처리
    df[['단지명', '준공연도', '세대수']] = df[['단지명', '준공연도', '세대수']].fillna(method="ffill")
    df['실거래가'] = pd.to_numeric(df['2025.03'], errors='coerce')
    df['현재호가'] = pd.to_numeric(df['20250521호가'], errors='coerce')
    df['추정가'] = pd.to_numeric(df['2025.05_보정_추정실거래가'], errors='coerce')
    df['거래일'] = pd.to_datetime(df['거래일'], errors='coerce')
    df['거래연도'] = df['거래일'].dt.year

    # 필터링: 가격 1억 이상
    df = df[df['실거래가'] >= 1.0]

    # 점수 계산
    df["점수"] = df.apply(lambda row: score_complex(row, cash, loan, area_group, condition, lines, household), axis=1)

    # 예산 상한 필터링
    df = df[df['실거래가'] <= budget_cap].copy()

    # 실사용가격 설정: 실거래가 > 호가 > 추정가 우선순위
    df['실사용가격'] = df['실거래가']
    df['가격출처'] = '실거래가'
    mask_호가 = df['실사용가격'].isna() & df['현재호가'].notna()
    df.loc[mask_호가, '실사용가격'] = df['현재호가']
    df.loc[mask_호가, '가격출처'] = '호가'
    mask_추정 = df['실사용가격'].isna() & df['추정가'].notna()
    df.loc[mask_추정, '실사용가격'] = df['추정가']
    df.loc[mask_추정, '가격출처'] = '추정'

    # 추정가 허용 상한
    df['추정가허용상한'] = df['실사용가격'] * 1.2
    df = df[~((df['가격출처'] == '추정') & (df['추정가허용상한'] > budget_upper))]

    # 오래된 거래 제외 (2024년 이후)
    df = df[(df['거래연도'].isna()) | (df['거래연도'] >= 2024)]

    # 예산 내 단지 필터링 및 상위 3개 추천
    df_filtered = df[df['실사용가격'] <= budget_upper].copy()
    top3 = df_filtered.sort_values(by=["점수", "세대수"], ascending=[False, False]).head(3)

    # 추천 결과 출력
    st.markdown("### 추천 단지")
    for _, row in top3.iterrows():
        단지명 = row['단지명']
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        면적 = row['전용면적']
        평형 = get_pyeong(면적)
        실거래 = round_price(row['실사용가격'])
        거래일 = row['거래일'].strftime("%Y.%m.%d") if pd.notna(row['거래일']) and row['거래연도'] >= 2024 else "최근 거래 없음"
        출처 = row['가격출처']
        조건설명 = get_condition_note(cash, loan, area_group, condition, lines, household, row)
        추천이유 = classify_recommendation(row, budget_upper)

        st.markdown(f"""#### {단지명}
- 평형: {평형}평 (전용면적: {round(면적, 1)}㎡)
- 준공연도: {준공} / 세대수: {세대}
- 가격: {실거래} (출처: {출처}, 거래일: {거래일})
- 조건 평가: {조건설명}
- 추천 이유: {추천이유}
""")

    st.markdown("---")
    st.markdown("""
    ※ 위 추천은 사용자의 입력 조건과 2025.03 기준가를 종합하여 제안드린 결과입니다.  
    ※ 본 추천 결과는 정보 제공 목적으로 이루어지는 테스트이며, 투자 권유 또는 자문이 아닙니다.  
    ※ 실제 매수 결정 시에는 본인의 판단과 책임 하에 신중히 검토해주시기 바랍니다.
""")
