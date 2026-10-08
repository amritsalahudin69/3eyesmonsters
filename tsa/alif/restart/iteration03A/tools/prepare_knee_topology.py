import bpy,bmesh,json,os,hashlib,math
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

ROOT=r"C:\Users\HWI-ADMIN\Downloads\3d"
SRC=os.path.join(ROOT,"tsa","alif","restart","iteration02","alif_armature_v1.blend")
OUT=os.path.join(ROOT,"tsa","alif","restart","iteration03A")
COPY=os.path.join(OUT,"alif_topology_v1.blend")
REF=os.path.join(ROOT,"tsa","alif","iteration01","validation")
VAL=os.path.join(OUT,"validation"); LOG=os.path.join(OUT,"logs")
os.makedirs(VAL,exist_ok=True); os.makedirs(LOG,exist_ok=True)
VIEWS={"front":((0,-8.2,2.10),(0,0,2.0)),"three_q_l":((-6.4,-6.4,2.35),(0,0,2.0)),"left":((-8.2,0,2.1),(0,0,2.0)),"back":((0,8.2,2.1),(0,0,2.0)),"right":((8.2,0,2.1),(0,0,2.0)),"three_q_r":((6.4,-6.4,2.35),(0,0,2.0))}
LEGS=('LEG_L_SUIT','LEG_R_SUIT'); BAND_HALF=.06; OFFSETS=(-.06,-.03,0,.03,.06); TARGET_SPACING=.04

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for x in iter(lambda:f.read(1048576),b''): h.update(x)
 return h.hexdigest()
def dump(n,d):
 with open(os.path.join(OUT,n),'w',encoding='utf8') as f: json.dump(d,f,indent=2,allow_nan=False)
def flat(m): return [float(m[r][c]) for r in range(4) for c in range(4)]
def snapshot():
 out={}
 for o in bpy.data.objects:
  x={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'matrix_world':flat(o.matrix_world),'location':list(map(float,o.location)),'rotation_euler':list(map(float,o.rotation_euler)),'scale':list(map(float,o.scale)),'dimensions':list(map(float,o.dimensions))}
  if o.type=='MESH': x.update(vertex_count=len(o.data.vertices),edge_count=len(o.data.edges),polygon_count=len(o.data.polygons))
  out[o.name]=x
 return out
def armature_snapshot(r):
 return {'matrix_world':flat(r.matrix_world),'bones':{b.name:{'head':list(map(float,b.head_local)),'tail':list(map(float,b.tail_local)),'matrix_local':flat(b.matrix_local),'parent':b.parent.name if b.parent else None} for b in r.data.bones}}
def point_camera(loc,target):
 c=bpy.data.objects['TSA_CAMERA']; c.location=loc; c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=c
def image(p):
 im=bpy.data.images.load(p,check_existing=False); x=(list(im.size),list(im.pixels)); bpy.data.images.remove(im); return x
def compare(a,b):
 sa,pa=image(a); sb,pb=image(b)
 if sa!=sb:return {'dimensions_actual':sa,'dimensions_reference':sb,'mean_pixel_difference':1.0,'max_pixel_difference':1.0,'pass':False}
 d=[abs(x-y) for x,y in zip(pa,pb)]; mean=sum(d)/len(d); mx=max(d); return {'dimensions':sa,'mean_pixel_difference':mean,'max_pixel_difference':mx,'pass':mean<=.0005 and mx<=.01}
def render_set(prefix):
 s=bpy.context.scene; s.render.engine='BLENDER_EEVEE'; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.film_transparent=False; out={}
 for n,(loc,target) in VIEWS.items():
  point_camera(loc,target); p=os.path.join(VAL,f'{prefix}_{n}.png'); s.render.filepath=p; bpy.ops.render.render(write_still=True); out[n]=compare(p,os.path.join(REF,f'alif_{n}.png'))
 return out
def knee_z(side):
 # Accepted joint is THIGH tail == SHIN head.
 a=RIG.matrix_world@RIG.data.bones[f'THIGH.{side}'].tail_local; b=RIG.matrix_world@RIG.data.bones[f'SHIN.{side}'].head_local
 if (a-b).length>1e-8: raise RuntimeError('Knee landmark discontinuity')
 return float((a.z+b.z)*.5)
def z_metrics(o,k):
 zs=sorted(float((o.matrix_world@v.co).z) for v in o.data.vertices); band=sorted(z for z in zs if k-BAND_HALF-1e-7<=z<=k+BAND_HALF+1e-7); unique=sorted(set(round(z,6) for z in band)); samples=[k-BAND_HALF]+unique+[k+BAND_HALF]; gaps=[b-a for a,b in zip(samples,samples[1:])]
 return {'vertex_count':len(o.data.vertices),'edge_count':len(o.data.edges),'polygon_count':len(o.data.polygons),'knee_center':k,'blend_band':[k-BAND_HALF,k+BAND_HALF],'vertices_inside_knee_band':len(band),'unique_longitudinal_samples':unique,'maximum_spacing_inside_band':max(gaps) if gaps else 2*BAND_HALF,'vertices_above_knee':sum(k+.01<z<=k+BAND_HALF+1e-7 for z in zs),'vertices_at_knee':sum(abs(z-k)<=.01 for z in zs),'vertices_below_knee':sum(k-BAND_HALF-1e-7<=z<k-.01 for z in zs)}
def original_surface(o):
 vs=[v.co.copy() for v in o.data.vertices]; polys=[tuple(p.vertices) for p in o.data.polygons]; return vs,BVHTree.FromPolygons(vs,polys,all_triangles=False)
def patch_leg(o,k):
 original=[v.co.copy() for v in o.data.vertices]; original_count=len(original); surf,bvh=original_surface(o); inv=o.matrix_world.inverted(); normal=(o.matrix_world.to_3x3().transposed()@Vector((0,0,1))).normalized()
 bm=bmesh.new(); bm.from_mesh(o.data)
 for offset in OFFSETS:
  co=inv@Vector((0,0,k+offset)); bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=normal,use_snap_center=False,clear_outer=False,clear_inner=False)
 bm.normal_update(); bm.to_mesh(o.data); bm.free(); o.data.update()
 # Every old coordinate must still exist exactly (index order is not assumed).
 tree=KDTree(len(o.data.vertices))
 for v in o.data.vertices: tree.insert(v.co,v.index)
 tree.balance(); ds=[tree.find(p)[2] for p in original]; moved=sum(d>1e-9 for d in ds); maxmove=max(ds)
 # Identify genuinely new coordinates by matching old coordinate KD-tree.
 oldtree=KDTree(len(original))
 for i,p in enumerate(original): oldtree.insert(p,i)
 oldtree.balance(); new=[]
 for v in o.data.vertices:
  if oldtree.find(v.co)[2]>1e-9:new.append(v)
 surface_dist=[]; outside=0
 for v in new:
  near=bvh.find_nearest(v.co); d=float(near[3]) if near else float('inf'); surface_dist.append(d)
  wz=(o.matrix_world@v.co).z; outside+=not(k-BAND_HALF-1e-6<=wz<=k+BAND_HALF+1e-6)
 return {'original_vertex_count':original_count,'new_vertex_count':len(new),'original_vertices_moved_count':moved,'max_original_vertex_displacement':maxmove,'max_new_vertex_distance_to_original_surface':max(surface_dist) if surface_dist else 0.0,'new_vertices_outside_knee_band':outside}
def max_transform_delta(a,b):
 best=0
 for n in a:
  for key in ('matrix_world','location','rotation_euler','scale','dimensions'):best=max(best,max(abs(x-y) for x,y in zip(a[n][key],b[n][key])))
 return best

source_before=sha(SRC); copy_initial=sha(COPY); O=bpy.data.objects; RIG=O.get('ALIF_RIG')
if not RIG or len(RIG.data.bones)!=27:raise RuntimeError('Accepted ALIF_RIG missing')
pre=render_set('prepatch')
if not all(x['pass'] for x in pre.values()):
 dump('alif_iteration03A_report.json',{'iteration':'3R-A','status':'BLOCKED','blockers':['PREPATCH_VISUAL_MISMATCH'],'prepatch_visual':pre}); raise RuntimeError('PREPATCH_VISUAL_MISMATCH')
before=snapshot(); arm_before=armature_snapshot(RIG); kz={'L':knee_z('L'),'R':knee_z('R')}
if abs(kz['L']-.54)>.02 or abs(kz['R']-.54)>.02:raise RuntimeError('Knee landmark inconsistent with proven blocker')
metrics_before={n:z_metrics(O[n],kz[n.split('_')[1]]) for n in LEGS}
patch={n:patch_leg(O[n],kz[n.split('_')[1]]) for n in LEGS}
metrics_after={n:z_metrics(O[n],kz[n.split('_')[1]]) for n in LEGS}
post=render_set('postpatch'); after=snapshot(); arm_after=armature_snapshot(RIG); source_after=sha(SRC)

transform_delta=max_transform_delta(before,after); parents_changed=sum(before[n]['parent']!=after[n]['parent'] for n in before); transforms_changed=sum(any(abs(x-y)>1e-8 for key in ('matrix_world','location','rotation_euler','scale','dimensions') for x,y in zip(before[n][key],after[n][key])) for n in before)
other_mesh_changes=[]
for n,x in before.items():
 if x['type']=='MESH' and n not in LEGS and any(x[k]!=after[n][k] for k in ('vertex_count','edge_count','polygon_count')):other_mesh_changes.append(n)
leg_changed=all(metrics_after[n]['vertex_count']>metrics_before[n]['vertex_count'] for n in LEGS)
ready=all(metrics_after[n]['vertices_inside_knee_band']>0 and metrics_after[n]['vertices_above_knee']>0 and metrics_after[n]['vertices_at_knee']>0 and metrics_after[n]['vertices_below_knee']>0 and metrics_after[n]['maximum_spacing_inside_band']<=TARGET_SPACING+1e-6 for n in LEGS)
symmetry=(metrics_after['LEG_L_SUIT']['vertex_count']==metrics_after['LEG_R_SUIT']['vertex_count'] and metrics_after['LEG_L_SUIT']['edge_count']==metrics_after['LEG_R_SUIT']['edge_count'] and metrics_after['LEG_L_SUIT']['polygon_count']==metrics_after['LEG_R_SUIT']['polygon_count'] and abs(metrics_after['LEG_L_SUIT']['maximum_spacing_inside_band']-metrics_after['LEG_R_SUIT']['maximum_spacing_inside_band'])<=1e-6)
armature_same=arm_before==arm_after; original_fixed=all(patch[n]['original_vertices_moved_count']==0 and patch[n]['max_original_vertex_displacement']<=1e-9 for n in LEGS); surface_ok=all(patch[n]['max_new_vertex_distance_to_original_surface']<=1e-6 and patch[n]['new_vertices_outside_knee_band']==0 for n in LEGS)
post_ok=all(x['pass'] for x in post.values()); arm_mods=sum(m.type=='ARMATURE' for o in O if o.type=='MESH' for m in o.modifiers); weights=sum(len(o.vertex_groups) for o in O if o.type=='MESH'); constraints=sum(len(p.constraints) for p in RIG.pose.bones); actions=len(bpy.data.actions); drivers=sum(len(o.animation_data.drivers) if o.animation_data else 0 for o in O)
contract={'iteration':'3R-A','allowed_modified_objects':list(LEGS),'knee_centers':kz,'knee_blend_half_width':BAND_HALF,'insertion_offsets':list(OFFSETS),'target_maximum_spacing':TARGET_SPACING,'topology_method':'five local bmesh bisect-plane loop insertions per leg; no global subdivision or remesh','surface_preservation_method':'retain all original coordinates; bisect intersections lie on original polygon surface; validate new vertices against original BVH','symmetry_rule':'identical offsets and operation for mirrored leg meshes'}
report={'left':{'before':metrics_before['LEG_L_SUIT'],'after':metrics_after['LEG_L_SUIT'],'surface_validation':patch['LEG_L_SUIT']},'right':{'before':metrics_before['LEG_R_SUIT'],'after':metrics_after['LEG_R_SUIT'],'surface_validation':patch['LEG_R_SUIT']},'original_vertices_moved_count':sum(patch[n]['original_vertices_moved_count'] for n in LEGS),'max_original_vertex_displacement':max(patch[n]['max_original_vertex_displacement'] for n in LEGS),'other_meshes_modified_count':len(other_mesh_changes),'other_meshes_modified':other_mesh_changes,'armature_change_count':0 if armature_same else 1,'transform_change_count':transforms_changed,'maximum_transform_delta':transform_delta,'parents_changed_count':parents_changed,'prepatch_visual_comparison':pre,'postpatch_visual_comparison':post}
checks={'iteration02R_source_preserved':source_before==source_after,'source_copy_initial_identical':source_before==copy_initial,'prepatch_visual_identity':all(x['pass'] for x in pre.values()),'only_leg_topology_changed':leg_changed and not other_mesh_changes,'original_vertices_unchanged':original_fixed,'new_vertices_on_original_surface':surface_ok,'knee_band_topology_L':ready,'knee_band_topology_R':ready,'knee_gap_L_solved':metrics_after['LEG_L_SUIT']['maximum_spacing_inside_band']<=TARGET_SPACING+1e-6,'knee_gap_R_solved':metrics_after['LEG_R_SUIT']['maximum_spacing_inside_band']<=TARGET_SPACING+1e-6,'left_right_symmetry':symmetry,'armature_unchanged':armature_same,'transforms_unchanged':transform_delta<=1e-8 and transforms_changed==0,'parents_unchanged':parents_changed==0,'postpatch_silhouette_preserved':post_ok,'armature_modifiers_zero':arm_mods==0,'weights_zero':weights==0,'constraints_zero':constraints==0,'actions_zero':actions==0,'drivers_zero':drivers==0}
status='PASS' if all(checks.values()) else 'BLOCKED'; blockers=[k for k,v in checks.items() if not v]
iteration={'iteration':'3R-A','character':'ALIF','objective':'local_knee_topology_preparation','status':status,'blockers':blockers,'iteration02R_sha256_before':source_before,'iteration02R_sha256_after':source_after,'copy_initial_sha256':copy_initial,'checks':checks,'binding_performed':False,'deformation_test_performed':False,'automatic_weights_used':False,'global_subdivision_used':False,'remesh_used':False,'visible_robot_geometry_added':False,'actions':actions,'constraints':constraints,'ik':sum(c.type=='IK' for p in RIG.pose.bones for c in p.constraints)}
dump('alif_topology_contract.json',contract); dump('alif_topology_report.json',report); dump('alif_iteration03A_report.json',iteration)
with open(os.path.join(LOG,'run.log'),'w',encoding='utf8') as f:f.write(json.dumps({'status':status,'blockers':blockers,'checks':checks},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=COPY)
print('TSA_ITERATION_3R_A',status,blockers)
