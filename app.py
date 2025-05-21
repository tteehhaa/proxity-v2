import streamlit as st
import pandas as pd

st.set_page_config(page_title="매수 아파트 단지 탐색기 – 잠원동 편", layout="centered")

st.markdown("""
# 🏠 매수 아파트 단지 탐색기 – 잠원동 편
#### 지금 조건에 맞는 단지를 Proxity가 추천합니다.
""")

with st.form("user_input_form"):
    st.markdown("### 📋 내 조건을 알려주세요")

    col1, col2 = st.columns(2)
    with col1:
        cash = st.number_input("현금 (예: 16.0억)", 0.0, 100.0, value=16.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액 (예: 12.0억)", 0.0, 30.0, value=12.0, step=0.5)
        area_group = st.selectbox("원하는 평형대는?", ["10평 이하", "20평대", "30평대", "40평 이상"])
        condition = st.selectbox("건물 컨디션은?", ["상관없음", "신축", "기축", "리모델링", "재건축"])

    with col2:
        lines = st.multiselect("선호하는 지하철 노선은?", ["상관없음", "3호선", "7호선", "9호선", "신분당선"])
        household = st.selectbox("단지 규모는?", ["대단지", "소단지", "상관없음"])

    total_budget = cash + loan
    flexible_budget = min(1.0, total_budget * 0.1)
    budget_upper = total_budget + flexible_budget
    budget_cap = total_budget * 1.3

    submitted = st.form_submit_button("📍 지금 추천 받기")

def score_complex(row, budget_upper, area_group, condition, lines, household):
    score = 0
    area = row['전용면적']

    if (
        (area_group == "10평 이하" and area <= 33) or
        (area_group == "20평대" and 34 <= area <= 66) or
        (area_group == "30평대" and 67 <= area <= 99) or
        (area_group == "40평 이상" and area >= 100)
    ):
        score += 1.5

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

if submitted:
    df = pd.read_csv("data/jw_v0.13_streamlit_ready.csv")
    df[['단지명', '준공연도', '세대수']] = df[['단지명', '준공연도', '세대수']].fillna(method="ffill")
    df['현재호가'] = pd.to_numeric(df['20250521호가'], errors='coerce')
    df['2025.05_보정_추정실거래가'] = pd.to_numeric(df['2025.05_보정_추정실거래가'], errors='coerce')

    df["점수"] = df.apply(lambda row: score_complex(row, budget_upper, area_group, condition, lines, household), axis=1)
    df = df[df['2025.05_보정_추정실거래가'] <= budget_cap].copy()

    df['실사용가격'] = df['현재호가']
    df['가격출처'] = "호가"
    missing_price_mask = df['실사용가격'].isna() & df['2025.05_보정_추정실거래가'].notna()
    df.loc[missing_price_mask, '실사용가격'] = df['2025.05_보정_추정실거래가']
    df.loc[missing_price_mask, '가격출처'] = "추정"

    df_filtered = df[df['실사용가격'] <= budget_upper].copy()
    top3 = df_filtered.sort_values(by=["점수", "세대수"], ascending=[False, False]).head(3)

    st.markdown("### 🎯 추천 단지")

    for i, row in top3.iterrows():
        단지명 = row['단지명']
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        면적 = round(row['전용면적'], 2)
        실거래 = row['2025.05_보정_추정실거래가']
        호가 = row['실사용가격']
        출처 = row['가격출처']
        유형 = row.get("건축유형", "미상")

        matched_condition = condition == "상관없음" or condition in str(row.get("건축유형", ""))
        if matched_condition:
            condition_note = "입력하신 조건을 바탕으로 추천드리는 단지입니다."
        else:
            condition_note = f'"{condition}" 조건에는 정확히 일치하지 않지만, 유사한 조건과 예산 내 우수 단지로 판단되어 제안드립니다.'

        price_note = ""
        if 출처 == "추정":
            price_note = "현재 호가 정보가 없어, 추정 실거래가 기준으로 추천되었습니다."

        st.markdown(f"""#### 🏢 {단지명}
- 전용면적: {면적}㎡ / 준공연도: {준공} / 세대수: {세대}세대
- 실거래가(2025.05 기준): {실거래}억 / 사용된 가격({출처}): {호가}억

✅ {condition_note}
{price_note}

📌 세대수, 지하철 접근성, 건물 컨디션 등 종합 기준으로 선별된 단지입니다.
""")
