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
      if (isNaN(parsedAmount) || parsedAmount <= 0) {
        return res.status(400).json({ error: 'Amount must be a positive number' });
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
          if (shareMemberIds.length === 0) {
            return res
              .status(400)
              .json({ error: 'At least one member must be included in the split' });
          }
          // Deduplicate — each member should appear once
          const uniqueIds = new Set(shareMemberIds);
          if (uniqueIds.size !== shareMemberIds.length) {
            return res
              .status(400)
              .json({ error: 'Duplicate members in share list' });
          }
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
          if (!shares || !Array.isArray(shares) || shares.length === 0) {
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
          computedShares = shares.map((s) => {
            const shareAmt = parseFloat(s.amount);
            if (isNaN(shareAmt) || shareAmt < 0) {
              return { memberId: s.memberId, amount: NaN, _error: true };
            }
            return {
              memberId: s.memberId,
              amount: parseFloat(shareAmt.toFixed(2)),
            };
          });
          const badShare = computedShares.find((s) => s._error);
          if (badShare) {
            return res.status(400).json({
              error: `Invalid share amount for member ${badShare.memberId}`,
            });
          }
          break;
        }

        case 'PERCENTAGE': {
          if (!shares || !Array.isArray(shares) || shares.length === 0) {
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

        // Validate description
        if (!exp.description || !String(exp.description).trim()) {
          return res
            .status(400)
            .json({ error: `Expense ${i}: description is required` });
        }

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
        if (isNaN(parsedAmount) || parsedAmount <= 0) {
          return res
            .status(400)
            .json({ error: `Expense ${i}: amount must be a positive number` });
        }

        if (!exp.shares || !Array.isArray(exp.shares) || exp.shares.length === 0) {
          return res
            .status(400)
            .json({ error: `Expense ${i}: shares array is required` });
        }

        let computedShares;
        switch (exp.splitType) {
          case 'EQUAL': {
            const shareMemberIds = exp.shares.map((s) => {
              if (s.memberName) {
                const id = memberMap.get(s.memberName);
                if (!id)
                  return null;
                return id;
              }
              return s.memberId;
            });
            // Check for unresolved member names
            const unresolvedIdx = shareMemberIds.findIndex((id) => id === null || !memberIds.has(id));
            if (unresolvedIdx >= 0) {
              const name = exp.shares[unresolvedIdx].memberName || exp.shares[unresolvedIdx].memberId;
              return res.status(400).json({
                error: `Expense ${i}: member "${name}" is not in this group`,
              });
            }
            if (shareMemberIds.length === 0) {
              return res.status(400).json({
                error: `Expense ${i}: at least one member must be included in the split`,
              });
            }
            computedShares = computeEqualShares(parsedAmount, shareMemberIds);
            break;
          }
          case 'EXACT': {
            computedShares = exp.shares.map((s) => {
              const mid = s.memberName ? memberMap.get(s.memberName) : s.memberId;
              if (!mid || !memberIds.has(mid)) {
                const name = s.memberName || s.memberId;
                return { memberId: null, amount: parseFloat(parseFloat(s.amount).toFixed(2)), _error: `member "${name}" is not in this group` };
              }
              return { memberId: mid, amount: parseFloat(parseFloat(s.amount).toFixed(2)) };
            });
            const exactErr = computedShares.find((s) => s._error);
            if (exactErr) {
              return res.status(400).json({ error: `Expense ${i}: ${exactErr._error}` });
            }
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
            computedShares = exp.shares.map((s) => {
              const mid = s.memberName ? memberMap.get(s.memberName) : s.memberId;
              if (!mid || !memberIds.has(mid)) {
                const name = s.memberName || s.memberId;
                return { memberId: null, percentage: parseFloat(s.percentage), _error: `member "${name}" is not in this group` };
              }
              return { memberId: mid, percentage: parseFloat(s.percentage) };
            });
            const pctErr = computedShares.find((s) => s._error);
            if (pctErr) {
              return res.status(400).json({ error: `Expense ${i}: ${pctErr._error}` });
            }
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
          description: String(exp.description).trim(),
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