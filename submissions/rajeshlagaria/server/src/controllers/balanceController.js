const { computeBalances } = require('../services/balanceService');
const Group = require('../models/group');

const balanceController = {
  async getBalances(req, res, next) {
    try {
      const group = await Group.findById(req.params.groupId);
      if (!group) return res.status(404).json({ error: 'Group not found' });

      const balances = await computeBalances(req.params.groupId);
      res.json(balances);
    } catch (err) {
      next(err);
    }
  },
};

module.exports = balanceController;