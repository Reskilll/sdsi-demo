// Pixel-art robots, one per agent. Drawn procedurally on a 16x22 grid so there are no image files to ship.
const BOT_W = 16, BOT_H = 22;
const OUTLINE = '#2b3345';
const SPECS = {
  lead:     { body: '#f4f6fa', accent: '#ff7a59', eye: '#2b3345', ant: 'flag',  eyes: 'dots',    acc: 'tie' },
  audit:    { body: '#cfd8e6', accent: '#2f6fed', eye: '#7fb0ff', ant: 'ball',  eyes: 'visor',   acc: 'none' },
  tech:     { body: '#b9e8cf', accent: '#1f9d6b', eye: '#12372a', ant: 'twin',  eyes: 'cyclops', acc: 'none' },
  speed:    { body: '#ffd9ab', accent: '#ff8c1a', eye: '#4a2a00', ant: 'bolt',  eyes: 'dots',    acc: 'none' },
  mobile:   { body: '#c8eefb', accent: '#00a6d6', eye: '#033a4a', ant: 'ball',  eyes: 'wide',    acc: 'none' },
  a11y:     { body: '#e3cffc', accent: '#8b5cf6', eye: '#2d1b5e', ant: 'twin',  eyes: 'dots',    acc: 'headset' },
  ux:       { body: '#ffd0e0', accent: '#e0457b', eye: '#4a1028', ant: 'ball',  eyes: 'wide',    acc: 'glasses' },
  geo:      { body: '#fff1b0', accent: '#d9a400', eye: '#4a3b00', ant: 'dish',  eyes: 'visor',   acc: 'none' },
  redesign: { body: '#ffbcbc', accent: '#ff5d5d', eye: '#4a0000', ant: 'none',  eyes: 'dots',    acc: 'beret' },
  bench:    { body: '#c4dbff', accent: '#3b82f6', eye: '#0b2a66', ant: 'twin',  eyes: 'dots',    acc: 'tie' },
  deck:     { body: '#cdf3dd', accent: '#10b981', eye: '#06402e', ant: 'ball',  eyes: 'wide',    acc: 'cap' },
  research: { body: '#dde3ff', accent: '#4f46e5', eye: '#1e1b4b', ant: 'dish',  eyes: 'wide',    acc: 'glasses' },
  tenders:  { body: '#f3e3c7', accent: '#c2410c', eye: '#3b1d05', ant: 'flag',  eyes: 'visor',   acc: 'tie' },
};

function drawBot(g, id, o) {
  const s = SPECS[id] || SPECS.lead;
  const P = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(x, y, w, h); };
  // antenna
  const a = s.ant;
  if (a === 'ball' || a === 'bolt' || a === 'flag') { P(7, 1, 2, 2, OUTLINE); P(a === 'flag' ? 8 : 7, 0, a === 'flag' ? 4 : 2, a === 'flag' ? 2 : 1, s.accent); }
  if (a === 'twin') { P(5, 0, 1, 3, OUTLINE); P(10, 0, 1, 3, OUTLINE); P(4, 0, 2, 1, s.accent); P(10, 0, 2, 1, s.accent); }
  if (a === 'dish') { P(7, 1, 2, 2, OUTLINE); P(5, 0, 6, 1, s.accent); }
  // head
  P(3, 3, 10, 9, OUTLINE); P(4, 4, 8, 7, s.body);
  P(2, 6, 1, 3, s.accent); P(13, 6, 1, 3, s.accent); // ears
  // eyes
  const e = s.eye;
  if (o.blink) { P(5, 7, 2, 1, OUTLINE); P(9, 7, 2, 1, OUTLINE); }
  else if (s.eyes === 'dots') { P(5, 6, 2, 2, e); P(9, 6, 2, 2, e); }
  else if (s.eyes === 'wide') { P(5, 5, 3, 3, '#fff'); P(8, 5, 3, 3, '#fff'); P(6, 6, 1, 2, e); P(9, 6, 1, 2, e); }
  else if (s.eyes === 'visor') { P(4, 5, 8, 3, OUTLINE); P(5, 6, 2, 1, e); P(9, 6, 2, 1, e); }
  else { P(6, 5, 4, 4, OUTLINE); P(7, 6, 2, 2, e); } // cyclops
  P(7, 9, 2, 1, OUTLINE); // mouth
  // accessories on the head
  if (s.acc === 'glasses') { P(4, 5, 4, 1, OUTLINE); P(8, 5, 4, 1, OUTLINE); P(7, 6, 2, 1, OUTLINE); }
  if (s.acc === 'headset') { P(2, 4, 1, 5, OUTLINE); P(13, 4, 1, 5, OUTLINE); P(4, 3, 8, 1, OUTLINE); P(2, 9, 3, 1, OUTLINE); }
  if (s.acc === 'beret') { P(4, 2, 8, 2, s.accent); P(8, 1, 2, 1, s.accent); }
  if (s.acc === 'cap') { P(4, 2, 8, 2, s.accent); P(10, 3, 4, 1, s.accent); }
  // torso
  P(4, 12, 8, 6, OUTLINE); P(5, 13, 6, 4, s.body); P(6, 14, 4, 2, s.accent);
  if (s.acc === 'tie') P(7, 12, 2, 4, s.accent);
  // arms and legs by pose
  const arm = (x, y, h) => { P(x, y, 2, h, OUTLINE); P(x + (x < 8 ? 1 : 0), y, 1, h, s.body); };
  const leg = (x, h) => { P(x, 18, 2, h, OUTLINE); };
  if (o.pose === 'type') { arm(2, o.f ? 14 : 15, 3); arm(12, o.f ? 15 : 14, 3); leg(5, 4); leg(9, 4); }
  else if (o.pose === 'cheer') { arm(1, 8, 5); arm(13, 8, 5); leg(5, 4); leg(9, 4); }
  else if (o.pose === 'walk') { arm(2, o.f ? 12 : 13, 5); arm(12, o.f ? 13 : 12, 5); leg(5, o.f ? 4 : 3); leg(9, o.f ? 3 : 4); }
  else { arm(2, 13, 5); arm(12, 13, 5); leg(5, 4); leg(9, 4); }
}

const frameCache = {};
/** Cached 16x22 sprite canvas for an agent in a given pose. */
function botFrame(id, pose = 'idle', f = 0, blink = false) {
  const key = `${id}|${pose}|${f}|${blink}`;
  if (!frameCache[key]) { const c = document.createElement('canvas'); c.width = BOT_W; c.height = BOT_H; drawBot(c.getContext('2d'), id, { pose, f, blink }); frameCache[key] = c; }
  return frameCache[key];
}

const avatarCache = {};
/** Square head-and-shoulders portrait as a data URL (used in the agent list). */
function avatarURL(id) {
  if (!avatarCache[id]) {
    const c = document.createElement('canvas'); c.width = 16; c.height = 16;
    const g = c.getContext('2d'); g.fillStyle = (SPECS[id] || SPECS.lead).accent + '33'; g.fillRect(0, 0, 16, 16);
    g.drawImage(botFrame(id, 'idle'), 0, 0, 16, 16, 0, 1, 16, 16);
    avatarCache[id] = c.toDataURL();
  }
  return avatarCache[id];
}

// 7x7 bitmap icons for the speech bubbles. Deliberately tiny: they hint at the activity, they are not meant to be read.
const ICONS = {
  dots:   ['.......', '.......', '.......', '#.#.#..', '.......', '.......', '.......'],
  gear:   ['#.###.#', '.#####.', '###.###', '##...##', '###.###', '.#####.', '#.###.#'],
  chart:  ['......#', '....#.#', '..#.#.#', '..#.#.#', '#.#.#.#', '#.#.#.#', '#######'],
  doc:    ['#####..', '#...##.', '#...###', '#.....#', '#.###.#', '#.....#', '#######'],
  mag:    ['.###...', '#...#..', '#...#..', '#...#..', '.###...', '....##.', '.....##'],
  phone:  ['.#####.', '.#...#.', '.#...#.', '.#...#.', '.#...#.', '.#.#.#.', '.#####.'],
  warn:   ['...#...', '..#.#..', '..#.#..', '.#...#.', '.#.#.#.', '#.....#', '#######'],
  check:  ['.......', '......#', '.....##', '#...##.', '.#.##..', '..##...', '...#...'],
  bolt:   ['....##.', '...##..', '..##...', '.#####.', '...##..', '..##...', '.##....'],
  brush:  ['......#', '.....##', '....##.', '...##..', '..##...', '.##....', '##.....'],
  eye:    ['.......', '.#####.', '#..#..#', '#.###.#', '#..#..#', '.#####.', '.......'],
  person: ['..###..', '.#####.', '..###..', '...#...', '.#####.', '#.###.#', '..#.#..'],
  flag:   ['#####..', '######.', '#####..', '#......', '#......', '#......', '#......'],
  news:   ['#######', '#.....#', '#.##..#', '#.....#', '#.###.#', '#.....#', '#######'],
  gov:    ['...#...', '.#####.', '#######', '.#.#.#.', '.#.#.#.', '.#.#.#.', '#######'],
};
const AGENT_ICON = { lead: 'flag', audit: 'doc', tech: 'gear', speed: 'bolt', mobile: 'phone', a11y: 'eye', ux: 'chart', geo: 'mag', redesign: 'brush', bench: 'person', deck: 'doc', research: 'news', tenders: 'gov' };
function drawIcon(g, name, x, y, color) {
  const rows = ICONS[name] || ICONS.dots; g.fillStyle = color;
  rows.forEach((row, j) => { for (let i = 0; i < 7; i++) if (row[i] === '#') g.fillRect(x + i, y + j, 1, 1); });
}
