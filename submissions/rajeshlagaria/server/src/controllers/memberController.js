const Member = require('../models/member');
const Group = require('../models/group');

const memberController = {
  async create(req, res, next) {
    try {
      const { groupId } = req.params;
      const group = await Group.findById(groupId);
      if (!group) {
        return res.status(404).json({ error: 'Group not found' });
      }

      const { name, email } = req.body;
      if (!name || !name.trim()) {
        return res.status(400).json({ error: 'Member name is required' });
      }

      // Check for duplicate name within the group
      const existing = await Member.findByGroupAndName(groupId, name.trim());
      if (existing) {
        return res
          .status(409)
          .json({ error: `Member "${name}" already exists in this group` });
      }

      const member = await Member.create(groupId, {
        name: name.trim(),
        email,
      });
      res.status(201).json(member);
    } catch (err) {
      next(err);
    }
  },

  async listByGroup(req, res, next) {
    try {
      const { groupId } = req.params;
      const group = await Group.findById(groupId);
      if (!group) {
        return res.status(404).json({ error: 'Group not found' });
      }
      const members = await Member.findByGroup(groupId);
      res.json(members);
    } catch (err) {
      next(err);
    }
  },

  async delete(req, res, next) {
    try {
      // Check if member is referenced in any expense (as payer or share)
      const pool = require('../db');
      const refCheck = await pool.query(
        `SELECT
          EXISTS(SELECT 1 FROM expenses WHERE payer_id = $1) OR
          EXISTS(SELECT 1 FROM expense_shares WHERE member_id = $1)
         AS has_refs`,
        [req.params.memberId]
      );
      if (refCheck.rows[0].has_refs) {
        return res.status(400).json({
          error:
            'Cannot remove this member: they are referenced in existing expenses. Remove those expenses first.',
        });
      }

      const member = await Member.delete(req.params.memberId);
      if (!member) {
        return res.status(404).json({ error: 'Member not found' });
      }
      res.json({ message: 'Member removed', member });
    } catch (err) {
      next(err);
    }
  },
};

module.exports = memberController;