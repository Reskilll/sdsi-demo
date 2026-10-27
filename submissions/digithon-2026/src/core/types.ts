export interface NetRequest {
  url: string;
  host: string;
  /** Chrome resource type: Document, Script, Stylesheet, Image, Font, XHR, Fetch, Media, Other. */
  type: string;
  mime: string;
  bytes: number;
  status: number;
  thirdParty: boolean;
}

export interface CrawlData {
  url: string;
  finalUrl: string;
  origin: string;
  title: string;
  description: string;
  lang: string;
  viewportMeta: boolean;
  h1s: string[];
  sections: { heading: string; text: string }[];
  nav: { text: string; href: string }[];
  ctas: { text: string; href: string }[];
  images: { src: string; alt: string }[];
  imageCount: number;
  missingAlt: number;
  logo: string | null;
  ogImage: string | null;
  /** The site's own name (og:site_name), when it declares one. */
  siteName?: string;
  colors: { bg: string; text: string; primary: string };
  fonts: string[];
  jsonLd: unknown[];
  heroText: string;
  bodySample: string;
  scriptCount: number;
  bytes: number;
  requests: number;
  perf: { lcp: number; cls: number; ttfb: number; load: number; fcp: number };
  robotsTxt: string | null;
  llmsTxt: boolean;
  shotDesktop: string;
  /** What a HAR would hold: every request the page made (capped). Used for the tech and traffic analysis. */
  network: NetRequest[];
  /** Response headers of the main document (lower-case names). */
  headers: Record<string, string>;
  /** Cookie names only, never values. */
  cookieNames: string[];
  /** Page HTML after load (capped); used for signature matching only. */
  html: string;
  /** Names of notable window globals present on the page. */
  globals: string[];
}

export type Category = 'speed' | 'mobile' | 'a11y' | 'ux' | 'geo';

export interface Finding {
  id: string;
  category: Category;
  /** 1 = minor, 3 = severe. */
  severity: 1 | 2 | 3;
  title: string;
  evidence: string;
  fix: string;
  /** Business impact sentence for the CMO. */
  impact: string;
  /** Org skill ids needed to fix this. */
  skills: string[];
}

export interface CategoryResult {
  category: Category;
  score: number;
  grade: string;
  headline: string;
  metrics: Record<string, string | number>;
  findings: Finding[];
  method: string;
}

export interface AuditReport {
  overall: number;
  grade: string;
  categories: CategoryResult[];
  topFixes: Finding[];
}

export interface BrandKit {
  name: string;
  title: string;
  description: string;
  logo: string | null;
  colors: { bg: string; text: string; primary: string };
  font: string;
  nav: { text: string; href: string }[];
  heroTitle: string;
  heroSub: string;
  cta: { text: string; href: string };
  sections: { heading: string; text: string }[];
  images: { src: string; alt: string }[];
  origin: string;
}

export interface Prototype {
  file: string;
  shotFile: string;
  usedLLM: boolean;
  changes: { change: string; fixes: string }[];
  reaudit: { category: Category; before: number; after: number }[];
}

export interface DevMatch {
  id: string;
  name: string;
  role: string;
  level: number;
  fit: number;
  rationale: string;
  availableFrom: string;
  skills: string[];
}

export interface SkillBreakdown {
  id: string;
  label: string;
  weight: number;
  needed: number;
  available: number;
  headcount: number;
  level: number;
  fit: number;
  availableFrom: string | null;
}

export interface MatchResult {
  orgScore: number;
  skills: SkillBreakdown[];
  strengths: string[];
  gaps: string[];
  team: DevMatch[];
  estimate: {
    workstreams: { name: string; days: number }[];
    totalDays: number;
    weeks: number;
    priceLow: number;
    priceHigh: number;
    currency: string;
    assumptions: string[];
  };
  idleCostRecovered: number;
}

export interface DeckResult {
  pptx: string;
  proposal: string;
}

export interface TrafficStats {
  totalRequests: number;
  totalBytes: number;
  failedRequests: number;
  uniqueDomains: number;
  thirdParty: { requests: number; bytes: number; requestShare: number; byteShare: number };
  byType: { type: string; requests: number; bytes: number }[];
  topDomains: { domain: string; requests: number; bytes: number; thirdParty: boolean }[];
}

export interface StackSkill {
  techId: string;
  tech: string;
  category: string;
  skillId: string;
  skillLabel: string;
  level: number;
  headcount: number;
  available: number;
  availableFrom: string | null;
  status: 'strong' | 'partial' | 'gap';
}

export interface StackReport {
  technologies: import('./techSignatures.js').Tech[];
  traffic: TrafficStats;
  coverage: { skills: StackSkill[]; score: number };
}
