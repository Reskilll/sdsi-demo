'use strict';

const express = require('express');
const { param } = require('express-validator');
const ctrl = require('../controllers/studentController');
const { authenticate, authorize } = require('../middleware/auth');
const { studentRules, handleValidation } = require('../middleware/validate');

const router = express.Router();

// Every student route requires a valid session.
router.use(authenticate);

const idRule = [param('id').isInt({ min: 1 }).withMessage('Invalid id.'), handleValidation];

// Read: any authenticated user.
router.get('/', ctrl.listStudents);
router.get('/:id', idRule, ctrl.getStudent);

// Write: admins only (role-based access control).
router.post('/', authorize('admin'), studentRules, handleValidation, ctrl.createStudent);
router.put('/:id', authorize('admin'), idRule, studentRules, handleValidation, ctrl.updateStudent);
router.delete('/:id', authorize('admin'), idRule, ctrl.deleteStudent);

module.exports = router;
