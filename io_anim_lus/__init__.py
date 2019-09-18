# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Export: SpringRTS Lua Unit Script (LUS)",
    "author": "An orchid",
	"version" : (0,1,2),
    "blender": (2, 80,0),
    "location": "File > Import-Export",
	'warning': '',
	  'wiki_url': 'https://github.com/Anarchid/blender2lus',
	'tracker_url': 'https://github.com/Anarchid/blender2lus/issues',
    "description": "Export Lua Unit Scripts from scene-defined actions",
	'support': 'COMMUNITY',
    "category": "Export"
    }

import bpy
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
from bpy.props import (StringProperty,EnumProperty)
from bpy_extras.io_utils import ExportHelper

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value

class ExportLUS(bpy.types.Operator, ExportHelper):
    """Save a scene-wide LUS animscript from currently active action on each object"""
    bl_idname = "export_lus.lua"
    bl_label = "Export LUS"
    #bl_space_type='VIEW_3D'
    #bl_context_mode='OBJECT'

    filename_ext = ".lua"
    filter_glob = bpy.props.StringProperty(
            default="*.lua",
            options={'HIDDEN'},
            )
    
    mode = bpy.props.EnumProperty(
                items=(('main', "Main Script File", "Export the animation alongside the animation framweork"),
                       ('include', "Animation Include", "Export just the animation as an include for the main script"),
                       ),
                name="Script type",
                description="Type of animation script to create",
                default='include',
                )

    @classmethod
    def poll(cls, context):
        obj = context.object
        if(obj):
            return True
        else:
            return True

    def invoke(self, context, event):
        return super().invoke(context, event)

    def execute(self, context):
        keywords = self.as_keywords(ignore=("check_existing", "filter_glob"))
        return self.export(self, context, **keywords)
    
    def export(self, operator, context, filepath="", mode="main"):
        print('exporting to '+str(filepath));
        
        only_keyframes = (mode == "include")
        anim_name=bpy.path.display_name_from_filepath(bpy.context.blend_data.filepath)
        write_pieces = (mode == "main")
        write_function = (mode == "main")
        write_create = (mode == "main")

        timeline = AutoVivification()
        props = {"location":"move", "rotation_euler":"turn"} 
        axes = {'location':['x_axis', 'y_axis', 'z_axis'],'rotation_euler':['x_axis', 'y_axis', 'z_axis']}
        
        rotation_axis_mults = [1,1,1]
               
        from mathutils import Matrix, Euler
        from math import degrees
        file = open(filepath, "w", encoding="utf8", newline="\n")
        
        if(write_pieces and not only_keyframes):
            for ob in bpy.data.objects:
                file.write("local "+ob.name+" = piece('"+ob.name+"');\n")
            file.write("local scriptEnv = {")
            for ob in bpy.data.objects:
                file.write("\t"+ob.name+" = "+ob.name+",\n")
            file.write('\tx_axis = x_axis,\n')
            file.write('\ty_axis = y_axis,\n')
            file.write('\tz_axis = z_axis,\n')
            file.write('}\n\n')
            file.write('local Animations = {};\n')
            file.write('-- you can include externally saved animations like this:\n')
            file.write('-- Animations[\'importedAnimation\'] = VFS.Include("Scripts/animations/animationscript.lua", scriptEnv)\n')
                    
        for ob in bpy.data.objects:
            if (not ob.animation_data is None):
                if(not ob.animation_data.action is None):
                    curves = ob.animation_data.action.fcurves;
                    for c in curves:
                        if(not c.data_path in props.keys()):
                            print('skipping curve for property '+c.data_path)
                            continue
                        
                        backtrack = None;
                        
                        keyframes = c.keyframe_points
                        i = 0
                        for k in keyframes:    
                            print("adding "+ob.name+" "+c.data_path+"<"+str(c.array_index)+"> keyframe "+str(i)+' at <'+str(k.co[0])+','+str(k.co[1])+">")
                            
                            kf_value = k.co[1]
                            
                            if(c.data_path == 'rotation_euler'):
                                kf_value = kf_value * rotation_axis_mults[c.array_index]
                                
                            if (backtrack is None):
                                print('no backtrack for '+str(c.data_path)+str(c.array_index)+": declaring initial")
                                timeline[k.co[0]][ob.name][c.data_path][c.array_index]['value'] = kf_value
                                timeline[k.co[0]][ob.name][c.data_path][c.array_index]['target'] = kf_value
                                timeline[k.co[0]][ob.name][c.data_path][c.array_index]['speed'] = 0
                                
                                print('timeline value is now '+str(timeline[k.co[0]][ob.name][c.data_path][c.array_index]['value']))
                            else:
                                print('backtrack found for '+str(c.data_path)+str(c.array_index)+": "+str(backtrack))
                                timeline[k.co[0]][ob.name][c.data_path][c.array_index]['value'] = kf_value
                                
                                time = k.co[0] - backtrack
                                old_value = timeline[backtrack][ob.name][c.data_path][c.array_index]['value']
                                
                                if(old_value == {}):
                                    print('value of previous keyframe is nil!?')
                                    diff = 0
                                else:
                                    diff = kf_value - old_value
                                # our blender time is in frames, but turn/move commands want radians|elmos per second
                                # there are 30 spring frames in a second, which means, speed per second = 30x speed per frame 
                                speed = abs(diff/time) * 30
                                
                                timeline[backtrack][ob.name][c.data_path][c.array_index]['speed'] = speed
                                timeline[backtrack][ob.name][c.data_path][c.array_index]['target'] = kf_value
                            backtrack = k.co[0]
                            i+=1
                    
        keys = sorted(timeline.keys())
        
        # prune useless data

        for k in keys:
            kf = timeline[k];
            for piece in list(kf):
                for channel in list(kf[piece]):
                    for axis in list(kf[piece][channel]):
                        if (not type(kf[piece][channel][axis]['target']).__name__=="float"):
                            # prune non-command entries
                            del kf[piece][channel][axis]
                        else:
                            # prune redundant commands
                            if k > 0 and kf[piece][channel][axis]['target'] == kf[piece][channel][axis]['value']:
                                del kf[piece][channel][axis]
                    # delete channel if all axes are non-acting
                    if len(kf[piece][channel]) == 0:
                        del kf[piece][channel]
                if len(kf[piece]) == 0:
                    del kf[piece]
            if len(kf) == 0:
                print("keyframe "+str(k)+" is idle, but keeping for trailing Sleep() calculation")
                #del timeline[k]
        
        if (only_keyframes):
            file.write("return {\n")
        else:
            file.write("\nAnimations['"+anim_name+"'] = {\n")
                        
        keys = sorted(timeline.keys())
        for k in keys:
            kf = timeline[k];
            file.write("\t{\n\t\t['time'] = "+str(int(k))+",\n\t\t['commands'] = {\n")
              
            for piece in kf:
                for channel in kf[piece]:
                    for axis in kf[piece][channel].keys():
                        if (type(kf[piece][channel][axis]['target']).__name__=="float"):
                            axis_name = axes[channel][axis]
                            file.write("\t\t\t{['c']='"+props[channel]+"',['p']="+piece+", ['a']="+axis_name+", ['t']=")
                            file.write('%f' % kf[piece][channel][axis]['target']+", ['s']="+'%f' % kf[piece][channel][axis]['speed']+'},\n')                        

            file.write("\t\t}\n\t},\n")
        file.write("}\n")
        
        if write_create and not only_keyframes:
            file.write("""
function constructSkeleton(unit, piece, offset)
    if (offset == nil) then
        offset = {0,0,0};
    end

    local bones = {};
    local info = Spring.GetUnitPieceInfo(unit,piece);

    for i=1,3 do
        info.offset[i] = offset[i]+info.offset[i];
    end 

    bones[piece] = info.offset;
    local map = Spring.GetUnitPieceMap(unit);
    local children = info.children;

    if (children) then
        for i, childName in pairs(children) do
            local childId = map[childName];
            local childBones = constructSkeleton(unit, childId, info.offset);
            for cid, cinfo in pairs(childBones) do
                bones[cid] = cinfo;
            end
        end
    end        
    return bones;
end

function script.Create()
    local map = Spring.GetUnitPieceMap(unitID);
    local offsets = constructSkeleton(unitID,map.Scene, {0,0,0});
    
    for a,anim in pairs(Animations) do
        for i,keyframe in pairs(anim) do
            local commands = keyframe.commands;
            for k,command in pairs(commands) do
                -- commands are described in (c)ommand,(p)iece,(a)xis,(t)arget,(s)peed format
                -- the t attribute needs to be adjusted for move commands from blender's absolute values
                if (command.c == "move") then
                    local adjusted =  command.t - (offsets[command.p][command.a]);
                    Animations[a][i]['commands'][k].t = command.t - (offsets[command.p][command.a]);
                end
            end
        end
    end
end
            """)
        
        if write_function and not only_keyframes:
            file.write("""
local animCmd = {['turn']=Turn,['move']=Move};
function PlayAnimation(animname)
    local anim = Animations[animname];
    for i = 1, #anim do
        local commands = anim[i].commands;
        for j = 1,#commands do
            local cmd = commands[j];
            animCmd[cmd.c](cmd.p,cmd.a,cmd.t,cmd.s);
        end
        if(i < #anim) then
            local t = anim[i+1]['time'] - anim[i]['time'];
            Sleep(t*33); -- sleep works on milliseconds
        end
    end
end
            """)
        file.close()
                
        return {'FINISHED'}

def menu_func_export(self, context):
                    self.layout.operator(
                    ExportLUS.bl_idname,
                    text="SpringRTS Lua Unit Script (.lua)"
                    )

def export_manual_map():
    url_manual_prefix = "https://github.com/Anarchid/blender2lus"
    url_manual_mapping = (
        ("bpy.ops.mesh.add_object", "editors/3dview/object"),
    )
    return url_manual_prefix, url_manual_mapping



def register():
    if (2, 80, 0) < bpy.app.version:
        bpy.utils.register_class(ExportLUS)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)      
    else:
        bpy.utils.register_class(__name__)
        bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    #endif
    
    bpy.utils.register_manual_map(export_manual_map)
   
def unregister():
    if (2, 80, 0) < bpy.app.version:
        bpy.utils.unregister_class(ExportLUS)
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    else:
        bpy.utils.unregister_class(__name__)
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)       
    #endif
    
    bpy.utils.unregister_manual_map(export_manual_map)

if __name__ == "__main__":
    register()
    
