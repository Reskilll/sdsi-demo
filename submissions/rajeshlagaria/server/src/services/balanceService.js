const pool = require('../db');

/**
 * Compute net balances for all members in a group (M2).
 *
 * Net balance = (total paid by member) - (total owed by member)
 * Positive = others owe them money (creditor)
 * Negative = they owe others money (debtor)
 */
async function computeBalances(groupId) {
  const result = await pool.query(
    `WITH paid AS (
       SELECT payer_id AS member_id, SUM(amount) AS total_paid
       FROM expenses
       WHERE group_id = $1
       GROUP BY payer_id
     ),
     owed AS (
       SELECT es.member_id, SUM(es.share_amount) AS total_owed
       FROM expense_shares es
       JOIN expenses e ON e.id = es.expense_id
       WHERE e.group_id = $1
       GROUP BY es.member_id
     )
     SELECT
       m.id,
       m.name,
       COALESCE(p.total_paid, 0)::NUMERIC(12,2) AS paid,
       COALESCE(o.total_owed, 0)::NUMERIC(12,2) AS owed,
       (COALESCE(p.total_paid, 0) - COALESCE(o.total_owed, 0))::NUMERIC(12,2) AS balance
     FROM members m
     LEFT JOIN paid p ON p.member_id = m.id
     LEFT JOIN owed o ON o.member_id = m.id
     WHERE m.group_id = $1
     ORDER BY balance DESC`,
    [groupId]
  );
  return result.rows;
}

module.exports = { computeBalances };