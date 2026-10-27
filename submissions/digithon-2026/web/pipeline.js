// The landing screen's pipeline: 50 hardcoded Indian company names (banks, e-commerce, healthcare, infrastructure, manufacturing, FMCG)
// and the rules for how a website moves through the agents. These entries are simulated demo activity, not analyses of those companies.
// Kept free of page code so it can be tested on its own (see src/test/pipeline.test.ts).
const PIPE_COMPANIES = [
  // Banking and finance
  ['ICICI Bank', 'Banking', 'icicibank.com'], ['State Bank of India', 'Banking', 'sbi.co.in'], ['Axis Bank', 'Banking', 'axisbank.com'], ['Kotak Mahindra Bank', 'Banking', 'kotak.com'],
  ['Bank of Baroda', 'Banking', 'bankofbaroda.in'], ['Punjab National Bank', 'Banking', 'pnbindia.in'], ['IndusInd Bank', 'Banking', 'indusind.com'], ['Bajaj Finance', 'Finance', 'bajajfinserv.in'],
  // E-commerce
  ['Flipkart', 'E-commerce', 'flipkart.com'], ['Myntra', 'E-commerce', 'myntra.com'], ['Nykaa', 'E-commerce', 'nykaa.com'], ['Meesho', 'E-commerce', 'meesho.com'], ['BigBasket', 'E-commerce', 'bigbasket.com'],
  ['Tata CLiQ', 'E-commerce', 'tatacliq.com'], ['FirstCry', 'E-commerce', 'firstcry.com'], ['Zomato', 'E-commerce', 'zomato.com'], ['Swiggy', 'E-commerce', 'swiggy.com'],
  // Healthcare
  ['Apollo Hospitals', 'Healthcare', 'apollohospitals.com'], ['Fortis Healthcare', 'Healthcare', 'fortishealthcare.com'], ['Max Healthcare', 'Healthcare', 'maxhealthcare.in'], ['Manipal Hospitals', 'Healthcare', 'manipalhospitals.com'],
  ['Narayana Health', 'Healthcare', 'narayanahealth.org'], ['Practo', 'Healthcare', 'practo.com'], ['Dr Lal PathLabs', 'Healthcare', 'lalpathlabs.com'], ['Sun Pharma', 'Pharma', 'sunpharma.com'],
  // Infrastructure
  ['Larsen & Toubro', 'Infrastructure', 'larsentoubro.com'], ['Adani Ports', 'Infrastructure', 'adaniports.com'], ['GMR Airports', 'Infrastructure', 'gmrgroup.in'], ['Tata Projects', 'Infrastructure', 'tataprojects.com'],
  ['IRB Infrastructure', 'Infrastructure', 'irb.co.in'], ['NTPC', 'Infrastructure', 'ntpc.co.in'], ['Power Grid', 'Infrastructure', 'powergrid.in'], ['DLF', 'Real estate', 'dlf.in'],
  // Manufacturing
  ['Tata Steel', 'Manufacturing', 'tatasteel.com'], ['JSW Steel', 'Manufacturing', 'jsw.in'], ['Mahindra & Mahindra', 'Manufacturing', 'mahindra.com'], ['Bajaj Auto', 'Manufacturing', 'bajajauto.com'],
  ['Hero MotoCorp', 'Manufacturing', 'heromotocorp.com'], ['Maruti Suzuki', 'Manufacturing', 'marutisuzuki.com'], ['Ashok Leyland', 'Manufacturing', 'ashokleyland.com'], ['Havells', 'Manufacturing', 'havells.com'], ['Asian Paints', 'Manufacturing', 'asianpaints.com'],
  // FMCG
  ['Hindustan Unilever', 'FMCG', 'hul.co.in'], ['ITC', 'FMCG', 'itcportal.com'], ['Nestlé India', 'FMCG', 'nestle.in'], ['Britannia', 'FMCG', 'britannia.co.in'], ['Dabur', 'FMCG', 'dabur.com'],
  ['Godrej Consumer Products', 'FMCG', 'godrejcp.com'], ['Marico', 'FMCG', 'marico.com'], ['Tata Consumer Products', 'FMCG', 'tataconsumer.com'],
].map(([name, sector, domain]) => ({ name, sector, domain }));

// Government tenders the Tender Scout picks up from tender portals and RSS feeds (simulated: titles and outcomes are demo data).
// `fit` is the triage result: a relevant tender goes on through the agents, the rest stop at triage.
const PIPE_TENDERS = [
  ['Ministry of Electronics and IT', 'meity.gov.in', 'Website revamp and GIGW accessibility audit', 'GeM portal', true, 'Web, accessibility'],
  ['Delhi Metro Rail Corporation', 'delhimetrorail.com', 'Civil works for depot expansion', 'CPPP RSS feed', false, 'Civil works, not digital'],
  ['Indian Railways (IRCTC)', 'irctc.co.in', 'Booking app speed and mobile upgrade', 'CPPP RSS feed', true, 'Mobile, performance'],
  ['Pune Smart City', 'punesmartcity.in', 'CCTV hardware supply and installation', 'State tender feed', false, 'Hardware supply'],
  ['Kerala State IT Mission', 'itmission.kerala.gov.in', 'Multilingual citizen services portal', 'State tender feed', true, 'Portal, languages'],
  ['UIDAI', 'uidai.gov.in', 'Accessibility compliance for the public website', 'GeM portal', true, 'Accessibility'],
].map(([name, domain, title, source, fit, why]) => ({ name, sector: 'Govt tender', domain, tender: { title, source, fit, why } }));

/** Where a website is on its way to a finished deck. `secs` is how long the agent works on it in this demo. */
const PIPE_STAGES = [
  { key: 'queued', label: 'Waiting for an agent', agent: 'lead', secs: 3 },
  { key: 'research', label: 'Researching the company', agent: 'research', secs: 4 },
  { key: 'audit', label: 'Auditing the site', agent: 'audit', secs: 6 },
  { key: 'stack', label: 'Reading the tech stack', agent: 'tech', secs: 5 },
  { key: 'design', label: 'Designing the new homepage', agent: 'redesign', secs: 7 },
  { key: 'match', label: 'Matching our people', agent: 'bench', secs: 5 },
  { key: 'deck', label: 'Writing the deck', agent: 'deck', secs: 5 },
];
/** Which agents work on an item at each stage. */
const PIPE_WORKING = { queued: ['lead'], tender: ['tenders'], research: ['research'], audit: ['audit', 'speed', 'mobile', 'a11y', 'ux', 'geo'], stack: ['tech'], design: ['redesign'], match: ['bench'], deck: ['deck'] };

/**
 * A stand-in for the dashboard when it is not open: four websites staggered through the pipeline on the wall clock,
 * so every page shows the same simulated activity at the same moment. Returns agent id -> what it is doing.
 */
function pipeSimulatedActivity(nowMs) {
  const doing = {}, cycle = PIPE_TOTAL_SECS, t = nowMs / 1000;
  const at = (list, i) => list[((i % list.length) + list.length) % list.length];
  for (let k = 0; k < 4; k++) {
    const start = t - k * (cycle / 4), n = Math.floor(start / cycle), c = k === 3 ? at(PIPE_TENDERS, n) : at(PIPE_COMPANIES, n * 4 + k);
    const stages = pipeStagesFor(c), stage = stages[pipeStageIndex(start - n * cycle, stages)];
    if (!stage) continue;
    (PIPE_WORKING[stage.key] || []).forEach((a) => { doing[a] ??= `${stage.label} · ${c.name}`; });
    if (stage.key !== 'queued') doing.lead ??= `Coordinating ${c.name}`;
  }
  return doing;
}

const PIPE_TENDER_STAGE = { key: 'tender', label: 'Triaging a government tender', agent: 'tenders', secs: 6 };
const pipeTotal = (stages) => stages.reduce((a, s) => a + s.secs, 0);
const PIPE_TOTAL_SECS = pipeTotal(PIPE_STAGES);

/** The stages an item goes through: a tender is triaged first, and only a relevant one carries on to the agents. */
function pipeStagesFor(item) {
  if (!item.tender) return PIPE_STAGES;
  return item.tender.fit ? [PIPE_TENDER_STAGE, ...PIPE_STAGES.slice(1)] : [PIPE_TENDER_STAGE];
}
/** Index into `stages` for an item `elapsedSecs` after it entered the pipeline; stages.length means finished. */
function pipeStageIndex(elapsedSecs, stages = PIPE_STAGES) {
  let t = 0;
  for (let i = 0; i < stages.length; i++) { t += stages[i].secs; if (elapsedSecs < t) return i; }
  return stages.length;
}
/** 0 to 1 across the whole pipeline. */
const pipeProgress = (elapsedSecs, stages = PIPE_STAGES) => Math.max(0, Math.min(1, elapsedSecs / pipeTotal(stages)));

/** Small seeded random numbers, so the sample history looks the same on every visit. */
function pipeRandom(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

/** The company name for a saved report: the title segment that matches the site's domain, else the first short one. */
function pipeBrand(title, url) {
  let host = ''; try { host = new URL(url).hostname.replace(/^www\./, ''); } catch { /* keep empty */ }
  const clean = (x) => x.toLowerCase().replace(/[^a-z0-9]/g, '');
  const label = clean(host.split('.')[0]);
  const segs = String(title || '').split(/[|\-–—:·•]/).map((s) => s.trim()).filter((s) => s.length > 1 && s.length < 40);
  const hit = label.length > 2 ? segs.filter((s) => clean(s).includes(label)).sort((a, b) => a.length - b.length)[0] : undefined;
  return hit ?? segs.find((s) => s.length < 28) ?? (host || 'Website');
}
