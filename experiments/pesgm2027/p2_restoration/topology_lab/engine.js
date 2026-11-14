/* P2 IEEE-123 static phase-terminal topology engine. NO AC POWER FLOW, no controller. */
(function(root){
'use strict';
const SWITCHES=['SW1','SW2','SW3','SW4','SW5','SW6','SW7','SW8'];
const DEFAULT_CLOSED=new Set(SWITCHES.slice(0,6));
const phaseKey=(bus,p)=>bus+':'+p;
function normalized(extra){
 if(!extra || !extra.enabled)return null;
 const pa=Array.from(new Set(extra.phases || [])).sort();
 return {id:'VIRTUAL_TIE',a:String(extra.a),b:String(extra.b),raw_a:String(extra.a)+'.'+pa.join('.'),raw_b:String(extra.b)+'.'+pa.join('.'),pa, pb:pa.slice(),phases:pa.length,kind:'virtual',virtual:true};
}
function calculate(data,faultsLike,closedLike,extra=null){
 const faults=new Set(faultsLike||[]),closed=new Set(closedLike||[]),virtual=normalized(extra);
 const edges=virtual?data.edges.concat([virtual]):data.edges;
 const graph=new Map(), parent=new Map(), topoEdges=new Set();
 const add=(a,b)=>{if(!graph.has(a))graph.set(a,[]);if(!graph.has(b))graph.set(b,[]);graph.get(a).push(b);graph.get(b).push(a);};
 const rootOf=x=>{if(!parent.has(x))parent.set(x,x);if(parent.get(x)!==x)parent.set(x,rootOf(parent.get(x)));return parent.get(x)};
 const active=[],busPairs=[],offline=[];let cycles=0;
 for(const e of edges){
   const isSwitch=e.kind==='switch'||e.kind==='virtual';
   const isClosed=e.kind==='virtual'?closed.has('VIRTUAL_TIE'):closed.has(e.id);
   if(faults.has(e.id)||(isSwitch&&!isClosed)){offline.push(e.id);continue;}
   active.push(e.id);
   for(let i=0;i<e.pa.length;i++)add(phaseKey(e.a,e.pa[i]),phaseKey(e.b,e.pb[i]));
   const pair=[e.a,e.b].sort().join('::');
   // Radiality is checked on distinct bus-level electrical connections; regulator phase parallels collapse.
   if(!topoEdges.has(pair)){
     topoEdges.add(pair);busPairs.push(pair);
     const ra=rootOf(e.a),rb=rootOf(e.b);
     if(ra===rb)cycles++; else parent.set(ra,rb);
   }
 }
 let visited=new Set(),queue=[];
 for(let p=1;p<=3;p++){
   const s=phaseKey(data.source,p);
   if(graph.has(s)){visited.add(s);queue.push(s)}
 }
 for(let i=0;i<queue.length;i++)for(const n of graph.get(queue[i])||[]){if(!visited.has(n)){visited.add(n);queue.push(n)}}
 const served=[],missing=[],totalLoads=data.nodes.reduce((a,n)=>a+n.loads.length,0);
 for(const n of data.nodes)for(const load of n.loads){
   const target=load.need.every(p=>visited.has(phaseKey(load.bus,p)));
   (target?served:missing).push(load);
 }
 const kw=served.reduce((sum,l)=>sum+l.kw,0);
 const totalKW=served.concat(missing).reduce((sum,l)=>sum+l.kw,0);
 const rounded=x=>Math.round((x+Number.EPSILON)*100)/100;
 return {served:served.length,missing:missing.length,totalLoads,kw:rounded(kw),totalKW:rounded(totalKW),disconnectedKW:rounded(totalKW-kw),cycles,radial:cycles===0,
   servedLoads:served.map(x=>x.id), missingLoads:missing.map(x=>x.id),
   reached:Array.from(visited), active,offline};
}
function switchAssignments(data,faults,extra){
 const ids=SWITCHES.concat(extra?.enabled?['VIRTUAL_TIE']:[]);
 const all=[];for(let m=0;m<1<<ids.length;m++){
  const closed=[];
  for(let i=0;i<ids.length;i++)if(m&(1<<i))closed.push(ids[i]);
  if(closed.some(id=>new Set(faults).has(id)))continue;
  const result=calculate(data,faults,closed,extra);
  if(result.radial){all.push({closed,result});}
 }
 return all;
}
function rank(data,faults,currentlyClosed,extra=null,limit=12){
 const current=new Set(currentlyClosed||[]),faultSet=new Set(faults||[]);
 const all=switchAssignments(data,faults,extra);
 const enriched=all.map(({closed,result})=>{
   const s=new Set(closed),moves=SWITCHES.concat(extra?.enabled?['VIRTUAL_TIE']:[]).filter(id=>!faultSet.has(id)&&current.has(id)!==s.has(id)).length;
   return {closed,result,moves};
 });
 enriched.sort((a,b)=>b.result.kw-a.result.kw || a.moves-b.moves || b.result.served-a.result.served || a.closed.join(',').localeCompare(b.closed.join(',')));
 return {feasible:all.length, candidates:enriched.slice(0,limit), best:enriched.length?enriched[0]:null};
}
function busPhaseInventory(data){
 const map=new Map();
 for(const n of data.nodes)map.set(n.id,new Set());
 for(const e of data.edges){for(const p of e.pa)map.get(e.a).add(p);for(const p of e.pb)map.get(e.b).add(p)}
 return map;
}
const API={SWITCHES,DEFAULT_CLOSED:Array.from(DEFAULT_CLOSED),calculate,rank,busPhaseInventory};
if(typeof module!=='undefined'&&module.exports)module.exports=API;
root.P2Engine=API;
})(typeof globalThis!=='undefined'?globalThis:this);
