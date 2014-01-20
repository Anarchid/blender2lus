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
    "author": "Anarchid",
    "blender": (2, 69, 0),
    "location": "File > Import-Export",
    "description": "Export Lua Unit Scripts from scene-defined actions",
    "category": "Import-Export"
    }

import bpy

from bpy.props import (StringProperty,
                       FloatProperty,
                       IntProperty,
                       BoolProperty,
                       EnumProperty,
                       )
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
    """Save a LUS animscript from each action defined in scene/selection"""
    bl_idname = "export_lus.lua"
    bl_label = "Export LUS"

    filename_ext = ".lua"
    filter_glob = StringProperty(
            default="*.lua",
            options={'HIDDEN'},
            )
    
    anim_name = StringProperty(
        name = "Anim name",
        default="myAnimation",
        description="name for the animation inside the animations table, if you want more than one for this model",
        )
    
    write_pieces = BoolProperty(
        name="Write Pieces",
        description="includes piece declarations in exported file, typically useful once per model",
        default=True,
        )
    
    write_function = BoolProperty(
        name="Write Animate() function",
        description="includes the Animate() function in exported file to playback saved keyframes",
        default=True,
        )
    
    write_create = BoolProperty(
        name="Write Create() function",
        description="includes the bindpose adjustment function in exported file, typically useful once per model",
        default=True,
        )

    @classmethod
    def poll(cls, context):
        obj = context.object
        if(obj):
            print('LusExport:poll received from object of type'+obj.type)
            return True
        else:
            print('LusExport:polling a non-object? huh? whatevs.')
            return True

    def invoke(self, context, event):
        print('LusExport:inglwnafh wgahnagl!')
        return super().invoke(context, event)

    def execute(self, context):
        print("LusExport:execute him!");
        keywords = self.as_keywords(ignore=("check_existing", "filter_glob"))
        return self.export(self, context, **keywords)
    
    def export(self, operator, context, filepath="", anim_name="myAnimation", write_pieces=True,write_function=True,write_create=True):
        print('exporting to '+str(filepath));

        timeline = AutoVivification()
        props = {"location":"move", "rotation_euler":"turn"} 
        axes = {'location':['x_axis', 'y_axis', 'z_axis'],'rotation_euler':['x_axis', 'y_axis', 'z_axis']}
        
        rotation_axis_mults = [1,1,1]
               
        from mathutils import Matrix, Euler
        from math import degrees
        file = open(filepath, "w", encoding="utf8", newline="\n")
        
        for ob in bpy.data.objects:
            
            if(write_pieces):
                file.write("local "+ob.name+" = piece('"+ob.name+"');\n")
            
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

        if write_pieces:
            file.write('local Animations = {};\n')
        
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
        
        if write_create:
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
        
        if write_function:
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
    self.layout.operator(ExportLUS.bl_idname, text="SpringRTS Lua Unit Script (.lua)")

def register():
    print("LusExport:Hello cruel world");
    bpy.utils.register_class(ExportLUS)
    bpy.types.INFO_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportLUS)
    print('LusExport: goodbye cruel world');

if __name__ == "__main__":
    register()
    
