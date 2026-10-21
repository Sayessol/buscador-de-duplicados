"""Prueba de humo de las ventanas auxiliares, con la interfaz de verdad:

  · el visor de imagen (zoom, ajustar, rueda, imagen rota, archivo que no es imagen),
  · el historial (deshacer un «mover», deshacer un «copiar», y un deshacer que falla),
  · el diálogo de qué hacer con los archivos que no son imágenes (aplicar y cancelar),
  · el desglose por extensión (excluir una),
  · la exportación a CSV y las miniaturas / vista previa de imágenes.

    python pruebas/humo_dialogos.py
"""

import csv
import os
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# No toca los datos reales del usuario (historial, configuración):
TMP = Path(tempfile.mkdtemp(prefix="dup_dlg_"))
os.environ["APPDATA"] = str(TMP / "appdata")

from PIL import Image                                   # noqa: E402

from core import historial                              # noqa: E402
from core.mover import MOVER                            # noqa: E402
from core.reunir import AGRUPAR, DEJAR                  # noqa: E402
from core.scanner import escanear                       # noqa: E402
from ui import icons, styles, thumbnails                # noqa: E402
from ui.history_window import VentanaHistorial          # noqa: E402
from ui.image_viewer import VisorImagen, abrir_visor    # noqa: E402
from ui.main_window import VentanaPrincipal             # noqa: E402
from ui.tipos_dialog import VentanaTiposNoImagen        # noqa: E402
from ui.tipos_duplicados_dialog import VentanaTipos     # noqa: E402

fallos = []
avisos = {"preguntas": 0, "info": 0, "aviso": 0, "error": 0}


def check(cond, msg):
    print(f"  [{'OK  ' if cond else 'FALLA'}] {msg}")
    if not cond:
        fallos.append(msg)


def simular_cuadros_de_dialogo():
    def contar(clave, devuelve=None):
        def f(*_a, **_k):
            avisos[clave] += 1
            return devuelve
        return f
    messagebox.askyesno = contar("preguntas", True)
    messagebox.showinfo = contar("info")
    messagebox.showwarning = contar("aviso")
    messagebox.showerror = contar("error")


def main():
    styles.aplicar_tema()
    simular_cuadros_de_dialogo()
    app = VentanaPrincipal()
    app.update()

    # ------------------------------------------------------------ visor de imagen
    print("Visor de imagen")
    foto = TMP / "foto.png"
    Image.new("RGB", (800, 600), (30, 120, 200)).save(foto)
    visor = VisorImagen(app, str(foto))
    app.update()
    visor._set_escala(1.0)
    check("800×600" in visor._lbl_info.cget("text"), "enseña las dimensiones de la foto")
    visor._zoom(1.25)
    check(abs(visor._escala - 1.25) < 1e-9, "el botón + amplía un 25 %")
    visor._zoom(1 / 1.25)
    visor._ajustar()
    app.update()
    check(0.05 <= visor._escala <= 1.0, "«Ajustar» deja la foto entera dentro de la ventana")
    anterior = visor._escala

    class Evento:
        delta = 120
    visor._rueda(Evento())
    check(visor._escala > anterior, "la rueda del ratón hacia arriba amplía")
    visor._set_escala(99)
    check(visor._escala == 8.0, "el zoom tiene un máximo (8×)")
    visor._set_appearance_mode("Light")
    visor.destroy()

    rota = TMP / "rota.png"
    rota.write_bytes(b"esto no es una imagen")
    visor_roto = VisorImagen(app, str(rota))
    app.update()
    check(visor_roto._orig is None, "una imagen rota no hace caer el visor")
    visor_roto.destroy()

    abrir_visor(app, str(TMP / "notas.txt"))                      # no es imagen: no abre nada
    abrir_visor(app, str(TMP / "no_existe.png"))                  # no existe: tampoco
    check(not any(isinstance(h, VisorImagen) for h in app.winfo_children()),
          "no abre el visor para archivos que no son imágenes o no existen")

    # ------------------------------------------------- miniaturas y vista previa
    print("Miniaturas")
    mini = thumbnails.miniatura_o_placeholder(str(foto), 40)
    check(mini.size == (40, 40), "miniatura cuadrada de una imagen real")
    placeholder = thumbnails.miniatura_o_placeholder(str(rota), 40)
    check(placeholder.size == (40, 40), "una imagen rota da un recuadro con la extensión")
    grande = thumbnails.vista_grande(str(foto), 250)
    check(max(grande.size) <= 250, "vista previa grande encajada en el cuadrado")
    check(thumbnails.vista_grande(str(rota), 250).size[0] > 0,
          "vista previa de imagen rota: recuadro")
    check(icons.icono_ventana(32).width() == 32, "el icono de la ventana se dibuja")

    # ------------------------------------------------------------------ historial
    print("Historial")
    vacio = VentanaHistorial(app)
    app.update()
    check(len(vacio.lista.winfo_children()) == 1, "sin operaciones: aviso de «todavía no hay»")
    vacio.destroy()

    origen, destino = TMP / "origen", TMP / "destino"
    origen.mkdir()
    destino.mkdir()
    movido = origen / "movido.txt"
    movido.write_text("hola")
    (destino / "movido.txt").write_text("hola")     # simula el archivo ya movido
    movido.unlink()
    copiado_origen = origen / "copiado.txt"
    copiado_origen.write_text("original")
    (destino / "copiado.txt").write_text("original")
    historial.registrar("cuarentena", "mover", str(origen), str(destino),
                        [(str(movido), str(destino / "movido.txt"))], "1 duplicado")
    historial.registrar("reunir", "copiar", str(origen), str(destino),
                        [(str(copiado_origen), str(destino / "copiado.txt"))], "1 imagen")
    ventana = VentanaHistorial(app)
    app.update()
    ops = historial.listar()
    check(len(ops) == 2, "el historial lista las dos operaciones")
    op_copiar, op_mover = ops[0], ops[1]          # la más reciente primero
    ventana._deshacer(op_mover)
    check(movido.exists() and not (destino / "movido.txt").exists(),
          "deshacer un «mover» devuelve el archivo a su sitio")
    ventana._deshacer(op_copiar)
    check(copiado_origen.exists() and not (destino / "copiado.txt").exists(),
          "deshacer un «copiar» borra la copia y NO toca el original")
    check(all(o["deshecha"] for o in historial.listar()), "las dos quedan marcadas como deshechas")

    (destino / "otro.txt").write_text("x")
    historial.registrar("cuarentena", "mover", str(origen), str(destino),
                        [(str(origen / "otro.txt"), str(destino / "no_esta.txt"))], "falla")
    avisos_antes = avisos["aviso"]
    ventana._deshacer(historial.listar()[0])
    check(avisos["aviso"] == avisos_antes + 1,
          "si no se puede deshacer, se avisa y la operación sigue sin marcarse")
    ventana.destroy()

    # --------------------------------------- qué hacer con los archivos que no son imágenes
    print("Diálogo de tipos no imagen")
    tipos = {"pdf": ["a.pdf"], "txt": ["b.txt", "c.txt"], "mp3": ["d.mp3"]}
    dlg = VentanaTiposNoImagen(app, tipos)
    app.update()
    seg_pdf, entrada_pdf = dlg._filas["pdf"]
    seg_txt, _ = dlg._filas["txt"]
    seg_pdf.set("Agrupar")
    dlg._toggle_entry("pdf")
    entrada_pdf.delete(0, "end")
    entrada_pdf.insert(0, "Mis documentos")
    seg_txt.set("Mover")
    dlg._toggle_entry("txt")
    dlg._aplicar()
    reglas = dlg.reglas
    check(reglas is not None and reglas.accion("pdf") == AGRUPAR
          and reglas.carpeta("pdf") == "Mis documentos", "«Agrupar» guarda el nombre de carpeta")
    check(reglas is not None and reglas.accion("txt") == MOVER, "«Mover» se recoge")
    check(reglas is not None and reglas.accion("mp3") == DEJAR,
          "lo que no se toca queda en «Dejar»")
    dlg2 = VentanaTiposNoImagen(app, tipos)
    app.update()
    dlg2._cancelar()
    check(dlg2.reglas is None, "cancelar devuelve None (no se hace nada)")

    # ---------------------------------------- desglose por extensión + exportar CSV
    print("Desglose por extensión y CSV")
    datos = TMP / "datos"
    (datos / "a").mkdir(parents=True)
    (datos / "b").mkdir()
    for carpeta in ("a", "b"):
        (datos / carpeta / "doc.txt").write_bytes(b"contenido del documento\n" * 20)
        (datos / carpeta / "foto.jpg").write_bytes(b"pixeles\n" * 50)
    resultado = escanear(str(datos))
    excluidas = []
    desglose = VentanaTipos(app, resultado, excluidas.append)
    app.update()
    desglose._excluir("txt")
    check(excluidas == ["txt"], "«Excluir» avisa de la extensión elegida")
    check("txt" in desglose.title(), "y lo dice en el título de la ventana")
    desglose.destroy()

    exactos = app.exactos
    exactos._resultado = resultado
    informe = TMP / "informe.csv"
    filedialog.asksaveasfilename = lambda *a, **k: str(informe)
    exactos._exportar_csv()
    filas = list(csv.reader(informe.open(encoding="utf-8-sig", newline="")))
    check(len(filas) == 1 + 4 and filas[0][0] == "Grupo_Duplicado",
          "el CSV tiene cabecera y los 4 archivos duplicados")
    filedialog.asksaveasfilename = lambda *a, **k: ""
    exactos._exportar_csv()                          # cancelar: no hace nada ni falla
    filedialog.asksaveasfilename = lambda *a, **k: str(TMP / "no" / "existe" / "i.csv")
    errores_antes = avisos["error"]
    exactos._exportar_csv()
    check(avisos["error"] == errores_antes + 1,
          "si no se puede escribir, se avisa en vez de romperse")

    app.destroy()
    print()
    if fallos:
        print(f"FALLARON {len(fallos)} comprobaciones.")
        sys.exit(1)
    print("HUMO DIÁLOGOS OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
