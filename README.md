blender2lus
===========

Springrts Lua Unit Script (LUS) Export addon for Blender 

Description
==========
This is a simple Blender addon that allows one to export animations created in Blender (provided they obey a long list of caveats and requirements) as SpringRTS Lua Unit Scripts in a fairly modular way.

Installing
==========
**1)** Paste the io_anim_lus folder into your blender's scripts/addons directory

**2)** Enable the addon in blender

**3)** ???

**4)** PROFIT

Using
=====
**1) Assemble a model** suitable for import by Spring's Assimp. This means, in particular:

* Each animatable piece of the model is a separate object

* You will have to apply all scale and rotation transformations before exporting the model and starting your animation work. Whatever model you use ingame has to perfectly match to what you will be animating on.

* Preferred export format for Spring import is .dae - others might work, but there's little guarantee.

**2) Obsessively change each object's Rotation Mode** in the hidden right pannel (or in object transform properties) to **"Euler ZXY"**.  

* It's possible to do this reasonably fast by posting the following snippet into Blender's Python console:
```
	for i in bpy.data.objects:
	    i.rotation_mode = 'ZXY'
```
 
* If you skip this step, your animations will not be usable. Switching rotation mode on already existing keyframe data does not convert the keyframes automatically, thus ruining the animation.

**3) Create your animation**. *Mind the limitations*.

**4) Hit the export button**! While doing so you can choose between two export modes:

* Save as an animation include. This will only output the animation data, without any additional stuff, ready to be imported into an animation script. This is the default option.

* Save as a main script file. This will create all the framework needed to import and run animations for your unit, as well as the animation itself. Useful only once per unit.

**5) Plug and play** the exported stuff into your greater script's logic. Sadly, exporter won't do all the work for you - it only allows you to separate artwork and programming.

Limitations and bugs
====================
* You absolutely **have** to change every object in your scene into Euler ZXY rotation mode, or untold horrors will plague you.

* Your object names have to be valid Lua variable names, because object names are not validated in any way. Generally, avoid anything containting spaces and punctuation marks.

* You **cannot** have multiple animations per blender file. Blender's Actions system doesn't really accomodate for a horror soup of a dozen objects trying to dance in concert.

* You can only use **Linear** interpolation between your keyframes, because there's no way to implement Bezier in Spring LUS... at least yet.  
Workaround: Use *a lot* of keyframes if you want smooth motion.

* You have to apply scaling transforms before export, and you **cannot use scaling** in your animations. In fact, you're limited to using LocRot.

* Local rotation transforms of each object in model's "bind pose" must be strictly 0,0,0. 

* You **cannot** use inverse kinematics, because you cannot use bones (at least, not without amount of effort making this approach self-defeating. This might be addressed in the future, but don't hold your breath).

* **Any** glaring horror i forgot to add to this readme. There are probably quite a few of those. Watch your step and report on sight.
