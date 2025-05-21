import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="매수 아파트 단지 탐색기 - 잠원동 편 (2025년 5월 v0.1)", layout="centered")

st.title("매수 아파트 단지 탐색기 - 잠원동 편 (2025년 5월 v0.1)")

with st.form("user_input"):
    st.subheader("내 조건 입력")

    col1, col2 = st.columns(2)
    with col1:
        budget = st.number_input("총 예산 (억 단위, 예: 24)", min_value=5.0, max_value=100.0, step=0.5)
        area_pref = st.selectbox("희망 평형", ["상관없음", "20평대", "30평대", "40평대"])
        condition = st.selectbox("건물 컨디션 선호", ["상관없음", "신축", "기축", "리모델링", "재건축"])
    with col2:
        subway_line = st.selectbox("선호 지하철 노선", ["상관없음", "3호선", "7호선", "9호선", "신분당선"])
        household_pref = st.radio("단지 규모", ["상관없음", "대단지(1000세대 이상)", "소단지(1000세대 미만)"])

    submitted = st.form_submit_button("단지 추천 받기")

if submitted:
    df = pd.read_csv("data/jw_v0.13_streamlit_ready.csv")
    df[["단지명", "준공연도", "세대수"]] = df[["단지명", "준공연도", "세대수"]].fillna(method="ffill")

    df = df[df["2025.05_보정_추정실거래가"] >= 1.0]

    df["실사용가격"] = df["20250521호가"]
    df["가격출처"] = "호가"
    mask = df["실사용가격"].isna() & df["2025.05_보정_추정실거래가"].notna()
    df.loc[mask, "실사용가격"] = df["2025.05_보정_추정실거래가"]
    df.loc[mask, "가격출처"] = "추정"

    # 예산 범위 확장: +10%까지 허용 (단, 최대 1억 추가만 허용)
    upper_limit = budget + min(1.0, budget * 0.1)
    df = df[(df["실사용가격"] > 1.0) & (df["실사용가격"] <= upper_limit)]

    # 평형 필터링
    if area_pref != "상관없음":
        if area_pref == "20평대":
            df = df[(df["평형"] >= 20) & (df["평형"] < 30)]
        elif area_pref == "30평대":
            df = df[(df["평형"] >= 30) & (df["평형"] < 40)]
        elif area_pref == "40평대":
            df = df[(df["평형"] >= 40) & (df["평형"] < 50)]

    if condition != "상관없음":
        df = df[df["건물컨디션"] == condition]

    if subway_line != "상관없음":
        df = df[df["노선"].str.contains(subway_line, na=False)]

    if household_pref == "대단지(1000세대 이상)":
        df = df[df["세대수"] >= 1000]
    elif household_pref == "소단지(1000세대 미만)":
        df = df[df["세대수"] < 1000]

    df["추천점수"] = 0
    if condition != "상관없음":
        df["추천점수"] += 1
    if subway_line != "상관없음":
        df["추천점수"] += 1
    if household_pref != "상관없음":
        df["추천점수"] += 1
    if area_pref != "상관없음":
        df["추천점수"] += 1

    df = df.sort_values(by=["추천점수", "세대수", "실사용가격"], ascending=[False, False, False])

    if len(df) == 0:
        st.warning("조건에 맞는 단지가 없습니다. 조건을 완화해보세요.")
    else:
        st.subheader("추천 단지")

        for _, row in df.head(3).iterrows():
            st.markdown(f"### {row['단지명']}")
            st.markdown(f"- 평형: {int(row['평형'])}평 (전용면적: {round(row['전용면적'],1)}m2)")
            st.markdown(f"- 준공연도: {int(row['준공연도'])} / 세대수: {int(row['세대수'])}")

            거래가 = round(row['2025.05_보정_추정실거래가'], 2)
            if row["가격출처"] == "호가":
                호가 = round(row["실사용가격"], 2)
                st.markdown(f"- 실거래가(2025.05 기준): {거래가}억")
                st.markdown(f"- 현재 호가 기준 예상가: {호가}억")
            else:
                st.markdown(f"- 현재 해당 평형 매물은 없으나, 예산 범위 내 매물로 추정됩니다.")

            st.markdown("**조건 평가:** 입력하신 조건을 바탕으로 추천드리는 단지입니다. 상황에 따라 세대수, 추정 실거래가 등 여러 요소를 종합적으로 고려하여 선별하였습니다.\n")
