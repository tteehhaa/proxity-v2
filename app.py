import streamlit as st
import pandas as pd
import math
import os

# Streamlit 페이지 설정
st.set_page_config(page_title="아파트 단지 추천 프로그램 (2025년 5월 잠원동생집사v0.1)", layout="centered")

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
        cash = st.number_input("현금 (예: 16.0억)", min_value=0.0, max_value=100.0, value=3.0, step=0.5)
        loan = st.number_input("주택담보대출 가능 금액 (예: 12.0억)", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
        area_group = st.selectbox("원하는 평형대", ["상관없음", "10평대", "20평대", "30평대", "40평 이상"])
        condition = st.selectbox("건물 컨디션", ["상관없음", "신축", "기축", "리모델링", "재건축"])
    with col2:
        lines = st.multiselect("선호 지하철 노선", ["상관없음", "3호선", "7호선", "9호선", "신분당선"])
        if "상관없음" in lines:
            lines = []
        household = st.selectbox("단지 규모", ["상관없음", "1000세대 이상 대단지", "세대수 300세대 이상", "세대수 300세대 이하"])
        household_map = {
            "1000세대 이상 대단지": "대단지",
            "세대수 300세대 이상": "소단지 (300세대 이상)",
            "세대수 300세대 이하": "소단지 (300세대 이하)",
            "상관없음": "상관없음"
        }
        household = household_map[household]


    # 예산 계산
    total_budget = cash + loan
    budget_upper = total_budget * 1.1  # +10% 추가 예산

    submitted = st.form_submit_button("지금 추천 받기")

# --- 함수 정의 ---
def get_area_range(area_group):
    """평형대 범위 반환 (평형 열 기준)"""
    if area_group == "10평대": return (0, 19.9)
    elif area_group == "20평대": return (20, 29.9)
    elif area_group == "30평대": return (30, 39.9)
    elif area_group == "40평 이상": return (40, 1000)
    return (0, 1000)

def estimate_similar_asking_price(row, df):
    """동일 단지 내 유사 평형 호가 추정"""
    if pd.isna(row['현재호가']):
        complex_name = row['단지명']
        target_area = math.floor(row['전용면적'])
        similar_units = df[(df['단지명'] == complex_name) & df['현재호가'].notna()]
        if not similar_units.empty:
            similar_units['면적차이'] = abs(similar_units['전용면적'].apply(math.floor) - target_area)
            closest_unit = similar_units.loc[similar_units['면적차이'].idxmin()]
            closest_area = closest_unit['전용면적']
            closest_price = closest_unit['현재호가']
            estimated_price = (closest_price / closest_area) * row['전용면적']
            return estimated_price, "동일단지 유사평형 호가 추정", closest_area
    return row['현재호가'], "호가", row['전용면적']

def score_complex(row, cash, loan, area_group, condition, lines, household):
    """단지 점수 계산: 사용자 조건과 데이터 일치도 기반"""
    score = 0
    pyeong = row["평형"]
    p_min, p_max = get_area_range(area_group)
    if p_min <= pyeong <= p_max:
        score += 1.5
    elif area_group == "상관없음":
        score += 1
    building_type = str(row.get("건축유형", "")).strip()
    if condition == "신축" and (row['준공연도'] >= 2018 or building_type == "신축"):
        score += 2.5
    elif condition == "상관없음" or condition == building_type:
        score += 1.5
    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines):
            score += 1.5
    else:
        score += 1
    세대수 = row['세대수'] if pd.notna(row['세대수']) else 0
    if household == "대단지" and 세대수 >= 1000:
        score += 1
    elif household == "소단지 (300세대 이상)" and 300 <= 세대수 < 1000:
        score += 1
    elif household == "소단지 (300세대 이하)" and 세대수 < 300:
        score += 1
    elif household == "상관없음":
        score += 1
    return score

def score_correlated_factors(row, area_group, condition, lines, household):
    """상관 요소(노선, 규모, 컨디션, 평형대)에 따른 추가 점수"""
    score = 0
    pyeong = row["평형"]
    p_min, p_max = get_area_range(area_group)
    if area_group != "상관없음" and p_min <= pyeong <= p_max:
        score += 0.5
    building_type = str(row.get("건축유형", "")).strip()
    if condition != "상관없음":
        if condition == "신축" and (row['준공연도'] >= 2018 or building_type == "신축"):
            score += 0.5
        elif condition == building_type:
            score += 0.5
    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines):
            score += 0.5
    세대수 = row['세대수'] if pd.notna(row['세대수']) else 0
    if household != "상관없음":
        if household == "대단지" and 세대수 >= 1000:
            score += 0.5
        elif household == "소단지 (300세대 이상)" and 300 <= 세대수 < 1000:
            score += 0.5
        elif household == "소단지 (300세대 이하)" and 세대수 < 300:
            score += 0.5
    return score

def round_price(val, price_type, is_estimated=False):
    """가격을 억 단위로 반올림, 실거래가는 범위 없이 정확한 금액, 호가/추정가는 +10% 범위 포함"""
    if pd.isna(val) or val < 1.0:
        return "현재 매물 없음"
    if price_type == "실거래가":
        return f"{round(val, 2):.2f}억"
    if price_type in ["호가", "동일단지 유사평형 호가 추정"] or is_estimated:
        upper = round(val * 1.1, 2)
        return f"{round(val, 2):.2f}~{upper:.2f}억"
    return f"{round(val, 2):.2f}억"

def get_condition_note(cash, loan, area_group, condition, lines, household, row):
    """사용자 조건 설명"""
    notes = []
    condition_mismatch = False
    if cash > 0:
        notes.append(f"현금 {cash}억")
    if loan > 0:
        notes.append(f"대출 {loan}억")
    actual_pyeong = row["평형"]
    p_min, p_max = get_area_range(area_group)
    if area_group != "상관없음":
        if p_min <= actual_pyeong <= p_max:
            notes.append(f"{area_group}")
        else:
            condition_mismatch = True
    if condition != "상관없음":
        building_type = str(row.get("건축유형", "")).strip()
        if condition == "신축" and (row['준공연도'] >= 2018 or building_type == "신축"):
            notes.append("신축")
        elif condition == building_type:
            notes.append(f"{condition}")
        else:
            condition_mismatch = True
    if "상관없음" not in lines:
        if row['역세권'] == "Y" and any(line in str(row.get("노선", "")) for line in lines):
            notes.append(f"{', '.join(lines)} 노선")
        else:
            condition_mismatch = True
    if household != "상관없음":
        세대수 = row['세대수'] if pd.notna(row['세대수']) else 0
        if household == "대단지" and 세대수 >= 1000:
            notes.append("대단지")
        elif household == "소단지 (300세대 이상)" and 300 <= 세대수 < 1000:
            notes.append("소단지 (300세대 이상)")
        elif household == "소단지 (300세대 이하)" and 세대수 < 300:
            notes.append("소단지 (300세대 이하)")
        else:
            condition_mismatch = True
    condition_text = "입력하신 조건(" + ", ".join(notes) + ")에 따라 추천된 단지입니다." if notes else "입력하신 조건을 기반으로 추천된 단지입니다."
    return condition_text, condition_mismatch

def classify_recommendation(row, budget_upper, total_budget):
    """추천 이유 분류: 예산 범위 및 10% 조건 반영, 매물 여부 반영"""
    budget_ten_percent = total_budget * 0.1  # 예산의 10%
    # 매물 여부 확인: 가격출처가 "호가"가 아니거나 현재호가가 없는 경우
    has_naver_listing = (row['가격출처'] == "호가") and not pd.isna(row['현재호가'])

    # 매물이 없는 경우
    if not has_naver_listing:
        return "입력하신 조건을 고려할 때, 매물이 있다면 고려 가능합니다."
    
    # 매물이 있는 경우 예산 조건에 따라 분류
    if row['실사용가격'] <= total_budget:
        return "입력하신 예산 범위 내에 속하는 단지입니다."
    elif row['실사용가격'] <= budget_upper:
        return "입력하신 예산의 10% 이내에 속하는 단지입니다."
    else:
        additional_budget = round(row['실사용가격'] - budget_upper, 2)
        return f"입력하신 예산을 초과하나, 조건에 부합해 추천드립니다. 약 {additional_budget}억의 추가 예산이 필요합니다."

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
    # 단지명 기준으로 세대수, 준공연도, 건축유형, 역세권, 노선 채우기
    df[['단지명', '준공연도', '세대수', '건축유형', '역세권', '노선']] = df.groupby('단지명')[['단지명', '준공연도', '세대수', '건축유형', '역세권', '노선']].fillna(method="ffill").fillna(method="bfill")
    df['실거래가'] = pd.to_numeric(df['2025.03'], errors='coerce')
    df['현재호가'] = pd.to_numeric(df['20250521호가'], errors='coerce')
    df['추정가'] = pd.to_numeric(df['2025.05_보정_추정실거래가'], errors='coerce')
    df['거래일'] = pd.to_datetime(df['거래일'], errors='coerce')
    df['거래연도'] = df['거래일'].dt.year
    # 이미 '신축'인 경우를 보호
    df['건축유형'] = df.apply(
        lambda row: row['건축유형'] if row['건축유형'] == '신축'
        else ('신축' if pd.notna(row['준공연도']) and row['준공연도'] >= 2018 else row.get('건축유형', '기축')),
        axis=1
    )
    df[['건축유형', '역세권', '노선']] = df.groupby('단지명')[['건축유형', '역세권', '노선']].fillna(method="ffill").fillna(method="bfill")

    # 필터링: 가격 1억 이상
    df = df[df['실거래가'] >= 1.0]

    # 점수 계산
    df["점수"] = df.apply(lambda row: score_complex(row, cash, loan, area_group, condition, lines, household), axis=1)
    df["상관_점수"] = df.apply(lambda row: score_correlated_factors(row, area_group, condition, lines, household), axis=1)
    min_households, max_households = df['세대수'].min(), df['세대수'].max()
    min_year, max_year = df['준공연도'].min(), df['준공연도'].max()
    df['세대수_점수'] = (df['세대수'] - min_households) / (max_households - min_households) if max_households != min_households else 0
    df['준공연도_점수'] = (df['준공연도'] - min_year) / (max_year - min_year) if max_year != min_year else 0
    df['통합_점수'] = 0.6 * df['세대수_점수'] + 0.4 * df['준공연도_점수']
    df['역세권_우선'] = df['역세권'].map({'Y': 1, 'N': 0})
    df['노선_우선'] = df['노선'].apply(lambda x: 1 if any(line in str(x) for line in ['3', '7', '9']) else 0)

    # 동일 단지 유사 평형 호가 추정
    df[['현재호가', '가격출처', '호가전용면적']] = df.apply(lambda row: pd.Series(estimate_similar_asking_price(row, df)), axis=1)

    # 실사용가격 설정
    df['실사용가격'] = df['실거래가']
    df['가격출처_실사용'] = df['가격출처'].fillna('실거래가')
    mask_호가 = df['실사용가격'].isna() & df['현재호가'].notna()
    df.loc[mask_호가, '실사용가격'] = df['현재호가']
    df.loc[mask_호가, '가격출처_실사용'] = df['가격출처']
    mask_추정 = df['실사용가격'].isna() & df['추정가'].notna()
    df.loc[mask_추정, '실사용가격'] = df['추정가']
    df.loc[mask_추정, '가격출처_실사용'] = '추정'
    # 실사용가격이 0이거나 NaN인 경우 제외
    df = df[df['실사용가격'].notna() & (df['실사용가격'] > 0)]

    # 오래된 거래 제외
    df = df[(df['거래연도'].isna()) | (df['거래연도'] >= 2024)]
    
    # 예산 내 단지 필터링 (예산 ±10%)
    budget_lower = total_budget * 0.9
    df_filtered = df[(df['실사용가격'] <= budget_upper) & (df['실사용가격'] >= budget_lower)].copy()
    
    # 평형 조건 필터링 (평형 기준)
    if area_group != "상관없음":
        p_min, p_max = get_area_range(area_group)
        df_filtered = df_filtered[
            (df_filtered['평형'] >= p_min) & (df_filtered['평형'] <= p_max)
        ]
    
    # 세대수 조건
    if household == "대단지":
        df_filtered = df_filtered[df_filtered['세대수'] >= 1000]
    elif household == "소단지 (300세대 이상)":
        df_filtered = df_filtered[(df_filtered['세대수'] >= 300) & (df_filtered['세대수'] < 1000)]
    elif household == "소단지 (300세대 이하)":
        df_filtered = df_filtered[df_filtered['세대수'] < 300]
    
    # 신축 조건
    if condition == "신축":
        df_filtered = df_filtered[
            (df_filtered['준공연도'] >= 2018) |
            (df_filtered['건축유형'] == "신축")
        ]
    
    # 정렬
    df_filtered = df_filtered.sort_values(
        by=["점수", "상관_점수", "통합_점수", "역세권_우선", "노선_우선"],
        ascending=[False, False, False, False, False]
    )
    
    # 단지 중복 제거 및 상위 3개 추출
    df_filtered = df_filtered.drop_duplicates(subset=['단지명'], keep='first')
    top3 = df_filtered.head(3)
    
    # ✅ fallback 추천: 예산 초과 단지 중 평형 조건도 만족하는 단지 보완
    if len(top3) < 3:
        df_extended = df[
            (df['실사용가격'] > budget_upper)
        ]
    
        # 평형 필터 추가
        if area_group != "상관없음":
            df_extended = df_extended[
                (df_extended['평형'] >= p_min) & (df_extended['평형'] <= p_max)
            ]
    
        df_extended["점수"] = df_extended.apply(lambda row: score_complex(row, cash, loan, area_group, condition, lines, household), axis=1)
        df_extended["상관_점수"] = df_extended.apply(lambda row: score_correlated_factors(row, area_group, condition, lines, household), axis=1)
        
        df_extended = df_extended.sort_values(
            by=["실사용가격", "점수", "상관_점수", "통합_점수", "역세권_우선", "노선_우선"],
            ascending=[True, False, False, False, False, False]
        )
    
        df_extended = df_extended.drop_duplicates(subset=['단지명'], keep='first')
        부족한개수 = 3 - len(top3)
        if not df_extended.empty:
            top3 = pd.concat([top3, df_extended.head(부족한개수)], ignore_index=True)

    
    # fallback 추천: 예산 초과 단지 중 평형 조건도 만족하고 예산 초과 폭이 제한된 단지 보완
    if len(top3) < 3:
        df_extended = df[df['실사용가격'] > budget_upper].copy()
    
        # 예산 초과 상한 제한 (예산의 1.5배 초과는 제외)
        fallback_price_limit = total_budget * 1.5
        df_extended = df_extended[df_extended['실사용가격'] <= fallback_price_limit]
    
        # 평형 필터 추가
        if area_group != "상관없음":
            p_min, p_max = get_area_range(area_group)
            df_extended = df_extended[(df_extended['평형'] >= p_min) & (df_extended['평형'] <= p_max)]
    
        # 점수 재계산
        df_extended["점수"] = df_extended.apply(lambda row: score_complex(row, cash, loan, area_group, condition, lines, household), axis=1)
        df_extended["상관_점수"] = df_extended.apply(lambda row: score_correlated_factors(row, area_group, condition, lines, household), axis=1)
    
        df_extended = df_extended.sort_values(
            by=["실사용가격", "점수", "상관_점수", "통합_점수", "역세권_우선", "노선_우선"],
            ascending=[True, False, False, False, False, False]
        )
    
        df_extended = df_extended.drop_duplicates(subset=['단지명'], keep='first')
    
        부족한개수 = 3 - len(top3)
        if not df_extended.empty:
            top3 = pd.concat([top3, df_extended.head(부족한개수)], ignore_index=True)

    # 안내 메시지 출력
    if len(top3) == 0:
        st.markdown("""
        **안내**: 현재 잠원동 아파트의 호가가 입력하신 예산보다 높게 형성되어 추천 가능한 단지가 없습니다.  
        2025년 5월 기준, 잠원동 아파트 시장은 호가가 실거래가보다 높게 형성되어 있습니다.  
    
        - 예산을 상향 조정해 보세요.  
        - 시장이 안정화될 때까지 기다려보는 것도 방법입니다.  
        추가 조건 조정이나 상담이 필요하시면 말씀해주세요!
        """)
        st.stop()
    elif len(top3) < 3:
        st.markdown("""
        **안내**: 입력 조건에 정확히 부합하는 단지가 부족하여, 일부 조건을 완화해 추가로 추천드립니다.  
        """)


    # 조건 불일치 확인
    condition_mismatch = False
    for _, row in top3.iterrows():
        _, mismatch = get_condition_note(cash, loan, area_group, condition, lines, household, row)
        if mismatch:
            condition_mismatch = True
            break

    # 조건 불일치 메시지
    if condition_mismatch:
        st.markdown("""
        **안내**: 입력하신 조건(평형, 컨디션, 노선, 세대수)에 정확히 부합하는 단지가 없는 경우 일부 조건을 완화해 추천드립니다.
        """)

    # 추천 결과 출력 (텍스트 형식)
    st.markdown("### 추천 단지")
    for idx, row in top3.iterrows():
        단지명 = row['단지명']
        준공 = int(row['준공연도']) if pd.notna(row['준공연도']) else "미상"
        세대 = int(row['세대수']) if pd.notna(row['세대수']) else "미상"
        평형 = row['평형']
        면적 = round(row['전용면적'], 1)
        실거래 = round_price(row['실사용가격'], row['가격출처_실사용'], is_estimated=(row['가격출처_실사용'] == '동일단지 유사평형 호가 추정'))
        거래일 = row['거래일'].strftime("%Y.%m.%d") if pd.notna(row['거래일']) and row['거래연도'] >= 2024 else "최근 거래 없음"
        호가 = round_price(row['현재호가'], row['가격출처'], is_estimated=(row['가격출처'] == '동일단지 유사평형 호가 추정'))
        호가전용면적 = round(row['호가전용면적'], 1) if pd.notna(row['호가전용면적']) else 면적
        출처 = row['가격출처']
        조건설명, _ = get_condition_note(cash, loan, area_group, condition, lines, household, row)
        추천이유 = classify_recommendation(row, budget_upper, total_budget)
        추천메시지 = f"{조건설명} {추천이유}".strip()

        # 가격 출력
        실거래출력 = f"{실거래} (거래일: {거래일})"
        if 출처 == "호가":
            호가출력 = f"현재 호가: {호가} (네이버 매물 기준)"
        elif 출처 == "동일단지 유사평형 호가 추정":
            호가출력 = f"추정가: {호가} (전용면적: {호가전용면적}㎡ 기준, 이전 실거래를 기반으로 계산된 임의 추정가로 시장 상황은 다를 수 있음)"
        else:
            호가출력 = "현재 매물은 없으나, 이전 실거래에 따라 추천되었습니다. 매물이 나올 경우 이전 실거래와 현재 매물 가격은 다를 수 있습니다."

        # 텍스트 형식으로 출력
        st.markdown(f"""
#### **{단지명}**

**기본 정보**:  
- 평형: {평형}평  
- 전용면적: {면적}㎡  
- 준공연도: {준공}  
- 세대수: {세대}  

**가격 정보**:  
- 실거래 가격: {실거래출력}  
- {호가출력}  

**추천 이유**:  {추천메시지}


---
        """)

    st.markdown("""
    ※ 위 추천은 사용자의 입력 조건과 2025.05 기준가를 종합하여 제안드린 결과입니다.  
    ※ 본 추천 결과는 동생의 내집마련을 위한 정보를 제공 목적으로 이루어지는 테스트이며, 투자 권유 또는 자문이 아닙니다.  
    ※ 실제 매수 결정 시에는 본인의 판단과 책임 하에 신중히 검토해주시기 바랍니다.  
    ※ 잠원동생집사 v0.1 - 20250521
    """)
