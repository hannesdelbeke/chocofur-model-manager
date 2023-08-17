# Created by Chocofur, Styriam Sp. z o.o., Open AI

bl_info = {
    "name": "Chocofur Model Manager",
    "author": "Chocofur",
    "version": (1, 2, 5),
    "blender": (3, 3, 1),
    "location": "View 3D > Tool Shelf",
    "wiki_url": "http://chocofur.com",
    "tracker_url": "http://chocofur.com",
    "support": "COMMUNITY",
    "category": "Add Mesh"
    }    
    
import bpy


# register
################################## 


from . import controller

from . import auto_load

auto_load.init(ignore=("addon_updater", "addon_updater_ops"), make_annotations=True)

def register():
    auto_load.register()
    
    # addon updater code and configurations
    # in case of broken version, try to register the updater first
    # so that users can revert back to a working version
    from . import addon_updater_ops
    addon_updater_ops.register(bl_info)
    from .addon_updater import Updater as updater
    updater.engine = "bitbucket"
    updater.user = "chocofur"
    updater.repo = "chocofur-model-manager-2.8"
    updater.addon = "chocofur_model_manager"
    updater.remove_pre_update_patterns = ["*.py","*.pyc"]
       
    addon_updater_ops.check_for_update_background()

def unregister():    
    auto_load.unregister()
    from . import addon_updater_ops
    addon_updater_ops.unregister()