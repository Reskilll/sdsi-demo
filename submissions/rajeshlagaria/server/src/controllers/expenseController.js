const Expense = require('../models/expense');
const Group = require('../models/group');
const Member = require('../models/member');
const {
  validatePercentages,
  validateExactAmounts,
  computeEqualShares,
  computePercentageShares,
} = require('../utils/validation');

const expenseController = {
  /**
   * POST /api/groups/:groupId/expenses
   * Create a single expense.
   */
  async create(req, res, next) {
    try {
      const { groupId } = req.params;
      const { payerId, description, amount, splitType, shares } = req.body;

      // --- Validation ---
      const group = await Group.findById(groupId);
      if (!group) return res.status(404).json({ error: 'Group not found' });

      // Validate payer is a group member (M5)
      const payer = await Member.findById(payerId);
      if (!payer || payer.group_id !== groupId) {
        return res
          .status(400)
          .json({ error: 'Payer must be a member of this group' });
      }

      if (!description || !description.trim()) {
        return res.status(400).json({ error: 'Description is required' });
      }

      const parsedAmount = parseFloat(amount);
      if (!parsedAmount || parsedAmount <= 0) {
        return res.status(400).json({ error: 'Amount must be positive' });
      }

      if (!['EQUAL', 'EXACT', 'PERCENTAGE'].includes(splitType)) {
        return res
          .status(400)
          .json({ error: 'splitType must be EQUAL, EXACT, or PERCENTAGE' });
      }

      // Validate all share memberIds are group members
      const groupMembers = await Member.findByGroup(groupId);
      const memberIds = new Set(groupMembers.map((m) => m.id));

      // Compute and validate shares
      let computedShares;
      switch (splitType) {
        case 'EQUAL': {
          if (!shares || !Array.isArray(shares) || shares.length === 0) {
            return res
              .status(400)
              .json({ error: 'shares array is required with memberIds' });
          }
          const shareMemberIds = shares.map((s) => s.memberId);
          for (const mid of shareMemberIds) {
            if (!memberIds.has(mid)) {
              return res
                .status(400)
                .json({ error: `Member ${mid} is not in this group` });
            }
          }
          computedShares = computeEqualShares(parsedAmount, shareMemberIds);
          break;
        }

        case 'EXACT': {
          if (!shares || !Array.isArray(shares)) {
            return res
              .status(400)
              .json({ error: 'shares array with exact amounts is required' });
          }
          for (const s of shares) {
            if (!memberIds.has(s.memberId)) {
              return res
                .status(400)
                .json({ error: `Member ${s.memberId} is not in this group` });
            }
          }
          // M5: exact amounts must sum to total
          if (!validateExactAmounts(shares, parsedAmount)) {
            return res.status(400).json({
              error: `Exact share amounts must sum to the total (${parsedAmount})`,
            });
          }
          computedShares = shares.map((s) => ({
            memberId: s.memberId,
            amount: parseFloat(parseFloat(s.amount).toFixed(2)),
          }));
          break;
        }

        case 'PERCENTAGE': {
          if (!shares || !Array.isArray(shares)) {
            return res
              .status(400)
              .json({ error: 'shares array with percentages is required' });
          }
          for (const s of shares) {
            if (!memberIds.has(s.memberId)) {
              return res
                .status(400)
                .json({ error: `Member ${s.memberId} is not in this group` });
            }
          }
          // M5: percentages must sum to 100
          if (!validatePercentages(shares)) {
            return res
              .status(400)
              .json({ error: 'Percentages must sum to 100' });
          }
          computedShares = computePercentageShares(parsedAmount, shares);
          break;
        }
      }

      const expense = await Expense.create({
        groupId,
        payerId,
        description: description.trim(),
        amount: parsedAmount,
        splitType,
        shares: computedShares,
      });

      res.status(201).json(expense);
    } catch (err) {
      next(err);
    }
  },

  /**
   * POST /api/groups/:groupId/expenses/batch
   * Create multiple expenses in a single transaction.
   */
  async batchCreate(req, res, next) {
    try {
      const { groupId } = req.params;
      const { expenses } = req.body;

      const group = await Group.findById(groupId);
      if (!group) return res.status(404).json({ error: 'Group not found' });

      if (!expenses || !Array.isArray(expenses) || expenses.length === 0) {
        return res.status(400).json({ error: 'expenses array is required' });
      }

      const groupMembers = await Member.findByGroup(groupId);
      const memberIds = new Set(groupMembers.map((m) => m.id));
      const memberMap = new Map(groupMembers.map((m) => [m.name, m.id]));

      const processed = [];

      for (let i = 0; i < expenses.length; i++) {
        const exp = expenses[i];

        // Resolve payer: accept either id or name
        let payerId = exp.payerId;
        if (!payerId && exp.payerName) {
          payerId = memberMap.get(exp.payerName);
          if (!payerId) {
            return res.status(400).json({
              error: `Expense ${i}: payer "${exp.payerName}" is not a group member`,
            });
          }
        }

        if (!payerId || !memberIds.has(payerId)) {
          return res
            .status(400)
            .json({ error: `Expense ${i}: payer must be a group member` });
        }

        const parsedAmount = parseFloat(exp.amount);
        if (!parsedAmount || parsedAmount <= 0) {
          return res
            .status(400)
            .json({ error: `Expense ${i}: amount must be positive` });
        }

        let computedShares;
        switch (exp.splitType) {
          case 'EQUAL': {
            const shareMemberIds = exp.shares.map((s) => {
              if (s.memberName) {
                const id = memberMap.get(s.memberName);
                if (!id)
                  throw new Error(
                    `Expense ${i}: member "${s.memberName}" not found`
                  );
                return id;
              }
              return s.memberId;
            });
            computedShares = computeEqualShares(parsedAmount, shareMemberIds);
            break;
          }
          case 'EXACT': {
            computedShares = exp.shares.map((s) => ({
              memberId: s.memberName
                ? memberMap.get(s.memberName)
                : s.memberId,
              amount: parseFloat(parseFloat(s.amount).toFixed(2)),
            }));
            if (
              !validateExactAmounts(
                computedShares.map((s) => ({ amount: s.amount })),
                parsedAmount
              )
            ) {
              return res.status(400).json({
                error: `Expense ${i}: exact amounts must sum to ${parsedAmount}`,
              });
            }
            break;
          }
          case 'PERCENTAGE': {
            computedShares = exp.shares.map((s) => ({
              memberId: s.memberName
                ? memberMap.get(s.memberName)
                : s.memberId,
              percentage: parseFloat(s.percentage),
            }));
            if (!validatePercentages(computedShares)) {
              return res
                .status(400)
                .json({ error: `Expense ${i}: percentages must sum to 100` });
            }
            computedShares = computePercentageShares(
              parsedAmount,
              computedShares
            );
            break;
          }
          default:
            return res
              .status(400)
              .json({ error: `Expense ${i}: invalid splitType` });
        }

        processed.push({
          payerId,
          description: exp.description,
          amount: parsedAmount,
          splitType: exp.splitType,
          shares: computedShares,
        });
      }

      const result = await Expense.batchCreate(groupId, processed);
      res.status(201).json(result);
    } catch (err) {
      next(err);
    }
  },

  /**
   * GET /api/groups/:groupId/expenses
   */
  async listByGroup(req, res, next) {
    try {
      const expenses = await Expense.findByGroup(req.params.groupId);
      res.json(expenses);
    } catch (err) {
      next(err);
    }
  },

  /**
   * GET /api/groups/:groupId/expenses/:expenseId
   */
  async getById(req, res, next) {
    try {
      const expense = await Expense.findById(req.params.expenseId);
      if (!expense)
        return res.status(404).json({ error: 'Expense not found' });
      res.json(expense);
    } catch (err) {
      next(err);
    }
  },

  /**
   * DELETE /api/groups/:groupId/expenses/:expenseId
   */
  async delete(req, res, next) {
    try {
      const expense = await Expense.delete(req.params.expenseId);
      if (!expense)
        return res.status(404).json({ error: 'Expense not found' });
      res.json({ message: 'Expense deleted', expense });
    } catch (err) {
      next(err);
    }
  },
};

module.exports = expenseController;