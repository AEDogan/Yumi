import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

const renderer = new THREE.WebGLRenderer({ alpha:true, antialias:true, preserveDrawingBuffer:true });
renderer.setClearColor(0,0);renderer.setPixelRatio(Math.min(devicePixelRatio,2));
document.body.append(renderer.domElement);
const scene=new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff,0xa8aabd,2));
const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(-2,4,5);scene.add(light);
const camera=new THREE.PerspectiveCamera(30,1,.01,100);
let vrm=null,generation=0,paused=false,last=performance.now(),framing=null;
let sourceNodes=[],sourceMeshes=[],desktop=false,latestFrame=null;
const desktopRoot=new THREE.Group();scene.add(desktopRoot);
const propTemplates=new Map(),propInstances=new Map();
let frameSerial=0;
let poleMesh=null,poleSpec='';
function clearDesktop(){
  if(poleMesh){poleMesh.removeFromParent();poleMesh.geometry.dispose();poleMesh.material.dispose();poleMesh=null;poleSpec='';}
  for(const instance of propInstances.values()){
    scene.remove(instance.group);
    for(const mesh of instance.meshes.values()){
      const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];materials.forEach(m=>m.dispose());
    }
  }
  propInstances.clear();latestFrame=null;
}
async function propTemplate(url){
  if(propTemplates.has(url))return propTemplates.get(url);
  const promise=(async()=>{
    const gltf=await new GLTFLoader().loadAsync(url);gltf.scene.updateMatrixWorld(true);
    const nodes=await gltf.parser.getDependencies('node');
    return {gltf,nodes,parts:new Map()};
  })();
  propTemplates.set(url,promise);
  return promise;
}
function propGeometry(template,descriptor){
  const key=descriptor.node+':'+descriptor.primitive;
  if(template.parts.has(key))return template.parts.get(key);
  const node=template.nodes[descriptor.node];
  const meshes=node?.isMesh?[node]:(node?.children.filter(n=>n.isMesh)??[]);
  const source=meshes[descriptor.primitive];if(!source)throw Error('Eşya parçası eşlenemedi.');
  const geometry=source.geometry.clone(),position=geometry.attributes.position;
  const point=new THREE.Vector3();
  for(let i=0;i<position.count;i++){source.getVertexPosition(i,point);point.applyMatrix4(source.matrixWorld);position.setXYZ(i,point.x,point.y,point.z);}
  const normal=geometry.attributes.normal,normalMatrix=new THREE.Matrix3().getNormalMatrix(source.matrixWorld);
  if(normal)for(let i=0;i<normal.count;i++){point.fromBufferAttribute(normal,i).applyNormalMatrix(normalMatrix);normal.setXYZ(i,point.x,point.y,point.z);}
  geometry.deleteAttribute('skinIndex');geometry.deleteAttribute('skinWeight');geometry.morphAttributes={};
  geometry.computeBoundingSphere();
  const result={geometry,material:source.material};template.parts.set(key,result);return result;
}
function updateProps(frame){
  const serial=++frameSerial;
  for(const instance of propInstances.values())instance.group.visible=false;
  frame.props.forEach((descriptor,index)=>{
    const key=index+':'+descriptor.url;
    let instance=propInstances.get(key);
    if(!instance){
      instance={group:new THREE.Group(),meshes:new Map(),template:null};
      propInstances.set(key,instance);scene.add(instance.group);
      const token=generation;
      propTemplate(descriptor.url).then(template=>{
        if(token===generation&&propInstances.get(key)===instance)instance.template=template;
      }).catch(()=>{if(token===generation)status.error='Yerel eşya three-vrm çizicisine yüklenemedi.';});
    }
    instance.lastSeen=serial;
    if(!instance.template)return;
    instance.group.visible=true;for(const mesh of instance.meshes.values())mesh.visible=false;
    for(const part of descriptor.parts){
      let mesh=instance.meshes.get(part.part);
      if(!mesh){
        const data=propGeometry(instance.template,part);
        const material=Array.isArray(data.material)?data.material.map(m=>m.clone()):data.material.clone();
        mesh=new THREE.Mesh(data.geometry,material);mesh.matrixAutoUpdate=false;instance.meshes.set(part.part,mesh);instance.group.add(mesh);
      }
      mesh.visible=true;mesh.matrix.fromArray(part.matrix);
      for(const material of (Array.isArray(mesh.material)?mesh.material:[mesh.material])){
        material.userData.sourceOpacity??=material.opacity;
        material.opacity=material.userData.sourceOpacity*descriptor.opacity;
        material.userData.originalTransparent??=material.transparent;
        const transparent=material.opacity<.999||material.userData.originalTransparent;
        if(material.transparent!==!!transparent){material.transparent=!!transparent;material.needsUpdate=true;}
      }
    }
  });
  for(const [key,instance] of propInstances)if(serial-instance.lastSeen>120){
    scene.remove(instance.group);
    for(const mesh of instance.meshes.values())for(const m of(Array.isArray(mesh.material)?mesh.material:[mesh.material]))m.dispose();
    propInstances.delete(key);
  }
  status.pendingProps=Array.from(propInstances.values()).filter(i=>i.lastSeen===serial&&!i.template).length;
  status.visiblePropParts=Array.from(propInstances.values()).reduce((n,i)=>n+(i.group.visible?Array.from(i.meshes.values()).filter(m=>m.visible).length:0),0);
}
function fitCamera(){
  if(!framing)return;const {size,center}=framing;
  const distance=Math.max(size.y,size.x/camera.aspect)*.5/Math.tan(THREE.MathUtils.degToRad(15))*1.16;
  camera.position.set(center.x,center.y,center.z+distance);camera.lookAt(center);
}
const status={engine:'three-vrm',version:'3.5.5',ready:false,error:null,frames:0};
window.yumiVRM={status,
  capture(){return renderer.domElement.toDataURL('image/png');},
  async load(url){
    const token=++generation;status.ready=false;status.error=null;status.url=url;
    clearDesktop();desktop=false;status.desktop=false;status.poseFrames=0;
    try{
      const loader=new GLTFLoader();loader.register(parser=>new VRMLoaderPlugin(parser));
      const gltf=await loader.loadAsync(url);
      const next=gltf.userData.vrm;if(!next)throw new Error('Dosyada desteklenen VRM uzantısı bulunamadı.');
      const nextNodes=await gltf.parser.getDependencies('node');
      if(token!==generation){VRMUtils.deepDispose(next.scene);return;}
      if(vrm){vrm.scene.removeFromParent();VRMUtils.deepDispose(vrm.scene);}
      vrm=next;VRMUtils.rotateVRM0(vrm);scene.add(vrm.scene);vrm.update(0);
      sourceNodes=nextNodes;sourceMeshes=[];
      vrm.scene.traverse(node=>{const association=gltf.parser.associations.get(node);if(node.isMesh&&association?.meshes!==undefined)sourceMeshes.push([node,association.meshes]);});
      const bounds=new THREE.Box3().setFromObject(vrm.scene),size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());
      framing={size,center};fitCamera();
      let meshes=0;vrm.scene.traverse(node=>{if(node.isMesh)meshes++;});
      Object.assign(status,{ready:true,meshes,sourceVersion:vrm.meta?.metaVersion,springs:vrm.springBoneManager?.joints.size??0,size:size.toArray()});
    }catch(error){if(token===generation)status.error=String(error.message??error);}
  },
  pose(pose){vrm?.humanoid.setNormalizedPose(pose);},
  desktopFrame(frame){
    if(!vrm||!status.ready)return;
    if(frame.width>0&&frame.height>0){
      const dpr=Math.max(.75,Math.min(3,frame.dpr??1));if(renderer.getPixelRatio()!==dpr)renderer.setPixelRatio(dpr);
      const size=new THREE.Vector2();renderer.getSize(size);
      if(size.x!==frame.width||size.y!==frame.height)renderer.setSize(frame.width,frame.height,false);
      camera.aspect=frame.width/frame.height;camera.updateProjectionMatrix();
    }
    if(!desktop){
      desktop=true;status.desktop=true;framing=null;
      vrm.scene.rotation.set(0,0,0);vrm.scene.updateMatrix();desktopRoot.add(vrm.scene);
      vrm.humanoid.autoUpdateHumanBones=false;
      camera.fov=35;camera.near=.1;camera.far=40;camera.position.set(0,0,0);camera.rotation.set(0,0,0);camera.updateProjectionMatrix();
    }
    latestFrame=frame;
    if(frame.pole){
      const spec=frame.pole.radius+':'+frame.pole.height;
      if(poleSpec!==spec){
        if(poleMesh){poleMesh.removeFromParent();poleMesh.geometry.dispose();poleMesh.material.dispose();}
        const geometry=new THREE.CylinderGeometry(frame.pole.radius,frame.pole.radius,frame.pole.height,24);geometry.translate(0,frame.pole.height/2,0);
        poleMesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0xa6b3be,metalness:.75,roughness:.28}));poleMesh.matrixAutoUpdate=false;scene.add(poleMesh);poleSpec=spec;
      }
      poleMesh.visible=true;poleMesh.matrix.fromArray(frame.pole.matrix);
    }else if(poleMesh)poleMesh.visible=false;
    desktopRoot.matrixAutoUpdate=false;desktopRoot.matrix.fromArray(frame.matrix);
    frame.nodes.forEach((values,index)=>{
      const node=sourceNodes[index];if(!node)return;
      node.matrixAutoUpdate=false;node.matrix.fromArray(values);node.matrixWorldNeedsUpdate=true;
    });
    const weights=new Map(frame.expressions.map(([mesh,index,value])=>[mesh+':'+index,value]));
    for(const [node,mesh] of sourceMeshes)if(node.morphTargetInfluences)
      for(let i=0;i<node.morphTargetInfluences.length;i++)node.morphTargetInfluences[i]=weights.get(mesh+':'+i)??0;
    updateProps(frame);status.poseFrames=(status.poseFrames??0)+1;
    renderer.render(scene,camera);
    if(status.poseFrames===18){
      desktopRoot.updateMatrixWorld(true);
      const bounds=new THREE.Box3().setFromObject(vrm.scene);
      status.desktopBounds=[bounds.min.toArray(),bounds.max.toArray()];status.desktopMatrix=frame.matrix;
    }
  },
  expression(name,value){vrm?.expressionManager?.setValue(name,Math.max(0,Math.min(1,value)));},
  pause(value){paused=value;last=performance.now();},
  dispose(){generation++;clearDesktop();if(vrm){vrm.scene.removeFromParent();VRMUtils.deepDispose(vrm.scene);vrm=null;}status.ready=false;}
};
function resize(){
  // The desktop WebEngine surface can be hidden/zero-sized. Its Qt host
  // supplies the canvas size; a browser resize must not erase that frame.
  if(desktop)return;
  const width=Math.max(innerWidth,1),height=Math.max(innerHeight,1);renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();fitCamera();
}
addEventListener('resize',resize);resize();
function draw(now){requestAnimationFrame(draw);const dt=Math.min((now-last)/1000,.05);last=now;if(paused)return;
  if(vrm&&!desktop)vrm.update(dt);renderer.render(scene,camera);status.frames++;
  status.drawCalls=renderer.info.render.calls;
}
requestAnimationFrame(draw);
