import random

import pandas as pd
import requests
import streamlit as st

API = "https://pokeapi.co/api/v2"
MAX_ID = 1025  # ids erboven zijn alternatieve vormen (mega's, ...)
STAT_LABELS = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special-attack": "Sp. attack",
    "special-defense": "Sp. defense",
    "speed": "Speed",
}

st.set_page_config(page_title="Pokédex", page_icon="⚡")


@st.cache_data(ttl="1d", max_entries=1)
def load_names() -> list[str]:
    r = requests.get(f"{API}/pokemon", params={"limit": MAX_ID}, timeout=10)
    r.raise_for_status()
    return [p["name"] for p in r.json()["results"]]


@st.cache_data(ttl="1d", max_entries=200)
def load_pokemon(name: str) -> dict:
    r = requests.get(f"{API}/pokemon/{name}", timeout=10)
    r.raise_for_status()
    d = r.json()
    return {
        "name": d["name"],
        "id": d["id"],
        "image": d["sprites"]["other"]["official-artwork"]["front_default"],
        "types": [t["type"]["name"] for t in d["types"]],
        "height_m": d["height"] / 10,
        "weight_kg": d["weight"] / 10,
        "stats": {STAT_LABELS[s["stat"]["name"]]: s["base_stat"] for s in d["stats"]},
    }


def pretty(name: str) -> str:
    return name.replace("-", " ").title()


def show_card(p: dict) -> None:
    with st.container(border=True):
        st.image(p["image"], width=220)
        st.subheader(f"#{p['id']} {pretty(p['name'])}")
        st.badge(" · ".join(t.title() for t in p["types"]), icon=":material/bolt:")
        st.caption(f"{p['height_m']} m · {p['weight_kg']} kg")


def pick_random(key: str) -> None:
    st.session_state[key] = random.choice(NAMES)


st.title("Pokédex")

try:
    NAMES = load_names()
except requests.RequestException as e:
    st.error(f"De PokéAPI is niet bereikbaar: {e}")
    st.stop()

for key, default in {"dex": "pikachu", "left": "charizard", "right": "blastoise"}.items():
    st.session_state.setdefault(key, default)

mode = st.segmented_control(
    "Modus", ["Pokédex", "Battle"], default="Pokédex", label_visibility="collapsed"
)

if mode == "Battle":
    st.write("Zes stats, zes rondes. Wie de meeste rondes wint, wint de battle.")
    cols = st.columns(2)
    picks = []
    for col, key in zip(cols, ["left", "right"]):
        with col:
            st.selectbox("Pokémon", NAMES, key=key, format_func=pretty)
            st.button(
                "Verras me",
                key=f"rnd_{key}",
                icon=":material/casino:",
                on_click=pick_random,
                args=(key,),
            )
            picks.append(load_pokemon(st.session_state[key]))
            show_card(picks[-1])

    a, b = picks
    rows = []
    wins_a = wins_b = 0
    for stat in STAT_LABELS.values():
        va, vb = a["stats"][stat], b["stats"][stat]
        wins_a += va > vb
        wins_b += vb > va
        rows.append({"Stat": stat, pretty(a["name"]): va, pretty(b["name"]): vb})
    df = pd.DataFrame(rows)

    st.bar_chart(df, x="Stat", y=[pretty(a["name"]), pretty(b["name"])], stack=False)

    tot_a, tot_b = sum(a["stats"].values()), sum(b["stats"].values())
    if wins_a != wins_b:
        winner = a if wins_a > wins_b else b
        st.success(
            f"{pretty(winner['name'])} wint met {max(wins_a, wins_b)}–{min(wins_a, wins_b)} rondes.",
            icon=":material/emoji_events:",
        )
    elif tot_a != tot_b:
        winner = a if tot_a > tot_b else b
        st.success(
            f"Gelijkspel in rondes ({wins_a}–{wins_b}); {pretty(winner['name'])} wint op totaal ({max(tot_a, tot_b)} vs {min(tot_a, tot_b)}).",
            icon=":material/emoji_events:",
        )
    else:
        st.info("Perfect gelijkspel.")
    st.caption(f"Totaal base stats: {pretty(a['name'])} {tot_a} · {pretty(b['name'])} {tot_b}")

else:
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.selectbox("Zoek een Pokémon", NAMES, key="dex", format_func=pretty)
        st.button("Verras me", icon=":material/casino:", on_click=pick_random, args=("dex",))

    p = load_pokemon(st.session_state["dex"])
    left, right = st.columns([1, 2])
    with left:
        show_card(p)
    with right:
        stats = pd.DataFrame({"Stat": list(p["stats"]), "Base stat": list(p["stats"].values())})
        st.bar_chart(stats, x="Stat", y="Base stat", horizontal=True)
        st.metric("Totaal base stats", sum(p["stats"].values()))

st.caption("Data: pokeapi.co")
