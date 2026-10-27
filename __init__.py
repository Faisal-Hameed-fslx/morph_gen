bl_info = {
    "name": "CC Character Generator",
    "author": "Malik",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > CC Char",
    "description": "Generate characters from Character Creator base meshes using morph sliders",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy

from . import properties, operators, panels


def register():
    properties.register()
    operators.register()
    panels.register()
    operators.register_handlers()


def unregister():
    operators.unregister_handlers()
    panels.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
