
import streamlit as st
import pandas as pd

st.set_page_config(page_title="잠원동에서 나에게 맞는 집", layout="centered")

st.markdown("""
# 🏠 잠원동에서 나에게 맞는 집
#### Proxity가 지금 조건에 맞는 단지를 추천합니다.
""")

# 사용자 입력
with st.form("user_input_form"):
    st.markdown("### 📋 내 조건을 알려주세요")

    col1, col2 = st.columns(2)
    with col1:
        cash = st.number_input("현금(보유+기존주택 매각대금 포함)", 0.0, 100.0, value=16.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액", 0.0, 30.0, value=12.0, step=0.5)

        area_group = st.selectbox("원하는 평형대는?", ["10평 이하", "20평대", "30평대", "40평 이상"])
        year_group = st.selectbox("건물 연식 기준은?", ["재건축", "기축", "신축"])

    with col2:
        lines = st.multiselect("선호하는 지하철 노선은?", ["3호선", "7호선", "9호선", "신분당선", "상관없음"])
        household = st.selectbox("단지 규모는 어느 정도가 좋으세요?", ["대단지", "상관없음"])

    total_budget = cash + loan
    submitted = st.form_submit_button("📍 지금 추천 받기")

# 점수 계산 함수
def score_complex(row, total_budget, area_group, year_group, lines, household):
    score = 0

    if row['2025.05_보정_추정실거래가'] <= total_budget:
        score += 2

    area = row['전용면적']
    if (
        (area_group == "10평 이하" and area <= 33) or
        (area_group == "20평대" and 34 <= area <= 66) or
        (area_group == "30평대" and 67 <= area <= 99) or
        (area_group == "40평 이상" and area >= 100)
    ):
        score += 1.5

    if (
        (year_group == "재건축" and row.get("재건축", "") == "Y") or
        (year_group == "기축" and 1990 <= row['준공연도'] <= 2009) or
        (year_group == "신축" and row['준공연도'] >= 2010)
    ):
        score += 1

    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines):
            score += 1.5
    else:
        score += 1

    if household == "대단지" and row['세대수'] >= 200:
        score += 1
    elif household == "상관없음":
        score += 1

    return score

# 추천 결과 출력
if submitted:
    df = pd.read_csv("data/jw_v0.13_streamlit_ready.csv")

    df["점수"] = df.apply(lambda row: score_complex(row, total_budget, area_group, year_group, lines, household), axis=1)

    # 예산 초과 단지 제외 후 정렬
    df_filtered = df[df['2025.05_보정_추정실거래가'] <= total_budget].copy()
    top3 = df_filtered.sort_values(by=["2025.05_보정_추정실거래가", "점수"], ascending=[False, False]).head(3)

    st.markdown("### 🎯 추천 단지")
    for i, row in top3.iterrows():
        condition_tags = []
        if row['역세권'] == "Y":
            condition_tags.append("역세권")
        if row['세대수'] >= 200:
            condition_tags.append("대단지")
        if row.get("재건축", "") == "Y":
            condition_tags.append("재건축")
        elif row['준공연도'] >= 2010:
            condition_tags.append("신축")
        tag_str = " · ".join(condition_tags)

        st.markdown(f"""#### 🏢 {row['단지명']}
- 전용면적: {row['전용면적']}m² / 준공연도: {row['준공연도']} / 세대수: {row['세대수']}세대
- 최근 실거래가: {row['2025.05_보정_추정실거래가']}억 / 현재 호가: {row['현재호가']}억
- 조건 요약: {tag_str}

> ✅ 예산({total_budget}억) 이내에서 조건을 가장 많이 충족한 단지입니다.  
> {tag_str} 기준으로 실거주와 투자 측면에서 균형이 좋습니다.
""")
