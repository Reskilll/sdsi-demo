/**
 * KnoxFlow Agentic Classifier
 * Classifies emails into 'General Information' or 'Task',
 * determines task type, priority, and SLA target hours.
 */

const GENERAL_INFO_KEYWORDS = [
  'announcement', 'newsletter', 'scheduled maintenance', 'firmware upgrade',
  'recording available', 'town hall', 'all-hands', 'happy hour', 'holiday',
  'policy update', 'office closed', 'quarterly review', 'fyi', 'bulletin'
];

const TASK_CATEGORIES = [
  {
    type: 'Access & Network',
    keywords: ['vpn', 'globalprotect', 'tunnel', 'ipsec', 'firewall', 'network timeout', 'connection refused', 'gateway'],
    priority: 'P1 - Critical (2h)',
    sla_hours: 2
  },
  {
    type: 'Infrastructure Bug',
    keywords: ['502 bad gateway', '500 internal server', 'ssl certificate', 'cert expired', 'outage', 'node crash', 'ingress down', 'kernel panic'],
    priority: 'P1 - Critical (2h)',
    sla_hours: 2
  },
  {
    type: 'Access Request',
    keywords: ['database access', 'credentials', 'read-only', 'permission', 'staging db', 'prod db', 'grant access', 'vault creds', 'iam role'],
    priority: 'P2 - High (4h)',
    sla_hours: 4
  },
  {
    type: 'CI/CD Pipeline Issue',
    keywords: ['ci runner', 'docker build', 'npm err', 'pipeline failed', 'build error', 'gitlab ci', 'github actions', 'econnreset', 'build #'],
    priority: 'P2 - High (4h)',
    sla_hours: 4
  },
  {
    type: 'Account & Licensing',
    keywords: ['jira license', 'confluence access', 'license allocation', 'okta tile', 'invitation link', 'onboarding seat', 'atlassian account'],
    priority: 'P3 - Medium (8h)',
    sla_hours: 8
  },
  {
    type: 'General Technical Query',
    keywords: ['review', 'schema migration', 'question', 'advice', 'how to', 'best practice', 'guidance', 'clarification', 'architecture feedback'],
    priority: 'P3 - Medium (8h)',
    sla_hours: 8
  }
];

function classifyEmail(subject = '', body = '') {
  const content = `${subject} ${body}`.toLowerCase();

  // 1. Check for General Information indicators
  const isGeneralInfo = GENERAL_INFO_KEYWORDS.some(kw => content.includes(kw)) &&
    !content.includes('urgent') && !content.includes('critical') && !content.includes('fail') && !content.includes('timeout');

  if (isGeneralInfo) {
    return {
      category: 'General Information',
      task_type: null,
      sla_priority: null,
      sla_target_hours: null,
      classification_reason: 'Broadcast or informational announcement detected; no actionable response required.'
    };
  }

  // 2. Classify as Task & match Task Type
  let bestMatch = null;
  let maxScore = 0;

  for (const cat of TASK_CATEGORIES) {
    let score = 0;
    for (const kw of cat.keywords) {
      if (content.includes(kw)) score += 1;
    }
    if (score > maxScore) {
      maxScore = score;
      bestMatch = cat;
    }
  }

  if (bestMatch && maxScore > 0) {
    // Check urgency modifiers
    let priority = bestMatch.priority;
    let slaHours = bestMatch.sla_hours;
    if (content.includes('urgent') || content.includes('critical') || content.includes('emergency')) {
      priority = 'P1 - Critical (2h)';
      slaHours = 2;
    }

    return {
      category: 'Task',
      task_type: bestMatch.type,
      sla_priority: priority,
      sla_target_hours: slaHours,
      classification_reason: `Actionable task categorized under '${bestMatch.type}' based on detected technical indicators.`
    };
  }

  // Fallback task category
  return {
    category: 'Task',
    task_type: 'General Technical Query',
    sla_priority: 'P4 - Standard (24h)',
    sla_target_hours: 24,
    classification_reason: 'Actionable inquiry requiring team response; standard 24h SLA assigned.'
  };
}

module.exports = { classifyEmail, TASK_CATEGORIES, GENERAL_INFO_KEYWORDS };
