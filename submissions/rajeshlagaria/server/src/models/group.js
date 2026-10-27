const pool = require('../db');

const Group = {
  async create({ name, description }) {
    const result = await pool.query(
      'INSERT INTO groups (name, description) VALUES ($1, $2) RETURNING *',
      [name, description || null]
    );
    return result.rows[0];
  },

  async findAll() {
    const result = await pool.query(
      'SELECT * FROM groups ORDER BY created_at DESC'
    );
    return result.rows;
  },

  async findById(id) {
    const result = await pool.query('SELECT * FROM groups WHERE id = $1', [id]);
    return result.rows[0] || null;
  },

  async update(id, { name, description }) {
    const result = await pool.query(
      'UPDATE groups SET name = COALESCE($2, name), description = COALESCE($3, description) WHERE id = $1 RETURNING *',
      [id, name, description]
    );
    return result.rows[0] || null;
  },

  async delete(id) {
    const result = await pool.query(
      'DELETE FROM groups WHERE id = $1 RETURNING *',
      [id]
    );
    return result.rows[0] || null;
  },
};

module.exports = Group;