// Renders assets/brand/ai-background.png: a dark navy slide background with a blue glow and a soft neural network. Run: npx tsx scripts/build-ai-background.ts
import { chromium } from 'playwright';
import { chromiumExecutable } from '../src/tools/browser.js';
const html = `<body style="margin:0;background:#050B2E"><canvas id=c width=2667 height=1500 style="width:1333px;height:750px"></canvas><script>
const c=document.getElementById('c'),x=c.getContext('2d');let s=7;const R=()=>(s=(s*16807)%2147483647)/2147483647;
let g=x.createRadialGradient(2000,350,0,2000,350,1700);g.addColorStop(0,'#2D69E2');g.addColorStop(.35,'#12308f');g.addColorStop(1,'#050B2E');x.fillStyle=g;x.fillRect(0,0,2667,1500);
g=x.createRadialGradient(300,1400,0,300,1400,1100);g.addColorStop(0,'rgba(45,105,226,.45)');g.addColorStop(1,'rgba(5,11,46,0)');x.fillStyle=g;x.fillRect(0,0,2667,1500);
const P=[];for(let i=0;i<90;i++)P.push([R()*2667,R()*1500,1.5+R()*3.5]);
for(const a of P)for(const b of P){const d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(d<330){x.strokeStyle='rgba(160,195,255,'+(0.28*(1-d/330))+')';x.lineWidth=1.5;x.beginPath();x.moveTo(a[0],a[1]);x.lineTo(b[0],b[1]);x.stroke();}}
for(const p of P){x.fillStyle='rgba(200,222,255,.85)';x.beginPath();x.arc(p[0],p[1],p[2],0,7);x.fill();x.fillStyle='rgba(120,170,255,.18)';x.beginPath();x.arc(p[0],p[1],p[2]*4,0,7);x.fill();}
</script>`;
const b = await chromium.launch({ executablePath: chromiumExecutable() }); const pg = await b.newPage({ viewport: { width: 1333, height: 750 }, deviceScaleFactor: 2 });
await pg.setContent(html); await pg.screenshot({ path: 'assets/brand/ai-background.png', clip: { x: 0, y: 0, width: 1333, height: 750 } }); await b.close(); console.log('ok');
