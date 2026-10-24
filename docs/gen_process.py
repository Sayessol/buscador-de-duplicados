"""Generates the creation process: 'proceso-de-creacion.pdf' (Spanish) and 'creation-process.pdf'.

    python docs/gen_process.py [es|en|all]
"""

import sys

from _pdf_common import generate
from content import process_en, process_es

generate({"es": ("proceso-de-creacion.pdf", process_es),
          "en": ("creation-process.pdf", process_en)}, sys.argv)
