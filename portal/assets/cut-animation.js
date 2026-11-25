/* Shared, read-only Canvas 2D renderer: no WebGL, CDN, controller or dependencies. */
(function () {
  "use strict";
  var $ = function(id){return document.getElementById(id);};
  var root = $("cut-player");
  if (!root) {
    var search=$("cut-search"), category=$("cut-category");
    if(search && category){
      var filter=function(){var count=0;document.querySelectorAll(".review-card").forEach(function(card){
        var match=(!category.value||card.dataset.category===category.value)&&card.textContent.toLowerCase().indexOf(search.value.trim().toLowerCase())!==-1;
        card.hidden=!match;if(match)count++;
      });$("cut-count").textContent=count+" modelos";};
      search.addEventListener("input",filter);category.addEventListener("change",filter);filter();
    }
    return;
  }
  var canvas=$("cut-canvas"),ctx=canvas.getContext("2d");
  if(!ctx)return;
  function init(data){
    if(data.schema!==1||data.tap_sha256!==root.dataset.hash||!Array.isArray(data.segments)||!data.segments.length||!(data.distance_mm>0))throw Error("Invalid simulation");
    var seg=data.segments,total=data.distance_mm,b=data.bbox,dist=0,playing=false,raf=0,last=0,w=0,h=0;
    var fmt=function(n){return n.toLocaleString("pt-BR",{maximumFractionDigits:1});};
    function locate(d){
      var lo=0,hi=seg.length-1;
      while(lo<hi){var mid=(lo+hi)>>1;if(seg[mid].end_distance_mm<d)lo=mid+1;else hi=mid;}
      var s=seg[lo],start=lo?seg[lo-1].end_distance_mm:0;
      var f=Math.max(0,Math.min(1,(d-start)/(s.end_distance_mm-start)));
      return {i:lo,p:[s.start[0]+(s.end[0]-s.start[0])*f,s.start[1]+(s.end[1]-s.start[1])*f]};
    }
    function paint(){
      if(!w||!h)return;
      var pos=locate(dist),front=$("cut-view").value==="front",dual=$("cut-dual").checked,stock=$("cut-stock").checked;
      var span=Math.max(1,b.width,b.height),pad=span*.035,offset=dual?Math.max(b.height*.6,span*.035):0,depth=front?0:span*.23;
      var angle=+$("cut-angle").value,dx=depth*angle,dy=depth*.48;
      var worldW=b.width+2*pad+Math.abs(dx),worldH=b.height+offset+2*pad+dy;
      var scale=Math.min((w-44)/Math.max(1,worldW),(h-70)/Math.max(1,worldH))*Number($("cut-zoom").value);
      var ox=w/2-(b.x_min+b.width/2+dx/2)*scale,oy=h/2+(b.y_min+b.height/2+offset/2+dy/2)*scale;
      function project(p,z,o){return [ox+(p[0]+z*dx)*scale,oy-(p[1]+o+z*dy)*scale];}
      function polygon(points,fill,stroke){ctx.beginPath();points.forEach(function(p,i){if(i)ctx.lineTo(p[0],p[1]);else ctx.moveTo(p[0],p[1]);});ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.stroke();}}
      function line(a,c,color,width){ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(c[0],c[1]);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();}
      ctx.clearRect(0,0,w,h);ctx.fillStyle="#142630";ctx.fillRect(0,0,w,h);
      var x0=b.x_min-pad,x1=b.x_max+pad,y0=b.y_min-pad,y1=b.y_max+offset+pad;
      if(stock){
        var a=[x0,y0],c=[x1,y0],e=[x1,y1],f=[x0,y1];
        if(!front){
          polygon([project(a,0,0),project(c,0,0),project(c,1,0),project(a,1,0)],"#294752","#577483");
          polygon([project(c,0,0),project(e,0,0),project(e,1,0),project(c,1,0)],"#d4e8f022","#7895a5");
          polygon([project(f,0,0),project(e,0,0),project(e,1,0),project(f,1,0)],"#e1edf133","#7895a5");
        }
        polygon([a,c,e,f].map(function(p){return project(p,0,0);}),"#e1edf11c","#829eac");
      }
      var offsets=dual?[0,offset]:[0];
      offsets.forEach(function(o,k){
        if($("cut-path").checked){ctx.beginPath();var start=project(seg[0].start,0,o);ctx.moveTo(start[0],start[1]);seg.forEach(function(s){var q=project(s.end,0,o);ctx.lineTo(q[0],q[1]);});ctx.strokeStyle="#819ba7";ctx.setLineDash([4,5]);ctx.lineWidth=1;ctx.stroke();ctx.setLineDash([]);}
        for(var i=0;i<=pos.i;i++){var s=seg[i],end=i===pos.i?pos.p:s.end;
          if(!front)polygon([project(s.start,0,o),project(end,0,o),project(end,1,o),project(s.start,1,o)],k?"#efb47c28":"#63d3be30");
          line(project(s.start,0,o),project(end,0,o),k?"#f2b37c":"#65ddbe",2);
        }
        var p=project(pos.p,0,o),q=project(pos.p,1,o),color=k?"#ffb576":"#ffe27f";
        if(!front){line(p,q,color,3);[p,q].forEach(function(pt){ctx.fillStyle="#819ba7";ctx.fillRect(pt[0]-3,pt[1]-7,6,5);});}
        ctx.beginPath();ctx.arc(p[0],p[1],4,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();
      });
      ctx.fillStyle="#b5cbd6";ctx.font="12px Arial";ctx.fillText("XY nominal · "+(dual?"2 fios esquemáticos":"1 fio")+" · superfície percorrida",14,h-13);
      $("cut-percent").textContent=Math.round(dist/total*100)+"%";$("cut-seek").value=Math.round(dist/total*1000);
      $("cut-x").textContent=fmt(pos.p[0])+" mm";$("cut-y").textContent=fmt(pos.p[1])+" mm";$("cut-block").textContent="N"+seg[pos.i].block;
      $("cut-distance").textContent=fmt(dist)+" mm";
    }
    function resize(){var rect=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1);w=rect.width;h=rect.height;canvas.width=Math.max(1,Math.round(w*dpr));canvas.height=Math.max(1,Math.round(h*dpr));ctx.setTransform(dpr,0,0,dpr,0,0);paint();}
    function stop(){playing=false;cancelAnimationFrame(raf);last=0;$("cut-play").textContent="Reproduzir";}
    function tick(t){if(!playing)return;if(last)dist=Math.min(total,dist+Math.min(.1,(t-last)/1000)*total/18*Number($("cut-speed").value));last=t;paint();if(dist>=total)stop();else raf=requestAnimationFrame(tick);}
    function seek(d){stop();dist=Math.max(0,Math.min(total,d));paint();}
    $("cut-play").addEventListener("click",function(){if(playing){stop();return;}if(dist>=total)dist=0;playing=true;$("cut-play").textContent="Pausar";raf=requestAnimationFrame(tick);});
    $("cut-seek").addEventListener("input",function(){seek(total*Number(this.value)/1000);});
    $("cut-reset").addEventListener("click",function(){seek(0);});
    $("cut-next").addEventListener("click",function(){var i=locate(dist).i;if(dist>=seg[i].end_distance_mm-1e-7)i=Math.min(i+1,seg.length-1);seek(seg[i].end_distance_mm);});
    $("cut-prev").addEventListener("click",function(){var i=locate(dist).i;seek(i?seg[i-1].end_distance_mm:0);});
    ["cut-view","cut-angle","cut-zoom","cut-dual","cut-stock","cut-path"].forEach(function(id){$(id).addEventListener("input",paint);$(id).addEventListener("change",paint);});
    document.addEventListener("visibilitychange",function(){if(document.hidden)stop();});
    if($("cut-stage").requestFullscreen){$("cut-full").hidden=false;$("cut-full").addEventListener("click",function(){if(document.fullscreenElement)document.exitFullscreen();else $("cut-stage").requestFullscreen().catch(function(){});});}
    document.addEventListener("fullscreenchange",resize);window.addEventListener("resize",resize);
    $("cut-fallback").hidden=true;canvas.hidden=false;$("cut-controls").hidden=false;$("cut-error").hidden=true;resize();
  }
  fetch(root.dataset.source,{credentials:"same-origin",cache:"no-store"}).then(function(r){if(!r.ok)throw Error("HTTP "+r.status);return r.json();}).then(init).catch(function(){$("cut-error").textContent="Não foi possível carregar a animação desta revisão. A prévia estática permanece disponível.";});
}());
