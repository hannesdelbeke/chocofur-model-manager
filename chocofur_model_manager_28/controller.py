import bpy
import os, random
from time import time, time_ns
from bpy.props import *
import bpy.utils.previews
from bpy.types import WindowManager


######################################################################
############################ Library Path ############################
######################################################################
def get_default_libpath():
    script_file = os.path.realpath(__file__)
    dir = os.path.dirname(script_file)
    return os.path.join(dir, 'Models')
    
class CHOCOFUR_OT_LibpathSetDefault(bpy.types.Operator):
    '''Restore default library path'''
    bl_idname = "chocofur.libpath_set_default"
    bl_label = "Restore Default Library Path"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        addon_prefs.library_path = get_default_libpath()
        bpy.ops.chocofur.refresh_categories()

        l=addon_prefs.library_collection.add()
        l.id = str(time_ns()) + ''.join(random.choice('0123456789ABCDEFGHIJKLMNOPRSTUWXYZ') for i in range(4))
        l.path = get_default_libpath()
        l.name = "Default Library"

        return{'FINISHED'}
    
class CHOCOFUR_OT_LibpathOpen(bpy.types.Operator):
    '''Open library in system file browser'''
    bl_idname = "chocofur.libpath_open"
    bl_label = "Library Path"
    
    libpath: StringProperty()

    def execute(self, context):
        try:
            bpy.ops.wm.path_open(filepath=self.libpath)
        except Exception:
            self.report({'ERROR'}, "Library path is incorrect. Set correct path in addon preferences.")
        return {'FINISHED'}

##################################################################
########################### Categories ###########################
##################################################################

from .gui import category_factory
categories_tmp = {}
def list_categories(lib):
    directory = lib.path
    dirs = []
    if os.path.exists(directory):
        for fn in os.listdir(directory):
            if not fn.startswith('.') and os.path.isdir(os.path.join(directory, fn)):
                dirs.append(fn)

    global categories_tmp
    categories_tmp[lib.id] = dirs[:]

    return dirs

class CHOCOFUR_OT_Refresh_Categories(bpy.types.Operator):
    bl_idname = "chocofur.refresh_categories"
    bl_label = "Refresh Categories"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        global collections
        # remove preview collections before adding them again (because categories need to be recreated to insure correct panel order)
        unused_libs = [k for k in collections if not get_library(context, k)]
        for lidx in unused_libs:
            clist = (c['main'] for c in collections[lidx].values())
            for c in clist:
                try:
                    bpy.utils.previews.remove(c)
                except KeyError:
                    print("Preview key error. Ignored.")

            for name in [n for n in bpy.types.__dir__() if 'CATEGORY_PT_chocofur_c'+lidx in n]:
                bpy.utils.unregister_class(getattr(bpy.types, name))
            for name in [n for n in context.scene.chocofur_model_manager.__dir__() if 'c'+lidx in n]:
                delattr(Chocofur_Model_Manager_Scene_Properties, name)
            del collections[lidx]

        for library in addon_prefs.library_collection:
            old_categories=[]
            if library.id in collections:
                clist = (c['main'] for c in collections[library.id].values())
                for c in clist:
                    try:
                        bpy.utils.previews.remove(c)
                    except KeyError:
                        print("Preview key error. Ignored.")

                # remove unused categories
                old_categories = categories_tmp[library.id][:]
            new_categories = list_categories(library)
            
            unused_categories = list(set(old_categories) - set(new_categories))
            for c in unused_categories:
                bpy.utils.unregister_class(getattr(bpy.types, "CATEGORY_PT_chocofur_c{}_{}".format(library.id, c)))
                delattr(Chocofur_Model_Manager_Scene_Properties, "c{}_{}_category".format(library.id, c))
                delattr(Chocofur_Model_Manager_Scene_Properties, "c{}_{}_previews".format(library.id, c))
                del collections[library.id][c]
                    
            ##

            for d in new_categories:
                pcoll = bpy.utils.previews.new()
                pcoll.previews_dir = ""
                pcoll.previews = ()
                if not library.id in collections:
                    collections[library.id] = {}
                collections[library.id][d]={'main': pcoll, 'updated': 0}
                
                bpy.utils.register_class(category_factory(library, d))

                setattr(Chocofur_Model_Manager_Scene_Properties, 'c{}_{}_previews'.format(library.id, d), EnumProperty(
                    items = enum_preview_items_func_factory(library, d)
                ))
                        
                setattr(Chocofur_Model_Manager_Scene_Properties, 'c{}_{}_category'.format(library.id, d), EnumProperty(
                    name="Collection {}, {} Category".format(library.name, d),
                    items=populate_category_func_factory(library, d),
                    description="Select "+d,
                ))

        return {'FINISHED'}
    
    
bpy.chocofur_refresh_time = 0
bpy.chocofur_category_time = 0
from bpy.app.handlers import persistent
@persistent
def chocofur_refresh(scene):
    newTime = time()
    if newTime > bpy.chocofur_refresh_time + 2:
        bpy.chocofur_refresh_time = newTime
        
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        force_refresh = False
        for lib in addon_prefs.library_collection:
            directory = lib.path
            if not os.path.exists(directory):
                print("Chocofur: Invalid path to model library")
                continue

            # Check if a .txt file is present in the root folder and force refresh
            for item in os.listdir(directory):
                _, file_extension = os.path.splitext(item)
                if file_extension.lower() == ".txt":
                    force_refresh = True
                    break

            # read file list from disk only when necessary
            dir_up = os.path.getmtime(directory)
            if dir_up > bpy.chocofur_category_time or force_refresh:
                bpy.chocofur_category_time = dir_up
                bpy.ops.chocofur.refresh_categories()
                return
        
##################################################################
############################ Previews ############################
##################################################################
def enum_preview_items_func_factory(lib, sname):
    def func(self, context):
        category = getattr(context.scene.chocofur_model_manager, "c{}_{}_category".format(lib.id, sname))
        chocoprops = context.window_manager.chocofur_model_manager
        directory = os.path.join(lib.path, sname, category, "renders")

        enum_items = []

        if context is None:
            return enum_items
        
        pcoll = collections[lib.id][sname]["main"]
        
        if directory == pcoll.previews_dir:
            return pcoll.previews

        if directory and os.path.exists(directory):
            image_paths = []
            for fn in os.listdir(directory):
                if fn.lower().endswith(".jpg"):
                    image_paths.append(fn)

            for i, name in enumerate(image_paths):
                filepath = os.path.join(directory, name)
                
                if filepath in pcoll:
                    enum_items.append((name, name, "", pcoll[filepath].icon_id, i))
                else:
                    thumb = pcoll.load(filepath, filepath, 'IMAGE')
                    enum_items.append((name, name, "", thumb.icon_id, i))
        enum_items.sort()

        pcoll.previews = enum_items
        pcoll.previews_dir = directory
        return pcoll.previews
    
    return func

collections = {}


################################################################
############################ Append ############################
################################################################


####### Append Furniture ####### 

class CHOCOFUR_OT_AddButton(bpy.types.Operator):
    '''Add object to scene'''
    bl_idname = "chocofur.add"
    bl_label = "Add Object"
    
    object_type: StringProperty()
    libpath: StringProperty()
    libid: StringProperty()

    def execute(self, context):
        chocoprops = context.window_manager.chocofur_model_manager
        
        selected_preview = getattr(context.scene.chocofur_model_manager, "c{}_{}_previews".format(self.libid, self.object_type))
        category = getattr(context.scene.chocofur_model_manager, "c{}_{}_category".format(self.libid, self.object_type))
        model_path = self.object_type
        scn = bpy.context.scene
        
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        filepath = (os.path.join(self.libpath, model_path, category, os.path.splitext(selected_preview)[0] + ".blend"))
        
        bpy.ops.object.select_all(action='DESELECT')        
        
        isLink = True if context.window_manager.chocofur_model_manager.import_mode == 'LINK' else False
        with bpy.data.libraries.load(filepath, link=isLink) as (data_from, data_to):
            data_to.objects = data_from.objects
            if hasattr(data_from, "groups") and data_from.groups:
                data_to.groups = data_from.groups
        
        #blender bug when localising linked library: when Empty (parent) is made local parenting stops working
        #workaround: use DFS to localise objects in order from youngest to oldest
        parents = (ob for ob in data_to.objects if not ob.parent)
        def process_object(obj):
            for child in obj.children:
                process_object(child)
                                
            context.collection.objects.link(obj)
            obj.make_local()

            if not isLink and obj.data and obj.data.library:
                # make linked data-block single user copy in case of name clash
                obj.data = obj.data.copy()

            obj.select_set(True)
                
        for obj in parents:
            process_object(obj)
        
        if context.window_manager.chocofur_model_manager.append_location == 'CURSOR':
            bpy.ops.transform.translate(value=context.scene.cursor.location)
               
        return{'FINISHED'}

class CHOCOFUR_OT_AddLibButton(bpy.types.Operator):
    '''Add new vendor library'''
    bl_idname = "chocofur.add_library"
    bl_label = "Add New Library"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        l=addon_prefs.library_collection.add()
        l.id = str(time_ns()) + ''.join(random.choice('0123456789ABCDEFGHIJKLMNOPRSTUWXYZ') for i in range(4))
               
        return{'FINISHED'}

class CHOCOFUR_OT_RemoveLibButton(bpy.types.Operator):
    '''Remove vendor library'''
    bl_idname = "chocofur.remove_library"
    bl_label = "Remove Vendor Library"
    bl_options = {"INTERNAL"}

    index: IntProperty()

    def execute(self, context):
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        addon_prefs.library_collection.remove(self.index)
        bpy.ops.chocofur.refresh_categories()
        from . gui import refresh_ui
        refresh_ui()
               
        return{'FINISHED'}

############################ Register ############################


class Chocofur_Model_Manager_WM_Properties(bpy.types.PropertyGroup):
            
    append_location: EnumProperty(
            name="Append Location",
            description="Where model is to be appended",
            items = [
                    ("CENTER", "Center", "", 0),
                    ("CURSOR", "Cursor", "", 1),
                ],
            default = "CENTER",
            )
    import_mode: EnumProperty(
            name="Import Mode",
            description="Whether to Link or Append from library.",
            items = [
                    ("APPEND", "Append", "", 0),
                    ("LINK", "Link", "", 1),
                ],
            default = "APPEND",
            )

def get_library(context, id):
    addon_prefs = context.preferences.addons[__package__].preferences
    for l in addon_prefs.library_collection:
        if l.id==id:
            return l
    return None

def populate_category_func_factory(lib, category):
    def func(self, context):
        directory = os.path.join(lib.path, category)
        
        if not os.path.exists(directory):
            print("Chocofur: Invalid path to model library")
            return []
        # read file list from disk only when necessary
        dir_up = os.path.getmtime(directory)
        if dir_up <= collections[lib.id][category]['updated']:
            return collections[lib.id][category]['items']
        
        mode_options = []
        counter=0
        for dir in (d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))):
            mode_options.append(
                (dir, dir, '', counter)
            )
            counter+=1
            
        collections[lib.id][category]['items'] = mode_options
        collections[lib.id][category]['updated'] = dir_up
        
        return mode_options
    return func

class Chocofur_Model_Manager_Scene_Properties(bpy.types.PropertyGroup):
    pass

def register():
    WindowManager.chocofur_model_manager = bpy.props.PointerProperty(type=Chocofur_Model_Manager_WM_Properties)
    bpy.types.Scene.chocofur_model_manager = bpy.props.PointerProperty(type=Chocofur_Model_Manager_Scene_Properties)

    addon_prefs = bpy.context.preferences.addons[__package__].preferences
    for lib in addon_prefs.library_collection:
        collections[lib.id]={}
        for d in list_categories(lib):
            setattr(Chocofur_Model_Manager_Scene_Properties, 'c{}_{}_previews'.format(lib.id, d), EnumProperty(
                    items = enum_preview_items_func_factory(lib, d)
            ))
                    
            setattr(Chocofur_Model_Manager_Scene_Properties, 'c{}_{}_category'.format(lib.id, d), EnumProperty(
                name="Collection {}, {} Category".format(lib.name, d),
                items=populate_category_func_factory(lib, d),
                description="Select "+d,
            ))

            
            pcoll = bpy.utils.previews.new()
            pcoll.previews_dir = ""
            pcoll.previews = ()
            collections[lib.id][d]={'main': pcoll, 'updated': 0}
    
    if not addon_prefs.library_collection:
        l=addon_prefs.library_collection.add()
        l.id = str(time_ns()) + ''.join(random.choice('0123456789ABCDEFGHIJKLMNOPRSTUWXYZ') for i in range(4))
        l.path = get_default_libpath()
    
    from .gui import refresh_ui
    refresh_ui()
    
    bpy.app.handlers.depsgraph_update_post.append(chocofur_refresh)

def unregister():
    del WindowManager.chocofur_model_manager
    del bpy.types.Scene.chocofur_model_manager
    
    for lib in collections.values():
        for col in lib.values():
            try:
                bpy.utils.previews.remove(col['main'])
            except KeyError:
                print("Preview key error. Ignored.")
            col['main'].clear()
        
    for name in [n for n in bpy.types.__dir__() if 'CATEGORY_PT_chocofur_' in n]:
        bpy.utils.unregister_class(getattr(bpy.types, name))
        
    bpy.app.handlers.depsgraph_update_post.remove(chocofur_refresh)

    print('Addon unregistered')