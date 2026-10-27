const { computeSettlements } = require('../services/settlementService');

const settlementController = {
  async getSettlements(req, res, next) {
    try {
      const settlements = await computeSettlements(req.params.groupId);
      res.json(settlements);
    } catch (err) {
      next(err);
    }
  },
};

module.exports = settlementController;