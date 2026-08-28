import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import datetime
import random
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="윈펜싱클럽 전력 분석 V38.0", page_icon="🤺", layout="wide")

st.title("🤺 윈펜싱클럽 통합 데이터랩 (V38.0 직관성 패치)")
st.markdown("세이버메트릭스 해설/등급제 + 일정표 에디터 탑재 + 에러 완벽 픽스!")

# ================= 🗄️ 데이터베이스 및 기본 설정 =================
PLAYER_DB_FILE = "fencing_player_db.csv"
MATCH_DB_FILE = "fencing_match_db.csv"
COMMENT_DB_FILE = "fencing_comment_db.csv"
CLUB_COMMENT_DB_FILE = "fencing_club_comment_db.csv"
SCHEDULE_DB_FILE = "fencing_schedule_db.csv"
PROFILE_DB_FILE = "fencing_profile_db.csv"

# 🌟 관리자 인증 및 사이드바
if 'admin_auth' not in st.session_state:
    st.session_state.admin_auth = False

with st.sidebar:
    st.header("🔒 관리자 모드")
    if not st.session_state.admin_auth:
        with st.form("admin_login"):
            admin_pw = st.text_input("비밀번호 (업로드/일정/프로필 관리)", type="password")
            if st.form_submit_button("로그인 (Enter)"):
                if admin_pw == "win1205!":
                    st.session_state.admin_auth = True
                    st.success("✅ 관리자 권한 활성화!")
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("✅ 관리자로 접속 중입니다.")
        if st.button("로그아웃"):
            st.session_state.admin_auth = False
            st.rerun()
            
    st.divider()
    if st.session_state.admin_auth:
        st.warning("⚠️ 랭킹 꼬임 / 연도(2026) 버그 리셋 시")
        if st.button("🗑️ 성적 데이터 완전 초기화"):
            if os.path.exists(PLAYER_DB_FILE): os.remove(PLAYER_DB_FILE)
            if os.path.exists(MATCH_DB_FILE): os.remove(MATCH_DB_FILE)
            for key in ['player_db', 'match_db']:
                if key in st.session_state: del st.session_state[key]
            st.success("성적 리셋 완료! (프로필 및 일정표 유지) 엑셀을 다시 올리시면 정상 적용됩니다.")
            st.rerun()

# DB 로딩 함수
def load_db(file_name, default_cols=None):
    if os.path.exists(file_name): return pd.read_csv(file_name)
    return pd.DataFrame(columns=default_cols) if default_cols else pd.DataFrame()

if 'player_db' not in st.session_state: st.session_state.player_db = load_db(PLAYER_DB_FILE)
if 'match_db' not in st.session_state: st.session_state.match_db = load_db(MATCH_DB_FILE)
if 'comment_db' not in st.session_state: st.session_state.comment_db = load_db(COMMENT_DB_FILE, ["대상선수", "작성자", "내용", "작성일시"])
if 'club_comment_db' not in st.session_state: st.session_state.club_comment_db = load_db(CLUB_COMMENT_DB_FILE, ["대상클럽", "작성자", "내용", "작성일시"])
if 'schedule_db' not in st.session_state: st.session_state.schedule_db = load_db(SCHEDULE_DB_FILE, ["대회일자", "대회명", "장소", "비고"])
if 'profile_db' not in st.session_state: st.session_state.profile_db = load_db(PROFILE_DB_FILE, ["고유이름", "사진URL", "신장", "주사용손", "주특기", "한줄소개"])

global_db = st.session_state.player_db.copy()
global_match = st.session_state.match_db.copy()

if not global_match.empty:
    if '기준득점' not in global_match.columns: global_match['기준득점'] = "-"
    if '상대득점' not in global_match.columns: global_match['상대득점'] = "-"
    if '라운드' not in global_match.columns: global_match['라운드'] = global_match['단계']

def get_age_group(div_str):
    if pd.isna(div_str): return "일반부"
    d = str(div_str).replace(" ", "")
    if any(x in d for x in ["초", "U-9", "U-10", "U-11", "U-12", "U9", "U10", "U11", "U12", "유소년", "초등"]): return "초등부"
    if any(x in d for x in ["중", "고", "청소년", "U-14", "U-15", "U-17", "U14", "U15", "U17"]): return "중고등부"
    if any(x in d for x in ["일반", "대학", "엘리트", "성인", "마스터즈"]): return "일반부"
    return "통합부"

# 💡 [버그 픽스] 연도 2026 고정 버그 해결 (현재 연도로 자동 매핑)
current_yr = datetime.date.today().year

if not global_db.empty:
    global_db['소속팀'] = global_db['소속팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_db['대회일자'] = pd.to_datetime(global_db['대회일자'], errors='coerce')
    global_db['연도'] = global_db['대회일자'].dt.year.fillna(current_yr).astype(int).astype(str)
    global_db['나이대'] = global_db['부수'].apply(get_age_group)
    for col in ['본선_순위(숫자)', '예선_순위(숫자)', '레이팅(PT)', '예선_승률(%)', '예선_승', '예선_패', '예선_득점', '예선_실점']:
        if col not in global_db.columns: global_db[col] = 0
        global_db[col] = pd.to_numeric(global_db[col], errors='coerce').fillna(0)
    global_db['고유이름'] = global_db['이름'] + " (" + global_db['소속팀'].fillna("소속불명") + ")"

if not global_match.empty:
    global_match['기준팀'] = global_match['기준팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_match['상대팀'] = global_match['상대팀'].replace({'(사)부산펜싱클럽': '윈펜싱클럽', '부산펜싱클럽': '윈펜싱클럽', '(사)부산펜싱': '윈펜싱클럽'})
    global_match['대회일자'] = pd.to_datetime(global_match['대회일자'], errors='coerce')
    global_match['연도'] = global_match['대회일자'].dt.year.fillna(current_yr).astype(int).astype(str)
    global_match['기준_고유'] = global_match['기준선수'] + " (" + global_match['기준팀'].fillna("소속불명") + ")"
    global_match['상대_고유'] = global_match['상대선수'] + " (" + global_match['상대팀'].fillna("소속불명") + ")"

sel_year = "전체 (통산 누적)"

with st.sidebar:
    st.header("🔍 시즌제 통합 필터")
    if not global_db.empty:
        years_list = sorted(list(global_db['연도'].unique()), reverse=True)
        sel_year = st.selectbox("📅 시즌 (연도) 선택", ["전체 (통산 누적)"] + years_list)
        if sel_year != "전체 (통산 누적)":
            global_db = global_db[global_db['연도'] == sel_year]
            global_match = global_match[global_match['연도'] == sel_year]
            st.info(f"💡 현재 랭킹 및 티어는 **[{sel_year}년도]** 성적만으로 산출 중입니다.")
        else:
            st.info("💡 현재 랭킹 및 티어는 **역대 통산** 기록으로 산출 중입니다.")

# ================= 🎯 UI 탭 구성 =================
tabs = st.tabs([
    "📖 가이드/일정표", "🏆 종합 랭킹 보드", "🏢 클럽 명전/방명록", 
    "🎮 1인 통합분석 (스탯/칭호/대회뿔)", "⚔️ 1:1 라이벌 매치", "🔮 명단 시뮬레이터", "⚙️ 데이터 관리(엑셀)"
])

# ================= TAB 0: 가이드 & 일정표 =================
with tabs[0]:
    st.subheader("📖 윈펜싱 데이터랩 V38.0 직관성 완결판 패치 노트")
    st.markdown("""
    *   **📈 세이버메트릭스 시각화 완전 개편:** 알기 어렵던 그래프를 지우고, 게임 스탯창처럼 **"상위 15% (S급)"** 등을 직관적으로 알려주는 해설형 UI(등급 카드)로 전면 교체했습니다!
    *   **📅 일정표 에디터 탑재:** 관리자로 로그인 시, 이 화면에서 엑셀처럼 더블클릭하여 일정을 쉽게 추가, 수정, 삭제하고 바로 저장할 수 있습니다.
    *   **🐛 표 에러(TypeError) 완벽 해결:** 뿔(Poule) 테이블을 불러올 때 가끔 숫자가 문자열에 막혀 뻗어버리던 서버 에러를 안전한 데이터 포맷팅으로 원천 차단했습니다.
    """)
    st.divider()
    st.subheader("📅 연간 대회 및 행사 일정표")
    
    # 💡 [핵심 패치 1] 관리자 엑셀형 일정 에디터 도입
    if st.session_state.admin_auth:
        st.info("✏️ **[관리자 전용 에디터]** 아래 표 안의 글자를 더블클릭하여 수정하거나, 맨 아래 빈 줄에 일정을 추가하세요. 왼쪽 체크박스를 누르고 'Delete' 키를 누르면 행이 지워집니다.")
        edited_schedule = st.data_editor(st.session_state.schedule_db, num_rows="dynamic", use_container_width=True)
        if st.button("💾 일정표 변경사항 영구 저장"):
            st.session_state.schedule_db = edited_schedule
            st.session_state.schedule_db.to_csv(SCHEDULE_DB_FILE, index=False, encoding='utf-8-sig')
            st.success("✅ 일정이 성공적으로 저장되었습니다!")
            st.rerun()
    else:
        if not st.session_state.schedule_db.empty:
            st.dataframe(st.session_state.schedule_db.sort_values(by="대회일자"), use_container_width=True, hide_index=True)
        else:
            st.info("현재 등록된 일정이 없습니다.")

# ================= TAB 1: 종합 랭킹 =================
with tabs[1]:
    st.subheader(f"🏆 종합 랭킹 보드 {'['+sel_year+' 시즌]' if sel_year != '전체 (통산 누적)' else '[역대 통산 누적]'}")
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
    else:
        st.warning("등록된 데이터가 없습니다. 관리자 탭에서 엑셀을 업로드 해주세요.")

# ================= TAB 2: 클럽 분석 =================
with tabs[2]:
    st.subheader(f"🏢 클럽 정밀 분석 & 명예의 전당 ({sel_year} 기준)")
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

            wk = h_db.groupby('고유이름').agg(승률=('예선_승률(%)','mean'), 예선승=('예선_승','sum')).reset_index()
            wk = wk[wk['예선승'] >= 5].sort_values('승률', ascending=False).head(10)
            s3.info("🔥 **[최고 승률왕]**\n\n예선 승률 Top 10 (최소 5승)")
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

# ================= TAB 3: 1인 통합 개인 분석 =================
with tabs[3]:
    st.subheader(f"🎮 1인 통합 정밀 분석실 ({sel_year} 시즌 데이터)")
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
            
            valid_ranks = p_data[p_data['본선_순위(숫자)'] > 0]['본선_순위(숫자)']
            best_r = valid_ranks.min() if not valid_ranks.empty else None
            
            prof_df = st.session_state.profile_db[st.session_state.profile_db['고유이름'] == sel_player]
            p_img = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
            p_height, p_hand, p_skill, p_motto = "미입력", "미입력", "미입력", "펜싱을 즐기는 검객입니다."
            if not prof_df.empty:
                r = prof_df.iloc[-1]
                if pd.notna(r['사진URL']) and str(r['사진URL']).strip(): p_img = str(r['사진URL'])
                if pd.notna(r['신장']): p_height = str(r['신장'])
                if pd.notna(r['주사용손']): p_hand = str(r['주사용손'])
                if pd.notna(r['주특기']): p_skill = str(r['주특기'])
                if pd.notna(r['한줄소개']): p_motto = str(r['한줄소개'])

            st.markdown("---")
            col_img, col_info, col_hex = st.columns([1, 1.8, 2.2])
            with col_img:
                st.markdown(f"<div style='text-align:center;'><img src='{p_img}' style='width:100%; max-width:180px; border-radius:15px; border:3px solid #54c3a6; object-fit:cover;'></div>", unsafe_allow_html=True)
                if st.session_state.admin_auth:
                    with st.expander("⚙️ 프로필 수정"):
                        with st.form("profile_form"):
                            new_h = st.text_input("신장", value=p_height if p_height != "미입력" else "")
                            new_hand = st.text_input("주사용손", value=p_hand if p_hand != "미입력" else "")
                            new_skill = st.text_input("주특기", value=p_skill if p_skill != "미입력" else "")
                            new_img = st.text_input("사진 URL", value=p_img if "pixabay" not in p_img else "")
                            new_motto = st.text_input("한줄소개", value=p_motto if p_motto != "펜싱을 즐기는 검객입니다." else "")
                            if st.form_submit_button("프로필 저장"):
                                st.session_state.profile_db = st.session_state.profile_db[st.session_state.profile_db['고유이름'] != sel_player]
                                new_row = pd.DataFrame([{"고유이름": sel_player, "사진URL": new_img, "신장": new_h, "주사용손": new_hand, "주특기": new_skill, "한줄소개": new_motto}])
                                st.session_state.profile_db = pd.concat([st.session_state.profile_db, new_row], ignore_index=True)
                                st.session_state.profile_db.to_csv(PROFILE_DB_FILE, index=False, encoding='utf-8-sig')
                                st.rerun()

            QUAL_MATCHES = 10
            t_m_hex = p_data['예선_승'].sum() + p_data['예선_패'].sum()
            is_qual = t_m_hex >= QUAL_MATCHES

            with col_info:
                st.markdown(f"## 🤺 {sel_player.split(' (')[0]}")
                st.markdown(f"**소속팀:** {p_data['소속팀'].iloc[-1]} &nbsp;|&nbsp; **주 참가부수:** {p_data['부수'].iloc[-1]}")
                st.markdown(f"**📏 신장:** {p_height} &nbsp;|&nbsp; **🖐️ 주사용손:** {p_hand}")
                st.markdown(f"**⚔️ 주특기:** {p_skill}")
                st.info(f"💬 \"{p_motto}\"")

            with col_hex:
                avg_sc = p_data['예선_득점'].sum() / t_m_hex if t_m_hex > 0 else 0
                avg_ls = p_data['예선_실점'].sum() / t_m_hex if t_m_hex > 0 else 5.0
                win_rate = p_data['예선_승률(%)'].mean() if len(p_data) > 0 else 0
                
                s_atk = min(40 + (avg_sc / 5.0) * 60, 100) if t_m_hex > 0 else 40
                s_def = min(40 + ((5.0 - avg_ls) / 5.0) * 60, 100) if t_m_hex > 0 else 40
                s_win = min(40 + (win_rate * 0.6), 100) if t_m_hex > 0 else 40
                s_exp = min(40 + (t_m_hex * 2.0), 100) if t_m_hex > 0 else 40
                
                up_c = len(m_data[(m_data['단계'] == '본선') & (m_data['승패'] == '승') & (m_data['업셋여부'] == 'Y')])
                sweats_h = len(m_data[(m_data['단계'] == '예선') & (m_data['진땀승'] == 'Y')])
                s_clu = min(40 + (up_c * 15) + (sweats_h * 10), 100) if t_m_hex > 0 else 40
                
                all_pts_hex = global_db.groupby('고유이름')['레이팅(PT)'].mean()
                luck_list_h = [all_pts_hex.get(o, 5.0) for tn in p_data['대회명'] for o in m_data[(m_data['단계']=='예선') & (m_data['대회명']==tn)]['상대_고유']]
                avg_luck_h = sum(luck_list_h)/len(luck_list_h) if luck_list_h else 15.0
                s_luck = min(40 + (avg_luck_h / 30.0) * 60, 100) if t_m_hex > 0 else 40

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=[s_atk, s_def, s_win, s_exp, s_clu, s_luck, s_atk],
                    theta=['공격력(극딜)', '방어력(짠물)', '결정력(승률)', '경험치(짬바)', '클러치(위기극복)', '대진운(강적조우)', '공격력(극딜)'],
                    fill='toself', fillcolor='rgba(84, 195, 166, 0.4)', line=dict(color='#54c3a6', width=2),
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 100])), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white', size=12), margin=dict(t=20, b=20, l=20, r=20), height=250)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            all_pts = global_db.groupby('고유이름')['레이팅(PT)'].sum()
            my_pt = all_pts.get(sel_player, 0)
            pct = (all_pts > my_pt).mean() * 100 if len(all_pts) > 1 else 50.0
            
            def get_sub_tier(pct, matches, is_qual):
                if not is_qual: return "⚪ 언랭크 (배치 중)", "#888888", f"티어 배치를 위해 규정 경기 수({QUAL_MATCHES}전)를 채워주세요!"
                if pct <= 1: return "👑 레디언트", "#ff3333", "생태계 절대 지배자 (Top 1%)"
                if pct <= 5: return f"💎 챌린저 {int((pct-1.0001)//1.0)+1}", "#e0b0ff", f"압도적 무력의 강자 (Top {pct:.1f}%)"
                if pct <= 15: return f"🥇 마스터 {int((pct-5.0001)//2.5)+1}", "#ffd700", f"최상위권 단골 손님 (Top {pct:.1f}%)"
                if pct <= 30: return f"🥈 다이아몬드 {int((pct-15.0001)//3.75)+1}", "#b9f2ff", f"탄탄한 기본기를 자랑하는 강자 (Top {pct:.1f}%)"
                if pct <= 50: return f"🥉 플래티넘 {int((pct-30.0001)//5.0)+1}", "#54c3a6", f"허리를 든든하게 받쳐주는 엘리트 (Top {pct:.1f}%)"
                if pct <= 75: return f"🟡 골드 {int((pct-50.0001)//6.25)+1}", "#f2a900", f"폭풍 성장 중인 펜서 (Top {pct:.1f}%)"
                if pct <= 90: return f"⚪ 실버 {int((pct-75.0001)//3.75)+1}", "#cccccc", f"잠재력 100%의 루키 (Top {pct:.1f}%)"
                return "🟤 브론즈", "#8c7355", "위대한 여정의 시작!"

            t_name, t_color, t_desc = get_sub_tier(pct, t_m_hex, is_qual)
            year_notice = f"💡 **[{sel_year} 시즌]** 기록 기준 티어입니다." if sel_year != "전체 (통산 누적)" else "💡 **[역대 통산]** 기록 기준 티어입니다."

            if not is_qual and t_m_hex > 0:
                st.warning(f"⚠️ **[규정 경기 수 미달]** 현재 예선 {int(t_m_hex)}전 참여 (규정: {QUAL_MATCHES}전). 스탯 신뢰도가 낮아 고급 티어/칭호 획득이 제한됩니다.")

            st.markdown(f"""
            <div style="background-color:#1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 8px solid {t_color};">
                <h2 style="margin-top:0px; color: {t_color};">{t_name}</h2>
                <p style="font-size: 15px; color:#ddd; margin-bottom: 5px;">{t_desc}</p>
                <div style="width: 100%; background-color: #333; border-radius: 10px; height: 12px; margin-top: 10px;">
                    <div style="width: {100-pct if is_qual else 0}%; background-color: {t_color}; height: 100%; border-radius: 10px;"></div>
                </div>
                <div style="text-align:right; font-size:12px; color:#888; margin-top:5px;">선택 시즌 상위 {pct:.1f}% 위치 | {year_notice}</div>
            </div>
            """, unsafe_allow_html=True)

            # --- 💡 [핵심 패치 2] 세이버메트릭스 직관성 대개편 (S/A/B/C 등급 카드) ---
            st.markdown(f"#### 🔬 세이버메트릭스 심층 분석 리포트")
            st.info("💡 **그래프 대신 직관적인 해설을 제공합니다!** 전체 펜서(최소 5경기 출전자)의 통계를 바탕으로 우리 선수의 폼이 전체 생태계 중 어디에 속하는지 직관적인 등급(S/A/B/C)으로 해석해 줍니다.")
            
            tot_tournaments = len(p_data)
            tot_matches = p_data['예선_승'].sum() + p_data['예선_패'].sum()
            actual_wr = (p_data['예선_승'].sum() / tot_matches * 100) if tot_matches > 0 else 0
            
            tot_sc = p_data['예선_득점'].sum()
            tot_ls = p_data['예선_실점'].sum()
            
            denom = (tot_sc**2) + (tot_ls**2)
            pythagorean = ((tot_sc**2) / denom * 100) if denom > 0 else 50.0
            
            main_m = m_data[m_data['단계'] == '본선']
            main_total = len(main_m)
            
            if main_total > 0:
                raw_main_wr = (len(main_m[main_m['승패'] == '승']) / main_total * 100)
                expected_main_wr = actual_wr * 0.85 
                choke_index = expected_main_wr - raw_main_wr 
            else:
                raw_main_wr = None
                expected_main_wr = None
                choke_index = None
            
            tot_wins = p_data['예선_승'].sum()
            sweats = len(m_data[(m_data['단계']=='예선') & (m_data['진땀승']=='Y')])
            dom_rate = ((tot_wins - sweats) / tot_wins * 100) if tot_wins > 0 else 0.0

            # 전역 지표 산출 (퍼센타일 랭킹용)
            player_stats = []
            for p in global_db['고유이름'].unique():
                p_d = global_db[global_db['고유이름'] == p]
                m_d = global_match[global_match['기준_고유'] == p]
                
                tw = p_d['예선_승'].sum()
                tl = p_d['예선_패'].sum()
                tm = tw + tl
                if tm < 5: continue
                    
                tsc = p_d['예선_득점'].sum()
                tls = p_d['예선_실점'].sum()
                d_denom = (tsc**2) + (tls**2)
                p_pyth = (tsc**2)/d_denom * 100 if d_denom > 0 else 50.0
                
                p_sweats = len(m_d[(m_d['단계']=='예선') & (m_d['진땀승']=='Y')])
                p_dom = ((tw - p_sweats) / tw * 100) if tw > 0 else 0.0
                
                p_main_m = m_d[m_d['단계'] == '본선']
                p_mtot = len(p_main_m)
                p_wr = (tw/tm)*100 if tm > 0 else 0.0
                if p_mtot > 0:
                    p_raw_m_wr = (len(p_main_m[p_main_m['승패']=='승']) / p_mtot * 100)
                    p_choke = (p_wr * 0.85) - p_raw_m_wr
                else:
                    p_choke = np.nan
                    
                p_advances = len(p_d[(p_d['본선_랭킹'].notna()) & (p_d['본선_랭킹'] != "예선탈락") & (p_d['본선_랭킹'] != "기록없음")])
                p_pass_rate = (p_advances / len(p_d) * 100) if len(p_d) > 0 else 0.0
                
                player_stats.append({'uid': p, 'pyth': p_pyth, 'dom': p_dom, 'choke': p_choke, 'pass': p_pass_rate})

            ps_df = pd.DataFrame(player_stats)
            
            def get_top_percentile(val, series, higher_is_better=True):
                if len(series) == 0: return 50.0
                if higher_is_better: return (series > val).mean() * 100
                else: return (series < val).mean() * 100

            def render_metric_card(title, value_str, pct, desc, is_na=False):
                if is_na:
                    return f"""
                    <div style="background-color:#1e1e1e; border-left: 5px solid #555; border-radius:8px; padding:15px; margin-bottom:15px;">
                        <h4 style="margin:0; color:#aaa;">{title} : {value_str}</h4>
                        <p style="color:#888; font-size:14px; margin-top:5px; margin-bottom:0;">{desc}<br>기록이 부족하여 전체 유저와 비교할 수 없습니다.</p>
                    </div>
                    """
                    
                pct = max(0.1, min(99.9, pct)) # 0이나 100 방지
                if pct <= 15:
                    level_text = f"상위 {pct:.1f}% (S급 - 최상위권)"
                    color = "#54c3a6" # Green
                    bar_w = 100 - pct
                elif pct <= 40:
                    level_text = f"상위 {pct:.1f}% (A급 - 우수)"
                    color = "#54c3a6" # Green
                    bar_w = 100 - pct
                elif pct <= 70:
                    level_text = f"하위 {100-pct:.1f}% (B급 - 평균)"
                    color = "#f2a900" # Yellow
                    bar_w = 100 - pct
                else:
                    level_text = f"하위 {100-pct:.1f}% (C급 - 보완필요)"
                    color = "#ff6666" # Red
                    bar_w = 100 - pct
                    
                return f"""
                <div style="background-color:#1e1e1e; border-left: 5px solid {color}; border-radius:8px; padding:15px; margin-bottom:15px;">
                    <h4 style="margin:0; color:{color};">{title} : {value_str}</h4>
                    <p style="color:#ddd; font-size:14px; margin-top:5px; margin-bottom:10px;">{desc}<br><span style="color:{color}; font-weight:bold;">➔ 전체 펜서 중 {level_text} 수준입니다.</span></p>
                    <div style="width:100%; background-color:#333; border-radius:5px; height:12px;">
                        <div style="width:{bar_w}%; background-color:{color}; height:100%; border-radius:5px;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#888; margin-top:5px;">
                        <span>C급 (하위권)</span>
                        <span>S급 (최상위권)</span>
                    </div>
                </div>
                """
                
            pct_pyth = get_top_percentile(pythagorean, ps_df['pyth'], True) if not ps_df.empty else 50.0
            pct_dom = get_top_percentile(dom_rate, ps_df['dom'], True) if not ps_df.empty else 50.0
            valid_choke = ps_df['choke'].dropna()
            pct_choke = get_top_percentile(choke_index, valid_choke, False) if choke_index is not None and not valid_choke.empty else 50.0
            
            main_advances = len(p_data[(p_data['본선_랭킹'].notna()) & (p_data['본선_랭킹'] != "예선탈락") & (p_data['본선_랭킹'] != "기록없음")])
            pass_rate = (main_advances / tot_tournaments * 100) if tot_tournaments > 0 else 0.0
            pct_pass = get_top_percentile(pass_rate, ps_df['pass'], True) if not ps_df.empty else 50.0

            st.markdown(render_metric_card(
                "🏁 예선 ➡ 본선 통과율", 
                f"{pass_rate:.1f}%", 
                pct_pass, 
                "출전한 대회 중 조별 예선을 통과하여 본선 토너먼트에 진출한 비율입니다.",
                is_na=(tot_tournaments==0)
            ), unsafe_allow_html=True)

            st.markdown(render_metric_card(
                "⚔️ 기대 승률 (순수 경기력)", 
                f"{pythagorean:.1f}%", 
                pct_pyth, 
                "운이나 요행을 제외하고, 득점과 실점의 비율로만 계산한 '통계적인 진짜 기본기'입니다.",
                is_na=(tot_matches==0)
            ), unsafe_allow_html=True)
            
            st.markdown(render_metric_card(
                "🥶 새가슴 지수 (15점 본선 멘탈)", 
                f"{choke_index:+.1f}%p" if choke_index is not None else "N/A", 
                pct_choke, 
                "15점제 단판 승부에서 예선만큼 실력을 발휘하는지 나타냅니다. 양수(+)면 본선에서 얼어붙는 새가슴, 음수(-)면 본선 무대 체질(강심장)을 뜻합니다.",
                is_na=(choke_index is None)
            ), unsafe_allow_html=True)
            
            st.markdown(render_metric_card(
                "🚀 경기 압도율 (완승 비율)", 
                f"{dom_rate:.1f}%", 
                pct_dom, 
                "이긴 경기 중에서 1점 차의 피말리는 접전(진땀승)을 제외하고, 상대를 넉넉한 점수 차로 여유롭게 완파한 비율입니다.",
                is_na=(tot_wins==0)
            ), unsafe_allow_html=True)

            st.divider()

            # --- 🤖 AI 리포트 ---
            st.markdown("#### 🤖 AI 스카우터 리포트")
            avg_sc_ai = tot_sc / (tot_matches if tot_matches else 1)
            avg_ls_ai = tot_ls / (tot_matches if tot_matches else 1)
            avg_margin = (tot_sc - tot_ls) / tot_matches if tot_matches > 0 else 0
            
            if is_qual:
                if avg_margin >= 3.0: l1 = f"평균 득실 마진 +{avg_margin:.1f}점! 상대를 압도하는 파괴적인 공격력과 단단한 방어를 동시에 갖춘 폭군입니다."
                elif avg_margin >= 1.5: l1 = f"마진 +{avg_margin:.1f}점의 안정적인 경기력. 공수 밸런스가 뛰어나 수비하기 까다로운 템포를 지니고 있습니다."
                elif avg_sc_ai >= 4.2: l1 = f"평균 {avg_sc_ai:.1f}점을 쓸어담는 화끈한 공격수! 수비는 잊어라! 맞기 전에 먼저 찌르는 낭만파입니다."
                elif avg_ls_ai <= 2.2: l1 = f"평균 실점이 단 {avg_ls_ai:.1f}점! 예리한 칼끝도 뚫어내기 힘든 늪지대 방어력을 자랑합니다."
                elif avg_margin < -1.5: l1 = f"아직 득실 마진에서는 고전하고 있으나, 특유의 변칙적인 템포는 상대를 당황시키기에 충분합니다."
                else: l1 = "공격과 수비의 밸런스를 유지하며, 어떤 상황에서도 유연하게 대처하는 능력을 지녔습니다."
                
                luck_index = actual_wr - pythagorean 
                if luck_index >= 10: l2 = f"기대 승률({pythagorean:.1f}%)보다 실제 승률({actual_wr:.1f}%)이 더 높습니다! 접전에서 승리를 훔쳐오는 엄청난 클러치의 소유자."
                elif luck_index <= -15: l2 = "스탯 내용은 훌륭하나 지독하게 승운이 따르지 않는 비운의 에이스. 억까를 이겨내면 성적이 폭발할 것입니다."
                elif choke_index is not None and choke_index <= -15: l2 = "예선에서는 힘을 빼고 있다가 토너먼트에 진입하면 오히려 폼이 올라가는 '본선 여포' 기질이 다분합니다."
                elif choke_index is not None and choke_index >= 15: l2 = "압도적인 예선 폼에 비해 15점제 본선 성적이 아쉽습니다. 체력 안배와 집중력만 보완한다면 우승권 텐션입니다."
                else: l2 = "매 경기 기복 없이 자신만의 확고한 템포로 묵묵하게 검을 휘두르는 안정적인 멘탈의 소유자입니다."
            else:
                l1 = f"공식 기록이 {tot_matches}전으로 아직 데이터가 부족하여 AI 전투력 평가가 보류되었습니다."
                l2 = "앞으로 대회를 더 출전하여 자신만의 데이터를 쌓고, 숨겨진 칭호들을 해금해보세요!"

            age_group = p_data['나이대'].iloc[-1]
            if tot_tournaments >= 15: l3 = "수많은 대회 출전으로 다져진 깊은 내공! 짬바에서 나오는 노련미가 타의 추종을 불허합니다."
            elif age_group == "초등부": l3 = "하루가 다르게 쑥쑥 크는 펜싱계의 미래를 밝힐 특급 유소년 유망주입니다!"
            elif age_group == "중고등부": l3 = "피지컬과 테크닉이 동시에 만개하는 시기! 청소년부 생태계를 지배할 차세대 에이스입니다."
            elif age_group == "일반부": l3 = "일과 펜싱을 병행하는 진정한 낭만 검객. 지능적인 플레이로 상대를 노련하게 요리합니다."
            else: l3 = "펜싱을 향한 순수한 열정으로 자신만의 무도를 완성해 나가는 멋진 펜서입니다."

            st.success(f"1️⃣ {l1}\n\n2️⃣ {l2}\n\n3️⃣ {l3}")
            st.divider()

            # --- 💡 [핵심 패치 4] 칭호 텍스트 간소화 ---
            st.markdown("#### 🏆 획득한 업적 및 칭호")
            titles = []
            
            golds = len(p_data[p_data['본선_순위(숫자)'] == 1])
            silvers = len(p_data[p_data['본선_순위(숫자)'] == 2])
            bronzes = len(p_data[p_data['본선_순위(숫자)'].isin([3, 4])])
            medals = golds + silvers + bronzes
            up_cnt = len(m_data[(m_data['단계'] == '본선') & (m_data['승패'] == '승') & (m_data['업셋여부'] == 'Y')])
            tot_pt = p_data['레이팅(PT)'].sum()
            p_loss = p_data['예선_패'].sum()
            p_win = p_data['예선_승'].sum()
            diff_opps = m_data['상대_고유'].nunique()

            if golds >= 10: titles.append(("👑 전설의 검귀 (GOAT)", "대회 우승 10회 고지를 밟은 절대자."))
            if golds >= 5: titles.append(("👑 인간계 멸망", f"우승 {golds}회! 이 바닥 생태계 파괴자."))
            if golds >= 3: titles.append(("🔥 황금의 지배자", "우승 3회 이상! 금메달로 밥을 비벼먹습니다."))
            if golds >= 2: titles.append(("🥇 더블 크라운", "우승의 짜릿한 맛을 두 번이나 본 강자."))
            if golds >= 1: titles.append(("🥇 우승의 달콤함", "가장 높은 곳의 공기를 마셔본 자만이 아는 쾌감!"))
            
            if silvers >= 3: titles.append(("😭 영원한 고통의 콩진호", "결승에서만 3번 좌절... 세상은 2등도 기억합니다!"))
            if silvers >= 1: titles.append(("🥈 비운의 2인자", "결승전 문턱에서 아쉬운 패배. 복수를 다짐합니다."))

            if bronzes >= 3: titles.append(("🥉 브론즈 마스터", "동메달만 3개 이상! 시상대 오른쪽 끝자리의 지배자."))
            if bronzes >= 1: titles.append(("🍲 든든한 국밥", "포디움 한 자리는 항상 내 차지."))
            
            if medals >= 20: titles.append(("🏛️ 썩은물 중의 썩은물", "입상 20회 이상. 클럽에 이분 동상을 세워야 합니다."))
            if medals >= 10: titles.append(("🎖️ 포디움 공무원", "입상 10회 이상! 집에 메달 걸어둘 곳이 부족합니다."))
            if medals >= 5: titles.append(("🏅 프로 수집가", "시상대에 5번 이상 꾸준히 올라간 엘리트 펜서."))
            if medals >= 1: titles.append(("🔰 랭커 입문", "공식 대회 입상 달성! 이제 다음 목표는 금메달."))

            if is_qual:
                if actual_wr == 100: titles.append(("✨ 절대 무결점 (God-like)", "승률 100%. 단 한 번의 패배도 허락하지 않은 불패의 신!"))
                if actual_wr >= 85: titles.append(("👿 생태계 교란종", "만나는 족족 썰어버리는 무자비한 승률."))
                if actual_wr >= 70: titles.append(("🔥 돌격대장", "막강한 돌파력으로 예선을 가볍게 뚫어버립니다."))
                if 45 <= actual_wr <= 55: titles.append(("⚖️ 인간 저울 (황금밸런스)", "강자든 약자든 무조건 반반 싸움으로 이끄는 기적의 밸런스."))
                
                if avg_sc_ai >= 4.6: titles.append(("🚀 핵불닭 볶음검", f"평균 {avg_sc_ai:.1f}득점! 방패는 갖다버린 극한의 공격수."))
                if avg_sc_ai >= 4.0: titles.append(("🗡️ 죽창맨", "매 경기 안정적으로 찌르고 베는 화끈한 닥공러."))
                if 0 < avg_sc_ai <= 2.5: titles.append(("🔫 스톰트루퍼", "공격이 더럽게 안 맞습니다. 영점 조절이 시급합니다!"))
                
                if 0 < avg_ls_ai <= 1.5: titles.append(("❄️ 람머스 (절대방벽)", f"평균 {avg_ls_ai:.1f}실점. 뚫는 것이 물리적으로 불가능합니다."))
                if 0 < avg_ls_ai <= 2.5: titles.append(("🐢 수면제 펜싱", "늪처럼 끈적한 수비로 상대를 질려버리게 만듭니다."))
                if avg_ls_ai >= 4.0: titles.append(("💸 자선사업가", "수비가 너무 관대하여 상대에게 점수를 마구 베풉니다."))

                if avg_sc_ai >= 4.2 and avg_ls_ai >= 4.0: titles.append(("💣 유리대포 (낭만합격)", "맞기 전에 찌른다! 서로 피터지게 싸우는 낭만파 검객."))

                if pythagorean >= 75: titles.append(("📐 피타고라스의 악마", "운빨 제로! 완벽한 순수 스탯의 정석."))
                if luck_index >= 12: titles.append(("🍀 주사위 신의 가호", "스탯은 평범한데 승리만 쏙쏙 빼먹는 기적의 럭키가이."))
                if luck_index <= -15: titles.append(("☔ 억까의 희생양", "지표는 강자인데 지독하게 운이 안 따릅니다. 굿 한 번 하세요."))
                
                if dom_rate >= 80 and p_win >= 5: titles.append(("🔪 살인전차", "1점 차 진땀승 따윈 취급 안 함. 무자비한 도미네이팅."))
                if dom_rate <= 30 and p_win >= 5: titles.append(("🩸 블라디미르 (꾸역승 마스터)", "보는 사람 피말리게 1점 차 접전으로 꾸역꾸역 이깁니다."))
                
                if choke_index is not None and choke_index >= 15: titles.append(("🥶 본선 자동문", "예선에서는 여포인데 15점제만 가면 심박수 200 찍는 새가슴."))
                if choke_index is not None and choke_index <= -15: titles.append(("🥷 다크템플러", "15점 단판승부만 가면 눈빛이 바뀌고 폼이 미쳐날뜁니다."))

            if p_win >= 100: titles.append(("⚔️ 무신 (武神)", "통산 100승 달성! 살아있는 전설."))
            if p_win >= 50: titles.append(("⚔️ 백전노장", "통산 50승. 수많은 검객을 베어 넘겼습니다."))
            if p_win >= 20: titles.append(("⚔️ 전투광", "통산 20승 돌파."))
            if p_win >= 1: titles.append(("🎉 달콤한 첫 승", "공식 무대에서의 짜릿한 첫 승리!"))
            
            if p_loss >= 50: titles.append(("💀 닼소 유저 (중꺾마)", "50번을 져도 내일 또 펜싱장에 나오는 진정한 무도인."))
            
            if tot_tournaments >= 30: titles.append(("🏛️ 살아있는 화석", "대회 30회 출전! 클럽의 산증인."))
            if tot_tournaments >= 10: titles.append(("🎒 프로 참석러", "대회 10회 출전. 개근상을 수여합니다."))

            if up_cnt >= 4: titles.append(("🏴‍☠️ 혁명군 대장", "본선에서 상위 시드를 4번 이상 찢어발긴 하극상 마스터!"))
            if up_cnt >= 1: titles.append(("🪓 반란군", "강자를 꺾어본 경험이 있는 다크호스."))
            
            if diff_opps >= 30: titles.append(("🤝 뉴비 판독기 (초인싸)", f"무려 {diff_opps}명의 다른 사람들과 칼을 섞은 마당발."))
            if diff_opps >= 10: titles.append(("👀 넓은 시야", f"다양한 유형의 상대 {diff_opps}명과 겨뤄봤습니다."))

            if p_win == 0 and tot_tournaments >= 2: titles.append(("🌱 떡잎마을 방범대", "조만간 터질 첫 승을 위해 칼을 갈고 있습니다!"))
            
            if len(titles) == 0: titles.append(("👤 은둔 고수", "조용히 자신만의 펜싱을 수련하는 검사."))

            st.write(f"**총 {len(titles)}개의 칭호를 장착 중입니다!**")
            t_col1, t_col2, t_col3 = st.columns(3)
            for i, (t, desc) in enumerate(titles):
                col = [t_col1, t_col2, t_col3][i % 3]
                col.markdown(f"<div style='padding:10px; background-color:#2a2a2a; border-radius:8px; margin-bottom:8px; border-left:4px solid {t_color};'><b style='color:#ffd700; font-size:14px;'>{t}</b><br><span style='color:#ccc; font-size:11px;'>{desc}</span></div>", unsafe_allow_html=True)
            
            st.divider()

            # --- 📜 대회별 매치 상세 리포트 (Poule 표 & 본선 스코어 보드) ---
            st.markdown("#### 📜 대회별 매치 상세 (Poule & Elimination)")
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("총 출전 대회", f"{tot_tournaments}회")
            b2.metric("누적 레이팅", f"{p_data['레이팅(PT)'].sum():.0f} PT")
            b3.metric("예선 누적 전적", f"{int(p_win)}승 {int(p_loss)}패")
            b4.metric("커리어 하이 (최고 순위)", f"{best_r:.0f}위" if pd.notna(best_r) and best_r > 0 else "-")

            st.info("👇 **출전했던 대회를 클릭하면 실제 대회장과 똑같은 '예선 조별(Poule) 십자 표'와 '본선 스코어 대진'이 펼쳐집니다!**")
            
            for tn in p_data['대회명'].unique()[::-1]:
                t_df = p_data[p_data['대회명'] == tn].iloc[-1]
                t_date_str = t_df['대회일자'].strftime('%Y-%m-%d') if pd.notna(t_df['대회일자']) else '날짜미상'
                
                pr = t_df['예선_랭킹']
                br = str(t_df['본선_랭킹']).strip()
                
                if br in ["예선탈락", "기록없음", "0위", "0"]: title_suffix = f"예선 {pr} ➔ ❌ [예선 탈락]"
                else:
                    br_str = br if '위' in br else f"{br}위"
                    title_suffix = f"예선 {pr} ➔ 🏅 본선 {br_str} (+{t_df['레이팅(PT)']:.0f}pt)"

                with st.expander(f"🏆 {t_date_str} | {tn} (부수: {t_df['부수']}) | {title_suffix}"):
                    t_matches = m_data[m_data['대회명'] == tn]
                    prelim_m = t_matches[t_matches['단계'] == '예선']
                    main_m = t_matches[t_matches['단계'] == '본선']
                    
                    st.markdown(f"**🔹 예선(Poules) 종합 성적:** {t_df['예선_승']}승 {t_df['예선_패']}패 (득점 {t_df['예선_득점']} / 실점 {t_df['예선_실점']})")
                    
                    col_p, col_m = st.columns([1.2, 0.8])
                    
                    with col_p:
                        st.markdown("<h5 style='color:#54c3a6;'>[예선 조별리그 (Poule) 매트릭스 보드]</h5>", unsafe_allow_html=True)
                        if not prelim_m.empty:
                            pool_players_uids = list(dict.fromkeys([sel_player] + prelim_m['상대_고유'].tolist()))
                            uid_to_name = {}
                            short_names_only = [p.split(' (')[0] for p in pool_players_uids]
                            for p in pool_players_uids:
                                sn = p.split(' (')[0]
                                if short_names_only.count(sn) > 1: uid_to_name[p] = p 
                                else: uid_to_name[p] = sn
                                
                            # 💡 [핵심 패치 5] TypeError 원천 차단: Dataframe 생성 시 아예 object(문자열 호환) 타입으로 강제 초기화합니다.
                            new_cols = ['승(V)', '득(TD)', '실(TR)', '지수(Ind)', '순위(R)']
                            all_cols = pool_players_uids + new_cols
                            poule_df = pd.DataFrame(index=pool_players_uids, columns=all_cols, dtype=object)
                            
                            # 비어있는 칸을 NaN이 아닌 빈 문자열("")로 채워 PyArrow 충돌을 방지합니다.
                            poule_df = poule_df.fillna("")
                            
                            for p in pool_players_uids: poule_df.loc[p, p] = "⬛"
                            
                            full_pool = global_match[(global_match['대회명'] == tn) & (global_match['단계'] == '예선')]
                            
                            for p1 in pool_players_uids:
                                for p2 in pool_players_uids:
                                    if p1 != p2:
                                        match = full_pool[(full_pool['기준_고유'] == p1) & (full_pool['상대_고유'] == p2)]
                                        if not match.empty:
                                            res = match.iloc[0]['승패']
                                            score = str(match.iloc[0]['기준득점']).replace(".0", "")
                                            if score == "-":
                                                poule_df.loc[p1, p2] = "V" if res == '승' else "D"
                                            else:
                                                if res == '승':
                                                    val = f"V{score}" if score.isdigit() and int(score) < 5 else "V5"
                                                    if score.upper().startswith("V"): val = score.upper()
                                                else:
                                                    val = f"D{score}" if score.isdigit() else "D"
                                                    if score.upper().startswith("D"): val = score.upper()
                                                # 값을 삽입할 때 반드시 str()로 캐스팅
                                                poule_df.loc[p1, p2] = str(val)
                                            
                            for p1 in pool_players_uids:
                                p_info = global_db[(global_db['고유이름'] == p1) & (global_db['대회명'] == tn)]
                                if not p_info.empty:
                                    r_info = p_info.iloc[-1]
                                    # 숫자를 넣을 때 발생하던 에러 방지를 위해 명시적으로 int 계산 후 str 변환
                                    p_wins = int(r_info['예선_승']) if pd.notna(r_info['예선_승']) else 0
                                    p_td = int(r_info['예선_득점']) if pd.notna(r_info['예선_득점']) else 0
                                    p_tr = int(r_info['예선_실점']) if pd.notna(r_info['예선_실점']) else 0
                                    p_ind = p_td - p_tr
                                    p_rank = str(r_info['예선_랭킹'])
                                    
                                    poule_df.loc[p1, '승(V)'] = str(p_wins)
                                    poule_df.loc[p1, '득(TD)'] = str(p_td)
                                    poule_df.loc[p1, '실(TR)'] = str(p_tr)
                                    poule_df.loc[p1, '지수(Ind)'] = str(p_ind)
                                    poule_df.loc[p1, '순위(R)'] = p_rank

                            poule_df.rename(index=uid_to_name, columns=uid_to_name, inplace=True)
                            
                            def highlight_me(row):
                                if row.name == uid_to_name[sel_player]: return ['background-color: rgba(84, 195, 166, 0.3)'] * len(row)
                                return [''] * len(row)
                                
                            st.dataframe(poule_df.style.apply(highlight_me, axis=1), use_container_width=True)
                        else:
                            st.caption("예선 상세 기록이 존재하지 않습니다.")

                    with col_m:
                        st.markdown("<h5 style='color:#ff6666;'>[본선 토너먼트 (Elimination) 기록표]</h5>", unsafe_allow_html=True)
                        if "예선 탈락" in title_suffix:
                            st.error("❌ 예선 성적 미달로 본선에 진출하지 못했습니다.")
                        else:
                            if not main_m.empty:
                                m_rows = []
                                for _, m in main_m.iterrows():
                                    rnd_tag = m.get('라운드', '본선')
                                    res = "🔵 승리" if m['승패'] == '승' else "🔴 패배"
                                    opp_name = m['상대선수'].split(' (')[0]
                                    
                                    s_my = str(m['기준득점']).replace(".0", "").strip()
                                    s_op = str(m['상대득점']).replace(".0", "").strip()
                                    
                                    if (s_my in ["V", "D"] and s_op in ["V", "D"]) or (s_my == "-" and s_op == "-"):
                                        score_str = "V : D (상세점수 생략)" if m['승패'] == '승' else "D : V (상세점수 생략)"
                                    else:
                                        score_str = f"{s_my} : {s_op}"
                                        
                                    note = "🔥 업셋" if m['업셋여부'] == 'Y' else ""
                                    m_rows.append({"라운드": rnd_tag, "상대 선수": f"{opp_name} ({m['상대팀']})", "결과": res, "스코어 (나 : 상대)": score_str, "비고": note})
                                st.dataframe(pd.DataFrame(m_rows), use_container_width=True, hide_index=True)
                            else:
                                st.warning("⚠️ **본선 상세 기록 스캔 불가**\n\n대진표(트리) 양식이 복잡하여 매치업 스캔에 실패했습니다.\n(※ '데이터 완전 초기화' 후 엑셀 재업로드 권장!)")

            st.divider()
            st.markdown(f"### 💬 {sel_player.split(' (')[0]} 선수 방명록")
            player_comments = st.session_state.comment_db[st.session_state.comment_db['대상선수'] == sel_player]
            if not player_comments.empty:
                for _, row in player_comments.sort_values(by='작성일시', ascending=False).iterrows():
                    st.markdown(f"<div style='background-color:#1e1e1e; padding:12px; border-left:4px solid {t_color}; border-radius:5px; margin-bottom:8px;'><b style='color:#00e5ff; font-size:16px;'>{row['작성자']}</b> <span style='font-size:12px;color:#aaaaaa;'>({row['작성일시']})</span><br><span style='color:#ffffff; font-size:15px;'>{row['내용']}</span></div>", unsafe_allow_html=True)
            
            with st.form("player_comment_form", clear_on_submit=True):
                c_c1, c_c2 = st.columns([1, 4])
                with c_c1: author = st.text_input("닉네임", placeholder="무명검객")
                with c_c2: comment_text = st.text_input("코멘트 남기기", placeholder="이번 대회 폼 미쳤다!! 화이팅!!")
                if st.form_submit_button("📝 선수 코멘트 등록") and comment_text.strip():
                    new_c = pd.DataFrame([{"대상선수": sel_player, "작성자": author if author else "익명", "내용": comment_text, "작성일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    st.session_state.comment_db = pd.concat([st.session_state.comment_db, new_c], ignore_index=True)
                    st.session_state.comment_db.to_csv(COMMENT_DB_FILE, index=False, encoding='utf-8-sig')
                    st.rerun()

# ================= TAB 4: 1:1 라이벌 비교 =================
with tabs[4]:
    st.subheader("⚔️ 1:1 라이벌 정밀 비교 & AI 가상 승부 예측")
    if not global_db.empty:
        c1, c2 = st.columns(2)
        with c1: 
            sel_d_a = st.selectbox("1. 🔴 A 대분류", ["전체"] + sorted(list(global_db['부수'].dropna().unique())), key="da")
            db_a = global_db if sel_d_a == "전체" else global_db[global_db['부수'] == sel_d_a]
            sel_t_a = st.selectbox("2. 🔴 A 클럽", ["전체"] + sorted(list(db_a['소속팀'].dropna().unique())), key="ta")
            if sel_t_a != "전체": db_a = db_a[db_a['소속팀'] == sel_t_a]
            pA = st.selectbox("3. 🔴 선수 A 선택", ["선택"] + sorted(list(db_a['고유이름'].dropna().unique())), key="pa")

        with c2: 
            sel_d_b = st.selectbox("1. 🔵 B 대분류", ["전체"] + sorted(list(global_db['부수'].dropna().unique())), key="db")
            db_b = global_db if sel_d_b == "전체" else global_db[global_db['부수'] == sel_d_b]
            sel_t_b = st.selectbox("2. 🔵 B 클럽", ["전체"] + sorted(list(db_b['소속팀'].dropna().unique())), key="tb")
            if sel_t_b != "전체": db_b = db_b[db_b['소속팀'] == sel_t_b]
            pB = st.selectbox("3. 🔵 선수 B 선택", ["선택"] + sorted(list(db_b['고유이름'].dropna().unique())), key="pb")
        
        st.divider()

        if pA != "선택" and pB != "선택":
            if pA == pB:
                st.warning("같은 선수를 선택했습니다. 다른 선수를 골라주세요!")
            else:
                h2h = global_match[(global_match['기준_고유'] == pA) & (global_match['상대_고유'] == pB)]
                st.markdown(f"<h3 style='text-align: center;'>🥊 [{pA.split(' (')[0]}] vs [{pB.split(' (')[0]}] 자존심 매치!</h3>", unsafe_allow_html=True)
                
                if not h2h.empty:
                    a_tot = len(h2h[h2h['승패'] == '승'])
                    b_tot = len(h2h[h2h['승패'] == '패'])
                    st.success(f"🔥 **종합 전적: 총 {len(h2h)}전 ➡️ 🔴 {pA.split(' (')[0]} {a_tot}승 / 🔵 {pB.split(' (')[0]} {b_tot}승**")
                    
                    df_h2h = h2h[['대회일자', '대회명', '단계', '라운드', '기준득점', '상대득점', '승패']].sort_values('대회일자', ascending=False).reset_index(drop=True)
                    df_h2h['승리자'] = df_h2h['승패'].apply(lambda x: f"🔴 {pA.split(' (')[0]} 승리" if x == '승' else f"🔵 {pB.split(' (')[0]} 승리")
                    df_h2h['매치 스코어'] = df_h2h.apply(lambda r: f"{str(r['기준득점']).replace('.0','')} : {str(r['상대득점']).replace('.0','')}" if str(r['기준득점']) not in ["-", "V", "D"] else "스코어 확인불가", axis=1)
                    st.dataframe(df_h2h[['대회일자', '대회명', '단계', '라운드', '매치 스코어', '승리자']], use_container_width=True, hide_index=True)
                else:
                    st.info("💡 공식 맞대결 기록이 없습니다. AI 가상 시뮬레이션을 진행합니다!")
                    a_data, b_data = global_db[global_db['고유이름'] == pA], global_db[global_db['고유이름'] == pB]
                    a_pt, a_wr = a_data['레이팅(PT)'].sum(), a_data['예선_승률(%)'].mean()
                    b_pt, b_wr = b_data['레이팅(PT)'].sum(), b_data['예선_승률(%)'].mean()
                    score_a = (a_pt * 0.5) + (a_wr * 2.0)
                    score_b = (b_pt * 0.5) + (b_wr * 2.0)
                    if score_a + score_b == 0: prob_a, prob_b = 50.0, 50.0
                    else: prob_a = (score_a / (score_a + score_b)) * 100; prob_b = 100 - prob_a
                    st.markdown(f"<h3 style='text-align: center;'>🤖 AI 승률 예측: 🔴 {pA.split(' (')[0]} {prob_a:.1f}% vs 🔵 {pB.split(' (')[0]} {prob_b:.1f}%</h3>", unsafe_allow_html=True)
                    st.progress(prob_a / 100)

# ================= TAB 5: 시뮬레이터 (명단 복붙) =================
with tabs[5]:
    st.subheader("🔮 다자간 파워 시드 시뮬레이터 (명단 복사/붙여넣기)")
    if not global_db.empty:
        raw_names_input = st.text_area("📋 출전 명단을 복사해서 붙여넣으세요.", height=150, placeholder="홍길동\n이순신")
        if st.button("🚀 명단 분석 및 랭킹 예측 가동"):
            if raw_names_input.strip():
                raw_names_list = list(dict.fromkeys([n.strip() for n in re.split(r'[,\n]+', raw_names_input) if n.strip()]))
                matched_uids, unmatched_names = [], []
                all_uids = global_db['고유이름'].dropna().unique()
                
                for name in raw_names_list:
                    name_clean = name.split('(')[0].strip()
                    matches = global_db[global_db['이름'] == name_clean]
                    if matches.empty:
                        if name in all_uids: matched_uids.append(name)
                        else: unmatched_names.append(name)
                    else:
                        best_match = matches.groupby('고유이름')['레이팅(PT)'].sum().idxmax()
                        if best_match not in matched_uids: matched_uids.append(best_match)

                if matched_uids or unmatched_names:
                    sim_rows = []
                    sim_db = global_db[global_db['고유이름'].isin(matched_uids)]
                    if not sim_db.empty:
                        ss = sim_db.groupby('고유이름').agg(누적PT=('레이팅(PT)', 'sum'), 승률=('예선_승률(%)', 'mean')).reset_index()
                        for _, row in ss.iterrows(): sim_rows.append({"참가선수": row['고유이름'], "누적PT": row['누적PT'], "승률": row['승률']})
                    for un in unmatched_names: sim_rows.append({"참가선수": f"{un} (기록없음 뉴비)", "누적PT": 0.0, "승률": 0.0})
                        
                    res_df = pd.DataFrame(sim_rows).sort_values(by=['누적PT', '승률'], ascending=[False, False]).reset_index(drop=True)
                    res_df.index += 1
                    st.dataframe(res_df, column_config={"누적PT": st.column_config.NumberColumn("누적 레이팅", format="%.1f pt"), "승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%")}, use_container_width=True)

# ================= TAB 6: 데이터 관리 =================
with tabs[6]:
    st.subheader("⚙️ 데이터 관리 센터 (엑셀 업로드)")
    if not st.session_state.admin_auth:
        st.error("🔒 좌측 사이드바에서 비밀번호를 입력해야 접속할 수 있습니다.")
    else:
        col1, col2 = st.columns(2)
        with col1: tourney_name = st.text_input("대회명 (수동입력, 파일 이름이 우선됨)")
        with col2: tourney_date = st.date_input("대회 일자")
            
        uploaded_files = st.file_uploader("원본 엑셀 파일(.xlsx) 업로드", type=['xlsx'], accept_multiple_files=True)
        
        if st.button("업로드 및 처리 가동"):
            if uploaded_files:
                new_players, new_matches = [], []
                
                def get_num(text):
                    if pd.isna(text) or str(text).strip() == "": return None
                    nums = re.findall(r'\d+', str(text))
                    return int(nums[0]) if nums else None
                
                def get_pt(rank_str, pre_str):
                    if rank_str == "예선탈락": return 5
                    t = get_num(rank_str) if get_num(rank_str) is not None else get_num(pre_str)
                    if t is None: return 5
                    if t == 1: return 100
                    if t == 2: return 80
                    if t in [3, 4]: return 60
                    if 5 <= t <= 8: return 45  
                    if 9 <= t <= 16: return 25 
                    if 17 <= t <= 32: return 10 
                    return 5

                def format_val(x):
                    if pd.isna(x): return ""
                    v = str(x).strip()
                    if v.endswith('.0'): return v[:-2]
                    return v

                success_count = 0
                for uploaded_file in uploaded_files:
                    file_name_no_ext = os.path.splitext(uploaded_file.name)[0]
                    t_name = tourney_name if tourney_name else file_name_no_ext
                    t_date_str = str(tourney_date)
                    
                    if not st.session_state.player_db.empty and t_name in st.session_state.player_db['대회명'].values: continue

                    try: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='calamine', header=None)
                    except: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl', header=None)

                    success_count += 1
                    for sheet_name, df in sheets.items():
                        if df.empty or "단체" in sheet_name or "단체" in t_name: continue 
                        all_rows = [[format_val(x) for x in row.values] for _, row in df.iterrows()]
                        
                        parsed_players, valid_names = {}, {}
                        in_pool, col_map = False, {}
                        pool_blocks, curr_pool = [], []
                        
                        for r in all_rows:
                            j = "".join(r).replace(" ", "")
                            c_str = [str(x).replace(" ", "") for x in r]
                            
                            if 'No' in c_str and '이름' in c_str and '소속팀' in c_str:
                                if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool}); curr_pool = []
                                in_pool, col_map = True, {n: i for i, n in enumerate(c_str) if n != ""}
                                continue
                            if "최종순위" in j or "뿔랭킹" in j or "최종랭킹" in j or "엘리미나시옹" in j or ("순위" in c_str and "이름" in c_str):
                                if curr_pool: pool_blocks.append({'map': col_map, 'p': curr_pool}); curr_pool = []
                                in_pool = False
                                
                            if in_pool:
                                n_idx, no_idx = col_map.get('이름'), col_map.get('No')
                                if n_idx is not None and n_idx < len(r):
                                    name = str(r[n_idx]).strip()
                                    if name and name not in ["이름", "0"] and not name.startswith("뿔"):
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
                                team1 = str(p1_r[cmap.get('소속팀')]).strip().replace('(사)부산펜싱클럽', '윈펜싱클럽').replace('부산펜싱클럽', '윈펜싱클럽') if '소속팀' in cmap else ""
                                
                                wins, v_matches, deuk, tight_wins = 0, 0, 0, 0
                                j_idx = cmap.get('지수')
                                try: jisu = int(str(p1_r[j_idx]).replace("+","").replace(" ","")) if j_idx is not None else 0
                                except: jisu = 0
                                
                                m_dict = {}
                                for j, p2 in enumerate(players):
                                    if i == j: continue
                                    name2 = str(p2['row'][cmap.get('이름')]).strip()
                                    opp_c = str(j + 1)
                                    my_c = str(i + 1)
                                    
                                    my_val = str(p1_r[cmap[opp_c]]).strip() if opp_c in cmap and cmap[opp_c] < len(p1_r) else ""
                                    opp_val = str(p2['row'][cmap[my_c]]).strip() if my_c in cmap and cmap[my_c] < len(p2['row']) else ""
                                    
                                    if my_val and (my_val.upper().startswith('V') or my_val.isdigit() or my_val == '0'):
                                        v_matches += 1
                                        is_win = my_val.upper().startswith('V')
                                        my_s = get_num(my_val) if get_num(my_val) is not None else (5 if is_win else 0)
                                        opp_s = get_num(opp_val) if get_num(opp_val) is not None else (5 if not is_win else 0)
                                        
                                        if is_win:
                                            wins += 1; deuk += my_s
                                            tight = my_val.upper() in ["V1", "V2", "V3", "V4"]
                                            if tight: tight_wins += 1
                                            m_dict[name2] = {'res': '승', 'my': my_s, 'opp': opp_s, 'tight': tight}
                                        else: 
                                            deuk += my_s
                                            m_dict[name2] = {'res': '패', 'my': my_s, 'opp': opp_s, 'tight': False}
                                                
                                wr = round((wins / v_matches) * 100, 1) if v_matches > 0 else 0.0
                                parsed_players[name1] = {
                                    '대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '이름': name1, '소속팀': team1, 
                                    '예선_승': wins, '예선_패': v_matches - wins, '예선_승률(%)': wr, '예선_득점': deuk, '예선_실점': deuk - jisu, 
                                    '진땀승': tight_wins, '예선_랭킹': "기록없음", '본선_랭킹': "기록없음"
                                }
                                pool_data.append({'이름': name1, '소속팀': team1, 'm': m_dict, 'No': p1['No']})

                        r_mode, bracket_names, in_bracket = None, set(), False
                        for r in all_rows:
                            j = "".join(r).replace(" ", "")
                            c_str = [str(x).replace(" ", "") for x in r]
                            
                            if ("순위" in c_str and "이름" in c_str) or ("결과" in c_str and "이름" in c_str) or "최종순위" in j or "최종결과" in j: r_mode = 'final'; in_bracket = False; continue
                            elif ("랭킹" in c_str and "이름" in c_str) or "예선랭킹" in j: r_mode = 'prelim'; in_bracket = False; continue
                            
                            if any(x in j for x in ["엘리미나시옹", "64강", "32강", "16강", "8강", "준결승", "결승"]):
                                r_mode = None; in_bracket = True
                                
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
                            
                            if in_bracket:
                                for cell in r:
                                    nk = str(cell).replace(" ", "")
                                    if nk in valid_names: bracket_names.add(valid_names[nk])

                        t_dict = {p['이름']: p['소속팀'] for p in pool_data}
                        for p in pool_data:
                            for o_name, md in p['m'].items():
                                opp_team = str(t_dict.get(o_name, "")).replace('(사)부산펜싱클럽', '윈펜싱클럽')
                                new_matches.append({
                                    '대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, 
                                    '기준선수': p['이름'], '기준팀': p['소속팀'], '상대선수': o_name, '상대팀': opp_team, 
                                    '승패': md['res'], '단계': '예선', '업셋여부': 'N', '진땀승': 'Y' if md['tight'] else 'N',
                                    '라운드': '예선풀', '기준득점': md['my'], '상대득점': md['opp']
                                })

                        sheet_players = []
                        for p_name, p_info in parsed_players.items():
                            if len(bracket_names) > 0:
                                if p_name not in bracket_names: p_info['본선_랭킹'] = "예선탈락"
                                elif p_info['본선_랭킹'] == "기록없음": p_info['본선_랭킹'] = p_info['예선_랭킹']
                            else:
                                if p_info['예선_랭킹'] != "기록없음" and p_info['본선_랭킹'] == "기록없음": p_info['본선_랭킹'] = "예선탈락"

                            if p_info['예선_랭킹'] == "기록없음" and p_info['본선_랭킹'] not in ["예선탈락", "기록없음"]: p_info['예선_랭킹'] = p_info['본선_랭킹']
                            p_info['예선_순위(숫자)'] = get_num(p_info['예선_랭킹'])
                            p_info['본선_순위(숫자)'] = get_num(p_info['본선_랭킹']) if p_info['본선_랭킹'] != "예선탈락" else 0
                            p_info['레이팅(PT)'] = get_pt(p_info['본선_랭킹'], p_info['예선_랭킹'])
                            
                            new_players.append(p_info)
                            sheet_players.append(p_info)

                        advanced = [p for p in sheet_players if p['본선_순위(숫자)'] is not None and p['본선_순위(숫자)'] > 0]
                        if advanced:
                            advanced.sort(key=lambda x: (x['예선_순위(숫자)'] if x['예선_순위(숫자)'] and x['예선_순위(숫자)'] > 0 else 9999))
                            for i, p in enumerate(advanced):
                                p['논리_시드'] = i + 1
                                    
                            def get_bracket(n):
                                if n == 2: return [1, 2]
                                prev = get_bracket(n // 2)
                                b = []
                                for p in prev: b.extend([p, n + 1 - p])
                                return b
                                
                            def get_rscore(rank):
                                if rank == 1: return 100
                                if rank == 2: return 90
                                if rank in [3, 4]: return 80
                                if 5 <= rank <= 8: return 70
                                if 9 <= rank <= 16: return 60
                                if 17 <= rank <= 32: return 50
                                return 20

                            ms = len(advanced)
                            bs = 2
                            while bs < ms: bs *= 2
                            b_seeds = get_bracket(bs)
                            
                            s2p = {p['논리_시드']: p for p in advanced}
                            cr = [s2p.get(s, None) for s in b_seeds]
                                    
                            round_num = bs
                            while len(cr) > 1:
                                nr = []
                                round_name = f"{round_num}강" if round_num > 4 else ("준결승" if round_num == 4 else "결승")
                                for i in range(0, len(cr), 2):
                                    p1, p2 = cr[i], cr[i+1]
                                    if p1 is None and p2 is None: nr.append(None)
                                    elif p1 is None: nr.append(p2)
                                    elif p2 is None: nr.append(p1)
                                    else:
                                        s1, s2 = get_rscore(p1['본선_순위(숫자)']), get_rscore(p2['본선_순위(숫자)'])
                                        if s1 > s2: w, l = p1, p2
                                        elif s2 > s1: w, l = p2, p1
                                        else: w, l = (p1, p2) if p1['논리_시드'] < p2['논리_시드'] else (p2, p1)
                                            
                                        is_up = 'Y' if w['논리_시드'] > l['논리_시드'] else 'N'
                                        w_name, l_name = w['이름'], l['이름']
                                        w_score, l_score = "-", "-"
                                        
                                        found = False
                                        for c in range(df.shape[1]):
                                            w_rows = [r for r in range(df.shape[0]) if str(df.iloc[r, c]).replace(" ", "").replace(".0", "") == valid_names.get(w_name.replace(" ", ""), "")]
                                            l_rows = [r for r in range(df.shape[0]) if str(df.iloc[r, c]).replace(" ", "").replace(".0", "") == valid_names.get(l_name.replace(" ", ""), "")]
                                            for wr in w_rows:
                                                for lr in l_rows:
                                                    if abs(wr - lr) <= 16:
                                                        if c + 1 < df.shape[1]:
                                                            s_w = str(df.iloc[wr, c+1]).replace(" ", "").replace(".0", "")
                                                            s_l = str(df.iloc[lr, c+1]).replace(" ", "").replace(".0", "")
                                                            if re.match(r'^[VDvd]?\d*$', s_w) or s_w in ['V', 'D', '기권', '포기']: w_score = s_w
                                                            if re.match(r'^[VDvd]?\d*$', s_l) or s_l in ['V', 'D', '기권', '포기']: l_score = s_l
                                                        found = True
                                                        break
                                                if found: break
                                            if found: break
                                        
                                        if w_score == "-" and l_score == "-": w_score, l_score = "V", "D"
                                        
                                        new_matches.append({'대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '기준선수': w['이름'], '기준팀': w['소속팀'], '상대선수': l['이름'], '상대팀': l['소속팀'], '승패': '승', '단계': '본선', '업셋여부': is_up, '진땀승':'N', '라운드': round_name, '기준득점': w_score, '상대득점': l_score})
                                        new_matches.append({'대회일자': str(t_date_str), '대회명': t_name, '부수': sheet_name, '기준선수': l['이름'], '기준팀': l['소속팀'], '상대선수': w['이름'], '상대팀': w['소속팀'], '승패': '패', '단계': '본선', '업셋여부': 'N', '진땀승':'N', '라운드': round_name, '기준득점': l_score, '상대득점': w_score})
                                        nr.append(w)
                                cr = nr
                                round_num //= 2
                
                if new_players:
                    st.session_state.player_db = pd.concat([st.session_state.player_db, pd.DataFrame(new_players)], ignore_index=True)
                    st.session_state.match_db = pd.concat([st.session_state.match_db, pd.DataFrame(new_matches)], ignore_index=True)
                    st.session_state.player_db.to_csv(PLAYER_DB_FILE, index=False, encoding='utf-8-sig')
                    st.session_state.match_db.to_csv(MATCH_DB_FILE, index=False, encoding='utf-8-sig')
                    st.success(f"✅ 총 {success_count}개 대회 파싱 완료! 엑셀 업로드 성공!")
                    st.rerun()
