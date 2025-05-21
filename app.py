import streamlit as st
import pandas as pd

st.set_page_config(page_title="잠원동 아파트 단지 추천기 (2025년 5월 v0.1)", layout="centered")

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
        cash = st.number_input("현금 (예: 16.0억)", 0.0, 100.0, value=16.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액 (예: 12.0억)", 0.0, 30.0, value=12.0, step=0.5)
        area_group = st.selectbox("원하는 평형대", ["상관없음", "10평 이하", "20평대", "30평대", "40평 이상"])
        condition = st.selectbox("건물 컨디션", ["상관없음", "신축", "기축", "리모델링", "재건축"])
    with col2:
        lines = st.multiselect("선호 지하철 노선", ["상관없음", "3호선", "7호선", "9호선", "신분당선"])
        household = st.selectbox("단지 규모", ["대단지", "소단지", "상관없음"])

    total_budget = cash + loan
    flexible_budget = min(2.0, total_budget * 0.2)
    budget_upper = total_budget + flexible_budget
    budget_cap = total_budget * 1.3
    budget_half = total_budget * 0.5

    submitted = st.form_submit_button("지금 추천 받기")

# --- 함수 정의 ---
def get_area_range(area_group):
    if area_group == "10평 이하": return (0, 19)
    elif area_group == "20평대": return (20, 29)
    elif area_group == "30평대": return (30, 39)
    elif area_group == "40평 이상": return (40, 1000)
    return (0, 1000)

def score_complex(row, area_group, condition, lines, household):
    score = 0
    pyeong = row.get("평형") or get_pyeong(row["전용면적"])  # 평형 컬럼이 있으면 우선 사용
    p_min, p_max = get_pyeong_range(area_group)
    if p_min <= pyeong <= p_max:
        score += 1.5
    elif area_group == "상관없음":
        score += 1
    building_type = str(row.get("건축유형", "")).strip()
    if condition == "상관없음" or condition in building_type: score += 1.5
    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines): score += 1.5
    else: score += 1
    if household == "대단지" and row['세대수'] >= 1000: score += 1
    elif household == "소단지" and row['세대수'] < 1000: score += 1
    elif household == "상관없음": score += 1
    return score

def round_price(val):
    return f"{round(val, 2):.2f}억" if not pd.isna(val) and val >= 1.0 else "정보 없음"

def get_pyeong(area):
    return round(area / 3.3, 1) + "평"  # 기존에도 있던 함수

def get_condition_note(cash, loan, area_group, condition, lines, household, row):
    notes = []
    if cash > 0: notes.append(f"현금 {cash}억")
    if loan > 0: notes.append(f"대출 {loan}억")

    # 정확한 면적 그룹 일치 여부 판단
    actual_area = row["전용면적"]
    actual_pyeong = actual_area / 3.3
    area_min, area_max = get_area_range(area_group)
    if area_group != "상관없음" and (area_min <= actual_area <= area_max):
        notes.append(f"{area_group}")

    if condition != "상관없음" and condition in str(row.get("건축유형", "")):
        notes.append(f"{condition}")
    if "상관없음" not in lines and row['역세권'] == "Y":
        notes.append(f"{', '.join(lines)} 노선")
    if household != "상관없음":
        if household == "대단지" and row['세대수'] >= 1000:
            notes.append("대단지")
        elif household == "소단지" and row['세대수'] < 1000:
            notes.append("소단지")

    return "입력하신 조건(" + ", ".join(notes) + ")에 따라 우선순위를 적용해 추천했습니다." if notes else "입력하신 조건을 기반으로 추천했습니다."

def classify_recommendation(row):
    if row['점수'] >= 4 and row['실사용가격'] <= budget_upper:
        return "예산과 조건을 모두 충족한 단지입니다."
    elif row['실사용가격'] <= budget_upper:
        return "조건 일부가 부합하지 않지만, 예산에 맞춰 추천된 단지입니다."
    else:
        return "예산과 부합하지 않지만, 일부 조건을 충족하여 추천된 단지입니다."

# --- 처리 및 출력 ---
if submitted:
    df = pd.read_csv("data/jw_v0.13_streamlit_ready.csv")
    df[['단지명', '준공연도', '세대수']] = df[['단지명', '준공연도', '세대수']].fillna(method="ffill")

    df['실거래가'] = pd.to_numeric(df['2025.03'], errors='coerce')
    df['현재호가'] = pd.to_numeric(df['20250521호가'], errors='coerce')
    df['2025.05_보정_추정실거래가'] = pd.to_numeric(df['2025.05_보정_추정실거래가'], errors='coerce')
    df["점수"] = df.apply(lambda row: score_complex(row, area_group, condition, lines, household), axis=1)

    # 실사용가격 계산: 실거래가 > 호가 > 추정가
    df['실사용가격'] = df['실거래가']
    df['가격출처'] = '실거래가'
    mask_ho = df['실사용가격'].isna() & df['현재호가'].notna()
    df.loc[mask_ho, '실사용가격'] = df['현재호가']
    df.loc[mask_ho, '가격출처'] = '호가'
    df = df[df['2025.05_보정_추정실거래가'] <= budget_cap]

    # 추정가 +10%가 예산 내인 경우 추정가 사용
    mask_est = df['실사용가격'].isna() & df['2025.05_보정_추정실거래가'].notna()
    df.loc[mask_est, '실사용가격'] = df['2025.05_보정_추정실거래가'] * 1.1
    df.loc[mask_est, '가격출처'] = '추정'

    # 너무 비싼 추정 단지 제외
    df = df[~((df['가격출처'] == '추정') & (df['실사용가격'] > budget_upper))]

    # 예산 범위 내 단지 필터링
    df_filtered = df[df['실사용가격'] <= budget_upper].copy()

    # 3개 미만일 경우 예산 초과 일부 포함
    if len(df_filtered) < 3:
        extra = df[(df['실사용가격'] > budget_upper) & (df['실사용가격'] <= budget_cap)]
        df_filtered = pd.concat([df_filtered, extra])
        df_filtered = df_filtered.drop_duplicates(subset=['단지명', '전용면적'])

    # 같은 단지 중복 제거, 세대수 기준 정렬
    top3 = df_filtered.sort_values(by=["세대수", "점수"], ascending=[False, False])\
                      .drop_duplicates(subset=["단지명"])\
                      .head(3)

    top3['추천이유'] = top3.apply(classify_recommendation, axis=1)

    # 신축 조건이지만 없을 경우 안내
    has_new = any("신축" in str(row.get("건축유형", "")) for _, row in top3.iterrows())
    if condition == "신축" and not has_new:
        st.info("요청하신 '신축' 조건에 정확히 부합하는 단지는 현재 없습니다. 조건 중 일부를 완화하여 대안 단지를 추천드립니다.")

    st.markdown("### 추천 단지")
    for _, row in top3.iterrows():
        단지명 = row['단지명']
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        면적 = row['전용면적']
        평형 = row.get("평형", get_pyeong(면적))
        실거래가 = round_price(row['실거래가'])
        거래일 = row['거래일'] if pd.notna(row['거래일']) and str(row['거래일']).startswith("2024") or str(row['거래일']).startswith("2025") else "2024년 이후 거래 없음"
        호가 = round_price(row['현재호가'])
        출처 = row['가격출처']
        조건설명 = get_condition_note(cash, loan, area_group, condition, lines, household, row)
        추천사유 = row['추천이유']

        st.markdown(f"""#### {단지명}
- 평형: {평형} (전용면적: {round(면적, 1)}m²)
- 준공연도: {준공} / 세대수: {세대}
- 마지막 실거래가: {실거래가} (거래일: {거래일})
- {f"현재 호가: {호가}" if 출처 == "호가" else "현재 매물은 없지만 예산 범위 내로 추정되는 단지입니다."}

조건 평가: {조건설명}  
추천 사유: {추천사유}
""")

    st.markdown("---")
    st.markdown("""
    ※ 위 추천은 사용자의 입력 조건과 시장 정보를 종합적으로 판단하여 제안드린 결과입니다.  
    ※ 본 추천 결과는 정보 제공 목적으로 이루어지는 테스트이며, 투자 권유 또는 자문이 아닙니다.  
    ※ 실제 매수 결정 시에는 본인의 판단과 책임 하에 신중히 검토해주시기 바랍니다.
""")

