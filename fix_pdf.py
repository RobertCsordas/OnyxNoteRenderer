#!/usr/bin/env python3

import fitz
import numpy as np
from onyx_render import smoothen
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) not in [2,3]:
        print("Usage: %s <in pdf file> <optional: output pdf file>" % sys.argv[0])
        sys.exit(-1)

    in_file = sys.argv[1]
    save_to = sys.argv[2] if len(sys.argv)>2 else None

    doc = fitz.open(in_file)

    for page in doc:
        annot = page.firstAnnot
        annots = []

        while annot is not None:
            if annot.type[0]==fitz.ANNOT_POLYLINE:
                annots.append(annot)
            annot = annot.next

        for annot in annots:
            vert = smoothen(np.asfarray(annot.vertices),10, 1).tolist()

            new_annot = page.addInkAnnot([vert])
            new_annot.setColors(annot.colors)
            new_annot.setFlags(annot.flags)
            # new_annot.setLineEnds(*annot.lineEnds)
            new_annot.setInfo(annot.info)
            new_annot.setOpacity(annot.opacity)
            new_annot.setRect(annot.rect)
            new_annot.setBorder(annot.border)
            new_annot.update()

            page.deleteAnnot(annot)

    if save_to is None:
        doc.save(in_file+"_fix_pdf", garbage=3, clean=True, deflate=True)
        doc.close()
        os.remove(in_file)
        os.rename(in_file+"_fix_pdf", in_file)
    else:
        doc.save(save_to, garbage=3, clean=True, deflate=True)
