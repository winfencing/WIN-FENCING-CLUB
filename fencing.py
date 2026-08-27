import streamlit as st
import pandas as pd
import os
import re
import datetime
import random
import plotly.graph_objects as go

st.set_page_config(page_title="윈펜싱클럽 전력 분석 V30.0", page_icon="🤺", layout="wide")

st.title("🤺 윈펜싱클럽 데이터랩 (V30.0 세이버메트릭스 에디션)")
st.markdown("나이대 기반 AI 3줄평, 피타고리안 기대승률, 다자간 예측 시뮬레이터, 보안 시스템 도입!")

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
        if col in global_db.columns: global_db[col] = pd.to_numeric(global_db[col], errors='coerce').fillna(0)
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
    "📖 튜토리얼 & 일정표", "🏆 종합 랭킹 보드", "🏢 클럽 스탯 & 방명록", 
    "🎮 펜싱 세이버메트릭스 (개인)", "💠 육각형 스탯 폼", 
    "⚔️ 1:1 라이벌 분석", "🔮 대회 예측 시뮬레이터", "⚙️ 데이터 관리 (관리자)"
])

# ================= TAB 0: 가이드 & 일정표 =================
with tabs[0]:
    st.subheader("📖 윈펜싱 데이터랩 V30.0 사용 가이드")
    st.markdown("""
    환영합니다! 이 곳은 펜싱 선수의 모든 데이터를 **세이버메트릭스(고급 통계 기법)**로 정밀 분석해주는 통합 데이터랩입니다.
    
    *   **🏆 종합 랭킹:** 우리 클럽과 선수의 누적 랭킹, 그리고 6대 폼 스탯을 확인합니다.
    *   **🎮 개인 분석 (세이버메트릭스):** 특정 선수를 검색하면 행운 지수를 따지는 **피타고리안 기대승률**, 압도율(Dominance), 본선 새가슴 지수를 분석하여 **수천 가지 조합의 AI 3줄 평**을 내려줍니다.
    *   **🔮 시뮬레이터:** 텍스트 입력의 오류를 없앴습니다. **선수 다중 선택(체크박스)** 방식으로 바뀌어 다음 대회 출전자들의 상성과 천적을 완벽하게 시뮬레이션 합니다.
    *   **💬 방명록:** 선수 개인뿐만 아니라, **클럽 단체 방명록**에 응원을 남길 수 있습니다.
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
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏢 전국 클럽 파워 랭킹")
            cs = global_db.groupby('소속팀').agg(총원=('고유이름', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 금메달=('본선_순위(숫자)', lambda x: (x == 1).sum())).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            cs.index += 1
            st.dataframe(cs, use_container_width=True)

        with c2:
            st.markdown("#### 🤺 전국 통합 선수 랭킹")
            ps = global_db.sort_values('대회일자').groupby('고유이름').agg(소속팀=('소속팀', 'last'), 나이대=('나이대', 'last'), 출전=('대회명', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 승률=('예선_승률(%)', 'mean')).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            ps.index += 1
            st.dataframe(ps, use_container_width=True)

# ================= TAB 2: 클럽 분석 & 방명록 =================
with tabs[2]:
    st.subheader("🏢 클럽 정밀 분석 & 클럽 단체 방명록")
    if not global_db.empty:
        my_team = st.selectbox("분석할 클럽(소속팀)을 선택하세요.", ["선택"] + sorted(list(global_db['소속팀'].dropna().unique())))
        if my_team != "선택":
            h_db = global_db[global_db['소속팀'] == my_team]
            h_match = global_match[global_match['기준팀'] == my_team]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 등록 선수", f"{h_db['고유이름'].nunique()}명")
            c2.metric("총 누적 레이팅", f"{h_db['레이팅(PT)'].sum():.0f} PT")
            c3.metric("금메달 획득 총합", f"{len(h_db[h_db['본선_순위(숫자)'] == 1])}개")
            c4.metric("본선 업셋 승리", f"{len(h_match[(h_match['단계'] == '본선') & (h_match['승패'] == '승') & (h_match['업셋여부'] == 'Y')])}회")
            
            st.divider()
            st.markdown(f"### 📣 {my_team} 단체 응원 방명록")
            
            club_comments = st.session_state.club_comment_db[st.session_state.club_comment_db['대상클럽'] == my_team]
            if not club_comments.empty:
                for _, row in club_comments.sort_values(by='작성일시', ascending=False).head(15).iterrows():
                    st.markdown(f"<div style='background-color:#1e2a3a; padding:12px; border-left:4px solid #54c3a6; border-radius:5px; margin-bottom:8px;'><b>{row['작성자']}</b> <span style='font-size:12px;color:#888;'>({row['작성일시']})</span><br><span style='color:#ddd; font-size:15px;'>{row['내용']}</span></div>", unsafe_allow_html=True)
            else: st.info("클럽에 첫 번째 응원을 남겨주세요!")
            
            with st.form("club_comment_form", clear_on_submit=True):
                cc1, cc2 = st.columns([1, 4])
                with cc1: author = st.text_input("닉네임 (익명 가능)", placeholder="예: 열혈팬")
                with cc2: content = st.text_input("응원 남기기", placeholder="우리 클럽 파이팅!!")
                if st.form_submit_button("📝 코멘트 등록"):
                    if content.strip():
                        new_c = pd.DataFrame([{"대상클럽": my_team, "작성자": author if author else "익명", "내용": content, "작성일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        st.session_state.club_comment_db = pd.concat([st.session_state.club_comment_db, new_c], ignore_index=True)
                        st.session_state.club_comment_db.to_csv(CLUB_COMMENT_DB_FILE, index=False, encoding='utf-8-sig')
                        st.success("등록 완료!"); st.rerun()

# ================= TAB 3: 개인 스탯 & 세이버메트릭스 & AI =================
with tabs[3]:
    st.subheader("🎮 펜싱 세이버메트릭스 & AI 3줄 스카우팅 리포트")
    if not global_db.empty:
        col1, col2, col3 = st.columns(3)
        with col1: sel_div = st.selectbox("1. 대분류", ["전체"] + sorted(list(global_db['부수'].dropna().unique())))
        with col2: 
            db_t4 = global_db if sel_div == "전체" else global_db[global_db['부수'] == sel_div]
            sel_team = st.selectbox("2. 클럽", ["전체"] + sorted(list(db_t4['소속팀'].dropna().unique())))
        with col3:
            if sel_team != "전체": db_t4 = db_t4[db_t4['소속팀'] == sel_team]
            sel_player = st.selectbox("3. 선수 선택", ["선택"] + sorted(list(db_t4['고유이름'].dropna().unique())))
        
        if sel_player != "선택":
            p_data = global_db[global_db['고유이름'] == sel_player].sort_values('대회일자')
            m_data = global_match[global_match['기준_고유'] == sel_player]
            
            # --- 📊 세이버메트릭스 지표 연산 ---
            age_group = p_data['나이대'].iloc[-1]
            tot_tournaments = len(p_data)
            tot_matches = p_data['예선_승'].sum() + p_data['예선_패'].sum()
            actual_wr = p_data['예선_승률(%)'].mean()
            
            tot_sc = p_data['예선_득점'].sum()
            tot_ls = p_data['예선_실점'].sum()
            avg_margin = (tot_sc - tot_ls) / tot_matches if tot_matches > 0 else 0
            
            # 1. 피타고리안 기대 승률
            denom = (tot_sc**2) + (tot_ls**2)
            pythagorean = ((tot_sc**2) / denom * 100) if denom > 0 else 50.0
            luck_index = actual_wr - pythagorean # +면 운좋음(클러치), -면 불운(새가슴)
            
            # 2. 예선 통과율 & 본선 새가슴 지수
            main_advances = len(p_data[p_data['본선_순위(숫자)'] > 0])
            pass_rate = (main_advances / tot_tournaments * 100) if tot_tournaments > 0 else 0.0
            
            main_m = m_data[m_data['단계'] == '본선']
            main_wins = len(main_m[main_m['승패'] == '승'])
            main_total = len(main_m)
            main_wr = (main_wins / main_total * 100) if main_total > 0 else 0.0
            choke_index = actual_wr - main_wr # +면 본선에서 굳음, -면 본선 여포
            
            # 3. 압도율(Dominance)
            tot_wins = p_data['예선_승'].sum()
            sweats = len(m_data[(m_data['단계']=='예선') & (m_data['진땀승']=='Y')])
            dom_rate = ((tot_wins - sweats) / tot_wins * 100) if tot_wins > 0 else 0.0

            st.markdown(f"### 🏅 {sel_player.split(' (')[0]} ({age_group}) 세이버메트릭스 분석실")
            
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("예선 통과율 (진출/출전)", f"{pass_rate:.1f}%", f"{main_advances}회 진출")
            s2.metric("기대 승률 (피타고리안)", f"{pythagorean:.1f}%", f"운/클러치 지수: {luck_index:+.1f}%p")
            s3.metric("예선 ➡ 본선 승률 변화", f"{actual_wr:.1f}% ➡ {main_wr:.1f}%", f"새가슴 지수: {choke_index:+.1f}%p", delta_color="inverse")
            s4.metric("압도율 (1점차 제외 완승)", f"{dom_rate:.1f}%", f"평균 득실 마진: {avg_margin:+.1f}점")
            
            # --- 🤖 AI 3줄 평 제너레이터 ---
            st.divider()
            st.markdown("#### 🤖 AI 스카우터 리포트 (3줄 요약)")
            random.seed(sel_player + str(tot_matches))
            
            # Line 1: 폼/스타일
            if avg_margin >= 2.5: l1 = random.choice(["상대를 압도하는 파괴적인 공격력과 단단한 방어를 동시에 갖춘 폭군입니다.", "초반부터 기선을 완벽하게 제압하여 상대를 펜스 끝으로 몰아넣습니다."])
            elif tot_sc / (tot_matches if tot_matches else 1) >= 4.2: l1 = random.choice(["수비는 잊어라! 맞기 전에 먼저 찔러버리는 극단적이고 화끈한 낭만 공격수입니다.", "경기장 밖까지 열기가 느껴지는 공격 펜싱의 대명사입니다."])
            elif tot_ls / (tot_matches if tot_matches else 1) <= 2.2: l1 = random.choice(["그 어떤 예리한 칼끝도 쉽게 뚫어내지 못하는 비브라늄급 방어력을 자랑합니다.", "상대를 지치게 만드는 늪지대 같은 수비로 승리를 갉아먹는 침착한 플레이어입니다."])
            elif avg_margin < -1.5: l1 = random.choice(["아직 공수 양면에서 폼이 완성되지 않았지만, 특유의 변칙적인 템포가 돋보입니다.", "점수를 내주면서도 실전을 통해 많은 것을 배우고 있는 성장형 펜서입니다."])
            else: l1 = random.choice(["공격과 수비의 밸런스를 유지하며, 어떤 상황에서도 유연하게 대처하는 능력을 지녔습니다.", "상황에 맞게 공수를 자유자재로 전환하는 지능적인 플레이가 장점입니다."])

            # Line 2: 멘탈/본선/행운
            if luck_index >= 15: l2 = random.choice(["기대 승률보다 훨씬 높은 실제 성적! 1점 차 피말리는 접전에서 묘하게 승리를 챙기는 클러치 달인입니다.", "운도 실력! 결정적인 순간에 발휘되는 엄청난 집중력과 승운이 따르는 선수입니다."])
            elif luck_index <= -15: l2 = random.choice(["스탯 내용은 훌륭하나 결과가 아쉬운 불운의 아이콘. 승운만 조금 터져주면 성적이 폭발할 것입니다.", "득실 마진은 좋으나 중요한 순간 1점을 내어주는 경향이 있습니다. 뒷심 극복이 관건입니다!"])
            elif choke_index <= -15 and pass_rate > 0: l2 = random.choice(["예선에서는 힘을 빼고 있다가 토너먼트에 진입하면 오히려 폼이 올라가는 '본선 여포' 기질이 다분합니다.", "큰 무대 체질! 지면 탈락하는 단판 승부에서 극강의 집중력을 발휘하는 승부사입니다."])
            elif choke_index >= 20 and pass_rate > 0: l2 = random.choice(["예선 생태계의 포식자! 다만 본선 단판 승부에서의 '새가슴' 기질을 극복하는 것이 최우선 과제입니다.", "예선 폼은 완벽하나 본선 첫 판에 굳어버리는 징크스가 있습니다. 마인드 컨트롤 훈련이 필요합니다."])
            else: l2 = random.choice(["매 경기 기복 없이 자신만의 확고한 템포로 묵묵하게 검을 휘두르는 안정적인 멘탈의 소유자입니다.", "흔들림 없는 평정심을 바탕으로 본인의 기량을 거짓 없이 정직하게 100% 발휘합니다."])

            # Line 3: 연령/잠재력
            if age_group == "초등부": l3 = random.choice(["무궁무진한 잠재력을 바탕으로 펜싱계의 미래를 밝힐 특급 신동입니다!", "스펀지처럼 기술을 흡수하며 하루가 다르게 폭풍 성장하고 있는 무서운 유소년 유망주입니다."])
            elif age_group == "중고등부": l3 = random.choice(["피지컬과 테크닉이 동시에 만개하는 시기! 청소년부 생태계를 지배할 차세대 에이스로 발돋움 중입니다.", "날카로운 반사신경과 패기로 무대를 휩쓸 준비가 끝난 청소년 기대주입니다."])
            elif age_group == "일반부": l3 = random.choice(["풍부한 인생 경험이 펜싱에도 녹아들어, 짬바에서 나오는 노련미가 일품인 성인부의 마스터입니다.", "퇴근 후 펜싱장에 인생을 바친 열정! 뇌지컬과 지능적인 플레이로 상대를 노련하게 요리합니다."])
            else: l3 = random.choice(["펜싱을 향한 순수한 열정으로 자신만의 무도를 완성해 나가는 멋진 검객입니다.", "성적을 떠나 검을 맞대는 순간 자체를 즐길 줄 아는 진정한 무도인의 자세를 갖췄습니다."])

            st.info(f"1️⃣ {l1}\n\n2️⃣ {l2}\n\n3️⃣ {l3}")
            random.seed()

            # --- 🏆 연령대 및 스탯 연동 칭호 ---
            st.divider()
            st.markdown("#### 🏆 획득 칭호 보드 (업적)")
            titles = []
            golds = len(p_data[p_data['본선_순위(숫자)'] == 1])
            silvers = len(p_data[p_data['본선_순위(숫자)'] == 2])
            
            if golds >= 5: titles.append(("👑 생태계 포식자", "우승 5회 이상. 말이 필요 없는 완벽한 지배자."))
            elif golds >= 1: titles.append(("🎖️ 챔피언", "시상대 최정상에 올라본 펜서."))
            if golds == 0 and silvers >= 2: titles.append(("🥈 콩라인", "결승에서만 미끄러지는 아쉬운 2인자!"))
            
            # 연령별 특수 칭호
            if age_group == "초등부" and golds >= 1: titles.append(("👶 언터쳐블 신동", "어린 나이에 우승을 차지한 될성부른 떡잎."))
            if age_group == "초등부" and pass_rate == 100: titles.append(("🚀 미래의 국대", "출전만 하면 본선에 직행하는 영재."))
            if age_group == "일반부" and p_data['레이팅(PT)'].sum() >= 300: titles.append(("👔 직장인 소드마스터", "야근을 뚫고 쟁취한 피땀 눈물의 랭커!"))
            
            # 세이버메트릭스 칭호
            if pythagorean >= 75: titles.append(("📐 피타고라스의 악마", "기대 승률 75% 이상. 완벽한 지표의 소유자."))
            if luck_index >= 15: titles.append(("🍀 럭키 가이 (클러치)", "실력 지표보다 실제 승률이 훨씬 높은 기적의 사나이."))
            if luck_index <= -15: titles.append(("☔ 억까의 아이콘", "지표는 깡패인데 승운이 안 따름. 조만간 떡상 예정."))
            if dom_rate >= 80 and tot_wins >= 5: titles.append(("🚀 학살자 (TDR)", "진땀승 따윈 없다. 오직 완벽한 완승뿐!"))
            if choke_index >= 25 and pass_rate > 0: titles.append(("🥶 본선 자동문 (새가슴)", "예선은 여포인데, 토너먼트만 가면 다리가 굳음."))
            if choke_index <= -20 and pass_rate > 0: titles.append(("🥷 다크템플러", "본선만 가면 눈빛이 바뀌는 토너먼트의 암살자."))
            
            if len(titles) == 0: titles.append(("👤 성실한 검사", "자신만의 무도를 묵묵히 걷고 있습니다."))

            t_col1, t_col2 = st.columns(2)
            for i, (t, desc) in enumerate(titles):
                col = t_col1 if i % 2 == 0 else t_col2
                col.markdown(f"<div style='padding:12px; background-color:#2a2a2a; border-radius:8px; margin-bottom:8px; border-left:4px solid #ffcc00;'><b>{t}</b><br><span style='font-size:12px;color:#aaa;'>{desc}</span></div>", unsafe_allow_html=True)

            # --- 방명록 ---
            st.divider()
            st.markdown(f"### 💬 {sel_player.split(' (')[0]} 선수 개인 팬명록")
            player_comments = st.session_state.comment_db[st.session_state.comment_db['대상선수'] == sel_player]
            if not player_comments.empty:
                for _, row in player_comments.sort_values(by='작성일시', ascending=False).iterrows():
                    st.markdown(f"<div style='background-color:#1e1e1e; padding:12px; border-left:4px solid #ff4b4b; border-radius:5px; margin-bottom:8px;'><b>{row['작성자']}</b> <span style='font-size:12px;color:#888;'>({row['작성일시']})</span><br><span style='color:#ddd; font-size:15px;'>{row['내용']}</span></div>", unsafe_allow_html=True)
            else:
                st.info("선수에게 첫 번째 응원 코멘트를 남겨주세요!")
            
            with st.form("player_comment_form", clear_on_submit=True):
                c_c1, c_c2 = st.columns([1, 4])
                with c_c1: author = st.text_input("닉네임", placeholder="무명검객")
                with c_c2: comment_text = st.text_input("코멘트 남기기", placeholder="이번 대회 화이팅!")
                if st.form_submit_button("📝 코멘트 등록") and comment_text.strip():
                    new_c = pd.DataFrame([{"대상선수": sel_player, "작성자": author if author else "익명", "내용": comment_text, "작성일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    st.session_state.comment_db = pd.concat([st.session_state.comment_db, new_c], ignore_index=True)
                    st.session_state.comment_db.to_csv(COMMENT_DB_FILE, index=False, encoding='utf-8-sig')
                    st.rerun()

# ================= TAB 5: 육각형 스탯 =================
with tabs[4]:
    st.subheader("💠 육각형(Hexagon) 스탯 레이더")
    if not global_db.empty:
        sel_hex_player = st.selectbox("선수 선택 (육각형)", ["선택"] + sorted(list(global_db['고유이름'].dropna().unique())))
        if sel_hex_player != "선택":
            p_h = global_db[global_db['고유이름'] == sel_hex_player]
            m_h = global_match[global_match['기준_고유'] == sel_hex_player]
            t_m = p_h['예선_승'].sum() + p_h['예선_패'].sum()
            
            s_atk = min(((p_h['예선_득점'].sum() / t_m if t_m>0 else 0) / 5.0) * 100, 100)
            s_def = max(100 - (((p_h['예선_실점'].sum() / t_m if t_m>0 else 5.0) / 5.0) * 100), 0)
            s_win = p_h['예선_승률(%)'].mean() if len(p_h) > 0 else 0
            s_exp = min((t_m / 50.0) * 100, 100)
            up_c = len(m_h[(m_h['단계'] == '본선') & (m_h['승패'] == '승') & (m_h['업셋여부'] == 'Y')])
            s_clu = min(((up_c * 2) / max(len(p_h), 1)) * 20, 100)
            s_luck = 50 

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[s_atk, s_def, s_win, s_exp, s_clu, s_luck, s_atk],
                theta=['공격력', '방어력', '승률', '경험치', '클러치(업셋)', '대진운', '공격력'],
                fill='toself', fillcolor='rgba(0, 191, 255, 0.5)', line=dict(color='#00bfff', width=2)
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white', size=14))
            st.plotly_chart(fig, use_container_width=True)

# ================= TAB 6: 1:1 라이벌 비교 =================
with tabs[5]:
    st.subheader("⚔️ 1:1 라이벌 정밀 비교")
    if not global_db.empty:
        c1, c2 = st.columns(2)
        with c1: pA = st.selectbox("🔴 선수 A", ["선택"] + sorted(list(global_db['고유이름'].dropna().unique())), key="pa")
        with c2: pB = st.selectbox("🔵 선수 B", ["선택"] + sorted(list(global_db['고유이름'].dropna().unique())), key="pb")
        
        if pA != "선택" and pB != "선택" and pA != pB:
            h2h = global_match[(global_match['기준_고유'] == pA) & (global_match['상대_고유'] == pB)]
            
            # 연령대 기반 라이벌 매치 코멘트
            ageA = get_age_group(global_db[global_db['고유이름']==pA]['부수'].iloc[-1])
            ageB = get_age_group(global_db[global_db['고유이름']==pB]['부수'].iloc[-1])
            intro_ment = "물러설 수 없는 자존심 매치!"
            if ageA == "초등부" and ageB == "초등부": intro_ment = "미래 국가대표들의 불꽃 튀는 펜싱 신동 매치! 🚀"
            elif ageA == "일반부" and ageB == "일반부": intro_ment = "퇴근 후 펜싱에 미친 두 마스터의 진검승부! ⚔️"
            elif ageA != ageB: intro_ment = f"{ageA}의 패기 vs {ageB}의 관록, 세대를 뛰어넘는 승부!"
            
            st.markdown(f"<h3 style='text-align: center;'>🥊 {intro_ment}</h3>", unsafe_allow_html=True)
            
            if not h2h.empty:
                st.success(f"🔥 **맞대결 전적: 🔴 {pA.split(' (')[0]} {len(h2h[h2h['승패']=='승'])}승 vs 🔵 {pB.split(' (')[0]} {len(h2h[h2h['승패']=='패'])}승**")
                st.dataframe(h2h[['대회일자', '대회명', '단계', '승패']].rename(columns={'승패':f'{pA.split(" (")[0]} 기준'}), use_container_width=True)
            else:
                st.info("공식 맞대결 기록이 없습니다. (AI 가상 시뮬레이션)")
                scA = global_db[global_db['고유이름']==pA]['레이팅(PT)'].sum()*0.5 + global_db[global_db['고유이름']==pA]['예선_승률(%)'].mean()*2.0
                scB = global_db[global_db['고유이름']==pB]['레이팅(PT)'].sum()*0.5 + global_db[global_db['고유이름']==pB]['예선_승률(%)'].mean()*2.0
                probA = (scA/(scA+scB))*100 if (scA+scB)>0 else 50.0
                st.markdown(f"<h3 style='text-align: center;'>🤖 AI 승률 예측: 🔴 {pA.split(' (')[0]} {probA:.1f}% vs 🔵 {pB.split(' (')[0]} {100-probA:.1f}%</h3>", unsafe_allow_html=True)
                st.progress(probA / 100)

# ================= TAB 7: 다자간 시뮬레이터 (멀티셀렉트 완벽 해결) =================
with tabs[6]:
    st.subheader("🔮 다음 대회 예측 시뮬레이터 (다중 선택)")
    st.markdown("텍스트 입력이 아닙니다! 출전 선수들을 클릭해서 체크 박스로 자유롭게 담아보세요. 상성 관계를 즉시 분석합니다.")
    if not global_db.empty:
        all_players_list = sorted(list(global_db['고유이름'].dropna().unique()))
        
        # 💡 [요청] 텍스트 입력의 버그를 잡은 직관적인 체크박스 멀티셀렉트 방식 적용
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
                    ss = sim_db.groupby('고유이름').agg(누적PT=('레이팅(PT)', 'sum'), 승률=('예선_승률(%)', 'mean')).reset_index().sort_values('누적PT', ascending=False)
                    ss.index += 1
                    st.dataframe(ss, use_container_width=True)
            else:
                st.warning("선수를 명단에서 선택해 주세요.")

# ================= TAB 8: 관리자 설정 (업로드 및 일정) =================
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
                
                # --- 기존 V29의 엑셀 파싱 로직을 한 글자도 빠짐없이 100% 동일하게 이식 ---
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
