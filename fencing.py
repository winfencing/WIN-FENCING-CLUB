import streamlit as st
import pandas as pd
import os
import re

st.set_page_config(page_title="윈펜싱클럽 전력 분석 V26.0 MAX", page_icon="🤺", layout="wide")

st.title("🤺 윈펜싱클럽 통합 전력 분석 대시보드 (V26.0 찐막 종결판)")
st.markdown("지역 랭킹 삭제, 라이벌 3단 필터, 클럽 전체 로스터, 명예의 전당 Top 10 확장 및 신규 칭호가 대거 추가된 갓벽 최종 버전입니다!")

PLAYER_DB_FILE = "fencing_player_db.csv"
MATCH_DB_FILE = "fencing_match_db.csv"

# 🌟 데이터 초기화
with st.sidebar:
    st.warning("⚠️ 새 버전을 깔았거나 랭킹이 꼬였을 때")
    if st.button("🗑️ 데이터 완전 초기화 (필수)"):
        if os.path.exists(PLAYER_DB_FILE): os.remove(PLAYER_DB_FILE)
        if os.path.exists(MATCH_DB_FILE): os.remove(MATCH_DB_FILE)
        if 'player_db' in st.session_state: del st.session_state.player_db
        if 'match_db' in st.session_state: del st.session_state.match_db
        st.success("데이터 리셋 완료! 원본 엑셀을 다시 올려주세요.")
        st.rerun()

if 'player_db' not in st.session_state:
    if os.path.exists(PLAYER_DB_FILE): st.session_state.player_db = pd.read_csv(PLAYER_DB_FILE)
    else: st.session_state.player_db = pd.DataFrame()

if 'match_db' not in st.session_state:
    if os.path.exists(MATCH_DB_FILE): st.session_state.match_db = pd.read_csv(MATCH_DB_FILE)
    else: st.session_state.match_db = pd.DataFrame()

global_db = st.session_state.player_db.copy()
global_match = st.session_state.match_db.copy()

# 데이터 전처리 (숫자형 유지 및 구버전 데이터 완벽 호환)
if not global_db.empty:
    global_db['대회일자'] = pd.to_datetime(global_db['대회일자'], errors='coerce')
    global_db['연도'] = global_db['대회일자'].dt.year.fillna(2026).astype(int).astype(str)
    global_db['본선_순위(숫자)'] = pd.to_numeric(global_db['본선_순위(숫자)'], errors='coerce')
    global_db['예선_순위(숫자)'] = pd.to_numeric(global_db['예선_순위(숫자)'], errors='coerce')
    global_db['레이팅(PT)'] = pd.to_numeric(global_db['레이팅(PT)'], errors='coerce')
    global_db['예선_승률(%)'] = pd.to_numeric(global_db['예선_승률(%)'], errors='coerce')
    
    for col in ['예선_승', '예선_패', '예선_득점', '예선_실점']:
        if col not in global_db.columns:
            global_db[col] = 0
        else:
            global_db[col] = pd.to_numeric(global_db[col], errors='coerce').fillna(0)

if not global_match.empty:
    global_match['대회일자'] = pd.to_datetime(global_match['대회일자'], errors='coerce')
    global_match['연도'] = global_match['대회일자'].dt.year.fillna(2026).astype(int).astype(str)

# 🔍 글로벌 대/중/소 필터
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📂 성적 업로드", "🏆 종합 랭킹 보드", "🏢 클럽 스탯 & 명예의전당", 
    "🎮 선수 개인 스탯 & 칭호", "⚔️ 1:1 라이벌 비교", "🔮 다음 대회 시뮬레이터"
])

with tab1:
    st.subheader("새로운 대회 성적 입력")
    st.info("💡 펜싱협회 웹사이트에서 표를 전체 드래그해서 빈 엑셀에 붙여넣고, **아무것도 수정하지 말고 그대로 저장**해서 올리십시오!")
    
    col1, col2 = st.columns(2)
    with col1: tourney_name = st.text_input("대회명 (예: 26년 8월 협회장배)")
    with col2: tourney_date = st.date_input("대회 일자")
        
    uploaded_file = st.file_uploader("복사한 원본 엑셀 파일(.xlsx) 업로드", type=['xlsx'])
    
    if st.button("데이터베이스에 추가하기 (자동 저장)"):
        if uploaded_file is not None and tourney_name:
            if not st.session_state.player_db.empty and tourney_name in st.session_state.player_db['대회명'].values:
                st.warning("이미 등록된 대회입니다! 꼬였다면 사이드바 초기화를 눌러주세요.")
            else:
                try: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='calamine', header=None)
                except: sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl', header=None)

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
                
                for sheet_name, df in sheets.items():
                    if df.empty or "단체" in sheet_name or "단체" in tourney_name: continue 
                    
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
                            team1 = str(p1_r[cmap.get('소속팀')]).strip() if '소속팀' in cmap and cmap.get('소속팀') < len(p1_r) else ""
                            
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
                                '대회일자': str(tourney_date), '대회명': tourney_name, '부수': sheet_name,
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
                            new_matches.append({
                                '대회일자': str(tourney_date), '대회명': tourney_name, '부수': sheet_name,
                                '기준선수': p['이름'], '기준팀': p['소속팀'], '상대선수': o_name, '상대팀': t_dict.get(o_name, ""),
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
                                    new_matches.append({'대회일자': str(tourney_date), '대회명': tourney_name, '부수': sheet_name, '기준선수': w['이름'], '기준팀': w['소속팀'], '상대선수': l['이름'], '상대팀': l['소속팀'], '승패': '승', '단계': '본선', '업셋여부': is_up, '진땀승':'N'})
                                    new_matches.append({'대회일자': str(tourney_date), '대회명': tourney_name, '부수': sheet_name, '기준선수': l['이름'], '기준팀': l['소속팀'], '상대선수': w['이름'], '상대팀': w['소속팀'], '승패': '패', '단계': '본선', '업셋여부': 'N', '진땀승':'N'})
                                    nr.append(w)
                            cr = nr
                
                if new_players:
                    st.session_state.player_db = pd.concat([st.session_state.player_db, pd.DataFrame(new_players)], ignore_index=True)
                    st.session_state.match_db = pd.concat([st.session_state.match_db, pd.DataFrame(new_matches)], ignore_index=True)
                    st.session_state.player_db.to_csv(PLAYER_DB_FILE, index=False, encoding='utf-8-sig')
                    st.session_state.match_db.to_csv(MATCH_DB_FILE, index=False, encoding='utf-8-sig')
                    st.success(f"✅ {tourney_name} 데이터 파싱 완료! 랭킹 표 누락 100% 픽스 완료!")
                    st.rerun()
        else:
            st.warning("대회명과 파일을 모두 입력해 주십시오.")

with tab2:
    st.subheader("🏆 종합 랭킹 보드")
    st.markdown("모든 표는 제목을 클릭하면 **오름차순/내림차순 정렬**이 완벽하게 지원됩니다. (지역 분류 삭제 완료!)")
    if not global_db.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### 🏢 전국 클럽 파워 스탯 랭킹 (팀 대항전)")
            cs = global_db.groupby('소속팀').agg(
                총원=('이름', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 평균PT=('레이팅(PT)', 'mean'),
                금메달=('본선_순위(숫자)', lambda x: (x.dropna() == 1).sum()), 은메달=('본선_순위(숫자)', lambda x: (x.dropna() == 2).sum()), 동메달=('본선_순위(숫자)', lambda x: x.dropna().isin([3, 4]).sum())
            ).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            cs.index += 1
            st.dataframe(cs, column_config={
                "합산PT": st.column_config.NumberColumn("합산 레이팅", format="%.0f pt"),
                "평균PT": st.column_config.NumberColumn("클럽 평균전력", format="%.1f pt")
            }, use_container_width=True)

        with c2:
            st.markdown("#### 🤺 선수 종합 스탯 랭킹 (전국 통합)")
            ps = global_db.sort_values('대회일자').groupby('이름').agg(
                최근소속팀=('소속팀', 'last'), 역대소속=('소속팀', lambda x: ", ".join(list(set(x.dropna())))),
                출전=('대회명', 'nunique'), 합산PT=('레이팅(PT)', 'sum'), 평균PT=('레이팅(PT)', 'mean'),
                승률=('예선_승률(%)', 'mean'), 평균예선=('예선_순위(숫자)', 'mean'), 평균본선=('본선_순위(숫자)', 'mean')
            ).reset_index().sort_values(by='합산PT', ascending=False).reset_index(drop=True)
            ps.index += 1
            st.dataframe(ps, column_config={
                "합산PT": st.column_config.NumberColumn("합산 레이팅", format="%.0f pt"),
                "평균PT": st.column_config.NumberColumn("평균 레이팅", format="%.1f pt"),
                "승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%"),
                "평균예선": st.column_config.NumberColumn("평균 예선", format="%.1f위"),
                "평균본선": st.column_config.NumberColumn("평균 본선", format="%.1f위")
            }, use_container_width=True)

with tab3:
    st.subheader("🏢 클럽 정밀 분석 & 명예의 전당 Top 10")
    if not global_db.empty:
        my_team = st.selectbox("분석할 클럽(소속팀)을 선택하세요.", ["선택"] + sorted(list(global_db['소속팀'].dropna().unique())))
        if my_team != "선택":
            h_db = global_db[global_db['소속팀'] == my_team]
            h_match = global_match[global_match['기준팀'] == my_team]
            
            t_pts = h_db['레이팅(PT)'].sum()
            t_win = h_db['예선_승률(%)'].mean()
            t_mems = h_db['이름'].nunique()
            t_upsets = len(h_match[(h_match['단계'] == '본선') & (h_match['승패'] == '승') & (h_match['업셋여부'] == 'Y')])
            
            st.markdown(f"### 🛡️ {my_team} 클럽 전력 분석실")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 등록 선수", f"{t_mems}명")
            c2.metric("클럽 총 누적 레이팅", f"{t_pts:.0f} PT")
            c3.metric("클럽 평균 승률", f"{t_win:.1f}%")
            c4.metric("클럽 총 자이언트 킬링", f"{t_upsets}회")
            
            st.markdown("---")
            st.markdown(f"### 🏅 {my_team} 명예의 전당 (Top 10)")
            s1, s2, s3, s4 = st.columns(4)
            
            golds = h_db[h_db['본선_순위(숫자)'] == 1].groupby('이름').size().reset_index(name='금메달').sort_values('금메달', ascending=False).head(10)
            s1.success("👑 **[우승 제조기]**\n\n클럽 내 1위 입상 횟수 Top 10")
            for i, row in golds.iterrows(): s1.write(f"- {row['이름']} (금 {row['금메달']}개)")
            
            medals = h_db[h_db['본선_순위(숫자)'] <= 4].groupby('이름').size().reset_index(name='메달').sort_values('메달', ascending=False).head(10)
            s2.warning("🎖️ **[메달 콜렉터]**\n\n포디움(1~3위) 입상 Top 10")
            for i, row in medals.iterrows(): s2.write(f"- {row['이름']} (총 {row['메달']}회)")

            wk = h_db.groupby('이름').agg(승률=('예선_승률(%)','mean'), 출전=('대회명','nunique')).reset_index()
            wk = wk[wk['출전'] >= 1].sort_values('승률', ascending=False).head(10)
            s3.info("🔥 **[최고 승률왕]**\n\n예선 평균 승률 Top 10")
            for i, row in wk.iterrows(): s3.write(f"- {row['이름']} ({row['승률']:.1f}%)")
            
            up_king = h_match[(h_match['단계'] == '본선') & (h_match['승패'] == '승') & (h_match['업셋여부'] == 'Y')].groupby('기준선수').size().reset_index(name='업셋').sort_values('업셋', ascending=False).head(10)
            s4.error("⚡ **[자이언트 킬러]**\n\n본선 업셋 승리 Top 10")
            for i, row in up_king.iterrows(): s4.write(f"- {row['기준선수']} ({row['업셋']}회)")

            st.divider()
            s5, s6, s7, s8 = st.columns(4)

            apps = h_db.groupby('이름')['대회명'].nunique().reset_index(name='출전').sort_values('출전', ascending=False).head(10)
            s5.info("🏃 **[강철 체력 / 개근상]**\n\n최다 대회 출전 Top 10")
            for i, row in apps.iterrows(): s5.write(f"- {row['이름']} (총 {row['출전']}회 출전)")
            
            sm = h_db.groupby('이름').agg(득점=('예선_득점','sum'), 예선승=('예선_승','sum'), 실점=('예선_실점','sum'), 예선패=('예선_패','sum')).reset_index() 
            sm['경기수'] = sm['예선승'] + sm['예선패']
            sm['평균득점'] = (sm['득점'] / sm['경기수']).fillna(0)
            s6.warning("🗡️ **[여포 / 득점 머신]**\n\n경기당 최고 득점 Top 10")
            for i, row in sm[sm['평균득점'] > 0].sort_values('평균득점', ascending=False).head(10).reset_index().iterrows(): s6.write(f"- {row['이름']} (평균 {row['평균득점']:.1f}점)")
            
            sm['평균실점'] = (sm['실점'] / sm['경기수']).fillna(0)
            s7.success("🛡️ **[통곡의 벽]**\n\n경기당 최소 실점 Top 10")
            for i, row in sm[sm['평균실점'] > 0].sort_values('평균실점', ascending=True).head(10).reset_index().iterrows(): s7.write(f"- {row['이름']} (평균 {row['평균실점']:.1f}점)")
            
            ls = h_db.groupby('이름')['예선_패'].sum().reset_index(name='패배수').sort_values('패배수', ascending=False).head(10)
            s8.error("😭 **[수난시대 / 성장형]**\n\n가장 많은 패배를 이겨내는 중")
            for i, row in ls.iterrows(): s8.write(f"- {row['이름']} (총 {row['패배수']}패)")

            st.markdown("---")
            st.markdown(f"### 📋 {my_team} 소속 선수 전체 스탯 로스터")
            st.markdown("해당 클럽에 속한 **전체 선수들의 요약 스탯**입니다. 제목을 클릭하여 정렬할 수 있습니다.")
            roster = h_db.groupby('이름').agg(
                출전대회=('대회명', 'nunique'),
                누적레이팅=('레이팅(PT)', 'sum'),
                평균레이팅=('레이팅(PT)', 'mean'),
                평균승률=('예선_승률(%)', 'mean'),
                예선승=('예선_승', 'sum'),
                예선패=('예선_패', 'sum'),
                본선최고순위=('본선_순위(숫자)', 'min')
            ).reset_index().sort_values('누적레이팅', ascending=False).reset_index(drop=True)
            roster.index += 1
            st.dataframe(roster, column_config={
                "누적레이팅": st.column_config.NumberColumn("총 PT", format="%.0f pt"),
                "평균레이팅": st.column_config.NumberColumn("평균 PT", format="%.1f pt"),
                "평균승률": st.column_config.NumberColumn("승률", format="%.1f%%"),
                "본선최고순위": st.column_config.NumberColumn("커리어하이", format="%.0f위")
            }, use_container_width=True)

with tab4:
    st.subheader("🎮 선수 개인 정밀 분석 & 스탯창")
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
            players = sorted(list(db_t3['이름'].dropna().unique()))
            sel_player = st.selectbox("3. 선수 이름 검색", ["선수를 선택하십시오."] + players)
        
        if sel_player != "선수를 선택하십시오.":
            p_data = global_db[global_db['이름'] == sel_player].sort_values('대회일자')
            m_data = global_match[global_match['기준선수'] == sel_player]
            
            # 티어 계산
            all_pts = global_db.groupby('이름')['레이팅(PT)'].mean()
            my_pt = all_pts.get(sel_player, 0)
            t_str = "배치 중"
            if len(all_pts) > 1:
                pct = (all_pts > my_pt).mean() * 100
                if pct <= 5: t_str = "💎 챌린저 (상위 5%)"
                elif pct <= 15: t_str = "🥇 마스터 (상위 15%)"
                elif pct <= 30: t_str = "🥈 다이아몬드 (상위 30%)"
                elif pct <= 50: t_str = "🥉 플래티넘 (상위 50%)"
                elif pct <= 75: t_str = "🟢 골드"
                else: t_str = "⚪ 실버"

            # 🎲 대진운 
            luck_l = []
            for tn in p_data['대회명']:
                opps = m_data[(m_data['단계']=='예선') & (m_data['대회명']==tn)]['상대선수']
                if len(opps) > 0: luck_l.append(opps.map(all_pts).fillna(5).mean())
                else: luck_l.append(5.0)
            avg_luck = sum(luck_l)/len(luck_l) if luck_l else 5.0

            titles = []
            tot_m = p_data['예선_승'].sum() + p_data['예선_패'].sum()
            avg_wr = p_data['예선_승률(%)'].mean()
            tot_pt = p_data['레이팅(PT)'].sum()
            num_tourneys = len(p_data)
            
            golds = len(p_data[p_data['본선_순위(숫자)'] == 1])
            silvers = len(p_data[p_data['본선_순위(숫자)'] == 2])
            medals = len(p_data[p_data['본선_순위(숫자)'].isin([1, 2, 3, 4])])
            up_cnt = len(m_data[(m_data['단계'] == '본선') & (m_data['승패'] == '승') & (m_data['업셋여부'] == 'Y')])
            sweats = len(m_data[(m_data['단계'] == '예선') & (m_data['진땀승'] == 'Y')])

            # 칭호 시스템 대규모 업데이트
            if golds >= 1: titles.append(("🥇 챔피언", "대회 우승을 차지해본 진정한 실력자"))
            elif golds >= 3: titles.append(("🏆 다이너스티", "대회 우승 3회 이상! 왕조를 건설한 절대자"))
            
            if medals >= 3: titles.append(("🎖️ 메달 콜렉터", "입상(4강 이상) 3회 이상의 검증된 강자"))
            if silvers >= 2 and golds == 0: titles.append(("🥈 콩라인", "아쉬운 준우승만 2번 이상.. 다음엔 기필코 우승!"))
            
            if tot_pt >= 300: titles.append(("👑 그랜드마스터", "누적 레이팅 300PT 이상! 서버를 지배하는 자"))
            elif tot_pt >= 150: titles.append(("🌟 마스터 검사", "누적 레이팅 150PT 돌파한 최상위권 엘리트"))
            
            if avg_wr >= 80 and num_tourneys >= 2: titles.append(("🔥 절대존엄", "압도적인 평균 승률 80% 이상의 지배자"))
            elif avg_wr == 100 and num_tourneys >= 1: titles.append(("✨ 무결점의 챔피언", "단 한 번의 예선 패배도 허용하지 않은 완벽주의자"))
            
            if tot_m >= 30: titles.append(("💪 강철 체력", "공식전 30경기 이상을 소화한 펜싱 열정러"))
            if num_tourneys >= 5: titles.append(("🏃 철인 (개근상)", f"무려 {num_tourneys}번의 대회에 출전한 엄청난 펜싱 사랑!"))
            
            avg_sc = (p_data['예선_득점'].sum() / tot_m) if tot_m > 0 else 0
            avg_ls = (p_data['예선_실점'].sum() / tot_m) if tot_m > 0 else 0
            if avg_sc >= 4.2 and avg_ls >= 4.0: titles.append(("⚔️ 낭만 검객 (유리대포)", "방어는 버렸다! 점수도 많이 뽑고 많이 잃는 상남자/상여자형 펜서"))
            elif avg_sc >= 4.2: titles.append((f"🗡️ 여포 (닥공형)", f"매 경기 평균 {avg_sc:.1f}득점을 내리꽂는 파괴전차"))
            elif 0 < avg_ls <= 2.2 and tot_m > 0: titles.append((f"🛡️ 통곡의 벽", f"경기당 평균 {avg_ls:.1f}실점만 내주는 철벽 방어막"))
            
            if avg_wr < 50 and up_cnt >= 1: titles.append(("🥷 암살자", "예선 승률은 낮아도 본선에서 상위 랭커의 목을 벰"))
            elif up_cnt >= 2: titles.append((f"⚡ 자이언트 킬러", f"본선에서 상위 시더의 목을 벤 업셋 이변 {up_cnt}회"))
            
            if sweats >= 3: titles.append(("💦 진땀 승부사 (클러치 마스터)", f"1점 차(V1~V4) 피말리는 승부를 {sweats}번이나 이겨낸 강심장"))

            if avg_luck >= 35 and p_data['본선_순위(숫자)'].min() <= 8: titles.append(("💎 낭중지추", "역대급 지옥의 조를 뚫고 8강 이상 진출한 진짜 에이스"))
            if p_data['예선_패'].sum() >= 15: titles.append(("🌱 대기만성 (성장형 아이콘)", "수많은 패배를 거름 삼아 묵묵히 전진 중인 대기만성형"))

            st.markdown(f"### 🎖️ {sel_player} 선수의 프로필 및 획득 칭호")
            st.success(f"**현재 티어: {t_str}** | 🎲 평균 대진운: {avg_luck:.1f}pt")
            for t, desc in titles:
                st.markdown(f"<div style='padding:8px; background-color:#1e1e1e; border-radius:5px; margin-bottom:4px;'><b>{t}</b><br><span style='color:#aaaaaa; font-size:13px;'>- {desc}</span></div>", unsafe_allow_html=True)
            
            st.markdown("#### 📊 스탯 보드")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("총 출전 대회", f"{len(p_data)}회")
            s2.metric("누적 레이팅", f"{tot_pt:.0f} PT")
            s3.metric("평균 승률", f"{avg_wr:.1f}%")
            best_r = p_data['본선_순위(숫자)'].min()
            s4.metric("커리어 하이", f"{best_r:.0f}위" if pd.notna(best_r) else "-")

            def g_luck(pt):
                if pt >= 40: return f"💀 지옥 뿔 ({pt:.1f})"
                if pt >= 25: return f"⚔️ 험난 뿔 ({pt:.1f})"
                if pt >= 15: return f"😐 평이 ({pt:.1f})"
                return f"🍯 꿀통 뿔 ({pt:.1f})"
            p_data['대진운'] = [g_luck(x) for x in luck_l]
            
            st.markdown("#### 📜 대회별 상세 기록 & 대진운")
            st.dataframe(p_data[['대회명', '부수', '소속팀', '예선_승률(%)', '예선_랭킹', '본선_랭킹', '레이팅(PT)', '대진운']], use_container_width=True, hide_index=True)
            
            st.markdown("#### ⚔️ 라이벌 / 상대 전적 분석 (Top 10)")
            if not m_data.empty:
                # 1. 통합 전적 (예선+본선)
                st.markdown("##### 🌐 [통합] 영혼의 맞대결 (예선+본선 합산)")
                c_tot1, c_tot2 = st.columns(2)
                ot = m_data.groupby(['상대선수', '상대팀']).agg(전적=('승패','count'), 승=('승패', lambda x:(x=='승').sum()), 패=('승패', lambda x:(x=='패').sum())).reset_index()
                c_tot1.error("🚨 [통합] 천적 Top 10 (패배순)")
                for _, r in ot[ot['패']>0].sort_values(by=['패', '전적'], ascending=[False, True]).head(10).iterrows(): c_tot1.write(f"- **{r['상대선수']}** ({r['상대팀']}): {r['승']}승 {r['패']}패")
                c_tot2.success("🎯 [통합] 훌륭한 단백질 공급원 Top 10 (승리순)")
                for _, r in ot[ot['승']>0].sort_values(by=['승', '전적'], ascending=[False, True]).head(10).iterrows(): c_tot2.write(f"- **{r['상대선수']}** ({r['상대팀']}): {r['승']}승 {r['패']}패")

                st.markdown("---")
                
                # 2. 예선 전적
                h_pre = m_data[m_data['단계'] == '예선']
                if not h_pre.empty:
                    st.markdown("##### 🤺 [예선 뿔] 상세 전적")
                    c1, c2 = st.columns(2)
                    op = h_pre.groupby(['상대선수', '상대팀']).agg(전적=('승패','count'), 승=('승패', lambda x:(x=='승').sum()), 패=('승패', lambda x:(x=='패').sum())).reset_index()
                    c1.error("🚨 예선 천적 Top 10")
                    for _, r in op[op['패']>0].sort_values(by=['패', '전적'], ascending=[False, True]).head(10).iterrows(): c1.write(f"- **{r['상대선수']}** ({r['상대팀']}): {r['승']}승 {r['패']}패")
                    c2.success("🎯 예선 승리 자판기 Top 10")
                    for _, r in op[op['승']>0].sort_values(by=['승', '전적'], ascending=[False, True]).head(10).iterrows(): c2.write(f"- **{r['상대선수']}** ({r['상대팀']}): {r['승']}승 {r['패']}패")

                # 3. 본선 전적
                h_main = m_data[m_data['단계'] == '본선']
                if not h_main.empty:
                    st.markdown("##### 🏆 [본선 토너먼트] 상세 전적")
                    c3, c4 = st.columns(2)
                    om = h_main.groupby(['상대선수', '상대팀']).agg(전적=('승패','count'), 승=('승패', lambda x:(x=='승').sum()), 패=('승패', lambda x:(x=='패').sum())).reset_index()
                    c3.error("🚨 본선 탈락의 주범 Top 10")
                    for _, r in om[om['패']>0].sort_values(by=['패', '전적'], ascending=[False, True]).head(10).iterrows(): c3.write(f"- **{r['상대선수']}** ({r['상대팀']}): {r['승']}승 {r['패']}패")
                    c4.success("🎯 본선 제물 Top 10")
                    for _, r in om[om['승']>0].sort_values(by=['승', '전적'], ascending=[False, True]).head(10).iterrows(): c4.write(f"- **{r['상대선수']}** ({r['상대팀']}): {r['승']}승 {r['패']}패")

with tab5:
    st.subheader("⚔️ 1:1 라이벌 전적 정밀 비교 (3단 정밀 필터)")
    st.markdown("선수 2명을 선택하여, **누가 더 우세한지 맞대결 기록**을 상세히 분석합니다. 예선과 본선에서의 성적도 따로 분리해서 보여드립니다!")
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
            
            players_a = sorted(list(db_a['이름'].dropna().unique()))
            pA = st.selectbox("3. 🔴 최종 A 선수", ["선택"] + players_a, key="pa")

        with c2:
            st.markdown("#### 🔵 선수 B 선택")
            divs_b = ["전체"] + sorted(list(global_db['부수'].dropna().unique()))
            sel_div_b = st.selectbox("1. B선수 부수 선택", divs_b, key="div_b")
            db_b = global_db if sel_div_b == "전체" else global_db[global_db['부수'] == sel_div_b]
            
            teams_b = ["전체"] + sorted(list(db_b['소속팀'].dropna().unique()))
            sel_team_b = st.selectbox("2. B선수 클럽 선택", teams_b, key="team_b")
            if sel_team_b != "전체": db_b = db_b[db_b['소속팀'] == sel_team_b]
            
            players_b = sorted(list(db_b['이름'].dropna().unique()))
            pB = st.selectbox("3. 🔵 최종 B 선수", ["선택"] + players_b, key="pb")
        
        st.divider()

        if pA != "선택" and pB != "선택":
            if pA == pB:
                st.warning("같은 선수를 선택했습니다. 다른 선수를 골라주세요!")
            else:
                h2h = global_match[(global_match['기준선수'] == pA) & (global_match['상대선수'] == pB)]
                st.markdown(f"<h3 style='text-align: center;'>🥊 {pA} vs {pB} 맞대결 스코어</h3>", unsafe_allow_html=True)
                if h2h.empty: st.info("두 선수의 맞대결 기록이 없습니다. (미지의 승부!)")
                else:
                    a_tot = len(h2h[h2h['승패'] == '승'])
                    b_tot = len(h2h[h2h['승패'] == '패'])
                    
                    prelim_m = h2h[h2h['단계'] == '예선']
                    main_m = h2h[h2h['단계'] == '본선']
                    
                    a_pre, b_pre = len(prelim_m[prelim_m['승패'] == '승']), len(prelim_m[prelim_m['승패'] == '패'])
                    a_main, b_main = len(main_m[main_m['승패'] == '승']), len(main_m[main_m['승패'] == '패'])
                    
                    st.success(f"🔥 **종합 전적: 총 {len(h2h)}전 ➡️ 🔴 {pA} {a_tot}승 / 🔵 {pB} {b_tot}승**")
                    
                    m1, m2 = st.columns(2)
                    m1.info(f"**[예선 기록] 🔴 {pA} {a_pre}승 / 🔵 {pB} {b_pre}승**")
                    m2.error(f"**[본선 기록] 🔴 {pA} {a_main}승 / 🔵 {pB} {b_main}승**")
                    
                    df_h2h = h2h[['대회명', '단계', '승패']].rename(columns={'승패':f'{pA} 기준 결과'}).sort_values('대회명', ascending=False).reset_index(drop=True)
                    df_h2h[f'{pA} 기준 결과'] = df_h2h[f'{pA} 기준 결과'].apply(lambda x: f"🔴 {pA} 승리" if x == '승' else f"🔵 {pB} 승리")
                    st.dataframe(df_h2h, use_container_width=True)

with tab6:
    st.subheader("🔮 대회 예상 시뮬레이터 (천적 경보)")
    entry_list_text = st.text_area("출전 선수 이름 입력 (쉼표나 엔터로 구분)", placeholder="예시: 권구현, 한준아, 박시원, 장우진")
    if st.button("예상 등수 시뮬레이션 가동"):
        if entry_list_text and not global_db.empty:
            names = [n.strip() for n in re.split(r'[,\n]+', entry_list_text) if n.strip()]
            sim_db = global_db[global_db['이름'].isin(names)]
            
            if not sim_db.empty:
                if len(names) >= 2 and not global_match.empty:
                    rel_m = global_match[global_match['기준선수'].isin(names) & global_match['상대선수'].isin(names)]
                    alerts = []
                    for pn in names:
                        pm = rel_m[rel_m['기준선수'] == pn]
                        for on in pm['상대선수'].unique():
                            h = pm[pm['상대선수'] == on]
                            w, l = len(h[h['승패'] == '승']), len(h[h['승패'] == '패'])
                            if w == 0 and l >= 1: alerts.append(f"🚨 **[{pn}]** 선수 비상! 단 한 번도 이겨보지 못한 천적 **[{on}]** 출전! ({l}전 전패)")
                    for a in list(set(alerts)): st.error(a)

                all_pts_sim = global_db.groupby('이름')['레이팅(PT)'].mean()
                def calc_luck(pn):
                    opps = global_match[(global_match['단계']=='예선') & (global_match['기준선수']==pn)]['상대선수']
                    if len(opps) == 0: return "평이"
                    avg_pt = opps.map(all_pts_sim).fillna(20).mean() 
                    if avg_pt >= 40: return f"💀 지옥 뿔 ({avg_pt:.1f}pt)"
                    if avg_pt <= 15: return f"🍯 꿀통 뿔 ({avg_pt:.1f}pt)"
                    return f"😐 평이 ({avg_pt:.1f}pt)"

                ss = sim_db.groupby(['이름', '소속팀']).agg(합산PT=('레이팅(PT)', 'sum'), 평균승률=('예선_승률(%)', 'mean')).reset_index()
                ss['예상 대진운'] = ss['이름'].apply(calc_luck)
                ss = ss.sort_values(by=['합산PT', '평균승률'], ascending=[False, False]).reset_index(drop=True)
                ss.index += 1
                
                st.dataframe(ss, column_config={
                    "합산PT": st.column_config.NumberColumn("누적 레이팅", format="%.1f pt"),
                    "평균승률": st.column_config.NumberColumn("평균 승률", format="%.1f%%")
                }, use_container_width=True)
            else: st.warning("기록이 없습니다.")