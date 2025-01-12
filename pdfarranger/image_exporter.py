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
    def __init__(self, files, pages, metadata, files_out, _quit_flag, config, pdfqueue, exportmode, export_msg):
        self.files = files
        self.model = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        for page in pages:
            page.zoom = config.image_dpi() / 72  # pdf is 72 dpi
            self.model.append([page])
        self.metadata = metadata
        self.files_out = files_out
        self.dpi = config.image_dpi()
        self.pdfqueue = pdfqueue
        self.exportmode = exportmode
        self.export_msg = export_msg
        self.rendering_thread = None
        self.all_done = False

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
            self.all_done = True
            return
        path = ref.get_path()
        page = self.model[path][0]

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

        pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, w1, h1)
        if self.exportmode in ['SELECTED_TO_PNG', 'SELECTED_TO_JPG']:
            self.write_to_image(path, pixbuf)

    def write_to_image(self, path, pixbuf):
        ind = Gtk.TreePath.get_indices(path)[0]
        filename = self.files_out[ind]
        ext = 'png' if self.exportmode == 'SELECTED_TO_PNG' else 'jpeg'
        success = pixbuf.savev(filename=filename, type=ext)
        if not success:
            self.exception_handler()

    def exception_handler(self):
        self.export_msg.put(["Exporting failed", Gtk.MessageType.ERROR])
        self.join()
