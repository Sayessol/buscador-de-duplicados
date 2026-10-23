"""
Buscador de archivos duplicados - Windows
-------------------------------------------
Recorre una carpeta (y todas sus subcarpetas) de forma recursiva,
calcula un hash (SHA-256) del CONTENIDO de cada archivo, y genera
un reporte CSV con los grupos de archivos duplicados encontrados.
 
IMPORTANTE: Este script SOLO LEE archivos. No mueve, no renombra,
no borra ni modifica nada. Es 100% seguro de correr.
 
Uso:
    1. Edita la variable CARPETA_A_ESCANEAR más abajo, o corre el
       script y te pedirá la ruta por consola.
    2. Ejecuta: python buscar_duplicados.py
    3. Al terminar, se genera un archivo "duplicados_reporte.csv"
       en la misma carpeta donde está este script.
"""
 
import os
import hashlib
import csv
from collections import defaultdict
 
# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
# Puedes escribir la ruta aquí directamente, por ejemplo:
# CARPETA_A_ESCANEAR = r"D:\MisArchivos"
# Si la dejas vacía (""), el script te la pedirá al ejecutarse.
CARPETA_A_ESCANEAR = ""
 
NOMBRE_REPORTE = "duplicados_reporte.csv"
 
# Tamaño del bloque de lectura para calcular el hash (no cambiar
# a menos que sepas lo que haces; 65536 bytes = 64 KB por bloque)
TAMANO_BLOQUE = 65536
 
 
def calcular_hash(ruta_archivo):
    """Calcula el hash SHA-256 del contenido de un archivo, leyendo
    en bloques para no consumir mucha memoria con archivos grandes."""
    sha256 = hashlib.sha256()
    try:
        with open(ruta_archivo, "rb") as f:
            while True:
                bloque = f.read(TAMANO_BLOQUE)
                if not bloque:
                    break
                sha256.update(bloque)
        return sha256.hexdigest()
    except (PermissionError, OSError) as e:
        print(f"  [AVISO] No se pudo leer: {ruta_archivo} ({e})")
        return None
 
 
def formatear_tamano(bytes_):
    """Convierte bytes a un formato legible (KB, MB, GB)."""
    for unidad in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unidad}"
        bytes_ /= 1024
    return f"{bytes_:.1f} PB"
 
 
def escanear_carpeta(carpeta_raiz):
    """Recorre recursivamente la carpeta y agrupa archivos por hash."""
    archivos_por_hash = defaultdict(list)
    total_archivos = 0
 
    print(f"\nEscaneando: {carpeta_raiz}")
    print("Esto puede tardar dependiendo de cuántos archivos haya...\n")
 
    for carpeta_actual, subcarpetas, archivos in os.walk(carpeta_raiz):
        for nombre_archivo in archivos:
            ruta_completa = os.path.join(carpeta_actual, nombre_archivo)
            total_archivos += 1
 
            if total_archivos % 200 == 0:
                print(f"  ...{total_archivos} archivos revisados hasta ahora")
 
            try:
                tamano = os.path.getsize(ruta_completa)
            except OSError:
                continue
 
            # Optimización: solo calculamos hash si ya hay otro archivo
            # del mismo tamaño en algún momento (esto se filtra después,
            # aquí simplemente guardamos todo agrupado por hash real)
            hash_archivo = calcular_hash(ruta_completa)
            if hash_archivo is None:
                continue
 
            archivos_por_hash[hash_archivo].append((ruta_completa, tamano))
 
    print(f"\nTotal de archivos revisados: {total_archivos}")
    return archivos_por_hash
 
 
def generar_reporte_csv(archivos_por_hash, ruta_reporte):
    """Escribe el CSV solo con los grupos que tienen 2+ archivos (duplicados)."""
    grupos_duplicados = {
        h: lista for h, lista in archivos_por_hash.items() if len(lista) > 1
    }
 
    with open(ruta_reporte, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow([
            "Grupo_Duplicado",
            "Ruta_Completa",
            "Tamano",
            "Tamano_Bytes",
            "Hash_SHA256",
        ])
 
        for numero_grupo, (hash_archivo, lista_archivos) in enumerate(
            grupos_duplicados.items(), start=1
        ):
            for ruta, tamano in lista_archivos:
                escritor.writerow([
                    f"Grupo {numero_grupo}",
                    ruta,
                    formatear_tamano(tamano),
                    tamano,
                    hash_archivo,
                ])
 
    return len(grupos_duplicados)
 
 
def main():
    carpeta = CARPETA_A_ESCANEAR.strip()
    if not carpeta:
        carpeta = input("Escribe la ruta de la carpeta a escanear (ej. D:\\Fotos): ").strip()
 
    if not os.path.isdir(carpeta):
        print(f"\n[ERROR] La ruta '{carpeta}' no existe o no es una carpeta.")
        return
 
    archivos_por_hash = escanear_carpeta(carpeta)
 
    ruta_reporte = os.path.join(os.getcwd(), NOMBRE_REPORTE)
    num_grupos = generar_reporte_csv(archivos_por_hash, ruta_reporte)
 
    print("\n" + "=" * 50)
    print(f"Grupos de duplicados encontrados: {num_grupos}")
    print(f"Reporte guardado en: {ruta_reporte}")
    print("No se movió ni se borró ningún archivo.")
    print("=" * 50)
 
 
if __name__ == "__main__":
    main()
 
