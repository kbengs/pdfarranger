from gi.repository import Gtk, GObject
import cairo
from math import pi



class GWItem(Gtk.Box):
    thumbnail = GObject.Property()
    angle = GObject.Property(type=int)
    position = GObject.Property(type=int)
    def __init__(self, thumbnail=None, angle=0, position=0):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        self.da = Gtk.DrawingArea(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        self.thumbnail = thumbnail
        self.da.set_draw_func(self.draw, None)
        self.append(self.da)
        self.append(Gtk.Label())
        self.angle = angle
        #self.position = position
        self.size = [1, 1]
        self.drag_dest_pos = None

        # evc2 = Gtk.DragSource(actions=Gdk.DragAction.COPY)
        # #evc2.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        # evc2.connect('drag_begin', self.drag_begin)
        # #evc2.connect('drag_end', self.iv_dnd_leave_end)
        # evc2.connect('drag_end', self.drag_end)
        # evc2.connect('prepare', self.prepare)
        # self.add_controller(evc2)
        #
        #evc = Gtk.EventControllerMotion()
        #evc = Gtk.DropTarget()
        #evc.connect('enter', self.focus_true)
        #evc.connect('leave', self.focus_false)
        #evc3.connect('motion', self.motion)
        # evc3.connect('drop', self.drop)
        #self.add_controller(evc)

    def set_drag_pos(self, pos):
        if pos == self.drag_dest_pos:
            return
        self.drag_dest_pos = pos
        self.da.queue_draw()

    def update_thumbnail(self):
        self.da.queue_draw()

    def draw(self, area, c, aw, ah, data):
        if self.thumbnail is None:
            return
        w, h = self.size

        dx = int(.5 + (aw - w) / 2)
        dy = int(.5 + (ah - h) / 2)

        c.translate(dx, dy)

        # Border
        c.set_source_rgb(0, 0, 0)
        c.rectangle(-1, -1, w + 2, h + 2)
        c.fill()

        # White paper
        c.set_source_rgb(1, 1, 1)
        c.rectangle(0, 0, w, h)
        c.fill()

        # Draw markers
        if self.drag_dest_pos == 'BEFORE':
            c.set_source_rgb(0, 0, 0)
            c.set_line_width(3)
            c.move_to(-5, -5)
            c.set_dash([6, 6])
            c.line_to(-5, ah)
            c.stroke()
        elif self.drag_dest_pos == 'AFTER':
            c.set_source_rgb(0, 0, 0)
            c.set_line_width(3)
            c.move_to(w + 5, -5)
            c.set_dash([6, 6])
            c.line_to(w + 5, ah)
            c.stroke()

        (dw0, dh0) = (h, w) if self.angle in [90, 270] else (w, h)
        if self.angle > 0:
            c.translate(w / 2, h / 2)
            c.rotate(self.angle * pi / 180)
            c.translate(-dw0 / 2, -dh0 / 2)
        tw, th = self.thumbnail.get_width(), self.thumbnail.get_height()
        tw, th = (th, tw) if self.angle in [90, 270] else (tw, th)
        c.scale(w / tw, h / th)

        c.set_source_surface(self.thumbnail)
        c.paint()


class GridViewEnhanced(Gtk.GridView):
    def __init__(self, model, selection_model):
        super().__init__()
        self.set_enable_rubberband(True)
        self.multi_selection = selection_model
        self.multi_selection.set_model(model)
        self.set_model(self.multi_selection)
        self.drag_dest_item_old = None
        self.drag_num = None
        self.drag_pos = None

    def get_selected_items(self):
        return self.multi_selection.get_selection()

    def set_drag_dest_item(self, num, pos):
        """Sets the drop marker at drag-and-drop"""
        gwitem_old = self.get_gwitem(self.drag_dest_item_old)
        if gwitem_old is not None and num != self.drag_dest_item_old:
            gwitem_old.set_drag_pos(None)

        gwitem = self.get_gwitem(num)
        if gwitem is not None:
            gwitem.set_drag_pos(pos)

        self.drag_dest_item_old = num
        self.update_geometry()
        self.drag_num = num
        self.drag_pos = pos

    def unset_all_drag_dest_item(self):
        """Remove any drop marker"""
        model = self.get_model()
        for num in range(len(model)):
            gwitem = self.get_gwitem(num)
            if gwitem is not None:
                gwitem.set_drag_pos(None)

    def get_num_at_pos(self, x, y):
        """Get the item number at coordinate x, y"""
        da = self.pick(x, y, Gtk.PickFlags.DEFAULT)
        if da is None:
            return None, None
        box = da.get_parent()
        if isinstance(box, GWItem):
            listitemwidget = box.get_parent()
            a = listitemwidget.get_allocation()

            x = x - a.x
            if x < (a.width + 1) * 0.4:
                area = 'BEFORE'
            elif x > (a.width + 1) * 0.6:
                area = 'AFTER'
            elif x >= (a.width + 1) * 0.4 and x <= (a.width + 1) * 0.6:
                area = 'CENTER'
            else:
                area = None

            return box.position, area
        else:
            return None, None

    def scroll_to_num(self, num):
        self.scroll_to(num, Gtk.ListScrollFlags.NONE, None)
        model = self.get_model()
        num = min(num, len(model) - 1)
        listitemwidget = self.get_listitemwidget(num)
        alloc = listitemwidget.get_allocation()
        sw = self.get_parent()
        sw_vadj = sw.get_vadjustment()
        sw_vadj.set_value(sw_vadj.get_value() + alloc.y)

    def get_listitemwidget(self, num):
        """Get listitemwidget at num. If not mapped return None"""
        listitemwidget = self.get_first_child()
        while listitemwidget is not None:
            gwitem = listitemwidget.get_first_child()
            if gwitem.position == num:
                break
            listitemwidget = listitemwidget.get_next_sibling()
        return listitemwidget

    def get_gwitem(self, num):
        """Get the widget at num. If not mapped return None"""
        listitemwidget = self.get_listitemwidget(num)
        if listitemwidget is None:
            return None
        gwitem = listitemwidget.get_first_child()
        return gwitem

    def get_drawingarea(self, num):
        """Get drawingarea in widget at num. If not mapped return None"""
        gwitem = self.get_gwitem(num)
        da = gwitem.get_first_child()
        return da

    def select_num(self, num):
        listitemwidget = self.get_listitemwidget(num)

        listitemwidget.grab_focus()
        #listitemwidget.set_state_flags(Gtk.StateFlags.SELECTED, clear=False)


    def get_visible_range(self):
        """Get range of items visible in window.

        A item is considered visible if more than 50% of item is visible.
        """
        listitemwidget = self.get_first_child()
        while not listitemwidget.get_mapped():
            next_listltemwidget = listitemwidget.get_next_sibling()
            if next_listltemwidget is None:
                break
            listitemwidget = next_listltemwidget
        gwitem = listitemwidget.get_first_child()
        first_visible = gwitem.position

        listitemwidget = self.get_last_child()
        while not listitemwidget.get_mapped():
            prev_listltemwidget = listitemwidget.get_prev_sibling()
            if prev_listltemwidget is None:
                break
            listitemwidget = prev_listltemwidget
        gwitem = listitemwidget.get_first_child()
        if gwitem is None:
            last_visible = first_visible
        else:
            last_visible = gwitem.position

        return first_visible, last_visible

    def update_geometry(self):
        """Set gridview item size and number of columns"""
        model = self.get_model()
        if len(model) == 0:
            return
        listitemwidget = self.get_first_child()
        while listitemwidget is not None:
            gwitem = listitemwidget.get_first_child()
            page = model[gwitem.position]
            gwitem.size  = page.size_in_pixel()
            drawingarea = gwitem.get_first_child()
            drawingarea.set_content_width(gwitem.size[0] + 20)
            drawingarea.set_content_height(gwitem.size[1] + 10)
            listitemwidget = listitemwidget.get_next_sibling()

        item_width = max(page.width_in_pixel() for page in model)
        sw = self.get_parent()
        iw_width = sw.get_allocation().width
        margins = 0
        padded_cell_width = max(80, item_width + 2 + 2 * 20)
        col_num = int((iw_width - margins) / padded_cell_width)
        self.set_max_columns(col_num)
        self.set_min_columns(col_num)
