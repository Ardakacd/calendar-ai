"""Generate the multi-agent architecture diagram as a high-res PNG."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ── Colors (matching slide palette) ─────────────────────────
BG       = "#0F172A"
CARD_BG  = "#17203A"
BLUE     = "#609CFF"
PURPLE   = "#7C5CFF"
GREEN    = "#4ADE80"
ORANGE   = "#FBBF24"
RED      = "#F87171"
TEAL     = "#2DD4BF"
CYAN     = "#22D3EE"
WHITE    = "#FFFFFF"
GRAY     = "#A0AAC0"
GRAY_DIM = "#4A5568"

fig, ax = plt.subplots(figsize=(14, 10), facecolor=BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis("off")

# ── Helpers ─────────────────────────────────────────────────
def draw_box(x, y, w, h, label, color, sublabel=None, fontsize=11):
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle="round,pad=0.12",
        facecolor=color + "22",
        edgecolor=color,
        linewidth=1.8,
    )
    ax.add_patch(box)
    ax.text(x, y + (0.08 if sublabel else 0), label,
            ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=WHITE, fontfamily="sans-serif")
    if sublabel:
        ax.text(x, y - 0.28, sublabel,
                ha="center", va="center", fontsize=8,
                color=GRAY, fontfamily="sans-serif")

def draw_arrow(x1, y1, x2, y2, color=GRAY, style="-", lw=1.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=color,
                    lw=lw,
                    linestyle=style,
                    shrinkA=6, shrinkB=6,
                    mutation_scale=14,
                ))

def draw_label(x1, y1, x2, y2, text, color=GRAY, offset=(0, 0.15)):
    mx = (x1 + x2) / 2 + offset[0]
    my = (y1 + y2) / 2 + offset[1]
    ax.text(mx, my, text, ha="center", va="center",
            fontsize=8, color=color, fontfamily="sans-serif",
            fontstyle="italic")

# ── Layout positions ────────────────────────────────────────
# Main flow (center column)
user_pos     = (7, 9.0)
router_pos   = (7, 7.6)
sched_pos    = (4.5, 6.0)
leisure_pos  = (9.5, 6.0)
convo_pos    = (11.5, 7.6)
conflict_pos = (4.5, 4.3)
finalize_pos = (4.5, 2.7)
notif_pos    = (4.5, 1.2)
response_pos = (9.5, 1.2)

# Tool clusters
tools_sched  = (1.3, 5.0)
tools_confl  = (1.3, 3.3)

# ── Draw boxes ──────────────────────────────────────────────
draw_box(*user_pos, 2.4, 0.6, "User Input", BLUE)
draw_box(*router_pos, 2.4, 0.7, "Router Agent", BLUE, "classifies intent")
draw_box(*sched_pos, 2.6, 0.7, "Scheduling Agent", GREEN, "create / update / delete / list")
draw_box(*leisure_pos, 2.6, 0.7, "Leisure Search", ORANGE, "Tavily web search")
draw_box(*convo_pos, 2.4, 0.6, "Conversation", GRAY_DIM, "general chat")
draw_box(*conflict_pos, 2.8, 0.7, "Conflict Resolution", RED, "overlaps & alternatives")
draw_box(*finalize_pos, 2.6, 0.7, "Scheduling Finalize", PURPLE, "execute operation")
draw_box(*notif_pos, 2.6, 0.7, "Notification Agent", TEAL, "push + email alerts")
draw_box(*response_pos, 2.4, 0.6, "Response", CYAN)

# ── MCP Tool boxes ──────────────────────────────────────────
def draw_tool_group(cx, cy, title, tools, color):
    # Background card
    w, h = 2.2, len(tools) * 0.32 + 0.6
    card = FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.1",
        facecolor=BG,
        edgecolor=color,
        linewidth=1.0,
        linestyle="--",
    )
    ax.add_patch(card)
    ax.text(cx, cy + h/2 - 0.2, title, ha="center", va="center",
            fontsize=8, fontweight="bold", color=color, fontfamily="sans-serif")
    for i, tool in enumerate(tools):
        ax.text(cx, cy + h/2 - 0.48 - i * 0.32, f"• {tool}",
                ha="center", va="center", fontsize=7, color=GRAY,
                fontfamily="sans-serif")

draw_tool_group(*tools_sched, "Calendar Tools", [
    "list_event",
    "create_event",
    "update_event",
    "delete_event",
], GREEN)

draw_tool_group(*tools_confl, "Conflict Tools", [
    "check_conflict",
    "suggest_alternatives",
    "find_free_slots",
], RED)

# ── Draw arrows ─────────────────────────────────────────────
# Main flow
draw_arrow(*user_pos, *router_pos, BLUE)

# Router branches
draw_arrow(router_pos[0], router_pos[1] - 0.35,
           sched_pos[0], sched_pos[1] + 0.35, GREEN, lw=2)
draw_label(router_pos[0], router_pos[1], sched_pos[0], sched_pos[1],
           "CRUD", GREEN, offset=(-0.3, 0.25))

draw_arrow(router_pos[0], router_pos[1] - 0.35,
           leisure_pos[0], leisure_pos[1] + 0.35, ORANGE, lw=2)
draw_label(router_pos[0], router_pos[1], leisure_pos[0], leisure_pos[1],
           "search", ORANGE, offset=(0.3, 0.25))

draw_arrow(router_pos[0] + 1.2, router_pos[1],
           convo_pos[0] - 1.2, convo_pos[1], GRAY_DIM, lw=1.2)
draw_label(router_pos[0], router_pos[1], convo_pos[0], convo_pos[1],
           "chat", GRAY, offset=(0, 0.18))

# Scheduling → Conflict
draw_arrow(sched_pos[0], sched_pos[1] - 0.35,
           conflict_pos[0], conflict_pos[1] + 0.35, RED)

# Conflict → Finalize
draw_arrow(conflict_pos[0], conflict_pos[1] - 0.35,
           finalize_pos[0], finalize_pos[1] + 0.35, PURPLE)

# Finalize → Notification
draw_arrow(finalize_pos[0], finalize_pos[1] - 0.35,
           notif_pos[0], notif_pos[1] + 0.35, TEAL)

# Notification → Response
draw_arrow(notif_pos[0] + 1.3, notif_pos[1],
           response_pos[0] - 1.2, response_pos[1], CYAN)

# Leisure → Response
draw_arrow(leisure_pos[0], leisure_pos[1] - 0.35,
           response_pos[0], response_pos[1] + 0.35, CYAN)

# Conversation → Response
draw_arrow(convo_pos[0], convo_pos[1] - 0.3,
           response_pos[0] + 0.5, response_pos[1] + 0.5, CYAN, lw=1.0)

# Dashed shortcut: no conflict → finalize
draw_arrow(sched_pos[0] + 1.3, sched_pos[1] - 0.15,
           finalize_pos[0] + 1.3, finalize_pos[1] + 0.15,
           GRAY_DIM, style="--", lw=1.0)
ax.text(6.2, 4.35, "no conflict", ha="center", va="center",
        fontsize=7, color=GRAY_DIM, fontfamily="sans-serif", fontstyle="italic")

# Tool connections (dashed)
draw_arrow(tools_sched[0] + 1.1, tools_sched[1] + 0.2,
           sched_pos[0] - 1.3, sched_pos[1] - 0.1,
           GREEN, style="--", lw=1.0)

draw_arrow(tools_confl[0] + 1.1, tools_confl[1] + 0.2,
           conflict_pos[0] - 1.4, conflict_pos[1] - 0.1,
           RED, style="--", lw=1.0)

# ── Title ───────────────────────────────────────────────────
ax.text(7, 9.7, "Calen — Multi-Agent Architecture",
        ha="center", va="center", fontsize=16, fontweight="bold",
        color=WHITE, fontfamily="sans-serif")

# ── Save ────────────────────────────────────────────────────
out = "/Users/ardakabadayi/Desktop/Code/calendar-ai/architecture_diagram.png"
plt.tight_layout(pad=0.5)
plt.savefig(out, dpi=200, facecolor=BG, bbox_inches="tight")
plt.close()
print(f"Saved to {out}")
