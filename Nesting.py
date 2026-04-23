import matplotlib
matplotlib.use("TkAgg")

import tkinter as tk
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import ezdxf

# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================
GAP = 10
ATTEMPTS = 10
ALLOW_ROTATION = True

pieces = []

# =====================================================
# FUNÇÕES GEOMÉTRICAS
# =====================================================
def intersects(r1, r2):
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2
    return not (
        x1 + w1 <= x2 or
        x2 + w2 <= x1 or
        y1 + h1 <= y2 or
        y2 + h2 <= y1
    )

def generate_candidates(placed):
    points = {(0, 0)}
    for x, y, w, h in placed:
        points.add((x + w, y))
        points.add((x, y + h))
    return sorted(points, key=lambda p: (p[1], p[0]))

# =====================================================
# NESTING ENGINE (OTIMIZADO + MULTI-CHAPAS)
# =====================================================
def nest_multi_sheet(pieces, sheet_w, sheet_h):
    best_solution = None
    best_area = 0

    for _ in range(ATTEMPTS):
        remaining = pieces[:]
        sheets = []

        while remaining:
            placed = []
            layout = []

            for w, h in sorted(
                remaining, key=lambda p: p[0]*p[1], reverse=True
            ):
                placed_flag = False
                candidates = generate_candidates(placed)

                for x, y in candidates:
                    orientations = [(w, h)]
                    if ALLOW_ROTATION:
                        orientations.append((h, w))

                    for rw, rh in orientations:
                        rwg = rw + GAP
                        rhg = rh + GAP

                        if x + rwg <= sheet_w and y + rhg <= sheet_h:
                            if all(
                                not intersects((x, y, rwg, rhg), r)
                                for r in placed
                            ):
                                placed.append((x, y, rwg, rhg))
                                layout.append((x, y, rw, rh))
                                placed_flag = True
                                break

                    if placed_flag:
                        break

                if placed_flag:
                    remaining.remove((w, h))

            sheets.append(layout)

        used_area = sum(
            w*h for sheet in sheets for _,_,w,h in sheet
        )

        if used_area > best_area:
            best_area = used_area
            best_solution = sheets

    return best_solution

# =====================================================
# EXPORTAÇÃO PDF
# =====================================================
def export_pdf(sheets, sheet_w, sheet_h, filename):
    c = canvas.Canvas(filename, pagesize=A4)

    for i, sheet in enumerate(sheets, start=1):
        c.drawString(50, 800, f"Chapa {i}")
        scale = min(500/sheet_w, 300/sheet_h)

        for x, y, w, h in sheet:
            c.rect(
                50 + x*scale,
                100 + y*scale,
                w*scale,
                h*scale
            )

        c.showPage()

    c.save()

# =====================================================
# EXPORTAÇÃO DXF
# =====================================================
def export_dxf(sheets, filename):
    doc = ezdxf.new()
    msp = doc.modelspace()
    offset_x = 0

    for sheet in sheets:
        for x, y, w, h in sheet:
            msp.add_lwpolyline([
                (offset_x + x, y),
                (offset_x + x + w, y),
                (offset_x + x + w, y + h),
                (offset_x + x, y + h),
                (offset_x + x, y)
            ])
        offset_x += 7000

    doc.saveas(filename)

# =====================================================
# INTERFACE – FUNÇÕES
# =====================================================
def add_piece():
    try:
        w = int(entry_pw.get())
        h = int(entry_ph.get())
        q = int(entry_qty.get())
        for _ in range(q):
            pieces.append((w, h))
        listbox.insert(tk.END, f"{q}x peça {w} x {h} mm")
    except ValueError:
        messagebox.showerror("Erro", "Dados inválidos")

def calculate():
    global current_solution

    try:
        sheet_w = int(entry_sw.get())
        sheet_h = int(entry_sh.get())
    except ValueError:
        messagebox.showerror("Erro", "Dimensão da chapa inválida")
        return

    if not pieces:
        messagebox.showerror("Erro", "Nenhuma peça cadastrada")
        return

    current_solution = nest_multi_sheet(pieces, sheet_w, sheet_h)

    used_area = sum(
        w*h for sheet in current_solution for _,_,w,h in sheet
    )
    utilization = used_area / (sheet_w * sheet_h) * 100

    fig, ax = plt.subplots(figsize=(14, 6))

    spacing = sheet_w + 500  # espaço visual entre chapas

    for i, sheet in enumerate(current_solution):
        offset_x = i * spacing

        # Desenhar contorno da chapa
        ax.add_patch(
            plt.Rectangle(
                (offset_x, 0),
                sheet_w,
                sheet_h,
                fill=False,
                linewidth=2,
                edgecolor="black"
            )
        )

        # Desenhar peças
        for x, y, w, h in sheet:
            ax.add_patch(
                plt.Rectangle(
                    (offset_x + x, y),
                    w,
                    h,
                    facecolor="tab:blue",
                    edgecolor="black",
                    alpha=0.7
                )
            )

        # Texto identificador da chapa
        ax.text(
            offset_x + sheet_w / 2,
            sheet_h + 80,
            f"Chapa {i+1}",
            ha="center",
            fontsize=10,
            weight="bold"
        )

    # Limites corretos em mm
    ax.set_xlim(0, spacing * len(current_solution))
    ax.set_ylim(0, sheet_h + 200)

    # Escala real
    ax.set_aspect("equal", adjustable="box")

    # Grade leve
    ax.grid(True, linestyle="--", alpha=0.4)

    # Labels
    ax.set_xlabel("Milímetros (X)")
    ax.set_ylabel("Milímetros (Y)")

    ax.set_title(
        f"Aproveitamento: {utilization:.2f}% | "
        f"Chapas usadas: {len(current_solution)}"
    )

    plt.tight_layout()
    plt.show()

def save_pdf():
    if not current_solution:
        return
    file = filedialog.asksaveasfilename(
        defaultextension=".pdf"
    )
    export_pdf(
        current_solution,
        int(entry_sw.get()),
        int(entry_sh.get()),
        file
    )

def save_dxf():
    if not current_solution:
        return
    file = filedialog.asksaveasfilename(
        defaultextension=".dxf"
    )
    export_dxf(current_solution, file)

def reset():
    pieces.clear()
    listbox.delete(0, tk.END)

# =====================================================
# INTERFACE – TKINTER
# =====================================================
current_solution = None

root = tk.Tk()
root.title("Nesting de Chapas – Versão Industrial")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

tk.Label(frame, text="Chapa (mm)").grid(row=0, column=0, columnspan=2)
tk.Label(frame, text="Largura").grid(row=1, column=0)
entry_sw = tk.Entry(frame, width=10)
entry_sw.insert(0, "6000")
entry_sw.grid(row=1, column=1)

tk.Label(frame, text="Altura").grid(row=2, column=0)
entry_sh = tk.Entry(frame, width=10)
entry_sh.insert(0, "2500")
entry_sh.grid(row=2, column=1)

tk.Label(frame, text="Peça (mm)").grid(row=3, column=0, columnspan=2, pady=5)
tk.Label(frame, text="Largura").grid(row=4, column=0)
entry_pw = tk.Entry(frame, width=10)
entry_pw.grid(row=4, column=1)

tk.Label(frame, text="Altura").grid(row=5, column=0)
entry_ph = tk.Entry(frame, width=10)
entry_ph.grid(row=5, column=1)

tk.Label(frame, text="Quantidade").grid(row=6, column=0)
entry_qty = tk.Entry(frame, width=10)
entry_qty.grid(row=6, column=1)

tk.Button(frame, text="Adicionar peça", command=add_piece)\
    .grid(row=7, column=0, columnspan=2, pady=5)

listbox = tk.Listbox(frame, width=35)
listbox.grid(row=8, column=0, columnspan=2)

tk.Button(frame, text="Calcular", command=calculate)\
    .grid(row=9, column=0, columnspan=2, pady=5)

tk.Button(frame, text="Exportar PDF", command=save_pdf)\
    .grid(row=10, column=0, pady=2)

tk.Button(frame, text="Exportar DXF", command=save_dxf)\
    .grid(row=10, column=1, pady=2)

tk.Button(frame, text="Limpar tudo", command=reset)\
    .grid(row=11, column=0, columnspan=2, pady=5)

root.mainloop()
