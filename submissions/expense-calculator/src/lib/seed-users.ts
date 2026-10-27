/**
 * Seeds localStorage with test user accounts for development/demo.
 *
 * Run in browser console:
 *   import('./lib/seed-users.js').then(m => m.seedTestUsers())
 *
 * Or call seedTestUsers() from any component during development.
 */

import { register } from './auth';

const TEST_USERS = [
  { name: 'Alice Johnson', email: 'alice@demo.com', password: 'demo123' },
  { name: 'Bob Smith',     email: 'bob@demo.com',   password: 'demo123' },
  { name: 'Charlie Park',  email: 'charlie@demo.com', password: 'demo123' },
  { name: 'Diana Lee',     email: 'diana@demo.com',  password: 'demo123' },
  { name: 'Eve Chen',      email: 'eve@demo.com',    password: 'demo123' },
];

export function seedTestUsers(): void {
  for (const cred of TEST_USERS) {
    const result = register(cred);
    if (result.success) {
      console.log(`✓ Created: ${cred.name} (${cred.email})`);
    } else {
      // Already exists — skip
      console.log(`- Skipped: ${cred.name} (${cred.email}) — ${result.error}`);
    }
  }
  console.log('\n--- Test Credentials ---');
  console.log('email:    alice@demo.com  |  bob@demo.com  |  charlie@demo.com  |  diana@demo.com  |  eve@demo.com');
  console.log('password: demo123         |  demo123       |  demo123            |  demo123         |  demo123');
  console.log('------------------------');
}

// Auto-seed when run directly with tsx/node
if (typeof process !== 'undefined' && process.env.SEED_USERS === '1') {
  seedTestUsers();
}