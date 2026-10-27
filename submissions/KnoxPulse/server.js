/**
 * KnoxFlow Autonomous Agentic Email & SLA Monitoring System
 * Pure Node.js Zero-Dependency Server (Node.js v18+)
 */

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const url = require('node:url');

const { processEmail, classifyEmail, calculateSLA, matchHistoricalSolution } = require('./agent/index');

const PORT = process.env.PORT || 3000;
const DATA_DIR = path.join(__dirname, 'data');
const PUBLIC_DIR = path.join(__dirname, 'public');

const TEAM_PATH = path.join(DATA_DIR, 'team.json');
const KB_PATH = path.join(DATA_DIR, 'historical_kb.json');
const EMAILS_PATH = path.join(DATA_DIR, 'emails.json');
const BACKUP_EMAILS_PATH = path.join(DATA_DIR, 'emails.benchmark.json');

// Memory state loaded from JSON
let team = [];
let historicalKb = [];
let emails = [];

// Load data
function loadData() {
  try {
    team = JSON.parse(fs.readFileSync(TEAM_PATH, 'utf-8'));
    historicalKb = JSON.parse(fs.readFileSync(KB_PATH, 'utf-8'));
    emails = JSON.parse(fs.readFileSync(EMAILS_PATH, 'utf-8'));

    // Save initial backup for benchmark reset
    if (!fs.existsSync(BACKUP_EMAILS_PATH)) {
      fs.writeFileSync(BACKUP_EMAILS_PATH, JSON.stringify(emails, null, 2), 'utf-8');
    }
    console.log(`[KnoxFlow] Loaded ${team.length} team members, ${historicalKb.length} KB articles, ${emails.length} emails.`);
  } catch (err) {
    console.error('[KnoxFlow] Error loading JSON data:', err);
  }
}

function saveEmails() {
  fs.writeFileSync(EMAILS_PATH, JSON.stringify(emails, null, 2), 'utf-8');
}

function saveKb() {
  fs.writeFileSync(KB_PATH, JSON.stringify(historicalKb, null, 2), 'utf-8');
}

loadData();

// Compute Manager and Team statistics
function computeAnalytics() {
  const now = new Date();
  
  // Re-run SLA metrics dynamically for all emails against current clock
  const processedEmails = emails.map(email => {
    const slaMetrics = calculateSLA(email, now);
    // Refresh historical match if not already fixed or matched
    let match = email.historical_match;
    if (!email.is_responded && email.category === 'Task') {
      match = matchHistoricalSolution(email, historicalKb, team);
    }
    return {
      ...email,
      historical_match: match,
      sla_metrics: slaMetrics
    };
  });

  const totalReceived = processedEmails.length;
  const tasks = processedEmails.filter(e => e.category === 'Task');
  const generalInfo = processedEmails.filter(e => e.category === 'General Information');
  const responded = tasks.filter(e => e.is_responded);
  const pendingTasks = tasks.filter(e => !e.is_responded);
  const breachedTasks = tasks.filter(e => e.sla_metrics && e.sla_metrics.is_breached);

  // Turnaround calculation for responded emails
  let totalTurnaround = 0;
  responded.forEach(e => {
    if (e.response_info && e.response_info.response_time_hours) {
      totalTurnaround += e.response_info.response_time_hours;
    }
  });
  const avgResponseTimeHours = responded.length > 0 ? (totalTurnaround / responded.length).toFixed(1) : 0;
  const slaCompliancePercent = tasks.length > 0 ? Math.round(((tasks.length - breachedTasks.length) / tasks.length) * 100) : 100;

  // Breakdown per team member
  const teamBreakdown = team.map(emp => {
    const empTasks = tasks.filter(e => e.assigned_to === emp.id);
    const empResponded = empTasks.filter(e => e.is_responded);
    const empPending = empTasks.filter(e => !e.is_responded);
    const empBreached = empTasks.filter(e => e.sla_metrics && e.sla_metrics.is_breached);

    let empTotalTurnaround = 0;
    empResponded.forEach(e => {
      if (e.response_info && e.response_info.response_time_hours) {
        empTotalTurnaround += e.response_info.response_time_hours;
      }
    });

    const empAvgResponseTime = empResponded.length > 0 ? (empTotalTurnaround / empResponded.length).toFixed(1) : 0;
    const empSlaPercent = empTasks.length > 0 ? Math.round(((empTasks.length - empBreached.length) / empTasks.length) * 100) : 100;

    return {
      employee: emp,
      total_assigned: empTasks.length,
      responded_count: empResponded.length,
      pending_count: empPending.length,
      breached_count: empBreached.length,
      avg_response_hours: empAvgResponseTime,
      sla_compliance_percent: empSlaPercent
    };
  });

  // Task type frequency
  const taskTypeDistribution = {};
  tasks.forEach(e => {
    const type = e.task_type || 'Unspecified';
    taskTypeDistribution[type] = (taskTypeDistribution[type] || 0) + 1;
  });

  // Solution categories frequency
  const solutionCategoryDistribution = {};
  responded.forEach(e => {
    if (e.response_info && e.response_info.solution_category) {
      const cat = e.response_info.solution_category;
      solutionCategoryDistribution[cat] = (solutionCategoryDistribution[cat] || 0) + 1;
    }
  });

  return {
    processedEmails,
    analytics: {
      total_received: totalReceived,
      total_tasks: tasks.length,
      total_general_info: generalInfo.length,
      total_responded: responded.length,
      total_pending: pendingTasks.length,
      sla_breached_count: breachedTasks.length,
      sla_compliance_percent: slaCompliancePercent,
      avg_response_time_hours: avgResponseTimeHours,
      team_breakdown: teamBreakdown,
      task_type_distribution: taskTypeDistribution,
      solution_category_distribution: solutionCategoryDistribution,
      server_time: now.toISOString()
    }
  };
}

// Request parser helper
function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

// MIME types for static files
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml'
};

// HTTP Server
const server = http.createServer(async (req, res) => {
  const reqUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = reqUrl.pathname;
  const method = req.method;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // --- REST API ENDPOINTS ---
  if (pathname.startsWith('/api/')) {
    res.setHeader('Content-Type', 'application/json');

    // 1. GET /api/data - Full dashboard payload
    if (pathname === '/api/data' && method === 'GET') {
      try {
        team = JSON.parse(fs.readFileSync(TEAM_PATH, 'utf-8'));
      } catch (e) {}
      const { processedEmails, analytics } = computeAnalytics();
      res.writeHead(200);
      res.end(JSON.stringify({
        team,
        emails: processedEmails,
        historical_kb: historicalKb,
        analytics
      }));
      return;
    }

    // 2. POST /api/emails/reassign - Manager re-assigns an email
    if (pathname === '/api/emails/reassign' && method === 'POST') {
      try {
        const payload = await readJsonBody(req);
        const { email_id, new_assigned_to, reassign_reason } = payload;

        const targetEmail = emails.find(e => e.id === email_id);
        if (!targetEmail) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: `Email ${email_id} not found` }));
          return;
        }

        const prevAssigneeId = targetEmail.assigned_to;
        targetEmail.assigned_to = new_assigned_to;
        targetEmail.reassignment_log = targetEmail.reassignment_log || [];
        targetEmail.reassignment_log.push({
          timestamp: new Date().toISOString(),
          from: prevAssigneeId,
          to: new_assigned_to,
          reason: reassign_reason || 'Manager workload rebalance / SLA escalation'
        });

        // Re-evaluate historical draft if template had assignee placeholder
        if (targetEmail.historical_match) {
          targetEmail.historical_match = matchHistoricalSolution(targetEmail, historicalKb, team);
        }

        saveEmails();
        res.writeHead(200);
        res.end(JSON.stringify({ success: true, message: `Email ${email_id} reassigned successfully`, email: targetEmail }));
      } catch (err) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: err.message }));
      }
      return;
    }

    // 3. POST /api/emails/respond - Employee responds & records resolution details
    if (pathname === '/api/emails/respond' && method === 'POST') {
      try {
        const payload = await readJsonBody(req);
        const { email_id, responder_id, solution_category, resolution_details, response_body, add_to_kb } = payload;

        const targetEmail = emails.find(e => e.id === email_id);
        if (!targetEmail) {
          res.writeHead(404);
          res.end(JSON.stringify({ error: `Email ${email_id} not found` }));
          return;
        }

        const responder = team.find(m => m.id === responder_id) || { name: 'Support Engineer' };
        const now = new Date();
        const receivedAt = new Date(targetEmail.received_at);
        const turnaroundHours = Math.max(0.1, Number(((now - receivedAt) / (1000 * 60 * 60)).toFixed(2)));

        targetEmail.is_responded = true;
        targetEmail.response_info = {
          responded_at: now.toISOString(),
          responded_by: responder.name,
          response_time_hours: turnaroundHours,
          solution_category: solution_category || 'General Technical Resolution',
          resolution_details: resolution_details || 'Resolved directly with verified team procedure.',
          response_body: response_body || 'Response dispatched to user.'
        };

        // If employee opts to store verified response into Historical Knowledge Base
        if (add_to_kb) {
          const newKbEntry = {
            id: `KB-${100 + historicalKb.length + 1}`,
            title: targetEmail.subject.replace(/^(URGENT:|CRITICAL:)\s*/i, ''),
            task_type: targetEmail.task_type || 'General Technical Query',
            issue_keywords: targetEmail.subject.toLowerCase().split(/[\s,:-]+/).filter(w => w.length > 3),
            solution_category: solution_category,
            historical_ticket_id: `TICK-${Math.floor(1000 + Math.random() * 9000)}`,
            resolved_by: responder.name,
            resolution_date: now.toISOString().split('T')[0],
            verified_draft: response_body,
            resolution_details: resolution_details
          };
          historicalKb.push(newKbEntry);
          saveKb();
        }

        saveEmails();
        res.writeHead(200);
        res.end(JSON.stringify({ success: true, message: `Email ${email_id} marked as responded`, email: targetEmail }));
      } catch (err) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: err.message }));
      }
      return;
    }

    // 4. POST /api/simulate - Ingest new incoming email into agent pipeline
    if (pathname === '/api/simulate' && method === 'POST') {
      try {
        const payload = await readJsonBody(req);
        const { subject, body, sender_name, sender_email, assigned_to } = payload;

        try {
          team = JSON.parse(fs.readFileSync(TEAM_PATH, 'utf-8'));
        } catch (e) {}

        let maxNum = 0;
        emails.forEach(e => {
          const match = (e.id || '').match(/EML-2026-(\d+)/);
          if (match) {
            const n = parseInt(match[1], 10);
            if (n > maxNum) maxNum = n;
          }
        });
        const newId = `EML-2026-${String(maxNum + 1).padStart(3, '0')}`;

        const rawEmail = {
          id: newId,
          subject: subject || 'New Inbound Support Inquiry',
          body: body || '',
          sender: {
            name: sender_name || 'Partner Engineer',
            email: sender_email || 'partner@enterprise.io'
          },
          received_at: new Date().toISOString(),
          assigned_to: assigned_to || (team.length > 0 ? team[Math.floor(Math.random() * team.length)].id : 'emp_01'),
          is_responded: false,
          response_info: null
        };

        // Process through Agent Pipeline
        const processed = processEmail(rawEmail, historicalKb, team, new Date());
        emails.unshift(processed);
        saveEmails();

        res.writeHead(201);
        res.end(JSON.stringify({ success: true, email: processed }));
      } catch (err) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: err.message }));
      }
      return;
    }

    // 5. POST /api/reset - Reset benchmark dataset for hackathon presentation demos
    if (pathname === '/api/reset' && method === 'POST') {
      try {
        if (fs.existsSync(BACKUP_EMAILS_PATH)) {
          emails = JSON.parse(fs.readFileSync(BACKUP_EMAILS_PATH, 'utf-8'));
          saveEmails();
        }
        res.writeHead(200);
        res.end(JSON.stringify({ success: true, message: 'Benchmark data re-initialized' }));
      } catch (err) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: err.message }));
      }
      return;
    }

    // Not found API route
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Endpoint not found' }));
    return;
  }

  // --- STATIC FILE SERVING ---
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('404 Not Found');
      } else {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end(`Server Error: ${err.code}`);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

server.listen(PORT, () => {
  console.log(`=======================================================`);
  console.log(` KnoxFlow Agentic SLA System is running!`);
  console.log(` URL: http://localhost:${PORT}`);
  console.log(` Zero external dependencies required.`);
  console.log(`=======================================================`);
});
