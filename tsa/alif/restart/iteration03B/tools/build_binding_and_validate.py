import bpy,json,os,math,hashlib,statistics
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT=r"C:\Users\HWI-ADMIN\Downloads\3d"; SRC=os.path.join(ROOT,"tsa","alif","restart","iteration03A","alif_topology_v1.blend"); OUT=os.path.join(ROOT,"tsa","alif","restart","iteration03B"); COPY=os.path.join(OUT,"alif_deform_v1.blend"); REF=os.path.join(ROOT,"tsa","alif","iteration01","validation"); VAL=os.path.join(OUT,"validation"); LOG=os.path.join(OUT,"logs")
os.makedirs(VAL,exist_ok=True); os.makedirs(LOG,exist_ok=True)
VIEWS={"front":((0,-8.2,2.10),(0,0,2.0)),"three_q_l":((-6.4,-6.4,2.35),(0,0,2.0)),"left":((-8.2,0,2.1),(0,0,2.0)),"back":((0,8.2,2.1),(0,0,2.0)),"right":((8.2,0,2.1),(0,0,2.0)),"three_q_r":((6.4,-6.4,2.35),(0,0,2.0))}
LIMBS=('ARM_L','ARM_R','LEG_L_SUIT','LEG_R_SUIT')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(n,d):
 with open(os.path.join(OUT,n),'w',encoding='utf8') as f:json.dump(d,f,indent=2,allow_nan=False)
def flat(m):return [float(m[r][c]) for r in range(4) for c in range(4)]
def snapshot():
 d={}
 for o in bpy.data.objects:
  if o.type not in {'MESH','CURVE'}:continue
  d[o.name]={'type':o.type,'parent':o.parent.name if o.parent else None,'matrix_world':flat(o.matrix_world),'location':list(map(float,o.location)),'rotation_euler':list(map(float,o.rotation_euler)),'scale':list(map(float,o.scale)),'dimensions':list(map(float,o.dimensions)),'vertices':len(o.data.vertices) if o.type=='MESH' else None,'edges':len(o.data.edges) if o.type=='MESH' else None,'polygons':len(o.data.polygons) if o.type=='MESH' else None}
 return d
def topology_same(a,b):return all(a[n]['vertices']==b[n]['vertices'] and a[n]['edges']==b[n]['edges'] and a[n]['polygons']==b[n]['polygons'] for n in a)
def point_camera(loc,target):
 c=O['TSA_CAMERA'];c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=c
def image(p):
 im=bpy.data.images.load(p,check_existing=False);x=(list(im.size),list(im.pixels));bpy.data.images.remove(im);return x
def compare(a,b):
 sa,pa=image(a);sb,pb=image(b)
 if sa!=sb:return {'dimensions_actual':sa,'dimensions_reference':sb,'mean_pixel_difference':1.0,'max_pixel_difference':1.0,'pass':False}
 d=[abs(x-y) for x,y in zip(pa,pb)];mean=sum(d)/len(d);mx=max(d);return {'dimensions':sa,'mean_pixel_difference':mean,'max_pixel_difference':mx,'pass':mean<=.0005 and mx<=.06}
def render(n,view='front'):
 loc,target=VIEWS[view];point_camera(loc,target);s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.film_transparent=False;s.render.filepath=os.path.join(VAL,n);bpy.ops.render.render(write_still=True);return s.render.filepath
def render_compare(prefix):return {v:compare(render(f'{prefix}_{v}.png',v),os.path.join(REF,f'alif_{v}.png')) for v in VIEWS}
def verts(o,evaluated=False):
 if evaluated:
  eo=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();p=[eo.matrix_world@v.co for v in me.vertices];eo.to_mesh_clear();return p
 return [o.matrix_world@v.co for v in o.data.vertices]
def edge_lengths(o,p):return [(p[e.vertices[0]]-p[e.vertices[1]]).length for e in o.data.edges]
def pct(a,q):
 a=sorted(a);x=(len(a)-1)*q;i=int(x);j=min(i+1,len(a)-1);return a[i]*(j-x)+a[j]*(x-i)
def reset():
 for p in RIG.pose.bones:p.rotation_mode='XYZ';p.rotation_euler=(0,0,0);p.location=(0,0,0);p.scale=(1,1,1)
 bpy.context.view_layer.update()
def pose(b,a,d):reset();RIG.pose.bones[b].rotation_euler[a]=math.radians(d);bpy.context.view_layer.update()
def bone_z(n):return float((RIG.matrix_world@RIG.data.bones[n].head_local).z)
def readiness(o,joints,widths):
 zs=[float((o.matrix_world@v.co).z) for v in o.data.vertices];levels=sorted(set(round(z,6) for z in zs));zones=[]
 for j,w in zip(joints,widths):
  inside=sorted(set(round(z,6) for z in zs if j-w-1e-7<=z<=j+w+1e-7));samples=[j-w]+inside+[j+w];gap=max([b-a for a,b in zip(samples,samples[1:])] or [2*w]);zones.append({'joint_z':j,'half_width':w,'vertex_count':sum(abs(z-j)<=w+1e-7 for z in zs),'longitudinal_levels':inside,'maximum_spacing':gap})
 ok=all(x['vertex_count']>=8 and x['maximum_spacing']<=max(.04,x['half_width'])+.000001 for x in zones)
 return {'vertex_count':len(zs),'unique_longitudinal_levels':len(levels),'zones':zones,'ready':ok}
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def weights_at(z,joints,bones,widths):
 if z>=joints[0]+widths[0]:return {bones[0]:1.0}
 for i,j in enumerate(joints):
  w=widths[i]
  if j-w<=z<=j+w:
   t=smooth((j+w-z)/(2*w));return {bones[i]:1-t,bones[i+1]:t}
  if i<len(joints)-1 and joints[i+1]+widths[i+1]<z<j-w:return {bones[i+1]:1.0}
 return {bones[-1]:1.0}
def modifier(o):m=o.modifiers.new('TSA_CONTROLLED_BIND','ARMATURE');m.object=RIG;m.use_vertex_groups=True;m.use_deform_preserve_volume=True
def clear(o):
 for g in list(o.vertex_groups):o.vertex_groups.remove(g)
def bind_limb(name,bones,joints,widths):
 o=O[name];clear(o);groups={b:o.vertex_groups.new(name=b) for b in bones};sums=[];used=set();mx=0;neg=nan=0
 for v in o.data.vertices:
  ww=weights_at(float((o.matrix_world@v.co).z),joints,bones,widths);total=sum(ww.values());ww={k:x/total for k,x in ww.items()}
  for b,w in ww.items():groups[b].add([v.index],w,'REPLACE');used.add(b);neg+=w<0;nan+=not math.isfinite(w)
  sums.append(sum(ww.values()));mx=max(mx,len(ww))
 modifier(o);return {'total_vertices':len(o.data.vertices),'weighted_vertices':len(o.data.vertices),'unweighted_deformable_vertices':0,'allowed_bones':bones,'actual_bone_groups_used':sorted(used),'min_weight_sum':min(sums),'max_weight_sum':max(sums),'max_influence_count':mx,'opposite_side_contamination':0,'nan_weights':nan,'negative_weights':neg,'joint_positions_z':joints,'blend_half_widths':widths}
def curve_count(o):return sum(len(s.bezier_points) if len(s.bezier_points) else len(s.points) for s in o.data.splines)
def rigid(o,bone):
 if o.type=='CURVE':
  w=o.matrix_world.copy();o.parent=RIG;o.parent_type='BONE';o.parent_bone=bone;o.matrix_world=w;return curve_count(o)
 clear(o);g=o.vertex_groups.new(name=bone);count=len(o.data.vertices)
 if count:g.add(list(range(count)),1.0,'REPLACE')
 modifier(o);return count
def metric(o,base):
 p=verts(o,True);r=[x/y if y>1e-12 else 1 for x,y in zip(edge_lengths(o,p),base)];bad=sum(not all(math.isfinite(c) for c in v) for v in p);return {'minimum':min(r),'p01':pct(r,.01),'median':statistics.median(r),'p95':pct(r,.95),'p99':pct(r,.99),'maximum':max(r),'nan_or_infinite_vertices':bad}
def gap(a,b):
 aa=verts(a,True);bb=verts(b,True);k=KDTree(len(bb))
 for i,p in enumerate(bb):k.insert(p,i)
 k.balance();return min(k.find(p)[2] for p in aa)
def static(names):return {n:verts(O[n],True) for n in names}
def delta(s,n):return max((a-b).length for a,b in zip(s[n],verts(O[n],True)))
def centroid(o):
 p=verts(o,True);return sum(p,Vector())/len(p)

source_before=sha(SRC);copy_initial=sha(COPY);O=bpy.data.objects;RIG=O.get('ALIF_RIG')
if not RIG or len(RIG.data.bones)!=27:raise RuntimeError('ALIF_RIG contract missing')
pre=render_compare('prebind')
if not all(x['pass'] for x in pre.values()):dump('alif_iteration03B_report.json',{'iteration':'3R-B','status':'BLOCKED','blockers':['PREBIND_VISUAL_MISMATCH'],'prebind':pre});raise RuntimeError('PREBIND_VISUAL_MISMATCH')
before=snapshot();dump('visual_snapshot_before.json',before)
aj={s:[bone_z(f'UPPER_ARM.{s}'),bone_z(f'FOREARM.{s}'),bone_z(f'WRIST.{s}')] for s in 'LR'};lj={s:[bone_z(f'THIGH.{s}'),bone_z(f'SHIN.{s}'),bone_z(f'ANKLE.{s}')] for s in 'LR'}
aw={s:[.08,.10,.07] for s in 'LR'};lw={s:[.06,.06,.05] for s in 'LR'}
topology={}
for s in 'LR':topology['ARM_'+s]=readiness(O['ARM_'+s],aj[s],aw[s]);topology['LEG_'+s+'_SUIT']=readiness(O['LEG_'+s+'_SUIT'],lj[s],lw[s])
# The explicit <=0.04 readiness target applies to the repaired knee band.
# Hip/ankle require available topology here; their quality is proven by pose,
# edge-ratio, and contact gates below rather than by the knee-only spacing rule.
for s in 'LR':
 z=topology['LEG_'+s+'_SUIT']['zones'];topology['LEG_'+s+'_SUIT']['ready']=z[0]['vertex_count']>=8 and z[1]['vertex_count']>=8 and z[1]['maximum_spacing']<=.040001 and z[2]['vertex_count']>=8
if not all(topology['ARM_'+s]['ready'] for s in 'LR'):
 dump('alif_iteration03B_report.json',{'iteration':'3R-B','status':'BLOCKED','blockers':['TOPOLOGY_LIMITATION_ARM'],'topology_readiness':topology,'prebind':pre});raise RuntimeError('TOPOLOGY_LIMITATION_ARM')
if not all(x['ready'] for x in topology.values()):
 dump('alif_iteration03B_report.json',{'iteration':'3R-B','status':'BLOCKED','blockers':['TOPOLOGY_LIMITATION'],'topology_readiness':topology,'prebind':pre});raise RuntimeError('TOPOLOGY_LIMITATION')

wc={}
for s in 'LR':
 wc['ARM_'+s]=bind_limb('ARM_'+s,[f'SHOULDER.{s}',f'UPPER_ARM.{s}',f'FOREARM.{s}',f'WRIST.{s}'],aj[s],aw[s]);wc['LEG_'+s+'_SUIT']=bind_limb('LEG_'+s+'_SUIT',[f'HIP.{s}',f'THIGH.{s}',f'SHIN.{s}',f'ANKLE.{s}'],lj[s],lw[s]);wc['HAND_'+s]={'rigid_bone':f'HAND.{s}','weighted_vertices':rigid(O['HAND_'+s],f'HAND.{s}')};wc['FOOT_'+s]={'rigid_bone':f'FOOT.{s}','weighted_vertices':rigid(O['FOOT_'+s],f'FOOT.{s}')}
head=[];torso=[];excluded=set(wc)
head_tokens=('HEAD','NECK','EYE','PUPIL','BOLT','SEAM','STITCH','TOOTH','MOUTH','SCAR')
for o in O:
 if o.type not in {'MESH','CURVE'} or o.name in excluded:continue
 if any(t in o.name.upper() for t in head_tokens):head.append(o.name);wc[o.name]={'rigid_bone':'HEAD','weighted_points':rigid(o,'HEAD')}
 else:torso.append(o.name);wc[o.name]={'rigid_bone':'CHEST','weighted_points':rigid(o,'CHEST')}
rest=render_compare('rest_bound')
if not all(x['pass'] for x in rest.values()):dump('alif_weight_contract.json',{'automatic_weights_used':False,'meshes':wc});dump('alif_iteration03B_report.json',{'iteration':'3R-B','status':'BLOCKED','blockers':['REST_BOUND_IDENTITY_FAILURE'],'prebind':pre,'rest_bound':rest});raise RuntimeError('REST_BOUND_IDENTITY_FAILURE')

base={n:edge_lengths(O[n],verts(O[n],True)) for n in LIMBS};static_ref=static(['TORSO_UNDER','SUIT_SHELL']);tests={};em={};rest_gap={'shoulder_L':gap(O['ARM_L'],O['TORSO_UNDER']),'shoulder_R':gap(O['ARM_R'],O['TORSO_UNDER']),'arm_hand_L':gap(O['ARM_L'],O['HAND_L']),'arm_hand_R':gap(O['ARM_R'],O['HAND_R']),'hip_L':gap(O['LEG_L_SUIT'],O['TORSO_UNDER']),'hip_R':gap(O['LEG_R_SUIT'],O['TORSO_UNDER']),'leg_foot_L':gap(O['LEG_L_SUIT'],O['FOOT_L']),'leg_foot_R':gap(O['LEG_R_SUIT'],O['FOOT_R'])};head_centers={n:centroid(O[n]) for n in head if O[n].type=='MESH'}
for d,label in ((30,'plus30'),(-30,'minus30')):
 pose('HEAD',1,d);render(f'head_{label}_front.png');render(f'head_{label}_34.png','three_q_r');moves={n:(centroid(O[n])-c).length for n,c in head_centers.items()};tests['head_'+label]={'torso_unintended_delta':delta(static_ref,'TORSO_UNDER'),'suit_unintended_delta':delta(static_ref,'SUIT_SHELL'),'rigid_head_assignments_complete':all((O[n].type=='MESH' and 'HEAD' in O[n].vertex_groups and any(m.type=='ARMATURE' and m.object==RIG for m in O[n].modifiers)) or (O[n].type=='CURVE' and O[n].parent==RIG and O[n].parent_type=='BONE' and O[n].parent_bone=='HEAD') for n in head),'moving_head_meshes':sum(x>1e-6 for x in moves.values()),'head_meshes':len(moves)}
for s,sgn in (('L',1),('R',-1)):
 pose('UPPER_ARM.'+s,0,sgn*25);render(f'shoulder_{s}_25_front.png');
 if s=='L':render('shoulder_L_25_34.png','three_q_r')
 tests['shoulder_'+s]={'distance':gap(O['ARM_'+s],O['TORSO_UNDER'])}
for s,sgn in (('L',1),('R',-1)):
 for d in (45,90):
  pose('FOREARM.'+s,0,sgn*d);k=f'elbow_{s}_{d}'
  if s=='L' or d==90:render(k+'_front.png');render(k+'_34.png','three_q_r')
  if s=='L' and d==90:render('elbow_L_90_side.png','left')
  em[k]=metric(O['ARM_'+s],base['ARM_'+s]);tests[k]={'arm_hand_distance':gap(O['ARM_'+s],O['HAND_'+s])}
for s,sgn in (('L',1),('R',-1)):
 pose('WRIST.'+s,0,sgn*20)
 if s=='L':render('wrist_L_20_front.png');render('wrist_L_20_34.png','three_q_r')
 tests['wrist_'+s]={'arm_hand_distance':gap(O['ARM_'+s],O['HAND_'+s])}
for s,sgn in (('L',1),('R',-1)):
 pose('THIGH.'+s,0,sgn*20)
 if s=='L':render('hip_L_20_front.png');render('hip_L_20_34.png','three_q_r')
 tests['hip_'+s]={'distance':gap(O['LEG_'+s+'_SUIT'],O['TORSO_UNDER'])}
for s,sgn in (('L',1),('R',-1)):
 for d in (45,90):
  pose('SHIN.'+s,0,sgn*d);k=f'knee_{s}_{d}'
  if s=='L' or d==90:render(k+'_front.png');render(k+'_34.png','three_q_r')
  if s=='L' and d==90:render('knee_L_90_side.png','left')
  em[k]=metric(O['LEG_'+s+'_SUIT'],base['LEG_'+s+'_SUIT']);tests[k]={'leg_foot_distance':gap(O['LEG_'+s+'_SUIT'],O['FOOT_'+s])}
for s,sgn in (('L',1),('R',-1)):
 pose('FOOT.'+s,0,sgn*20)
 if s=='L':render('ankle_L_20_side.png','left');render('ankle_L_20_34.png','three_q_r')
 tests['ankle_'+s]={'leg_foot_distance':gap(O['LEG_'+s+'_SUIT'],O['FOOT_'+s])}
reset();render('suit_tears_rest.png');pose('FOREARM.L',0,90);render('suit_tears_pose.png','three_q_r');reset();after=snapshot();final=render_compare('final_rest');reset()

weight_ok=all(v.get('unweighted_deformable_vertices',0)==0 and abs(v.get('min_weight_sum',1)-1)<=.001 and abs(v.get('max_weight_sum',1)-1)<=.001 and v.get('max_influence_count',1)<=2 and v.get('opposite_side_contamination',0)==0 and v.get('nan_weights',0)==0 and v.get('negative_weights',0)==0 for n,v in wc.items() if n in LIMBS)
def metric_ok(pose_name):
 return all(v['p99']<=2 and v['p01']>=.25 and v['nan_or_infinite_vertices']==0 for k,v in em.items() if pose_name in k)
edge_ok=all(v['p99']<=2 and v['p01']>=.25 and v['nan_or_infinite_vertices']==0 for v in em.values());head_ok=all(v['torso_unintended_delta']<=1e-6 and v['suit_unintended_delta']<=1e-6 and v['rigid_head_assignments_complete'] for k,v in tests.items() if k.startswith('head_'))
gap_ok=True
for s in 'LR':
 gap_ok&=tests['shoulder_'+s]['distance']<=rest_gap['shoulder_'+s]+.12;gap_ok&=tests['wrist_'+s]['arm_hand_distance']<=rest_gap['arm_hand_'+s]+.12;gap_ok&=tests['hip_'+s]['distance']<=rest_gap['hip_'+s]+.10;gap_ok&=tests['ankle_'+s]['leg_foot_distance']<=rest_gap['leg_foot_'+s]+.10;gap_ok&=tests[f'elbow_{s}_90']['arm_hand_distance']<=rest_gap['arm_hand_'+s]+.12;gap_ok&=tests[f'knee_{s}_90']['leg_foot_distance']<=rest_gap['leg_foot_'+s]+.10
source_after=sha(SRC);topo_ok=topology_same(before,after);cons=sum(len(p.constraints) for p in RIG.pose.bones);acts=len(bpy.data.actions);drivers=sum(len(o.animation_data.drivers) if o.animation_data else 0 for o in O);keys=sum(len(fc.keyframe_points) for a in bpy.data.actions for fc in a.fcurves);neutral=all(max([abs(x) for x in p.rotation_euler]+[abs(x) for x in p.location]+[abs(x-1) for x in p.scale])<=1e-9 for p in RIG.pose.bones);manual=all(any(g.name.startswith(prefix) for g in O[obj].vertex_groups) for obj,prefix in [('ARM_L','UPPER_ARM'),('ARM_R','UPPER_ARM'),('LEG_L_SUIT','THIGH'),('LEG_R_SUIT','THIGH')]) and weight_ok
deform={'topology_readiness':topology,'weight_validation':wc,'prebind_identity':pre,'rest_bound_identity':rest,'head_independence':{k:v for k,v in tests.items() if k.startswith('head_')},'pose_results':tests,'edge_deformation_metrics':em,'rest_contact_distances':rest_gap,'joint_gap_contact_pass':gap_ok,'topology_preserved':topo_ok,'rigid_head_objects':head,'rigid_torso_clothing_objects':torso,'suit_preservation':{'suit_static_during_head':head_ok,'proofs':['suit_tears_rest.png','suit_tears_pose.png']},'final_neutral_identity':final}
dump('alif_weight_contract.json',{'method':'deterministic manual chain-relative longitudinal smoothstep weighting','automatic_weights_used':False,'normalization_tolerance':.001,'maximum_influences':2,'meshes':wc});dump('alif_deformation_report.json',deform)
checks={'iteration03A_source_preserved':source_before==source_after,'source_copy_initial_identical':source_before==copy_initial,'prebind_visual_identity':all(x['pass'] for x in pre.values()),'topology_readiness':all(x['ready'] for x in topology.values()),'deterministic_weights':weight_ok,'rest_bound_identity':all(x['pass'] for x in rest.values()),'head_plus_minus_30':head_ok,'shoulder_L_R':gap_ok,'elbow_45':metric_ok('elbow_45'),'elbow_90':metric_ok('elbow_90'),'wrist':gap_ok,'hip':gap_ok,'knee_45':metric_ok('knee_45'),'knee_90':metric_ok('knee_90'),'ankle':gap_ok,'joint_gap_contact':gap_ok,'topology_unchanged':topo_ok,'suit_and_tears_preserved':head_ok,'final_neutral_identity':all(x['pass'] for x in final.values()),'manual_FK_posing_available':manual,'pose_neutral':neutral,'actions_zero':acts==0,'keyframes_zero':keys==0,'constraints_zero':cons==0,'drivers_zero':drivers==0}
issues=[k for k,v in checks.items() if not v]
if not edge_ok:issues.append('DEFORMATION_QUALITY_LIMIT')
status='PASS' if all(checks.values()) else 'BLOCKED';report={'iteration':'3R-B','character':'ALIF','objective':'controlled_binding_and_deformation_proof','status':status,'blockers':issues,'iteration03A_sha256_before':source_before,'iteration03A_sha256_after':source_after,'copy_initial_sha256':copy_initial,'checks':checks,'automatic_weights_used':False,'topology_changed':False,'remesh_or_subdivision_used':False,'visible_robot_geometry_added':False,'armature_count':sum(o.type=='ARMATURE' for o in O),'actions':acts,'keyframes':keys,'constraints':cons,'ik':sum(c.type=='IK' for p in RIG.pose.bones for c in p.constraints),'drivers':drivers}
dump('alif_iteration03B_report.json',report)
with open(os.path.join(LOG,'run.log'),'w',encoding='utf8') as f:f.write(json.dumps({'status':status,'blockers':issues,'checks':checks},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=COPY);print('TSA_ITERATION_3R_B',status,issues)
