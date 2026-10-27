const { computeSettlements } = require('../services/settlementService');
const Group = require('../models/group');

const settlementController = {
  async getSettlements(req, res, next) {
    try {
      const group = await Group.findById(req.params.groupId);
      if (!group) return res.status(404).json({ error: 'Group not found' });

      const settlements = await computeSettlements(req.params.groupId);
      res.json(settlements);
    } catch (err) {
      next(err);
    }
  },
};

module.exports = settlementController;