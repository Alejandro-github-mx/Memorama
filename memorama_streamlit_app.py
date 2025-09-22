import streamlit as st
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

st.set_page_config(page_title="Memorama – SWPS Español", page_icon="🧠", layout="wide")

# -----------------------------
# Styles (CSS animations + layout)
# -----------------------------
st.markdown(
    """
    <style>
      /* Base card styles */
      .card-btn { width: 100%; height: 88px; font-weight: 700; border-radius: 16px; }
      .card-grid { display: grid; grid-gap: 10px; }

      /* Responsive grid: choose columns based on total cards */
      @media (min-width: 1024px) {
        .cols-6 { grid-template-columns: repeat(6, 1fr); }
        .cols-8 { grid-template-columns: repeat(8, 1fr); }
        .cols-10{ grid-template-columns: repeat(10, 1fr); }
      }
      @media (max-width: 1023px) {
        .cols-4 { grid-template-columns: repeat(4, 1fr); }
        .cols-5 { grid-template-columns: repeat(5, 1fr); }
      }

      /* Simple shuffle animation for tiles */
      .shuffle .ghost-tile {
        height: 60px; border-radius: 12px; margin: 6px; opacity: .85;
        background: linear-gradient(45deg, #cad7ff, #e8ecff);
        animation: wiggle 0.9s ease-in-out infinite alternate;
      }
      @keyframes wiggle {
        from { transform: translate(-6px, 4px) rotate(-2deg); }
        to   { transform: translate(6px, -4px) rotate(2deg); }
      }

      /* Celebration overlay */
      .celebrate {
        position: fixed; inset: 0; pointer-events: none; z-index: 9999;
        background: radial-gradient(ellipse at center, rgba(255,255,255,.0) 0%, rgba(255,255,255,.0) 60%, rgba(255,255,255,.85) 100%);
        animation: fadeout 1.8s ease forwards;
      }
      @keyframes fadeout { from {opacity: 1} to {opacity: 0} }

      /* Face-up card content */
      .term { font-size: 14px; font-weight: 700; }
      .term small { font-weight: 600; opacity: .7; }
      .img { max-width: 100%; max-height: 60px; display:block; margin: 4px auto 0; border-radius: 8px; }

      /* Muted helper text */
      .muted { opacity: .75; }
    </style>
    """,
    unsafe_allow_html=True,
)

@dataclass
class Term:
    text: str
    image: Optional[str] = None

# ---------------
# Helpers
# ---------------

def parse_term_line(line: str) -> Term:
    """Parse a single line into Term. Accepted formats:
    - "term"
    - "term | image_url"
    - "term, image_url"
    - "term\timage_url"
    Whitespace around separators is stripped.
    """
    raw = line.strip().strip('"').strip("'")
    if not raw:
        return Term("")
    # Try common separators
    for sep in ["|", ",", "\t", ";"]:
        if sep in raw:
            a, b = raw.split(sep, 1)
            t = a.strip()
            img = b.strip() or None
            return Term(text=t, image=img)
    return Term(text=raw)


def build_deck(terms: List[Term]) -> Tuple[List[Term], List[int]]:
    """Duplicate terms to make pairs, shuffle positions, and return deck + order.
    order: list of indices (positions) shuffled.
    """
    pairs = terms + terms  # duplicate to create pairs
    order = list(range(len(pairs)))
    random.shuffle(order)
    return pairs, order


def cols_for_total(n_cards: int) -> Tuple[str, str]:
    """Return CSS classes for desktop and mobile grids based on total cards."""
    if n_cards <= 20:
        return "cols-6", "cols-4"
    if n_cards <= 40:
        return "cols-8", "cols-5"
    return "cols-10", "cols-5"

# ---------------
# Session State init
# ---------------
if "phase" not in st.session_state:
    st.session_state.phase = "setup"  # setup | playing | finished
if "selected_n" not in st.session_state:
    st.session_state.selected_n = 10
if "terms_raw" not in st.session_state:
    st.session_state.terms_raw = ""
if "deck" not in st.session_state:
    st.session_state.deck = []  # list[Term] of length 2N (pairs duplicated)
if "order" not in st.session_state:
    st.session_state.order = []  # permutation of positions
if "face_up" not in st.session_state:
    st.session_state.face_up = set()  # positions (0..2N-1)
if "matched" not in st.session_state:
    st.session_state.matched = set()
if "pair_map" not in st.session_state:
    st.session_state.pair_map = {}  # pos -> pair_id (0..N-1)
if "resolve_at" not in st.session_state:
    st.session_state.resolve_at = None  # timestamp when to resolve a pending pair
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "shuffle_show" not in st.session_state:
    st.session_state.shuffle_show = False

# ---------------
# Sidebar: Teacher controls
# ---------------
with st.sidebar:
    st.header("🎛️ Configuración (Profesor)")
    st.session_state.selected_n = st.radio(
        "Número de términos (pares)",
        options=[10, 20, 30, 50],
        index=[10, 20, 30, 50].index(st.session_state.selected_n),
        help="Elige cuántos pares quieres jugar.",
    )

    st.write("Pegue sus términos abajo (1 por línea). Opcionalmente agregue URL de imagen tras un separador.")
    st.caption("Formatos válidos: `término`, `término | https://...`, `término, https://...` o con tabulador.")
    st.session_state.terms_raw = st.text_area(
        "Términos (máximo 50)",
        height=220,
        placeholder=(
            "Ejemplos:\nMe despierto | https://ejemplo.com/imagen1.png\nMe visto\nDesayuno, https://ejemplo.com/imagen2.jpg\nLlego a la escuela\n..."
        ),
        value=st.session_state.terms_raw,
    )

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        start_btn = st.button("Construir tablero", type="primary")
    with col_sb2:
        reset_btn = st.button("Reiniciar todo", help="Vuelve a la configuración inicial.")

    if reset_btn:
        for k in [
            "phase","deck","order","face_up","matched","pair_map","resolve_at",
            "attempts","start_time","shuffle_show"
        ]:
            st.session_state[k] = {"face_up": set(), "matched": set()}.get(k, None) if k in ["face_up","matched"] else None
        st.session_state.phase = "setup"
        st.experimental_rerun()

# ---------------
# Build board when requested
# ---------------
if start_btn:
    # Parse terms
    lines = [ln for ln in st.session_state.terms_raw.splitlines() if ln.strip()]
    terms_all = [parse_term_line(ln) for ln in lines]
    # Filter out empties
    terms_all = [t for t in terms_all if t.text]

    if len(terms_all) < st.session_state.selected_n:
        st.warning(f"Necesitas al menos {st.session_state.selected_n} términos válidos. Actualmente tienes {len(terms_all)}.")
    else:
        terms = terms_all[: st.session_state.selected_n]
        deck, order = build_deck(terms)
        # Build pair map: same pair_id for two copies
        pair_map = {}
        # The deck is duplicated in order: terms + terms. We'll pair by index modulo N
        N = len(terms)
        for i in range(len(deck)):
            pair_map[i] = i % N
        st.session_state.deck = deck
        st.session_state.order = order
        st.session_state.pair_map = pair_map
        st.session_state.face_up = set()
        st.session_state.matched = set()
        st.session_state.attempts = 0
        st.session_state.start_time = time.time()
        st.session_state.phase = "playing"
        st.session_state.shuffle_show = True
        st.experimental_rerun()

# ---------------
# Header
# ---------------
st.title("🧠 Memorama – Encuentra los pares")
st.caption("Profesor: configure los términos en la barra lateral. Al jugar, las tarjetas boca abajo muestran números en orden ascendente.")

# ---------------
# Shuffle animation screen
# ---------------
if st.session_state.phase == "playing" and st.session_state.shuffle_show:
    n_pairs = len(st.session_state.deck) // 2
    n_cards = n_pairs * 2
    d_cls, m_cls = cols_for_total(n_cards)

    st.subheader("Mezclando fichas…")
    st.markdown(f"<div class='card-grid shuffle {d_cls} {m_cls}'>" + "".join(["<div class='ghost-tile'></div>" for _ in range(n_cards)]) + "</div>", unsafe_allow_html=True)
    # Show animation briefly then reveal the board
    time.sleep(1.2)
    st.session_state.shuffle_show = False
    st.experimental_rerun()

# ---------------
# Gameplay board
# ---------------
if st.session_state.phase == "playing":
    deck = st.session_state.deck
    order = st.session_state.order
    n_cards = len(deck)
    N = n_cards // 2

    # Resolve pending pair after a short display delay
    if st.session_state.resolve_at and time.time() >= st.session_state.resolve_at:
        pos1, pos2 = sorted(list(st.session_state.face_up))[:2]
        same = st.session_state.pair_map[pos1] == st.session_state.pair_map[pos2]
        if same:
            st.session_state.matched.update({pos1, pos2})
        # In both cases we clear the face_up after the reveal window
        st.session_state.face_up = set()
        st.session_state.resolve_at = None
        # Check finish
        if len(st.session_state.matched) == n_cards:
            st.session_state.phase = "finished"
            st.experimental_rerun()

    # Stats row
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Pares", f"{len(st.session_state.matched)//2} / {N}")
    with col_b:
        st.metric("Intentos", f"{st.session_state.attempts}")
    with col_c:
        elapsed = 0 if not st.session_state.start_time else int(time.time() - st.session_state.start_time)
        st.metric("Tiempo (s)", f"{elapsed}")
    with col_d:
        if st.button("Revelar todo (1s)"):
            # Temporarily show all, then hide again
            st.session_state.face_up = set(range(n_cards))
            st.session_state.resolve_at = time.time() + 1.0
            st.experimental_rerun()

    # Choose grid classes
    d_cls, m_cls = cols_for_total(n_cards)

    # Render the grid
    # We'll iterate in ascending display order by position id (1..n_cards) for the numbering requirement
    grid_html = []
    # We will create one button per card using columns to maintain interactivity
    # To respect ascending numbering, we map visual_position -> actual shuffled index
    visual_positions = list(range(n_cards))  # 0..n_cards-1

    # Create a container to hold the grid with custom CSS grid
    grid = st.container()
    with grid:
        # We'll simulate a grid with columns per row size decided by approx columns based on total
        # But to keep a consistent look, we render using HTML for the grid wrapper and have Streamlit buttons inside via columns chunking
        per_row = 6 if n_cards <= 20 else (8 if n_cards <= 40 else 10)
        rows = [visual_positions[i:i+per_row] for i in range(0, n_cards, per_row)]
        for row in rows:
            cols = st.columns(len(row), gap="small")
            for j, vpos in enumerate(row):
                pos = order[vpos]  # actual deck index at this visual position
                is_matched = pos in st.session_state.matched
                is_up = (pos in st.session_state.face_up) or is_matched
                label_number = vpos + 1  # ascending numbers on the back

                # Build label
                if is_up:
                    term = deck[pos].text
                    label = f"{term}"
                else:
                    label = f"{label_number}"

                disabled = is_matched or (st.session_state.resolve_at is not None and not is_up)
                clicked = cols[j].button(label, key=f"btn-{vpos}", disabled=disabled, use_container_width=True)

                # Show image/text when face-up
                if is_up:
                    t = deck[pos]
                    with cols[j]:
                        st.markdown(f"<div class='term muted'><small>#{label_number}</small></div>", unsafe_allow_html=True)
                        if t.image:
                            try:
                                st.image(t.image, caption=None, use_column_width=True)
                            except Exception:
                                st.caption("(No se pudo cargar la imagen)")

                if clicked and not is_up:
                    # Flip this card
                    st.session_state.face_up.add(pos)
                    if len(st.session_state.face_up) % 2 == 0:
                        # Just flipped the 2nd card of a pair -> schedule resolve
                        st.session_state.attempts += 1
                        st.session_state.resolve_at = time.time() + 0.65
                    st.experimental_rerun()

# ---------------
# Finished state
# ---------------
if st.session_state.phase == "finished":
    duration = int(time.time() - (st.session_state.start_time or time.time()))
    pairs = len(st.session_state.deck)//2
    st.markdown("<div class='celebrate'></div>", unsafe_allow_html=True)
    st.balloons()
    st.success("¡Todas las fichas encontradas! 🎉")
    col1, col2, col3 = st.columns(3)
    col1.metric("Pares totales", f"{pairs}")
    col2.metric("Intentos", f"{st.session_state.attempts}")
    col3.metric("Tiempo (s)", f"{duration}")

    st.caption("Use la barra lateral para reiniciar y cargar una nueva lista de términos.")

# ---------------
# Footer help
# ---------------
st.divider()
st.markdown(
    """
    **Cómo usar (rápido):**
    1) En la barra lateral, elija 10/20/30/50 pares.  
    2) Pegue sus términos, uno por línea. Para añadir imagen opcional, use `|` o `,` seguido de la URL.  
    3) Presione **Construir tablero**.  
    4) Las tarjetas boca abajo muestran números ascendentes. Al voltearlas, verán el término (y su imagen si existe).  
    5) Al completar todos los pares, aparece una animación de celebración.
    """
)
