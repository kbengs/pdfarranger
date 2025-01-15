# Copyright (C) 2025 pdfarranger contributors
#
# pdfarranger is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import cairo
import gi
import pikepdf

from math import pi
from gi.repository import Gtk, Gdk, GObject

from .core import PDFRenderer, _img_to_pdf
from .metadata import merge
from .exporter import _set_meta


class ImageExporter:
    def __init__(self, files, pages, metadata, files_out, _quit_flag, config, pdfqueue, exportmode, export_msg, tmp_dir):
        self.files = files
        self.model = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        for page in pages:
            page.zoom = config.image_dpi() / 72  # pdf is 72 dpi
            page.resample = -1
            self.model.append([page])
        self.metadata = metadata
        self.files_out = files_out
        self.pdfqueue = pdfqueue
        self.exportmode = exportmode
        self.export_msg = export_msg
        self.tmp_dir = tmp_dir
        self.rendering_thread = None
        self.all_done = False
        if exportmode in ['SELECTED_TO_PDF_PNG', 'SELECTED_TO_PDF_JPG']:
            self.pdf_out = pikepdf.Pdf.new()

    def start(self):
        self.rendering_thread = PDFRenderer(self.model, self.pdfqueue, [0, len(self.model) - 1] , 1)
        self.rendering_thread.connect('update_thumbnail', self.create_page)
        self.rendering_thread.start()

    def join(self, timeout=None):
        if not self.rendering_thread:
            return
        self.rendering_thread.quit = True
        self.rendering_thread.join(timeout=timeout)
        self.all_done = True

    def is_alive(self):
        return not self.all_done

    def create_page(self, _obj, ref, thumbnail, _zoom, _scale, _is_preview):
        if self.rendering_thread.quit:
            return
        if thumbnail is None:
            # Rendering has ended
            if self.exportmode in ['SELECTED_TO_PDF_PNG', 'SELECTED_TO_PDF_JPG']:
                m = merge(self.metadata, self.files)
                _set_meta(m, [], self.pdf_out)
                self.pdf_out.save(self.files_out[0])
            self.all_done = True
            return
        path = ref.get_path()
        page = self.model[path][0]
        ind = Gtk.TreePath.get_indices(path)[0]

        w = thumbnail.get_width()
        h = thumbnail.get_height()
        w1, h1 = (h, w) if page.angle in [90, 270] else (w, h)

        # Add a white paper
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w1, h1)
        cr = cairo.Context(surface)
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, w1, h1)
        cr.fill()

        if page.angle > 0:
            cr.translate(w1 / 2, h1 / 2)
            cr.rotate(page.angle * pi / 180)
            cr.translate(-w / 2, -h / 2)
        cr.set_source_surface(thumbnail)
        cr.paint()

        ext = 'png' if self.exportmode in ['SELECTED_TO_PNG', 'SELECTED_TO_PDF_PNG'] else 'jpeg'
        pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, w1, h1)
        if self.exportmode in ['SELECTED_TO_PNG', 'SELECTED_TO_JPG']:
            success = pixbuf.savev(filename=self.files_out[ind], type=ext)
        else:
            success, imgbuf = pixbuf.save_to_bufferv(ext)
            if success:
                pdf = _img_to_pdf(imgbuf, tmp_dir=self.tmp_dir, page_size=page.size_in_points())
                src = pikepdf.Pdf.open(pdf)
                self.pdf_out.pages.extend(src.pages)
        if not success:
            self.export_msg.put(["Export failed", Gtk.MessageType.ERROR])
            self.join()

        while Gtk.events_pending():
            Gtk.main_iteration()
