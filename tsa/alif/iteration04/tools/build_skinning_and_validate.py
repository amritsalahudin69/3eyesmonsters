import bpy,json,os,math,hashlib,statistics
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=r"C:\Users\HWI-ADMIN\Downloads\3d"; I3=os.path.join(ROOT,"tsa","alif","iteration03"); OUT=os.path.join(ROOT,"tsa","alif","iteration04"); VAL=os.path.join(OUT,"validation"); LOG=os.path.join(OUT,"logs")
SRC=os.path.join(I3,"alif_armature_v1.blend"); DST=os.path.join(OUT,"alif_deform_v1.blend")
os.makedirs(VAL,exist_ok=True); os.makedirs(LOG,exist_ok=True)
def sha(p):
 h=hashlib.sha256(); f=open(p,'rb')
 for b in iter(lambda:f.read(1048576),b''): h.update(b)
 f.close(); return h.hexdigest()
def dump(n,d):
 with open(os.path.join(OUT,n),'w',encoding='utf8') as f: json.dump(d,f,indent=2)
def verts(o,eval=False):
 if eval:
  eo=o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=eo.to_mesh(); p=[eo.matrix_world@v.co for v in me.vertices]; eo.to_mesh_clear(); return p
 return [o.matrix_world@v.co for v in o.data.vertices]
def edgelen(o,p): return [(p[e.vertices[0]]-p[e.vertices[1]]).length for e in o.data.edges]
def percentile(a,p):
 a=sorted(a); x=(len(a)-1)*p; i=int(x); j=min(i+1,len(a)-1); return a[i]*(j-x)+a[j]*(x-i)
def camera(az):
 c=bpy.data.objects['Camera']; t=Vector((0,0,1.8)); r=8.5; q=math.radians(az); c.location=(r*math.sin(q),r*math.cos(q),3); c.rotation_euler=((t-c.location).to_track_quat('-Z','Y')).to_euler(); bpy.context.scene.camera=c
def render(n,az=0):
 camera(az); s=bpy.context.scene; s.render.engine='BLENDER_EEVEE'; s.render.resolution_x=s.render.resolution_y=480; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.filepath=os.path.join(VAL,n); bpy.ops.render.render(write_still=True)
def pixels(p):
 im=bpy.data.images.load(p,check_existing=False); x=(list(im.size),list(im.pixels)); bpy.data.images.remove(im); return x
def compare(a,b):
 sa,pa=pixels(a); sb,pb=pixels(b); d=[abs(x-y) for x,y in zip(pa,pb)]; return {'dimensions':sa,'mean_absolute_pixel_difference':sum(d)/len(d),'max_pixel_difference':max(d)}
def bone_parent(o,b):
 w=o.matrix_world.copy(); o.parent=R; o.parent_type='BONE'; o.parent_bone=b; o.matrix_world=w
def reset():
 for p in R.pose.bones: p.rotation_mode='XYZ'; p.rotation_euler=(0,0,0); p.location=(0,0,0); p.scale=(1,1,1)
 bpy.context.view_layer.update()
def pose(b,a,d): reset(); R.pose.bones[b].rotation_euler[a]=math.radians(d); bpy.context.view_layer.update()
def weight(o,names):
 seg=[(n,R.matrix_world@R.data.bones[n].head_local,R.matrix_world@R.data.bones[n].tail_local) for n in names]
 for g in list(o.vertex_groups): o.vertex_groups.remove(g)
 gs={n:o.vertex_groups.new(name=n) for n in names}; sums=[]; mx=0
 for v in o.data.vertices:
  p=o.matrix_world@v.co; ds=[]
  for n,a,b in seg:
   ab=b-a; t=max(0,min(1,(p-a).dot(ab)/max(ab.length_squared,1e-12))); ds.append(((p-(a+ab*t)).length,n))
  ds.sort(); use=ds[:2]; inv=[1/max(x[0],1e-5)**2 for x in use]; total=sum(inv); ws=[x/total for x in inv]
  for (_,n),w in zip(use,ws): gs[n].add([v.index],w,'REPLACE')
  sums.append(sum(ws)); mx=max(mx,len(ws))
 m=o.modifiers.new('TSA_CONTROLLED_DEFORM','ARMATURE'); m.object=R; m.use_deform_preserve_volume=True
 return {'vertex_count':len(o.data.vertices),'weighted_vertex_count':len(o.data.vertices),'unweighted_count':0,'min_weight_sum':min(sums),'max_weight_sum':max(sums),'max_influences_per_vertex':mx,'allowed_groups':names,'algorithm':'two nearest canonical bone segments, inverse-square, normalized, world coordinates'}
def topo(): return {n:{'vertices':len(O[n].data.vertices),'edges':len(O[n].data.edges),'polygons':len(O[n].data.polygons)} for n in LIMBS}
def metric(o,base):
 p=verts(o,True); rr=[a/b if b>1e-9 else 1 for a,b in zip(edgelen(o,p),base)]; bad=sum(not all(math.isfinite(x) for x in q) for q in p)
 return {'median_ratio':statistics.median(rr),'p95_ratio':percentile(rr,.95),'p99_ratio':percentile(rr,.99),'p01_ratio':percentile(rr,.01),'minimum_ratio':min(rr),'maximum_ratio':max(rr),'nan_or_infinite_vertices':bad}
def gap(a,b):
 aa=verts(a,True); bb=verts(b,True); k=KDTree(len(bb))
 for i,p in enumerate(bb): k.insert(p,i)
 k.balance(); return min(k.find(p)[2] for p in aa)
def snap(names): return {n:verts(O[n],True) for n in names}
def delta(s,n): return max((a-b).length for a,b in zip(s[n],verts(O[n],True)))

rep=json.load(open(os.path.join(I3,'alif_iteration03_report.json'),encoding='utf8'))
if rep.get('status')!='PASS': raise RuntimeError('Iteration 3 not PASS')
hb=sha(SRC); O=bpy.data.objects; R=O.get('ALIF_RIG')
required=['HEAD_CTRL_REGION','TORSO_CTRL_REGION','ARM_L_REGION','ARM_R_REGION','LEG_L_REGION','LEG_R_REGION','HEAD','TORSO_UNDER','BELLY_CORE','SUIT_SHELL','ARM_L','ARM_R','HAND_L','HAND_R','LEG_L_SUIT','LEG_R_SUIT','FOOT_L','FOOT_R']
missing=[n for n in required if not O.get(n)]
if missing: raise RuntimeError('Missing '+str(missing))
views={'front':0,'three_q_l':-35,'left':-90,'back':180,'right':90,'three_q_r':35}
for n,a in views.items(): render('baseline_'+n+'.png',a)
bpy.ops.wm.save_as_mainfile(filepath=DST)
H=O['HEAD_CTRL_REGION']; tokens=('HEAD','EYE_','BOLT_','SEAM_','TOOTH_','MOUTH','TEAR_REVEAL'); heads=[o for o in O if o!=R and any(t in o.name.upper() for t in tokens) and o!=H]
for o in heads:
 if o.parent!=H:
  w=o.matrix_world.copy(); o.parent=H; o.parent_type='OBJECT'; o.matrix_world=w
bone_parent(H,'HEAD'); bone_parent(O['TORSO_CTRL_REGION'],'CHEST')
LIMBS=['ARM_L','ARM_R','LEG_L_SUIT','LEG_R_SUIT']; chains={'ARM_L':['SHOULDER.L','UPPER_ARM.L','FOREARM.L','WRIST.L'],'ARM_R':['SHOULDER.R','UPPER_ARM.R','FOREARM.R','WRIST.R'],'LEG_L_SUIT':['HIP.L','THIGH.L','SHIN.L','ANKLE.L'],'LEG_R_SUIT':['HIP.R','THIGH.R','SHIN.R','ANKLE.R']}
weights={n:weight(O[n],chains[n]) for n in LIMBS}
for n,b in [('HAND_L','HAND.L'),('HAND_R','HAND.R'),('FOOT_L','FOOT.L'),('FOOT_R','FOOT.R')]: bone_parent(O[n],b)
tb=topo(); base={n:edgelen(O[n],verts(O[n],True)) for n in LIMBS}; ts=snap(['TORSO_UNDER','SUIT_SHELL']); rest={}
for n,a in views.items():
 render('rest_'+n+'.png',a); rest[n]=compare(os.path.join(VAL,'baseline_'+n+'.png'),os.path.join(VAL,'rest_'+n+'.png'))
tests={}; edges={}; contacts={'rest':{'shoulder_torso_L':gap(O['ARM_L'],O['TORSO_UNDER']),'arm_hand_L':gap(O['ARM_L'],O['HAND_L']),'hip_torso_L':gap(O['LEG_L_SUIT'],O['TORSO_UNDER']),'leg_foot_L':gap(O['LEG_L_SUIT'],O['FOOT_L'])}}
for d,l in [(30,'plus30'),(-30,'minus30')]:
 pose('HEAD',2,d); render('head_'+l+'_front.png'); render('head_'+l+'_34.png',35); tests['head_'+l]={'torso_max_vertex_delta':delta(ts,'TORSO_UNDER'),'suit_max_vertex_delta':delta(ts,'SUIT_SHELL'),'head_details_follow':all(o.parent==H or o==O['HEAD'] for o in heads)}
pose('UPPER_ARM.L',0,25); render('arm_shoulder25_front.png'); render('arm_shoulder25_34.png',35); tests['shoulder25_L']={'contact':gap(O['ARM_L'],O['TORSO_UNDER'])}
pose('UPPER_ARM.R',0,-25); render('arm_shoulder25_R_front.png'); tests['shoulder25_R']={'contact':gap(O['ARM_R'],O['TORSO_UNDER'])}
for side,sgn in [('L',1),('R',-1)]:
 for d in (45,90):
  pose('FOREARM.'+side,0,sgn*d); p='elbow'+str(d)+('' if side=='L' else '_R'); render(p+'_front.png'); render(p+'_34.png',35)
  if side=='L' and d==90: render('elbow90_side.png',90)
  edges[p]=metric(O['ARM_'+side],base['ARM_'+side]); tests[p]={'arm_hand_contact':gap(O['ARM_'+side],O['HAND_'+side])}
for side,sgn in [('L',1),('R',-1)]:
 pose('HAND.'+side,0,sgn*20)
 if side=='L': render('wrist20_front.png'); render('wrist20_34.png',35)
 tests['wrist20_'+side]={'arm_hand_contact':gap(O['ARM_'+side],O['HAND_'+side])}
pose('THIGH.L',0,20); render('hip20_front.png'); render('hip20_34.png',35); tests['hip20_L']={'contact':gap(O['LEG_L_SUIT'],O['TORSO_UNDER'])}
for side,sgn in [('L',1),('R',-1)]:
 for d in (45,90):
  pose('SHIN.'+side,0,sgn*d); p='knee'+str(d)+('' if side=='L' else '_R'); render(p+'_front.png'); render(p+'_34.png',35)
  if side=='L' and d==90: render('knee90_side.png',90)
  edges[p]=metric(O['LEG_'+side+'_SUIT'],base['LEG_'+side+'_SUIT']); tests[p]={'leg_foot_contact':gap(O['LEG_'+side+'_SUIT'],O['FOOT_'+side])}
for side,sgn in [('L',1),('R',-1)]:
 pose('FOOT.'+side,0,sgn*20)
 if side=='L': render('ankle20_side.png',90); render('ankle20_34.png',35)
 tests['ankle20_'+side]={'leg_foot_contact':gap(O['LEG_'+side+'_SUIT'],O['FOOT_'+side])}
reset(); render('suit_tears_rest.png'); pose('FOREARM.L',0,90); render('suit_tears_pose.png',35); reset()
ta=topo(); ha=sha(SRC); restmax=max(x['max_pixel_difference'] for x in rest.values()); restmean=max(x['mean_absolute_pixel_difference'] for x in rest.values()); wok=all(v['unweighted_count']==0 and abs(v['min_weight_sum']-1)<=.001 and abs(v['max_weight_sum']-1)<=.001 and v['max_influences_per_vertex']<=3 for v in weights.values()); eok=all(v['p99_ratio']<=2 and v['p01_ratio']>=.25 and v['nan_or_infinite_vertices']==0 for v in edges.values()); hok=all(v['torso_max_vertex_delta']<=1e-6 and v['suit_max_vertex_delta']<=1e-6 and v['head_details_follow'] for k,v in tests.items() if k.startswith('head_')); rok=restmax<=.01 and restmean<=.0005
cons=sum(len(p.constraints) for p in R.pose.bones); acts=len(bpy.data.actions); drivers=sum(len(o.animation_data.drivers) if o.animation_data else 0 for o in O)
deform={'weight_validation':weights,'rest_pose_comparison':rest,'head_independence':{k:v for k,v in tests.items() if k.startswith('head_')},'pose_tests':tests,'edge_metrics':edges,'contact_gap_measurements':contacts,'topology_before':tb,'topology_after':ta,'topology_unchanged':tb==ta,'source_hash_before':hb,'source_hash_after':ha,'source_preserved':hb==ha,'automatic_weights_used':False,'remesh_or_subdivision_used':False}
issues=[]
if not rok: issues.append('REST_IDENTITY_FAILURE')
if not eok: issues.append('TOPOLOGY_LIMITATION')
if not hok: issues.append('HEAD_INDEPENDENCE_FAILURE')
if not wok: issues.append('WEIGHT_VALIDATION_FAILURE')
status='PASS' if all([hb==ha,wok,eok,hok,rok,tb==ta,cons==0,acts==0,drivers==0]) else 'BLOCKED'
final={'iteration':4,'character':'ALIF','objective':'controlled_skinning_and_deformation_proof','status':status,'blockers':issues,'iteration3_source_preserved':hb==ha,'rest_pose_identity':rok,'head_rotation_pass':hok,'arm_weights_normalized':wok,'leg_weights_normalized':wok,'topology_unchanged':tb==ta,'edge_thresholds_pass':eok,'armature_count':sum(o.type=='ARMATURE' for o in O),'action_count':acts,'constraints':cons,'ik_constraints':sum(c.type=='IK' for p in R.pose.bones for c in p.constraints),'drivers':drivers,'automatic_weights_used':False,'robot_joint_geometry_added':False,'remesh_or_subdivision_used':False,'final_neutral_pose':all(max(abs(x) for x in p.rotation_euler)<=1e-9 for p in R.pose.bones)}
dump('alif_weight_contract.json',{'method':'deterministic_manual_geometry_weighting','coordinate_space':'world','normalization_tolerance':.001,'max_influences':3,'meshes':weights}); dump('alif_deformation_report.json',deform); dump('alif_iteration04_report.json',final)
bpy.ops.wm.save_as_mainfile(filepath=DST)
with open(os.path.join(LOG,'run.log'),'w') as f: f.write(json.dumps(final,indent=2))
print('TSA_ITERATION04',status,issues)
