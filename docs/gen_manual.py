"""Generates the user manual: 'manual-de-usuario.pdf' (Spanish) and 'user-manual.pdf' (English).

python docs/gen_manual.py [es|en|all]
"""

import sys

from _pdf_common import generate
from content import manual_en, manual_es

generate(
    {"es": ("manual-de-usuario.pdf", manual_es), "en": ("user-manual.pdf", manual_en)}, sys.argv
)
