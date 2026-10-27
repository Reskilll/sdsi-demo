/**
 * KnoxFlow Deterministic Historical Knowledge Base Matcher
 * 
 * Strict Constraint: Automatic response drafts are ONLY suggested if a matching
 * historical problem was previously verified and resolved. Generative AI inventions
 * for unverified solutions are strictly suppressed.
 */

function matchHistoricalSolution(email, historicalKb = [], teamMembers = []) {
  if (email.category === 'General Information') {
    return null;
  }

  const queryText = `${email.subject || ''} ${email.body || ''}`.toLowerCase();
  let bestMatch = null;
  let highestScore = 0;

  for (const entry of historicalKb) {
    let matchedKeywords = 0;
    for (const kw of entry.issue_keywords) {
      if (queryText.includes(kw.toLowerCase())) {
        matchedKeywords++;
      }
    }

    // Similarity calculation based on matched keywords ratio
    const keywordCoverage = matchedKeywords / entry.issue_keywords.length;
    let score = keywordCoverage;

    // Bonus if task_type matches
    if (email.task_type && entry.task_type && email.task_type.toLowerCase() === entry.task_type.toLowerCase()) {
      score += 0.25;
    }

    if (matchedKeywords >= 2 && score > highestScore && score >= 0.5) {
      highestScore = score;
      bestMatch = entry;
    }
  }

  if (!bestMatch) {
    return null;
  }

  // Find assignee name if available
  const assignee = teamMembers.find(m => m.id === email.assigned_to);
  const assigneeName = assignee ? assignee.name : 'Engineering Support Team';
  const senderName = (email.sender && email.sender.name) ? email.sender.name : 'Team';

  // Populate verified template variables
  let populatedDraft = bestMatch.verified_draft || '';
  populatedDraft = populatedDraft.replace(/\{\{sender_name\}\}/g, senderName);
  populatedDraft = populatedDraft.replace(/\{\{assignee_name\}\}/g, assigneeName);

  return {
    matched_kb_id: bestMatch.id,
    kb_title: bestMatch.title,
    similarity_score: Math.min(Number(highestScore.toFixed(2)), 0.98),
    historical_ticket_id: bestMatch.historical_ticket_id,
    resolved_by: bestMatch.resolved_by,
    resolution_date: bestMatch.resolution_date,
    solution_category: bestMatch.solution_category,
    resolution_details: bestMatch.resolution_details,
    verified_draft: populatedDraft,
    source_verification: '100% Sourced from Historical Resolution Record (No Hallucinated AI Output)'
  };
}

module.exports = { matchHistoricalSolution };
