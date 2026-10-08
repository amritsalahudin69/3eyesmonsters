import bpy, json, os, math, hashlib, struct
from mathutils import Vector

ROOT = r"C:\Users\HWI-ADMIN\Downloads\3d"
SOURCE = r"C:\Users\HWI-ADMIN\alif_output_v1\alif_v1.blend"
OUT = os.path.join(ROOT, "tsa", "alif", "restart", "iteration02")
COPY = os.path.join(OUT, "alif_armature_v1.blend")
REF = os.path.join(ROOT, "tsa", "alif", "iteration01", "validation")
VAL = os.path.join(OUT, "validation")
LOG = os.path.join(OUT, "logs")
os.makedirs(VAL, exist_ok=True); os.makedirs(LOG, exist_ok=True)

VIEWS = {
    "front": ((0,-8.2,2.10),(0,0,2.0)),
    "three_q_l": ((-6.4,-6.4,2.35),(0,0,2.0)),
    "left": ((-8.2,0,2.1),(0,0,2.0)),
    "back": ((0,8.2,2.1),(0,0,2.0)),
    "right": ((8.2,0,2.1),(0,0,2.0)),
    "three_q_r": ((6.4,-6.4,2.35),(0,0,2.0)),
}

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def write_json(name,data):
    with open(os.path.join(OUT,name),'w',encoding='utf-8') as f: json.dump(data,f,indent=2,allow_nan=False)

def flat_matrix(m): return [float(m[r][c]) for r in range(4) for c in range(4)]

def mesh_hash(obj):
    h=hashlib.sha256()
    for v in obj.data.vertices: h.update(struct.pack('<3d',*map(float,v.co)))
    for e in obj.data.edges: h.update(struct.pack('<2I',*e.vertices))
    for p in obj.data.polygons:
        h.update(struct.pack('<I',len(p.vertices)))
        for i in p.vertices: h.update(struct.pack('<I',i))
    return h.hexdigest()

def snapshot(names):
    out={}
    for name in names:
        o=bpy.data.objects[name]
        out[name]={
            'type':o.type,'parent':o.parent.name if o.parent else None,
            'parent_type':o.parent_type,'parent_bone':o.parent_bone,
            'matrix_parent_inverse':flat_matrix(o.matrix_parent_inverse),
            'matrix_world':flat_matrix(o.matrix_world),'origin_world':list(map(float,o.matrix_world.translation)),
            'location':list(map(float,o.location)),'rotation_mode':o.rotation_mode,
            'rotation_quaternion':list(map(float,o.rotation_quaternion)),
            'rotation_euler':list(map(float,o.rotation_euler)),'scale':list(map(float,o.scale)),
            'dimensions':list(map(float,o.dimensions)),
            'mesh_hash':mesh_hash(o) if o.type=='MESH' else None,
            'vertex_groups':[(g.name,g.index) for g in o.vertex_groups] if o.type=='MESH' else [],
            'modifiers':[(m.name,m.type) for m in o.modifiers],
        }
    return out

def max_numeric_delta(a,b):
    best=0.0
    for n in a:
        for k in ('matrix_parent_inverse','matrix_world','origin_world','location','rotation_quaternion','rotation_euler','scale','dimensions'):
            best=max(best,max(abs(x-y) for x,y in zip(a[n][k],b[n][k])))
    return best

def unchanged(a,b):
    structural=all(a[n]['type']==b[n]['type'] and a[n]['parent']==b[n]['parent'] and a[n]['parent_type']==b[n]['parent_type'] and a[n]['parent_bone']==b[n]['parent_bone'] and a[n]['mesh_hash']==b[n]['mesh_hash'] and a[n]['vertex_groups']==b[n]['vertex_groups'] and a[n]['modifiers']==b[n]['modifiers'] for n in a)
    return structural and max_numeric_delta(a,b)<=1e-8

def point_camera(loc,target):
    cam=bpy.data.objects.get('TSA_CAMERA')
    if cam is None: raise RuntimeError('TSA_CAMERA missing')
    cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=cam

def render_set(prefix):
    scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
    results={}
    for name,(loc,target) in VIEWS.items():
        point_camera(loc,target); scene.render.filepath=os.path.join(VAL,f'{prefix}_{name}.png'); bpy.ops.render.render(write_still=True)
        results[name]=compare(scene.render.filepath,os.path.join(REF,f'alif_{name}.png'))
    return results

def image_data(path):
    im=bpy.data.images.load(path,check_existing=False); size=list(im.size); px=list(im.pixels); bpy.data.images.remove(im); return size,px

def compare(a,b):
    sa,pa=image_data(a); sb,pb=image_data(b)
    if sa!=sb or len(pa)!=len(pb): return {'dimensions_actual':sa,'dimensions_reference':sb,'mean_absolute_difference':1.0,'max_difference':1.0,'pass':False}
    diffs=[abs(x-y) for x,y in zip(pa,pb)]
    mean=sum(diffs)/len(diffs); maximum=max(diffs)
    return {'dimensions':sa,'mean_absolute_difference':mean,'max_difference':maximum,'pass':mean<=0.0005 and maximum<=0.01}

def bounds(name):
    o=bpy.data.objects[name]; pts=[o.matrix_world@Vector(c) for c in o.bound_box]
    return Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))

def center(name):
    a,b=bounds(name); return (a+b)*0.5

def create_armature():
    # Landmarks are derived only from canonical world-space object bounds.
    tc=center('TORSO_UNDER'); tmin,tmax=bounds('TORSO_UNDER'); nc=center('NECK_BRIDGE'); hmin,hmax=bounds('HEAD')
    arm={s:(center('ARM_'+s),bounds('ARM_'+s),center('HAND_'+s),bounds('HAND_'+s)) for s in ('L','R')}
    leg={s:(center('LEG_'+s+'_SUIT'),bounds('LEG_'+s+'_SUIT'),center('FOOT_'+s),bounds('FOOT_'+s)) for s in ('L','R')}
    zground=min(bounds('FOOT_L')[0].z,bounds('FOOT_R')[0].z)
    B={
      'ROOT':((0,0,zground),(0,0,zground+0.2),None,False),
      'COG':((0,0,tc.z-0.12),(0,0,tc.z+0.12),'ROOT',False),
      'PELVIS':((0,0,tmin.z+0.32),(0,0,tc.z),'COG',True),
      'SPINE':((0,0,tc.z),(0,0,tmax.z-0.42),'PELVIS',True),
      'CHEST':((0,0,tmax.z-0.42),(0,0,tmax.z-0.08),'SPINE',True),
      'NECK':((nc.x,nc.y,nc.z-0.20),(nc.x,nc.y,nc.z+0.20),'CHEST',True),
      'HEAD':((0,0,hmin.z+0.15),(0,0,hmax.z-0.25),'NECK',True),
    }
    for s in ('L','R'):
        ac,(amin,amax),hc,(hmn,hmx)=arm[s]; inner=0.30 if ac.x>0 else -0.30; joint=(ac.x,ac.y,amax.z-0.18); elbow=(ac.x,ac.y,(amin.z+amax.z)*0.5); wrist=(ac.x,ac.y,amin.z+0.15); hand_top=(hc.x,hc.y,hc.z)
        B.update({f'SHOULDER.{s}':((inner,ac.y,joint[2]),joint,'CHEST',True),f'UPPER_ARM.{s}':(joint,elbow,f'SHOULDER.{s}',True),f'FOREARM.{s}':(elbow,wrist,f'UPPER_ARM.{s}',True),f'WRIST.{s}':(wrist,hand_top,f'FOREARM.{s}',True),f'HAND.{s}':(hand_top,(hc.x,hc.y,hmn.z+0.10),f'WRIST.{s}',True)})
    for s in ('L','R'):
        lc,(lmin,lmax),fc,(fmin,fmax)=leg[s]; inner=0.18 if lc.x>0 else -0.18; hip=(lc.x,lc.y,lmax.z-0.10); knee=(lc.x,lc.y,(lmin.z+lmax.z)*0.5); ankle=(lc.x,lc.y,lmin.z+0.10); footbase=(fc.x,fc.y,fmax.z-0.08)
        B.update({f'HIP.{s}':((inner,lc.y,hip[2]),hip,'PELVIS',True),f'THIGH.{s}':(hip,knee,f'HIP.{s}',True),f'SHIN.{s}':(knee,ankle,f'THIGH.{s}',True),f'ANKLE.{s}':(ankle,footbase,f'SHIN.{s}',True),f'FOOT.{s}':(footbase,(fc.x,fmin.y+0.10,fc.z),f'ANKLE.{s}',True)})
    data=bpy.data.armatures.new('ALIF_RIG'); rig=bpy.data.objects.new('ALIF_RIG',data); bpy.context.collection.objects.link(rig); rig.hide_render=True; rig.show_in_front=True
    bpy.context.view_layer.objects.active=rig; rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
    made={}
    for name,(head,tail,parent,deform) in B.items():
        b=data.edit_bones.new(name); b.head=head; b.tail=tail; b.use_deform=deform; made[name]=b
        if parent: b.parent=made[parent]
    bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False)
    return rig,B

source_before=sha256(SOURCE); copy_initial=sha256(COPY); names=sorted(o.name for o in bpy.data.objects)
pre=render_set('pre_rig')
if not all(v['pass'] for v in pre.values()):
    write_json('alif_iteration02R_report.json',{'iteration':'2R','status':'BLOCKED','blockers':['PRE_RIG_VISUAL_MISMATCH'],'canonical_input':SOURCE,'canonical_iter1_sha256_before':source_before,'copy_initial_sha256':copy_initial,'source_copy_initial_identical':source_before==copy_initial,'pre_rig_comparison':pre})
    raise RuntimeError('PRE_RIG_VISUAL_MISMATCH')

before=snapshot(names); write_json('alif_iter1_object_snapshot_before.json',before)
rig,landmarks=create_armature()
after=snapshot(names); write_json('alif_iter1_object_snapshot_after.json',after)
post=render_set('post_rig'); source_after=sha256(SOURCE)

hierarchy={n:v[2] for n,v in landmarks.items()}; symmetry=True
for base in ('SHOULDER','UPPER_ARM','FOREARM','WRIST','HAND','HIP','THIGH','SHIN','ANKLE','FOOT'):
    l=landmarks[base+'.L']; r=landmarks[base+'.R']
    symmetry &= all(abs(l[i][0]+r[i][0])<=1e-6 and abs(l[i][1]-r[i][1])<=1e-6 and abs(l[i][2]-r[i][2])<=1e-6 for i in (0,1))

arm_modifiers=sum(1 for n in names for m in bpy.data.objects[n].modifiers if m.type=='ARMATURE')
vertex_groups_after=sum(len(bpy.data.objects[n].vertex_groups) for n in names if bpy.data.objects[n].type=='MESH')
vertex_groups_before=sum(len(before[n]['vertex_groups']) for n in names if before[n]['type']=='MESH')
constraints=sum(len(p.constraints) for p in rig.pose.bones); actions=len(bpy.data.actions); drivers=sum(len(o.animation_data.drivers) if o.animation_data else 0 for o in bpy.data.objects)
parents_ok=all(before[n]['parent']==after[n]['parent'] and before[n]['parent_type']==after[n]['parent_type'] and before[n]['parent_bone']==after[n]['parent_bone'] for n in names)
matrix_delta=max(max(abs(x-y) for x,y in zip(before[n]['matrix_world'],after[n]['matrix_world'])) for n in names)
origins_ok=all(max(abs(x-y) for x,y in zip(before[n]['origin_world'],after[n]['origin_world']))<=1e-8 for n in names)
mesh_ok=all(before[n]['mesh_hash']==after[n]['mesh_hash'] for n in names if before[n]['type']=='MESH')
post_ok=all(v['pass'] for v in post.values()); transforms_ok=unchanged(before,after)
bone_count=len(rig.data.bones); armature_count=sum(o.type=='ARMATURE' for o in bpy.data.objects)

landmark_json=[]
for n,(h,t,p,d) in landmarks.items(): landmark_json.append({'name':n,'head':list(map(float,h)),'tail':list(map(float,t)),'parent':p,'use_deform':d,'placement_source':'canonical Iteration 1 object bounds'})
contract={'character':'ALIF','iteration':'2R','armature_object':'ALIF_RIG','bone_count':bone_count,'bones':list(landmarks),'hierarchy':hierarchy,'coordinate_system':{'front':'-Y','up':'+Z','symmetry':'X=0'},'symmetry_valid':bool(symmetry),'binding':False,'armature_modifiers':arm_modifiers,'new_deformation_vertex_groups':vertex_groups_after-vertex_groups_before,'constraints':constraints,'ik':0,'drivers':drivers,'actions':actions}
write_json('alif_armature_contract.json',contract); write_json('alif_bone_landmarks.json',landmark_json)

checks={'canonical_source_preserved':source_before==source_after,'source_copy_initial_hash_identical':source_before==copy_initial,'pre_rig_visual_matches':all(v['pass'] for v in pre.values()),'armature_count_one':armature_count==1,'primary_bones_27':bone_count==27,'hierarchy_complete':all((p is None or p in landmarks) for p in hierarchy.values()),'symmetry_valid':bool(symmetry),'existing_parents_unchanged':parents_ok,'existing_matrix_world_unchanged':matrix_delta<=1e-8,'origins_unchanged':origins_ok,'mesh_geometry_unchanged':mesh_ok,'all_existing_state_unchanged':transforms_ok,'post_rig_visual_matches':post_ok,'armature_modifiers_zero':arm_modifiers==0,'new_vertex_groups_zero':vertex_groups_after==vertex_groups_before,'constraints_zero':constraints==0,'drivers_zero':drivers==0,'actions_zero':actions==0}
status='PASS' if all(checks.values()) else 'BLOCKED'; blockers=[k for k,v in checks.items() if not v]
report={'iteration':'2R','character':'ALIF','objective':'repository_knowledge_and_clone_only_internal_armature','status':status,'blockers':blockers,'canonical_input':SOURCE,'canonical_iter1_sha256_before':source_before,'canonical_iter1_sha256_after':source_after,'copy_initial_sha256':copy_initial,'environment':{'agent':'WSL Ubuntu 24.04','blender':'Windows-native Blender 5.2','windows_root':ROOT,'wsl_root':'/mnt/c/Users/HWI-ADMIN/Downloads/3d/'},'blender_version':bpy.app.version_string,'checks':checks,'existing_object_max_numeric_delta':max_numeric_delta(before,after),'existing_matrix_world_max_delta':matrix_delta,'pre_rig_comparison':pre,'post_rig_comparison':post,'armature_contract':'alif_armature_contract.json','bone_landmarks':'alif_bone_landmarks.json'}
write_json('alif_iteration02R_report.json',report)
with open(os.path.join(LOG,'run.log'),'w',encoding='utf-8') as f: f.write(json.dumps({'status':status,'blockers':blockers,'checks':checks},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=COPY)
print('TSA_ITERATION_2R',status,blockers)
