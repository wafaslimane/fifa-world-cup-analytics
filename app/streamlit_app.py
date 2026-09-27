"""FIFA World Cup Analytics - tableau de bord Streamlit.

Lancer :  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fifa_pipeline.config import WAREHOUSE_PATH  # noqa: E402

# --------------------------------------------------------------------------- style
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
CONF_COLORS = {"UEFA": BLUE, "CONMEBOL": ORANGE, "CONCACAF": AQUA, "AFC": YELLOW, "CAF": MAGENTA, "OFC": GREEN}
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

st.set_page_config(page_title="FIFA World Cup Analytics", page_icon="⚽", layout="wide")

st.markdown(f"""
<style>
  .block-container {{ padding-top: 2rem; }}
  div[data-testid="stMetric"] {{ background:#fff; border:1px solid rgba(11,11,11,.08); border-radius:10px; padding:12px 16px; }}
  div[data-testid="stMetricLabel"] p {{ color:{INK2}; font-size:.85rem; }}
  .subtitle {{ color:{INK2}; margin-top:-.6rem; }}
  .insight {{ border-left:3px solid {BLUE}; padding:.4rem .8rem; background:#f3f7fd; border-radius:4px; color:{INK}; margin:.3rem 0 1rem; }}
</style>""", unsafe_allow_html=True)


def style(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=78 if legend else 48, b=10),
        title=dict(y=1, yanchor="top", yref="container", pad=dict(t=12), x=0.005, xanchor="left", xref="container"),
        plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK2, size=13),
        title_font=dict(color=INK, size=15, weight=600), showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, title=None, traceorder="normal"),
        hoverlabel=dict(bgcolor="white", font_color=INK, bordercolor=GRID),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor=BASE, tickfont_color=MUTED, title_font_color=INK2, tickangle=0, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=BASE, tickfont_color=MUTED, title_font_color=INK2,
                     automargin=True)
    fig.update_traces(marker_line_width=0, selector=dict(type="bar"))
    return fig


def pct(x: float) -> str:
    return f"{x:.0%}".replace(".", ",")


def num(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


# --------------------------------------------------------------------------- data
@st.cache_resource(show_spinner="Construction de l'entrepôt de données…")
def get_connection() -> duckdb.DuckDBPyConnection:
    if not WAREHOUSE_PATH.exists():
        from src.fifa_pipeline.run import main as run_pipeline
        if run_pipeline() != 0:
            st.error("Le pipeline a échoué : voir reports/data_quality.md")
            st.stop()
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=True)


@st.cache_data
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return get_connection().execute(sql, list(params)).df()


# --------------------------------------------------------------------------- filters
st.title("⚽ FIFA World Cup Analytics")
st.markdown('<p class="subtitle">Près d\'un siècle de Coupes du monde : performances des nations, buteurs, '
            'dynamique des matchs. Données : Fjelstul World Cup Database (CC-BY-SA 4.0).</p>',
            unsafe_allow_html=True)

with st.sidebar:
    st.header("Filtres")
    competition = st.radio("Compétition", ["Hommes", "Femmes"], horizontal=True)
    years = q("SELECT DISTINCT year FROM dim_tournament WHERE competition = ? ORDER BY year", (competition,))["year"].tolist()
    y0, y1 = st.select_slider("Éditions", options=years, value=(years[0], years[-1]))
    st.caption(f"{sum(y0 <= y <= y1 for y in years)} éditions sélectionnées")
    st.divider()
    st.caption("Pipeline : CSV → Pandas (nettoyage, modèle en étoile) → contrôles qualité → DuckDB + vues SQL → Streamlit")

P = (competition, y0, y1)
WHERE = "competition = ? AND year BETWEEN ? AND ?"

tabs = st.tabs(["Vue d'ensemble", "Équipes", "Buteurs", "Buts & dynamique", "Confédérations & hôtes",
                "Matchs", "Qualité des données"])

# =========================================================================== 1. Overview
with tabs[0]:
    k = q(f"SELECT * FROM v_tournament_kpis WHERE {WHERE} ORDER BY year", P)
    c = st.columns(6)
    c[0].metric("Éditions", len(k))
    c[1].metric("Matchs", num(k["matches"].sum()))
    c[2].metric("Buts", num(k["goals"].sum()))
    c[3].metric("Buts / match", num(k["goals"].sum() / k["matches"].sum(), 2))
    c[4].metric("Matchs nuls", pct((k["draw_rate"] * k["matches"]).sum() / k["matches"].sum()))
    c[5].metric("Hôte titré", f"{int(k['host_won'].sum())} / {len(k)}")

    avg = k["goals"].sum() / k["matches"].sum()
    best, worst = k.loc[k["goals_per_match"].idxmax()], k.loc[k["goals_per_match"].idxmin()]
    st.markdown(f'<div class="insight">Édition la plus offensive : <b>{best.year}</b> ({num(best.goals_per_match, 2)} buts/match) · '
                f'la plus fermée : <b>{worst.year}</b> ({num(worst.goals_per_match, 2)}).</div>', unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure()
        fig.add_scatter(x=k["year"], y=k["goals_per_match"], mode="lines+markers", name="Buts par match",
                        line=dict(color=BLUE, width=2), marker=dict(size=8, line=dict(color="#fcfcfb", width=2)),
                        customdata=k[["host_country", "winner", "matches"]],
                        hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>%{y:.2f} buts/match<br>"
                                      "%{customdata[2]} matchs · vainqueur : %{customdata[1]}<extra></extra>")
        fig.add_hline(y=avg, line=dict(color=MUTED, dash="dot", width=1),
                      annotation_text=f"moyenne {avg:.2f}", annotation_font_color=MUTED)
        fig.update_layout(title="Buts par match, par édition", hovermode="x unified")
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)
    with right:
        titles = (q(f"""SELECT team_name, COUNT(*) AS titres, string_agg(year::VARCHAR, ', ' ORDER BY year) AS annees
                        FROM v_team_tournament WHERE {WHERE} AND final_position = 1
                        GROUP BY team_name ORDER BY titres, team_name""", P))
        fig = px.bar(titles, x="titres", y="team_name", orientation="h", custom_data=["annees"],
                     title="Palmarès sur la période")
        fig.update_traces(marker_color=BLUE, hovertemplate="<b>%{y}</b><br>%{x} titre(s) : %{customdata[0]}<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None, xaxis_dtick=1)
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)

    fig = go.Figure()
    fig.add_bar(x=k["year"], y=k["count_teams"], name="Équipes", marker_color=AQUA,
                hovertemplate="<b>%{x}</b><br>%{y} équipes<extra></extra>")
    fig.update_layout(title="Nombre d'équipes par édition", xaxis_title=None, yaxis_title=None)
    st.plotly_chart(style(fig, 260, legend=False), width="stretch", theme=None)

    with st.expander("Tableau des éditions"):
        st.dataframe(k[["year", "host_country", "winner", "count_teams", "matches", "goals", "goals_per_match",
                        "draw_rate", "shootouts", "penalty_goals", "own_goals"]]
                     .rename(columns={"year": "Année", "host_country": "Hôte", "winner": "Vainqueur",
                                      "count_teams": "Équipes", "matches": "Matchs", "goals": "Buts",
                                      "goals_per_match": "Buts/match", "draw_rate": "% nuls", "shootouts": "Tirs au but",
                                      "penalty_goals": "Penalties", "own_goals": "CSC"}),
                     hide_index=True, width="stretch",
                     column_config={"% nuls": st.column_config.NumberColumn(format="percent")})

# =========================================================================== 2. Teams
with tabs[1]:
    tt = q(f"SELECT * FROM v_team_tournament WHERE {WHERE}", P)
    ranking = (tt.groupby(["team_name", "confederation_code"], as_index=False)
                 .agg(participations=("tournament_id", "nunique"), matchs=("matches", "sum"), victoires=("wins", "sum"),
                      nuls=("draws", "sum"), defaites=("losses", "sum"), bp=("goals_for", "sum"),
                      bc=("goals_against", "sum"), points=("points", "sum"),
                      titres=("final_position", lambda s: (s == 1).sum()),
                      demi=("final_position", lambda s: (s <= 4).sum())))
    ranking["pts_match"] = ranking["points"] / ranking["matchs"]
    ranking["taux_victoire"] = ranking["victoires"] / ranking["matchs"]
    ranking = ranking.sort_values(["points", "pts_match"], ascending=False).reset_index(drop=True)

    teams = ranking["team_name"].tolist()
    default = "France" if "France" in teams else teams[0]
    team = st.selectbox("Équipe", teams, index=teams.index(default))
    r = ranking[ranking["team_name"] == team].iloc[0]
    rank = int(ranking.index[ranking["team_name"] == team][0]) + 1

    c = st.columns(6)
    c[0].metric("Participations", int(r.participations))
    c[1].metric("Titres", int(r.titres))
    c[2].metric("Demi-finales", int(r.demi))
    c[3].metric("Taux de victoire", pct(r.taux_victoire))
    c[4].metric("Points / match", num(r.pts_match, 2))
    c[5].metric("Rang (points cumulés)", f"{rank}e / {len(ranking)}")

    left, right = st.columns([3, 2])
    with left:
        path = tt[tt["team_name"] == team].sort_values("year")
        path = path.assign(level=path["final_position"].map({1: 9, 2: 8, 3: 7, 4: 6}).astype("Float64")
                           .fillna(path["best_stage_order"].astype("Float64")))
        fig = go.Figure()
        fig.add_bar(x=path["year"], y=path["level"], width=2.4,
                    marker=dict(color=[ORANGE if p else BLUE for p in path["final_position"].eq(1).fillna(False)],
                                cornerradius=4),
                    customdata=path[["finish", "wins", "draws", "losses", "goals_for", "goals_against"]],
                    hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>%{customdata[1]}V %{customdata[2]}N "
                                  "%{customdata[3]}D · buts %{customdata[4]}–%{customdata[5]}<extra></extra>")
        fig.update_yaxes(tickvals=[1, 2, 4, 5, 6, 7, 8, 9], range=[0, 9.4],
                         ticktext=["Poules", "2e tour", "8es", "Quarts", "4e", "3e", "Finaliste", "Vainqueur"])
        fig.update_layout(title=f"Parcours de {team} par édition (orange = titre)")
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)
    with right:
        res = pd.DataFrame({"Résultat": ["Victoires", "Nuls", "Défaites"],
                            "Matchs": [r.victoires, r.nuls, r.defaites]})
        fig = px.bar(res, x="Matchs", y="Résultat", orientation="h", color="Résultat",
                     color_discrete_map={"Victoires": BLUE, "Nuls": MUTED, "Défaites": ORANGE},
                     title=f"Bilan : {int(r.matchs)} matchs, {int(r.bp)} buts marqués / {int(r.bc)} encaissés")
        fig.update_traces(hovertemplate="%{y} : %{x}<extra></extra>", texttemplate="%{x}", textposition="outside",
                          textfont_color=INK2)
        fig.update_layout(yaxis_title=None, xaxis_title=None, xaxis_range=[0, max(res["Matchs"]) * 1.15])
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)

    st.subheader("Classement général")
    min_matches = st.slider("Nombre minimum de matchs joués", 1, 50, 10)
    top = ranking[ranking["matchs"] >= min_matches].nlargest(15, "pts_match").sort_values("pts_match")
    fig = px.bar(top, x="pts_match", y="team_name", orientation="h", color="confederation_code",
                 color_discrete_map=CONF_COLORS, custom_data=["matchs", "titres", "taux_victoire"],
                 title="Top 15 : points par match (barème 3/1/0 appliqué à toutes les éditions)")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.2f} pts/match<br>%{customdata[0]} matchs · "
                                    "%{customdata[1]} titre(s) · %{customdata[2]:.0%} de victoires<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title=None, yaxis_categoryorder="total ascending")
    st.plotly_chart(style(fig, 480), width="stretch", theme=None)

    st.dataframe(ranking.rename(columns={"team_name": "Équipe", "confederation_code": "Confédération",
                                         "participations": "Participations", "matchs": "Matchs", "victoires": "V",
                                         "nuls": "N", "defaites": "D", "bp": "BP", "bc": "BC", "points": "Points",
                                         "titres": "Titres", "demi": "Top 4", "pts_match": "Pts/match",
                                         "taux_victoire": "% victoires"}),
                 hide_index=True, width="stretch", height=300,
                 column_config={"Pts/match": st.column_config.NumberColumn(format="%.2f"),
                                "% victoires": st.column_config.NumberColumn(format="percent")})

# =========================================================================== 3. Scorers
with tabs[2]:
    sc = q(f"""SELECT p.player_name, tm.team_name, p.position,
                      COUNT(*) AS buts, SUM(g.penalty::INT) AS penalties,
                      COUNT(DISTINCT g.tournament_id) AS editions,
                      COUNT(DISTINCT g.match_id) AS matchs_buteur,
                      string_agg(DISTINCT g.year::VARCHAR, ', ' ORDER BY g.year::VARCHAR) AS annees
               FROM fact_goal g JOIN dim_player p USING (player_id)
               JOIN dim_team tm ON tm.team_id = g.player_team_id
               WHERE NOT g.own_goal AND g.{WHERE.replace(' AND year', ' AND g.year')}
               GROUP BY ALL ORDER BY buts DESC, penalties ASC""", P)
    n = st.slider("Nombre de buteurs affichés", 5, 30, 15)
    top = sc.head(n).iloc[::-1]
    c = st.columns(4)
    c[0].metric("Buteurs différents", num(len(sc)))
    c[1].metric("Record de buts", int(sc.iloc[0].buts), sc.iloc[0].player_name, delta_color="off", delta_arrow="off")
    c[2].metric("Part des penalties", pct(sc["penalties"].sum() / sc["buts"].sum()))
    c[3].metric("Buteurs à 1 seul but", pct((sc["buts"] == 1).mean()))

    fig = go.Figure()
    fig.add_bar(y=top["player_name"] + " (" + top["team_name"] + ")", x=top["buts"] - top["penalties"],
                orientation="h", name="Jeu", marker_color=BLUE,
                customdata=top[["buts", "editions", "annees"]],
                hovertemplate="<b>%{y}</b><br>%{customdata[0]} buts sur %{customdata[1]} édition(s) : "
                              "%{customdata[2]}<br>dont %{x} dans le jeu<extra></extra>")
    fig.add_bar(y=top["player_name"] + " (" + top["team_name"] + ")", x=top["penalties"], orientation="h",
                name="Penalty", marker_color=ORANGE, hovertemplate="%{x} penalty(s)<extra></extra>")
    fig.update_layout(barmode="stack", title="Meilleurs buteurs (hors CSC, hors tirs au but)",
                      xaxis_title=None, yaxis_title=None, bargap=0.2)
    st.plotly_chart(style(fig, max(380, 26 * n)), width="stretch", theme=None)

    left, right = st.columns(2)
    with left:
        pos = sc.groupby("position", as_index=False)["buts"].sum().sort_values("buts")
        fig = px.bar(pos, x="buts", y="position", orientation="h", title="Buts par poste")
        fig.update_traces(marker_color=BLUE, hovertemplate="%{y} : %{x} buts<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(style(fig, 300, legend=False), width="stretch", theme=None)
    with right:
        dist = sc["buts"].clip(upper=8).value_counts().sort_index().reset_index()
        dist["label"] = dist["buts"].astype(str).replace({"8": "8+"})
        fig = px.bar(dist, x="label", y="count", title="Distribution : nombre de buts par joueur")
        fig.update_traces(marker_color=AQUA, hovertemplate="%{x} but(s) : %{y} joueurs<extra></extra>")
        fig.update_layout(xaxis_title="Buts", yaxis_title="Joueurs")
        st.plotly_chart(style(fig, 300, legend=False), width="stretch", theme=None)

# =========================================================================== 4. Goals & dynamics
with tabs[3]:
    gt = q(f"SELECT minute_bucket, SUM(goals) goals, SUM(stoppage_time_goals) st FROM v_goal_timing WHERE {WHERE} GROUP BY 1", P)
    order = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "Prolongations"]
    gt["minute_bucket"] = pd.Categorical(gt["minute_bucket"], order, ordered=True)
    gt = gt.sort_values("minute_bucket")
    gt["label"] = gt["minute_bucket"].astype(str).replace({"Prolongations": "Prol."})
    gt["share"] = gt["goals"] / gt["goals"].sum()
    late = gt.loc[gt["minute_bucket"].isin(["76-90"]), "share"].sum()
    st.markdown(f'<div class="insight">{pct(late)} des buts sont marqués dans le dernier quart d\'heure du temps '
                f'réglementaire, contre {pct(gt.iloc[0].share)} dans le premier.</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        fig = px.bar(gt, x="label", y="goals", title="Quand les buts sont-ils marqués ?", custom_data=["share"])
        fig.update_traces(marker_color=BLUE, hovertemplate="<b>%{x}'</b><br>%{y} buts (%{customdata[0]:.1%})<extra></extra>")
        fig.update_layout(xaxis_title="Minute", yaxis_title=None)
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)
    with right:
        ms = q(f"""SELECT total_goals, COUNT(*) n FROM fact_match WHERE {WHERE} GROUP BY 1 ORDER BY 1""", P)
        ms["label"] = ms["total_goals"].clip(upper=7).astype(str).replace({"7": "7+"})
        ms = ms.groupby("label", as_index=False)["n"].sum()
        fig = px.bar(ms, x="label", y="n", title="Distribution du nombre de buts par match")
        fig.update_traces(marker_color=AQUA, hovertemplate="%{x} but(s) : %{y} matchs<extra></extra>")
        fig.update_layout(xaxis_title="Buts dans le match", yaxis_title=None)
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)

    stage = q(f"""SELECT stage, stage_order, COUNT(*) matchs, AVG(total_goals) buts,
                         AVG(CASE WHEN result='Nul' OR penalty_shootout THEN 1 ELSE 0 END) nuls,
                         AVG(extra_time::INT) prolong
                  FROM fact_match WHERE {WHERE} GROUP BY ALL ORDER BY stage_order""", P)
    fig = go.Figure()
    fig.add_bar(y=stage["stage"], x=stage["buts"], orientation="h", marker_color=BLUE,
                customdata=stage[["matchs", "prolong"]],
                hovertemplate="<b>%{y}</b><br>%{x:.2f} buts/match<br>%{customdata[0]} matchs · "
                              "%{customdata[1]:.0%} avec prolongation<extra></extra>")
    fig.update_layout(title="Buts par match selon la phase de compétition",
                      xaxis_title="Buts par match", yaxis_title=None, yaxis_autorange="reversed")
    st.plotly_chart(style(fig, 340, legend=False), width="stretch", theme=None)

    k = q(f"SELECT year, penalty_goals, own_goals, goals, shootouts FROM v_tournament_kpis WHERE {WHERE} ORDER BY year", P)
    fig = go.Figure()
    fig.add_scatter(x=k["year"], y=k["penalty_goals"] / k["goals"], name="Buts sur penalty", mode="lines+markers",
                    line=dict(color=ORANGE, width=2), marker=dict(size=8),
                    hovertemplate="%{x} : %{y:.1%} des buts<extra>Penalty</extra>")
    fig.add_scatter(x=k["year"], y=k["own_goals"] / k["goals"], name="CSC", mode="lines+markers",
                    line=dict(color=VIOLET, width=2), marker=dict(size=8),
                    hovertemplate="%{x} : %{y:.1%} des buts<extra>CSC</extra>")
    fig.update_layout(title="Part des penalties et des CSC dans les buts (en %)", yaxis_tickformat=".0%",
                      hovermode="x unified")
    st.plotly_chart(style(fig, 320), width="stretch", theme=None)

# =========================================================================== 5. Confederations & hosts
with tabs[4]:
    cf = q(f"SELECT * FROM v_confederation_tournament WHERE {WHERE} ORDER BY year", P)
    left, right = st.columns(2)
    with left:
        agg = cf.groupby("confederation_code", as_index=False).agg(wins=("wins", "sum"), matches=("matches", "sum"),
                                                                   sf=("semi_finalists", "sum"))
        agg["ppm"] = agg["wins"] / agg["matches"]
        agg = agg.sort_values("sf")
        fig = px.bar(agg, x="sf", y="confederation_code", orientation="h", color="confederation_code",
                     color_discrete_map=CONF_COLORS, custom_data=["ppm", "matches"],
                     title="Places dans le dernier carré par confédération")
        fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x} demi-finalistes<br>%{customdata[1]} matchs · "
                                        "%{customdata[0]:.0%} de victoires<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(style(fig, legend=False), width="stretch", theme=None)
    with right:
        fig = px.bar(cf, x="year", y="teams", color="confederation_code", color_discrete_map=CONF_COLORS,
                     title="Équipes qualifiées par confédération",
                     category_orders={"confederation_code": list(CONF_COLORS)})
        fig.update_traces(hovertemplate="%{x} · %{y} équipes<extra>%{fullData.name}</extra>",
                          marker_line_color="#fcfcfb", marker_line_width=1)
        fig.update_layout(xaxis_title=None, yaxis_title=None, barmode="stack")
        st.plotly_chart(style(fig), width="stretch", theme=None)

    st.subheader("L'effet pays hôte")
    hp = q(f"SELECT * FROM v_host_performance WHERE {WHERE}", P)
    eff = (hp.groupby(["team_name", "is_host"])
             .apply(lambda d: d["points"].sum() / d["matches"].sum(), include_groups=False)
             .unstack().dropna().rename(columns={True: "Hôte", False: "Hors hôte"}))
    if eff.empty:
        st.info("Pas assez d'éditions sur la période pour comparer.")
    else:
        eff = eff.assign(delta=eff["Hôte"] - eff["Hors hôte"]).sort_values("delta")
        share = (eff["delta"] > 0).mean()
        st.markdown(f'<div class="insight">{pct(share)} des pays organisateurs font mieux à domicile '
                    f'(points par match) que lors de leurs autres participations. Écart moyen : '
                    f'{eff["delta"].mean():+.2f} pt/match.</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for _, row in eff.iterrows():
            fig.add_shape(type="line", x0=row["Hors hôte"], x1=row["Hôte"], y0=row.name, y1=row.name,
                          line=dict(color=BASE, width=2))
        fig.add_scatter(x=eff["Hors hôte"], y=eff.index, mode="markers", name="Hors hôte",
                        marker=dict(size=11, color=MUTED, line=dict(color="#fcfcfb", width=2)),
                        hovertemplate="%{y} hors hôte : %{x:.2f} pts/match<extra></extra>")
        fig.add_scatter(x=eff["Hôte"], y=eff.index, mode="markers", name="Hôte",
                        marker=dict(size=11, color=BLUE, line=dict(color="#fcfcfb", width=2)),
                        hovertemplate="%{y} à domicile : %{x:.2f} pts/match<extra></extra>")
        fig.update_layout(title="Points par match : à domicile vs autres éditions", xaxis_title="Points par match")
        st.plotly_chart(style(fig, max(320, 28 * len(eff))), width="stretch", theme=None)

# =========================================================================== 6. Matches
with tabs[5]:
    mt = q(f"SELECT * FROM v_matches WHERE {WHERE} ORDER BY match_date DESC", P)
    c1, c2, c3 = st.columns([2, 2, 1])
    team_f = c1.multiselect("Équipe(s)", sorted(set(mt["home_team"]) | set(mt["away_team"])))
    stage_f = c2.multiselect("Phase", mt.sort_values("stage_order")["stage"].unique().tolist())
    ko = c3.toggle("Tirs au but uniquement")
    if team_f:
        mt = mt[mt["home_team"].isin(team_f) | mt["away_team"].isin(team_f)]
    if stage_f:
        mt = mt[mt["stage"].isin(stage_f)]
    if ko:
        mt = mt[mt["penalty_shootout"]]
    st.caption(f"{len(mt)} matchs")
    st.dataframe(mt[["match_date", "year", "stage", "home_team", "score", "away_team", "winner", "stadium_name", "city_name"]]
                 .rename(columns={"match_date": "Date", "year": "Édition", "stage": "Phase", "home_team": "Équipe 1",
                                  "score": "Score", "away_team": "Équipe 2", "winner": "Vainqueur",
                                  "stadium_name": "Stade", "city_name": "Ville"}),
                 hide_index=True, width="stretch", height=520,
                 column_config={"Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
                                "Édition": st.column_config.NumberColumn(format="%d")})
    st.download_button("Télécharger (CSV)", mt.to_csv(index=False).encode("utf-8"), "matchs.csv", "text/csv")

# =========================================================================== 7. Data quality
with tabs[6]:
    dq = q("SELECT * FROM data_quality_checks")
    ok = int(dq["passed"].sum())
    c = st.columns(4)
    c[0].metric("Contrôles réussis", f"{ok} / {len(dq)}")
    c[1].metric("Bloquants en échec", int(((~dq["passed"]) & (dq["severity"] == "bloquant")).sum()))
    c[2].metric("Alertes", int(((~dq["passed"]) & (dq["severity"] == "alerte")).sum()))
    c[3].metric("Dernière exécution", pd.to_datetime(dq["run_at"].iloc[0]).strftime("%d/%m/%Y"))

    dq["Statut"] = dq.apply(lambda r: "✅ OK" if r.passed else ("⚠️ Alerte" if r.severity == "alerte" else "❌ KO"), axis=1)
    st.dataframe(dq[["Statut", "category", "table", "check", "severity", "failed_rows", "total_rows"]]
                 .rename(columns={"category": "Catégorie", "table": "Table", "check": "Contrôle",
                                  "severity": "Sévérité", "failed_rows": "Lignes KO", "total_rows": "Lignes"}),
                 hide_index=True, width="stretch", height=420)

    tables = q("""SELECT table_name AS "Table", estimated_size AS "Lignes"
                  FROM duckdb_tables() ORDER BY table_name""")
    st.markdown("**Modèle en étoile chargé dans DuckDB**")
    st.dataframe(tables, hide_index=True)
    st.markdown("""
**Traitements appliqués** : harmonisation des libellés de phase (`quarter-final` / `quarter-finals` → *Quarts de finale*),
conversion des valeurs `not available` en valeurs manquantes, typage des dates et booléens, calcul du vainqueur
incluant les tirs au but, barème 3/1/0 appliqué à toutes les éditions, découpage des minutes de but en tranches,
séparation compétitions Hommes / Femmes.
""")
