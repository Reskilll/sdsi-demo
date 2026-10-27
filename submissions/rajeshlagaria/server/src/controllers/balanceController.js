const { computeBalances } = require('../services/balanceService');

const balanceController = {
  async getBalances(req, res, next) {
    try {
      const balances = await computeBalances(req.params.groupId);
      res.json(balances);
    } catch (err) {
      next(err);
    }
  },
};

module.exports = balanceController;