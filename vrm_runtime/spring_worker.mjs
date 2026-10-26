// Persistent local transport. VRM0/1 interpretation and integration are upstream.
import readline from 'node:readline';
import { Object3D, Scene, Matrix4, Vector3 } from 'three';
import { VRMSpringBoneLoaderPlugin } from '@pixiv/three-vrm';

const rigs = new Map();
console.warn = (...args) => process.stderr.write(args.join(' ') + '\n');
async function handle(message) {
  if (message.op === 'close') { rigs.delete(message.id); return {}; }
  if (message.op === 'init') {
    const json = message.json;
    const nodes = json.nodes.map((n, index) => {
      const bone = new Object3D(); bone.name = n.name ?? `node_${index}`;
      bone.userData.index = index;
      new Matrix4().fromArray(message.local[index]).decompose(bone.position, bone.quaternion, bone.scale);
      return bone;
    });
    const parented = new Set();
    json.nodes.forEach((n, i) => (n.children ?? []).forEach(j => { nodes[i].add(nodes[j]); parented.add(j); }));
    const scene = new Scene(); nodes.forEach((n, i) => { if (!parented.has(i)) scene.add(n); });
    scene.updateMatrixWorld(true);
    const parser = { json, getDependencies: async kind => {
      if (kind !== 'node') throw new Error(`Unexpected dependency: ${kind}`);
      return nodes;
    } };
    const gltf = { scene, parser, userData: {} };
    await new VRMSpringBoneLoaderPlugin(parser).afterRoot(gltf);
    const manager = gltf.userData.vrmSpringBoneManager;
    const declared = json.extensions?.VRMC_springBone?.springs?.length || json.extensions?.VRM?.secondaryAnimation?.boneGroups?.length;
    if (declared && !manager) throw new Error('Unsupported authored SpringBone declaration');
    const indices = [...new Set([...(manager?.joints ?? [])].map(j => j.bone.userData.index))];
    if (indices.some(i => !Number.isInteger(i))) throw new Error('Unmapped spring joint');
    rigs.set(message.id, { scene, nodes, manager, indices });
    const declarations=[...(manager?.joints ?? [])].map(j=>({node:j.bone.userData.index,
      stiffness:j.settings.stiffness,dragForce:j.settings.dragForce,gravityPower:j.settings.gravityPower,
      gravityDir:j.settings.gravityDir.toArray(),hitRadius:j.settings.hitRadius}));
    return { engine: 'three-vrm', version: '3.5.5', indices, declarations };
  }
  const rig = rigs.get(message.id);
  if (!rig) throw new Error('Unknown rig');
  if (message.op !== 'step') throw new Error('Unknown operation');
  const { scene, nodes, manager, indices } = rig;
  if (message.local.length !== nodes.length) throw new Error('Node count changed');
  const matrix = new Matrix4();
  nodes.forEach((node, i) => matrix.fromArray(message.local[i]).decompose(node.position, node.quaternion, node.scale));
  scene.updateMatrixWorld(true);
  if (message.reset) manager?.reset();
  // Mouse dragging moves the native window, outside this skeleton's coordinates.
  // Add that bounded inertial force to authored gravity for this integration only.
  const force = new Vector3().fromArray(message.externalForce ?? [0,0,0]);
  if (![force.x,force.y,force.z].every(Number.isFinite)) throw new Error('Invalid external force');
  force.clampLength(0, .35);
  const hairNodes=new Set(message.hairNodes??[]);
  const clothNodes=new Set(message.clothNodes??[]);
  const skirtNodes=new Set(message.skirtNodes??[]);
  const saved=[];
  try {
    for (const joint of manager?.joints ?? []) {
      const settings=joint.settings;
      saved.push([settings,settings.gravityDir.clone(),settings.gravityPower,settings.dragForce]);
      // Dampen garments independently; retain authored stiffness and length.
      const cloth=clothNodes.has(joint.bone.userData.index)&&!hairNodes.has(joint.bone.userData.index);
      const skirt=cloth&&skirtNodes.has(joint.bone.userData.index);
      if(cloth)settings.dragForce=Math.max(settings.dragForce,skirt?.90:.8);
      const combined=settings.gravityDir.clone().multiplyScalar(settings.gravityPower).addScaledVector(force,hairNodes.has(joint.bone.userData.index)?1.3:skirt?.15:cloth?.3:1);
      settings.gravityPower=combined.length();
      if(settings.gravityPower>0)settings.gravityDir.copy(combined).normalize();
    }
    manager?.update(Math.min(Math.max(message.dt, 0), .05));
  } finally {
    for(const [settings,direction,power,drag] of saved){settings.gravityDir.copy(direction);settings.gravityPower=power;settings.dragForce=drag;}
  }
  return { rotations: indices.map(i => [i, nodes[i].quaternion.toArray()]) };
}
// Sequential requests: no concurrent updates of a shared skeleton.
for await (const line of readline.createInterface({ input: process.stdin, crlfDelay: Infinity })) {
  try {
    const request = JSON.parse(line);
    const result = await handle(request);
    process.stdout.write(JSON.stringify({ seq: request.seq, ok: true, result }) + '\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(error.message ?? error) }) + '\n');
  }
}
