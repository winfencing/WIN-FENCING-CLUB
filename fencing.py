import streamlit as st
import pandas as pd
import os
import re
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="윈펜싱클럽 전력 분석 V29.0", page_icon="🤺", layout="wide")

st.title("🤺 윈펜싱클럽 통합 전력 분석 대시보드 (V29.0 얼티밋 에디션)")
st.markdown("단일 파일 원샷 업로드, **(사)부산펜싱 통합**, 유저 방명록, 100종 칭호, 육각형 차트 분석 적용!")

PLAYER_DB_FILE = "fencing_player_db.csv"
MATCH_DB_FILE = "fencing_match_db.csv"
COMMENT_DB_FILE = "fencing_comment_db.csv" # 💬 댓글 저장용 DB 추가

# 🌟 데이터 초기화
with st.sidebar:
    st.warning("⚠️ 새 버전을 깔았거나 랭킹이 꼬였을 때")
    if st.button("🗑️ 데이터 완전 초기화 (필수)"):
        if os.path.exists(PLAYER_DB_FILE): os.remove(PLAYER_DB_FILE)
        if os.path.exists(MATCH_DB_FILE): os.remove(MATCH_DB_FILE)
        if os.path.exists(COMMENT_DB_FILE): os.remove(COMMENT_DB_FILE)
        for key in ['player_db', 'match_db', 'comment_db']:
            if key in st.session_state: del st.session_state[key]
        st.success("데이터 리셋 완료! 원본 엑셀을 다시 올려주세요.")
        st.rerun()

if 'player_db' not in st.session_state:
    if os.path.exists(PLAYER_DB_FILE): st.session_state.player_db = pd.read_csv(PLAYER_DB_FILE)
    else: st.session_state.player_db = pd.DataFrame()

if 'match_db' not in st.session_state:
    if os.path.exists(MATCH_DB_FILE): st.session_state.match_db = pd.read_csv(MATCH_DB_FILE)
    else: st.session_state.match_db = pd.DataFrame()

if 'comment_db' not in st.session_state:
    if os.path.exists(COMMENT_DB_FILE): st.session_state.comment_db = pd.read_csv(COMMENT_DB_FILE)
    else: st.session_state.comment_db = pd.DataFrame(columns=["대상선수", "작성자", "내용", "작성일시"])

global_db = st.session_state.player_db.copy()
global_match = st.session_state.match_db.copy()

# 💡 [요청사항 1] 소속팀 병합 처리: (사)부산펜싱클럽, 부산펜싱클럽 -> 윈펜싱클럽
if not global_db.empty:
    global_db['소속팀'] = global_db['소속팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
if not global_match.empty:
    global_match['기준팀'] = global_match['기준팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_match['상대팀'] = global_match['상대팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})

# 데이터 전처리
if not global_db.empty:
    global_db['대회일자'] = pd.to_datetime(global_db['대회일자'], errors='coerce')
    global_db['연도'] = global_db['대회일자'].dt.year.fillna(2026).astype(int).astype(str)
    global_db['본선_순위(숫자)'] = pd.to_numeric(global_db['본선_순위(숫자)'], errors='coerce')
    global_db['예선_순위(숫자)'] = pd.to_numeric(global_db['예선_순위(숫자)'], errors='coerce')
    global_db['레이팅(PT)'] = pd.to_numeric(global_db['레이팅(PT)'], errors='coerce')
    global_db['예선_승률(%)'] = pd.to_numeric(global_db['예선_승률(%)'], errors='coerce')
    
    for col in ['예선_승', '예선_패', '예선_득점', '예선_실점']:
        if col not in global_db.columns: global_db[col] = 0
        else: global_db[col] = pd.to_numeric(global_db[col], errors='coerce').fillna(0)
    
    global_db['고유이름'] = global_db['이름'] + " (" + global_db['소속팀'].fillna("소속불명") + ")"

if not global_match.empty:
    global_match['대회일자'] = pd.to_datetime(global_match['대회일자'], errors='coerce')
    global_match['연도'] = global_match['대회일자'].dt.year.fillna(2026).astype(int).astype(str)
    global_match['기준_고유'] = global_match['기준선수'] + " (" + global_match['기준팀'].fillna("소속불명") + ")"
    global_match['상대_고유'] = global_match['상대선수'] + " (" + global_match['상대팀'].fillna("소속불명") + ")"

# 🔍 글로벌 검색 필터
with st.sidebar:
    st.header("🔍 통합 검색 필터")
    if not global_db.empty:
        years = ["전체"] + sorted(list(global_db['연도'].unique()), reverse=True)
        sel_year = st.selectbox("📅 연도", years)
        if sel_year != "전체":
            global_db = global_db[global_db['연도'] == sel_year]
            global_match = global_match[global_match['연도'] == sel_year]
            
        divs = ["전체"] + sorted(list(global_db['부수'].dropna().unique()))
        sel_div = st.selectbox("🏅 부수(학년)", divs)
        if sel_div != "전체":
            global_db = global_db[global_db['부수'] == sel_div]
            global_match = global_match[global_match['부수'] == sel_div]

# 탭 구성
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏆 종합 랭킹 보드", "🏢 클럽 스탯 & 명전", 
    "🎮 개인 분석 & 방명록", "💠 6대 스탯 & 폼 분석", "⚔️ 1:1 라이벌 비교", "🔮 다음 대회 시뮬레이터", "📂 성적 업로드 (관리자)"
])

# ================= TAB 1: 종합 랭킹 =================
with tab1:
    st.subheader("🏆 종합 랭킹 보드")
    if not global_db.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### 🏢 전국 클럽 파워 스탯 랭킹 (팀 대항전)")
            cs = global_db.groupby('소속팀').agg(
                총원=('고유이름', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 평균PT=('레이팅(PT)', 'mean'),
                금메달=('본선_순위(숫자)', lambda x: (x.dropna() == 1).sum()), 은메달=('본선_순위(숫자)', lambda x: (x.dropna() == 2).sum()), 동메달=('본선_순위(숫자)', lambda x: x.dropna().isin([3, 4]).sum())
            ).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            cs.index += 1
            st.dataframe(cs, column_config={"합산PT": st.column_config.NumberColumn("합산 레이팅", format="%.0f pt"), "평균PT": st.column_config.NumberColumn("클럽 평균전력", format="%.1f pt")}, use_container_width=True)

        with c2:
            st.markdown("#### 🤺 선수 종합 스탯 랭킹 (전국 통합)")
            ps = global_db.sort_values('대회일자').groupby('고유이름').agg(
                소속팀=('소속팀', 'last'), 출전=('대회명', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 평균PT=('레이팅(PT)', 'mean'),
                승률=('예선_승률(%)', 'mean'), 평균예선=('예선_순위(숫자)', 'mean'), 평균본선=('본선_순위(숫자)', 'mean')
            ).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            ps.index += 1
            st.dataframe(ps, column_config={"합산PT": st.column_config.NumberColumn("합산 레이팅", format="%.0f pt"), "평균PT": st.column_config.NumberColumn("평균 레이팅", format="%.1f pt"), "승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%")}, use_container_width=True)

# ================= TAB 2: 클럽 정밀 분석 =================
with tab2:
    st.subheader("🏢 클럽 정밀 분석 & 명예의 전당 Top 10")
    if not global_db.empty:
        my_team = st.selectbox("분석할 클럽(소속팀)을 선택하세요.", ["선택"] + sorted(list(global_db['소속팀'].dropna().unique())))
        if my_team != "선택":
            h_db = global_db[global_db['소속팀'] == my_team]
            h_match = global_match[global_match['기준팀'] == my_team]
            
            st.markdown(f"### 🛡️ {my_team} 전력 분석실")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 등록 선수", f"{h_db['고유이름'].nunique()}명")
            c2.metric("클럽 총 누적 레이팅", f"{h_db['레이팅(PT)'].sum():.0f} PT")
            c3.metric("클럽 평균 승률", f"{h_db['예선_승률(%)'].mean():.1f}%")
            c4.metric("클럽 총 자이언트 킬링", f"{len(h_match[(h_match['단계'] == '본선') & (h_match['승패'] == '승') & (h_match['업셋여부'] == 'Y')])}회")
            
            st.markdown("---")
            st.markdown(f"### 🏅 {my_team} 명예의 전당 (Top 10)")
            s1, s2, s3, s4 = st.columns(4)
            
            golds = h_db[h_db['본선_순위(숫자)'] == 1].groupby('고유이름').size().reset_index(name='금메달').sort_values('금메달', ascending=False).head(10)
            s1.success("👑 **[우승 제조기]**\n\n클럽 내 1위 입상 Top 10")
            for i, row in golds.iterrows(): s1.write(f"- {row['고유이름'].split(' (')[0]} (금 {row['금메달']}개)")
            
            medals = h_db[h_db['본선_순위(숫자)'] <= 4].groupby('고유이름').size().reset_index(name='메달').sort_values('메달', ascending=False).head(10)
            s2.warning("🎖️ **[메달 콜렉터]**\n\n포디움(1~3위) 입상 Top 10")
            for i, row in medals.iterrows(): s2.write(f"- {row['고유이름'].split(' (')[0]} (총 {row['메달']}회)")

            wk = h_db.groupby('고유이름').agg(승률=('예선_승률(%)','mean'), 출전=('대회명','nunique')).reset_index()
            wk = wk[wk['출전'] >= 1].sort_values('승률', ascending=False).head(10)
            s3.info("🔥 **[최고 승률왕]**\n\n예선 평균 승률 Top 10")
            for i, row in wk.iterrows(): s3.write(f"- {row['고유이름'].split(' (')[0]} ({row['승률']:.1f}%)")
            
            up_king = h_match[(h_match['단계'] == '본선') & (h_match['승패'] == '승') & (h_match['업셋여부'] == 'Y')].groupby('기준_고유').size().reset_index(name='업셋').sort_values('업셋', ascending=False).head(10)
            s4.error("⚡ **[자이언트 킬러]**\n\n본선 업셋 승리 Top 10")
            for i, row in up_king.iterrows(): s4.write(f"- {row['기준_고유'].split(' (')[0]} ({row['업셋']}회)")

            st.divider()
            st.markdown(f"### 📋 {my_team} 소속 선수 전체 로스터")
            roster = h_db.groupby('고유이름').agg(
                출전대회=('대회명', 'nunique'), 누적레이팅=('레이팅(PT)', 'sum'), 평균레이팅=('레이팅(PT)', 'mean'), 평균승률=('예선_승률(%)', 'mean'), 본선최고순위=('본선_순위(숫자)', 'min')
            ).reset_index().sort_values('누적레이팅', ascending=False).reset_index(drop=True)
            roster.index += 1
            st.dataframe(roster, use_container_width=True)


# ================= TAB 3: 선수 개인 스탯 & 칭호 & 방명록 =================
with tab3:
    st.subheader("🎮 선수 개인 정밀 분석 & 100+ 칭호 방명록")
    if not global_db.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            divs = ["전체"] + sorted(list(global_db['부수'].dropna().unique()))
            sel_div_t3 = st.selectbox("1. 대분류 (부수)", divs, key="d3")
        with col2:
            db_t3 = global_db if sel_div_t3 == "전체" else global_db[global_db['부수'] == sel_div_t3]
            teams = ["전체"] + sorted(list(db_t3['소속팀'].dropna().unique()))
            sel_team_t3 = st.selectbox("2. 중분류 (소속팀)", teams, key="t3")
        with col3:
            if sel_team_t3 != "전체": db_t3 = db_t3[db_t3['소속팀'] == sel_team_t3]
            players = sorted(list(db_t3['고유이름'].dropna().unique()))
            sel_player = st.selectbox("3. 선수 이름 검색", ["선수를 선택하십시오."] + players)
        
        if sel_player != "선수를 선택하십시오.":
            p_data = global_db[global_db['고유이름'] == sel_player].sort_values('대회일자')
            m_data = global_match[global_match['기준_고유'] == sel_player]
            
            # --- 💡 [요청 4] 시각적 티어 시스템 (Progress Bar) ---
            all_pts = global_db.groupby('고유이름')['레이팅(PT)'].mean()
            my_pt = all_pts.get(sel_player, 0)
            
            pct = (all_pts > my_pt).mean() * 100 if len(all_pts) > 1 else 50.0
            
            t_name, t_color, t_desc = "", "", ""
            if pct <= 1: t_name, t_color, t_desc = "👑 레디언트 (상위 1%)", "#ff3333", "신들의 영역. 전국구 펜싱 생태계의 절대적인 지배자입니다."
            elif pct <= 5: t_name, t_color, t_desc = "💎 챌린저 (상위 5%)", "#e0b0ff", "어딜가나 에이스 대접을 받는 압도적 무력의 소유자."
            elif pct <= 15: t_name, t_color, t_desc = "🥇 마스터 (상위 15%)", "#ffd700", "대회 본선 상위권의 단골 손님. 강력한 실력자입니다."
            elif pct <= 30: t_name, t_color, t_desc = "🥈 다이아몬드 (상위 30%)", "#b9f2ff", "탄탄한 기본기를 바탕으로 누구도 쉽게 볼 수 없는 강자."
            elif pct <= 50: t_name, t_color, t_desc = "🥉 플래티넘 (상위 50%)", "#54c3a6", "클럽 내 허리를 든든하게 받쳐주는 실력파 검객."
            elif pct <= 75: t_name, t_color, t_desc = "🟡 골드 (상위 75%)", "#f2a900", "꾸준히 대회에 참여하며 폭풍 성장중인 유망주."
            else: t_name, t_color, t_desc = "⚪ 실버/아이언", "#a0a0a0", "이제 막 펜싱의 진짜 재미를 알아가는 잠재력 100%의 루키."

            st.markdown(f"### 🎖️ {sel_player.split(' (')[0]} 선수의 종합 분석 리포트")
            
            st.markdown(f"""
            <div style="background-color:#1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 8px solid {t_color};">
                <h2 style="margin-top:0px; color: {t_color};">{t_name}</h2>
                <p style="font-size: 15px; color:#ddd; margin-bottom: 10px;">{t_desc}</p>
                <div style="width: 100%; background-color: #333; border-radius: 10px; height: 12px; margin-top: 10px;">
                    <div style="width: {100-pct}%; background-color: {t_color}; height: 100%; border-radius: 10px;"></div>
                </div>
                <div style="text-align:right; font-size:12px; color:#888; margin-top:5px;">현재 생태계 상위 {pct:.1f}% 위치</div>
            </div>
            """, unsafe_allow_html=True)

            luck_l = []
            for tn in p_data['대회명']:
                opps = m_data[(m_data['단계']=='예선') & (m_data['대회명']==tn)]['상대_고유']
                if len(opps) > 0: luck_l.append(opps.map(all_pts).fillna(5).mean())
                else: luck_l.append(5.0)
            avg_luck = sum(luck_l)/len(luck_l) if luck_l else 5.0

            # --- 💡 [요청 3] 100+종 방대한 칭호(업적) 시스템 ---
            titles = []
            tot_m = p_data['예선_승'].sum() + p_data['예선_패'].sum()
            avg_wr = p_data['예선_승률(%)'].mean()
            tot_pt = p_data['레이팅(PT)'].sum()
            num_tourneys = len(p_data)
            golds = len(p_data[p_data['본선_순위(숫자)'] == 1])
            silvers = len(p_data[p_data['본선_순위(숫자)'] == 2])
            bronzes = len(p_data[p_data['본선_순위(숫자)'].isin([3, 4])])
            medals = golds + silvers + bronzes
            up_cnt = len(m_data[(m_data['단계'] == '본선') & (m_data['승패'] == '승') & (m_data['업셋여부'] == 'Y')])
            sweats = len(m_data[(m_data['단계'] == '예선') & (m_data['진땀승'] == 'Y')])
            avg_sc = (p_data['예선_득점'].sum() / tot_m) if tot_m > 0 else 0
            avg_ls = (p_data['예선_실점'].sum() / tot_m) if tot_m > 0 else 0
            p_loss = p_data['예선_패'].sum()
            p_win = p_data['예선_승'].sum()
            best_r = p_data['본선_순위(숫자)'].min()

            # [우승 / 메달]
            if golds >= 10: titles.append(("👑 언킬러블 데몬 킹 (Faker)", "대회 우승 10회! 신의 경지에 오른 펜싱계의 GOAT."))
            elif golds >= 7: titles.append(("🪐 우주적 존재", "우승 7회! 이미 인간의 궤도를 벗어난 펜서."))
            elif golds >= 5: titles.append(("👑 불사대마왕", "우승 5회! 생태계 최상위 포식자이자 공포의 대상."))
            elif golds >= 4: titles.append(("🏆 쿼드라킬", "우승 4회! 왕조를 굳건히 지키는 군주."))
            elif golds >= 3: titles.append(("🔥 펜싱 3대장", "우승 3회! 범접할 수 없는 압도적인 무력."))
            elif golds == 2: titles.append(("🥇 더블 킬", "우승 2회! 우승이 운이 아님을 실력으로 증명."))
            elif golds == 1: titles.append(("🎖️ 챔피언 (퍼스트 블러드)", "짜릿한 첫 우승의 맛을 본 진정한 실력자."))
            if golds == 0 and silvers >= 4: titles.append(("😭 영원한 고통의 콩진호", "결승에서만 4번 패배... 세상은 2등도 기억합니다!"))
            elif golds == 0 and silvers >= 3: titles.append(("🥈 비운의 황태자", "결승 문턱에서 3번이나 좌절... 다음엔 무조건 우승!"))
            elif golds == 0 and silvers >= 2: titles.append(("🥈 콩라인 탑승자", "은메달만 2개 이상. 아쉬운 2인자!"))
            if golds == 0 and silvers == 0 and bronzes >= 4: titles.append(("🥉 브론즈 마스터", "동메달 4개! 시상대 한구석의 완벽한 지배자."))
            elif golds == 0 and silvers == 0 and bronzes >= 3: titles.append(("🍲 든든한 국밥 요정", "우승은 못해도 4강(사스널)은 무조건 가는 뜨끈한 픽."))
            if medals >= 15: titles.append(("🏛️ 올림푸스의 신", "입상 15회! 시상대 위가 본인 안방입니다."))
            elif medals >= 10: titles.append(("🏛️ 포디움의 지배자", "입상 10회! 메달 수집하는 취미가 있습니다."))
            elif medals >= 5: titles.append(("🥇 메달 콜렉터", "입상 5회! 집에 메달 걸어둘 곳이 부족합니다."))

            # [레이팅 체급]
            if tot_pt >= 1500: titles.append(("🐉 엘더 드래곤", "누적 1500PT. 마주치면 도망치는 것이 상책."))
            elif tot_pt >= 1000: titles.append(("🪐 측정 불가", "누적 1000PT 돌파! 스카우터가 터졌습니다."))
            elif tot_pt >= 700: titles.append(("👑 초월자", "누적 700PT. 범접할 수 없는 그랜드마스터."))
            elif tot_pt >= 500: titles.append(("🌟 최고 존엄", "누적 500PT. 최상위권 랭커의 위엄."))
            elif tot_pt >= 300: titles.append(("⚔️ 소드 마스터", "누적 300PT. 어디가서 펜싱 마스터라고 부를 수 있음."))
            elif tot_pt >= 150: titles.append(("🛡️ 정예 기사", "누적 150PT. 안정적인 궤도에 오른 강자."))
            if golds == 0 and tot_pt >= 300: titles.append(("🥀 무관의 제왕", "우승컵만 없을 뿐, 누적 스탯은 챔피언급."))

            # [승률/폼]
            if avg_wr == 100 and num_tourneys >= 3: titles.append(("✨ 무결점의 신 (퍼펙트 게임)", "출전한 모든 대회 예선 전승! 흠잡을 곳 없는 완벽함."))
            elif avg_wr == 100 and num_tourneys >= 1: titles.append(("✨ 엑조디아", "예선 전승! 완전체가 되어 나타났습니다."))
            elif avg_wr >= 90 and num_tourneys >= 3: titles.append(("👿 타노스", "예선 승률 90% 이상! 참가자의 절반을 가루로 만듭니다."))
            elif avg_wr >= 80 and num_tourneys >= 2: titles.append(("🦅 사신 (Grim Reaper)", "예선 승률 80% 이상. 한 대 맞추기도 버거운 포스."))
            elif avg_wr >= 70 and num_tourneys >= 2: titles.append(("🔥 1티어 픽", "예선 승률 70% 이상. 대회에서 가장 만나기 싫은 상대."))
            elif 48 <= avg_wr <= 52 and tot_m >= 15: titles.append(("⚖️ 인간 저울 (황금밸런스)", "만인을 평등하게 만드는 기적의 반반 승률."))
            elif 45 <= avg_wr <= 55 and tot_m >= 10: titles.append(("⚖️ 펜싱 수문장", "나를 이기면 강자, 지면 약자. 전투력 판독기."))
            elif avg_wr <= 20 and num_tourneys >= 4: titles.append(("🌱 심해의 잠수함", "아직은 심해에 있지만 언젠가 수면 위로 떡상할 유망주!"))

            # [플레이스타일 (득실점)]
            if avg_sc >= 4.9 and tot_m >= 5: titles.append(("🚀 핵탄두 (ICBM)", f"평균 {avg_sc:.1f}득점! 방어막을 찢어발기는 극단적 닥공."))
            elif avg_sc >= 4.6 and tot_m >= 5: titles.append(("🚀 둠피스트", f"평균 {avg_sc:.1f}득점! 스치기만 해도 치명타."))
            elif avg_sc >= 4.3 and avg_ls >= 4.0 and tot_m >= 5: titles.append(("💣 탑신병자 (유리대포)", "방어? 그게 뭐죠? 맞기 전에 찌르는 낭만파!"))
            elif avg_sc >= 4.2 and tot_m >= 5: titles.append(("🗡️ 전장의 여포", f"매 경기 {avg_sc:.1f}점을 꽂아넣는 폭격기."))
            if avg_sc == 5.0 and tot_m >= 3: titles.append(("⚡ 원펀맨", "출전한 모든 경기에서 5점을 꽉 채운 미친 공격력!"))
            
            if 0 < avg_ls <= 1.0 and tot_m >= 5: titles.append(("❄️ 절대영도 (A.T.필드)", f"평균 {avg_ls:.1f}실점! 뚫는 것이 물리적으로 불가능."))
            elif 0 < avg_ls <= 1.5 and tot_m >= 5: titles.append(("🧱 비브라늄 방패", f"평균 {avg_ls:.1f}실점! 캡틴 아메리카도 울고 갈 우주 방어."))
            elif 0 < avg_ls <= 2.2 and tot_m >= 5: titles.append(("🛡️ 이지스함", "빈틈이 보이지 않는 견고한 방어 라인."))
            elif 0 < avg_sc <= 2.5 and 0 < avg_ls <= 2.5 and tot_m >= 5: titles.append(("🐢 늪지대 장인 (가시갑옷)", "점수도 안내고 내주지도 않는다... 극한의 짠물 펜싱."))
            elif avg_ls >= 4.5 and tot_m >= 5: titles.append(("💸 자선사업가 (자동문)", "수비가 너무 후한 나머지 점수를 마구 베풉니다."))

            # [클러치 / 멘탈]
            if up_cnt >= 8: titles.append(("🏴‍☠️ 혁명군 수장 (드래곤)", "업셋 8회 이상! 시드 체계를 완벽히 붕괴시키는 파괴자."))
            elif up_cnt >= 4: titles.append(("🪓 자이언트 킬러", f"본선에서 상위 시드를 {up_cnt}번이나 썰어버림."))
            if avg_wr <= 35 and up_cnt >= 2: titles.append(("🥷 암살자 (다크템플러)", "예선에서는 죽어있다가 본선에서 1시드의 목을 벰."))
            if sweats >= 10: titles.append(("🥶 얼음 심장 (타짜)", f"1점 차 진땀승만 {sweats}번. 심박수가 변하지 않는 멘탈 갑."))
            elif sweats >= 4: titles.append(("💦 클러치 장인", "4-4 데스매치 접전에서 절대 지지 않는 승부사."))

            # [출전 빈도 / 짬바]
            if tot_m >= 150: titles.append(("🦾 사이버네틱 펜서", "예선 150경기 소화! 펜싱 기계 그 자체."))
            elif tot_m >= 60: titles.append(("💪 강철체력 (무한동력)", f"공식전 {tot_m}경기. 지치지 않는 에너자이저."))
            if num_tourneys >= 15: titles.append(("🏛️ 살아있는 화석 (고인물)", f"{num_tourneys}번 대회 개근! 클럽 역사의 산증인."))
            elif num_tourneys >= 7: titles.append(("🏃 철인 (개근상)", f"{num_tourneys}번 출전! 주말을 반납한 펜싱 광인."))

            # [대진운 / 기타 밈]
            if avg_luck >= 42 and num_tourneys >= 2: titles.append(("☠️ 억까의 신", f"평균 대진운 {avg_luck:.1f}pt. 왜 나한테만 우승후보가 걸리는가?"))
            elif avg_luck >= 35 and pd.notna(best_r) and best_r <= 8: titles.append(("💎 낭중지추", "매번 지옥의 조에 끌려가지만 꾸역꾸역 8강을 뚫어냄."))
            elif avg_luck <= 15 and num_tourneys >= 2: titles.append(("🍯 양봉업자 (럭키가이)", f"평균 대진운 {avg_luck:.1f}pt. 꿀대진 냄새를 기가 막히게 맡습니다."))
            if p_loss >= 40: titles.append(("🔥 칠전팔기 불사조 (중꺾마)", "40번을 져도 절대 검을 놓지 않는 불굴의 의지. 리스펙트!"))
            elif p_loss >= 20: titles.append(("🌱 소년만화 주인공", "수많은 패배를 거름 삼아 묵묵히 성장 중입니다."))
            if p_win == 0 and num_tourneys >= 3: titles.append(("😭 영고라인 (영원히 고통받는)", "아직 공식전 첫 승의 기쁨을 누리지 못했습니다... 파이팅!"))
            if num_tourneys == 1: titles.append(("🐣 삐약이 (뉴비)", "이제 막 첫발을 내디딘 루키! 앞날을 응원합니다."))

            if len(titles) == 0: titles.append(("👤 묵묵한 검사", "자신만의 길을 걷고 있는 성실한 펜서."))

            st.markdown("#### 🏆 획득한 특수 칭호 보드 (업적)")
            t_col1, t_col2 = st.columns(2)
            for i, (t, desc) in enumerate(titles):
                col = t_col1 if i % 2 == 0 else t_col2
                col.markdown(f"<div style='padding:12px; background-color:#2a2a2a; border-radius:8px; margin-bottom:8px; border-left:4px solid {t_color};'><b>{t}</b><br><span style='color:#aaaaaa; font-size:13px;'>{desc}</span></div>", unsafe_allow_html=True)
            
            st.markdown("#### 📊 스탯 보드")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("총 출전 대회", f"{len(p_data)}회")
            s2.metric("누적 레이팅", f"{tot_pt:.0f} PT")
            s3.metric("평균 승률", f"{avg_wr:.1f}%")
            best_r = p_data['본선_순위(숫자)'].min()
            s4.metric("커리어 하이", f"{best_r:.0f}위" if pd.notna(best_r) else "-")

            def g_luck(pt):
                if pt >= 40: return f"💀 지옥 뿔 ({pt:.1f}pt)"
                if pt >= 25: return f"⚔️ 험난 뿔 ({pt:.1f}pt)"
                if pt >= 15: return f"😐 평이 ({pt:.1f}pt)"
                return f"🍯 꿀통 뿔 ({pt:.1f}pt)"
            p_data['대진운'] = [g_luck(x) for x in luck_l]
            
            st.markdown("#### 📜 대회별 상세 기록 & 대진운 분석")
            st.dataframe(p_data[['대회명', '부수', '소속팀', '예선_승률(%)', '예선_랭킹', '본선_랭킹', '레이팅(PT)', '대진운']], use_container_width=True, hide_index=True)
            
            # --- 💡 [요청 2] 💬 선수 팬명록(방명록) 시스템 ---
            st.divider()
            st.markdown(f"### 💬 {sel_player.split(' (')[0]} 선수 팬명록 (방명록)")
            st.markdown("선수에게 응원의 메시지나 재미있는 코멘트를 남겨주세요!")
            
            # 기존 댓글 출력
            if 'comment_db' in st.session_state and not st.session_state.comment_db.empty:
                player_comments = st.session_state.comment_db[st.session_state.comment_db['대상선수'] == sel_player]
                if not player_comments.empty:
                    for _, row in player_comments.sort_values(by='작성일시', ascending=False).iterrows():
                        st.markdown(f"""
                        <div style='background-color:#1e1e1e; padding:12px; border-left:4px solid {t_color}; border-radius:5px; margin-bottom:8px;'>
                            <span style='color:#fff; font-weight:bold;'>{row['작성자']}</span> <span style='color:#888; font-size:12px;'>({row['작성일시']})</span><br>
                            <span style='color:#ddd; font-size:15px;'>{row['내용']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("아직 등록된 코멘트가 없습니다. 첫 번째 응원을 남겨주세요! 🎉")
            
            # 새 댓글 폼
            with st.form("comment_form", clear_on_submit=True):
                c_c1, c_c2 = st.columns([1, 4])
                with c_c1: author = st.text_input("닉네임 (익명 가능)", placeholder="예: 무명검객")
                with c_c2: comment_text = st.text_input("응원 또는 코멘트 남기기", placeholder="이번 대회 폼 미쳤다!! 찢었다!!")
                
                submit_btn = st.form_submit_button("📝 코멘트 등록")
                if submit_btn:
                    if comment_text.strip():
                        w_name = author.strip() if author.strip() else "익명"
                        new_comment = pd.DataFrame([{"대상선수": sel_player, "작성자": w_name, "내용": comment_text, "작성일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        if 'comment_db' not in st.session_state or st.session_state.comment_db.empty:
                            st.session_state.comment_db = new_comment
                        else:
                            st.session_state.comment_db = pd.concat([st.session_state.comment_db, new_comment], ignore_index=True)
                        st.session_state.comment_db.to_csv(COMMENT_DB_FILE, index=False, encoding='utf-8-sig')
                        st.success("코멘트가 성공적으로 등록되었습니다!")
                        st.rerun()
                    else:
                        st.error("코멘트 내용을 입력해주세요.")


# ================= TAB 4: 육각형 스탯 & 폼 분석 (New) =================
with tab4:
    st.subheader("💠 육각형(Hexagon) 스탯 레이더 & 폼 트렌드")
    st.markdown("선수의 6대 핵심 스탯(공격, 방어, 승률, 경험, 클러치, 대진운)을 0~100 스케일로 시각화합니다.")
    
    if not global_db.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            sel_div_t4 = st.selectbox("1. 대분류 (부수)", ["전체"] + sorted(list(global_db['부수'].dropna().unique())), key="d4")
        with col2:
            db_t4 = global_db if sel_div_t4 == "전체" else global_db[global_db['부수'] == sel_div_t4]
            sel_team_t4 = st.selectbox("2. 중분류 (소속팀)", ["전체"] + sorted(list(db_t4['소속팀'].dropna().unique())), key="t4")
        with col3:
            if sel_team_t4 != "전체": db_t4 = db_t4[db_t4['소속팀'] == sel_team_t4]
            players_t4 = sorted(list(db_t4['고유이름'].dropna().unique()))
            sel_hex_player = st.selectbox("3. 선수 선택 (육각형 차트)", ["선택"] + players_t4, key="hex_player")

        if sel_hex_player != "선택":
            p_data_hex = global_db[global_db['고유이름'] == sel_hex_player]
            m_data_hex = global_match[global_match['기준_고유'] == sel_hex_player]
            tot_m_hex = p_data_hex['예선_승'].sum() + p_data_hex['예선_패'].sum()
            
            # 스탯 1: 공격력
            avg_sc = (p_data_hex['예선_득점'].sum() / tot_m_hex) if tot_m_hex > 0 else 0
            stat_atk = min((avg_sc / 5.0) * 100, 100)
            
            # 스탯 2: 방어력 (역산)
            avg_ls = (p_data_hex['예선_실점'].sum() / tot_m_hex) if tot_m_hex > 0 else 5.0
            stat_def = max(100 - ((avg_ls / 5.0) * 100), 0)
            
            # 스탯 3: 결정력(승률)
            stat_win = p_data_hex['예선_승률(%)'].mean() if len(p_data_hex) > 0 else 0
            
            # 스탯 4: 경험치 (최대 50경기 100점)
            stat_exp = min((tot_m_hex / 50.0) * 100, 100)
            
            # 스탯 5: 클러치 (위기관리)
            up_cnt_hex = len(m_data_hex[(m_data_hex['단계'] == '본선') & (m_data_hex['승패'] == '승') & (m_data_hex['업셋여부'] == 'Y')])
            sweats_hex = len(m_data_hex[(m_data_hex['단계'] == '예선') & (m_data_hex['진땀승'] == 'Y')])
            stat_clutch = min(((up_cnt_hex * 2 + sweats_hex) / max(len(p_data_hex), 1)) * 20, 100)
            
            # 스탯 6: 대진운 (역경 증명)
            all_pts_hex = global_db.groupby('고유이름')['레이팅(PT)'].mean()
            luck_list = []
            for tn in p_data_hex['대회명']:
                opps = m_data_hex[(m_data_hex['단계']=='예선') & (m_data_hex['대회명']==tn)]['상대_고유']
                if len(opps) > 0: luck_list.append(opps.map(all_pts_hex).fillna(5).mean())
            avg_luck = sum(luck_list)/len(luck_list) if luck_list else 15.0
            stat_luck = min((avg_luck / 40.0) * 100, 100)

            categories = ['공격력', '방어력', '결정력(승률)', '경험치', '클러치', '대진증명력']
            values = [stat_atk, stat_def, stat_win, stat_exp, stat_clutch, stat_luck]
            
            # Plotly 육각형 방사형 차트 생성
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                fillcolor='rgba(0, 191, 255, 0.5)',
                line=dict(color='#00bfff', width=2),
                name=sel_hex_player.split(' (')[0]
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor='#555'),
                    bgcolor='rgba(0,0,0,0)'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white', size=14),
                margin=dict(l=40, r=40, t=20, b=20)
            )
            
            c_chart, c_desc = st.columns([3, 2])
            with c_chart:
                st.plotly_chart(fig, use_container_width=True)
            with c_desc:
                st.markdown(f"### 📌 {sel_hex_player.split(' (')[0]} 스카우팅 리포트")
                st.info(f"**⚔️ 공격력 ({stat_atk:.0f}/100)**: 경기당 평균 {avg_sc:.1f} 득점")
                st.info(f"**🛡️ 방어력 ({stat_def:.0f}/100)**: 경기당 평균 {avg_ls:.1f} 실점")
                st.info(f"**👑 결정력 ({stat_win:.0f}/100)**: 예선 승률 {stat_win:.1f}%")
                st.info(f"**💪 경험치 ({stat_exp:.0f}/100)**: 공식 예선 {tot_m_hex}전")
                st.info(f"**💦 클러치 ({stat_clutch:.0f}/100)**: 접전승/업셋 지수")
                st.info(f"**🍀 대진운 ({stat_luck:.0f}/100)**: 헬대진 억까 극복 지수")

            st.divider()
            st.markdown("#### 📈 대회별 폼(Form) 트렌드 (승률 변화)")
            
            # 대회명 중복 시 에러를 방지하기 위해 대회명+일자로 고유 인덱스 생성
            trend_df = p_data_hex[['대회일자', '대회명', '예선_승률(%)']].sort_values('대회일자').dropna(subset=['대회일자'])
            if len(trend_df) >= 2:
                trend_df['대회정보'] = trend_df['대회명'] + " (" + trend_df['대회일자'].dt.strftime('%y.%m.%d') + ")"
                st.line_chart(trend_df.set_index('대회정보')['예선_승률(%)'], use_container_width=True)
            else:
                st.warning("대회 트렌드 그래프를 생성하려면 최소 2번 이상의 대회 출전 기록이 필요합니다.")


# ================= TAB 5: 1:1 라이벌 비교 & AI 승률 예측 =================
with tab5:
    st.subheader("⚔️ 1:1 라이벌 전적 정밀 비교 & AI 가상 승부 예측")
    st.markdown("선수 2명을 선택하여 맞대결 기록을 비교합니다. **맞대결 기록이 없다면 AI가 두 선수의 누적 스탯을 정밀 분석하여 가상 승률 예측과 해설을 제공합니다!** 🤖")
    if not global_db.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔴 선수 A 선택")
            divs_a = ["전체"] + sorted(list(global_db['부수'].dropna().unique()))
            sel_div_a = st.selectbox("1. A선수 부수 선택", divs_a, key="div_a")
            db_a = global_db if sel_div_a == "전체" else global_db[global_db['부수'] == sel_div_a]
            teams_a = ["전체"] + sorted(list(db_a['소속팀'].dropna().unique()))
            sel_team_a = st.selectbox("2. A선수 클럽 선택", teams_a, key="team_a")
            if sel_team_a != "전체": db_a = db_a[db_a['소속팀'] == sel_team_a]
            players_a = sorted(list(db_a['고유이름'].dropna().unique()))
            pA = st.selectbox("3. 🔴 최종 A 선수", ["선택"] + players_a, key="pa")

        with c2:
            st.markdown("#### 🔵 선수 B 선택")
            divs_b = ["전체"] + sorted(list(global_db['부수'].dropna().unique()))
            sel_div_b = st.selectbox("1. B선수 부수 선택", divs_b, key="div_b")
            db_b = global_db if sel_div_b == "전체" else global_db[global_db['부수'] == sel_div_b]
            teams_b = ["전체"] + sorted(list(db_b['소속팀'].dropna().unique()))
            sel_team_b = st.selectbox("2. B선수 클럽 선택", teams_b, key="team_b")
            if sel_team_b != "전체": db_b = db_b[db_b['소속팀'] == sel_team_b]
            players_b = sorted(list(db_b['고유이름'].dropna().unique()))
            pB = st.selectbox("3. 🔵 최종 B 선수", ["선택"] + players_b, key="pb")
        
        st.divider()

        if pA != "선택" and pB != "선택":
            if pA == pB:
                st.warning("같은 선수를 선택했습니다. 다른 선수를 골라주세요!")
            else:
                h2h = global_match[(global_match['기준_고유'] == pA) & (global_match['상대_고유'] == pB)]
                st.markdown(f"<h3 style='text-align: center;'>🥊 {pA.split(' (')[0]} vs {pB.split(' (')[0]} 맞대결 스코어</h3>", unsafe_allow_html=True)
                
                if h2h.empty: 
                    st.info("💡 두 선수의 공식 맞대결 기록이 없습니다. AI가 누적 스탯을 기반으로 가상 시뮬레이션을 진행합니다! 🤖")
                    
                    a_data, b_data = global_db[global_db['고유이름'] == pA], global_db[global_db['고유이름'] == pB]
                    a_match, b_match = global_match[global_match['기준_고유'] == pA], global_match[global_match['기준_고유'] == pB]
                    
                    a_pt, a_wr = a_data['레이팅(PT)'].sum(), a_data['예선_승률(%)'].mean()
                    a_exp = a_data['예선_승'].sum() + a_data['예선_패'].sum()
                    a_clutch = len(a_match[(a_match['단계']=='예선') & (a_match['진땀승']=='Y')])
                    a_up = len(a_match[(a_match['단계']=='본선') & (a_match['승패']=='승') & (a_match['업셋여부']=='Y')])
                    
                    b_pt, b_wr = b_data['레이팅(PT)'].sum(), b_data['예선_승률(%)'].mean()
                    b_exp = b_data['예선_승'].sum() + b_data['예선_패'].sum()
                    b_clutch = len(b_match[(b_match['단계']=='예선') & (b_match['진땀승']=='Y')])
                    b_up = len(b_match[(b_match['단계']=='본선') & (b_match['승패']=='승') & (b_match['업셋여부']=='Y')])

                    score_a = (a_pt * 0.5) + (a_wr * 2.0) + (min(a_exp, 50) * 1.5) + (a_clutch * 5.0) + (a_up * 10.0)
                    score_b = (b_pt * 0.5) + (b_wr * 2.0) + (min(b_exp, 50) * 1.5) + (b_clutch * 5.0) + (b_up * 10.0)

                    if score_a + score_b == 0: prob_a, prob_b = 50.0, 50.0
                    else: prob_a = (score_a / (score_a + score_b)) * 100; prob_b = 100 - prob_a

                    st.markdown(f"<h3 style='text-align: center;'>🤖 AI 승률 예측: 🔴 {pA.split(' (')[0]} {prob_a:.1f}% vs 🔵 {pB.split(' (')[0]} {prob_b:.1f}%</h3>", unsafe_allow_html=True)
                    st.progress(prob_a / 100)

                    col1, col2 = st.columns(2)
                    col1.error(f"**🔴 {pA.split(' (')[0]} 주요 스탯**\n- 누적 체급(PT): {a_pt:.0f}\n- 예선 돌파력(승률): {a_wr:.1f}%\n- 실전 짬바(경험치): {int(a_exp)}전\n- 위기관리(클러치/업셋): {int(a_clutch + a_up)}회")
                    col2.info(f"**🔵 {pB.split(' (')[0]} 주요 스탯**\n- 누적 체급(PT): {b_pt:.0f}\n- 예선 돌파력(승률): {b_wr:.1f}%\n- 실전 짬바(경험치): {int(b_exp)}전\n- 위기관리(클러치/업셋): {int(b_clutch + b_up)}회")
                    
                    comments = []
                    if abs(prob_a - prob_b) <= 10: comments.append("🔥 **종합 분석:** 양 선수의 스탯 지표가 팽팽합니다. 경기 당일의 컨디션과 초반 선취점이 승패를 가를 초박빙 매치입니다!")
                    elif prob_a > prob_b: comments.append(f"🔥 **종합 분석:** 객관적인 스탯에서 🔴 **{pA.split(' (')[0]}** 선수가 우세합니다. 안정적인 경기 운영을 펼친다면 무난한 승리가 예상됩니다.")
                    else: comments.append(f"🔥 **종합 분석:** 객관적인 스탯에서 🔵 **{pB.split(' (')[0]}** 선수가 우세합니다. 안정적인 경기 운영을 펼친다면 무난한 승리가 예상됩니다.")

                    if a_exp > b_exp + 10: comments.append(f"🧠 **경험치 우위:** 공식전 출전 짬바가 훨씬 많은 🔴 **{pA.split(' (')[0]}** 선수가 심리적인 여유와 템포 조절에서 앞설 수 있습니다.")
                    elif b_exp > a_exp + 10: comments.append(f"🧠 **경험치 우위:** 공식전 출전 짬바가 훨씬 많은 🔵 **{pB.split(' (')[0]}** 선수가 심리적인 여유와 템포 조절에서 앞설 수 있습니다.")
                    
                    if a_clutch > b_clutch + 2: comments.append(f"💦 **클러치 상황:** 1점 차 피말리는 접전 승부로 간다면 강심장인 🔴 **{pA.split(' (')[0]}** 선수의 집중력이 빛을 발할 확률이 높습니다.")
                    elif b_clutch > a_clutch + 2: comments.append(f"💦 **클러치 상황:** 1점 차 피말리는 접전 승부로 간다면 강심장인 🔵 **{pB.split(' (')[0]}** 선수의 집중력이 빛을 발할 확률이 높습니다.")

                    st.markdown("#### 💡 AI 해설위원 관전 포인트")
                    for c in comments: st.write(f"- {c}")

                else:
                    a_tot = len(h2h[h2h['승패'] == '승'])
                    b_tot = len(h2h[h2h['승패'] == '패'])
                    
                    prelim_m = h2h[h2h['단계'] == '예선']
                    main_m = h2h[h2h['단계'] == '본선']
                    
                    a_pre, b_pre = len(prelim_m[prelim_m['승패'] == '승']), len(prelim_m[prelim_m['승패'] == '패'])
                    a_main, b_main = len(main_m[main_m['승패'] == '승']), len(main_m[main_m['승패'] == '패'])
                    
                    st.success(f"🔥 **종합 전적: 총 {len(h2h)}전 ➡️ 🔴 {pA.split(' (')[0]} {a_tot}승 / 🔵 {pB.split(' (')[0]} {b_tot}승**")
                    
                    m1, m2 = st.columns(2)
                    m1.info(f"**[예선 기록] 🔴 {pA.split(' (')[0]} {a_pre}승 / 🔵 {pB.split(' (')[0]} {b_pre}승**")
                    m2.error(f"**[본선 기록] 🔴 {pA.split(' (')[0]} {a_main}승 / 🔵 {pB.split(' (')[0]} {b_main}승**")
                    
                    df_h2h = h2h[['대회명', '단계', '승패']].rename(columns={'승패':f'{pA.split(" (")[0]} 기준 결과'}).sort_values('대회명', ascending=False).reset_index(drop=True)
                    df_h2h[f'{pA.split(" (")[0]} 기준 결과'] = df_h2h[f'{pA.split(" (")[0]} 기준 결과'].apply(lambda x: f"🔴 {pA.split(' (')[0]} 승리" if x == '승' else f"🔵 {pB.split(' (')[0]} 승리")
                    st.dataframe(df_h2h, use_container_width=True)

# ================= TAB 6: 다음 대회 시뮬레이터 =================
with tab6:
    st.subheader("🔮 대회 예상 시뮬레이터 (천적 경보)")
    st.markdown("출전 선수 이름을 입력하면, 같은 이름의 모든 선수 스탯과 맞대결 천적을 조회해 줍니다.")
    entry_list_text = st.text_area("출전 선수 이름 입력 (쉼표나 엔터로 구분)", placeholder="예시: 홍길동, 김철수")
    if st.button("예상 등수 시뮬레이션 가동"):
        if entry_list_text and not global_db.empty:
            names = [n.strip() for n in re.split(r'[,\n]+', entry_list_text) if n.strip()]
            sim_db = global_db[global_db['이름'].isin(names)]
            
            if not sim_db.empty:
                goyu_names = sim_db['고유이름'].unique().tolist()
                
                if len(goyu_names) >= 2 and not global_match.empty:
                    rel_m = global_match[global_match['기준_고유'].isin(goyu_names) & global_match['상대_고유'].isin(goyu_names)]
                    alerts = []
                    for pn in goyu_names:
                        pm = rel_m[rel_m['기준_고유'] == pn]
                        for on in pm['상대_고유'].unique():
                            h = pm[pm['상대_고유'] == on]
                            w, l = len(h[h['승패'] == '승']), len(h[h['승패'] == '패'])
                            if w == 0 and l >= 1: 
                                alerts.append(f"🚨 **[{pn.split(' (')[0]}]** 선수 비상! 단 한 번도 이겨보지 못한 천적 **[{on.split(' (')[0]}]** 출전! ({l}전 전패)")
                    for a in list(set(alerts)): st.error(a)

                all_pts_sim = global_db.groupby('고유이름')['레이팅(PT)'].mean()
                def calc_luck(pn):
                    opps = global_match[(global_match['단계']=='예선') & (global_match['기준_고유']==pn)]['상대_고유']
                    if len(opps) == 0: return "평이"
                    avg_pt = opps.map(all_pts_sim).fillna(20).mean() 
                    if avg_pt >= 40: return f"💀 지옥 뿔 ({avg_pt:.1f}pt)"
                    if avg_pt >= 25: return f"⚔️ 험난 뿔 ({avg_pt:.1f}pt)"
                    if avg_pt >= 15: return f"😐 평이 뿔 ({avg_pt:.1f}pt)"
                    return f"🍯 꿀통 뿔 ({avg_pt:.1f}pt)"

                ss = sim_db.groupby('고유이름').agg(합산PT=('레이팅(PT)', 'sum'), 평균승률=('예선_승률(%)', 'mean')).reset_index()
                ss['예상 대진운'] = ss['고유이름'].apply(calc_luck)
                ss = ss.sort_values(by=['합산PT', '평균승률'], ascending=[False, False]).reset_index(drop=True)
                ss.index += 1
                
                st.dataframe(ss, column_config={
                    "고유이름": "참가선수 (소속)",
                    "합산PT": st.column_config.NumberColumn("누적 레이팅", format="%.1f pt"),
                    "평균승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%")
                }, use_container_width=True)
            else: st.warning("입력하신 이름의 선수 기록이 없습니다.")

# ================= TAB 7: 성적 업로드 (관리자 전용) =================
with tab7:
    st.error("🚨 **[엄중 경고] 관리자 전용 데이터 업로드 구역입니다!** \n\n일반 회원이 웹에서 엑셀을 업로드하거나 조작하면, 서버가 새로고침 될 때 데이터가 전부 증발할 수 있습니다. 엑셀 업로드는 오직 **관리자의 로컬(내 컴퓨터) 환경에서 파이썬을 실행했을 때만** 진행하십시오.")
    st.subheader("📂 새로운 대회 성적 업로드 (다중 파일 & 다중 시트 지원)")
    
    col1, col2 = st.columns(2)
    with col1: tourney_name = st.text_input("대회명 (파일명에 날짜 형식이 없을 때만 적용됨)")
    with col2: tourney_date = st.date_input("대회 일자 (파일명에 날짜 형식이 없을 때만 적용됨)")
        
    uploaded_files = st.file_uploader("원본 엑셀 파일(.xlsx) 업로드 (여러 개 동시 선택 가능!)", type=['xlsx'], accept_multiple_files=True)
    
    if st.button("데이터베이스에 일괄 추가하기 (자동 저장)"):
        if uploaded_files:
            new_players = []
            new_matches = []
            
            def format_val(x):
                if pd.isna(x): return ""
                v = str(x).strip()
                if v.endswith('.0'): return v[:-2]
                if ":" in v or "1900-" in v or "1899-" in v: return "0"
                return v
            
            def get_num(text):
                if pd.isna(text) or str(text).strip() == "": return None
                nums = re.findall(r'\d+', str(text))
                return int(nums[0]) if nums else None
            
            def get_pt(final_rank, prelim_rank):
                t = get_num(final_rank)
                if t is None: t = get_num(prelim_rank)
                if t is None: return 5
                if t == 1: return 100
                elif t == 2: return 80
                elif t in [3, 4]: return 60
                elif 5 <= t <= 8: return 45  
                elif 9 <= t <= 16: return 25 
                elif 17 <= t <= 32: return 10 
                else: return 5

            def get_bracket(n):
                if n == 2: return [1, 2]
                prev = get_bracket(n // 2)
                b = []
                for p in prev: b.extend([p, n + 1 - p])
                return b

            def get_rscore(rank):
                if pd.isna(rank): return 0
                if rank == 1: return 100
                if rank == 2: return 90
                if rank in [3, 4]: return 80
                if 5 <= rank <= 8: return 70
                if 9 <= rank <= 16: return 60
                if 17 <= rank <= 32: return 50
                return 0
                
            success_count = 0
            for uploaded_file in uploaded_files:
                file_name_no_ext = os.path.splitext(uploaded_file.name)[0]
                
                t_name = tourney_name
                t_date_str = str(tourney_date)
                
                if "_" in file_name_no_ext:
                    parts = file_name_no_ext.rsplit("_", 1)
                    if len(parts) == 2 and re.match(r'\d{4}-\d{2}-\d{2}', parts[1]):
                        t_name = parts[0]
                        t_date_str = parts[1]
                    else:
                        t_name = file_name_no_ext
                else:
                    if not t_name:
                        t_name = file_name_no_ext
                
                if not st.session_state.player_db.empty and t_name in st.session_state.player_db['대회명'].values:
                    st.warning(f"⚠️ '{t_name}' 대회는 이미 등록되어 있어 건너뜁니다.")
                    continue

                try: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='calamine', header=None)
                except: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl', header=None)

                success_count += 1
                for sheet_name, df in sheets.items():
                    if df.empty or "단체" in sheet_name or "단체" in t_name: continue 
                    
                    all_rows = [[format_val(x) for x in row.values] for _, row in df.iterrows()]
                    
                    parsed_players = {}
                    valid_names = {}
                    bracket_players = set()
                    
                    in_pool = False
                    col_map = {}
                    pool_blocks, curr_pool = [], []
                    
                    for r in all_rows:
                        j = "".join(r).replace(" ", "")
                        c_str = [str(x).replace(" ", "") for x in r]
                        
                        if 'No' in c_str and '이름' in c_str and '소속팀' in c_str:
                            if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool}); curr_pool = []
                            in_pool = True
                            col_map = {n: i for i, n in enumerate(c_str) if n != ""}
                            continue
                            
                        if "최종순위" in j or "뿔랭킹" in j or "최종랭킹" in j or "엘리미나시옹" in j or "8강전" in j or ("순위" in c_str and "이름" in c_str and "소속팀" in c_str) or ("랭킹" in c_str and "이름" in c_str):
                            if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool}); curr_pool = []
                            in_pool = False
                            
                        if in_pool:
                            n_idx = col_map.get('이름')
                            no_idx = col_map.get('No')
                            if n_idx is not None and n_idx < len(r):
                                name = str(r[n_idx]).strip()
                                if name and name not in ["이름", "nan", "0"] and not name.startswith("뿔"):
                                    p_no = str(r[no_idx]).strip() if no_idx is not None and no_idx < len(r) else str(len(curr_pool)+1)
                                    curr_pool.append({'row': r, 'No': p_no})
                                    valid_names[name.replace(" ", "")] = name
                                    
                    if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool})

                    pool_data = []
                    for b in pool_blocks:
                        cmap, players = b['map'], b['p']
                        for i, p1 in enumerate(players):
                            p1_r = p1['row']
                            name1 = str(p1_r[cmap.get('이름')]).strip()
                            
                            # 💡 엑셀 업로드 파싱 시점에서 소속팀 이름 강제 통합
                            team1 = str(p1_r[cmap.get('소속팀')]).strip() if '소속팀' in cmap and cmap.get('소속팀') < len(p1_r) else ""
                            team1 = team1.replace('(사)부산펜싱클럽', '윈펜싱클럽').replace('부산펜싱클럽', '윈펜싱클럽').replace('(사)부산펜싱', '윈펜싱클럽')
                            
                            wins, v_matches, deuk = 0, 0, 0
                            tight_wins = 0
                            
                            j_idx = cmap.get('지수')
                            try: jisu = int(str(p1_r[j_idx]).replace("+","").replace(" ","")) if j_idx is not None else 0
                            except: jisu = 0
                            
                            m_dict = {}
                            for j, p2 in enumerate(players):
                                if i == j: continue
                                name2 = str(p2['row'][cmap.get('이름')]).strip()
                                opp_c = str(j + 1)
                                if opp_c in cmap and cmap[opp_c] < len(p1_r):
                                    sc = str(p1_r[cmap[opp_c]]).strip()
                                    if sc and (sc.upper().startswith('V') or sc.isdigit() or sc == '0'):
                                        v_matches += 1
                                        if sc.upper().startswith('V'):
                                            wins += 1
                                            m_dict[name2] = '승'
                                            s_num = get_num(sc)
                                            deuk += s_num if s_num is not None else 5
                                            if sc.upper() in ["V1", "V2", "V3", "V4"]: tight_wins += 1
                                        else: 
                                            m_dict[name2] = '패'
                                            s_num = get_num(sc)
                                            deuk += s_num if s_num is not None else 0
                                            
                            wr = round((wins / v_matches) * 100, 1) if v_matches > 0 else 0.0
                            parsed_players[name1] = {
                                '대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name,
                                '이름': name1, '소속팀': team1, '예선_승': wins, '예선_패': v_matches - wins,
                                '예선_승률(%)': wr, '예선_득점': deuk, '예선_실점': deuk - jisu, '진땀승': tight_wins,
                                '예선_랭킹': "기록없음", '본선_랭킹': "기록없음"
                            }
                            pool_data.append({'이름': name1, '소속팀': team1, 'm': m_dict, 'No': p1['No']})

                    r_mode = None
                    for r in all_rows:
                        j = "".join(r).replace(" ", "")
                        c_str = [str(x).replace(" ", "") for x in r]
                        
                        if ("순위" in c_str and "이름" in c_str) or "최종순위" in j or "최종랭킹" in j: r_mode = 'final'; continue
                        elif ("랭킹" in c_str and "이름" in c_str and "No" not in c_str) or "뿔랭킹" in j or "예선랭킹" in j: r_mode = 'prelim'; continue
                        elif "엘리미나시옹" in j or "8강전" in j or "결과" in j or ('No' in c_str and '이름' in c_str): r_mode = None
                            
                        if r_mode:
                            for c_idx, cell in enumerate(r):
                                nk = str(cell).replace(" ", "")
                                if nk in valid_names and c_idx > 0:
                                    r_name = valid_names[nk]
                                    lv = ""
                                    for p_c in range(c_idx - 1, -1, -1):
                                        cand = str(r[p_c]).strip()
                                        if cand and cand not in ["위", "랭킹", "순위", "이름"]:
                                            if cand.isdigit() or '위' in cand: lv = cand; break
                                    if lv:
                                        if '위' not in lv: lv += '위'
                                        if r_mode == 'final': parsed_players[r_name]['본선_랭킹'] = lv
                                        elif r_mode == 'prelim': parsed_players[r_name]['예선_랭킹'] = lv
                        
                        if "엘리미나시옹" in j or "8강전" in j or "준결승" in j:
                            for cell in r:
                                nk = str(cell).replace(" ", "")
                                if nk in valid_names: bracket_players.add(valid_names[nk])

                    t_dict = {p['이름']: p['소속팀'] for p in pool_data}
                    for p in pool_data:
                        for o_name, res in p['m'].items():
                            # 💡 엑셀 업로드 파싱 시점에서 상대팀 이름 강제 통합
                            opp_team = str(t_dict.get(o_name, ""))
                            opp_team = opp_team.replace('(사)부산펜싱클럽', '윈펜싱클럽').replace('부산펜싱클럽', '윈펜싱클럽').replace('(사)부산펜싱', '윈펜싱클럽')
                            new_matches.append({
                                '대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name,
                                '기준선수': p['이름'], '기준팀': p['소속팀'], '상대선수': o_name, '상대팀': opp_team,
                                '승패': res, '단계': '예선', '업셋여부': 'N', '진땀승': 'Y' if res=='승' and parsed_players[p['이름']]['진땀승']>0 else 'N'
                            })

                    sheet_players = []
                    for p_data in parsed_players.values():
                        if p_data['예선_랭킹'] == "기록없음" and p_data['본선_랭킹'] != "기록없음": p_data['예선_랭킹'] = p_data['본선_랭킹']
                        elif p_data['본선_랭킹'] == "기록없음" and p_data['예선_랭킹'] != "기록없음": p_data['본선_랭킹'] = p_data['예선_랭킹']
                        p_data['예선_순위(숫자)'] = get_num(p_data['예선_랭킹'])
                        p_data['본선_순위(숫자)'] = get_num(p_data['본선_랭킹'])
                        p_data['레이팅(PT)'] = get_pt(p_data['본선_랭킹'], p_data['예선_랭킹'])
                        new_players.append(p_data)
                        sheet_players.append(p_data)

                    advanced = [p for p in sheet_players if p['이름'] in bracket_players and p['예선_순위(숫자)'] is not None]
                    if advanced:
                        ms = max(p['예선_순위(숫자)'] for p in advanced)
                        bs = 2
                        while bs < ms: bs *= 2
                        b_seeds = get_bracket(bs)
                        s2p = {p['예선_순위(숫자)']: p for p in advanced}
                        
                        cr = [s2p.get(s) for s in b_seeds]
                        while len(cr) > 1:
                            nr = []
                            for i in range(0, len(cr), 2):
                                p1, p2 = cr[i], cr[i+1]
                                if p1 is None and p2 is None: nr.append(None)
                                elif p1 is None: nr.append(p2)
                                elif p2 is None: nr.append(p1)
                                else:
                                    s1, s2 = get_rscore(p1['본선_순위(숫자)']), get_rscore(p2['본선_순위(숫자)'])
                                    if s1 > s2: w, l = p1, p2
                                    elif s2 > s1: w, l = p2, p1
                                    else: w, l = (p1, p2) if p1['예선_순위(숫자)'] < p2['예선_순위(숫자)'] else (p2, p1)
                                        
                                    is_up = 'Y' if w['예선_순위(숫자)'] > l['예선_순위(숫자)'] else 'N'
                                    new_matches.append({'대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '기준선수': w['이름'], '기준팀': w['소속팀'], '상대선수': l['이름'], '상대팀': l['소속팀'], '승패': '승', '단계': '본선', '업셋여부': is_up, '진땀승':'N'})
                                    new_matches.append({'대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '기준선수': l['이름'], '기준팀': l['소속팀'], '상대선수': w['이름'], '상대팀': w['소속팀'], '승패': '패', '단계': '본선', '업셋여부': 'N', '진땀승':'N'})
                                    nr.append(w)
                            cr = nr
            
            if new_players:
                st.session_state.player_db = pd.concat([st.session_state.player_db, pd.DataFrame(new_players)], ignore_index=True)
                st.session_state.match_db = pd.concat([st.session_state.match_db, pd.DataFrame(new_matches)], ignore_index=True)
                st.session_state.player_db.to_csv(PLAYER_DB_FILE, index=False, encoding='utf-8-sig')
                st.session_state.match_db.to_csv(MATCH_DB_FILE, index=False, encoding='utf-8-sig')
                st.success(f"✅ 총 {success_count}개 대회 파일 데이터 파싱 및 저장 완료! 랭킹 표 누락 100% 픽스 완료!")
                st.rerun()
        else:
            st.warning("대회 파일들을 업로드해 주십시오.")