const Group = require('../models/group');

const groupController = {
  async create(req, res, next) {
    try {
      const { name, description } = req.body;
      if (!name || !name.trim()) {
        return res.status(400).json({ error: 'Group name is required' });
      }
      const group = await Group.create({ name: name.trim(), description });
      res.status(201).json(group);
    } catch (err) {
      next(err);
    }
  },

  async list(_req, res, next) {
    try {
      const groups = await Group.findAll();
      res.json(groups);
    } catch (err) {
      next(err);
    }
  },

  async getById(req, res, next) {
    try {
      const group = await Group.findById(req.params.groupId);
      if (!group) {
        return res.status(404).json({ error: 'Group not found' });
      }
      res.json(group);
    } catch (err) {
      next(err);
    }
  },

  async update(req, res, next) {
    try {
      const group = await Group.update(req.params.groupId, req.body);
      if (!group) {
        return res.status(404).json({ error: 'Group not found' });
      }
      res.json(group);
    } catch (err) {
      next(err);
    }
  },

  async delete(req, res, next) {
    try {
      const group = await Group.delete(req.params.groupId);
      if (!group) {
        return res.status(404).json({ error: 'Group not found' });
      }
      res.json({ message: 'Group deleted', group });
    } catch (err) {
      next(err);
    }
  },
};

module.exports = groupController;