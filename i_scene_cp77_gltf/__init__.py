bl_info = {
    "name": "Cyberpunk 2077 glTF Importer",
    "author": "HitmanHimself, Turk, Jato, dragonzkiller",
    "version": (1, 0, 7),
    "blender": (3, 0, 0),
    "location": "File > Import-Export",
    "description": "Import WolvenKit Cyberpunk2077 glTF Models With Materials",
    "warning": "",
    "category": "Import-Export",
}

import bpy
import bpy.utils.previews
import glob
import json
import os
import os.path
import platform


from bpy.props import (
    StringProperty,
    EnumProperty,
    BoolProperty)
from bpy_extras.io_utils import ImportHelper
from io_scene_gltf2.io.imp.gltf2_io_gltf import glTFImporter
from io_scene_gltf2.blender.imp.gltf2_blender_gltf import BlenderGlTF
from .main.setup import MaterialBuilder

icons_dir = os.path.join(os.path.dirname(__file__), "icons")
custom_icon_col = {}

class CP77StreamingSectorImport(bpy.types.Operator,ImportHelper):
    bl_idname = "io_scene_glft.cp77sector"
    bl_label = "Import StreamingSector"
    use_filter_folder = True
    filter_glob: StringProperty(
        default=".",
        options={'HIDDEN'},
        )
    import_materials: BoolProperty(name="Import Model Materials",default=True,description="Enable this option to include materials on the imported meshes")
    image_format: EnumProperty(
        name="Textures",
        items=(("png", "Use PNG textures", ""),
                ("dds", "Use DDS textures", ""),
                ("jpg", "Use JPG textures", ""),
                ("tga", "Use TGA textures", ""),
                ("bmp", "Use BMP textures", ""),
                ("jpeg", "Use JPEG textures", "")),
        description="Texture Format",
        default="png")
    exclude_unused_mats: BoolProperty(name="Exclude Unused Materials",default=True,description="Enabling this options skips all the materials that aren't being used by any mesh") 

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'import_materials')
        layout.prop(self, 'image_format')
        layout.prop(self, 'exclude_unused_mats')

    def execute(self, context):
        path = self.properties.filepath

        jsonpath = glob.glob(path+"\**\*.streamingsector.json", recursive = True)
        filepath = jsonpath[0]

        path2 = os.path.splitext(filepath)[0] + r'.worldNodeData.json'

        with open(filepath,'r') as f: 
              j=json.load(f) 
      
        with open(path2,'r') as f: 
              t=json.load(f) 
      
        meshes =  glob.glob(path+"\**\*.glb", recursive = True)

        glbnames = [ os.path.basename(x) for x in meshes]
        meshnames = [ os.path.splitext(x)[0]+".mesh" for x in glbnames]

        prop = j["Data"]["RootChunk"]["Properties"]
        nodes = prop["nodes"]

        for i,e in enumerate(nodes):
            data = e['Data']["Properties"]
            for k in (data.keys()):
                if isinstance(data[k], dict) and ("DepotPath" in data[k].keys()):
                    meshname = data[k]['DepotPath']
            
                    if(meshname != 0):
                        glbfoundname = [ x for x in meshes if os.path.splitext(str(meshname))[0] in x] 
                        if(len(glbfoundname) == 1):
                            instances = [x for x in t if x['NodeIndex'] == i]
                            nn = str(data['debugName']).replace('{','').replace('}','')
                    
                            for inst in instances:
                                gltf_importer = glTFImporter(glbfoundname[0], { "files": None, "loglevel": 0, "import_pack_images" :True, "merge_vertices" :False, "import_shading" : 'NORMALS', "bone_heuristic":'TEMPERANCE', "guess_original_bind_pose" : False, "import_user_extensions": ""})
                                gltf_importer.read()
                                gltf_importer.checks()

                                if self.import_materials:
                                    existingMeshes = bpy.data.meshes.keys()
                                    existingObjects = bpy.data.objects.keys()
                                    existingMaterials = bpy.data.materials.keys()

                                BlenderGlTF.create(gltf_importer)
                        
                                objects = bpy.context.selected_objects
                                for obj in objects:                            
                                    nn = [nn[1:],nn][nn[0].isalnum()]
                                    obj.name = nn

                                    obj.location.x = inst['Position']['Properties']['X'] /100
                                    obj.location.y = inst['Position']['Properties']['Y'] /100
                                    obj.location.z = inst['Position']['Properties']['Z'] /100

                                    obj.rotation_quaternion.x = inst['Orientation']['Properties']['i']
                                    obj.rotation_quaternion.y = inst['Orientation']['Properties']['j']
                                    obj.rotation_quaternion.z = inst['Orientation']['Properties']['k']
                                    obj.rotation_quaternion.w = inst['Orientation']['Properties']['r']

                                    obj.scale.x = inst['Scale']['Properties']['X'] /100
                                    obj.scale.y = inst['Scale']['Properties']['Y'] /100
                                    obj.scale.z = inst['Scale']['Properties']['Z'] /100

                                # TODO: move material processing out to it's own function
                                if self.import_materials:
                                    for name in bpy.data.materials.keys():
                                        if name not in existingMaterials:
                                            bpy.data.materials.remove(bpy.data.materials[name], do_unlink=True, do_id_user=True, do_ui_user=True)

                                    if platform.system() == 'Windows':
                                        # windows can reach MAX_PATH easily
                                        BasePath = u"\\\\?\\" + os.path.splitext(glbfoundname[0])[0]
                                    else:
                                        BasePath = os.path.splitext(glbfoundname[0])[0]

                                    file = open(BasePath + ".Material.json",mode='r')
                                    obj2 = json.loads(file.read())
                                    BasePath = str(obj2["MaterialRepo"])  + "\\"

                                    Builder = MaterialBuilder(obj2, BasePath, str(self.image_format))

                                    usedMaterials = {}
                                    counter = 0
                                    for name in bpy.data.meshes.keys():
                                        if name not in existingMeshes:
                                            bpy.data.meshes[name].materials.clear()
                                            for matname in gltf_importer.data.meshes[counter].extras["materialNames"]:
                                                if matname not in usedMaterials.keys():
                                                    index = 0
                                                    for rawmat in obj2["Materials"]:
                                                        if rawmat["Name"] == matname:
                                                            bpymat = Builder.create(index)
                                                            bpy.data.meshes[name].materials.append(bpymat)
                                                            usedMaterials.update( {matname: bpymat} )
                                                        index = index + 1
                                                else:
                                                    bpy.data.meshes[name].materials.append(usedMaterials[matname])
                        
                                            counter = counter + 1

                                    if not self.exclude_unused_mats:
                                        index = 0
                                        for rawmat in obj2["Materials"]:
                                            if rawmat["Name"] not in usedMaterials:
                                                Builder.create(index)
                                            index = index + 1

                                    collection = bpy.data.collections.new(os.path.splitext(os.path.basename(glbfoundname[0]))[0])
                                    bpy.context.scene.collection.children.link(collection)

                                    for name in bpy.data.objects.keys():
                                        if name not in existingObjects:
                                            for parent in bpy.data.objects[name].users_collection:
                                                parent.objects.unlink(bpy.data.objects[name])
                                            collection.objects.link(bpy.data.objects[name])

        self.report({'INFO'}, "Streaming Sector Import successful!")
        return {'FINISHED'}

class CP77Import(bpy.types.Operator,ImportHelper):
    bl_idname = "io_scene_gltf.cp77"
    bl_label = "Import glTF"
    filter_glob: StringProperty(
        default="*.gltf;*.glb",
        options={'HIDDEN'},
        )
    image_format: EnumProperty(
        name="Textures",
        items=(("png", "Use PNG textures", ""),
                ("dds", "Use DDS textures", ""),
                ("jpg", "Use JPG textures", ""),
                ("tga", "Use TGA textures", ""),
                ("bmp", "Use BMP textures", ""),
                ("jpeg", "Use JPEG textures", "")),
        description="Texture Format",
        default="png")
    exclude_unused_mats: BoolProperty(name="Exclude Unused Materials",default=True,description="Enabling this options skips all the materials that aren't being used by any mesh") 
    filepath: StringProperty(subtype = 'FILE_PATH')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'exclude_unused_mats')
        layout.prop(self, 'image_format')

    def execute(self, context):
        gltf_importer = glTFImporter(self.filepath, { "files": None, "loglevel": 0, "import_pack_images" :True, "merge_vertices" :False, "import_shading" : 'NORMALS', "bone_heuristic":'TEMPERANCE', "guess_original_bind_pose" : False, "import_user_extensions": ""})
        gltf_importer.read()
        gltf_importer.checks()

        existingMeshes = bpy.data.meshes.keys()
        existingObjects = bpy.data.objects.keys()
        existingMaterials = bpy.data.materials.keys()

        BlenderGlTF.create(gltf_importer)

        for name in bpy.data.materials.keys():
            if name not in existingMaterials:
                bpy.data.materials.remove(bpy.data.materials[name], do_unlink=True, do_id_user=True, do_ui_user=True)

        BasePath = os.path.splitext(self.filepath)[0]
        file = open(BasePath + ".Material.json",mode='r')
        obj = json.loads(file.read())
        BasePath = str(obj["MaterialRepo"])  + "\\"

        Builder = MaterialBuilder(obj,BasePath,str(self.image_format))

        usedMaterials = {}
        counter = 0
        for name in bpy.data.meshes.keys():
            if name not in existingMeshes:
                bpy.data.meshes[name].materials.clear()
                for matname in gltf_importer.data.meshes[counter].extras["materialNames"]:
                    if matname not in usedMaterials.keys():
                        index = 0
                        for rawmat in obj["Materials"]:
                            if rawmat["Name"] == matname:
                                bpymat = Builder.create(index)
                                bpy.data.meshes[name].materials.append(bpymat)
                                usedMaterials.update( {matname: bpymat} )
                            index = index + 1
                    else:
                        bpy.data.meshes[name].materials.append(usedMaterials[matname])
                        
                counter = counter + 1

        if not self.exclude_unused_mats:
            index = 0
            for rawmat in obj["Materials"]:
                if rawmat["Name"] not in usedMaterials:
                    Builder.create(index)
                index = index + 1


        collection = bpy.data.collections.new(os.path.splitext(os.path.basename(self.filepath))[0])
        bpy.context.scene.collection.children.link(collection)

        for name in bpy.data.objects.keys():
            if name not in existingObjects:
                for parent in bpy.data.objects[name].users_collection:
                    parent.objects.unlink(bpy.data.objects[name])
                collection.objects.link(bpy.data.objects[name])

        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(CP77Import.bl_idname, text="Cyberpunk GLTF (.gltf/.glb)", icon_value=custom_icon_col["import"]['WKIT'].icon_id)
    self.layout.operator(CP77StreamingSectorImport.bl_idname, text="Cyberpunk StreamingSector (.json)")

def register():
    custom_icon = bpy.utils.previews.new()
    custom_icon.load("WKIT", os.path.join(icons_dir, "wkit.png"), 'IMAGE')
    custom_icon_col["import"] = custom_icon

    bpy.utils.register_class(CP77Import)
    bpy.utils.register_class(CP77StreamingSectorImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
def unregister():
    bpy.utils.previews.remove(custom_icon_col["import"])

    bpy.utils.unregister_class(CP77Import)
    bpy.utils.unregister_class(CP77StreamingSectorImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        
if __name__ == "__main__":
    register()