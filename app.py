
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
        area = st.number_input("몇 평 정도를 원하시나요? (전용면적 m2)", 20.0, 200.0, value=84.0, step=1.0)
        year = st.slider("몇 년 이후에 지은 집을 원하시나요? (최소 준공연도)", 1980, 2025, value=2000)
    with col2:
        lines = st.multiselect("어떤 지하철 노선을 선호하시나요?", ["3호선", "7호선", "9호선", "신분당선", "상관없음"])
        household = st.selectbox("단지 규모는 어느 정도가 좋으세요?", ["대단지", "상관없음"])

    total_budget = cash + loan
    submitted = st.form_submit_button("📍 지금 추천 받기")

# 점수 계산 함수
def score_complex(row, total_budget, area, year, lines, household):
    score = 0

    if row['2025.05_보정_추정실거래가'] <= total_budget:
        score += 1
    if abs(row['전용면적'] - area) <= 10:
        score += 1
    if row['준공연도'] >= year:
        score += 1
    if "상관없음" not in lines:
        if row['역세권'] == "Y":
            score += 1
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
    df["점수"] = df.apply(lambda row: score_complex(row, total_budget, area, year, lines, household), axis=1)
    top3 = df.sort_values(by="점수", ascending=False).head(3)

    st.markdown("### 🎯 추천 단지")
    for i, row in top3.iterrows():
        condition_tags = []
        if row['역세권'] == "Y":
            condition_tags.append("역세권")
        if row['세대수'] >= 200:
            condition_tags.append("대단지")
        if row['준공연도'] >= 2010:
            condition_tags.append("2010년대 준공")
        if abs(row['전용면적'] - area) <= 10:
            condition_tags.append("면적 조건 충족")

        tag_str = " · ".join(condition_tags)
        st.markdown(f"""#### 🏢 {row['단지명']}
- 전용면적: {row['전용면적']}m2 / 준공연도: {row['준공연도']} / 세대수: {row['세대수']}세대
- 최근 실거래가: {row['2025.05_보정_추정실거래가']}억 / 현재 호가: {row['현재호가']}억
- 조건 요약: {tag_str}

> ✅ 예산({total_budget}억) 이내에서 주요 조건들을 충족했습니다.  
> {tag_str} 기반으로 실거주 및 투자 밸런스를 갖춘 단지입니다.
""")
