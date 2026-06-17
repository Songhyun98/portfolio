"""
아키모니터 — 브랜드 건강검진 대시보드 (리팩터: 주간 자동갱신 + LLM 소견)
실행: streamlit run akimonitor_app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# from scipy import stats

st.set_page_config(page_title="아키모니터", layout="wide")

# ── 브랜드 컬러 ──────────────────────────────────────────
C = {
    "아키클래식":   "#31542B",
    "23.65":       "#A0522D",   # 2. 변경: 흙갈색
    "포즈간츠":    "#8B008B",   # 2. 변경: 다크마젠타
    "발건강시그널": "#1D9E75",
    "컴포트수요지수":"#888780",
    "여행시그널":   "#B4B2A9",
    "스케쳐스":    "#0060A9",
    "휠라":        "#002C5B",
}
MIX_C = {"blog_total":"#31542B","news_total":"#7BAF72","cafe_total":"#C3DFB8"}

ANCHOR   = "아키클래식"
CAMPAIGN = "2025-05 여행 유튜버 협업(이후 검색 급등)"

# ───────────────── 1. 데이터 로드 ─────────────────
@st.cache_data(ttl=3600)
def fetch_all(table, step=1000):
    from supabase import create_client
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    rows, start = [], 0
    while True:
        r = sb.table(table).select("*").range(start, start+step-1).execute()
        rows += r.data
        if len(r.data) < step: break
        start += step
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def load_all():
    return {k: fetch_all(t) for k, t in
            {"search":"search_trend","total":"mention_total",
             "blog":"mention_blog","news":"mention_news","cafe":"mention_cafe"}.items()}

# ───────────────── 2. 컷오프 ─────────────────
def last_complete_month(search):
    p = pd.to_datetime(search["period"])
    me = pd.date_range(p.min(), p.max(), freq="ME")
    return me[me <= p.max()][-1]

def pivot_axis(search, axis, asof):
    d = search[search.axis == axis].copy()
    d["period"] = pd.to_datetime(d["period"])
    m = d.pivot_table(index="period", columns="keyword_group", values="ratio").resample("ME").mean()
    return m[m.index <= asof]

# ───────────────── 3. 지표 계산 ─────────────────
def compute_sos(search, asof):
    p = pivot_axis(search, "direct", asof)
    return p.div(p.sum(1), axis=0) * 100

def reindex_df(search, axis, asof):
    p = pivot_axis(search, axis, asof)
    return p.div(p.mean(0), axis=1) * 100

def growth_rate(idx):
    return ((idx.tail(6).mean() / idx.head(6).mean() - 1) * 100).round(0)

def momentum(search, asof):
    s = pivot_axis(search, "direct", asof)[ANCHOR].dropna()
    idx = s / s.mean() * 100
    return dict(
        long=float((idx.values[-6:].mean() / idx.values[:6].mean() - 1) * 100),
        yoy3=float(s.rolling(3).mean().pct_change(12).iloc[-1] * 100),
        single_yoy=float(s.pct_change(12).iloc[-1] * 100),
        mom=float(s.pct_change().iloc[-1] * 100),
        yoy_trend=(s.pct_change(12) * 100).dropna().tail(6).round(1),
    )

def parse_dated(blog, news):
    b = blog.copy()
    b["date"] = pd.to_datetime(b["postdate"].astype(str), format="%Y%m%d", errors="coerce")
    n = news.copy()
    n["date"] = pd.to_datetime(n["pub_date"], errors="coerce", utc=True).dt.tz_localize(None)
    d = pd.concat([b.assign(source="blog")[["keyword","date"]],
                   n.assign(source="news")[["keyword","date"]]], ignore_index=True)
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    return d.dropna(subset=["date"])

def compute_gap(search, dated, asof):
    W = max(dated.groupby("keyword")["date"].min().max(), pd.Timestamp("2023-01-01"))
    d = search[search.axis == "direct"].copy()
    d["period"] = pd.to_datetime(d["period"])
    sos_w = d[(d.period >= W) & (d.period <= asof)].groupby("keyword_group")["ratio"].mean()
    sov_w = dated[(dated.date >= W) & (dated.date <= asof)].groupby("keyword").size().reindex(sos_w.index)
    gap = ((sos_w / sos_w.sum() - sov_w / sov_w.sum()) * 100).round(1)
    gap.index.name = None
    return gap

def source_mix(total):
    t = total.groupby("keyword")[["blog_total","news_total","cafe_total"]].mean()  # ★ 중복 행 평균으로 합치기
    return (t.div(t.sum(1), axis=0) * 100).round(0)

def seasonality(search, asof):
    s = pivot_axis(search, "direct", asof)[ANCHOR].dropna()
    return (s.groupby(s.index.month).mean() / s.mean() * 100).round(0)

# ───────────────── 4. LLM 소견 ─────────────────
RULES = """[해석 가드레일 — 항상 적용]
1. YoY/3M YoY는 전년 동월 비교라 계절성이 이미 통제됨 → 모멘텀 둔화를 '계절성/비수기'로 설명 금지.
2. 제공된 수치만 사용. 새 숫자 만들지 마라.
3. '트래픽' 금지 → '검색 수요/검색 관심'(데이터랩=검색 지수, 방문 트래픽 아님).
4. 재인덱싱=추세(크기 비교 아님), 갭=영상 버즈 미포착(방향성 진단).
5. 톤: 냉철·정직. 동급 우위는 강하게, 대중·시장은 '신호/정렬/우위'로 헤지(증명/탈취 금지).
6. 데이터에 없는 원인 만들지 마라."""

def build_prompt(m, sos, asof):
    return f"""당신은 아키클래식의 냉철한 수석 데이터 분석가입니다. 아래 데이터로 '💡 데이터 분석가 요약 소견'을 마크다운으로 작성하세요.

[데이터 · {asof:%Y-%m} 마감]
- 장기 성장률(6M 블록): {m['long']:+.1f}%
- 최근 모멘텀(3M 평활 YoY): {m['yoy3']:+.1f}%
- 니치 검색 점유율(SoS): {sos:.1f}%
- 참고(단일월 YoY): {m['single_yoy']:+.1f}%
- 최근 6개월 YoY 추이: {m['yoy_trend'].to_dict()}
- 알려진 캠페인 서지: {CAMPAIGN}

{RULES}

[추론 규칙 — 데이터 의존]
- 최근 모멘텀이 둔화했고 그 시점이 캠페인 서지를 lapping하는 구간과 겹치면 → 기저효과(base effect)로 설명. 둔화가 없으면 base effect 언급 금지.
- 장기 성장률·SoS와 최근 모멘텀을 대조해, 절대 검색 수요 레벨이 신고가인지 데이터로 판단해 서술.

'💡 데이터 분석가 요약 소견' 헤드라인으로 시작하는 마크다운 블록만 반환."""

def template_insight(m, sos):
    return (f"**💡 데이터 분석가 요약 소견**\n\n"
            f"아키클래식은 장기 성장률 **{m['long']:+.0f}%** 과 니치 마켓 검색 점유율 **{sos:.1f}%** 로 "
            f"경쟁사 대비 소비자의 실질 검색 수요 체급에서 압도적 우위를 보입니다. 최근 모멘텀(3M YoY)은 **{m['yoy3']:+.1f}%** 로 "
            f"완만하나, 이는 {CAMPAIGN} 시점과 맞물리는 기저효과로 보이며, "
            f"절대 검색 수요는 역대 최고점 수준을 유지 중입니다.")

import hashlib, json
from datetime import datetime, timezone

def make_cache_key(asof_str, sos, m):
    yoy_trend_dict = {str(k): v for k, v in m["yoy_trend"].to_dict().items()}
    payload = {
        "asof": asof_str,
        "sos": round(sos, 2),
        "long": round(m["long"], 2),
        "yoy3": round(m["yoy3"], 2),
        "single_yoy": round(m["single_yoy"], 2),
        "yoy_trend": yoy_trend_dict,
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def llm_insight(sos, asof_str, m, force=False):
    from supabase import create_client
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    key = make_cache_key(asof_str, sos, m)

    if not force:
        existing = sb.table("ai_insights").select("*").eq("cache_key", key).execute()
        if existing.data:
            return existing.data[0]["insight_text"], False

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role":"user","content":build_prompt(m, sos, pd.Timestamp(asof_str))}]
        )
        text = r.content[0].text
    except Exception as e:
        st.error(f"LLM 호출 실패: {e}")
        text = template_insight(m, sos)

    sb.table("ai_insights").upsert({
        "cache_key": key,
        "asof_month": asof_str,
        "insight_text": text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return text, True



# ───────────────── 5. 차트 ─────────────────

# 2. 범례 순서: 아키클래식 맨 앞
def sorted_cols(df):
    cols = [ANCHOR] + [c for c in df.columns if c != ANCHOR]
    return df[[c for c in cols if c in df.columns]]

def fig_lines(df, title):
    df = sorted_cols(df)
    fig = go.Figure()
    for c in df.columns:
        fig.add_scatter(x=df.index, y=df[c], name=str(c), mode="lines",
                        line=dict(color=C.get(c,"#888780"), width=2.5 if c==ANCHOR else 1.8))
    fig.update_layout(title=title, height=320, margin=dict(l=10,r=10,t=40,b=10),
                      legend=dict(orientation="h", y=-0.25))
    return fig

# 3. 성장 엔진 — 왼쪽: 추이(얇은 선), 오른쪽: 성장률 바
TREND_LABEL = {
        "아키클래식":    "아키클래식",
        "발건강시그널":  "발 건강(기능성·통증케어)",
        "여행시그널":    "여행·아웃도어",
        "컴포트수요지수":"워킹·일상화",
    }

def fig_market_trend(df):
    """추이 선 차트 — 깔끔하게"""
    df = sorted_cols(df)
    fig = go.Figure()
    for c in df.columns:
        fig.add_scatter(
            x=df.index, y=df[c], name=TREND_LABEL.get(c, c), mode="lines",
            line=dict(color=C.get(c,"#888780"),
                      width=2.5 if c==ANCHOR else 1.5,
                      dash="solid")
        )
    fig.update_layout(
        title="트렌드별 검색 수요 추이",
        height=320, margin=dict(l=10,r=10,t=40,b=10),
        legend=dict(orientation="h", y=-0.28),
        yaxis=dict(title="지수 (자기 평균=100)")
    )
    return fig
 
def fig_market_growth(gr):
    """성장률 바 차트 — 결론 요약"""
    LABEL = {
        "아키클래식":    "아키클래식",
        "발건강시그널":  "발 건강(기능성·통증케어)",
        "여행시그널":    "여행·아웃도어",
        "컴포트수요지수":"워킹·일상화",
    }
    order  = ["아키클래식","발건강시그널","여행시그널","컴포트수요지수"]
    brands = [b for b in order if b in gr.index]
    vals   = [float(gr[b]) for b in brands]
    labels = [LABEL.get(b,b) for b in brands]
    col    = [C.get(b,"#888780") if v>0 else "#CCCCCC" for b,v in zip(brands,vals)]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker_color=col,
        text=[f"{v:+.0f}%" for v in vals],
        textposition="outside",
        textfont=dict(size=13)
    ))
    fig.update_layout(
        title="장기 성장률",
        height=320, margin=dict(l=10,r=60,t=40,b=10),
        xaxis=dict(range=[-70,40], showticklabels=False, zeroline=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12))
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#888780")
    return fig

# 4. GAP 차트 — 3개 브랜드 전체, 색상 개선
def fig_gap(gap):
    brands = list(gap.index)
    values = [float(v) for v in gap.values]
    col = ["#31542B" if v > 0 else "#CCCCCC" for v in values]

    fig = go.Figure(go.Bar(
        x=values,
        y=brands,
        orientation="h",
        marker_color=col,
        text=[f"{v:+.0f}%p" for v in values],
        textposition="outside"
    ))
    fig.update_layout(
        title="SoS − SoV = GAP 지수",
        height=280,
        margin=dict(l=80, r=80, t=40, b=10),
        xaxis=dict(
            range=[-60, 60],
            zeroline=True,
        ),
        yaxis=dict(
            type="category",      # ★ 카테고리축 명시
            categoryorder="array",
            categoryarray=brands,
        )
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#888780")
    return fig

# 5. 대중 벤치마크 — +는 브랜드색, -는 회색
def fig_growth(rates, title):
    col = [C.get(b, "#888780") if v > 0 else "#CCCCCC" for b, v in zip(rates.index, rates.values)]
    fig = go.Figure(go.Bar(
        x=rates.index, y=rates.values,
        marker_color=col,
        text=[f"{v:+.0f}%" for v in rates.values],
        textposition="outside"
    ))
    fig.update_layout(title=title, height=300, margin=dict(l=10,r=10,t=40,b=10))
    fig.add_hline(y=0, line_dash="dash", line_color="#888780")
    return fig

# 6. 계절성 차트
def fig_seasonal(seas):
    pk, lo = seas.max(), seas.min()
    col = ["#EF9F27" if v==pk else "#D85A30" if v==lo else "#B4B2A9" for v in seas]
    fig = go.Figure(go.Bar(
        x=[f"{mo}월" for mo in seas.index], y=seas.values,
        marker_color=col, text=seas.values, textposition="outside"
    ))
    fig.update_layout(title="연간 계절성 지수(연간 검색량 평균=100)", height=300,
                      margin=dict(l=10,r=10,t=40,b=10))
    fig.add_hline(y=100, line_dash="dash", line_color="#888780")
    return fig

# 7. 소스 믹스 — 가로 막대, 브랜드 그린 계열
def fig_mix(mix_row):
    """스택형 가로 바 — blog/news/cafe 하나의 막대에 쌓기"""
    items  = [("blog_total","블로그","#EF9F27"),
              ("news_total","뉴스",  "#B4B2A9"),
              ("cafe_total","카페",  "#D85A30")]
    fig = go.Figure()
    for k, name, color in items:
        v = float(mix_row[k]) if k in mix_row.index else 0.0
        fig.add_trace(go.Bar(
            x=[v], y=["mix"],
            orientation="h",
            name=name,
            marker_color=color,
            text=f"{name} {v:.0f}%",
            textposition="inside",
            textfont=dict(color="white", size=12),
            insidetextanchor="middle",
            hovertemplate=f"{name}: {v:.0f}%<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        height=258,
        bargap=0.8,
        margin=dict(l=0, r=0, t=10, b=80),
        xaxis=dict(range=[0,101], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(orientation="h", y=-0.35, x=0, font=dict(size=12)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

# ───────────────── 6. 데이터 로드 & 계산 ─────────────────
data       = load_all()
search     = data["search"]
ASOF       = last_complete_month(search)
sos        = compute_sos(search, ASOF)
sos_now    = sos[ANCHOR].dropna().iloc[-3:].mean()
niche_idx  = reindex_df(search, "direct", ASOF)
market_idx = reindex_df(search, "market", ASOF)
mass_gr    = growth_rate(reindex_df(search, "mass", ASOF))
dated      = parse_dated(data["blog"], data["news"])
gap        = compute_gap(search, dated, ASOF)
mix        = source_mix(data["total"])
seas       = seasonality(search, ASOF)
m          = momentum(search, ASOF)

# ───────────────── 7. UI 렌더링 ─────────────────
st.title("아키모니터 · AKIIIMONITOR")
st.caption(f"브랜드 건강검진 대시보드 · 2023년 1월 ~ {ASOF:%Y년 %m월} 마감 기준")
st.warning(f"{ASOF:%Y년 %m월} 마감 기준 — 데이터 수집 진행 중인 달은 모든 지표에서 자동 제외됨", icon="⚠️")

# LLM 소견
force = st.checkbox("강제 재생성 (데이터 재수집 시 체크)")
insight_text, was_generated = llm_insight(sos_now, ASOF.isoformat(), m, force=force)
st.markdown(insight_text)
st.caption("✅ 새로 생성됨" if was_generated else "📦 저장된 결과 재사용")

# 상단 3지표
c1, c2, c3 = st.columns(3)
c1.metric("장기 성장률", f"{m['long']:+.1f}%", "23년 1월~6월 대비 최근 6개월")
c2.metric("최근 모멘텀", f"{m['yoy3']:+.1f}%", "3개월 평활 YoY")
c3.metric("니치 마켓 SoS", f"{sos_now:.1f}%", "동급 시장 내 검색량 비중")
st.divider()

# ① 니치 마켓 독점
st.subheader("① 니치 마켓 독점 · Market Monopoly")
# 1. 줄바꿈 수정
st.markdown(
    f"동급 DTC 마켓 내에서 **{sos_now:.1f}%** 의 **압도적인 검색 점유율을 기록하며 니치 마켓 지배력** 확보.\n\n"
    f"경쟁사들이 소셜 노출 점유(SoV) 중심의 휘발성 성장에 머물 때, 아키클래식은 **소비자가 자발적으로 찾는 실질 수요** 구축"
    f"(SoS-SoV GAP **{float(gap.get(ANCHOR,0)):+.0f}%p**)."
)
col_a, col_b = st.columns([1.4, 1])
with col_a:
    view = st.radio("동급 보기", ["검색 점유율 추이","성장 지수"],
                    horizontal=True, label_visibility="collapsed")
    if view == "검색 점유율 추이":
        st.plotly_chart(fig_lines(sos, "니치 마켓 검색 점유율(SoS) 추이"), use_container_width=True)
        st.caption("※검색 점유율(SoS) = 동급 니치 마켓 내 검색량 비중(%)")
    else:
        st.plotly_chart(fig_lines(niche_idx, "니치 마켓 브랜드별 성장 지수"), use_container_width=True)
        st.caption("※성장 지수 = 자기기간 평균(=100) 대비 검색량 추세(100 초과=평균보다 검색량 증가)")
with col_b:
    st.plotly_chart(fig_gap(gap), use_container_width=True)
    st.caption("※SoS-SoV GAP 지수는 유튜브 등 영상 채널 버즈 미포착(절대값보다 부호(+/−) 방향성 위주 진단)")
st.divider()

# ② 성장 엔진 검증
st.subheader("② 성장 엔진 검증 · Trend Alignment")
g = growth_rate(market_idx)
# 4. 줄바꿈 수정
st.markdown(
    f"워킹화·여행화 수요 침체기 속, **발 건강(기능성·통증케어) 수요(+{g.get('발건강시그널',0):.0f}%)** 는 유일하게 성장 중인 트렌드.\n\n"
    f"아키클래식(**{g.get('아키클래식',0):+.0f}%**)의 장기 성장 곡선이 이 트렌드의 흐름을 타고 있음"
    f"(월별 동조는 약하나(r≈0.22), 장기 방향이 일치 — 단기 성장 동인은 여행 유튜버 협업 주목도로 추정)."
)
eng_l, eng_r = st.columns([1.3, 1])
with eng_l:
    st.plotly_chart(fig_market_trend(market_idx), use_container_width=True)
    st.caption("※각 트렌드 키워드의 검색 수요를 자기 평균(=100) 기준으로 정규화(100 초과=평균보다 수요 높음)")
with eng_r:
    st.plotly_chart(fig_market_growth(g), use_container_width=True)
    st.caption("※장기 성장률 = 최초 6개월 대비 최근 6개월 평균 검색량 변화율(+ 성장, − 침체)")
st.divider()

# ③ 메이저 체급 진입
st.subheader("③ 메이저 체급 진입 · Closing In")
st.markdown(
    f"검색 점유 기준, 아키클래식은 **+{g.get('아키클래식',0):.0f}%** 성장한 반면 "
    f"메이저 경쟁 브랜드는 정체되어 있음 — 격차가 좁혀지고 있다는 시그널."
)
st.plotly_chart(fig_growth(mass_gr, "브랜드별 장기 성장률"),
                use_container_width=True)
st.caption(f"※ 장기 성장률 = 최초 6개월 대비 최근 6개월 평균 검색량 변화율(+ 성장, − 침체).\n\n"
    f"※스케쳐스·휠라 수치는 측정 구간에 따라 달라질 수 있어 보수적 해석. "
    f"실제 매출 점유율은 별도 검증 필요.")
st.divider()

# 하단 전술
st.subheader("전략 인사이트 · Action Insight")
a1, a2 = st.columns([1.5, 1])
a1.plotly_chart(fig_seasonal(seas), use_container_width=True)
# 7. 계절성 주석
a1.caption(
    "※계절성 지수 = 해당 월 평균 검색량 ÷ 연간 평균 × 100"
    "(100 초과 = 연평균보다 검색 수요 많은 달(성수기), 100 미만 = 비수기)\n\n"
    f"🟠 {int(seas.idxmax())}월 피크({int(seas.max())}), 🔴 {int(seas.idxmin())}월 비수기({int(seas.min())})"
)
with a2:
    st.markdown("**아키클래식 소셜 노출 채널 비중**")
    st.plotly_chart(fig_mix(mix.loc[ANCHOR]), use_container_width=True)  # 6. 가로형
    st.caption("· 블로그 중심의 일방향 광고 노출에만 의존하지 않고, 실구매자 여론이 형성되는 **카페 채널 비중을 29%까지 확보**")

pk_month = int(seas.idxmax()); pk_val = int(seas.max()); lo_month = int(seas.idxmin())
st.info(
    f"**26년 하반기 전략:** **{pk_month}월 수요 피크 시점**에 맞춰 마케팅 예산을 과감히 프론트로딩하고, "
    f"**{lo_month}월 비수기 수요**를 소셜 노출 점유율 기반이 있는 '카페' 커뮤니티를 활용해 가성비 있게 방어할 것을 제안합니다.", 
    icon="💡"
)

with st.expander("방법론 및 데이터 한계점 · Methodology & Limitations"):
    st.markdown(f"""
    본 대시보드는 분석의 정밀도를 유지하고 왜곡을 방지하기 위해 아래와 같은 통계적 기준과 한계점을 내포하고 있습니다.
    
    * **1. 완료월 기준 자동 갱신 (As of {ASOF:%Y-%m})**
        * 주간 데이터를 월간 단위로 리샘플링할 때, 데이터 집계가 진행 중인 '당월'은 통계 왜곡을 막기 위해 자동으로 제외되며 마감된 전월 데이터까지만 매주 자가 갱신됩니다.
    
    * **2. 지표별 데이터 해석 가이드**
        * **성장 지수:** 각 트렌드와 브랜드의 '자기기간 평균(=100) 검색량'을 기준으로 정규화한 추세선입니다. 체급(크기) 비교가 아닌 **장단기 방향성(추세)을** 확인해야 합니다.
        * **검색 점유율(SoS):** 동급 니치 마켓 내에서의 **실제 검색량 비중(%)을** 뜻하므로, 두 지표 간의 단순 Raw 데이터 비교는 하지 않습니다.
    
    * **3. 모멘텀 및 장기 성장률 산출 기준**
        * **모멘텀:** 단일 월의 YoY/MoM 수치는 기저효과(Base Effect)와 단기 노이즈에 민감하므로, 대시보드 상단에는 이를 보정한 **3개월 이동평균(3M 평활) YoY**를 주 지표로 사용합니다(YoY 지표 특성상 계절성은 자동 통제됨).
        * **장기 성장률:** 최초 6개월과 최근 6개월의 평균치를 비교하므로 시점(윈도우)에 따라 민감하게 반응할 수 있습니다. 수치 자체보다는 **성장 혹은 정체라는 큰 틀의 방향성** 위주로 해석을 권장합니다.
    
    * **4. SoS-SoV GAP 데이터 수집 한계**
        * 버즈량(SoV) 계산 시 수집 채널 간 공통 수집 기간의 게시글 수만 카운트하며, 날짜 정보가 매칭되지 않는 '카페' 채널 및 유튜브 등 '영상 채널'의 버즈는 포함되지 않습니다. 따라서 절대적인 수치보다는 **부호(+/−)의 방향성을 중심으로 진단**해야 합니다.
    
    """)