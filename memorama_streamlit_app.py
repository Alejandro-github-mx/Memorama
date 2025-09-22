import streamlit as st
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

st.set_page_config(page_title="Memorama – SWPS Español", page_icon="🧠", layout="wide")

# -----------------------------
# Cargar estilos desde styles.css (tolerante a ausencia)
# -----------------------------
def local_css(file_name: str):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

local_css("styles.css")

@dataclass
class Term:
    text: str
    image: Optional[str] = None

# ---------------
# Helpers
# ---------------
def parse_term_line(raw: str) -> Term:
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        return Term("")
    if "\t" in raw:
        a, b = raw.split("\t", 1)
        return Term(text=a.strip(), image=b.strip() or None)
    if ";" in raw:
        a, b = raw.split(";", 1)
        return Term(text=a.strip(), image=b.strip() or None)
    return Term(text=raw)

def build_deck(terms: List[Term]) -> Tuple[List[Term], List[int]]:
    pairs = terms + terms
    order = list(range(len(pairs)))
    random.shuffle(order)
    return pairs, order

def cols_for_total(n_cards: int) -> Tuple[str, str]:
    if n_cards <= 20:
        return "cols-6", "cols-4"
    if n_cards <= 40:
        return "cols-8", "cols-5"
    return "cols-10", "cols-5"

def reset_state():
    st.session_state.phase = "setup"
    st.session_state.selected_n = 5
    st.session_state.terms_raw = ""
    st.session_state.deck = []
    st.session_state.order = []
    st.session_state.face_up = []        # lista (mantiene orden)
    st.session_state.matched = set()
    st.session_state.pair_map = {}
    st.session_state.resolve_at = None
    st.session_state.attempts = 0
    st.session_state.shuffle_show = False

# ---------------
# Session State init
# ---------------
if "phase" not in st.session_state:
    reset_state()
else:
    # Garantizar que existan todas las claves si el usuario viene de una sesión previa
    st.session_state.setdefault("selected_n", 5)
    st.session_state.setdefault("terms_raw", "")
    st.session_state.setdefault("deck", [])
    st.session_state.setdefault("order", [])
    st.session_state.setdefault("face_up", [])
    st.session_state.setdefault("matched", set())
    st.session_state.setdefault("pair_map", {})
    st.session_state.setdefault("resolve_at", None)
    st.session_state.setdefault("attempts", 0)
    st.session_state.setdefault("shuffle_show", False)

# ---------------
# Sidebar
# ---------------
with st.sidebar:
    st.header("🎛️ Configuración (Profesor)")

    valid_options = [5, 15, 20]
    if st.session_state.selected_n not in valid_options:
        st.session_state.selected_n = 5  # valor por defecto seguro

    st.session_state.selected_n = st.radio(
        "Número de términos (pares)",
        options=valid_options,
        index=valid_options.index(st.session_state.selected_n),
        help="Cada término tiene una ficha doble (p. ej., 5 términos = 10 fichas).",
    )

    st.write("Pegue sus términos abajo (separados por Enter, tabulador o punto y coma).")
    st.caption("Ejemplo:\nHola\thttps://ejemplo.com/imagen.png\nMundo;https://ejemplo.com/imagen2.jpg")

    st.session_state.terms_raw = st.text_area(
        "Términos (máximo 20)",
        height=220,
        value=st.session_state.terms_raw,
    )

    raw_input = st.session_state.terms_raw.strip()
    raw_terms = []
    if raw_input:
        normalized = raw_input.replace("\t", "\n").replace(";", "\n")
        raw_terms = [x.strip() for x in normalized.splitlines() if x.strip()]

    st.caption(f"Actualmente tienes {len(raw_terms)} término(s) detectado(s).")

    col_sb1, col_sb2 = st.columns(2)
    start_btn = reset_btn = False
    with col_sb1:
        if st.button("Construir tablero", type="primary"):
            start_btn = True
    with col_sb2:
        if st.button("Reiniciar todo"):
            reset_btn = True

    if reset_btn:
        reset_state()
        st.rerun()

# ---------------
# Build board
# ---------------
if start_btn:
    lines = [ln for ln in st.session_state.terms_raw.splitlines() if ln.strip()]
    terms_all = [parse_term_line(ln) for ln in lines]
    terms_all = [t for t in terms_all if t.text]

    if len(terms_all) < st.session_state.selected_n:
        st.warning(f"Necesitas al menos {st.session_state.selected_n} términos.")
    else:
        terms = terms_all[: st.session_state.selected_n]

        deck, order = build_deck(terms)

        # asignamos pares: indices 0..N-1 y N..2N-1 comparten id de par
        pair_map = {}
        for i, _term in enumerate(terms):
            pair_map[i] = i
            pair_map[i + len(terms)] = i

        st.session_state.deck = deck
        st.session_state.order = order
        st.session_state.pair_map = pair_map
        st.session_state.face_up = []
        st.session_state.matched = set()
        st.session_state.attempts = 0
        st.session_state.phase = "playing"
        st.session_state.shuffle_show = True
        st.rerun()

# ---------------
# Header
# ---------------
st.title("🧠 Memorama – Encuentra los pares")

# ---------------
# Shuffle animation
# ---------------
if st.session_state.phase == "playing" and st.session_state.shuffle_show:
    n_cards = len(st.session_state.deck)
    st.subheader("Mezclando fichas…")
    st.markdown(
        "<div style='display:grid;grid-template-columns:repeat(6,1fr);gap:8px;'>"
        + "".join(["<div class='ghost-tile'></div>" for _ in range(n_cards)])
        + "</div>",
        unsafe_allow_html=True
    )
    time.sleep(1.2)
    st.session_state.shuffle_show = False
    st.rerun()

# -------------------
# Gameplay
# -------------------
if st.session_state.phase == "playing":
    deck = st.session_state.deck
    order = st.session_state.order
    n_cards = len(deck)
    N = n_cards // 2

    # Resolver pares pendientes (con guardas)
    if st.session_state.resolve_at and time.time() >= st.session_state.resolve_at:
        # Considerar solo cartas volteadas que aún no están emparejadas
        not_matched_flipped = [p for p in st.session_state.face_up if p not in st.session_state.matched]
        last_two = not_matched_flipped[-2:]
        if len(last_two) == 2:
            pos1, pos2 = last_two
            same = st.session_state.pair_map.get(pos1) == st.session_state.pair_map.get(pos2)
            if same:
                st.session_state.matched.update({pos1, pos2})

        # Tras la espera, dejar visibles únicamente las emparejadas
        st.session_state.face_up = [p for p in st.session_state.face_up if p in st.session_state.matched]
        st.session_state.resolve_at = None
        st.rerun()

    # Barra de stats
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Pares", f"{len(st.session_state.matched)//2} / {N}")
    with col_b:
        st.metric("Intentos", f"{st.session_state.attempts}")
    with col_c:
        if st.button("Revelar todo (1s)"):
            # Mostrar todo temporalmente, luego ocultar no emparejadas sin intentar comparar
            st.session_state.face_up = list(range(n_cards))
            st.session_state.resolve_at = time.time() + 1.0
            st.rerun()

    # Tablero
    visual_positions = list(range(n_cards))
    per_row = 6 if n_cards <= 20 else 8
    rows = [visual_positions[i:i+per_row] for i in range(0, n_cards, per_row)]

    for row in rows:
        cols = st.columns(len(row), gap="small")
        for j, vpos in enumerate(row):
            pos = order[vpos]
            is_up = pos in st.session_state.face_up or pos in st.session_state.matched
            label_number = vpos + 1

            with cols[j]:
                if is_up:
                    face_label = deck[pos].text
                    st.button(face_label, key=f"up-{vpos}", disabled=True, use_container_width=True)
                else:
                    if st.button(f"{label_number}", key=f"btn-{vpos}", use_container_width=True):
                        # Evitar duplicar la misma carta si ya está abierta (por seguridad)
                        if pos not in st.session_state.face_up and pos not in st.session_state.matched:
                            st.session_state.face_up.append(pos)
                            # Cuando hay dos nuevas abiertas, contar intento y programar resolución
                            not_matched_flipped = [p for p in st.session_state.face_up if p not in st.session_state.matched]
                            if len(not_matched_flipped) % 2 == 0:
                                st.session_state.attempts += 1
                                st.session_state.resolve_at = time.time() + 0.9
                        st.rerun()

# ---------------
# Botón de celebración
# ---------------
if st.button("🎉 Celebrar"):
    choice = random.choice(["balloons", "success", "snow"])
    if choice == "balloons":
        st.balloons()
    elif choice == "success":
        st.success("¡Felicidades, gran trabajo! 🎉")
    elif choice == "snow":
        st.snow()

# ---------------
# Footer
# ---------------
st.divider()
st.markdown(
    """
    **Cómo usar:**
    1) En la barra lateral, elija 5/15/20 pares.  
    2) Pegue sus términos (solo texto o texto + imagen con tab/;).  
    3) Presione **Construir tablero**.  
    4) Voltee las cartas. Si quiere festejar, presione el botón **🎉 Celebrar**.
    """
)
