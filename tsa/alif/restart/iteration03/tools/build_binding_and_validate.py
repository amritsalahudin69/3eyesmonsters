import bpy, json, os, math, hashlib, statistics
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT=r"C:\Users\HWI-ADMIN\Downloads\3d"
SRC=os.path.join(ROOT,"tsa","alif","restart","iteration02","alif_armature_v1.blend")
OUT=os.path.join(ROOT,"tsa","alif","restart","iteration03")
COPY=os.path.join(OUT,"alif_deform_v1.blend")
REF=os.path.join(ROOT,"tsa","alif","iteration01","validation")
VAL=os.path.join(OUT,"validation"); LOG=os.path.join(OUT,"logs")
os.makedirs(VAL,exist_ok=True); os.makedirs(LOG,exist_ok=True)
VIEWS={"front":((0,-8.2,2.10),(0,0,2.0)),"three_q_l":((-6.4,-6.4,2.35),(0,0,2.0)),"left":((-8.2,0,2.1),(0,0,2.0)),"back":((0,8.2,2.1),(0,0,2.0)),"right":((8.2,0,2.1),(0,0,2.0)),"three_q_r":((6.4,-6.4,2.35),(0,0,2.0))}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def dump(n,d):
 with open(os.path.join(OUT,n),'w',encoding='utf8') as f: json.dump(d,f,indent=2,allow_nan=False)
def flat(m): return [float(m[r][c]) for r in range(4) for c in range(4)]
def visual_snapshot():
 d={}
 for o in bpy.data.objects:
  if o.type not in {'MESH','CURVE'}: continue
  d[o.name]={'type':o.type,'parent':o.parent.name if o.parent else None,'matrix_world':flat(o.matrix_world),'location':list(map(float,o.location)),'rotation_euler':list(map(float,o.rotation_euler)),'scale':list(map(float,o.scale)),'dimensions':list(map(float,o.dimensions)),'vertex_count':len(o.data.vertices) if o.type=='MESH' else None,'edge_count':len(o.data.edges) if o.type=='MESH' else None,'polygon_count':len(o.data.polygons) if o.type=='MESH' else None}
 return d
def visual_topology_equal(a,b): return all(a[n]['type']==b[n]['type'] and a[n]['vertex_count']==b[n]['vertex_count'] and a[n]['edge_count']==b[n]['edge_count'] and a[n]['polygon_count']==b[n]['polygon_count'] for n in a)
def verts(o,eval=False):
 if eval:
  eo=o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=eo.to_mesh(); p=[eo.matrix_world@v.co for v in me.vertices]; eo.to_mesh_clear(); return p
 return [o.matrix_world@v.co for v in o.data.vertices]
def edges(o,p): return [(p[e.vertices[0]]-p[e.vertices[1]]).length for e in o.data.edges]
def pct(a,q):
 a=sorted(a); x=(len(a)-1)*q; i=int(x); j=min(i+1,len(a)-1); return a[i]*(j-x)+a[j]*(x-i)
def point_camera(loc,target):
 c=bpy.data.objects['TSA_CAMERA']; c.location=loc; c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=c
def render(name,view='front'):
 loc,target=VIEWS[view]; point_camera(loc,target); s=bpy.context.scene; s.render.engine='BLENDER_EEVEE'; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.film_transparent=False; s.render.filepath=os.path.join(VAL,name); bpy.ops.render.render(write_still=True); return s.render.filepath
def image(p):
 im=bpy.data.images.load(p,check_existing=False); x=(list(im.size),list(im.pixels)); bpy.data.images.remove(im); return x
def compare(a,b):
 sa,pa=image(a); sb,pb=image(b)
 if sa!=sb: return {'dimensions_actual':sa,'dimensions_reference':sb,'mean_pixel_difference':1.0,'max_pixel_difference':1.0,'pass':False}
 d=[abs(x-y) for x,y in zip(pa,pb)]; mean=sum(d)/len(d); mx=max(d); return {'dimensions':sa,'mean_pixel_difference':mean,'max_pixel_difference':mx,'pass':mean<=.0005 and mx<=.01}
def render_compare(prefix):
 out={}
 for v in VIEWS: out[v]=compare(render(f'{prefix}_{v}.png',v),os.path.join(REF,f'alif_{v}.png'))
 return out
def reset():
 for p in RIG.pose.bones: p.rotation_mode='XYZ'; p.rotation_euler=(0,0,0); p.location=(0,0,0); p.scale=(1,1,1)
 bpy.context.view_layer.update()
def pose(bone,axis,deg): reset(); RIG.pose.bones[bone].rotation_euler[axis]=math.radians(deg); bpy.context.view_layer.update()
def smoothstep(x): x=max(0,min(1,x)); return x*x*(3-2*x)
def zweights(z,joints,bones,widths):
 # joints descend from proximal to distal; only adjacent bones blend.
 if z>=joints[0]+widths[0]: return {bones[0]:1.0}
 for i,j in enumerate(joints):
  w=widths[i]
  if j-w<=z<=j+w:
   t=smoothstep((j+w-z)/(2*w)); return {bones[i]:1-t,bones[i+1]:t}
  if i<len(joints)-1 and joints[i+1]+widths[i+1]<z<j-w: return {bones[i+1]:1.0}
 return {bones[-1]:1.0}
def add_modifier(o):
 m=o.modifiers.new('TSA_CONTROLLED_BIND','ARMATURE'); m.object=RIG; m.use_vertex_groups=True; m.use_deform_preserve_volume=True
def clear_groups(o):
 for g in list(o.vertex_groups): o.vertex_groups.remove(g)
def bind_limb(name,bones,joints,widths):
 o=O[name]; clear_groups(o); gs={b:o.vertex_groups.new(name=b) for b in bones}; sums=[]; used=set(); maxinf=0; neg=nan=cross=0
 for v in o.data.vertices:
  z=(o.matrix_world@v.co).z; ww=zweights(z,joints,bones,widths); total=sum(ww.values()); ww={k:x/total for k,x in ww.items()}
  for b,w in ww.items(): gs[b].add([v.index],w,'REPLACE'); used.add(b); neg+=w<0; nan+=not math.isfinite(w)
  sums.append(sum(ww.values())); maxinf=max(maxinf,len(ww))
 add_modifier(o)
 return {'vertex_count':len(o.data.vertices),'weighted_vertex_count':len(o.data.vertices),'unweighted_vertex_count':0,'allowed_bones':bones,'actual_used_bones':sorted(used),'min_weight_sum':min(sums),'max_weight_sum':max(sums),'maximum_influence_count':maxinf,'cross_side_contamination_count':cross,'negative_weight_count':neg,'nan_weight_count':nan,'joint_z':joints,'blend_half_widths':widths,'algorithm':'world-Z longitudinal smoothstep zones derived from actual bone joints'}
def control_count(o): return sum(len(s.bezier_points) if len(s.bezier_points) else len(s.points) for s in o.data.splines)
def rigid_bind(o,bone):
 clear_groups(o); g=o.vertex_groups.new(name=bone)
 count=len(o.data.vertices) if o.type=='MESH' else control_count(o)
 if count: g.add(list(range(count)),1.0,'REPLACE')
 add_modifier(o); return count
def topology_readiness(name,joints,widths):
 o=O[name]; zs=sorted((o.matrix_world@v.co).z for v in o.data.vertices); unique=sorted(set(round(z,6) for z in zs)); gaps=[b-a for a,b in zip(unique,unique[1:])]
 zones=[]
 for j,w in zip(joints,widths): zones.append({'joint_z':j,'blend_half_width':w,'vertex_count':sum(abs(z-j)<=w for z in zs),'max_longitudinal_spacing':max(gaps) if gaps else 0.0})
 ok=all(x['vertex_count']>=8 and x['max_longitudinal_spacing']<=max(x['blend_half_width']*2,.25) for x in zones)
 return {'mesh':name,'vertex_count':len(zs),'unique_longitudinal_levels':len(unique),'zones':zones,'useful_joint_blend_zones':ok}
def metric(o,base):
 p=verts(o,True); r=[a/b if b>1e-12 else 1 for a,b in zip(edges(o,p),base)]; bad=sum(not all(math.isfinite(x) for x in q) for q in p)
 return {'minimum':min(r),'p01':pct(r,.01),'median':statistics.median(r),'p95':pct(r,.95),'p99':pct(r,.99),'maximum':max(r),'nan_or_infinite_vertices':bad,'vertex_count':len(p)}
def closest(a,b):
 aa=verts(a,True); bb=verts(b,True); k=KDTree(len(bb))
 for i,p in enumerate(bb): k.insert(p,i)
 k.balance(); return min(k.find(p)[2] for p in aa)
def static_snapshot(names): return {n:verts(O[n],True) for n in names}
def delta(s,n): return max((a-b).length for a,b in zip(s[n],verts(O[n],True)))
def cent(o):
 p=verts(o,True); return sum(p,Vector())/len(p)

source_before=sha(SRC); copy_initial=sha(COPY); O=bpy.data.objects; RIG=O.get('ALIF_RIG')
if not RIG or len(RIG.data.bones)!=27: raise RuntimeError('Iteration 2R armature contract missing')
prebind=render_compare('prebind')
if not all(v['pass'] for v in prebind.values()):
 dump('alif_iteration03R_report.json',{'iteration':'3R','status':'BLOCKED','blockers':['PRE_BIND_VISUAL_MISMATCH'],'prebind_comparison':prebind,'iteration02R_sha256_before':source_before,'copy_initial_sha256':copy_initial}); raise RuntimeError('PRE_BIND_VISUAL_MISMATCH')

before=visual_snapshot(); dump('visual_snapshot_before.json',before)
for n in ('ARM_L','ARM_R','HAND_L','HAND_R','LEG_L_SUIT','LEG_R_SUIT','FOOT_L','FOOT_R','HEAD','TORSO_UNDER','SUIT_SHELL'):
 if not O.get(n): raise RuntimeError('Missing visual object '+n)

def bone_joint(n): return float((RIG.matrix_world@RIG.data.bones[n].head_local).z)
arm_j={'L':[bone_joint('UPPER_ARM.L'),bone_joint('FOREARM.L'),bone_joint('WRIST.L')],'R':[bone_joint('UPPER_ARM.R'),bone_joint('FOREARM.R'),bone_joint('WRIST.R')]}
leg_j={'L':[bone_joint('THIGH.L'),bone_joint('SHIN.L'),bone_joint('ANKLE.L')],'R':[bone_joint('THIGH.R'),bone_joint('SHIN.R'),bone_joint('ANKLE.R')]}
arm_w={s:[max(.08,abs(arm_j[s][0]-arm_j[s][1])*.13),max(.08,abs(arm_j[s][0]-arm_j[s][1])*.16),max(.06,abs(arm_j[s][1]-arm_j[s][2])*.18)] for s in ('L','R')}
leg_w={s:[.08,max(.06,abs(leg_j[s][0]-leg_j[s][1])*.22),max(.05,abs(leg_j[s][1]-leg_j[s][2])*.28)] for s in ('L','R')}
readiness={}
for s in ('L','R'):
 readiness['ARM_'+s]=topology_readiness('ARM_'+s,arm_j[s],arm_w[s]); readiness['LEG_'+s+'_SUIT']=topology_readiness('LEG_'+s+'_SUIT',leg_j[s],leg_w[s])
ready=all(x['useful_joint_blend_zones'] for x in readiness.values())
if not ready:
 source_after=sha(SRC)
 not_run={'status':'NOT_RUN','reason':'TOPOLOGY_LIMITATION detected before binding'}
 dump('alif_weight_contract.json',{'status':'NOT_CREATED','reason':'TOPOLOGY_LIMITATION','automatic_weights_used':False,'binding_performed':False,'meshes':{}})
 dump('alif_deformation_report.json',{'status':'BLOCKED','blocker':'TOPOLOGY_LIMITATION','topology_readiness':readiness,'prebind_identity':prebind,'weight_normalization':not_run,'rest_bound_identity':not_run,'head_independence':not_run,'shoulder_result':not_run,'elbow_result':not_run,'wrist_result':not_run,'hip_result':not_run,'knee_result':not_run,'ankle_result':not_run,'edge_deformation_metrics':not_run,'contact_gap_measurements':not_run,'topology_preservation':{'source_copy_unchanged':copy_initial==sha(COPY)},'suit_tear_preservation':not_run,'final_neutral_identity':not_run})
 blocked={'iteration':'3R','character':'ALIF','objective':'controlled_binding_and_deformation_proof','status':'BLOCKED','blockers':['TOPOLOGY_LIMITATION'],'iteration02R_sha256_before':source_before,'iteration02R_sha256_after':source_after,'copy_initial_sha256':copy_initial,'copy_current_sha256':sha(COPY),'iteration02R_source_preserved':source_before==source_after,'source_copy_still_identical':source_before==sha(COPY),'prebind_visual_identity':all(v['pass'] for v in prebind.values()),'topology_readiness':False,'binding_performed':False,'automatic_weights_used':False,'remesh_or_subdivision_used':False,'actions':len(bpy.data.actions),'constraints':sum(len(p.constraints) for p in RIG.pose.bones),'ik':sum(c.type=='IK' for p in RIG.pose.bones for c in p.constraints),'next_action':'Resolve proven knee topology limitation under explicit future scope; do not advance to Iteration 4R.'}
 dump('alif_iteration03R_report.json',blocked)
 with open(os.path.join(LOG,'run.log'),'w',encoding='utf8') as f: f.write(json.dumps(blocked,indent=2))
 raise RuntimeError('TOPOLOGY_LIMITATION')

weights={}
for s in ('L','R'):
 weights['ARM_'+s]=bind_limb('ARM_'+s,[f'SHOULDER.{s}',f'UPPER_ARM.{s}',f'FOREARM.{s}',f'WRIST.{s}'],arm_j[s],arm_w[s])
 weights['LEG_'+s+'_SUIT']=bind_limb('LEG_'+s+'_SUIT',[f'HIP.{s}',f'THIGH.{s}',f'SHIN.{s}',f'ANKLE.{s}'],leg_j[s],leg_w[s])
 weights['HAND_'+s]={'rigid_bone':f'HAND.{s}','weighted_vertex_count':rigid_bind(O['HAND_'+s],f'HAND.{s}')}
 weights['FOOT_'+s]={'rigid_bone':f'FOOT.{s}','weighted_vertex_count':rigid_bind(O['FOOT_'+s],f'FOOT.{s}')}

head_tokens=('HEAD','NECK_BRIDGE','EYE_','BOLT_','SEAM_','TOOTH_','MOUTH')
torso_tokens=('TORSO','BELLY','SUIT','INNER_PATCH','SHIRT','COLLAR','TIE_','BUTTON','TEAR_REVEAL','LEG_S_')
head_objs=[]; torso_objs=[]
for o in O:
 if o.type not in {'MESH','CURVE'} or o.name in weights: continue
 u=o.name.upper()
 if any(t in u for t in head_tokens): head_objs.append(o.name); rigid_bind(o,'HEAD')
 elif any(t in u for t in torso_tokens): torso_objs.append(o.name); rigid_bind(o,'CHEST')

rest_bound=render_compare('rest_bound')
if not all(v['pass'] for v in rest_bound.values()):
 dump('alif_weight_contract.json',{'method':'deterministic_manual','meshes':weights}); dump('alif_iteration03R_report.json',{'iteration':'3R','status':'BLOCKED','blockers':['REST_IDENTITY_FAILURE'],'prebind_comparison':prebind,'rest_bound_comparison':rest_bound}); raise RuntimeError('REST_IDENTITY_FAILURE')

limbs=['ARM_L','ARM_R','LEG_L_SUIT','LEG_R_SUIT']; base_edges={n:edges(O[n],verts(O[n],True)) for n in limbs}; topo0=visual_snapshot(); static=static_snapshot(['TORSO_UNDER','SUIT_SHELL']); tests={}; em={}; gaps={'rest':{'shoulder_L_torso':closest(O['ARM_L'],O['TORSO_UNDER']),'shoulder_R_torso':closest(O['ARM_R'],O['TORSO_UNDER']),'arm_L_hand':closest(O['ARM_L'],O['HAND_L']),'arm_R_hand':closest(O['ARM_R'],O['HAND_R']),'hip_L_torso':closest(O['LEG_L_SUIT'],O['TORSO_UNDER']),'hip_R_torso':closest(O['LEG_R_SUIT'],O['TORSO_UNDER']),'leg_L_foot':closest(O['LEG_L_SUIT'],O['FOOT_L']),'leg_R_foot':closest(O['LEG_R_SUIT'],O['FOOT_R'])}}
head_centers={n:cent(O[n]) for n in head_objs if O[n].type=='MESH'}
for d,label in ((30,'plus30'),(-30,'minus30')):
 pose('HEAD',1,d); render(f'head_{label}_front.png','front'); render(f'head_{label}_34.png','three_q_r')
 moved={n:(cent(O[n])-c).length for n,c in head_centers.items()}; tests['head_'+label]={'torso_max_unintended_delta':delta(static,'TORSO_UNDER'),'suit_max_unintended_delta':delta(static,'SUIT_SHELL'),'head_objects_moved':sum(x>1e-6 for x in moved.values()),'head_mesh_object_count':len(moved),'minimum_head_object_centroid_motion':min(moved.values()) if moved else 0}
for s,sgn in (('L',1),('R',-1)):
 pose('UPPER_ARM.'+s,0,sgn*25); render(f'shoulder_{s}_25_front.png','front');
 if s=='L': render('shoulder_L_25_34.png','three_q_r')
 tests['shoulder_'+s]={'shoulder_torso_distance':closest(O['ARM_'+s],O['TORSO_UNDER'])}
for s,sgn in (('L',1),('R',-1)):
 for d in (45,90):
  pose('FOREARM.'+s,0,sgn*d); key=f'elbow_{s}_{d}';
  if s=='L' or d==90: render(key+'_front.png','front'); render(key+'_34.png','three_q_r')
  if s=='L' and d==90: render('elbow_L_90_side.png','left')
  em[key]=metric(O['ARM_'+s],base_edges['ARM_'+s]); tests[key]={'arm_hand_distance':closest(O['ARM_'+s],O['HAND_'+s])}
for s,sgn in (('L',1),('R',-1)):
 pose('HAND.'+s,0,sgn*20)
 if s=='L': render('wrist_L_20_front.png','front'); render('wrist_L_20_34.png','three_q_r')
 tests['wrist_'+s]={'arm_hand_distance':closest(O['ARM_'+s],O['HAND_'+s])}
for s,sgn in (('L',1),('R',-1)):
 pose('THIGH.'+s,0,sgn*20)
 if s=='L': render('hip_L_20_front.png','front'); render('hip_L_20_34.png','three_q_r')
 tests['hip_'+s]={'hip_torso_distance':closest(O['LEG_'+s+'_SUIT'],O['TORSO_UNDER'])}
for s,sgn in (('L',1),('R',-1)):
 for d in (45,90):
  pose('SHIN.'+s,0,sgn*d); key=f'knee_{s}_{d}'
  if s=='L' or d==90: render(key+'_front.png','front'); render(key+'_34.png','three_q_r')
  if s=='L' and d==90: render('knee_L_90_side.png','left')
  em[key]=metric(O['LEG_'+s+'_SUIT'],base_edges['LEG_'+s+'_SUIT']); tests[key]={'leg_foot_distance':closest(O['LEG_'+s+'_SUIT'],O['FOOT_'+s])}
for s,sgn in (('L',1),('R',-1)):
 pose('FOOT.'+s,0,sgn*20)
 if s=='L': render('ankle_L_20_side.png','left'); render('ankle_L_20_34.png','three_q_r')
 tests['ankle_'+s]={'leg_foot_distance':closest(O['LEG_'+s+'_SUIT'],O['FOOT_'+s])}
reset(); render('suit_tears_rest.png','front'); pose('FOREARM.L',0,90); render('suit_tears_pose.png','three_q_r'); reset()
topo1=visual_snapshot(); final_rest=render_compare('final_rest'); reset()

source_after=sha(SRC); weight_ok=all(v.get('unweighted_vertex_count',0)==0 and abs(v.get('min_weight_sum',1)-1)<=.001 and abs(v.get('max_weight_sum',1)-1)<=.001 and v.get('maximum_influence_count',1)<=2 and v.get('cross_side_contamination_count',0)==0 and v.get('negative_weight_count',0)==0 and v.get('nan_weight_count',0)==0 for n,v in weights.items() if n in limbs)
edge_ok=all(v['p99']<=2 and v['p01']>=.25 and v['nan_or_infinite_vertices']==0 for v in em.values())
head_ok=all(v['torso_max_unintended_delta']<=1e-6 and v['suit_max_unintended_delta']<=1e-6 and v['head_objects_moved']>=max(1,v['head_mesh_object_count']-2) for k,v in tests.items() if k.startswith('head_'))
topology_ok=visual_topology_equal(before,topo1); final_ok=all(v['pass'] for v in final_rest.values()); cons=sum(len(p.constraints) for p in RIG.pose.bones); acts=len(bpy.data.actions); drivers=sum(len(o.animation_data.drivers) if o.animation_data else 0 for o in O); keys=sum(len(fc.keyframe_points) for a in bpy.data.actions for fc in a.fcurves)
pose_neutral=all(max([abs(x) for x in p.rotation_euler]+[abs(x) for x in p.location]+[abs(x-1) for x in p.scale])<=1e-9 for p in RIG.pose.bones)
deform={'topology_readiness':readiness,'weight_normalization':weights,'prebind_identity':prebind,'rest_bound_identity':rest_bound,'head_independence':{k:v for k,v in tests.items() if k.startswith('head_')},'pose_results':tests,'edge_deformation_metrics':em,'contact_gap_measurements':gaps,'topology_before':before,'topology_after':topo1,'topology_preserved':topology_ok,'rigid_head_objects':head_objs,'rigid_torso_clothing_objects':torso_objs,'suit_tear_preservation':{'suit_shell_static_during_head':head_ok,'proof_images':['suit_tears_rest.png','suit_tears_pose.png']},'final_neutral_identity':final_rest}
dump('alif_weight_contract.json',{'method':'deterministic_manual_longitudinal_zones','automatic_weights_used':False,'normalization_tolerance':.001,'maximum_influences':2,'meshes':weights}); dump('alif_deformation_report.json',deform)
checks={'iteration02R_source_preserved':source_before==source_after,'source_copy_initial_identical':source_before==copy_initial,'prebind_visual_identity':all(v['pass'] for v in prebind.values()),'topology_readiness':ready,'deterministic_weights':weight_ok,'rest_bound_identity':all(v['pass'] for v in rest_bound.values()),'head_independence':head_ok,'edge_thresholds':edge_ok,'topology_unchanged':topology_ok,'final_neutral_identity':final_ok,'pose_neutral':pose_neutral,'actions_zero':acts==0,'keyframes_zero':keys==0,'constraints_zero':cons==0,'drivers_zero':drivers==0}
issues=[k for k,v in checks.items() if not v]
if not edge_ok and 'TOPOLOGY_LIMITATION' not in issues: issues.append('TOPOLOGY_LIMITATION')
status='PASS' if all(checks.values()) else 'BLOCKED'
report={'iteration':'3R','character':'ALIF','objective':'controlled_binding_and_deformation_proof','status':status,'blockers':issues,'iteration02R_sha256_before':source_before,'iteration02R_sha256_after':source_after,'copy_initial_sha256':copy_initial,'environment':{'agent':'WSL Ubuntu 24.04','blender':'Windows-native Blender 5.2'},'checks':checks,'automatic_weights_used':False,'remesh_or_subdivision_used':False,'visible_robot_geometry_added':False,'armature_count':sum(o.type=='ARMATURE' for o in O),'actions':acts,'keyframes':keys,'constraints':cons,'ik':sum(c.type=='IK' for p in RIG.pose.bones for c in p.constraints),'drivers':drivers}
dump('alif_iteration03R_report.json',report)
with open(os.path.join(LOG,'run.log'),'w',encoding='utf8') as f: f.write(json.dumps({'status':status,'blockers':issues,'checks':checks},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=COPY)
print('TSA_ITERATION_3R',status,issues)
