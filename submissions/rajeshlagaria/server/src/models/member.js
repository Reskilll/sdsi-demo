const pool = require('../db');

const Member = {
  async create(groupId, { name, email }) {
    const result = await pool.query(
      'INSERT INTO members (group_id, name, email) VALUES ($1, $2, $3) RETURNING *',
      [groupId, name, email || null]
    );
    return result.rows[0];
  },

  async findByGroup(groupId) {
    const result = await pool.query(
      'SELECT * FROM members WHERE group_id = $1 ORDER BY name ASC',
      [groupId]
    );
    return result.rows;
  },

  async findById(id) {
    const result = await pool.query('SELECT * FROM members WHERE id = $1', [id]);
    return result.rows[0] || null;
  },

  async findByGroupAndName(groupId, name) {
    const result = await pool.query(
      'SELECT * FROM members WHERE group_id = $1 AND name = $2',
      [groupId, name]
    );
    return result.rows[0] || null;
  },

  async delete(id) {
    const result = await pool.query(
      'DELETE FROM members WHERE id = $1 RETURNING *',
      [id]
    );
    return result.rows[0] || null;
  },
};

module.exports = Member;