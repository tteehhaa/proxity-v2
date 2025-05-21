
import streamlit as st
import pandas as pd

st.set_page_config(page_title="잠원동에서 나에게 맞는 집", layout="centered")

st.markdown("""
# 🏠 매수 아파트 단지 탐색기 - 잠원동 편
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

    # 병합 깨진 셀 보정
    df[['단지명', '준공연도', '세대수']] = df[['단지명', '준공연도', '세대수']].fillna(method="ffill")

    # 숫자형 변환 (쉼표 있는 경우 대비 가능)
    df['현재호가'] = pd.to_numeric(df['현재호가'], errors='coerce')
    df['2025.05_보정_추정실거래가'] = pd.to_numeric(df['2025.05_보정_추정실거래가'], errors='coerce')

    # 점수 계산
    df["점수"] = df.apply(lambda row: score_complex(row, total_budget, area_group, year_group, lines, household), axis=1)

    # 예산 이내 단지만 추천 대상
    df_filtered = df[df['현재호가'] <= total_budget].copy()

    # 예산 꽉 채운 순 → 점수 순
    top3 = df_filtered.sort_values(by=["현재호가", "점수"], ascending=[False, False]).head(3)

    st.markdown("### 🎯 추천 단지")

    for i, row in top3.iterrows():
        # 안전한 기본값 처리
        단지명 = row['단지명'] if pd.notna(row['단지명']) else "이름 없음"
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        면적 = round(row['전용면적'], 2)
        실거래 = row['2025.05_보정_추정실거래가']
        호가 = row['현재호가']

        # 단지 조건 태그
        tag_list = []
        if row['역세권'] == "Y":
            tag_list.append("역세권")
        if row['세대수'] >= 200:
            tag_list.append("대단지")
        if row.get("재건축", "") == "Y":
            tag_list.append("재건축")
        elif row['준공연도'] >= 2010:
            tag_list.append("신축")
        tag_str = " · ".join(tag_list)

        # 사용자 조건 요약
        user_tags = []
        if "10평 이하" in area_group:
            user_tags.append("10평 이하")
        elif "20" in area_group:
            user_tags.append("20평대")
        elif "30" in area_group:
            user_tags.append("30평대")
        elif "40" in area_group:
            user_tags.append("40평 이상")
        user_tags.append(year_group)
        if household == "대단지":
            user_tags.append("대단지")
        if "상관없음" not in lines:
            user_tags += lines
        user_tag_str = ", ".join(user_tags)

        # 설명 출력
        st.markdown(f"""#### 🏢 {단지명}
- 전용면적: {면적}㎡ / 준공연도: {준공} / 세대수: {세대}세대
- 최근 실거래가: {실거래}억 / 현재 호가: {호가}억
- 조건 요약: {tag_str}

✅ 예산 {total_budget}억 이내에서 추천된 단지입니다.

📍 입력하신 선호 조건:
- {user_tag_str}

💡 이 단지는 위 조건 대부분을 충족하며,  
**현재 호가 기준 실구매 가능 + 향후 가치 측면에서 균형이 좋은 단지**로 판단되어 추천되었습니다.
""")

