import streamlit as st
import pandas as pd
import os
import re
import datetime
import random
import plotly.graph_objects as go

st.set_page_config(page_title="윈펜싱클럽 전력 분석 V32.0", page_icon="🤺", layout="wide")

st.title("🤺 윈펜싱클럽 통합 데이터랩 (V32.0 퍼펙트 에디션)")
st.markdown("V31 버그 완벽 수정 + 세이버메트릭스 **동일 부수 내 상위 % 비교** 랭킹 시스템 탑재!")

# ================= 🗄️ 데이터베이스 및 기본 설정 =================
PLAYER_DB_FILE = "fencing_player_db.csv"
MATCH_DB_FILE = "fencing_match_db.csv"
COMMENT_DB_FILE = "fencing_comment_db.csv"
CLUB_COMMENT_DB_FILE = "fencing_club_comment_db.csv"
SCHEDULE_DB_FILE = "fencing_schedule_db.csv"

# 🌟 관리자 인증 및 사이드바
if 'admin_auth' not in st.session_state:
    st.session_state.admin_auth = False

with st.sidebar:
    st.header("🔒 관리자 모드")
    if not st.session_state.admin_auth:
        admin_pw = st.text_input("비밀번호 (업로드/일정 관리)", type="password")
        if admin_pw == "win1205!":
            st.session_state.admin_auth = True
            st.success("✅ 관리자 권한 활성화!")
            st.rerun()
    else:
        st.success("✅ 관리자로 접속 중입니다.")
        if st.button("로그아웃"):
            st.session_state.admin_auth = False
            st.rerun()
            
    st.divider()
    st.warning("⚠️ 랭킹이 꼬였을 때만 누르세요")
    if st.button("🗑️ 성적 데이터 완전 초기화"):
        if st.session_state.admin_auth:
            if os.path.exists(PLAYER_DB_FILE): os.remove(PLAYER_DB_FILE)
            if os.path.exists(MATCH_DB_FILE): os.remove(MATCH_DB_FILE)
            for key in ['player_db', 'match_db']:
                if key in st.session_state: del st.session_state[key]
            st.success("성적 데이터 리셋 완료! (방명록 및 일정은 유지됩니다)")
            st.rerun()
        else:
            st.error("데이터 초기화는 관리자 권한이 필요합니다.")

# DB 로딩 함수
def load_db(file_name, default_cols=None):
    if os.path.exists(file_name): return pd.read_csv(file_name)
    return pd.DataFrame(columns=default_cols) if default_cols else pd.DataFrame()

if 'player_db' not in st.session_state: st.session_state.player_db = load_db(PLAYER_DB_FILE)
if 'match_db' not in st.session_state: st.session_state.match_db = load_db(MATCH_DB_FILE)
if 'comment_db' not in st.session_state: st.session_state.comment_db = load_db(COMMENT_DB_FILE, ["대상선수", "작성자", "내용", "작성일시"])
if 'club_comment_db' not in st.session_state: st.session_state.club_comment_db = load_db(CLUB_COMMENT_DB_FILE, ["대상클럽", "작성자", "내용", "작성일시"])
if 'schedule_db' not in st.session_state: st.session_state.schedule_db = load_db(SCHEDULE_DB_FILE, ["대회일자", "대회명", "장소", "비고"])

global_db = st.session_state.player_db.copy()
global_match = st.session_state.match_db.copy()

# ================= 💡 데이터 전처리 및 나이대 추론 =================
def get_age_group(div_str):
    if pd.isna(div_str): return "일반부"
    d = str(div_str).replace(" ", "")
    if any(x in d for x in ["초", "U-9", "U-10", "U-11", "U-12", "U9", "U10", "U11", "U12", "유소년", "초등"]): return "초등부"
    if any(x in d for x in ["중", "고", "청소년", "U-14", "U-15", "U-17", "U14", "U15", "U17"]): return "중고등부"
    if any(x in d for x in ["일반", "대학", "엘리트", "성인", "마스터즈"]): return "일반부"
    return "통합부"

if not global_db.empty:
    global_db['소속팀'] = global_db['소속팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_db['대회일자'] = pd.to_datetime(global_db['대회일자'], errors='coerce')
    global_db['연도'] = global_db['대회일자'].dt.year.fillna(2026).astype(int).astype(str)
    global_db['나이대'] = global_db['부수'].apply(get_age_group)
    for col in ['본선_순위(숫자)', '예선_순위(숫자)', '레이팅(PT)', '예선_승률(%)', '예선_승', '예선_패', '예선_득점', '예선_실점']:
        if col not in global_db.columns: global_db[col] = 0
        global_db[col] = pd.to_numeric(global_db[col], errors='coerce').fillna(0)
    global_db['고유이름'] = global_db['이름'] + " (" + global_db['소속팀'].fillna("소속불명") + ")"

if not global_match.empty:
    global_match['기준팀'] = global_match['기준팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_match['상대팀'] = global_match['상대팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_match['대회일자'] = pd.to_datetime(global_match['대회일자'], errors='coerce')
    global_match['연도'] = global_match['대회일자'].dt.year.fillna(2026).astype(int).astype(str)
    global_match['기준_고유'] = global_match['기준선수'] + " (" + global_match['기준팀'].fillna("소속불명") + ")"
    global_match['상대_고유'] = global_match['상대선수'] + " (" + global_match['상대팀'].fillna("소속불명") + ")"

# 글로벌 검색 필터
with st.sidebar:
    st.header("🔍 통합 검색 필터")
    if not global_db.empty:
        sel_year = st.selectbox("📅 연도", ["전체"] + sorted(list(global_db['연도'].unique()), reverse=True))
        if sel_year != "전체":
            global_db = global_db[global_db['연도'] == sel_year]
            global_match = global_match[global_match['연도'] == sel_year]

# ================= 🎯 UI 탭 구성 =================
tabs = st.tabs([
    "📖 가이드/일정표", "🏆 종합 랭킹 보드", "🏢 클럽 명전/방명록", 
    "🎮 개인분석 (칭호/세이버)", "💠 육각형 스탯 폼", 
    "⚔️ 1:1 라이벌 비교", "🔮 대회 예측 시뮬", "⚙️ 데이터 관리"
])

# ================= TAB 0: 가이드 & 일정표 =================
with tabs[0]:
    st.subheader("📖 윈펜싱 데이터랩 V32.0 얼티밋 에디션")
    st.markdown("""
    환영합니다! V32는 기존 세이버메트릭스 지표가 얼마나 뛰어난 수치인지 직관적으로 파악할 수 있도록 **'동급 부수 대비 상위 % 랭킹 시스템'**을 도입했습니다.
    
    *   **🏆 종합 랭킹:** 전국 클럽 및 선수의 누적 PT 및 종합 스탯을 확인합니다.
    *   **🏢 클럽 스탯:** 명예의 전당(우승/메달/승률왕) 기록과 전체 로스터, 단체 방명록을 제공합니다.
    *   **🎮 개인 분석 (세이버메트릭스+100칭호):** 100여 종의 칭호 시스템과 동일 부수 내 상대 랭킹(%)을 결합하여 분석합니다.
    *   **💠 육각형 스탯 & 라이벌 비교:** [대분류 ➡️ 클럽 ➡️ 선수]의 3단계 필터로 빠르고 편하게 선수를 찾을 수 있습니다.
    *   **🔮 시뮬레이터:** 체크박스 다중 선택 방식으로 직관적인 천적/상성 시뮬레이션을 돌립니다.
    """)
    st.divider()
    st.subheader("📅 연간 대회 및 행사 일정표")
    if not st.session_state.schedule_db.empty:
        st.dataframe(st.session_state.schedule_db.sort_values(by="대회일자"), use_container_width=True, hide_index=True)
    else:
        st.info("현재 등록된 일정이 없습니다.")

# ================= TAB 1: 종합 랭킹 =================
with tabs[1]:
    st.subheader("🏆 종합 랭킹 보드")
    if not global_db.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### 🏢 전국 클럽 파워 스탯 랭킹")
            cs = global_db.groupby('소속팀').agg(
                총원=('고유이름', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 평균PT=('레이팅(PT)', 'mean'),
                금메달=('본선_순위(숫자)', lambda x: (x.dropna() == 1).sum()), 은메달=('본선_순위(숫자)', lambda x: (x.dropna() == 2).sum()), 동메달=('본선_순위(숫자)', lambda x: x.dropna().isin([3, 4]).sum())
            ).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            cs.index += 1
            st.dataframe(cs, column_config={"합산PT": st.column_config.NumberColumn("합산 레이팅", format="%.0f pt"), "평균PT": st.column_config.NumberColumn("클럽 평균전력", format="%.1f pt")}, use_container_width=True)

        with c2:
            st.markdown("#### 🤺 선수 종합 스탯 랭킹 (전국 통합)")
            ps = global_db.sort_values('대회일자').groupby('고유이름').agg(
                소속팀=('소속팀', 'last'), 출전=('대회명', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 
                평균PT=('레이팅(PT)', 'mean'), 승률=('예선_승률(%)', 'mean')
            ).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            ps.index += 1
            st.dataframe(ps, column_config={"합산PT": st.column_config.NumberColumn("합산 레이팅", format="%.0f pt"), "평균PT": st.column_config.NumberColumn("평균 레이팅", format="%.1f pt"), "승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%")}, use_container_width=True)

# ================= TAB 2: 클럽 분석 & 명예의 전당 & 방명록 =================
with tabs[2]:
    st.subheader("🏢 클럽 정밀 분석 & 명예의 전당 & 방명록")
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
            c4.metric("본선 업셋 (자이언트 킬링)", f"{len(h_match[(h_match['단계'] == '본선') & (h_match['승패'] == '승') & (h_match['업셋여부'] == 'Y')])}회")
            
            st.markdown("---")
            st.markdown(f"### 🏅 {my_team} 명예의 전당 (Top 10)")
            s1, s2, s3, s4 = st.columns(4)
            
            golds = h_db[h_db['본선_순위(숫자)'] == 1].groupby('고유이름').size().reset_index(name='금메달').sort_values('금메달', ascending=False).head(10)
            s1.success("👑 **[우승 제조기]**\n\n클럽 내 1위 입상 Top 10")
            for i, row in golds.iterrows(): s1.write(f"- {row['고유이름'].split(' (')[0]} (금 {row['금메달']}개)")
            
            medals = h_db[(h_db['본선_순위(숫자)'] >= 1) & (h_db['본선_순위(숫자)'] <= 4)].groupby('고유이름').size().reset_index(name='메달').sort_values('메달', ascending=False).head(10)
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
                출전대회=('대회명', 'nunique'), 누적레이팅=('레이팅(PT)', 'sum'), 평균레이팅=('레이팅(PT)', 'mean'), 평균승률=('예선_승률(%)', 'mean'), 본선최고순위=('본선_순위(숫자)', lambda x: x[x>0].min() if len(x[x>0]) > 0 else None)
            ).reset_index().sort_values('누적레이팅', ascending=False).reset_index(drop=True)
            roster.index += 1
            st.dataframe(roster, use_container_width=True)
            
            st.divider()
            st.markdown(f"### 📣 {my_team} 단체 응원 방명록")
            club_comments = st.session_state.club_comment_db[st.session_state.club_comment_db['대상클럽'] == my_team]
            if not club_comments.empty:
                for _, row in club_comments.sort_values(by='작성일시', ascending=False).head(15).iterrows():
                    st.markdown(f"<div style='background-color:#1e2a3a; padding:12px; border-left:4px solid #54c3a6; border-radius:5px; margin-bottom:8px;'><b>{row['작성자']}</b> <span style='font-size:12px;color:#888;'>({row['작성일시']})</span><br><span style='color:#ddd; font-size:15px;'>{row['내용']}</span></div>", unsafe_allow_html=True)
            else: st.info("클럽에 첫 번째 단체 응원을 남겨주세요!")
            
            with st.form("club_comment_form", clear_on_submit=True):
                cc1, cc2 = st.columns([1, 4])
                with cc1: author = st.text_input("닉네임 (익명 가능)", placeholder="예: 열혈팬")
                with cc2: content = st.text_input("응원 남기기", placeholder="우리 클럽 파이팅!!")
                if st.form_submit_button("📝 단체 코멘트 등록"):
                    if content.strip():
                        new_c = pd.DataFrame([{"대상클럽": my_team, "작성자": author if author else "익명", "내용": content, "작성일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        st.session_state.club_comment_db = pd.concat([st.session_state.club_comment_db, new_c], ignore_index=True)
                        st.session_state.club_comment_db.to_csv(CLUB_COMMENT_DB_FILE, index=False, encoding='utf-8-sig')
                        st.success("등록 완료!"); st.rerun()

# ================= TAB 3: 개인 스탯 & 세이버메트릭스 & AI & 100 칭호 =================
with tabs[3]:
    st.subheader("🎮 개인 정밀 분석 (세이버메트릭스 & 100+ 칭호 시스템)")
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

            st.markdown(f"### 🎖️ {sel_player.split(' (')[0]} 선수의 종합 스카우팅 리포트")
            
            st.markdown(f"""
            <div style="background-color:#1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 8px solid {t_color};">
                <h2 style="margin-top:0px; color: {t_color};">{t_name}</h2>
                <p style="font-size: 15px; color:#ddd; margin-bottom: 10px;">{t_desc}</p>
                <div style="width: 100%; background-color: #333; border-radius: 10px; height: 12px; margin-top: 10px;">
                    <div style="width: {100-pct}%; background-color: {t_color}; height: 100%; border-radius: 10px;"></div>
                </div>
                <div style="text-align:right; font-size:12px; color:#888; margin-top:5px;">현재 생태계 전체 상위 {pct:.1f}% 위치</div>
            </div>
            """, unsafe_allow_html=True)

            # --- 세이버메트릭스 지표 연산 ---
            age_group = p_data['나이대'].iloc[-1]
            tot_tournaments = len(p_data)
            tot_matches = p_data['예선_승'].sum() + p_data['예선_패'].sum()
            actual_wr = p_data['예선_승률(%)'].mean()
            tot_sc = p_data['예선_득점'].sum()
            tot_ls = p_data['예선_실점'].sum()
            avg_margin = (tot_sc - tot_ls) / tot_matches if tot_matches > 0 else 0
            
            denom = (tot_sc**2) + (tot_ls**2)
            pythagorean = ((tot_sc**2) / denom * 100) if denom > 0 else 50.0
            luck_index = actual_wr - pythagorean 
            
            main_advances = len(p_data[p_data['본선_순위(숫자)'] > 0])
            pass_rate = (main_advances / tot_tournaments * 100) if tot_tournaments > 0 else 0.0
            
            # 🔥 무조건 새가슴이 되지 않도록 본선 승률 예외처리
            main_m = m_data[m_data['단계'] == '본선']
            main_total = len(main_m)
            if main_total > 0:
                main_wins = len(main_m[main_m['승패'] == '승'])
                main_wr = (main_wins / main_total * 100)
                choke_index = actual_wr - main_wr 
            else:
                main_wr = None
                choke_index = None
            
            tot_wins = p_data['예선_승'].sum()
            sweats = len(m_data[(m_data['단계']=='예선') & (m_data['진땀승']=='Y')])
            dom_rate = ((tot_wins - sweats) / tot_wins * 100) if tot_wins > 0 else 0.0

            # --- 💡 세이버메트릭스 동급 부수 내 상위 % (백분위) 고속 연산 ---
            my_div = p_data['부수'].iloc[-1]
            div_p = global_db[global_db['부수'] == my_div]
            div_m = global_match[global_match['기준_고유'].isin(div_p['고유이름'].unique())]
            
            # 예선 통과율 계산
            div_tourneys = div_p.groupby('고유이름').size()
            div_advances = div_p[div_p['본선_순위(숫자)'] > 0].groupby('고유이름').size()
            div_pass_rate = (div_advances.reindex(div_tourneys.index, fill_value=0) / div_tourneys) * 100
            
            # 피타고리안 계산
            div_sc = div_p.groupby('고유이름')['예선_득점'].sum()
            div_ls = div_p.groupby('고유이름')['예선_실점'].sum()
            div_denom = (div_sc**2) + (div_ls**2)
            div_pyth = ((div_sc**2) / div_denom * 100).fillna(50.0)
            
            # 본선 승률 계산
            div_main_m = div_m[div_m['단계'] == '본선']
            div_main_wins = div_main_m[div_main_m['승패'] == '승'].groupby('기준_고유').size()
            div_main_total = div_main_m.groupby('기준_고유').size()
            div_main_wr = (div_main_wins.reindex(div_main_total.index, fill_value=0) / div_main_total) * 100
            
            # 압도율 계산
            div_tot_wins = div_p.groupby('고유이름')['예선_승'].sum()
            div_sweats = div_m[(div_m['단계'] == '예선') & (div_m['진땀승'] == 'Y')].groupby('기준_고유').size()
            div_dom = ((div_tot_wins - div_sweats.reindex(div_tot_wins.index, fill_value=0)) / div_tot_wins * 100).fillna(0.0)
            
            def get_percentile(series, val, higher_is_better=True):
                if series.empty or pd.isna(val): return "비교불가"
                if higher_is_better:
                    pct = (series > val).mean() * 100
                else:
                    pct = (series < val).mean() * 100
                return f"상위 {max(1, int(pct))}%"

            pct_pass = get_percentile(div_pass_rate, pass_rate)
            pct_pyth = get_percentile(div_pyth, pythagorean)
            pct_dom = get_percentile(div_dom, dom_rate)
            pct_main_wr = get_percentile(div_main_wr, main_wr) if main_wr is not None else "비교불가"

            # --- 💡 세이버메트릭스 지표 설명문 추가 ---
            st.markdown("#### 🔬 세이버메트릭스 (고급 통계 지표 및 동일 부수 비교)")
            st.info(f"""
            **💡 세이버메트릭스 용어 설명 (기준: 가장 최근에 출전한 [{my_div}] 참가자 그룹 대상)**
            - **상위 % 비교**: 각 스탯 제목 괄호 안의 퍼센트는 **동일 부수에 출전한 선수들 중 내가 전체 상위 몇 %**인지 객관적으로 보여주는 지표입니다.
            - **피타고리안 기대승률**: 득점/실점 비율로 산출한 '이론적 기대 승률' (실제 승률 > 기대 승률 = 접전에 강함/운이 좋음)
            - **새가슴 지수**: (예선 승률 - 본선 승률). 단판 토너먼트 특성상 1패를 안고 탈락하기에 지수가 높게(플러스로) 측정되는 것이 정상입니다. 따라서 **본선을 최소 3번 이상 치르고 하락폭이 30%p 이상일 때만** 새가슴 징크스로 판정합니다.
            - **압도율 (Dominance)**: 승리한 경기 중 1점차 진땀승을 제외한 넉넉한 '완승'의 비율입니다.
            """)
            
            s1, s2, s3, s4 = st.columns(4)
            s1.metric(f"예선 통과율 ({pct_pass})", f"{pass_rate:.1f}%", f"{main_advances}회 본선 진출", delta_color="off")
            s2.metric(f"기대 승률 ({pct_pyth})", f"{pythagorean:.1f}%", f"운/클러치 지수: {luck_index:+.1f}%p", delta_color="off")
            
            if main_wr is not None:
                s3.metric(f"예선 ➡ 본선 승률 ({pct_main_wr})", f"{actual_wr:.0f}% ➡ {main_wr:.0f}%", f"새가슴 지수: {choke_index:+.1f}%p", delta_color="inverse")
            else:
                s3.metric("예선 ➡ 본선 승률", f"{actual_wr:.0f}% ➡ N/A", f"본선 진출 기록 없음", delta_color="off")
                
            s4.metric(f"압도율 ({pct_dom})", f"{dom_rate:.1f}%", f"평균 득실 마진: {avg_margin:+.1f}점", delta_color="off")

            # --- AI 3줄 평 제너레이터 ---
            st.markdown("#### 🤖 AI 스카우터 리포트 (3줄 요약)")
            random.seed(sel_player + str(tot_matches))
            
            if avg_margin >= 2.5: l1 = random.choice(["상대를 압도하는 파괴적인 공격력과 단단한 방어를 동시에 갖춘 폭군입니다.", "초반부터 기선을 완벽하게 제압하여 상대를 펜스 끝으로 몰아넣습니다."])
            elif tot_sc / (tot_matches if tot_matches else 1) >= 4.2: l1 = random.choice(["수비는 잊어라! 맞기 전에 먼저 찔러버리는 극단적이고 화끈한 낭만 공격수입니다.", "경기장 밖까지 열기가 느껴지는 공격 펜싱의 대명사입니다."])
            elif tot_ls / (tot_matches if tot_matches else 1) <= 2.2: l1 = random.choice(["그 어떤 예리한 칼끝도 쉽게 뚫어내지 못하는 비브라늄급 방어력을 자랑합니다.", "상대를 지치게 만드는 늪지대 같은 수비로 승리를 갉아먹는 침착한 플레이어입니다."])
            elif avg_margin < -1.5: l1 = random.choice(["아직 공수 양면에서 폼이 완성되지 않았지만, 특유의 변칙적인 템포가 돋보입니다.", "점수를 내주면서도 실전을 통해 많은 것을 배우고 있는 성장형 펜서입니다."])
            else: l1 = random.choice(["공격과 수비의 밸런스를 유지하며, 어떤 상황에서도 유연하게 대처하는 능력을 지녔습니다.", "상황에 맞게 공수를 자유자재로 전환하는 지능적인 플레이가 장점입니다."])

            if luck_index >= 15: l2 = random.choice(["기대 승률보다 훨씬 높은 실제 성적! 1점 차 피말리는 접전에서 묘하게 승리를 챙기는 클러치 달인입니다.", "운도 실력! 결정적인 순간에 발휘되는 엄청난 집중력과 승운이 따르는 선수입니다."])
            elif luck_index <= -15: l2 = random.choice(["스탯 내용은 훌륭하나 결과가 아쉬운 불운의 아이콘. 승운만 조금 터져주면 성적이 폭발할 것입니다.", "득실 마진은 좋으나 중요한 순간 1점을 내어주는 경향이 있습니다. 뒷심 극복이 관건입니다!"])
            # 🔥 무분별한 새가슴 판정을 막기 위한 밸런스 패치
            elif choke_index is not None and main_advances >= 3 and choke_index <= -15 and pass_rate > 0: l2 = random.choice(["예선에서는 힘을 빼고 있다가 토너먼트에 진입하면 오히려 폼이 올라가는 '본선 여포' 기질이 다분합니다.", "큰 무대 체질! 지면 탈락하는 단판 승부에서 극강의 집중력을 발휘하는 승부사입니다."])
            elif choke_index is not None and main_advances >= 3 and choke_index >= 30 and pass_rate > 0: l2 = random.choice(["예선 생태계의 포식자! 다만 본선 단판 승부에서의 '새가슴' 기질을 극복하는 것이 최우선 과제입니다.", "예선 폼은 완벽하나 본선 첫 판에 굳어버리는 징크스가 있습니다. 마인드 컨트롤 훈련이 필요합니다."])
            else: l2 = random.choice(["매 경기 기복 없이 자신만의 확고한 템포로 묵묵하게 검을 휘두르는 안정적인 멘탈의 소유자입니다.", "흔들림 없는 평정심을 바탕으로 본인의 기량을 거짓 없이 정직하게 100% 발휘합니다."])

            if age_group == "초등부": l3 = random.choice(["무궁무진한 잠재력을 바탕으로 펜싱계의 미래를 밝힐 특급 신동입니다!", "스펀지처럼 기술을 흡수하며 하루가 다르게 폭풍 성장하고 있는 무서운 유소년 유망주입니다."])
            elif age_group == "중고등부": l3 = random.choice(["피지컬과 테크닉이 동시에 만개하는 시기! 청소년부 생태계를 지배할 차세대 에이스로 발돋움 중입니다.", "날카로운 반사신경과 패기로 무대를 휩쓸 준비가 끝난 청소년 기대주입니다."])
            elif age_group == "일반부": l3 = random.choice(["풍부한 인생 경험이 펜싱에도 녹아들어, 짬바에서 나오는 노련미가 일품인 성인부의 마스터입니다.", "퇴근 후 펜싱장에 인생을 바친 열정! 뇌지컬과 지능적인 플레이로 상대를 노련하게 요리합니다."])
            else: l3 = random.choice(["펜싱을 향한 순수한 열정으로 자신만의 무도를 완성해 나가는 멋진 검객입니다.", "성적을 떠나 검을 맞대는 순간 자체를 즐길 줄 아는 진정한 무도인의 자세를 갖췄습니다."])

            st.success(f"1️⃣ {l1}\n\n2️⃣ {l2}\n\n3️⃣ {l3}")
            random.seed()
            st.divider()

            # --- 💡 방대한 100+종 칭호(업적) 시스템 완벽 복구 ---
            titles = []
            golds = len(p_data[p_data['본선_순위(숫자)'] == 1])
            silvers = len(p_data[p_data['본선_순위(숫자)'] == 2])
            bronzes = len(p_data[p_data['본선_순위(숫자)'].isin([3, 4])])
            medals = golds + silvers + bronzes
            up_cnt = len(m_data[(m_data['단계'] == '본선') & (m_data['승패'] == '승') & (m_data['업셋여부'] == 'Y')])
            tot_pt = p_data['레이팅(PT)'].sum()
            avg_wr = actual_wr
            avg_sc = tot_sc / tot_matches if tot_matches > 0 else 0
            avg_ls = tot_ls / tot_matches if tot_matches > 0 else 0
            p_loss = p_data['예선_패'].sum()
            p_win = p_data['예선_승'].sum()
            best_r = p_data['본선_순위(숫자)'].min()

            luck_l = []
            for tn in p_data['대회명']:
                opps = m_data[(m_data['단계']=='예선') & (m_data['대회명']==tn)]['상대_고유']
                if len(opps) > 0: luck_l.append(opps.map(all_pts).fillna(5).mean())
                else: luck_l.append(5.0)
            avg_luck = sum(luck_l)/len(luck_l) if luck_l else 5.0

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

            # [레이팅 / 폼 지표 (V29)]
            if tot_pt >= 1500: titles.append(("🐉 엘더 드래곤", "누적 1500PT. 마주치면 도망치는 것이 상책."))
            elif tot_pt >= 1000: titles.append(("🪐 측정 불가", "누적 1000PT 돌파! 스카우터가 터졌습니다."))
            elif tot_pt >= 700: titles.append(("👑 초월자", "누적 700PT. 범접할 수 없는 그랜드마스터."))
            elif tot_pt >= 500: titles.append(("🌟 최고 존엄", "누적 500PT. 최상위권 랭커의 위엄."))
            elif tot_pt >= 300: titles.append(("⚔️ 소드 마스터", "누적 300PT. 어디가서 펜싱 마스터라고 부를 수 있음."))
            elif tot_pt >= 150: titles.append(("🛡️ 정예 기사", "누적 150PT. 안정적인 궤도에 오른 강자."))

            if avg_wr == 100 and tot_tournaments >= 3: titles.append(("✨ 무결점의 신 (퍼펙트 게임)", "출전한 모든 대회 예선 전승! 흠잡을 곳 없는 완벽함."))
            elif avg_wr >= 90 and tot_tournaments >= 3: titles.append(("👿 타노스", "예선 승률 90% 이상! 참가자의 절반을 가루로 만듭니다."))
            elif avg_wr >= 80 and tot_tournaments >= 2: titles.append(("🦅 사신 (Grim Reaper)", "예선 승률 80% 이상. 한 대 맞추기도 버거운 포스."))
            elif 48 <= avg_wr <= 52 and tot_matches >= 15: titles.append(("⚖️ 인간 저울 (황금밸런스)", "만인을 평등하게 만드는 기적의 반반 승률."))
            elif 45 <= avg_wr <= 55 and tot_matches >= 10: titles.append(("⚖️ 펜싱 수문장", "나를 이기면 강자, 지면 약자. 전투력 판독기."))

            # [플레이스타일 득실점 (V29)]
            if avg_sc >= 4.9 and tot_matches >= 5: titles.append(("🚀 핵탄두 (ICBM)", f"평균 {avg_sc:.1f}득점! 방어막을 찢어발기는 극단적 닥공."))
            elif avg_sc >= 4.6 and tot_matches >= 5: titles.append(("🚀 둠피스트", f"평균 {avg_sc:.1f}득점! 스치기만 해도 치명타."))
            elif avg_sc >= 4.3 and avg_ls >= 4.0 and tot_matches >= 5: titles.append(("💣 탑신병자 (유리대포)", "방어? 그게 뭐죠? 맞기 전에 찌르는 낭만파!"))
            elif avg_sc >= 4.2 and tot_matches >= 5: titles.append(("🗡️ 전장의 여포", f"매 경기 {avg_sc:.1f}점을 꽂아넣는 폭격기."))
            if avg_sc == 5.0 and tot_matches >= 3: titles.append(("⚡ 원펀맨", "출전한 모든 경기에서 5점을 꽉 채운 미친 공격력!"))

            if 0 < avg_ls <= 1.0 and tot_matches >= 5: titles.append(("❄️ 절대영도 (A.T.필드)", f"평균 {avg_ls:.1f}실점! 뚫는 것이 물리적으로 불가능."))
            elif 0 < avg_ls <= 1.5 and tot_matches >= 5: titles.append(("🧱 비브라늄 방패", f"평균 {avg_ls:.1f}실점! 캡틴 아메리카도 울고 갈 우주 방어."))
            elif 0 < avg_sc <= 2.5 and 0 < avg_ls <= 2.5 and tot_matches >= 5: titles.append(("🐢 늪지대 장인 (가시갑옷)", "극한의 짠물 펜싱."))
            elif avg_ls >= 4.5 and tot_matches >= 5: titles.append(("💸 자선사업가 (자동문)", "수비가 너무 후한 나머지 점수를 마구 베풉니다."))

            # [세이버메트릭스 연동 칭호 조건 완화 적용 (V30)]
            if pythagorean >= 75: titles.append(("📐 피타고라스의 악마", "기대 승률 75% 이상. 완벽한 지표의 소유자."))
            if luck_index >= 15: titles.append(("🍀 럭키 가이 (클러치)", "실력 지표보다 실제 승률이 훨씬 높은 기적의 사나이."))
            if luck_index <= -15: titles.append(("☔ 억까의 아이콘", "지표는 깡패인데 승운이 안 따름. 조만간 떡상 예정."))
            if dom_rate >= 80 and tot_wins >= 5: titles.append(("🚀 학살자 (TDR)", "진땀승 따윈 없다. 오직 완벽한 완승뿐!"))
            # 🔥 여기서도 새가슴 기준 상향
            if choke_index is not None and choke_index >= 30 and main_advances >= 3: titles.append(("🥶 본선 자동문 (새가슴)", "예선은 여포인데, 토너먼트만 가면 다리가 굳음."))
            if choke_index is not None and choke_index <= -20 and main_advances >= 3: titles.append(("🥷 다크템플러", "본선만 가면 눈빛이 바뀌는 토너먼트의 암살자."))

            # [클러치 & 연령 / 대진운 / 짬바 (V29)]
            if up_cnt >= 8: titles.append(("🏴‍☠️ 혁명군 수장 (드래곤)", "업셋 8회 이상! 시드 체계를 완벽히 붕괴시키는 파괴자."))
            elif up_cnt >= 4: titles.append(("🪓 자이언트 킬러", f"본선에서 상위 시드를 {up_cnt}번이나 썰어버림."))
            if sweats >= 10: titles.append(("🥶 얼음 심장 (타짜)", f"1점 차 진땀승만 {sweats}번. 심박수가 변하지 않는 멘탈 갑."))
            
            if tot_matches >= 150: titles.append(("🦾 사이버네틱 펜서", "예선 150경기 소화! 펜싱 기계 그 자체."))
            # 🔥 에러가 나던 변수명 `num_tourneys`를 `tot_tournaments`로 고쳤습니다.
            elif tot_tournaments >= 15: titles.append(("🏛️ 살아있는 화석 (고인물)", f"{tot_tournaments}번 대회 개근! 클럽 역사의 산증인."))
            
            if avg_luck >= 42 and tot_tournaments >= 2: titles.append(("☠️ 억까의 신", f"평균 대진운 {avg_luck:.1f}pt. 왜 나한테만 우승후보가 걸리는가?"))
            elif avg_luck <= 15 and tot_tournaments >= 2: titles.append(("🍯 양봉업자 (꿀대진)", f"평균 대진운 {avg_luck:.1f}pt. 꿀대진 냄새를 기가 막히게 맡습니다."))
            if p_loss >= 40: titles.append(("🔥 칠전팔기 불사조 (중꺾마)", "40번을 져도 절대 검을 놓지 않는 불굴의 의지. 리스펙트!"))
            if p_win == 0 and tot_tournaments >= 3: titles.append(("😭 영고라인", "아직 공식전 첫 승의 기쁨을 누리지 못했습니다... 파이팅!"))
            if tot_tournaments == 1: titles.append(("🐣 삐약이 (뉴비)", "이제 막 첫발을 내디딘 루키! 앞날을 응원합니다."))

            if age_group == "초등부" and golds >= 1: titles.append(("👶 언터쳐블 신동", "어린 나이에 우승을 차지한 될성부른 떡잎."))
            if age_group == "초등부" and pass_rate == 100: titles.append(("🚀 미래의 국대", "출전만 하면 본선에 직행하는 영재."))
            if age_group == "일반부" and tot_pt >= 300: titles.append(("👔 직장인 소드마스터", "야근을 뚫고 쟁취한 피땀 눈물의 랭커!"))

            if len(titles) == 0: titles.append(("👤 묵묵한 검사", "자신만의 길을 걷고 있는 성실한 펜서."))

            st.markdown("#### 🏆 획득한 특수 칭호 보드 (업적)")
            t_col1, t_col2 = st.columns(2)
            for i, (t, desc) in enumerate(titles):
                col = t_col1 if i % 2 == 0 else t_col2
                col.markdown(f"<div style='padding:12px; background-color:#2a2a2a; border-radius:8px; margin-bottom:8px; border-left:4px solid {t_color};'><b>{t}</b><br><span style='color:#aaaaaa; font-size:13px;'>{desc}</span></div>", unsafe_allow_html=True)
            
            # --- 💡 V29 기초 스탯 보드 및 상세 기록 표 복구 ---
            st.divider()
            st.markdown("#### 📊 누적 스탯 보드 및 대회별 상세 기록")
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("총 출전 대회", f"{tot_tournaments}회")
            b2.metric("누적 레이팅", f"{tot_pt:.0f} PT")
            b3.metric("예선 누적 전적", f"{int(p_win)}승 {int(p_loss)}패")
            b4.metric("커리어 하이 (최고 순위)", f"{best_r:.0f}위" if pd.notna(best_r) and best_r > 0 else "-")

            def g_luck(pt):
                if pt >= 40: return f"💀 지옥 뿔 ({pt:.1f}pt)"
                if pt >= 25: return f"⚔️ 험난 뿔 ({pt:.1f}pt)"
                if pt >= 15: return f"😐 평이 ({pt:.1f}pt)"
                return f"🍯 꿀통 뿔 ({pt:.1f}pt)"
            p_data['대진운'] = [g_luck(x) for x in luck_l]
            
            st.dataframe(p_data[['대회일자', '대회명', '부수', '예선_승률(%)', '예선_랭킹', '본선_랭킹', '레이팅(PT)', '대진운']].sort_values('대회일자', ascending=False), use_container_width=True, hide_index=True)

            # --- V30 선수 개인 방명록 ---
            st.divider()
            st.markdown(f"### 💬 {sel_player.split(' (')[0]} 선수 개인 팬명록 (방명록)")
            player_comments = st.session_state.comment_db[st.session_state.comment_db['대상선수'] == sel_player]
            if not player_comments.empty:
                for _, row in player_comments.sort_values(by='작성일시', ascending=False).iterrows():
                    st.markdown(f"<div style='background-color:#1e1e1e; padding:12px; border-left:4px solid {t_color}; border-radius:5px; margin-bottom:8px;'><b>{row['작성자']}</b> <span style='font-size:12px;color:#888;'>({row['작성일시']})</span><br><span style='color:#ddd; font-size:15px;'>{row['내용']}</span></div>", unsafe_allow_html=True)
            else:
                st.info("선수에게 따뜻한 응원 코멘트를 남겨주세요!")
            
            with st.form("player_comment_form", clear_on_submit=True):
                c_c1, c_c2 = st.columns([1, 4])
                with c_c1: author = st.text_input("닉네임", placeholder="무명검객")
                with c_c2: comment_text = st.text_input("코멘트 남기기", placeholder="이번 대회 폼 미쳤다!! 화이팅!!")
                if st.form_submit_button("📝 선수 코멘트 등록") and comment_text.strip():
                    new_c = pd.DataFrame([{"대상선수": sel_player, "작성자": author if author else "익명", "내용": comment_text, "작성일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    st.session_state.comment_db = pd.concat([st.session_state.comment_db, new_c], ignore_index=True)
                    st.session_state.comment_db.to_csv(COMMENT_DB_FILE, index=False, encoding='utf-8-sig')
                    st.rerun()

# ================= TAB 4: 육각형 스탯 & 폼 분석 =================
with tabs[4]:
    st.subheader("💠 육각형(Hexagon) 스탯 레이더 & 폼 트렌드")
    if not global_db.empty:
        # --- 💡 V29의 3단계 필터 완벽 적용 ---
        col1, col2, col3 = st.columns(3)
        with col1: sel_div_t4 = st.selectbox("1. 대분류 (부수)", ["전체"] + sorted(list(global_db['부수'].dropna().unique())), key="d4")
        with col2:
            db_t4 = global_db if sel_div_t4 == "전체" else global_db[global_db['부수'] == sel_div_t4]
            sel_team_t4 = st.selectbox("2. 중분류 (소속팀)", ["전체"] + sorted(list(db_t4['소속팀'].dropna().unique())), key="t4")
        with col3:
            if sel_team_t4 != "전체": db_t4 = db_t4[db_t4['소속팀'] == sel_team_t4]
            sel_hex_player = st.selectbox("3. 선수 선택 (육각형 차트)", ["선택"] + sorted(list(db_t4['고유이름'].dropna().unique())), key="hex_player")

        if sel_hex_player != "선택":
            p_h = global_db[global_db['고유이름'] == sel_hex_player]
            m_h = global_match[global_match['기준_고유'] == sel_hex_player]
            t_m = p_h['예선_승'].sum() + p_h['예선_패'].sum()
            
            s_atk = min(((p_h['예선_득점'].sum() / t_m if t_m>0 else 0) / 5.0) * 100, 100)
            s_def = max(100 - (((p_h['예선_실점'].sum() / t_m if t_m>0 else 5.0) / 5.0) * 100), 0)
            s_win = p_h['예선_승률(%)'].mean() if len(p_h) > 0 else 0
            s_exp = min((t_m / 50.0) * 100, 100)
            up_c = len(m_h[(m_h['단계'] == '본선') & (m_h['승패'] == '승') & (m_h['업셋여부'] == 'Y')])
            sweats_h = len(m_h[(m_h['단계'] == '예선') & (m_h['진땀승'] == 'Y')])
            s_clu = min(((up_c * 2 + sweats_h) / max(len(p_h), 1)) * 20, 100)
            
            all_pts_hex = global_db.groupby('고유이름')['레이팅(PT)'].mean()
            luck_list = []
            for tn in p_h['대회명']:
                opps = m_h[(m_h['단계']=='예선') & (m_h['대회명']==tn)]['상대_고유']
                if len(opps) > 0: luck_list.append(opps.map(all_pts_hex).fillna(5).mean())
            avg_luck = sum(luck_list)/len(luck_list) if luck_list else 15.0
            s_luck = min((avg_luck / 40.0) * 100, 100)

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[s_atk, s_def, s_win, s_exp, s_clu, s_luck, s_atk],
                theta=['공격력', '방어력', '결정력(승률)', '경험치', '클러치', '대진증명력', '공격력'],
                fill='toself', fillcolor='rgba(0, 191, 255, 0.5)', line=dict(color='#00bfff', width=2),
                name=sel_hex_player.split(' (')[0]
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white', size=14))
            
            c_chart, c_desc = st.columns([3, 2])
            with c_chart: st.plotly_chart(fig, use_container_width=True)
            with c_desc:
                st.markdown(f"### 📌 {sel_hex_player.split(' (')[0]} 스카우팅 리포트")
                st.info(f"**⚔️ 공격력 ({s_atk:.0f}/100)**: 평균 {p_h['예선_득점'].sum() / t_m if t_m>0 else 0:.1f} 득점")
                st.info(f"**🛡️ 방어력 ({s_def:.0f}/100)**: 평균 {p_h['예선_실점'].sum() / t_m if t_m>0 else 5.0:.1f} 실점")
                st.info(f"**👑 결정력 ({s_win:.0f}/100)**: 예선 승률 {s_win:.1f}%")
                st.info(f"**💪 경험치 ({s_exp:.0f}/100)**: 공식 예선 {int(t_m)}전")
                st.info(f"**💦 클러치 ({s_clu:.0f}/100)**: 접전승/업셋 지수")
                st.info(f"**🍀 대진운 ({s_luck:.0f}/100)**: 헬대진 극복 지수")

            st.divider()
            st.markdown("#### 📈 대회별 폼(Form) 트렌드 (승률 변화)")
            trend_df = p_h[['대회일자', '대회명', '예선_승률(%)']].sort_values('대회일자').dropna(subset=['대회일자'])
            if len(trend_df) >= 2:
                trend_df['대회정보'] = trend_df['대회명'] + " (" + trend_df['대회일자'].dt.strftime('%y.%m.%d') + ")"
                st.line_chart(trend_df.set_index('대회정보')['예선_승률(%)'], use_container_width=True)
            else:
                st.warning("대회 트렌드 그래프를 생성하려면 최소 2번 이상의 대회 출전 기록이 필요합니다.")

# ================= TAB 5: 1:1 라이벌 비교 =================
with tabs[5]:
    st.subheader("⚔️ 1:1 라이벌 정밀 비교 & AI 가상 승부 예측")
    if not global_db.empty:
        # --- 💡 V29의 선수별 3단계 분리 필터 완벽 적용 ---
        c1, c2 = st.columns(2)
        with c1: 
            st.markdown("#### 🔴 선수 A 선택")
            sel_d_a = st.selectbox("1. A 대분류", ["전체"] + sorted(list(global_db['부수'].dropna().unique())), key="da")
            db_a = global_db if sel_d_a == "전체" else global_db[global_db['부수'] == sel_d_a]
            sel_t_a = st.selectbox("2. A 클럽", ["전체"] + sorted(list(db_a['소속팀'].dropna().unique())), key="ta")
            if sel_t_a != "전체": db_a = db_a[db_a['소속팀'] == sel_t_a]
            pA = st.selectbox("3. 🔴 선수 A", ["선택"] + sorted(list(db_a['고유이름'].dropna().unique())), key="pa")

        with c2: 
            st.markdown("#### 🔵 선수 B 선택")
            sel_d_b = st.selectbox("1. B 대분류", ["전체"] + sorted(list(global_db['부수'].dropna().unique())), key="db")
            db_b = global_db if sel_d_b == "전체" else global_db[global_db['부수'] == sel_d_b]
            sel_t_b = st.selectbox("2. B 클럽", ["전체"] + sorted(list(db_b['소속팀'].dropna().unique())), key="tb")
            if sel_t_b != "전체": db_b = db_b[db_b['소속팀'] == sel_t_b]
            pB = st.selectbox("3. 🔵 선수 B", ["선택"] + sorted(list(db_b['고유이름'].dropna().unique())), key="pb")
        
        st.divider()

        if pA != "선택" and pB != "선택":
            if pA == pB:
                st.warning("같은 선수를 선택했습니다. 다른 선수를 골라주세요!")
            else:
                h2h = global_match[(global_match['기준_고유'] == pA) & (global_match['상대_고유'] == pB)]
                
                ageA = get_age_group(global_db[global_db['고유이름']==pA]['부수'].iloc[-1])
                ageB = get_age_group(global_db[global_db['고유이름']==pB]['부수'].iloc[-1])
                intro_ment = "물러설 수 없는 자존심 매치!"
                if ageA == "초등부" and ageB == "초등부": intro_ment = "미래 국가대표들의 불꽃 튀는 펜싱 신동 매치! 🚀"
                elif ageA == "일반부" and ageB == "일반부": intro_ment = "퇴근 후 펜싱에 미친 두 마스터의 진검승부! ⚔️"
                elif ageA != ageB: intro_ment = f"{ageA}의 패기 vs {ageB}의 관록, 세대를 뛰어넘는 승부!"
                
                st.markdown(f"<h3 style='text-align: center;'>🥊 {intro_ment}</h3>", unsafe_allow_html=True)
                
                if not h2h.empty:
                    # --- 💡 V29의 예선/본선 스코어 분리 및 상세표 복구 ---
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
                    
                    df_h2h = h2h[['대회일자', '대회명', '단계', '승패']].rename(columns={'승패':f'{pA.split(" (")[0]} 기준 결과'}).sort_values('대회일자', ascending=False).reset_index(drop=True)
                    df_h2h[f'{pA.split(" (")[0]} 기준 결과'] = df_h2h[f'{pA.split(" (")[0]} 기준 결과'].apply(lambda x: f"🔴 {pA.split(' (')[0]} 승리" if x == '승' else f"🔵 {pB.split(' (')[0]} 승리")
                    st.dataframe(df_h2h, use_container_width=True, hide_index=True)
                else:
                    st.info("💡 공식 맞대결 기록이 없습니다. AI가 누적 스탯을 기반으로 가상 시뮬레이션을 진행합니다! 🤖")
                    
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
                    
                    if a_clutch + a_up > b_clutch + b_up + 2: comments.append(f"💦 **클러치 상황:** 1점 차 피말리는 접전 승부로 간다면 강심장인 🔴 **{pA.split(' (')[0]}** 선수의 집중력이 빛을 발할 확률이 높습니다.")
                    elif b_clutch + b_up > a_clutch + a_up + 2: comments.append(f"💦 **클러치 상황:** 1점 차 피말리는 접전 승부로 간다면 강심장인 🔵 **{pB.split(' (')[0]}** 선수의 집중력이 빛을 발할 확률이 높습니다.")

                    st.markdown("#### 💡 AI 해설위원 관전 포인트")
                    for c in comments: st.write(f"- {c}")

# ================= TAB 6: 다자간 시뮬레이터 =================
with tabs[6]:
    st.subheader("🔮 다음 대회 예측 시뮬레이터 (멀티 체크박스 선택)")
    st.markdown("출전 선수들을 클릭해서 체크 박스로 자유롭게 담아보세요. 상성 관계를 즉시 분석합니다.")
    if not global_db.empty:
        all_players_list = sorted(list(global_db['고유이름'].dropna().unique()))
        
        selected_names = st.multiselect("✅ 대회 출전 선수 명단 선택 (이름 검색 가능)", all_players_list)
        
        if st.button("🚀 천적 상성 및 예상 성적 분석 가동"):
            if selected_names:
                sim_db = global_db[global_db['고유이름'].isin(selected_names)]
                if not sim_db.empty:
                    rel_m = global_match[global_match['기준_고유'].isin(selected_names) & global_match['상대_고유'].isin(selected_names)]
                    
                    alerts = []
                    for pn in selected_names:
                        pm = rel_m[rel_m['기준_고유'] == pn]
                        for on in pm['상대_고유'].unique():
                            h = pm[pm['상대_고유'] == on]
                            l = len(h[h['승패'] == '패'])
                            w = len(h[h['승패'] == '승'])
                            if w == 0 and l >= 1:
                                alerts.append(f"🚨 **비상! [{pn.split(' (')[0]}]** 선수의 무상성 극상성 천적 **[{on.split(' (')[0]}]** 출전! (상대전적 {l}전 전패)")
                    
                    if alerts:
                        for a in list(set(alerts)): st.error(a)
                    else: 
                        st.success("✨ 선택된 인원들 사이에는 절대적인 천적(전패) 관계가 존재하지 않습니다. 당일 컨디션 승부입니다!")
                    
                    st.markdown("#### 📊 누적 체급(PT) 기반 파워 시드 예상 랭킹")
                    
                    # --- 💡 V29의 대진운(Luck) 로직을 시뮬레이터 풀에 맞게 적용 ---
                    all_pts_sim = global_db.groupby('고유이름')['레이팅(PT)'].mean()
                    def calc_luck(pn):
                        opps_in_sim = [n for n in selected_names if n != pn]
                        if not opps_in_sim: return "평이"
                        avg_pt = sum(all_pts_sim.get(o, 20) for o in opps_in_sim) / len(opps_in_sim)
                        if avg_pt >= 40: return f"💀 지옥 ({avg_pt:.1f}pt)"
                        if avg_pt >= 25: return f"⚔️ 험난 ({avg_pt:.1f}pt)"
                        if avg_pt >= 15: return f"😐 평이 ({avg_pt:.1f}pt)"
                        return f"🍯 꿀통 ({avg_pt:.1f}pt)"

                    ss = sim_db.groupby('고유이름').agg(누적PT=('레이팅(PT)', 'sum'), 승률=('예선_승률(%)', 'mean')).reset_index()
                    ss['예상대진운'] = ss['고유이름'].apply(calc_luck)
                    ss = ss.sort_values(by=['누적PT', '승률'], ascending=[False, False]).reset_index(drop=True)
                    ss.index += 1
                    st.dataframe(ss, column_config={
                        "고유이름": "참가선수 (소속)",
                        "누적PT": st.column_config.NumberColumn("누적 레이팅", format="%.1f pt"),
                        "승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%")
                    }, use_container_width=True)
            else:
                st.warning("선수를 명단에서 선택해 주세요.")

# ================= TAB 7: 관리자 설정 (업로드 및 일정) =================
with tabs[7]:
    st.subheader("⚙️ 데이터 관리 센터 (관리자 전용)")
    if not st.session_state.admin_auth:
        st.error("🔒 이 탭은 대회 일정을 등록하고 새로운 엑셀 성적을 시스템에 올리는 클럽 코치진 전용 구역입니다.")
        st.info("좌측 사이드바에서 비밀번호를 입력해야 모든 관리 메뉴가 나타납니다.")
    else:
        st.success("🔓 관리자 권한 활성화 됨 (대회 일정 및 성적 관리가 가능합니다.)")
        
        # 1. 일정 관리
        st.markdown("#### 📅 윈펜싱 대회 일정표 등록")
        with st.form("sch_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1: s_date = st.date_input("대회 일자")
            with col2: s_name = st.text_input("대회명")
            with col3: s_loc = st.text_input("장소")
            with col4: s_note = st.text_input("비고 (신청 마감 등)")
            
            if st.form_submit_button("일정표에 추가하기") and s_name:
                new_sch = pd.DataFrame([{"대회일자": str(s_date), "대회명": s_name, "장소": s_loc, "비고": s_note}])
                st.session_state.schedule_db = pd.concat([st.session_state.schedule_db, new_sch], ignore_index=True)
                st.session_state.schedule_db.to_csv(SCHEDULE_DB_FILE, index=False, encoding='utf-8-sig')
                st.success("대회 일정이 등록되었습니다!"); st.rerun()

        st.divider()

        # 2. 성적 업로드
        st.markdown("#### 📂 대회 성적 엑셀 일괄 업로드")
        col1, col2 = st.columns(2)
        with col1: tourney_name = st.text_input("대회명 (파일 이름에 없을 경우 수동입력)")
        with col2: tourney_date = st.date_input("대회 일자 (파일 이름에 없을 경우)")
            
        uploaded_files = st.file_uploader("원본 엑셀 파일(.xlsx) 다중 업로드", type=['xlsx'], accept_multiple_files=True)
        
        if st.button("데이터베이스에 업로드 및 추가하기"):
            if uploaded_files:
                new_players, new_matches = [], []
                
                # --- 기존 V29의 완벽한 엑셀 파싱 로직 ---
                def get_num(text):
                    if pd.isna(text) or str(text).strip() == "": return None
                    nums = re.findall(r'\d+', str(text))
                    return int(nums[0]) if nums else None
                
                def get_pt(f_r, p_r):
                    t = get_num(f_r)
                    if t is None: t = get_num(p_r)
                    if t is None: return 5
                    if t == 1: return 100
                    elif t == 2: return 80
                    elif t in [3, 4]: return 60
                    elif 5 <= t <= 8: return 45  
                    elif 9 <= t <= 16: return 25 
                    elif 17 <= t <= 32: return 10 
                    else: return 5

                def get_rscore(rank):
                    if pd.isna(rank): return 0
                    if rank == 1: return 100
                    if rank == 2: return 90
                    if rank in [3, 4]: return 80
                    if 5 <= rank <= 8: return 70
                    if 9 <= rank <= 16: return 60
                    if 17 <= rank <= 32: return 50
                    return 0

                def format_val(x):
                    if pd.isna(x): return ""
                    v = str(x).strip()
                    if v.endswith('.0'): return v[:-2]
                    if ":" in v or "1900-" in v or "1899-" in v: return "0"
                    return v
                
                def get_bracket(n):
                    if n == 2: return [1, 2]
                    prev = get_bracket(n // 2)
                    b = []
                    for p in prev: b.extend([p, n + 1 - p])
                    return b

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
                        if not t_name: t_name = file_name_no_ext
                    
                    if not st.session_state.player_db.empty and t_name in st.session_state.player_db['대회명'].values:
                        st.warning(f"⚠️ '{t_name}' 대회는 이미 등록되어 있어 건너뜁니다.")
                        continue

                    try: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='calamine', header=None)
                    except: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl', header=None)

                    success_count += 1
                    for sheet_name, df in sheets.items():
                        if df.empty or "단체" in sheet_name or "단체" in t_name: continue 
                        all_rows = [[format_val(x) for x in row.values] for _, row in df.iterrows()]
                        
                        parsed_players, valid_names = {}, {}
                        bracket_players = set()
                        in_pool, col_map = False, {}
                        pool_blocks, curr_pool = [], []
                        
                        for r in all_rows:
                            j = "".join(r).replace(" ", "")
                            c_str = [str(x).replace(" ", "") for x in r]
                            
                            if 'No' in c_str and '이름' in c_str and '소속팀' in c_str:
                                if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool}); curr_pool = []
                                in_pool, col_map = True, {n: i for i, n in enumerate(c_str) if n != ""}
                                continue
                            if "최종순위" in j or "뿔랭킹" in j or "최종랭킹" in j or "엘리미나시옹" in j or "8강전" in j or ("순위" in c_str and "이름" in c_str and "소속팀" in c_str) or ("랭킹" in c_str and "이름" in c_str):
                                if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool}); curr_pool = []
                                in_pool = False
                                
                            if in_pool:
                                n_idx, no_idx = col_map.get('이름'), col_map.get('No')
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
                                team1 = str(p1_r[cmap.get('소속팀')]).strip() if '소속팀' in cmap and cmap.get('소속팀') < len(p1_r) else ""
                                team1 = team1.replace('(사)부산펜싱클럽', '윈펜싱클럽').replace('부산펜싱클럽', '윈펜싱클럽').replace('(사)부산펜싱', '윈펜싱클럽')
                                
                                wins, v_matches, deuk, tight_wins = 0, 0, 0, 0
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
                                                wins += 1; m_dict[name2] = '승'
                                                s_num = get_num(sc)
                                                deuk += s_num if s_num is not None else 5
                                                if sc.upper() in ["V1", "V2", "V3", "V4"]: tight_wins += 1
                                            else: 
                                                m_dict[name2] = '패'
                                                s_num = get_num(sc)
                                                deuk += s_num if s_num is not None else 0
                                                
                                wr = round((wins / v_matches) * 100, 1) if v_matches > 0 else 0.0
                                parsed_players[name1] = {
                                    '대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '이름': name1, '소속팀': team1, 
                                    '예선_승': wins, '예선_패': v_matches - wins, '예선_승률(%)': wr, '예선_득점': deuk, '예선_실점': deuk - jisu, 
                                    '진땀승': tight_wins, '예선_랭킹': "기록없음", '본선_랭킹': "기록없음"
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
                                opp_team = str(t_dict.get(o_name, ""))
                                opp_team = opp_team.replace('(사)부산펜싱클럽', '윈펜싱클럽').replace('부산펜싱클럽', '윈펜싱클럽').replace('(사)부산펜싱', '윈펜싱클럽')
                                new_matches.append({
                                    '대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '기준선수': p['이름'], '기준팀': p['소속팀'], 
                                    '상대선수': o_name, '상대팀': opp_team, '승패': res, '단계': '예선', '업셋여부': 'N', '진땀승': 'Y' if res=='승' and parsed_players[p['이름']]['진땀승']>0 else 'N'
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
                    st.success(f"✅ 총 {success_count}개 대회 파일 데이터 파싱 및 저장 완료! 세이버메트릭스 지표 업데이트 성공!")
                    st.rerun()
            else:
                st.warning("엑셀 대회 파일들을 업로드해 주십시오.")
