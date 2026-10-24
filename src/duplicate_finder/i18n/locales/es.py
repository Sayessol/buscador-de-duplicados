"""Textos en español (de España). Mismas claves y marcadores que en.py."""

MESSAGES = {
    # breakdown
    "breakdown.exclude": "Excluir",
    "breakdown.intro": (
        "Ordenado por espacio ocupado. «Excluir» añade la extensión al filtro; "
        "después hay que volver a escanear."
    ),
    "breakdown.row_detail": "    {count} archivos   ·   {size}",
    "breakdown.title": "Tipos de archivo entre los duplicados",
    "breakdown.title_added": "Tipos de archivo  ·  .{ext} añadido al filtro",
    # category
    "category.archives": "Comprimidos",
    "category.audio": "Audio",
    "category.documents": "Documentos",
    "category.images": "Imágenes",
    "category.video": "Vídeo",
    # common
    "common.all_files": "Todos los archivos",
    "common.app_name": "Buscador de duplicados",
    "common.cancel": "Cancelar",
    "common.cancelling": "Cancelando…",
    "common.choose": "Elegir",
    "common.close": "Cerrar",
    "common.confirm": "Confirmar",
    "common.confirm_title": "Confirmar movimiento a cuarentena",
    "common.continue_question": "\n\n¿Continuar?",
    "common.copying": "Copiando",
    "common.date_format": "%d/%m/%Y %H:%M",
    "common.done": "Listo.",
    "common.done_title": "Hecho",
    "common.error_detail": "{name}: {datum}",
    "common.file_gone": "el archivo ya no está en su sitio",
    "common.folder_placeholder": "Ej.  D:\\Fotos",
    "common.invalid_folder_title": "Carpeta no válida",
    "common.invalid_quarantine_title": "Carpeta de cuarentena no válida",
    "common.log_note": "\n\nRegistro: {log_path}",
    "common.move_error_title": "Error al mover",
    "common.move_quarantine": "Mover a cuarentena",
    "common.moving": "Moviendo",
    "common.no_extension": "(sin extensión)",
    "common.not_a_folder": "No es una carpeta: {root_folder}",
    "common.pick_quarantine": "Elige (o crea) la carpeta de cuarentena",
    "common.scan": "Escanear",
    "common.tile_recoverable": "Espacio recuperable",
    "common.warning": "Atención",
    # csv
    "csv.action": "Accion",
    "csv.date": "Fecha",
    "csv.destination": "Destino",
    "csv.duplicate_group": "Grupo_Duplicado",
    "csv.error": "Error",
    "csv.full_path": "Ruta_Completa",
    "csv.group": "Grupo",
    "csv.hash": "Hash",
    "csv.scanned_folder": "Carpeta_Escaneada",
    "csv.size": "Tamano",
    "csv.size_bytes": "Tamano_Bytes",
    "csv.source": "Origen",
    "csv.source_root": "Origen_Raiz",
    "csv.status": "Estado",
    "csv.status_done": "hecho",
    "csv.status_error": "ERROR",
    "csv.status_moved": "movido",
    # exact
    "exact.all_kinds_placeholder": "vacío = se buscan todos los tipos",
    "exact.cancelled": "Escaneo cancelado.",
    "exact.cancelled_detail": "Pulsa «Escanear» para intentarlo de nuevo.",
    "exact.cancelled_title": "Escaneo cancelado",
    "exact.categories_hint": (
        "Marca una categoría o escribe extensiones a mano. Si lo dejas vacío "
        "se buscan duplicados de cualquier tipo."
    ),
    "exact.choose_folder_header": "Elige la carpeta que quieres revisar",
    "exact.choose_main": "Elegir la principal",
    "exact.clear_all": "Quitar todo",
    "exact.click_to_enlarge": "Clic para ver la imagen en grande",
    "exact.confirm_msg": (
        "Se van a MOVER {n} archivo(s) ({frees}) "
        "a:\n\n{quarantine_folder}\n\nLos originales que has marcado para "
        "conservar NO se tocan. No se borra nada: todo queda en la cuarentena "
        "para que lo revises y lo borres tú manualmente cuando "
        "quieras.\n\n¿Mover ahora?"
    ),
    "exact.defaults": "Valores por defecto",
    "exact.empty_detail": (
        "Elige una carpeta arriba y pulsa «Escanear». Los grupos de archivos "
        "duplicados aparecerán aquí."
    ),
    "exact.empty_title": "Todavía no hay resultados",
    "exact.error_msg": "Ha ocurrido un problema:\n\n{name}: {e}",
    "exact.error_title": "Error durante el escaneo",
    "exact.excluded_suffix": "  ·  {total_excluded} ignorados por filtro",
    "exact.export_csv": "Exportar CSV",
    "exact.extensions": "Extensiones:",
    "exact.failed": "El escaneo ha fallado.",
    "exact.failed_note": "\n{failed} no se han podido mover (consulta el CSV de registro).",
    "exact.folders": "Carpetas:",
    "exact.hint_all_resolved": (
        "Todos los grupos tienen una sola copia marcada para conservar. Ya "
        "puedes mover a cuarentena."
    ),
    "exact.hint_main_kept": (
        "La app conservará la copia principal de cada grupo. Doble clic en una "
        "fila para conservar otra. Cuando quieras, pulsa «Mover a cuarentena»."
    ),
    "exact.hint_unresolved": (
        "{count} grupo(s) sin resolver (resaltados en la tabla). Marca una "
        "sola copia para conservar en cada uno. El botón «Mover a cuarentena» "
        "está bloqueado."
    ),
    "exact.ignore_also": "Ignorar además:",
    "exact.ignore_empty": "Ignorar archivos de 0 bytes",
    "exact.invalid_folder_msg": "La ruta no existe o no es una carpeta:\n\n{folder}",
    "exact.keep_header": "Decide qué copia conservar en cada grupo",
    "exact.missing_folder_msg": "Elige primero una carpeta para escanear.",
    "exact.missing_folder_title": "Falta la carpeta",
    "exact.move_done": "Movimiento a cuarentena terminado.",
    "exact.move_failed": "El movimiento ha fallado.",
    "exact.moved_summary": "Se han movido {moved} archivo(s) ({size}).",
    "exact.moved_title": "Archivos movidos a cuarentena",
    "exact.moved_totals": (
        "{moved} archivo(s) movidos a cuarentena. Vuelve a escanear si quieres continuar."
    ),
    "exact.moving": "Moviendo a cuarentena…",
    "exact.names": "Nombres:",
    "exact.need_preferred_msg": "Escribe o elige antes una carpeta preferida.",
    "exact.need_preferred_title": "Falta la carpeta preferida",
    "exact.no_preview": "(sin vista previa)",
    "exact.no_such_folder_msg": (
        "La carpeta preferida no existe ahora "
        "mismo:\n\n{preferred_folder}\n\n¿Quieres aplicar la regla igualmente? "
        "(los grupos sin coincidencia quedarán sin decidir)"
    ),
    "exact.no_such_folder_title": "La carpeta no existe",
    "exact.none_found": "No se han encontrado duplicados.",
    "exact.none_found_detail": "Se han revisado {total_files} archivos y todos son únicos.",
    "exact.none_found_title": "No se han encontrado duplicados",
    "exact.not_scanned": "Sin escanear todavía.",
    "exact.only_kinds": "Buscar solo estos tipos de archivo:",
    "exact.open_quarantine_question": "\n\n¿Quieres abrir la carpeta de cuarentena?",
    "exact.options_toggle": "Opciones de escaneo (filtrar por tipo de archivo)",
    "exact.pick_preferred_folder": "Elige la carpeta preferida",
    "exact.pick_scan_folder": "Elige la carpeta a escanear",
    "exact.preferred_folder": "Carpeta preferida:",
    "exact.preferred_placeholder": (
        "Las copias dentro de esta carpeta se conservan.  Ej.  D:\\Fotos\\Organizado"
    ),
    "exact.preparing": "Preparando el escaneo…",
    "exact.preview_hint": "Selecciona un archivo\npara ver la vista previa",
    "exact.report_saved_msg": "Se han guardado {n} grupos de duplicados en:\n\n{path}",
    "exact.report_saved_title": "Informe guardado",
    "exact.rule_applied": "Regla aplicada: {resolved} grupo(s) resueltos automáticamente.",
    "exact.rule_by_folder": "Regla por carpeta",
    "exact.rule_no_match": (
        "\n{no_match} grupo(s) no tienen ninguna copia dentro de la carpeta "
        "preferida: han quedado resaltados para que elijas manualmente (un "
        "clic sobre la copia que quieres conservar, o doble clic para "
        "conservar solo esa)."
    ),
    "exact.rule_title": "Regla automática",
    "exact.save_failed_msg": "No se pudo escribir el archivo:\n\n{e}",
    "exact.save_failed_title": "No se pudo guardar",
    "exact.save_report_title": "Guardar informe CSV",
    "exact.scan_again": " Vuelve a escanear para continuar.",
    "exact.scanning": "Escaneando…",
    "exact.searching_detail": "Buscando archivos duplicados.",
    "exact.separate_hint": "Separa los valores con espacios o comas.",
    "exact.tile_files": "Archivos duplicados",
    "exact.tile_groups": "Grupos de duplicados",
    "exact.tile_to_move": "Archivos a mover",
    "exact.totals": (
        "{total_groups} grupos · {total_files_duplicates} archivos duplicados{excl_text}"
    ),
    "exact.totals_none": "{total_files} archivos revisados{excl_text} · 0 duplicados.",
    "exact.unreadable": "  {count} archivo(s) no se pudieron leer.",
    "exact.view_kinds": "Ver tipos de archivo",
    # gather
    "gather.action_copy": "Copiar",
    "gather.action_label": "Acción:",
    "gather.action_move": "Mover",
    "gather.and_more": "… y {hidden} más (se reunirán todas las marcadas igualmente).",
    "gather.confirm_and_others": " y {n_others} archivo(s) más",
    "gather.confirm_files": "Se van a {upper} {count} imagen(es)",
    "gather.confirm_tail": " a:\n\n{destination}\n\nSe mantienen las subcarpetas. ¿Continuar?",
    "gather.confirm_whole_folder": (
        "Se va a {upper} la carpeta «{name}» ENTERA (con todo lo que hay "
        "dentro) a:\n\n{destination}\\{name}\\\n\n¿Continuar?"
    ),
    "gather.description_files": "{count} imágenes",
    "gather.description_folder": "carpeta «{name}» entera",
    "gather.destination_placeholder": "Carpeta común de destino",
    "gather.done_summary": "Listo: {count} archivo(s) {verb}(s).",
    "gather.empty_detail": (
        "Elige una carpeta y pulsa «Buscar imágenes». Aparecerán aquí para que "
        "elijas cuáles reunir."
    ),
    "gather.error_detail": "{name}: {e}",
    "gather.error_title": "Error al reunir",
    "gather.failed": "La operación ha fallado.",
    "gather.failed_suffix": "  {count} con error.",
    "gather.find_images": "Buscar imágenes",
    "gather.first_level_suffix": " en el primer nivel",
    "gather.folder_placeholder": "Carpeta a revisar.  Ej.  D:\\Fotos",
    "gather.folder_progress": "{verb} la carpeta «{name}»…",
    "gather.gather_here": "Reunir aquí",
    "gather.header": "Reúne todas las imágenes en una carpeta",
    "gather.infinitive_copy": "copiar",
    "gather.infinitive_move": "mover",
    "gather.intro": (
        "Junta en un solo sitio las fotos que tengas repartidas por una carpeta y sus subcarpetas."
    ),
    "gather.invalid_destination_title": "Destino no válido",
    "gather.invalid_folder_msg": "Elige una carpeta para revisar.",
    "gather.missing_destination_msg": "Elige la carpeta común de destino.",
    "gather.missing_destination_title": "Falta el destino",
    "gather.no_images_detail": "En esa carpeta no hay archivos de imagen",
    "gather.no_images_title": "No se han encontrado imágenes",
    "gather.not_searched_title": "Sin buscar todavía",
    "gather.open_destination_question": "\n\n¿Abrir la carpeta de destino?",
    "gather.past_copy": "copiado",
    "gather.past_move": "movido",
    "gather.pick_destination": "Elige (o crea) la carpeta de destino",
    "gather.pick_folder": "Elige la carpeta a revisar",
    "gather.read_error_title": "Error al leer la carpeta",
    "gather.result_detail": "{count} archivo(s) {verb}(s) a:\n\n{destination}",
    "gather.result_title": "{count} archivo(s) {verb}(s)",
    "gather.scope_all": "Todas las subcarpetas",
    "gather.scope_first": "Solo el primer nivel",
    "gather.starting": "Empezando…",
    "gather.strategy_files": "Por archivos",
    "gather.strategy_folder": "Carpeta entera",
    "gather.strategy_label": "Estrategia:",
    "gather.tile_found": "Imágenes encontradas",
    "gather.tile_marked": "Marcadas para reunir",
    "gather.tile_others": "Otros archivos",
    "gather.totals": "{n} imagen(es) marcadas · {others} archivos que no son imágenes",
    "gather.totals_done": "{count} archivo(s) {verb}(s) a {destination}.",
    "gather.undo_hint": (
        "Puedes deshacerlo desde «Historial» (arriba, en modo Avanzada). "
        "Vuelve a buscar si quieres continuar."
    ),
    # history
    "history.already_undone": "esta operación ya se deshizo",
    "history.gone_from_destination": "ya no está en el destino",
    "history.op_not_found": "operación no encontrada",
    "history.original_path_taken": "ya hay algo en la ruta original",
    "history.description_exact": "{count} duplicados exactos",
    "history.description_similar": "{count} fotos parecidas",
    # history_ui
    "history_ui.confirm_delete_copies": (
        "Se van a BORRAR {n} archivo(s) copiados en:\n\n{destination}\n\nSon "
        "las copias que hizo la app. Los originales no se tocan. Esta acción "
        "no se puede deshacer.\n\n¿Continuar?"
    ),
    "history_ui.confirm_return": (
        "Se van a devolver {n} archivo(s) a su ubicación original (desde "
        "{destination}).\n\n¿Continuar?"
    ),
    "history_ui.empty": "Todavía no hay operaciones registradas.",
    "history_ui.failure_line": "· {name}: {m}",
    "history_ui.intro": (
        "Cada operación se puede deshacer. «Mover» devuelve los archivos a su "
        "sitio; «copiar» borra las copias del destino."
    ),
    "history_ui.item_title": "·  {n} archivo(s) {verb}",
    "history_ui.kind_gather": "Reunir imágenes",
    "history_ui.kind_gather_folder": "Reunir (carpeta entera)",
    "history_ui.refresh": "Actualizar",
    "history_ui.title": "Historial de operaciones",
    "history_ui.undo": "Deshacer",
    "history_ui.undo_done": "Operación deshecha: {reverted} archivo(s).",
    "history_ui.undo_title": "Deshacer operación",
    "history_ui.undo_warnings_msg": (
        "Revertidos: {reverted}.\nNo se pudieron revertir {count}:\n\n{detail}"
    ),
    "history_ui.undo_warnings_title": "Deshacer con avisos",
    "history_ui.undone": "{OK} deshecha",
    "history_ui.verb_copied": "copiados",
    "history_ui.verb_moved": "movidos",
    # kinds
    "kinds.apply": "Aplicar",
    "kinds.folder_name_placeholder": "nombre carpeta",
    "kinds.group": "Agrupar",
    "kinds.intro": (
        "En esas carpetas también hay archivos que no son imágenes. Elige qué hacer con cada tipo:"
    ),
    "kinds.leave": "Dejar",
    "kinds.move": "Mover",
    "kinds.title": "Archivos que no son imágenes",
    # main
    "main.error_msg": (
        "Ha ocurrido un error inesperado ({name}: {val}).\n\n{where}\n\nPuedes "
        "seguir usando la aplicación; si el fallo se repite, cierra y vuelve a "
        "abrirla. Tus archivos no se han tocado."
    ),
    "main.error_title": "Error inesperado",
    "main.history": "Historial",
    "main.language_changed_msg": "El idioma cambiará la próxima vez que abras la aplicación.",
    "main.language_changed_title": "Idioma",
    "main.language_label": "Idioma:",
    "main.log_failed": "No se ha podido guardar el registro.",
    "main.log_saved": "Se ha anotado en el registro:\n{path}",
    "main.mode_advanced": "Avanzada",
    "main.mode_simple": "Sencilla",
    "main.tab_exact": "Duplicados exactos",
    "main.tab_gather": "Reunir imágenes",
    "main.tab_similar": "Fotos parecidas",
    "main.tagline": (
        "Encuentra archivos repetidos y muévelos a cuarentena. Nunca se borran tus originales."
    ),
    "main.theme_auto": "Automático",
    "main.theme_dark": "Oscuro",
    "main.theme_label": "Tema:",
    "main.theme_light": "Claro",
    "main.view_label": "Vista:",
    "main.window_title": "Buscador de duplicados {version}",
    # moves
    "moves.inside_source": (
        "El destino está dentro de la carpeta de origen. Elige una carpeta fuera de ella."
    ),
    "moves.progress": "{verb} {i}/{total}: {basename}",
    "moves.same_folder": "El destino no puede ser la misma carpeta que el origen.",
    "moves.source_inside_destination": (
        "Atención: la carpeta de origen está dentro del destino. Se puede "
        "continuar, pero revisa que sea lo que quieres."
    ),
    # perceptual
    "perceptual.analyzing": "Analizando imágenes… ({i}/{total})",
    "perceptual.finished": "Comparación terminada.",
    # quarantine
    "quarantine.inside_scanned": (
        "La carpeta de cuarentena está dentro de la carpeta escaneada. Elige "
        "una carpeta fuera de ella."
    ),
    "quarantine.progress": "Moviendo {i}/{total}: {basename}",
    "quarantine.same_as_scanned": (
        "La carpeta de cuarentena no puede ser la misma que la carpeta escaneada."
    ),
    "quarantine.scanned_inside_quarantine": (
        "Atención: la carpeta escaneada está dentro de la carpeta de "
        "cuarentena. Se puede continuar, pero revisa que sea lo que quieres."
    ),
    "quarantine.unresolved_groups": (
        "Hay grupos sin resolver: cada grupo debe tener exactamente una copia "
        "marcada como conservar antes de mover."
    ),
    # report
    "report.group_label": "Grupo {number}",
    # scan
    "scan.finished": "Escaneo terminado.",
    "scan.step_hashes": "Paso 2/2: calculando hashes... ({processed}/{total_candidates})",
    "scan.step_sizes": "Paso 1/2: revisando tamaños... ({total_files} archivos)",
    "scan.step_verifying": (
        "Paso 2/2: verificando archivos completos... ({full_processed}/{total_finalists})"
    ),
    # similar
    "similar.analyze": "Analizar",
    "similar.analyzing": "Analizando…",
    "similar.best_quality": "mejor calidad",
    "similar.cancelled": "Análisis cancelado.",
    "similar.cancelled_detail": "Pulsa «Analizar» para intentarlo de nuevo.",
    "similar.cancelled_title": "Análisis cancelado",
    "similar.comparing_detail": "Comparando las fotos entre sí.",
    "similar.confirm_msg": (
        "Se van a MOVER {n} foto(s) ({frees}) a:\n\n{destination}\n\nLas fotos "
        "marcadas para conservar NO se tocan. No se borra nada.\n\n¿Mover "
        "ahora?"
    ),
    "similar.empty_detail": (
        "Elige una carpeta con fotos y pulsa «Analizar». Los grupos de fotos "
        "parecidas aparecerán aquí, con miniatura de cada una."
    ),
    "similar.error_detail": "{name}: {e}",
    "similar.error_title": "Error durante el análisis",
    "similar.failed": "El análisis ha fallado.",
    "similar.finding_images": "Buscando imágenes…",
    "similar.finished": "Análisis terminado.{extra}",
    "similar.folder_placeholder": "Carpeta con fotos.  Ej.  D:\\Fotos",
    "similar.group_title": "Grupo {number}   ·   {count} fotos parecidas   ·   liberas {size}",
    "similar.header": "Busca fotos parecidas (no idénticas)",
    "similar.intro": (
        "Encuentra la misma foto guardada varias veces: recomprimida, en menor "
        "resolución o con un filtro de color. No detecta recortes ni "
        "rotaciones."
    ),
    "similar.invalid_folder_msg": "Elige una carpeta con fotos para analizar.",
    "similar.keep_this": "Conservar esta",
    "similar.kept": "Se conserva",
    "similar.loading_thumbnails": "Cargando miniaturas… ({processed_count}/{total})",
    "similar.moved_detail": "Se han movido {count} fotos. Vuelve a analizar para continuar.",
    "similar.moved_summary": "Se han movido {count} fotos.",
    "similar.moved_title": "Fotos movidas a cuarentena",
    "similar.moved_totals": (
        "{count} foto(s) movidas a cuarentena. Vuelve a analizar si quieres continuar."
    ),
    "similar.next": "Siguiente  ›",
    "similar.no_preview": "(sin\nvista previa)",
    "similar.none_found": "No se han encontrado fotos parecidas.",
    "similar.none_found_detail": (
        "Se han comparado {total_images} imágenes. Prueba a subir la sensibilidad si esperabas más."
    ),
    "similar.none_found_title": "No se han encontrado fotos parecidas",
    "similar.normal": "normal",
    "similar.not_analyzed": "Sin analizar todavía.",
    "similar.not_analyzed_title": "Sin analizar todavía",
    "similar.open_quarantine_question": "\n\n¿Abrir la carpeta de cuarentena?",
    "similar.page_label": "Página {page} de {pages}  ·  grupos {first}–{end} de {total}",
    "similar.pick_folder": "Elige la carpeta con fotos",
    "similar.previous": "‹  Anterior",
    "similar.ready": "Listo: se moverán {to_move} fotos ({size}).",
    "similar.sensitivity": "Sensibilidad:",
    "similar.sensitivity_label": "  ({label})",
    "similar.similarity": "{percent:.0f}% parecida",
    "similar.strict": "estricta",
    "similar.tile_groups": "Grupos de parecidas",
    "similar.tile_photos": "Fotos en grupos",
    "similar.tile_to_move": "Fotos a mover",
    "similar.tolerant": "tolerante",
    "similar.too_many_kept": (
        "{count} grupo(s) con más de una foto marcada para conservar. Deja solo una en cada grupo."
    ),
    "similar.totals_none": "{total_images} imágenes analizadas{extra} · 0 grupos.",
    "similar.unreadable_suffix": "  ·  {count} imagen(es) ilegibles",
    "similar.very_strict": "muy estricta",
    "similar.very_tolerant": "muy tolerante",
    # table
    "table.col_decision": "Decisión",
    "table.col_group": "Grupo / Archivo",
    "table.col_size": "Tamaño",
    "table.decision_keep": "✔ conservar",
    "table.decision_move": "→ mover",
    "table.group_title": "Grupo {number}  ·  {count} copias",
    "table.reclaim": "libera {size}",
    "table.state_choose": "elige cuál conservar",
    "table.state_ready": "listo",
    # thumbs
    "thumbs.no_extension": "sin ext.",
    # viewer
    "viewer.cannot_show": "No se puede mostrar esta imagen.",
    "viewer.fit": "Ajustar",
}
