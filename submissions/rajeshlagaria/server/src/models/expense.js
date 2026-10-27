const pool = require('../db');

const Expense = {
  /**
   * Create an expense with its shares in a transaction.
   * @param {Object} params
   * @param {string} params.groupId
   * @param {string} params.payerId
   * @param {string} params.description
   * @param {number} params.amount
   * @param {'EQUAL'|'EXACT'|'PERCENTAGE'} params.splitType
   * @param {Array<{memberId: string, amount: number, percentage?: number}>} params.shares
   */
  async create({ groupId, payerId, description, amount, splitType, shares }) {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      const expenseResult = await client.query(
        `INSERT INTO expenses (group_id, payer_id, description, amount, split_type)
         VALUES ($1, $2, $3, $4, $5) RETURNING *`,
        [groupId, payerId, description, amount, splitType]
      );
      const expense = expenseResult.rows[0];

      for (const share of shares) {
        await client.query(
          `INSERT INTO expense_shares (expense_id, member_id, share_amount, share_percentage)
           VALUES ($1, $2, $3, $4)`,
          [expense.id, share.memberId, share.amount, share.percentage || null]
        );
      }

      await client.query('COMMIT');
      return this.findById(expense.id);
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  },

  /**
   * Batch create expenses in a single transaction (all-or-nothing).
   */
  async batchCreate(groupId, expenses) {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const created = [];

      for (const exp of expenses) {
        const expenseResult = await client.query(
          `INSERT INTO expenses (group_id, payer_id, description, amount, split_type)
           VALUES ($1, $2, $3, $4, $5) RETURNING *`,
          [groupId, exp.payerId, exp.description, exp.amount, exp.splitType]
        );
        const expense = expenseResult.rows[0];

        for (const share of exp.shares) {
          await client.query(
            `INSERT INTO expense_shares (expense_id, member_id, share_amount, share_percentage)
             VALUES ($1, $2, $3, $4)`,
            [expense.id, share.memberId, share.amount, share.percentage || null]
          );
        }

        created.push(expense.id);
      }

      await client.query('COMMIT');

      // Fetch all created expenses with shares
      const result = await client.query(
        `SELECT e.*, json_agg(json_build_object(
          'id', es.id, 'memberId', es.member_id, 'amount', es.share_amount, 'percentage', es.share_percentage
        )) as shares
         FROM expenses e
         JOIN expense_shares es ON es.expense_id = e.id
         WHERE e.id = ANY($1)
         GROUP BY e.id`,
        [created]
      );
      return result.rows;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  },

  async findById(id) {
    const result = await pool.query(
      `SELECT e.*,
              json_agg(json_build_object(
                'id', es.id,
                'memberId', es.member_id,
                'amount', es.share_amount,
                'percentage', es.share_percentage
              )) as shares
       FROM expenses e
       JOIN expense_shares es ON es.expense_id = e.id
       WHERE e.id = $1
       GROUP BY e.id`,
      [id]
    );
    return result.rows[0] || null;
  },

  async findByGroup(groupId) {
    const result = await pool.query(
      `SELECT e.*,
              json_agg(json_build_object(
                'id', es.id, 'memberId', es.member_id, 'amount', es.share_amount, 'percentage', es.share_percentage
              )) as shares,
              m.name as payer_name
       FROM expenses e
       JOIN expense_shares es ON es.expense_id = e.id
       JOIN members m ON m.id = e.payer_id
       WHERE e.group_id = $1
       GROUP BY e.id, m.name
       ORDER BY e.created_at DESC`,
      [groupId]
    );
    return result.rows;
  },

  async delete(id) {
    const result = await pool.query(
      'DELETE FROM expenses WHERE id = $1 RETURNING *',
      [id]
    );
    return result.rows[0] || null;
  },
};

module.exports = Expense;