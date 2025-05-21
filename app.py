
import streamlit as st
import pandas as pd

st.set_page_config(page_title="매수 아파트 단지 탐색기 – 잠원동 편", layout="centered")

st.markdown("""
# 🏠 매수 아파트 단지 탐색기 – 잠원동 편
#### 지금 조건에 맞는 단지를 Proxity가 추천합니다.
""")

# 사용자 입력
with st.form("user_input_form"):
    st.markdown("### 📋 내 조건을 알려주세요")

    col1, col2 = st.columns(2)
    with col1:
        cash = st.number_input("현금 (예: 16.0억)", 0.0, 100.0, value=16.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액 (예: 12.0억)", 0.0, 30.0, value=12.0, step=0.5)
        area_group = st.selectbox("원하는 평형대는?", ["10평 이하", "20평대", "30평대", "40평 이상"])
        condition = st.selectbox("건물 컨디션은?", ["신축", "기축", "리모델링", "재건축"])

    with col2:
        lines = st.multiselect("선호하는 지하철 노선은?", ["3호선", "7호선", "9호선", "신분당선", "상관없음"])
        household = st.selectbox("단지 규모는?", ["대단지", "소단지", "상관없음"])

    total_budget = cash + loan
    submitted = st.form_submit_button("📍 지금 추천 받기")

def score_complex(row, total_budget, area_group, condition, lines, household):
    score = 0

    if row['현재호가'] <= total_budget:
        score += 2

    area = row['전용면적']
    if (
        (area_group == "10평 이하" and area <= 33) or
        (area_group == "20평대" and 34 <= area <= 66) or
        (area_group == "30평대" and 67 <= area <= 99) or
        (area_group == "40평 이상" and area >= 100)
    ):
        score += 1.5

    building_type = str(row.get("건축유형", "")).strip()
    if condition in building_type:
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

    df["점수"] = df.apply(lambda row: score_complex(row, total_budget, area_group, condition, lines, household), axis=1)

    df_filtered = df[df['현재호가'] <= total_budget].copy()
    top3 = df_filtered.sort_values(by=["점수", "세대수"], ascending=[False, False]).head(3)

    st.markdown("### 🎯 추천 단지")

    for i, row in top3.iterrows():
        단지명 = row['단지명']
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        면적 = round(row['전용면적'], 2)
        실거래 = row['2025.05_보정_추정실거래가']
        호가 = row['현재호가']
        유형 = row.get("건축유형", "미상")

        tag_list = []
        if row['역세권'] == "Y":
            tag_list.append("역세권")
        if row['세대수'] >= 1000:
            tag_list.append("대단지")
        else:
            tag_list.append("소단지")
        tag_list.append(유형)
        tag_str = " · ".join(tag_list)

        # 컨디션 충족 여부 설명 분기
        matched_condition = condition in str(row.get("건축유형", ""))
        if matched_condition:
            condition_note = f"💡 선택하신 "{condition}" 컨디션을 충족하는 단지입니다."
        else:
            condition_note = f"⚠️ "{condition}" 조건에 정확히 부합하지 않지만, 
예산과 유사 조건을 고려해 추천드리는 대안 단지입니다."

        st.markdown(f"""#### 🏢 {단지명}
- 전용면적: {면적}㎡ / 준공연도: {준공} / 세대수: {세대}세대
- 최근 실거래가: {실거래}억 / 현재 호가: {호가}억
- 조건 요약: {tag_str}

✅ 예산 {total_budget}억 이내 + 입력 조건을 반영한 추천입니다.

📍 선택하신 컨디션: **{condition}**, 평형: **{area_group}**, 규모: **{household}**

{condition_note}

💡 조건 충족도와 단지 규모 기준으로 우선순위 정렬된 단지입니다.
""")
