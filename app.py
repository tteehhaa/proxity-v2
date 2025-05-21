
import streamlit as st
import pandas as pd

st.set_page_config(page_title="잠원동 아파트 단지 추천기 (2025년 5월 v0.1)", layout="centered")

st.markdown("""
# 잠원동 아파트 단지 추천기
**2025년 5월 버전 v0.1**

사용자의 조건을 기반으로, 잠원동 내에서 예산에 부합하고 선호 조건에 가장 적합한 아파트 단지를 추천해드립니다.
""")

with st.form("user_input_form"):
    st.markdown("### 조건을 입력해주세요")
    col1, col2 = st.columns(2)
    with col1:
        cash = st.number_input("현금 (예: 16.0억)", 0.0, 100.0, value=16.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액 (예: 12.0억)", 0.0, 30.0, value=12.0, step=0.5)
        area_group = st.selectbox("원하는 평형대", ["상관없음", "10평 이하", "20평대", "30평대", "40평 이상"])
        condition = st.selectbox("건물 컨디션", ["상관없음", "신축", "기축", "리모델링", "재건축"])
    with col2:
        lines = st.multiselect("선호 지하철 노선", ["상관없음", "3호선", "7호선", "9호선", "신분당선"], default=["상관없음"])
        household = st.selectbox("단지 규모", ["대단지", "소단지", "상관없음"])

    total_budget = cash + loan
    flexible_budget = min(1.0, total_budget * 0.1)
    budget_upper = total_budget + flexible_budget
    budget_cap = total_budget * 1.3
    budget_half = total_budget * 0.5
    submitted = st.form_submit_button("지금 추천 받기")

def get_area_range(area_group):
    if area_group == "10평 이하": return (0, 33)
    elif area_group == "20평대": return (34, 66)
    elif area_group == "30평대": return (67, 99)
    elif area_group == "40평 이상": return (100, 1000)
    return (0, 1000)

def score_complex(row, area_group, condition, lines, household):
    score = 0
    area = row['전용면적']
    area_min, area_max = get_area_range(area_group)
    if area_min <= area <= area_max: score += 1.5
    elif area_group == "상관없음": score += 1
    building_type = str(row.get("건축유형", "")).strip()
    if condition == "상관없음" or condition in building_type: score += 1.5
    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines): score += 1.5
    else: score += 1
    if household == "대단지" and row['세대수'] >= 1000: score += 1
    elif household == "소단지" and row['세대수'] < 1000: score += 1
    elif household == "상관없음": score += 1
    return score

def round_price(val): return f"{round(val, 2):.2f}억" if not pd.isna(val) else "정보 없음"
def get_pyeong(area): return str(int(round(area / 3.3))) + "평"

if submitted:
    df = pd.read_csv("data/jw_v0.13_streamlit_ready.csv")
    df[['단지명', '준공연도', '세대수']] = df[['단지명', '준공연도', '세대수']].fillna(method="ffill")
    df['현재호가'] = pd.to_numeric(df['20250521호가'], errors='coerce')
    df['2025.05_보정_추정실거래가'] = pd.to_numeric(df['2025.05_보정_추정실거래가'], errors='coerce')
    df["점수"] = df.apply(lambda row: score_complex(row, area_group, condition, lines, household), axis=1)
    df = df[df['2025.05_보정_추정실거래가'] <= budget_cap].copy()
    df['실사용가격'] = df['현재호가']
    df['가격출처'] = "호가"
    mask = df['실사용가격'].isna() & df['2025.05_보정_추정실거래가'].notna()
    df.loc[mask, '실사용가격'] = df['2025.05_보정_추정실거래가']
    df.loc[mask, '가격출처'] = "추정"
    df = df[~((df['실사용가격'].isna()) & (df['2025.05_보정_추정실거래가'] > budget_half))]
    df_filtered = df[df['실사용가격'] <= budget_upper].copy()
    top3 = df_filtered.sort_values(by=["점수", "세대수"], ascending=[False, False]).head(3)

    st.markdown("### 추천 단지")
    for _, row in top3.iterrows():
        단지명 = row['단지명']
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        면적 = row['전용면적']
        평형 = get_pyeong(면적)
        실거래 = round_price(row['2025.05_보정_추정실거래가'])
        출처 = row['가격출처']
        유형 = row.get("건축유형", "미상")
        matched = condition == "상관없음" or condition in 유형
        note = "입력하신 조건을 바탕으로 추천드리는 단지입니다." if matched else f'"{condition}" 조건에는 완전히 부합하지 않지만 유사 조건을 바탕으로 추천드립니다.'
        price_note = "현재 해당 평형 매물은 없으나, 예산 범위 내 매물로 추정됩니다." if 출처 == "추정" else ""
        st.markdown(f"""#### {단지명}
- 전용면적: {round(면적, 1)}m2 ({평형})
- 준공연도: {준공} / 세대수: {세대}
- 실거래가(2025.05 기준): {실거래}
- {price_note}

조건 평가: {note}

입력하신 기준을 종합적으로 고려하여 선별된 단지입니다.
""")
