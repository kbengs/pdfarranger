import os
os.environ["G_ENABLE_DIAGNOSTIC"]="1"
import sys
from pdfarranger import pdfarranger

pdfarranger.PdfArranger().run(sys.argv)
