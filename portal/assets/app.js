/* ES5 baseline: browsing/downloads do not require this script. */
(function(){
  var filter=document.getElementById('filters'),list=document.getElementById('models');
  if(filter&&list){var search=document.getElementById('search'),category=document.getElementById('category'),toggle=document.getElementById('list-toggle'),cards=list.getElementsByTagName('article');
    function norm(s){s=s.toLowerCase();return s.normalize?s.normalize('NFD').replace(/[\u0300-\u036f]/g,''):s;}
    function refresh(){var count=0,i,card,q=norm(search.value);for(i=0;i<cards.length;i++){card=cards[i];var show=norm(card.getAttribute('data-search')).indexOf(q)!==-1&&(!category.value||category.value===card.getAttribute('data-category'));card.hidden=!show;if(show){count++;}}document.getElementById('results').textContent=count+' modelo(s)';document.getElementById('empty').hidden=count!==0;}
    search.oninput=refresh;category.onchange=refresh;toggle.onclick=function(){var active=list.className.indexOf('list-mode')!==-1;list.className=active?'models':'models list-mode';toggle.setAttribute('aria-pressed',String(!active));toggle.textContent=active?'Modo lista':'Modo galeria';};filter.hidden=false;
  }
  var button=document.getElementById('load-3d');
  if(!button){return;}
  var canvas=document.createElement('canvas'),modern=('noModule' in document.createElement('script'))&&window.customElements;
  try{modern=modern&&canvas.getContext('webgl2');}catch(e){modern=false;}
  var message=document.getElementById('viewer-message');
  if(!modern){message.textContent='Visualização 3D não disponível neste navegador.';return;}
  button.hidden=false;
  button.onclick=function(){button.disabled=true;message.textContent='Carregando visualizador…';var script=document.createElement('script');script.type='module';
    // Pinned optional CDN, fetched only after a click. A local vendor can be supplied later.
    script.src='https://ajax.googleapis.com/ajax/libs/model-viewer/4.4.0/model-viewer.min.js';
    script.onerror=function(){message.textContent='Não foi possível carregar o 3D. Use as imagens ou baixe o GLB.';button.disabled=false;};
    script.onload=function(){window.customElements.whenDefined('model-viewer').then(function(){var viewer=document.createElement('model-viewer');viewer.setAttribute('src',button.getAttribute('data-model'));viewer.setAttribute('poster',button.getAttribute('data-poster'));viewer.setAttribute('alt','Modelo tridimensional EPS');viewer.setAttribute('camera-controls','');viewer.setAttribute('touch-action','pan-y');viewer.setAttribute('shadow-intensity','0.6');viewer.addEventListener('error',function(){message.textContent='Falha ao abrir o modelo. As imagens continuam disponíveis.';});viewer.addEventListener('load',function(){message.textContent='Arraste para girar; use a roda para ampliar.';});document.getElementById('viewer').appendChild(viewer);button.hidden=true;});};
    document.head.appendChild(script);
  };
}());