"""Generates the code guide: 'guia-del-codigo.pdf' (Spanish) and 'code-guide.pdf' (English).

python docs/gen_code_guide.py [es|en|all]
"""

import sys

from _pdf_common import generate
from content import guide_en, guide_es

generate({"es": ("guia-del-codigo.pdf", guide_es), "en": ("code-guide.pdf", guide_en)}, sys.argv)
