import bpy

# updater ops import, all setup in this file
from . import addon_updater_ops

def category_factory(lib, category, closed=True):
    libname = [t for t in bpy.types.__dir__() if t.startswith("CATEGORY_PT_chocofur_c{}_Panel".format(lib.id))]
    # if not hasattr(bpy.types, libname):
    if not libname:
        libname = "CATEGORY_PT_chocofur_c{}_Panel_{}".format(lib.id, ''.join(random.choice('0123456789ABCDEFGHIJKLMNOPRSTUWXYZ') for i in range(4)))
        bpy.utils.register_class(type(libname, (bpy.types.Panel,), {
            "bl_label": lib.name,
            "bl_space_type": 'VIEW_3D',
            "bl_region_type": 'UI',
            "bl_category": "Chocofur Model Manager",
            "bl_options": {'DEFAULT_CLOSED'} if closed else set(),
            "draw": lambda self, context: None,
        }))
    else:
        libname = libname[0]

    def draw_func(self, context):
        category_prev = getattr(context.scene.chocofur_model_manager, "c{}_{}_previews".format(lib.id, category))
        layout = self.layout

        ############## Category Panel ##############
        box = layout.box()
        ####### Drop Down Menu
        row = box.row()
        row.prop(context.scene.chocofur_model_manager, "c{}_{}_category".format(lib.id, category), text="")
        ####### Previews
        row = box.row()
        row.scale_y = 1.5
        row.template_icon_view(context.scene.chocofur_model_manager, "c{}_{}_previews".format(lib.id, category), show_labels=True)
        ####### Model Name
        row = box.row()
        row.alignment = 'CENTER'
        row.scale_y = 0.5
        row.label(text=category_prev.split('.jpg')[0])
        ####### Add Button
        row = box.row()
        op = row.operator("chocofur.add", text="Add Asset")
        op.object_type=category
        op.libpath=lib.path
        op.libid=lib.id
        
    return type("CATEGORY_PT_chocofur_c{}_{}".format(lib.id, category), (bpy.types.Panel,), {
        "bl_label": category,
        "bl_parent_id": libname,
        "bl_space_type": 'VIEW_3D',
        "bl_region_type": 'UI',
        "bl_category": "Chocofur Model Manager",
        "bl_options":{'DEFAULT_CLOSED'},
        "draw": draw_func,
        "libid": lib.id,
    })
        
#################################################################
############################ Toolbar ############################
#################################################################
def options_panel_factory():
    def draw_func(self, context):
        layout = self.layout
        ############## Library Panel ##############
        box = layout.box()
        row = box.row()
        
        ############## Import Options ##############
        box.label(text="Model Import Location:")
        row = box.row()        
        row.prop(context.window_manager.chocofur_model_manager, "append_location", expand=True)
        
        box.label(text="Model Import Method:")
        row = box.row()        
        row.prop(context.window_manager.chocofur_model_manager, "import_mode", expand=True)
        
        addon_updater_ops.update_notice_box_ui(self, context)
        
    return type("CATEGORY_PT_chocofur_OptionsPanel_{}".format(''.join(random.choice('0123456789ABCDEFGHIJKLMNOPRSTUWXYZ') for i in range(4))), (bpy.types.Panel,), {
        "bl_label": "Chocofur Model Manager",
        "bl_space_type": 'VIEW_3D',
        "bl_region_type": 'UI',
        "bl_category": "Chocofur Model Manager",
        "bl_options":{'DEFAULT_CLOSED'},
        "draw": draw_func,
    })

############## Preferences ##############

# autoupdater preferences
from . controller import get_default_libpath
import random

def refresh_categories(self, context):
    try:
        bpy.ops.chocofur.refresh_categories()
        refresh_ui()
    except AttributeError as e:
        # context is not yet defined
        pass

    return None

def refresh_ui(self=None, context=None):
    for name in [n for n in bpy.types.__dir__() if 'CATEGORY_PT_chocofur_' in n]:
        bpy.utils.unregister_class(getattr(bpy.types, name))

    bpy.utils.register_class(options_panel_factory())

    from . controller import list_categories

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    for i, lib in enumerate(addon_prefs.library_collection):
        for d in list_categories(lib):
            bpy.utils.register_class(category_factory(lib, d, closed= i !=0 ))
    return None

class CHOCOFUR_OT_ItemDown(bpy.types.Operator):
    '''Move library entry down'''
    bl_idname = "chocofur.library_item_down"
    bl_label = "Down"
    bl_options = {"INTERNAL"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        lib = addon_prefs.library_collection
        if self.index < len(lib)-1:
            lib.move(self.index, self.index+1)
            refresh_ui(self, context)
               
        return{'FINISHED'}

class CHOCOFUR_OT_ItemUp(bpy.types.Operator):
    '''Move library entry up'''
    bl_idname = "chocofur.library_item_up"
    bl_label = "Up"
    bl_options = {"INTERNAL"}

    index: bpy.props.IntProperty()

    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        lib = addon_prefs.library_collection
        if self.index > 0:
            lib.move(self.index-1, self.index)
            refresh_ui(self, context)
               
        return{'FINISHED'}

class LibraryItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Model Library", update = refresh_ui)
    path: bpy.props.StringProperty(name="Path", subtype = 'DIR_PATH', update = refresh_categories)
    id: bpy.props.StringProperty()

@addon_updater_ops.make_annotations
class ChocofurManagerPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    library_collection = bpy.props.CollectionProperty(type=LibraryItem)
   
    # Addon updater preferences.

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)

    updater_interval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)
    
    def draw(self, context):
        layout = self.layout
        row = layout.split(factor=.75, align=False)
        
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        row.label(text="Library paths:")
        
        for i, lib in enumerate(addon_prefs.library_collection):
            col = layout.column()
            row = col.split(factor=.35, align=True)
            row.prop(lib, "name")
            sub = row.row()
            sub = sub.split(factor=.75, align=True)
            sub.prop(lib, "path")
            # sub = sub.split(factor=.5, align=True)
            sub.operator("chocofur.libpath_open", icon="ZOOM_IN", text="").libpath=lib.path
            sub.operator("chocofur.remove_library", icon="X", text="").index=i
            # sub = sub.row(align=True)
            sub.separator()
            sub.operator("chocofur.library_item_down", icon="TRIA_DOWN", text="").index=i
            sub.operator("chocofur.library_item_up", icon="TRIA_UP", text="").index=i
        
        col = layout.column()
        col.operator('chocofur.add_library', icon="ADD")
        col.operator('chocofur.libpath_set_default')
        
        
        layout = self.layout
        # col = layout.column() # works best if a column, or even just self.layout
        mainrow = layout.row()
        col = mainrow.column()

        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # col.operator("wm.url_open","Open webpage ").url=addon_updater_ops.updater.website