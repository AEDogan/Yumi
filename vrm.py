"""Embedded GLB/VRM humanoid loading, retargeting, skinning and expressions."""
from __future__ import annotations
import json, struct, math, time
from pathlib import Path
from functools import lru_cache
import numpy as np
from PySide6.QtGui import QImage
from OpenGL.GL import *
from motion import MotionRig, ik
from joint_limits import limit_rotation, rotation_limits
DTYPES = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

def rotation(q):
    x, y, z, w = q
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length < 1e-08:
        return np.eye(3)
    x, y, z, w = (v / length for v in q)
    return np.array([[1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * z * w, 2 * x * z + 2 * y * w], [2 * x * y + 2 * z * w, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * x * w], [2 * x * z - 2 * y * w, 2 * y * z + 2 * x * w, 1 - 2 * x * x - 2 * y * y]])

def aim(source, target):
    ax, ay, az = source
    bx, by, bz = target
    an = max(math.sqrt(ax * ax + ay * ay + az * az), 1e-09)
    bn = max(math.sqrt(bx * bx + by * by + bz * bz), 1e-09)
    ax /= an
    ay /= an
    az /= an
    bx /= bn
    by /= bn
    bz /= bn
    x = ay * bz - az * by
    y = az * bx - ax * bz
    z = ax * by - ay * bx
    c = ax * bx + ay * by + az * bz
    if c < -0.99999:
        x, y, z = (-az, 0.0, ax)
        length = math.sqrt(x * x + z * z)
        if length < 1e-06:
            x, y, z = (0.0, -az, ay)
            length = math.sqrt(y * y + z * z)
        axis = np.array([x / length, y / length, z / length])
        return 2 * np.outer(axis, axis) - np.eye(3)
    f = 1 / max(1 + c, 1e-09)
    return np.array([[1 - (y * y + z * z) * f, -z + x * y * f, y + x * z * f], [z + x * y * f, 1 - (x * x + z * z) * f, -x + y * z * f], [-y + x * z * f, x + y * z * f, 1 - (x * x + y * y) * f]])

class VRMData:

    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        import hashlib
        self.source_sha256=hashlib.sha256(raw).hexdigest()
        self.mapping_sha256=None
        if len(raw) < 20 or len(raw) > 150 * 1024 * 1024:
            raise ValueError('VRM dosyası boyutu geçersiz (en fazla 150 MB).')
        magic, version, length = struct.unpack_from('<III', raw)
        if magic != 1179937895 or version != 2 or length != len(raw):
            raise ValueError('Geçerli bir VRM / GLB 2.0 dosyası değil.')
        offset = 12
        self.bin = b''
        self.g = None
        while offset + 8 <= len(raw):
            size, kind = struct.unpack_from('<II', raw, offset)
            offset += 8
            if offset + size > len(raw):
                raise ValueError('Eksik GLB veri bloğu.')
            if kind == 1313821514:
                self.g = json.loads(raw[offset:offset + size])
            elif kind == 5130562:
                self.bin = raw[offset:offset + size]
            offset += size
        if not self.g:
            raise ValueError('VRM JSON verisi yok.')
        ext = self.g.get('extensions', {})
        self.legacy = 'VRM' in ext
        self.vrm = ext.get('VRM', ext.get('VRMC_vrm'))
        if not self.vrm and self.path.suffix.lower()=='.glb':
            # Explicit local humanoid mapping lets a skinned GLB retain its
            # geometry and materials. Unmapped prop GLBs remain unsupported.
            sidecar=self.path.with_suffix('.humanoid.json')
            if sidecar.is_file() and sidecar.stat().st_size<=1024*1024:
                import hashlib
                config=json.loads(sidecar.read_text(encoding='utf-8'))
                self.mapping_sha256=hashlib.sha256(sidecar.read_bytes()).hexdigest()
                if config.get('format_version')!=1 or config.get('source_sha256')!=hashlib.sha256(raw).hexdigest():
                    raise ValueError('GLB karakter eşlemesi bu dosyayla uyuşmuyor.')
                self.vrm=config.get('character')
        if not self.vrm:
            raise ValueError('Yalnız VRM humanoid karakterler destekleniyor; dosyada VRM bilgisi bulunamadı.')
        self.meta = self.vrm.get('meta', {})
        bones = self.vrm.get('humanoid', {}).get('humanBones', {})
        self.bones = {v['bone']: v['node'] for v in bones} if isinstance(bones, list) else {k: v['node'] for k, v in bones.items()}
        for required in ('hips','head','leftUpperArm','leftLowerArm','leftHand','rightUpperArm','rightLowerArm','rightHand','leftUpperLeg','leftLowerLeg','leftFoot','rightUpperLeg','rightLowerLeg','rightFoot'):
            if required not in self.bones:
                raise ValueError('VRM iskeletinde eksik kemik: ' + required)
        self.nodes = self.g['nodes']
        for name,node in self.bones.items():
            if not isinstance(node,int) or not 0<=node<len(self.nodes):raise ValueError('VRM iskeletinde geçersiz kemik düğümü: '+name)
        self.parents = {}
        self.local = []
        self.order = []
        for i, node in enumerate(self.nodes):
            for child in node.get('children', []):
                self.parents[child] = i
            if 'matrix' in node:
                m = np.array(node['matrix'], float).reshape(4, 4).T
            else:
                m = np.eye(4)
                m[:3, :3] = rotation(node.get('rotation', [0, 0, 0, 1])) @ np.diag(node.get('scale', [1, 1, 1]))
                m[:3, 3] = node.get('translation', [0, 0, 0])
            self.local.append(m)

        def visit(i, ancestors):
            if i in ancestors:
                raise ValueError('İskelette döngü var.')
            self.order.append(i)
            for child in self.nodes[i].get('children', []):
                visit(child, ancestors | {i})
        for i in range(len(self.nodes)):
            if i not in self.parents:
                visit(i, set())
        self.rest = np.empty((len(self.nodes), 4, 4))
        for i in self.order:
            self.rest[i] = self.rest[self.parents[i]] @ self.local[i] if i in self.parents else self.local[i]
        self.flip = np.diag([-1.0, 1.0, -1.0]) if self.legacy else np.eye(3)
        self.skins = []
        for skin in self.g.get('skins', []):
            joints = np.array(skin['joints'], int)
            inverse = self.array(skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1) if 'inverseBindMatrices' in skin else np.tile(np.eye(4), (len(joints), 1, 1))
            self.skins.append((joints, inverse))
        self.expressions = {}
        if self.legacy:
            for group in self.vrm.get('blendShapeMaster', {}).get('blendShapeGroups', []):
                name = group.get('presetName')
                if not name or name == 'unknown':
                    name = group.get('name', '')
                if name:
                    self.expressions[name.lower()] = [(b['mesh'], b['index'], b['weight'] / 100) for b in group.get('binds', [])]
        else:
            groups=self.vrm.get('expressions', {})
            for name, group in {**groups.get('custom',{}),**groups.get('preset',{})}.items():
                self.expressions[name.lower()] = [(self.nodes[b['node']]['mesh'], b['index'], b['weight']) for b in group.get('morphTargetBinds', [])]
        needed = {(mesh, index) for binds in self.expressions.values() for mesh, index, weight in binds}
        self.parts = []
        for ni, node in enumerate(self.nodes):
            if 'mesh' not in node:
                continue
            mi = node['mesh']
            for primitive in self.g['meshes'][mi]['primitives']:
                if primitive.get('mode', 4) != 4:
                    continue
                attrs = primitive['attributes']
                pos = self.array(attrs['POSITION']).astype('float32')
                count = len(pos)
                if count > 300000:
                    raise ValueError('VRM parçası çok büyük.')
                material = primitive.get('material', 0)
                label = self.g['materials'][material].get('name', '').lower()
                kind = 'hair' if 'hair' in label else 'face' if any((x in label for x in ('eye', 'head', 'mouth', 'face'))) else 'cloth' if any((x in label for x in ('cloth', 'dress', 'drape', 'cape', 'skirt', 'fur'))) else 'body'
                part = {'node': ni, 'mesh': mi, 'skin': node.get('skin'), 'pos': pos, 'normal': self.array(attrs['NORMAL']).astype('float32') if 'NORMAL' in attrs else np.tile([0, 1, 0], (count, 1)).astype('float32'), 'uv': self.array(attrs['TEXCOORD_0']).astype('float32') if 'TEXCOORD_0' in attrs else np.zeros((count, 2), dtype='float32'), 'indices': self.array(primitive['indices']).astype('uint32').ravel() if 'indices' in primitive else np.arange(count, dtype='uint32'), 'material': material, 'kind': kind, 'morphs': {}}
                if len(part['indices']) and part['indices'].max() >= count:
                    raise ValueError('Geçersiz VRM üçgen indeksi.')
                if 'JOINTS_0' in attrs:
                    part['joints'] = self.array(attrs['JOINTS_0']).astype('int32')
                    weights = self.array(attrs['WEIGHTS_0']).astype('float32')
                    part['weights'] = weights / np.maximum(weights.sum(axis=1, keepdims=True), 1e-08)
                for index, target in enumerate(primitive.get('targets', [])):
                    if (mi, index) in needed and 'POSITION' in target:
                        part['morphs'][index] = self.array(target['POSITION']).astype('float32')
                self.parts.append(part)
        if not self.parts:
            raise ValueError('VRM görünür üçgen içermiyor.')
        self.front_cloth_roots = []
        self.front_cloth_fold_nodes = []
        for ni, node in enumerate(self.nodes):
            name = node.get('name', '').lower()
            parent_name = self.nodes[self.parents[ni]].get('name', '').lower() if ni in self.parents else ''
            if ('front loin cloth' in name or 'front loincloth' in name) and (not ('front loin cloth' in parent_name or 'front loincloth' in parent_name)):
                self.front_cloth_roots.append(ni)
                cursor = ni
                for step in range(3):
                    children = [c for c in self.nodes[cursor].get('children', []) if 'front loin' in self.nodes[c].get('name', '').lower()]
                    if not children:
                        break
                    cursor = children[0]
                if cursor != ni:
                    self.front_cloth_fold_nodes.append(cursor)
        bounds = []
        for p in self.parts:
            used=np.unique(p['indices'])
            if not len(used):continue
            raw=np.c_[p['pos'][used], np.ones(len(used))]
            if p['skin'] is not None and 'joints' in p:
                nodes,inverse=self.skins[p['skin']];palette=self.rest[nodes]@inverse
                position=np.zeros_like(raw)
                for k in range(4):position+=np.einsum('nij,nj->ni',palette[p['joints'][used,k]],raw)*p['weights'][used,k,None]
            else:position=raw@self.rest[p['node']].T
            bounds.append(position[:, :3] @ self.flip.T)
        vertices = np.concatenate(bounds)
        lo = vertices.min(axis=0)
        hi = vertices.max(axis=0)
        self.origin = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
        self.scale = 3.1 / max(hi[1] - lo[1], 0.01)
        from model_analysis import analyze
        self.analysis=analyze(self)
        for part,record in zip(self.parts,self.analysis['parts']):part['analysis']=record

    def array(self, index):
        a = self.g['accessors'][index]
        dtype = np.dtype(DTYPES[a['componentType']])
        width = WIDTHS[a['type']]
        count = a['count']
        if count > 1000000:
            raise ValueError('VRM veri dizisi çok büyük.')
        out = np.zeros((count, width), dtype=dtype)
        if 'bufferView' in a:
            view = self.g['bufferViews'][a['bufferView']]
            if view.get('buffer', 0) != 0:
                raise ValueError('Harici VRM veri bloğu desteklenmiyor.')
            offset = view.get('byteOffset', 0) + a.get('byteOffset', 0)
            stride = view.get('byteStride', dtype.itemsize * width)
            out = np.ndarray((count, width), dtype=dtype, buffer=self.bin, offset=offset, strides=(stride, dtype.itemsize)).copy()
        if 'sparse' in a:
            sp = a['sparse']
            iv = self.g['bufferViews'][sp['indices']['bufferView']]
            vv = self.g['bufferViews'][sp['values']['bufferView']]
            ix = np.frombuffer(self.bin, dtype=DTYPES[sp['indices']['componentType']], count=sp['count'], offset=iv.get('byteOffset', 0) + sp['indices'].get('byteOffset', 0))
            values = np.frombuffer(self.bin, dtype=dtype, count=sp['count'] * width, offset=vv.get('byteOffset', 0) + sp['values'].get('byteOffset', 0)).reshape(-1, width)
            out[ix] = values
        if a.get('normalized') and dtype.kind in 'iu':
            out = np.maximum(out.astype('float32') / np.iinfo(dtype).max, -1)
        return out

@lru_cache(maxsize=3)
def load_data(path):
    return VRMData(path)

class VRMModel:

    def __init__(self, path):
        self.data = load_data(str(Path(path).resolve()))
        from model_compatibility import profile,summary
        if not hasattr(self.data,'compatibility'):self.data.compatibility=profile(self.data)
        if not self.data.compatibility['desktop_supported']:
            raise ValueError('Karakter masaüstü hareketlerine uygun değil: '+summary(self.data.compatibility))
        self.rig = MotionRig()
        self.textures = {}
        self.frames = []
        self.world = self.data.rest.copy()
        self.last_pose = 'idle'
        self.gpu_program = None
        self.gpu_failed = False
        self.uniforms = {}
        self.attributes = {}
        self.last_args = None
        self.palettes = []
        self.bounds = None
        self.sleep_support = 0.0
        self.clip = None
        self.clip_start = 0.0
        self.clip_loop = False
        self.mouth_level = 0.0
        self.walk_clock = None
        self.walk_entry = None
        self.locomotion = None
        self.arm_clearance = 0.
        self.authored_clips = {}
        self.authored_pose = None
        self.authored_start = 0.0
        self.authored_entry = None
        self.transition_entry = None
        self.transition_start = 0.0
        from springs import HairSprings
        self.hair_springs = HairSprings(self.data)
        mesh_names = [str(mesh.get('name', '')).casefold() for mesh in self.data.g.get('meshes', [])]
        self.sleep_body_meshes = {i for i, name in enumerate(mesh_names) if 'body' in name}
        if not self.sleep_body_meshes:
            self.sleep_body_meshes = set(range(len(mesh_names)))
        groups = {}
        for part in self.data.parts:
            key = ('skin', part['skin'], part['mesh']) if part['skin'] is not None and 'joints' in part else ('node', part['node'], part['mesh'])
            group = groups.setdefault(key, {'points': [], 'joints': [], 'weights': []})
            sample = part['pos'][::24]
            group['points'].append(np.column_stack((sample, np.ones(len(sample)))))
            if key[0] == 'skin':
                group['joints'].append(part['joints'][::24])
                group['weights'].append(part['weights'][::24])
        self.bounds_groups = []
        for key, group in groups.items():
            self.bounds_groups.append((key, np.concatenate(group['points']), np.concatenate(group['joints']) if group['joints'] else None, np.concatenate(group['weights']) if group['weights'] else None))
        self.rest_canonical = {name: (self.data.rest[node, :3, 3] @ self.data.flip.T - self.data.origin) * self.data.scale for name, node in self.data.bones.items()}
        from grounding import SoleGround
        self.ground=SoleGround(self.data)
        from hand_pose import HandPoses
        from pose_transition import ArmTransition
        self.hand_poses=HandPoses(self.data,self.hair_springs.physics);self.hand_gesture=None
        from conversation_motion import ConversationMotion
        self.conversation=ConversationMotion()
        from cat_motion import CatMotion
        self.cat_motion=CatMotion(self.data);self.cat_emotion=None
        self.conversation.fit(self.rest_canonical,self.data,self.hair_springs.physics)
        self.arm_transition=ArmTransition(self.data,self.hair_springs.physics)
        from seated_attention import SeatedAttention
        self.seated_attention=SeatedAttention()
        self.seating=None
        # Rest cloth envelope at hip/thigh height; conservative clearance only,
        # not a general cloth collision solver or a model-name heuristic.
        leg=np.mean([np.linalg.norm(self.rest_canonical[s+'LowerLeg']-self.rest_canonical[s+'UpperLeg'])+np.linalg.norm(self.rest_canonical[s+'Foot']-self.rest_canonical[s+'LowerLeg']) for s in ('left','right')])
        hip_y=self.rest_canonical['hips'][1]
        widths=[]
        for part in self.data.parts:
            if part['kind']!='cloth':continue
            points=(part['pos'][::8]@self.data.flip.T-self.data.origin)*self.data.scale
            band=points[(points[:,1]>hip_y-leg*.40)&(points[:,1]<hip_y+.06*leg)]
            if len(band):widths.append(float(np.percentile(np.abs(band[:,0]),95)))
        self.arm_clearance=min(.48*leg,max(widths,default=0.)+.035*leg)
        self.joint_limits = rotation_limits(self.data.bones)
        self.curl_nodes = {node for name, node in self.data.bones.items() if 'Proximal' in name or 'Intermediate' in name}
        self.walk_curl_nodes = {node for name, node in self.data.bones.items() if 'Proximal' in name and 'Thumb' not in name}
        self.motion_paths = {path.stem: path for path in (Path(__file__).parent / 'motions').glob('*.vrma')}
        if 'Yumi-Walk' in self.motion_paths:
            from natural_walk import load_walk
            load_walk().prepare(self.data)

    def frame(self, t, pose, desk, speaking, sleep=0.0):
        pose = pose if pose in ('idle', 'walk', 'wave', 'listen', 'clip') else 'idle'
        desk = 0.0
        sleep = 0.0
        self.last_args = (t, pose, desk, speaking, sleep)
        if pose != self.last_pose:
            if self.last_pose=='clip' and pose in ('idle','wave','listen'):
                self.ground.plant_active=False;self.ground.neutral_pending=True
            self.transition_start = t
            self.transition_entry = {i: np.linalg.inv(self.world[self.data.parents[i]]) @ self.world[i] if i in self.data.parents else self.world[i].copy() for i in self.data.order}
            self.last_pose = pose
        d = self.data
        j = d.bones
        natural_mode=pose=='walk' and 'Yumi-Walk' in self.motion_paths
        targets = None if natural_mode else self.rig.sample(t, pose, desk)
        world = np.empty_like(d.rest)
        mapping = {}
        rest_canonical = self.rest_canonical
        walk_joints = None
        walk_shift = np.zeros(3)
        if pose == 'walk' and 'Yumi-Walk' not in self.motion_paths:
            from gait import sample as sample_walk
            if self.walk_clock is None:
                self.walk_clock = t
                self.walk_entry = {name: (self.world[node, :3, 3] @ d.flip.T - d.origin) * d.scale for name, node in j.items()}
            walk_time=self.locomotion.phase if self.locomotion is not None else t-self.walk_clock
            walk_joints, walk_shift = sample_walk(rest_canonical,walk_time,clearance=self.arm_clearance)
            weight = self.locomotion.weight if self.locomotion is not None else min(1.0, max(0.0, (t - self.walk_clock) / 0.35))
            weight = weight * weight * (3 - 2 * weight)
            walk_joints = {name: self.walk_entry[name] * (1 - weight) + point * weight for name, point in walk_joints.items()}
            walk_shift *= weight
        else:
            self.walk_clock = None
        for side, dummy in ([] if natural_mode else [('left', 'right'), ('right', 'left')]):
            for a, b in [('UpperArm', 'LowerArm'), ('LowerArm', 'Hand'), ('UpperLeg', 'LowerLeg'), ('LowerLeg', 'Foot')]:
                first = side + a
                second = side + b
                if first in j and second in j:
                    source = d.rest[j[second], :3, 3] - d.rest[j[first], :3, 3]
                    direction_canonical = targets[dummy + b] - targets[dummy + a]
                    if walk_joints is not None:
                        direction_canonical = walk_joints[second] - walk_joints[first]
                    direction = d.flip.T @ direction_canonical
                    mapping[j[first]] = aim(source, direction) @ d.rest[j[first], :3, :3]
        if walk_joints is not None:
            for side in ('left', 'right'):
                if side + 'Foot' in j:
                    from gait import foot_roll,PERIOD
                    phase=(walk_time/PERIOD+(0. if side=='left' else .5))%1.
                    pitch=foot_roll(phase)*weight
                    roll=rotation([math.sin(pitch/2),0,0,math.cos(pitch/2)])
                    mapping[j[side + 'Foot']] = d.flip.T@roll@d.flip@d.rest[j[side + 'Foot'], :3, :3]
        gesture_bones = {}
        gesture_face = {}
        gesture_lips = {}
        if speaking and getattr(self, 'conversation', None):
            gesture_bones, gesture_face, gesture_lips = self.conversation.sample(self.mouth_level)
        clip_rotations = {}
        clip_translation = np.zeros(3)
        clip_expression = {}
        if pose == 'clip' and self.clip:
            music_time=getattr(self,'music_clip_time',None)
            clip_rotations, clip_translation, clip_expression = self.clip.pose(t-self.clip_start if music_time is None else music_time, d, loop=self.clip_loop)
            if music_time is not None:
                bound=getattr(self.clip,'max_root_offset',0.)
                canonical_translation=d.flip@clip_translation*d.scale
                distance=float(np.linalg.norm(canonical_translation[[0,2]]))
                if distance>bound:
                    canonical_translation[[0,2]]*=bound/max(distance,1e-9)
                    clip_translation=d.flip.T@canonical_translation/d.scale
            mapping = {}
        authored_name = {'idle': 'Idle_Talking_Loop' if speaking else 'Idle_Loop', 'listen': 'Idle_Talking_Loop', 'wave': 'VRMA_02', 'walk':'Natural_Walk'}.get(pose) if desk < 0.001 and sleep < 0.001 else None
        standing_activity=getattr(self,'scenario_activity',None)
        if standing_activity and standing_activity.kind in ('coffee','window') and standing_activity.scene.phase=='seated' and not speaking:
            authored_name=None
        if speaking and authored_name=='Idle_Talking_Loop' and getattr(self,'conversation',None):
            candidate='Yumi-Gesture-'+self.conversation.intent
            if candidate in self.motion_paths:authored_name=candidate
        if self.seating is not None and self.seating.weight>0:
            authored_name={'lower':'Sitting_Enter','rise':'Sitting_Exit'}.get(self.seating.phase,'Sitting_Talking_Loop' if speaking else None)
        authored = None
        authored_weight = 1.0
        if authored_name:
            from vrma import MotionClip
            path = self.motion_paths.get('Yumi-Walk' if authored_name=='Natural_Walk' else (authored_name if authored_name.startswith(('VRMA_','Yumi-Gesture-')) else 'quaternius-' + authored_name))
            if path is not None:
                if authored_name not in self.authored_clips:
                    if authored_name=='Natural_Walk':
                        from natural_walk import load_walk
                        self.authored_clips[authored_name]=load_walk()
                    else:self.authored_clips[authored_name] = MotionClip(path)
                authored = self.authored_clips[authored_name]
                if self.authored_pose != authored_name:
                    self.authored_start = t
                    self.authored_pose = authored_name
                    self.authored_entry = {i: np.linalg.inv(self.world[d.parents[i]]) @ self.world[i] if i in d.parents else self.world[i].copy() for i in d.order}
                elapsed = t - self.authored_start
                authored_weight = min(1.0, max(0.0, elapsed / 0.4))
                authored_weight = authored_weight ** 2 * (3 - 2 * authored_weight)
                if authored_name=='Natural_Walk':
                    from natural_walk import PLAYBACK_RATE,START_PHASE
                    clock=self.locomotion.phase if self.locomotion is not None else elapsed
                    if self.locomotion is not None:
                        authored_weight=self.locomotion.weight**2*(3-2*self.locomotion.weight)
                    clip_rotations,clip_translation,clip_expression=authored.pose(START_PHASE+clock*PLAYBACK_RATE,d,True)
                else:
                    clip_rotations, clip_translation, clip_expression = authored.pose(elapsed, d, loop=not authored_name.startswith('VRMA_'))
                    clip_translation[[0, 2]] = 0.0
                mapping = {}
        if not authored:
            self.authored_pose = None
        if authored and pose in ('idle','listen','wave'):
            # Standing conversation/wave clips supply the upper body. Imported
            # clips may contain a deep crouch or a lifted leg; those tracks do
            # not belong to a standing desktop gesture. Explicit clips and
            # natural walking retain their complete authored lower body.
            lower_body={j[name] for name in ('hips','leftUpperLeg','rightUpperLeg','leftLowerLeg','rightLowerLeg','leftFoot','rightFoot','leftToes','rightToes') if name in j}
            clip_rotations={node:value for node,value in clip_rotations.items() if node not in lower_body}
            clip_translation=np.zeros(3)
        if authored_name and authored_name.startswith('Yumi-Gesture-'):
            gesture_bones={}
        hand_style=self.hand_gesture
        if not hand_style and speaking and self.conversation.intent=='agree' and self.conversation.variant%3==0:hand_style='thumbs_up'
        if not hand_style and speaking and self.conversation.intent=='uncertain' and self.conversation.variant%4==0:hand_style='shrug'
        if hand_style and not self.hand_poses.supports(hand_style):hand_style='open_palm'
        accent=getattr(self,'music_dance_accent',None)
        if pose=='clip' and accent and not speaking:
            from dance_styles import accents
            gesture_bones=accents(*accent)
        self.active_hand_style=hand_style
        performing=pose=='clip' and getattr(self,'music_clip_time',None) is not None
        self.garment_hanging=bool(performing)
        activity=getattr(self,'scenario_activity',None)
        quiet_standing=bool(activity and activity.kind in ('coffee','window') and activity.scene.phase=='seated' and not activity.cleanup)
        if quiet_standing:
            # This standing scene has no chair weight to replace the generic
            # idle leg targets. Keep the measured neutral stance after arrival.
            for name in ('hips','leftUpperLeg','leftLowerLeg','leftFoot','leftToes','rightUpperLeg','rightLowerLeg','rightFoot','rightToes'):
                if name in j:mapping[j[name]]=d.rest[j[name],:3,:3]
            if not speaking:
                for name in ('spine','chest','upperChest','neck','head'):
                    if name in j:mapping[j[name]]=d.rest[j[name],:3,:3]
        if performing:gesture_bones={};hand_style=None
        if (speaking or hand_style) and not performing and getattr(self, 'conversation', None):
            arm_targets = self.conversation.arm_targets(rest_canonical,hand_style)
            for side in ('left', 'right'):
                for first, second in (('UpperArm', 'LowerArm'), ('LowerArm', 'Hand')):
                    a = side + first
                    b = side + second
                    if a in arm_targets and b in arm_targets:
                        source = d.rest[j[b], :3, 3] - d.rest[j[a], :3, 3]
                        direction = d.flip.T @ (arm_targets[b] - arm_targets[a])
                        mapping[j[a]] = aim(source, direction) @ d.rest[j[a], :3, :3]
        if hand_style=='shrug':
            for side in ('left','right'):
                node=j.get(side+'Shoulder')
                if node is None:continue
                sign=1 if rest_canonical[side+'UpperArm'][0]>=rest_canonical['hips'][0] else -1
                lift=rotation([0.,0.,math.sin(sign*.055),math.cos(.055)])
                mapping[node]=d.flip.T@lift@d.flip@d.rest[node,:3,:3]
        for i in d.order:
            parent = world[d.parents[i]] if i in d.parents else np.eye(4)
            local = d.local[i].copy()
            if pose == 'clip' and self.clip or authored:
                if i in clip_rotations:
                    local[:3, :3] = clip_rotations[i]
                if i == j['hips']:
                    local[:3, 3] += np.linalg.inv(parent[:3, :3]) @ clip_translation
            if i in mapping:
                local[:3, :3] = np.linalg.inv(parent[:3, :3]) @ mapping[i]
            if walk_joints is not None and i == j.get('hips'):
                local[:3, 3] += np.linalg.inv(parent[:3, :3]) @ (d.flip.T @ walk_shift / d.scale)
            if walk_joints is not None and i in self.walk_curl_nodes:
                local[:3, :3] = local[:3, :3] @ rotation([math.sin(0.1), 0, 0, math.cos(0.1)])
            if pose != 'clip' and authored is None:
                cycle = 0.5 - 0.5 * math.cos(t * 1.1)
                chest_pitch = 0.0
                if walk_joints is not None and i in (j.get('spine'),j.get('chest')):
                    yaw=.035*math.sin(2*math.pi*walk_time/1.45)*weight
                    local[:3,:3]=local[:3,:3]@rotation([0,math.sin(yaw/2),0,math.cos(yaw/2)])
                head_pitch = 0.025 * math.sin(t * 1.5) if pose == 'listen' else 0.0
                chest_pitch *= -1
                head_pitch *= -1
                if i == j.get('chest'):
                    local[:3, :3] = local[:3, :3] @ rotation([math.sin(chest_pitch / 2), 0, 0, math.cos(chest_pitch / 2)])
                if i == j.get('head') and not quiet_standing:
                    angle = math.sin(t * 0.8) * 0.025 * (1 - sleep)
                    local[:3, :3] = local[:3, :3] @ rotation([math.sin(head_pitch / 2), 0, 0, math.cos(head_pitch / 2)]) @ rotation([0, math.sin(angle / 2), 0, math.cos(angle / 2)])
            if authored and authored_weight < 1.0:
                entry = self.authored_entry[i]
                blend = entry[:3, :3] * (1 - authored_weight) + local[:3, :3] * authored_weight
                u, _, v = np.linalg.svd(blend)
                local[:3, :3] = u @ np.diag([1, 1, np.linalg.det(u @ v)]) @ v
                local[:3, 3] = entry[:3, 3] * (1 - authored_weight) + local[:3, 3] * authored_weight
            if authored is None and pose != 'walk' and self.transition_entry and (t - self.transition_start < 0.45):
                weight = max(0.0, min(1.0, (t - self.transition_start) / 0.45))
                weight = weight ** 2 * (3 - 2 * weight)
                entry = self.transition_entry[i]
                u, _, v = np.linalg.svd(entry[:3, :3] * (1 - weight) + local[:3, :3] * weight)
                local[:3, :3] = u @ np.diag([1, 1, np.linalg.det(u @ v)]) @ v
                local[:3, 3] = entry[:3, 3] * (1 - weight) + local[:3, 3] * weight
            if gesture_bones:
                for name, angles in gesture_bones.items():
                    if i == j.get(name):
                        for axis, angle in enumerate(angles):
                            q = [0.0, 0.0, 0.0, math.cos(angle / 2)]
                            q[axis] = math.sin(angle / 2)
                            local[:3, :3] = local[:3, :3] @ rotation(q)
            prelimited=natural_mode and authored_weight>=1.0 and not gesture_bones and i in clip_rotations
            if i in self.joint_limits and not prelimited:
                side=next((s for s in ('left','right') if i==j.get(s+'LowerArm')),None)
                if performing and getattr(self.clip,'pole',False) and side:
                    from joint_limits import limit_forearm
                    axis=np.linalg.solve(d.rest[i][:3,:3],d.rest[j[side+'Hand'],:3,3]-d.rest[i,:3,3])
                    local[:3,:3]=limit_forearm(d.local[i][:3,:3],local[:3,:3],axis)
                else:local[:3, :3] = limit_rotation(d.local[i][:3, :3], local[:3, :3], self.joint_limits[i])
            world[i] = parent @ local
        if hand_style:
            side='left' if self.conversation.variant%2==0 else 'right'
            self.hand_poses.apply(world,hand_style,side)
        elif not speaking and pose!='clip':self.hand_poses.relax(world)
        elif performing and not getattr(self.clip,'pole',False):
            for side in ('left','right'):self.hand_poses.fingers(world,side,'relaxed')
        if performing and not getattr(self.clip,'pole',False):
            from dance_contacts import legs
            legs(d,world,self.hair_springs.physics)
        signature=(pose,speaking,self.conversation.intent if speaking else None,self.conversation.variant if speaking else None,hand_style)
        if self.seating is None or self.seating.weight<=0:self.ground.plant(world,pose,t,self.hair_springs.physics)
        music_time=getattr(self,'music_clip_time',None)
        support=getattr(self.clip,'supported',None) if performing else None
        supported=bool(callable(support) and support(music_time,d,world))
        # Aerial choreography must prove post-limit hand contact. Other music
        # clips keep their established sole grounding.
        self.ground.apply(world,'clip' if supported else ('idle' if music_time is not None else pose))
        if self.seating is not None:
            self.speaking_for_seat=speaking;self.seating.apply(world,self);self.ground.points=self.ground.sample(world)
        activity=getattr(self,'scenario_activity',None)
        if activity is not None:activity.apply_pose(world,self)
        self.arm_transition.apply(world,self.world,t,signature)
        self.seated_attention.apply(self,world,t,speaking)
        listening=getattr(self,'music_listen',None)
        if listening and not speaking:
            from hand_pose import turn
            node=j.get('head')
            if node is not None:
                phase,amount=listening
                self.hair_springs.physics._rotate_subtree(world,node,d.flip.T@turn(np.array([1.,0.,0.]),math.sin(phase*math.tau)*amount)@d.flip)
        if getattr(self,'skill_reaction',None) and pose not in ('walk','clip'):
            import time as _time
            from skill_reactions import head_pose
            started,intent=self.skill_reaction;nod=head_pose(intent,_time.perf_counter()-started)
            head=d.bones.get('head')
            if head is not None and abs(nod)>1e-6:
                from hand_pose import turn
                parent=world[d.parents[head],:3,:3]
                local=np.linalg.solve(parent,world[head,:3,:3])@turn(np.array([1.,0.,0.]),nod)
                target=parent@limit_rotation(d.local[head][:3,:3],local,45.)
                self.hair_springs.physics._rotate_subtree(world,head,target@np.linalg.inv(world[head,:3,:3]))
        gripping=performing and getattr(self.clip,'pole',False) or bool(activity and activity.kind in ('coffee','window') and activity.scene.phase=='seated')
        # A carried prop is still held while turning/reaching to put it down.
        # Losing the grip mode here applies the relaxed-arm twist envelope to
        # the solved elbow and moves the wrist away from its placement target.
        if activity and activity.returner and not activity.returner.ready:gripping=True
        self.hair_springs.physics.solve_arms(world,gripping=gripping,preserve_grip=bool(activity and activity.returner and not activity.returner.ready))
        if not gripping and not performing and (activity is None or self.hand_gesture):
            self.arm_transition.limit_final(world,self.world,t,bool(hand_style or speaking))
        if activity and activity.returner:
            from placement_fit import refine
            refine(activity.returner,world)
        if activity is not None:activity.apply_fingers(world,self)
        if performing and not getattr(self.clip,'pole',False):
            from dance_contacts import avoid_head
            avoid_head(d,world,self.hair_springs.physics)
        if activity and activity.kind in ('coffee','window') and activity.event=='sip' and not activity.cleanup:
            from scenario_timeline import pulse
            activity.cup_grip.meet_rim(world,pulse('sip',activity.event_clock))
        self.hair_springs.apply(t, world)
        self.cat_motion.apply(t,world,self,pose,speaking)
        self.world = world
        palettes = [world[nodes] @ inverse for nodes, inverse in d.skins]
        self.palettes = palettes
        expression = {}
        from model_analysis import expression_name
        blink = max(0, 1 - abs(t % 4.6 - 4.25) / 0.09)
        blink_names=['blink'] if expression_name(d,'blink') else ['blinkLeft','blinkRight']
        for name, amount in [(n,blink) for n in blink_names]+[('aa', self.mouth_level if speaking and (not getattr(self, 'conversation', None)) else 0), ('happy', 0.3 if pose == 'wave' else 0)]:
            for mesh, index, weight in d.expressions.get(expression_name(d,name), []):
                expression[mesh, index] = amount * weight
        for name, amount in clip_expression.items():
            for mesh, index, weight in d.expressions.get(expression_name(d,name), []):
                expression[mesh, index] = amount * weight
        if activity is not None and not speaking and not activity.cleanup:
            from scenario_timeline import face as activity_face
            for name,amount in activity_face(activity.event,activity.event_clock).items():
                for mesh,index,weight in d.expressions.get(expression_name(d,name),[]):
                    expression[mesh,index]=max(expression.get((mesh,index),0.),amount*weight)
        if speaking and getattr(self, 'conversation', None):
            for name in dict.fromkeys((*gesture_face,*gesture_lips)):
                target = expression_name(d,name)
                amount = gesture_lips.get(name, gesture_face.get(name, 0.0))
                if name in gesture_lips and (not d.expressions.get(target)):
                    target = expression_name(d,'aa')
                for mesh, index, weight in d.expressions.get(target, []):
                    # Several semantic expressions can share one authored
                    # target. A subtle relaxed layer must not erase a smile.
                    expression[mesh, index] = max(expression.get((mesh, index), 0.0), amount * weight)
        if getattr(self,'skill_reaction',None):
            import time as _time
            from skill_reactions import face
            started,intent=self.skill_reaction;age=_time.perf_counter()-started
            weight=max(0.,min(1.,age/.18,(2.8-age)/.6))
            for name,amount in face(intent,weight).items():
                for mesh,index,value in d.expressions.get(expression_name(d,name),[]):
                    expression[mesh,index]=max(expression.get((mesh,index),0.),amount*value)
        self.expression_weights=expression
        self.frames = []
        bounds_samples = []
        for part in d.parts:
            pos = part['pos']
            for index, delta in part['morphs'].items():
                amount = expression.get((part['mesh'], index), 0)
                if amount:
                    if pos is part['pos']:
                        pos = pos.copy()
                    pos += delta * amount
            if (self.gpu_program is not None or getattr(self,"external_renderer",False)):
                self.frames.append((part, pos, part['normal']))
                continue
            if part['skin'] is not None and 'joints' in part:
                matrices = palettes[part['skin']]
                points = np.c_[pos, np.ones(len(pos), dtype='float32')]
                skin = np.zeros((len(pos), 4), dtype='float32')
                norm = np.zeros((len(pos), 3), dtype='float32')
                for k in range(4):
                    selected = matrices[part['joints'][:, k]]
                    w = part['weights'][:, k, None]
                    skin += np.einsum('nij,nj->ni', selected, points, optimize=True) * w
                    norm += np.einsum('nij,nj->ni', selected[:, :3, :3], part['normal'], optimize=True) * w
                pos = skin[:, :3]
            else:
                pos = (np.c_[pos, np.ones(len(pos))] @ world[part['node']].T)[:, :3]
                norm = part['normal'] @ world[part['node'], :3, :3].T
            pos = (pos @ d.flip.T - d.origin) * d.scale
            norm = norm @ d.flip.T
            from garment_contacts import weights as garment_weights,capsules as garment_capsules,project as garment_project
            contact_weight=garment_weights(self,part)
            if np.any(contact_weight):
                from garment_contacts import rest_points
                rest=rest_points(self,part);hip=d.bones['hips'];frame=world[hip]@np.linalg.inv(d.rest[hip])
                hanging=((np.c_[rest[:,:3],np.ones(len(rest))]@frame.T)[:,:3]@d.flip.T-d.origin)*d.scale
                blend=rest[:,3,None]*float(self.garment_hanging)
                pos=pos*(1-blend)+hanging*blend
                capsule_start,capsule_end=garment_capsules(self)
                center=(self.world[d.bones['hips'],:3,3]@d.flip.T-d.origin)*d.scale
                pos=garment_project(pos,norm,contact_weight,capsule_start,capsule_end,center)
            self.frames.append((part, np.ascontiguousarray(pos, dtype='float32'), np.ascontiguousarray(norm, dtype='float32')))
        if (self.gpu_program is not None or getattr(self,"external_renderer",False)) and (sleep > 0.001 or pose in ('sleep', 'dream', 'snore', 'turn')):
            body_samples = []
            for (kind, index, mesh), points, ids, weights in self.bounds_groups:
                if kind == 'skin':
                    matrices = palettes[index]
                    sampled = np.zeros((len(points), 4))
                    for k in range(4):
                        sampled += np.einsum('nij,nj->ni', matrices[ids[:, k]], points) * weights[:, k, None]
                    sample = sampled[:, :3]
                else:
                    sample = (points @ world[index].T)[:, :3]
                canonical = (sample @ d.flip.T - d.origin) * d.scale
                bounds_samples.append(canonical)
                if mesh in self.sleep_body_meshes:
                    body_samples.append(canonical)
        if bounds_samples or (not (self.gpu_program is not None or getattr(self,"external_renderer",False)) and (sleep > 0.001 or pose in ('sleep', 'dream', 'snore', 'turn'))):
            allpoints = np.concatenate(bounds_samples if (self.gpu_program is not None or getattr(self,"external_renderer",False)) else [p for _, p, _ in self.frames])
            self.bounds = (allpoints.min(axis=0) - 0.012, allpoints.max(axis=0) + 0.012)
            contact = allpoints[(allpoints[:, 1] > 1.1) & (allpoints[:, 1] < 2.45)]
            support_points = np.concatenate(body_samples) if (self.gpu_program is not None or getattr(self,"external_renderer",False)) and body_samples else np.concatenate([p for part, p, _ in self.frames if part['mesh'] in self.sleep_body_meshes]) if not (self.gpu_program is not None or getattr(self,"external_renderer",False)) else allpoints
            contact = support_points[(support_points[:, 1] > 1.1) & (support_points[:, 1] < 2.45)]
            if len(contact):
                torso = contact[(np.abs(contact[:, 0]) < 0.43) & (np.abs(contact[:, 2]) < 0.34)]
                if len(torso):
                    self.sleep_support = float(np.percentile(torso[:, 0] * 0.81915 - torso[:, 2] * 0.57358, 90))

    def hip_height(self):
        d = self.data
        legs = [d.bones[name] for name in ('leftUpperLeg', 'rightUpperLeg')]
        return float(np.mean([((self.world[node, :3, 3] @ d.flip.T - d.origin) * d.scale)[1] for node in legs]))

    def sleep_clearance(self):
        return 0.48 + (self.sleep_support + 0.012) * 0.56

    def texture(self, index):
        if index in self.textures:
            return self.textures[index]
        d = self.data
        image = d.g['images'][d.g['textures'][index]['source']]
        if 'bufferView' not in image:
            raise ValueError('Harici VRM dokusu desteklenmiyor.')
        view = d.g['bufferViews'][image['bufferView']]
        start = view.get('byteOffset', 0)
        q = QImage.fromData(d.bin[start:start + view['byteLength']])
        if q.isNull():
            raise ValueError('VRM dokusu çözümlenemedi.')
        limit = min(4096, int(glGetIntegerv(GL_MAX_TEXTURE_SIZE)))
        if max(q.width(), q.height()) > limit:
            q = q.scaled(limit, limit, aspectMode=__import__('PySide6.QtCore', fromlist=['Qt']).Qt.AspectRatioMode.KeepAspectRatio)
        q = q.convertToFormat(QImage.Format.Format_RGBA8888)
        data = bytes(q.bits())
        tex = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, tex)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, q.width(), q.height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        self.textures[index] = tex
        return tex

    def draw(self):
        d = self.data
        if self.gpu_program is None and (not self.gpu_failed):
            try:
                from vrm_shader import build
                count = max([len(j) for j, ib in d.skins] + [1])
                if int(glGetIntegerv(GL_MAX_VERTEX_UNIFORM_COMPONENTS)) < count * 16 + 256:
                    raise RuntimeError('GPU bone uniform limit')
                self.gpu_program = build(count)
                self.uniforms = {name: glGetUniformLocation(self.gpu_program, name) for name in ('modelBones[0]', 'modelFlip', 'modelOrigin', 'modelScale', 'modelTexture', 'textured', 'toon', 'shadeColor', 'shadeShift', 'shadeToony', 'normalTexture', 'normalMapped', 'normalStrength', 'emissionTexture', 'emissiveMapped', 'emissionColor')}
                self.attributes = {name: glGetAttribLocation(self.gpu_program, name) for name in ('jointId', 'jointWeight')}
                from furniture_contacts import FurnitureContacts
                extra=('furnitureEnabled','deskEnabled','seatHeight','deskHeight','deskShift','contactFrame','contactInverse')+tuple(n for name in FurnitureContacts.names for n in (name,name+'Bounds'))
                self.uniforms.update({name:glGetUniformLocation(self.gpu_program,name) for name in extra})
                self.attributes['contactRoot']=glGetAttribLocation(self.gpu_program,'contactRoot')
                self.attributes['garmentWeight']=glGetAttribLocation(self.gpu_program,'garmentWeight')
                self.attributes['garmentRest']=glGetAttribLocation(self.gpu_program,'garmentRest')
                for name in ('bodyCapsuleStart[0]','bodyCapsuleEnd[0]','garmentCenter','garmentFrame','garmentHanging'):self.uniforms[name]=glGetUniformLocation(self.gpu_program,name)
                self.frame(*self.last_args)
            except Exception as error:
                import logging
                logging.warning('VRM GPU skinning unavailable; CPU fallback: %s', error)
                self.gpu_failed = True
                self.gpu_program = None
        if self.gpu_program is not None:
            glUseProgram(self.gpu_program)
            glUniformMatrix3fv(self.uniforms['modelFlip'], 1, GL_TRUE, np.asarray(d.flip, dtype='float32'))
            glUniform3fv(self.uniforms['modelOrigin'], 1, np.asarray(d.origin, dtype='float32'))
            glUniform1f(self.uniforms['modelScale'], d.scale)
            glUniform1i(self.uniforms['modelTexture'], 0)
            from garment_contacts import capsules
            capsule_start,capsule_end=capsules(self)
            glUniform4fv(self.uniforms['bodyCapsuleStart[0]'],6,capsule_start)
            glUniform4fv(self.uniforms['bodyCapsuleEnd[0]'],6,capsule_end)
            center=(self.world[d.bones['hips'],:3,3]@d.flip.T-d.origin)*d.scale
            glUniform3fv(self.uniforms['garmentCenter'],1,np.asarray(center,dtype='float32'))
            hip=d.bones['hips'];frame=self.world[hip]@np.linalg.inv(d.rest[hip])
            glUniformMatrix4fv(self.uniforms['garmentFrame'],1,GL_TRUE,np.asarray(frame,dtype='float32'))
            glUniform1f(self.uniforms['garmentHanging'],float(getattr(self,'garment_hanging',False)))
            glActiveTexture(GL_TEXTURE0)
            contacts=getattr(self,'furniture_contacts',None)
            if not getattr(self,'furniture_surface_guard',False):contacts=None
            glUniform1i(self.uniforms['furnitureEnabled'],int(contacts is not None))
            if contacts:contacts.bind(self)
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glDisable(GL_LIGHTING)
        glEnable(GL_NORMALIZE)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        properties = d.vrm.get('materialProperties', [])
        parts = sorted(self.frames, key=lambda f: properties[f[0]['material']].get('renderQueue', 2000) if properties else 3000 if d.g['materials'][f[0]['material']].get('alphaMode') == 'BLEND' else 2000)
        samples = int(glGetIntegerv(GL_SAMPLES))
        last_palette = None
        try:
            for part, pos, norm in parts:
                mat = d.g['materials'][part['material']]
                pbr = mat.get('pbrMetallicRoughness', {})
                prop = properties[part['material']] if properties else {}
                floats = prop.get('floatProperties', {})
                vectors = prop.get('vectorProperties', {})
                textures = prop.get('textureProperties', {})
                rgba = vectors.get('_Color', pbr.get('baseColorFactor', [1, 1, 1, 1]))
                glColor4f(*rgba)
                texture = pbr.get('baseColorTexture', {}).get('index')
                if self.gpu_program is not None:
                    if part['skin'] is not None and 'joints' in part:
                        matrices = self.palettes[part['skin']]
                        if 'gpu_joints' not in part:
                            part['gpu_joints'] = part['joints'].astype('float32')
                        ids = part['gpu_joints']
                        weights = part['weights']
                    else:
                        matrices = self.world[part['node']:part['node'] + 1]
                        ids = np.zeros((len(pos), 4), dtype='float32')
                        weights = ids.copy()
                        weights[:, 0] = 1
                    palette_key = ('skin', part['skin']) if part['skin'] is not None and 'joints' in part else ('node', part['node'])
                    if palette_key != last_palette:
                        glUniformMatrix4fv(self.uniforms['modelBones[0]'], len(matrices), GL_TRUE, np.ascontiguousarray(matrices, dtype='float32'))
                        last_palette = palette_key
                    glUniform1i(self.uniforms['textured'], int(texture is not None))
                    glUniform1i(self.uniforms['toon'], int(prop.get('shader') == 'VRM/MToon'))
                    glUniform3fv(self.uniforms['shadeColor'], 1, np.array(vectors.get('_ShadeColor', [1, 1, 1])[:3], dtype='float32'))
                    glUniform1f(self.uniforms['shadeShift'], floats.get('_ShadeShift', 0))
                    glUniform1f(self.uniforms['shadeToony'], floats.get('_ShadeToony', 0))
                    normal = textures.get('_BumpMap', mat.get('normalTexture', {}).get('index'))
                    emission = textures.get('_EmissionMap', mat.get('emissiveTexture', {}).get('index'))
                    for unit, name, index in [(1, 'normalTexture', normal), (2, 'emissionTexture', emission)]:
                        glActiveTexture(GL_TEXTURE0 + unit)
                        if index is not None:
                            glBindTexture(GL_TEXTURE_2D, self.texture(index))
                        glUniform1i(self.uniforms[name], unit)
                    glActiveTexture(GL_TEXTURE0)
                    glUniform1i(self.uniforms['normalMapped'], int(normal is not None))
                    glUniform1f(self.uniforms['normalStrength'], floats.get('_BumpScale', 1))
                    glUniform1i(self.uniforms['emissiveMapped'], int(emission is not None))
                    glUniform3fv(self.uniforms['emissionColor'], 1, np.array(vectors.get('_EmissionColor', mat.get('emissiveFactor', [0, 0, 0]))[:3], dtype='float32'))
                    glEnableVertexAttribArray(self.attributes['jointId'])
                    glVertexAttribPointer(self.attributes['jointId'], 4, GL_FLOAT, GL_FALSE, 0, ids)
                    glEnableVertexAttribArray(self.attributes['jointWeight'])
                    glVertexAttribPointer(self.attributes['jointWeight'], 4, GL_FLOAT, GL_FALSE, 0, weights)
                    from garment_contacts import weights as garment_weights
                    glEnableVertexAttribArray(self.attributes['garmentWeight'])
                    glVertexAttribPointer(self.attributes['garmentWeight'],1,GL_FLOAT,GL_FALSE,0,garment_weights(self,part))
                    from garment_contacts import rest_points
                    glEnableVertexAttribArray(self.attributes['garmentRest'])
                    glVertexAttribPointer(self.attributes['garmentRest'],4,GL_FLOAT,GL_FALSE,0,rest_points(self,part))
                    from furniture_contacts import contact_roots
                    roots=contact_roots(d,part)
                    glEnableVertexAttribArray(self.attributes['contactRoot'])
                    glVertexAttribPointer(self.attributes['contactRoot'],4,GL_FLOAT,GL_FALSE,0,roots)
                if texture is not None:
                    glEnable(GL_TEXTURE_2D)
                    glBindTexture(GL_TEXTURE_2D, self.texture(texture))
                    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
                else:
                    glDisable(GL_TEXTURE_2D)
                cull = int(floats.get('_CullMode', 0 if mat.get('doubleSided') else 2))
                if cull:
                    glEnable(GL_CULL_FACE)
                    glCullFace(GL_BACK if cull == 2 else GL_FRONT)
                else:
                    glDisable(GL_CULL_FACE)
                mode = mat.get('alphaMode', 'OPAQUE')
                glDepthMask(GL_TRUE if floats.get('_ZWrite', 0 if mode == 'BLEND' else 1) else GL_FALSE)
                if mode == 'BLEND':
                    glEnable(GL_BLEND)
                    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
                else:
                    glDisable(GL_BLEND)
                coverage = mode == 'MASK' and samples > 0
                if coverage:
                    glEnable(GL_SAMPLE_ALPHA_TO_COVERAGE)
                else:
                    glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE)
                glEnable(GL_ALPHA_TEST)
                glAlphaFunc(GL_GREATER, 0.02 if coverage else mat.get('alphaCutoff', 0.5) if mode == 'MASK' else 0.02)
                glNormalPointer(GL_FLOAT, 0, norm)
                glVertexPointer(3, GL_FLOAT, 0, pos)
                glTexCoordPointer(2, GL_FLOAT, 0, part['uv'])
                glDrawElements(GL_TRIANGLES, len(part['indices']), GL_UNSIGNED_INT, part['indices'])
        finally:
            if self.gpu_program is not None:
                glDisableVertexAttribArray(self.attributes['jointId'])
                glDisableVertexAttribArray(self.attributes['jointWeight'])
                glDisableVertexAttribArray(self.attributes['contactRoot'])
                glDisableVertexAttribArray(self.attributes['garmentWeight'])
                glDisableVertexAttribArray(self.attributes['garmentRest'])
                glUseProgram(0)
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glPopAttrib()

    def release(self):
        self.hair_springs.close()
        if self.gpu_program is not None:
            glDeleteProgram(self.gpu_program)
            self.gpu_program = None
        if self.textures:
            glDeleteTextures(list(self.textures.values()))
            self.textures.clear()
