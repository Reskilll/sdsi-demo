/**
 * KnoxFlow Agentic Pipeline Orchestrator
 */

const { classifyEmail } = require('./classifier');
const { calculateSLA } = require('./slaTracker');
const { matchHistoricalSolution } = require('./historicalMatcher');

function processEmail(rawEmail, historicalKb = [], teamMembers = [], referenceTime = new Date()) {
  // 1. Classification Agent
  const classification = classifyEmail(rawEmail.subject, rawEmail.body);
  
  const emailWithClass = {
    ...rawEmail,
    category: classification.category,
    task_type: classification.task_type,
    sla_priority: classification.sla_priority,
    sla_target_hours: classification.sla_target_hours,
    classification_reason: classification.classification_reason
  };

  // 2. Historical Knowledge Base Matcher (Deterministic)
  const historicalMatch = matchHistoricalSolution(emailWithClass, historicalKb, teamMembers);
  emailWithClass.historical_match = historicalMatch;

  // 3. SLA & Aging Tracker Agent
  const slaMetrics = calculateSLA(emailWithClass, referenceTime);
  emailWithClass.sla_metrics = slaMetrics;

  return emailWithClass;
}

module.exports = {
  processEmail,
  classifyEmail,
  calculateSLA,
  matchHistoricalSolution
};
