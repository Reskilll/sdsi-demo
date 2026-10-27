import type { NetRequest } from './types.js';

export type TechCategory =
  | 'Frontend framework' | 'Commerce platform' | 'CMS & experience' | 'Marketing & campaign' | 'Analytics' | 'Tag manager'
  | 'Personalization & testing' | 'CDN & hosting' | 'Server & language' | 'Payments' | 'Consent' | 'Monitoring'
  | 'Search' | 'Support & chat' | 'Reviews & feedback' | 'Tracking pixels' | 'Other';

export interface Signals {
  headers: Record<string, string>;
  cookieNames: string[];
  html: string;
  globals: string[];
  network: NetRequest[];
}

export interface Tech {
  id: string;
  name: string;
  category: TechCategory;
  /** Org skill id this technology maps to (see config/org-skills.json), if any. */
  skill?: string;
  /** confirmed = two or more independent signals; likely = one. */
  confidence: 'confirmed' | 'likely';
  evidence: string[];
}

interface Sig {
  id: string; name: string; cat: TechCategory; skill?: string;
  /** [header-name pattern, value pattern] */ h?: [RegExp, RegExp][];
  c?: RegExp[]; html?: RegExp[]; u?: RegExp[]; g?: string[];
}

const S = (id: string, name: string, cat: TechCategory, skill: string | undefined, t: Omit<Sig, 'id' | 'name' | 'cat' | 'skill'>): Sig => ({ id, name, cat, skill, ...t });
const any = /.*/;

export const SIGNATURES: Sig[] = [
  // Frontend frameworks
  S('react', 'React', 'Frontend framework', 'nextjs', { g: ['React'], html: [/data-reactroot|__reactFiber|_reactRootContainer|data-react-helmet/], u: [/react(-dom)?(\.production)?(\.min)?\.js/i] }),
  S('nextjs', 'Next.js', 'Frontend framework', 'nextjs', { g: ['__NEXT_DATA__'], html: [/\/_next\/static\//], h: [[/x-powered-by/, /Next\.js/i]] }),
  S('nuxt', 'Nuxt', 'Frontend framework', 'vue', { g: ['__NUXT__'], html: [/\/_nuxt\//] }),
  S('vue', 'Vue.js', 'Frontend framework', 'vue', { g: ['Vue', '__VUE__'], html: [/data-v-[0-9a-f]{6,}|data-server-rendered/] }),
  S('angular', 'Angular', 'Frontend framework', 'angular', { g: ['angular'], html: [/ng-version=|<app-root|ng-app=/] }),
  S('spartacus', 'SAP Composable Storefront (Spartacus)', 'Frontend framework', 'sap-hybris', { html: [/<cx-storefront|spartacus/i] }),
  S('svelte', 'Svelte / SvelteKit', 'Frontend framework', undefined, { html: [/__sveltekit|svelte-[a-z0-9]{5,}/] }),
  S('jquery', 'jQuery', 'Frontend framework', undefined, { g: ['jQuery'], u: [/jquery[.-]?[\d.]*(min)?\.js/i] }),
  S('bootstrap', 'Bootstrap', 'Frontend framework', undefined, { u: [/bootstrap(\.min)?\.(css|js)/i] }),
  // Commerce platforms
  S('hybris', 'SAP Commerce Cloud (Hybris)', 'Commerce platform', 'sap-hybris', { html: [/\/_ui\/(responsive|desktop|mobile)|yCommerce|hybris|\/medias\/\?context=/i], u: [/\/_ui\/(responsive|desktop)/, /\/occ\/v[12]\/|\/rest\/v2\/|\/newhybris|hybrisapi/i], g: ['ACC', 'smartedit'] }),
  S('sfcc', 'Salesforce Commerce Cloud', 'Commerce platform', 'salesforce-commerce', { u: [/demandware\.static|\/on\/demandware\.store|dwanalytics/i], html: [/demandware/i], g: ['dw', 'dwAnalytics'], c: [/^dw(sid|_anonymous)|^__cq_/] }),
  S('magento', 'Adobe Commerce (Magento)', 'Commerce platform', 'magento', { g: ['Magento', 'mage'], html: [/Magento_[A-Z]|\/static\/version\d+\//], c: [/^mage-cache|^form_key$/] }),
  S('shopify', 'Shopify', 'Commerce platform', 'shopify', { g: ['Shopify'], u: [/cdn\.shopify\.com/], h: [[/x-shopify|x-shopid/, any]] }),
  S('bigcommerce', 'BigCommerce', 'Commerce platform', undefined, { u: [/bigcommerce\.com/] }),
  S('woocommerce', 'WooCommerce', 'Commerce platform', 'wordpress', { html: [/woocommerce/i] }),
  S('commercetools', 'commercetools', 'Commerce platform', undefined, { u: [/commercetools\.com/] }),
  // CMS and experience
  S('aem', 'Adobe Experience Manager', 'CMS & experience', 'adobe-aem', { html: [/\/etc\.clientlibs\/|\/etc\/designs\/|\/content\/dam\/|cq-wcm|\/libs\/granite/], u: [/\/etc\.clientlibs\/|\/content\/dam\//], g: ['Granite', 'CQ'], h: [[/x-vhost|x-dispatcher|x-aem/, any]] }),
  S('wordpress', 'WordPress', 'CMS & experience', 'wordpress', { html: [/wp-content\/|wp-includes\/|content="WordPress/], u: [/wp-content|wp-json/] }),
  S('drupal', 'Drupal', 'CMS & experience', 'php', { html: [/Drupal\.settings|drupalSettings|sites\/default\/files/], h: [[/x-generator/, /Drupal/i]] }),
  S('sitecore', 'Sitecore', 'CMS & experience', 'dotnet', { html: [/\/-\/media\/|sitecore/i], c: [/^SC_ANALYTICS_GLOBAL_COOKIE/] }),
  S('contentful', 'Contentful', 'CMS & experience', 'cms', { u: [/ctfassets\.net|contentful\.com/] }),
  // Marketing and campaign
  S('adobe-campaign', 'Adobe Campaign', 'Marketing & campaign', 'adobe-campaign', { html: [/neolane|\/nl\/jsp\/|nms:/i], u: [/neolane|\/nl\/jsp\//i] }),
  S('sfmc', 'Salesforce Marketing Cloud', 'Marketing & campaign', 'salesforce-marketing', { u: [/exacttarget|marketingcloudapis|\.marketingcloud/i], html: [/exacttarget|marketingcloudapis|ETWebTracker/i] }),
  S('pardot', 'Salesforce Pardot', 'Marketing & campaign', 'salesforce-marketing', { g: ['piAId'], u: [/pi\.pardot\.com|pardot\.com\/pd\.js/] }),
  S('marketo', 'Adobe Marketo', 'Marketing & campaign', undefined, { g: ['Munchkin'], u: [/munchkin\.marketo\.net/] }),
  S('hubspot', 'HubSpot', 'Marketing & campaign', undefined, { u: [/js\.hs-scripts\.com|hs-analytics|hubspot\.com/] }),
  S('klaviyo', 'Klaviyo', 'Marketing & campaign', undefined, { g: ['klaviyo', '_learnq'], u: [/klaviyo\.com/] }),
  S('braze', 'Braze', 'Marketing & campaign', undefined, { g: ['braze', 'appboy'], u: [/braze\.com|appboy/] }),
  // Analytics and tags
  S('ga4', 'Google Analytics 4', 'Analytics', 'web-analytics', { u: [/googletagmanager\.com\/gtag\/js|google-analytics\.com\/g\/collect|analytics\.google\.com/], g: ['gtag'], c: [/^_ga(_|$)/] }),
  S('ua', 'Google Analytics (Universal)', 'Analytics', 'web-analytics', { u: [/google-analytics\.com\/(analytics|ga)\.js|google-analytics\.com\/collect/], g: ['_gaq'] }),
  S('adobe-analytics', 'Adobe Analytics', 'Analytics', 'adobe-analytics', { g: ['s_account', 's_gi'], u: [/omtrdc\.net|2o7\.net|AppMeasurement|\/b\/ss\//], c: [/^(s_cc|s_sq|AMCV_|s_vi)/] }),
  S('segment', 'Segment', 'Analytics', 'web-analytics', { g: ['analytics'], u: [/cdn\.segment\.(com|io)/] }),
  S('mixpanel', 'Mixpanel', 'Analytics', 'web-analytics', { g: ['mixpanel'], u: [/mixpanel\.com|mxpnl/] }),
  S('amplitude', 'Amplitude', 'Analytics', 'web-analytics', { g: ['amplitude'], u: [/amplitude\.com/] }),
  S('hotjar', 'Hotjar', 'Analytics', undefined, { g: ['hj'], u: [/static\.hotjar\.com|hotjar\.io/] }),
  S('clarity', 'Microsoft Clarity', 'Analytics', undefined, { g: ['clarity'], u: [/clarity\.ms/] }),
  S('fullstory', 'FullStory', 'Analytics', undefined, { g: ['FS'], u: [/fullstory\.com/] }),
  S('gtm', 'Google Tag Manager', 'Tag manager', 'web-analytics', { u: [/googletagmanager\.com\/gtm\.js/], g: ['google_tag_manager'], html: [/GTM-[A-Z0-9]{4,}/] }),
  S('adobe-launch', 'Adobe Experience Platform Launch', 'Tag manager', 'adobe-analytics', { g: ['_satellite'], u: [/assets\.adobedtm\.com/] }),
  S('tealium', 'Tealium', 'Tag manager', 'web-analytics', { g: ['utag'], u: [/tags\.tiqcdn\.com|tealiumiq/] }),
  // Personalization and testing
  S('adobe-target', 'Adobe Target', 'Personalization & testing', 'personalization', { u: [/tt\.omtrdc\.net|\/at\.js|\/mbox/], c: [/^mbox/] }),
  S('optimizely', 'Optimizely', 'Personalization & testing', 'personalization', { g: ['optimizely'], u: [/cdn\.optimizely\.com/] }),
  S('dynamicyield', 'Dynamic Yield', 'Personalization & testing', 'personalization', { g: ['DY', 'DYO'], u: [/dynamicyield\.com/] }),
  S('vwo', 'VWO', 'Personalization & testing', 'personalization', { u: [/visualwebsiteoptimizer\.com/] }),
  S('abtasty', 'AB Tasty', 'Personalization & testing', 'personalization', { u: [/abtasty\.com/] }),
  // Tracking pixels
  S('meta-pixel', 'Meta Pixel', 'Tracking pixels', undefined, { g: ['fbq'], u: [/connect\.facebook\.net\/.*fbevents|facebook\.com\/tr/] }),
  S('tiktok-pixel', 'TikTok Pixel', 'Tracking pixels', undefined, { g: ['ttq'], u: [/analytics\.tiktok\.com/] }),
  S('linkedin', 'LinkedIn Insight Tag', 'Tracking pixels', undefined, { u: [/snap\.licdn\.com|px\.ads\.linkedin\.com/] }),
  S('criteo', 'Criteo', 'Tracking pixels', undefined, { g: ['criteo_q'], u: [/static\.criteo\.net|criteo\.com/] }),
  S('google-ads', 'Google Ads / DoubleClick', 'Tracking pixels', undefined, { u: [/doubleclick\.net|googleadservices\.com|googlesyndication\.com/] }),
  // Consent
  S('onetrust', 'OneTrust', 'Consent', undefined, { g: ['Optanon', 'OneTrust'], u: [/cdn\.cookielaw\.org|onetrust\.com/] }),
  S('cookiebot', 'Cookiebot', 'Consent', undefined, { g: ['Cookiebot'], u: [/consent\.cookiebot\.com/] }),
  S('usercentrics', 'Usercentrics', 'Consent', undefined, { u: [/usercentrics\.eu/] }),
  // Monitoring
  S('sentry', 'Sentry', 'Monitoring', undefined, { g: ['Sentry'], u: [/sentry-cdn\.com|sentry\.io/] }),
  S('newrelic', 'New Relic', 'Monitoring', undefined, { g: ['NREUM', 'newrelic'], u: [/js-agent\.newrelic\.com|nr-data\.net/] }),
  S('datadog', 'Datadog RUM', 'Monitoring', undefined, { g: ['DD_RUM'], u: [/datadoghq\.(com|eu)/] }),
  S('dynatrace', 'Dynatrace', 'Monitoring', undefined, { html: [/ruxitagentjs|dynatrace/i] }),
  S('mpulse', 'Akamai mPulse', 'Monitoring', undefined, { u: [/go-mpulse\.net/] }),
  // Payments
  S('stripe', 'Stripe', 'Payments', 'payments', { g: ['Stripe'], u: [/js\.stripe\.com/] }),
  S('paypal', 'PayPal', 'Payments', 'payments', { g: ['paypal'], u: [/paypal\.com\/sdk|paypalobjects\.com/] }),
  S('adyen', 'Adyen', 'Payments', 'payments', { u: [/adyen\.com/] }),
  S('klarna', 'Klarna', 'Payments', 'payments', { g: ['Klarna'], u: [/klarna\.com/] }),
  // Search and support
  S('algolia', 'Algolia', 'Search', undefined, { g: ['algoliasearch'], u: [/algolia\.net|algolianet\.com|algolia\.io/] }),
  S('coveo', 'Coveo', 'Search', undefined, { u: [/coveo\.com/] }),
  S('bloomreach', 'Bloomreach', 'Search', undefined, { u: [/brsrvr\.com|bloomreach\.(com|io)/] }),
  S('intercom', 'Intercom', 'Support & chat', undefined, { g: ['Intercom'], u: [/intercom\.io|intercomcdn/] }),
  S('zendesk', 'Zendesk', 'Support & chat', undefined, { g: ['zE'], u: [/zdassets\.com|zendesk\.com/] }),
  S('drift', 'Drift', 'Support & chat', undefined, { g: ['drift'], u: [/drift\.com|driftt\.com/] }),
  // CDN and hosting
  S('akamai', 'Akamai', 'CDN & hosting', 'devops-cdn', { h: [[/^server$/, /AkamaiGHost|AkamaiNetStorage/i], [/x-akamai/, any]], u: [/akamaihd\.net|akamaized\.net|edgekey\.net/], c: [/^(ak_bmsc|bm_sv|_abck)$/] }),
  S('cloudflare', 'Cloudflare', 'CDN & hosting', 'devops-cdn', { h: [[/^server$/, /cloudflare/i], [/^cf-ray$/, any]], c: [/^(__cf_bm|cf_clearance)$/] }),
  S('fastly', 'Fastly', 'CDN & hosting', 'devops-cdn', { h: [[/fastly/, any], [/x-served-by/, /cache-/]] }),
  S('cloudfront', 'Amazon CloudFront', 'CDN & hosting', 'devops-cdn', { h: [[/^via$/, /cloudfront/i], [/x-amz-cf-id/, any]] }),
  S('aws', 'Amazon Web Services', 'CDN & hosting', 'devops-cdn', { h: [[/x-amz-(request|id)/, any]], u: [/amazonaws\.com/] }),
  S('azure', 'Microsoft Azure', 'CDN & hosting', 'devops-cdn', { h: [[/x-azure-ref|x-ms-request-id/, any]], u: [/azureedge\.net|azurefd\.net|blob\.core\.windows\.net/] }),
  S('gcp', 'Google Cloud', 'CDN & hosting', 'devops-cdn', { h: [[/^server$/, /Google Frontend|^gws$/i], [/^via$/, /google/i]] }),
  S('vercel', 'Vercel', 'CDN & hosting', 'nextjs', { h: [[/^server$/, /Vercel/i], [/x-vercel-id/, any]] }),
  S('netlify', 'Netlify', 'CDN & hosting', undefined, { h: [[/^server$/, /Netlify/i], [/x-nf-request-id/, any]] }),
  // Server and language
  S('aspnet', '.NET / ASP.NET', 'Server & language', 'dotnet', { h: [[/x-powered-by/, /ASP\.NET/i], [/x-aspnet(mvc)?-version/, any]], c: [/^(ASP\.NET_SessionId|\.AspNetCore|\.ASPXAUTH)/], html: [/__VIEWSTATE|__EVENTVALIDATION/], u: [/\.aspx(\?|$)|WebResource\.axd/] }),
  S('iis', 'Microsoft IIS', 'Server & language', 'dotnet', { h: [[/^server$/, /Microsoft-IIS/i]] }),
  S('java', 'Java (servlet / JSP)', 'Server & language', 'java', { h: [[/x-powered-by/, /Servlet|JSP|JBoss|Tomcat|Jetty/i], [/^server$/, /Apache-Coyote|Tomcat|Jetty|WebLogic|WebSphere|JBoss|Undertow/i]], c: [/^JSESSIONID$/], u: [/\.jsp(\?|;|$)|\.do(\?|$)|;jsessionid=/i] }),
  S('flask', 'Flask', 'Server & language', 'python', { h: [[/^server$/, /Werkzeug/i], [/x-powered-by/, /Flask/i]] }),
  S('django', 'Django', 'Server & language', 'python', { c: [/^csrftoken$/], html: [/csrfmiddlewaretoken/], h: [[/x-powered-by/, /Django/i]] }),
  S('python', 'Python (WSGI / ASGI server)', 'Server & language', 'python', { h: [[/^server$/, /gunicorn|uvicorn|WSGIServer|Hypercorn|waitress|^Python/i], [/x-powered-by/, /Python/i]] }),
  S('nodejs', 'Node.js (Express)', 'Server & language', 'nodejs', { h: [[/x-powered-by/, /Express/i]] }),
  S('php', 'PHP', 'Server & language', 'php', { h: [[/x-powered-by/, /PHP/i]], c: [/^PHPSESSID$/], u: [/\.php(\?|$)/] }),
  S('nginx', 'nginx', 'Server & language', undefined, { h: [[/^server$/, /nginx/i]] }),
  S('apache', 'Apache HTTP Server', 'Server & language', undefined, { h: [[/^server$/, /^Apache(?!-Coyote)/i]] }),
  // ── Added after probing samsung.com (v0.4.2): chat, reviews, personalisation, Adobe data, ad tech, consent, payments ──
  S('gigya', 'SAP Customer Data Cloud (Gigya)', 'Commerce platform', 'sap-hybris', { u: [/gigya\.com|cdns\.gigya/] }),
  S('bazaarvoice', 'Bazaarvoice', 'Reviews & feedback', undefined, { g: ['BV', '$BV', 'bvCallback'], u: [/bazaarvoice\.com|bvapi|ugc\.bv/i] }),
  S('yotpo', 'Yotpo', 'Reviews & feedback', undefined, { u: [/yotpo\.com/] }),
  S('trustpilot', 'Trustpilot', 'Reviews & feedback', undefined, { u: [/trustpilot\.com/] }),
  S('powerreviews', 'PowerReviews', 'Reviews & feedback', undefined, { u: [/powerreviews\.com/] }),
  S('medallia', 'Medallia', 'Reviews & feedback', undefined, { u: [/medallia\.com|kampyle/i] }),
  S('qualtrics', 'Qualtrics', 'Reviews & feedback', undefined, { u: [/qualtrics\.com|siteintercept/i], g: ['QSI'] }),
  S('sprinklr', 'Sprinklr', 'Support & chat', undefined, { u: [/sprinklr\.com/] }),
  S('liveperson', 'LivePerson', 'Support & chat', undefined, { g: ['lpTag'], u: [/liveperson\.net|lpsnmedia\.net/] }),
  S('genesys', 'Genesys', 'Support & chat', undefined, { u: [/genesys(cloud)?\.com|mypurecloud/i] }),
  S('livechat', 'LiveChat', 'Support & chat', undefined, { u: [/livechatinc\.com/] }),
  S('freshworks', 'Freshworks (Freshchat / Freshdesk)', 'Support & chat', undefined, { g: ['fcWidget'], u: [/freshchat\.com|freshdesk\.com|freshworks\.com/] }),
  S('sf-chat', 'Salesforce Service Cloud chat', 'Support & chat', 'salesforce-marketing', { g: ['embedded_svc'], u: [/embeddedservice|salesforceliveagent|service\.force\.com|salesforce-scrt/i] }),
  S('koreai', 'Kore.ai', 'Support & chat', undefined, { u: [/kore\.ai/] }),
  S('yellowai', 'Yellow.ai', 'Support & chat', undefined, { u: [/yellow\.ai|yellowmessenger\.com/] }),
  S('haptik', 'Haptik', 'Support & chat', undefined, { u: [/haptik\.ai/] }),
  S('tidio', 'Tidio', 'Support & chat', undefined, { u: [/tidio\.(co|com)|tidiochat/i] }),
  S('insider', 'Insider (personalisation)', 'Personalization & testing', 'personalization', { g: ['Insider', 'insider_object'], u: [/useinsider\.com/] }),
  S('evergage', 'Salesforce Interaction Studio', 'Personalization & testing', 'personalization', { u: [/evergage\.com/] }),
  S('aam', 'Adobe Audience Manager', 'Marketing & campaign', 'adobe-analytics', { u: [/demdex\.net/], c: [/^demdex$/] }),
  S('adobe-adv', 'Adobe Advertising Cloud', 'Tracking pixels', 'adobe-analytics', { u: [/everesttech\.net/] }),
  S('adobe-edge', 'Adobe Experience Platform Web SDK', 'Analytics', 'adobe-analytics', { u: [/edge\.adobedc\.net/], g: ['alloy'] }),
  S('bing-uet', 'Microsoft Advertising (UET)', 'Tracking pixels', undefined, { g: ['uetq'], u: [/bat\.bing\.com/] }),
  S('snap-pixel', 'Snapchat Pixel', 'Tracking pixels', undefined, { u: [/tr\.snapchat\.com|sc-static\.net/] }),
  S('x-pixel', 'X (Twitter) Ads pixel', 'Tracking pixels', undefined, { u: [/analytics\.twitter\.com|static\.ads-twitter\.com/] }),
  S('amazon-ads', 'Amazon Ads', 'Tracking pixels', undefined, { u: [/amazon-adsystem\.com/] }),
  S('pinterest-tag', 'Pinterest Tag', 'Tracking pixels', undefined, { u: [/ct\.pinterest\.com|s\.pinimg\.com\/ct/] }),
  S('adexchanges', 'Programmatic ad exchanges and data partners', 'Tracking pixels', undefined, { u: [/adsrvr\.org|adnxs\.com|adform\.net|rubiconproject\.com|pubmatic\.com|openx\.net|casalemedia\.com|crwdcntrl\.net|eyeota\.net|zeotap\.com|mathtag\.com|rfihub\.com|ml314\.com|rlcdn\.com|taboola\.com|outbrain\.com|bidswitch\.net/] }),
  S('trustarc', 'TrustArc', 'Consent', undefined, { g: ['truste'], u: [/trustarc\.com|truste\.com/] }),
  S('didomi', 'Didomi', 'Consent', undefined, { g: ['Didomi'], u: [/didomi\.io/] }),
  S('osano', 'Osano', 'Consent', undefined, { u: [/osano\.com/] }),
  S('cookieyes', 'CookieYes', 'Consent', undefined, { u: [/cookieyes\.com/] }),
  S('quantcast-choice', 'Quantcast Choice', 'Consent', undefined, { u: [/quantcast\.mgr\.consensu\.org|choice\.quantcast\.com/] }),
  S('razorpay', 'Razorpay', 'Payments', 'payments', { g: ['Razorpay'], u: [/razorpay\.com/] }),
  S('payu', 'PayU', 'Payments', 'payments', { u: [/payu\.(in|com)/] }),
  S('paytm', 'Paytm', 'Payments', 'payments', { u: [/paytm(payments)?\.com/] }),
  S('worldpay', 'Worldpay', 'Payments', 'payments', { u: [/worldpay\.com/] }),
  S('checkoutcom', 'Checkout.com', 'Payments', 'payments', { u: [/checkout\.com\/frames|cko-/] }),
  S('constructor', 'Constructor', 'Search', undefined, { u: [/constructor\.io|cnstrc\.com/] }),
  S('klevu', 'Klevu', 'Search', undefined, { u: [/klevu\.com/] }),
  S('heap', 'Heap', 'Analytics', 'web-analytics', { g: ['heap'], u: [/heapanalytics\.com/] }),
  S('matomo', 'Matomo', 'Analytics', 'web-analytics', { g: ['_paq'], u: [/matomo\.(js|php)|piwik\.(js|php)/] }),
  S('imperva', 'Imperva (Incapsula)', 'CDN & hosting', 'devops-cdn', { h: [[/x-iinfo|x-cdn/, /incap|imperva/i]], c: [/^(incap_ses|visid_incap)/] }),
  S('recaptcha', 'Google reCAPTCHA', 'Other', undefined, { g: ['grecaptcha'], u: [/google\.com\/recaptcha|gstatic\.com\/recaptcha/] }),
  S('gmaps', 'Google Maps', 'Other', undefined, { u: [/maps\.googleapis\.com|maps\.gstatic\.com/] }),
];

/** Matches every signature against what the crawl observed. Pure function: easy to test with fixtures. */
export function detectTech(sig: Signals): Tech[] {
  const found: Tech[] = [];
  const reqUrls = sig.network.map((n) => n.url);
  // Server-side signals must come from the site's own domain: a third-party's .php or .jsp says nothing about the site's stack.
  const ownUrls = sig.network.filter((n) => !n.thirdParty).map((n) => n.url);
  const globals = new Set(sig.globals);
  for (const s of SIGNATURES) {
    const evidence: string[] = [];
    for (const [nameRe, valRe] of s.h ?? []) {
      const hit = Object.entries(sig.headers).find(([k, v]) => nameRe.test(k) && valRe.test(v));
      if (hit) { evidence.push(`header ${hit[0]}${hit[1].length < 40 ? ': ' + hit[1] : ''}`); break; }
    }
    const ck = s.c && sig.cookieNames.find((n) => s.c!.some((re) => re.test(n)));
    if (ck) evidence.push(`cookie ${ck}`);
    const hm = s.html?.find((re) => re.test(sig.html));
    if (hm) evidence.push('page markup');
    const um = s.u && (s.cat === 'Server & language' ? ownUrls : reqUrls).find((u) => s.u!.some((re) => re.test(u)));
    if (um) evidence.push(`request ${um.replace(/^https?:\/\//, '').slice(0, 60)}`);
    const gl = s.g?.find((g) => globals.has(g));
    if (gl) evidence.push(`script global ${gl}`);
    if (evidence.length) found.push({ id: s.id, name: s.name, category: s.cat, skill: s.skill, confidence: evidence.length >= 2 ? 'confirmed' : 'likely', evidence });
  }
  // A framework implied by another is reported once: Next.js implies React.
  const ids = new Set(found.map((t) => t.id));
  return found.filter((t) => !(t.id === 'react' && ids.has('nextjs') && t.evidence.length < 2));
}
