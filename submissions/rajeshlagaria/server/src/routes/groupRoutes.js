const { Router } = require('express');
const groupController = require('../controllers/groupController');
const memberController = require('../controllers/memberController');
const expenseController = require('../controllers/expenseController');
const balanceController = require('../controllers/balanceController');
const settlementController = require('../controllers/settlementController');

const router = Router();

// Group routes
router.post('/', groupController.create);
router.get('/', groupController.list);
router.get('/:groupId', groupController.getById);
router.patch('/:groupId', groupController.update);
router.delete('/:groupId', groupController.delete);

// Nested member routes
router.post('/:groupId/members', memberController.create);
router.get('/:groupId/members', memberController.listByGroup);
router.delete('/:groupId/members/:memberId', memberController.delete);

// Nested expense routes
router.post('/:groupId/expenses', expenseController.create);
router.post('/:groupId/expenses/batch', expenseController.batchCreate);
router.get('/:groupId/expenses', expenseController.listByGroup);
router.get('/:groupId/expenses/:expenseId', expenseController.getById);
router.delete('/:groupId/expenses/:expenseId', expenseController.delete);

// Balances (M2)
router.get('/:groupId/balances', balanceController.getBalances);

// Settlements (M3)
router.get('/:groupId/settlements', settlementController.getSettlements);

module.exports = router;