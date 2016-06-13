"""
Game generator from project citygen
Reads a .json file generated with citygen.py, and generate a 3D model for the city

Copyright 2014 Jose M. Espadero <josemiguel.espadero@urjc.es>
Copyright 2014 Juan Ramos <juanillo07@gmail.com>

Run option 1:
blender --background --python cityGen3D.py

Run option 2:

Open blender and type this in the python console:
  exec(compile(open("cityGen3D.py").read(), "cityGen3D.py", 'exec'))

"""

import bpy
import math, json, random, os, sys
from math import sqrt, acos, sin, cos
from pprint import pprint
import numpy as np
from mathutils import Vector
from datetime import datetime


# Set a default filename to read configuration
argsFilename = 'cg-config.json'   

#Set default values for args
args={
'cleanLayer1' : True,       # Clean all objects in layer 1
'createGlobalLight' : True,         # Add new light to scene
'inputFilename' : 'city.graph.json',  # Set a filename to read 2D city map data
'inputFilenameAI' : 'city.AI.json',   # Set a filename to read AI data
'internalPointsFileName' : 'cg-internalPoints.json', # Set a filename to write internal points to file.
'inputHouses' : 'cg-library.blend',  # Set a filename for houses library.
'inputPlayerboy' : 'cg-playerBoy.blend',   # Set a filename for player system.
'inputSkyDome': 'cg-skyDomeNight.blend',   # set a filename for a skyDome
'inputMonster' : 'cg-spider.blend',  # Set a filename for monster.
'createDefenseWall' : True,  # Create exterior boundary of the city
'createGround' : True,       # Create ground boundary of the city
'createStreets' : True,      # Create streets of the city
'numMonsters' : 4,
'outputCityFilename' : 'outputcity.blend', #Output file with just the city
'outputTouristFilename' : 'outputtourist.blend', #Output file with complete game
'outputGameFilename' : 'outputgame.blend', #Output file with complete game
}

#Check if there is arguments after '--'
if '--' in sys.argv:
    argv = sys.argv[1+sys.argv.index('--'):]
    print("argv", argv)
    if argv:
        #By now, only use last argument as configuration file
        argsFilename = argv[-1]


#Read options from external file
print("Trying to read options from file: %s" % argsFilename)   
try:
    with open(argsFilename, 'r') as f:
        import json
        args.update(json.load(f))
        #print("Read args:", [x for x in args]);
        for n in args:
            print("  *",n,"=",args[n])
        #Python documentation say NOT to do this :-)
        #globals().update(args)
except IOError:
    print("Could not read file:", argsFilename)
    pass
               
#################################################################
# Functions to create a new cityMap scene (does need run inside blender)

def duplicateObject(sourceObj, objName="copy", select=False, scene=bpy.context.scene):
    """Duplicate a object in the scene.
    sourceObj -- the blender obj to be copied
    objName   -- the name of the new object
    scene     -- the blender scene where the new object will be linked
    """

    # Create new mesh
    #mesh = bpy.data.meshes.new(objName)
    #ob_new = bpy.data.objects.new(objName, mesh)
    #ob_new.data = sourceObj.data.copy()
    #ob_new.scale = sourceObj.scale
    ob_new = sourceObj.copy()

    # Link new object to the given scene and select it
    ob_new.name = objName
    scene.objects.link(ob_new)
    ob_new.select = select

    return ob_new


def duplicateAlongSegment(pt1, pt2, objName, gapSize, force=False):
    """Duplicate an object several times along a path
    pt1 -- First extreme of the path
    pt2 -- Second extreme of the path
    objName -- the name of blender obj to be copied
    gapSize -- Desired space between objects. Will be adjusted to fit path
    """

    #Compute the orientation of segment pt1-pt2
    dx = pt1[0]-pt2[0]
    dy = pt1[1]-pt2[1]

    # return if pt1 == pt2
    if dx == 0 and dy == 0:
        return

    # Compute the angle with the Y-axis
    ang = acos(dy/sqrt((dx**2)+(dy**2)))
    if dx > 0:
        ang = -ang

    # Get the size of the replicated object in the Y dimension
    ob = bpy.data.objects[objName]
    objSize = (ob.bound_box[7][1]-ob.bound_box[0][1])*ob.scale[1]
    totalSize = objSize+gapSize

    # Compute the direction of the segment
    pathVec = Vector(pt2)-Vector(pt1)
    pathLen = pathVec.length
    pathVec.normalize()

    if (objSize > pathLen):
        return

    #if gapSize is not zero, change the gap to one that adjust the object
    #Compute the num of (obj+gap) segments in the interval (pt1-pt2)
    if gapSize != 0:
        numObj = round(pathLen/totalSize)
        step = pathLen/numObj
        stepVec = pathVec * step
        iniPoint = Vector(pt1)+(stepVec * 0.5)
    else:
        numObj = math.floor(pathLen/objSize)
        step = objSize
        stepVec = pathVec * step
        delta = pathLen-step*numObj #xke? (delta es el espacio que falta para completar una fila)
        iniPoint = Vector(pt1)+(stepVec*0.5) #se multiplicaba esto por delta, xke?
        

    #Duplicate the object along the path, numObj times
    iniPoint.resize_3d()
    stepVec.resize_3d()
    if force:
        numObj = numObj - 1
    for i in range(numObj):
        loc = iniPoint + stepVec * i
        g1 = duplicateObject(ob, "_%s" % (objName))
        g1.rotation_euler = (0, 0, ang)
        g1.location = loc
    if force:
            loc = Vector(pt2) - stepVec * 0.5
            g1 = duplicateObject(ob, "_%s" % (objName))
            g1.rotation_euler = (0, 0, ang)
            g1.location = loc
            

 
def knapsack_unbounded_dp(items, C, maxofequalhouse):
    NAME, SIZE, VALUE = range(3)
    # order by max value per item size
    C=int(C*10)
    #print(C)
    #items = sorted(items, key=lambda items: (items[1]), reverse=True)
 
    # Sack keeps track of max value so far as well as the count of each item in the sack
    sack = [(0, [0 for i in items]) for i in range(0, C+1)]   # value, [item counts]
 
    for i,item in enumerate(items):
        name, size, value = item
        for c in range(size, C+1):
            sackwithout = sack[c-size]  # previous max sack to try adding this item to
            trial = sackwithout[0] + value
            used = sackwithout[1][i]
            if sack[c][0] < trial:
                # old max sack with this added item is better
                sackaux=sack[c]
                sack[c] = (trial, sackwithout[1][:])
                if i!= len(items)-1:
                    if sack [c][1][i]<maxofequalhouse:
                        sack[c][1][i] +=1   # use one more
                    else:
                        sack[c]=sackaux 
                        break
                else:
                    sack[c][1][i] +=1
        else:
            continue               
                       
                    
 
    value, bagged = sack[C]
    numbagged = sum(bagged)
    size = sum(items[i][1]*n for i,n in enumerate(bagged))
    # convert to (iten, count) pairs) in name order
    bagged = sorted((items[i][NAME], n) for i,n in enumerate(bagged) if n)
    
    
    return value, size, numbagged, bagged

def knapsack_unbounded_dp_control(pathLen, gapSize, objList=None):
    
    items = []
    for k in objList:
        objName=k
        ob = bpy.data.objects[objName]
        objSize = (ob.bound_box[7][1]-ob.bound_box[0][1])*ob.scale[1]
        totalSize = objSize+gapSize
        item = ((objName, int(totalSize*10), int(totalSize*10)))
        items.append(item)

    maxofequalhouse=20
    """
    fin=False
    x = 0
    while fin!=True:
        x+=1
        fin=True
        if maxofequalhouse!=1:
            a,b,c,d = knapsack_unbounded_dp(items,pathLen,maxofequalhouse)
            for k in d:
                for j in d:
                    if j[1]/k[1]>3:
                        maxofequalhouse -=1
                        fin=False     
                    
        if x==40:
            fin=True
            print(knapsack_unbounded_dp(items,pathLen,maxofequalhouse))
            print(items[0][1])
            print(items[1][1])
            print(items[2][1])
            print("ERRROR")        
    """
    
    #print("House Built")
    #print("value, size, numbagged, bagged")
    #print(knapsack_unbounded_dp(items,pathLen,maxofequalhouse))  
    a,b,c,d = knapsack_unbounded_dp(items,pathLen,maxofequalhouse)
                      
    return d,b

        

            
def duplicateAlongSegmentMix(pt1, pt2, gapSize, objList=None):
    """Duplicate an object several times along a path
    pt1 -- First extreme of the path
    pt2 -- Second extreme of the path
    objName -- the name of blender obj to be copied
    gapSize -- Desired space between objects. Will be adjusted to fit path
    """
    
    
    #if mix==True:
    #    objName = objList[0]
    objName=objList[1]
    mix = True
    force= False
    #Compute the orientation of segment pt1-pt2
    dx = pt1[0]-pt2[0]
    dy = pt1[1]-pt2[1]

    # return if pt1 == pt2
    if dx == 0 and dy == 0:
        return

    # Compute the angle with the Y-axis
    ang = acos(dy/sqrt((dx**2)+(dy**2)))
    if dx > 0:
        ang = -ang
        
    
    # Compute the direction of the segment
    pathVec = Vector(pt2)-Vector(pt1)
    pathLen = pathVec.length
    pathVec.normalize() 
    
   
    list,spaceUsed = knapsack_unbounded_dp_control(pathLen,gapSize,objList)
    objList=[]
    for m in list:
        for n in range(m[1]):
            objList.append(m[0])
    
    random.shuffle(objList)
    delta = (int(pathLen*10)-spaceUsed)/10
    if objList == []:
        return
    delta = delta/len(objList)
    
    iniPoint = Vector(pt1)
   
    for i in objList:
        ob = bpy.data.objects[i]
        objSize = (ob.bound_box[7][1]-ob.bound_box[0][1])*ob.scale[1]
        totalSize = objSize+gapSize+delta
        loc = iniPoint
        g1 = duplicateObject(ob, "_%s" % (objName))
        g1.rotation_euler = (0, 0, ang)
        g1.location = loc
        iniPoint = iniPoint + pathVec * totalSize

def makeGround(cList=[], objName="meshObj", meshName="mesh", radius=10.0, material='Floor3'):
    """Create a polygon to represent the ground around a city 
    cList    -- A list of 3D points with the vertex of the polygon (corners of the city block)
    objName  -- the name of the new object
    meshName -- the name of the new mesh
    radius   -- radius around the city
    """
    print("makeGround", datetime.now().time())
    #Create a mesh and an object
    me = bpy.data.meshes.new(meshName)
    ob = bpy.data.objects.new(objName, me)
    bpy.context.scene.objects.link(ob)  # Link object to scene

    # Fill the mesh with verts, edges, faces
    if cList:
        vectors = [vertices3D[i] for i in cList]
    else:
        #Create a 16-sides polygon centered on (0,0,0)
        step = 2 * math.pi / 16
        vectors = [(sin(step*i) * radius, cos(step*i) * radius, -0.1) for i in range(16)]
    
    me.from_pydata(vectors, [], [tuple(range(len(vectors)))])
    me.update(calc_edges=True)    # Update mesh with new data
    #Assign a material to this object
    me.materials.append(bpy.data.materials[material])



def makePolygon(cList, objName="meshObj", meshName="mesh", height=0.0, reduct=0.0, hide=True):
    """Create a polygon/prism to represent a city block
    cList    -- A list of 3D points with the vertex of the polygon (corners of the city block)
    objName  -- the name of the new object
    meshName -- the name of the new mesh
    height   -- the height of the prism
    reduct   -- a distance to reduce from corner
    """
    print(".", end="")
    
    nv = len(cList)

    #Compute center of voronoi region
    media = [0.0,0.0]
    for v in cList:
        media[0] += v[0]
        media[1] += v[1]
    media[0] /= nv
    media[1] /= nv
    #pprint(media)

    #Compute reduced region coordinates
    cList2 = []
    for i in range(nv):
        dx = cList[i][0]-media[0]
        dy = cList[i][1]-media[1]
        dist = sqrt(dx*dx+dy*dy)
        if dist < reduct:
            cList2.append(cList[i])
        else:
            vecx = reduct * dx / dist
            vecy = reduct * dy / dist
            cList2.append((cList[i][0]-vecx,cList[i][1]-vecy,cList[i][2]))

    # 1. Create a mesh for streets arround this region
    # This is the space between polygons clist and clist2
    me = bpy.data.meshes.new("_Street")
    ob = bpy.data.objects.new("_Street", me)
    streetData = []
    for i in range(nv):
        streetData.append(((i-1) % nv, i, nv+i, nv+(i-1) % nv))
    # pprint(streetData)
    me.from_pydata(cList+cList2, [], streetData)
    me.update(calc_edges=True)
    me.materials.append(bpy.data.materials['Floor1'])
    bpy.context.scene.objects.link(ob)

    # 2. Create a mesh interior of this region
    # This is the space inside polygon clist2
    me = bpy.data.meshes.new("_Region")
    ob = bpy.data.objects.new("_Region", me)
    me.from_pydata(cList2, [], [tuple(range(nv))])
    me.update(calc_edges=True)
    me.materials.append(bpy.data.materials['Floor2'])
    #me.materials.append(bpy.data.materials['Grass'])
    bpy.context.scene.objects.link(ob)

    # 3. Put a tree in the center of the region
    g1 = duplicateObject(bpy.data.objects["Tree"], "_Tree")
    g1.location = (media[0], media[1], 0.0)

    """
    # 4. Put a stone in each corner of the region
    for i in range(len(cList2)):
        g1 = duplicateObject(bpy.data.objects["Stone"], "_Stone%02d"%i)
        g1.location=(cList2[i][0],cList2[i][1],0.0)
    """

    # 5. Fill boundary of region with fences
    for i in range(nv):
        duplicateAlongSegment(cList2[i-1], cList2[i], "Curb", 0.1)
    
    # 6. Create Houses
    
    #Compute new reduced region coordinates
    cList3 = []
    cList4 = []
    reduct = reduct * 6
    for i in range(nv):
        dx = cList[i][0]-media[0]
        dy = cList[i][1]-media[1]
        dist = sqrt(dx*dx+dy*dy)
        if dist < reduct:
            cList3.append(cList[i])
        else:
            vecx = reduct * dx / dist
            vecy = reduct * dy / dist
            vecxM = reduct * 1.5 * dx / dist
            vecyM = reduct * 1.5 * dy / dist
            cList3.append((cList[i][0]-vecx,cList[i][1]-vecy,cList[i][2]))
            cList4.append((cList[i][0]-vecxM,cList[i][1]-vecyM,cList[i][2]))
    
    for i in range(nv):
        duplicateAlongSegmentMix (cList3[i-1], cList3[i], 1 ,("House7", "House3","House4","House5","House6"))
        duplicateAlongSegment(cList4[i-1], cList4[i], "WallHouse", 0, True )



    """
    #Create a mesh for colision
    me = bpy.data.meshes.new(meshName)   # create a new mesh
    ob = bpy.data.objects.new(objName, me) # create an object with that mesh
    bpy.context.scene.objects.link(ob)  # Link object to scene

    # Fill the mesh with verts, edges, faces
    me.from_pydata(cList2,[],[tuple(range(len(cList2)))])   # (0,1,2,3..N)
    me.update(calc_edges=True)    # Update mesh with new data

    #Avoid extrusion if height == 0
    if (not height):
        return

    #Extrude the mesh in the direction of +Z axis
    if (bpy.context.scene.objects.active):
        bpy.context.scene.objects.active.select = False
    bpy.context.scene.objects.active = ob
    ob.select = True
    bpy.ops.object.mode_set(mode = 'EDIT')
    hVec=Vector((0.0,0.0,height))
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":hVec})
    me.update(calc_edges=True)    # Update mesh with new data
    bpy.ops.object.mode_set(mode = 'OBJECT')

    ob.select = False
    #Hide this region
    ob.hide = hide
    """


def UNUSEDmakePath(cList, objName="pathObj", curveName="path", guardian=""):
    """Create a path arround a city block, using a curve.
    cList     -- A list of 3D points with the vertex of the polygon (corners of the city block)
    objName   -- the name of the new object
    curveName -- the name of the new curve
    guardian  -- The name of an object to be copied and configured to walkarround the path
    """

    # BlenderGame use keyframes instead paths
    """
    #Add a curve as path
    curve = bpy.data.curves.new(name=curveName, type='CURVE')
    curve.dimensions = '3D'
    curve.use_path=True

    obj = bpy.data.objects.new(objName, curve)
    obj.location = (0,0,0) #object origin
    bpy.context.scene.objects.link(obj)

    polyline = curve.splines.new('POLY')
    polyline.points.add(len(cList)-1)
    polyline.use_cyclic_u = True # Make a closed curve
    for num in range(len(cList)):
        x, y, z = cList[num]
        polyline.points[num].co = (x, y, z, 1)
    """

    # Add a guardian that walk arround this path
    if (not guardian):
        return

    g1 = duplicateObject(bpy.data.objects[guardian], "_"+guardian)

    # BlenderGame use keyframes instead paths
    """
    #Create the animation data on the path
    if (bpy.context.scene.objects.active):
        bpy.context.scene.objects.active.select = False
    bpy.context.scene.objects.active = g1
    g1.select = True
    #Create a constraint to associate the guardian and the path
    cn=g1.constraints.new(type='FOLLOW_PATH')
    cn.target = obj
    cn.use_curve_follow = True
    bpy.ops.constraint.followpath_path_animate(constraint="Follow Path", owner='OBJECT')
    """
    # TODO:
    # Compute the lenght of the curve and use to set a fixed speed

    g1.animation_data_create()
    g1.animation_data.action = bpy.data.actions.new(name="Animate")
    fcu_x = g1.animation_data.action.fcurves.new(data_path="location", index=0)
    fcu_y = g1.animation_data.action.fcurves.new(data_path="location", index=1)
    fcu_z = g1.animation_data.action.fcurves.new(data_path="location", index=2)
    fcu_x.keyframe_points.add(len(cList))
    fcu_y.keyframe_points.add(len(cList))
    fcu_z.keyframe_points.add(len(cList))
    for i in range(len(cList)):
        x, y, z = cList[i]
        # Fixed 50 frames per side of the path -> g1 will change speed
        # TODO: We should be using the lenght of the side and the path
        frame = 50 * i
        fcu_x.keyframe_points[i].co = frame, x
        fcu_x.keyframe_points[i].handle_left = frame - 1, x
        fcu_x.keyframe_points[i].handle_right = frame + 1, x
        fcu_y.keyframe_points[i].co = frame, y
        fcu_y.keyframe_points[i].handle_left = frame - 1, y
        fcu_y.keyframe_points[i].handle_right = frame + 1, y
        fcu_z.keyframe_points[i].co = frame, z
        fcu_z.keyframe_points[i].handle_left = frame - 1, z
        fcu_z.keyframe_points[i].handle_right = frame + 1, z


def nearestPoint(vList, centerPoint=(0,0) ):
    """Return the position of the point of vlist nearest to centerPoint 
    vlist       -- list of vertex to search
    centerPoint -- Target point of the search
    """    
    #compute the center of the voronoi vertex (average)
    #We search the neares to [0,0]
    #for v in vList:
        #centerPoint[0] += v[0]
        #centerPoint[1] += v[1]
    #centerPoint[0] /= len(vList)
    #centerPoint[1] /= len(vList)
    #print("Center point", centerPoint)
    
    #Search the vertex closest to the center
    meanVertex = None
    minDist = float('Inf')
    for k,v in enumerate(vList):
        dx = v[0]-centerPoint[0]
        dy = v[1]-centerPoint[1]
        dist = dx*dx+dy*dy
        if (dist < minDist):
            meanVertex = k
            minDist = dist
    #print("Nearest vertex to center is at position", meanVertex, ", distance to center", minDist)
    return meanVertex



def importLibrary(filename, link=False, destinationLayer=1, importScripts=False):
    """Import all the objects/assets from an external blender file
    filename -- the name of the blender file to import
    link     -- Choose to copy or link the objects
    destinationLayer  -- The destination layer where to copy the objects
    importScripts -- Choose to import also the scripts (texts) 
    """
    print("Importing objects from file %s" % filename)
    with bpy.data.libraries.load(filename, link=link) as (data_from, data_to):
        #Import all objects
        objNames = [o.name for o in bpy.data.objects]
        for objName in data_from.objects:
            if objName.startswith('_'):
                print('  - Ignore', filename, '->', objName, '(name starts with _)')
            else:
                print('  + Import', filename, '->', objName)
                if objName in objNames:
                    print('Warning: object', objName, 'is already in this file')
                else:
                    data_to.objects.append(objName)
        if importScripts:
            #Import all text/scripts
            textNames = [o.name for o in bpy.data.texts]
            for textName in data_from.texts:
                if textName in textNames:
                    print('  - Warning: script', textName, 'is already in this file')
                else:
                    print('  + Import', filename, '->', textName)
                    data_to.texts.append(textName)
    
    #link to scene, and move to layer destinationLayer
    for o in bpy.data.objects :
        if o.users_scene == () :
            bpy.context.scene.objects.link(o)
            #Set the layer
            if destinationLayer:
                o.layers[destinationLayer] = True
                o.layers[0] = False


def UNUSEDimportPlayer(vList3D, locPlayer):
    """Import the player and game system
    """
    print("Importing game player from %s" % inputPlayerboy)
    with bpy.data.libraries.load(cwd+inputPlayerboy, link=False) as (data_from, data_to):                    
        data_to.objects = [name for name in data_from.objects]
        data_to.texts = [name for name in data_from.texts]

    #link to scene, on current layer
    for o in bpy.data.objects :
        if o.users_scene == () :
            bpy.context.scene.objects.link(o)
            
            
    obj = bpy.data.objects['Player']
    # Set active object operator
    bpy.context.scene.objects.active = obj
    locP = vList3D[locPlayer]
    obj.location = (locP[0],locP[1],0.5)

def UNUSEDdistance2D(p1,p2):
     return sqrt( (p2[0]-p1[0])**2+(p2[1]-p1[1])**2)

def UNUSEDxPositionsFar(vList3D, internal, number):   
    xPos=[]
    for n in internal:
         if vList3D[n]!= (0.0,0.0,0.0):
            xPos.append((vList3D[n][0],vList3D[n][1],n))
    xPos.sort(key=distance, reverse=True)
    
    internalSort = []
    for n in xPos:
         internalSort.append(n[2])
    #print("internal ", internal)
    #print("internal Sort ", internalSort)

    return xPos,internalSort
            
def importMonsters(vList3D, number, xPosFar, filename):    
    saveActiveObject=bpy.context.scene.objects.active
    #TODO: use importLibrary instead...
    for w in range(number):
        monsterVertex = xPosFar[w]
        monsterLocation=(vList3D[monsterVertex][0], vList3D[monsterVertex][1], 1.0)
        print("Importing Monster", w , "from %s"  % filename, "vertex", monsterVertex, "position", monsterLocation )
        #Read from blender file
        with bpy.data.libraries.load(filename, link=False) as (data_from, data_to):
            #data_to.objects = [name for name in data_from.objects]
            objNames = [o.name for o in bpy.data.objects]
            for objName in data_from.objects:
                if objName.startswith('_'):
                    print('  - Ignore', filename, '->', objName, '(name starts with _)')
                else:
                    print('  + Import', filename, '->', objName)
                    if objName in objNames:
                        print('  * Warning: object', objName, 'is already in this file.')
                    data_to.objects.append(objName)
            
            data_to.texts = [name for name in data_from.texts]
        for o in bpy.data.objects :
            if o.users_scene == ():
                bpy.context.scene.objects.link(o)  
        #Configure the monster...
        obj = bpy.data.objects['Monster']
        # Set active object operator
        #bpy.context.scene.objects.active = obj
        obj.location = monsterLocation
        obj.name= 'Monster ' + str(w)
        
        monsterToken = bpy.data.objects['MonsterToken']
        monsterToken.location = monsterLocation
        monsterToken.name= 'MonsterToken ' + str(w)
        bpy.data.texts['initMonster.py'].name = 'initMonster ' + str(w) + '.py'
        if 'debugVisibleTokens' in args:
            monsterToken.hide_render = not args['debugVisibleTokens']


        #Set the name of the monster as a property
        bpy.context.scene.objects.active = obj
        bpy.ops.object.game_property_new(name='monsterName', type='STRING')
        obj.game.properties['monsterName'].value=obj.name

    #Restore old active object
    bpy.context.scene.objects.active=saveActiveObject

        
       
###########################
# The one and only... main
def main():
    # Current time
    iniTime = datetime.now()
    filepath = bpy.data.filepath
    cwd = os.path.dirname(filepath)+'/'
    if cwd == '/':
        cwd = ''
    
    print("Current file: %s" % filepath)
    print("Current dir: %s" % cwd)

    #Ensure configuration of blenderplayer in mode 'GLSL'
    bpy.context.scene.render.engine = 'BLENDER_GAME'
    bpy.context.scene.game_settings.show_fullscreen = True
    bpy.context.scene.game_settings.use_desktop = True
    bpy.context.scene.game_settings.material_mode = 'GLSL'
    #bpy.context.space_data.viewport_shade = 'MATERIAL'
    for a in bpy.data.screens['Default'].areas:
        if a.type == 'VIEW_3D':
            a.spaces[0].viewport_shade = 'MATERIAL'

    
    # Select Layer 0 and clear the scene
    bpy.context.scene.layers[0] = True
    for i in range(1, 20):
        bpy.context.scene.layers[i] = False
        
    if args['cleanLayer1']:
        print("Cleaning Screen, One Second Please")
        #clean objects in layer 0
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        #clean scripts
        for k in bpy.data.texts:
            if '.py' in k.name and 'run-' not in k.name:
                print("Remove script: ", k.name)
                bpy.data.texts.remove(k)
        #clean unused data
        for k in bpy.data.textures:
            if k.users == 0:
                print("Remove texture: ", k.name)
                bpy.data.textures.remove(k)
        for k in bpy.data.materials:
            if k.users == 0:
                print("Remove material: ", k.name)
                bpy.data.materials.remove(k)
        for k in bpy.data.actions:
            if k.users == 0:
                print("Remove action: ", k.name)
                bpy.data.actions.remove(k)

    # This is a hack to give blender a current working directory. If not, it will
    # write several warnings of the type "xxxxx can not make relative"
    print('Saving empty blender model:')
    bpy.ops.wm.save_as_mainfile(filepath=cwd+'empty.blend', compress=False, copy=False)
    os.remove(cwd+'empty.blend')

    # Read point, vertex and regions from a file
    inputFilename = args['inputFilename']
    print("Read data from: %s" % inputFilename)
    with open(cwd+inputFilename, 'r') as f:
        data = json.load(f)
        print("Data:", [x for x in data]);
        if 'name' in data:
            print("City name: %s" % data['name'])
        seeds = data['barrierSeeds']
        vertices = data['vertices']
        regions = data['regions']
        externalPoints = data['externalPoints']

    #Save a copy of input data as a buffer in blend file
    if inputFilename in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts[inputFilename])
    bpy.data.texts.load(inputFilename, True)
    
    #Save a copy of input data AI as a buffer in blend file
    inputFilenameAI = args['inputFilenameAI']
    if inputFilenameAI in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts[inputFilenameAI])
    bpy.data.texts.load(inputFilenameAI, True)
    
    # Convert vertex from 2D to 3D
    vertices3D = []
    for v in vertices:
        vertices3D.append((v[0], v[1], 0.0))

    #This piece of code has been moved to cg-playerBoy.blend//boy-move.py
    #just under reading the .json file. !!!!
    
    #Build list of internal vertex
    internalPoints = [i for i in range(len(vertices)) if i not in externalPoints]
    
    #save as a internal text
    internalPointsFileName = args['internalPointsFileName']
    if internalPointsFileName in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts[internalPointsFileName])
    txt = bpy.data.texts.new(internalPointsFileName)
    txt.from_string((json.dumps(internalPoints)))
    
    
    # Insert a camera and a light in the origin position
    # bpy.ops.object.camera_add(view_align=True, enter_editmode=False, location=(0,0,1.5), rotation=((math.radians(90)), 0, 0))
    # bpy.ops.object.lamp_add(type='SUN', view_align=False, location=(0, 0, 2))

    #Read all the assets for buildings from cg-library
    inputHouses = args['inputHouses']
    importLibrary(cwd+inputHouses, link=False, destinationLayer=1, importScripts=False)

    #Insert global ilumination to scene
    if 'createGlobalLight' in args and args['createGlobalLight']:
        print("Creating Global Light")
        bpy.ops.object.lamp_add(type='SUN', radius=1, view_align=False, location=(0,0,2), rotation=(0,0.175,0))
        bpy.data.lamps[-1].name='ASun1'
        bpy.ops.object.lamp_add(type='SUN', radius=1, view_align=False, location=(0,0,2), rotation=(0,-0.175,0))
        bpy.data.lamps[-1].name='ASun2'
    
    #Insert and scale skyDome
    if 'inputSkyDome' in args and args['inputSkyDome']:
        importLibrary(args['inputSkyDome'], link=False, destinationLayer=0, importScripts=False)
        #Compute the radius of the dome and apply scale
        skyDomeRadius = 50+(np.linalg.norm(vertices, axis=1)).max()
        print("Scaling SkyDome object to radius",skyDomeRadius)
        bpy.data.objects["SkyDome"].scale=(skyDomeRadius, skyDomeRadius, skyDomeRadius/2)

        """ Nice, but still need some configuration
        importLibrary("cg-skyboxshader.blend", link=False, destinationLayer=0, importScripts=True)
        """
       
        """ OK. If you want mist
        #Add mist
        bpy.context.scene.world.mist_settings.use_mist = True
        bpy.context.scene.world.horizon_color = (0.685146, 0.800656, 0.728434)
        #"""
                
    # Exterior boundary of the city
    if 'createDefenseWall' in args and args['createDefenseWall']:
        print("Creating External Boundary of the City, Defense Wall")
        numTowers = len(externalPoints)
        axisX = Vector((1.0, 0.0))
        
        for i in range(numTowers):
            v1 = vertices3D[externalPoints[i-1]]
            v2 = vertices3D[externalPoints[i]]
            v3 = vertices3D[externalPoints[(i+1) % numTowers]]
            v_1_2 = Vector((v1[0]-v2[0], v1[1]-v2[1]))
            v_3_2 = Vector((v3[0]-v2[0], v3[1]-v2[1]))
            # Compute orientation of both walls with axisX
            angL = v_1_2.angle_signed(axisX)
            angR = v_3_2.angle_signed(axisX)
            # Force angR > angL, so force angL < average < angR
            if (angL > angR):
                angR += 6.283185307

            ang = (angL+angR)*0.5
            
            # Place a new tower on point v2
            g1 = duplicateObject(bpy.data.objects["StoneTower"], "_Tower%03d" % i)
            g1.location = (v2[0], v2[1], 0)
            g1.rotation_euler = (0, 0, ang)
            # g1.show_name = True #Debug info
            # Place a new door on point v2, oriented to angL
            g1 = duplicateObject(bpy.data.objects["StoneTowerDoor"], "_Door%03d_A" % i)
            g1.location = (v2[0], v2[1], 0)
            g1.rotation_euler = (0, 0, angL)

            # Place a second door on point v2, oriented to angR
            g1 = duplicateObject(bpy.data.objects["StoneTowerDoor"], "_Door%03d_B" % i)
            g1.location = (v2[0], v2[1], 0)
            g1.rotation_euler = (0, 0, angR)

            # print("New StoneWall section", v1, "->", v2)
            duplicateAlongSegment(v1, v2, "StoneWall", 0.0)

        totalTime = datetime.now()-iniTime
        print("createDefenseWall: Total Time %s" % totalTime)

    # Create a ground around the boundary
    if 'createGround' in args and args['createGround']:
        createGround = args['createGround']
        groundRadius = 50+(np.linalg.norm(vertices, axis=1)).max()
        makeGround([], '_groundO', '_groundM', radius=groundRadius, material='Floor3')

    if 'createStreets' in args and args['createStreets']:
        # Create paths and polygon for internal regions
        print("Creating Districts")
        for region in regions:
            print(".", end="")
            corners = [vertices3D[i] for i in region]
            makePolygon(corners, "houseO", "houseM", height=0.5, reduct=1.0)
        print(".")

    #Save the current file, if outputCityFilename is set.
    if 'outputCityFilename' in args and args['outputCityFilename']:
        outputCityFilename = args['outputCityFilename']
        print('Saving blender model as:', outputCityFilename)
        bpy.ops.wm.save_as_mainfile(filepath=cwd+outputCityFilename, compress=True, copy=False)

    #Import the player system
    if 'inputPlayerboy' in args and args['inputPlayerboy']:
        importLibrary(args['inputPlayerboy'], destinationLayer=0, importScripts=True)

        #locate the object named Player
        player = bpy.data.objects['Player']

        #Calculate the vertex nearest to the center of the city
        playerVertex = nearestPoint(vertices, (0,0) )        
        locP = vertices[playerVertex]+[3.0]
        player.location = locP
        print('Player starts at vertex:', playerVertex, 'position:', locP)
        
        #Inject a new string property to the object
        bpy.context.scene.objects.active = player
        bpy.ops.object.game_property_new(name="playerName", type='STRING')
        player.game.properties['playerName'].value='Juanillo'

        #Inject a string property with a json code that can be parsed by a controller
        bpy.context.scene.objects.active = player
        bpy.ops.object.game_property_new(name="locP.json", type='STRING')
        player.game.properties['locP.json'].value=json.dumps(locP)

        #Inject a new python controller to the object, linked to an existing text
        #This is a trick so BGE can find a text object
        #http://blenderartists.org/forum/showthread.php?226148-reading-text-datablocks-via-python
        #See leeme.txt to find an example to search and parse a complex json-text
        bpy.context.scene.objects.active = player
        bpy.ops.logic.controller_add(name='cg-data.json', type='PYTHON')
        player.game.controllers['cg-data.json'].text = bpy.data.texts[inputFilename]        
        
        #Inject a new python controller to the object, linked to inputFilenameAI
        bpy.context.scene.objects.active = player
        bpy.ops.logic.controller_add(name='cg-ia.json', type='PYTHON')
        player.game.controllers['cg-ia.json'].text = bpy.data.texts[inputFilenameAI]

    #Insert a background music
    if 'backgroundMusic' in args and args['backgroundMusic']:
        backgroundMusic = args['backgroundMusic']
        print('Insert background music file:', backgroundMusic)
        #bpy.ops.sequencer.sound_strip_add(filepath=backgroundMusic, relative_path=True, frame_start=1, channel=1)
        bpy.ops.sound.open(filepath=backgroundMusic, relative_path=True)
        bpy.ops.logic.sensor_add(name='playMusic', type='ALWAYS', object='Player')
        bpy.ops.logic.controller_add(name='playMusic', object='Player')
        bpy.ops.logic.actuator_add(name='playMusic', type='SOUND', object='Player') #Try to link to other object...
        player.game.actuators['playMusic'].sound = bpy.data.sounds[os.path.basename(backgroundMusic)]
        player.game.actuators['playMusic'].mode = 'LOOPEND'
        player.game.controllers['playMusic'].link(sensor=player.game.sensors['playMusic'], actuator=player.game.actuators['playMusic'])

        
    #Save the current file, if outputGameFilename is set.
    if 'outputTouristFilename' in args and args['outputTouristFilename']:
        outputTouristFilename = args['outputTouristFilename']
        print('Saving blender tourist as:', outputTouristFilename)
        bpy.ops.wm.save_as_mainfile(filepath=cwd+outputTouristFilename, compress=True, copy=False)

    #Insert monsters in the city
    numMonsters = 0
    if 'numMonsters' in args:
        numMonsters = args['numMonsters']
            
    if numMonsters > 0:
        AIData={}
        print("Read AI data from: %s" % inputFilenameAI)
        with open(cwd+inputFilenameAI, 'r') as f:
            AIData.update(json.load(f))
            print("AIData:", [x for x in AIData]);
        
            
        print("Choosing starting points for monsters...")
        #print("internalPoints=", internalPoints)
        monsterVertex=[]
        for i in range(numMonsters):
            maxDistance = -1
            maxDistVertex = None
            for v in [n for n in internalPoints if n not in monsterVertex]:
                #Sum of distances from vertex v to every other monster/player
                #distance = sum(AIData["shortestPathMatrix"][v][j] for j in [playerVertex]+monsterVertex)
                #Minimum distance from vertex v to every other monster/player
                distance = min(AIData["shortestPathMatrix"][v][j] for j in [playerVertex]+monsterVertex)
                #Choose the vertex v which maximizes the distance to others
                if distance > maxDistance and distance < float('Inf'):
                    maxDistance = distance
                    maxDistVertex = v

            #print("  + Selected vertex", maxDistVertex, "at distance", maxDistance)
            monsterVertex += [maxDistVertex]
        print("Starting points for monsters", monsterVertex)
        
        #Import monsters...
        importMonsters(vertices3D, numMonsters, monsterVertex, args['inputMonster'])
    
    #Save the current file, if outputGameFilename is set.
    if 'outputGameFilename' in args and args['outputGameFilename']:
        outputGameFilename = args['outputGameFilename']
        print('Saving blender game as:', outputGameFilename)
        bpy.ops.wm.save_as_mainfile(filepath=cwd+outputGameFilename, compress=True, copy=False)
            
    totalTime = (datetime.now()-iniTime).total_seconds()
    print("Regions: %d Total Time: %s " % (len(regions), totalTime))

#Call the main function
main()