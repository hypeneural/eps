/* Optional orbital read-only renderer. All modules are local and version-pinned. */
import * as THREE from "./three.module.min.js";
import { OrbitControls } from "./OrbitControls.js";

export function createCutThree(host, data, onFailure) {
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));
  renderer.setClearColor(0x142630);
  host.appendChild(renderer.domElement);
  const scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera(38,1,.01,100);
  const controls=new OrbitControls(camera,renderer.domElement);
  controls.enableDamping=false;
  const b=data.bbox, span=Math.max(b.width,b.height,1), depth=.38, gap=Math.max(b.height/span*.62,.05);
  const X=x=>(x-b.x_min-b.width/2)/span, Y=y=>(y-b.y_min)/span;
  const point=(p,z=0,o=0)=>new THREE.Vector3(X(p[0]),Y(p[1])+o,z);
  const groups=[new THREE.Group(),new THREE.Group()]; groups.forEach(g=>scene.add(g));
  const light=new THREE.HemisphereLight(0xf0faff,0x253747,2);scene.add(light);
  const sun=new THREE.DirectionalLight(0xffffff,2);sun.position.set(1,3,2);scene.add(sun);
  const material=(color,opacity=1)=>new THREE.MeshStandardMaterial({color,roughness:.85,transparent:opacity<1,opacity,depthWrite:opacity===1});
  const frameMat=material(0x54788a), stockMat=material(0xe5f0f6,.25);
  const frame=new THREE.Group();scene.add(frame);
  function box(w,h,d,x,y,z,mat,group){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);mesh.position.set(x,y,z);group.add(mesh);return mesh;}
  const width=Math.max(b.width/span,.025),height=Math.max(b.height/span,.025);
  box(width+.18,.045,depth+.14,0,-.065,depth/2,frameMat,frame);
  for(const x of [-width/2-.08,width/2+.08])for(const z of [-.06,depth+.06]){
    box(.025,height+gap+.18,.025,x,(height+gap+.06)/2,z,frameMat,frame);
  }
  for(const z of [-.06,depth+.06])box(width+.18,.025,.025,0,height+gap+.12,z,frameMat,frame);
  const stock=box(width+.03,height+gap+.03,depth,0,(height+gap)/2,depth/2,stockMat,scene);
  const stockSingle=box(width+.03,height+.03,depth,0,height/2,depth/2,stockMat,scene);
  const wires=[];
  const segments=data.segments;
  groups.forEach((g,k)=>{
    const o=k?gap:0,col=k?0xff8a5b:0xffd166,cut=k?0xf0a479:0x65ddbe;
    const verts=[],faces=[];
    segments.forEach(s=>{
      const a=point(s.start,0,o),b=point(s.end,0,o),c=point(s.end,depth,o),d=point(s.start,depth,o);
      verts.push(...a.toArray(),...b.toArray());
      for(const v of [a,b,c,a,c,d])faces.push(...v.toArray());
    });
    const lines=new THREE.BufferGeometry();lines.setAttribute("position",new THREE.Float32BufferAttribute(verts,3));
    const remaining=new THREE.LineSegments(lines,new THREE.LineBasicMaterial({color:0x91a6b4,transparent:true,opacity:.4}));g.add(remaining);
    const doneGeom=lines.clone();const done=new THREE.LineSegments(doneGeom,new THREE.LineBasicMaterial({color:cut}));g.add(done);
    const surfaceGeom=new THREE.BufferGeometry();surfaceGeom.setAttribute("position",new THREE.Float32BufferAttribute(faces,3));
    const surface=new THREE.Mesh(surfaceGeom,new THREE.MeshBasicMaterial({color:cut,side:THREE.DoubleSide,transparent:true,opacity:.25,depthWrite:false}));g.add(surface);
    const wireGeom=new THREE.BufferGeometry();wireGeom.setAttribute("position",new THREE.Float32BufferAttribute(new Float32Array(6),3));
    const wire=new THREE.Line(wireGeom,new THREE.LineBasicMaterial({color:col}));wire.frustumCulled=false;g.add(wire);
    const tips=[0,depth].map(()=>{const m=new THREE.Mesh(new THREE.SphereGeometry(.009,12,8),new THREE.MeshBasicMaterial({color:col}));g.add(m);return m;});
    const partialGeom=new THREE.BufferGeometry();partialGeom.setAttribute("position",new THREE.Float32BufferAttribute(new Float32Array(6),3));
    const partial=new THREE.Line(partialGeom,new THREE.LineBasicMaterial({color:cut}));partial.frustumCulled=false;g.add(partial);
    const partialSurfaceGeom=new THREE.BufferGeometry();partialSurfaceGeom.setAttribute("position",new THREE.Float32BufferAttribute(new Float32Array(18),3));
    const partialSurface=new THREE.Mesh(partialSurfaceGeom,new THREE.MeshBasicMaterial({color:cut,side:THREE.DoubleSide,transparent:true,opacity:.25,depthWrite:false}));partialSurface.frustumCulled=false;g.add(partialSurface);
    wires.push({o,remaining,doneGeom,surfaceGeom,wireGeom,tips,partialGeom,partialSurfaceGeom});
  });
  const nominal=new THREE.Group();scene.add(nominal);
  const regions=data.regions;
  if(regions&&regions.demonstrable){
    [regions.lower_region_xy,regions.upper_region_xy].forEach((ring,i)=>{
      const shape=new THREE.Shape();ring.forEach((p,j)=>{const x=X(p[0]),y=Y(p[1]);if(j)shape.lineTo(x,y);else shape.moveTo(x,y);});shape.closePath();
      const geo=new THREE.ExtrudeGeometry(shape,{depth,bevelEnabled:false,steps:1});
      const mesh=new THREE.Mesh(geo,material(i?0x94aeba:0xf2f5f7));mesh.position.y=i?.025:-.025;nominal.add(mesh);
    });
  }
  nominal.visible=false;
  function draw(){renderer.render(scene,camera);}
  function fit(front=false){controls.target.set(0,(height+gap)/2,depth/2);camera.position.set(front?0:1.4,front?controls.target.y:1.15,front?2.2:1.8);controls.update();draw();}
  function resize(){const rect=host.getBoundingClientRect();if(rect.width&&rect.height){renderer.setSize(rect.width,rect.height,false);camera.aspect=rect.width/rect.height;camera.updateProjectionMatrix();draw();}}
  controls.addEventListener("change",draw);
  const lost=e=>{e.preventDefault();onFailure();};renderer.domElement.addEventListener("webglcontextlost",lost);
  fit();resize();
  function attr(geo,points){const a=geo.getAttribute("position");a.array.set(points.flatMap(v=>v.toArray()));a.needsUpdate=true;}
  function update(pos,options){
    frame.visible=options.machine;groups[1].visible=options.dual;
    stock.visible=options.stock&&options.dual;stockSingle.visible=options.stock&&!options.dual;
    nominal.visible=Boolean(options.result&&regions&&regions.demonstrable);
    groups[0].visible=!nominal.visible;groups[1].visible=options.dual&&!nominal.visible;
    wires.forEach(v=>{
      v.remaining.visible=options.path;
      v.doneGeom.setDrawRange(0,pos.i*2);v.surfaceGeom.setDrawRange(0,pos.i*6);
      const a=point(segments[pos.i].start,0,v.o),b=point(pos.p,0,v.o),c=point(pos.p,depth,v.o),d=point(segments[pos.i].start,depth,v.o);
      attr(v.wireGeom,[b,c]);v.tips[0].position.copy(b);v.tips[1].position.copy(c);
      attr(v.partialGeom,[a,b]);attr(v.partialSurfaceGeom,[a,b,c,a,c,d]);
    });draw();
  }
  function dispose(){controls.dispose();renderer.domElement.removeEventListener("webglcontextlost",lost);scene.traverse(o=>{if(o.geometry)o.geometry.dispose();if(o.material)o.material.dispose();});renderer.dispose();renderer.domElement.remove();}
  return {update,resize,fit,dispose};
}
