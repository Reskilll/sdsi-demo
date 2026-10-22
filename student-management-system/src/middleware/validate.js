'use strict';

const { validationResult, body } = require('express-validator');

// Collects express-validator errors into a single 422 response.
function handleValidation(req, res, next) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(422).json({
      error: 'Validation failed.',
      details: errors.array().map((e) => ({ field: e.path, message: e.msg })),
    });
  }
  return next();
}

// Strong password: >= 8 chars, upper, lower, number, symbol.
const passwordRule = body('password')
  .isString()
  .isLength({ min: 8, max: 128 })
  .withMessage('Password must be 8-128 characters.')
  .matches(/[a-z]/)
  .withMessage('Password must contain a lowercase letter.')
  .matches(/[A-Z]/)
  .withMessage('Password must contain an uppercase letter.')
  .matches(/[0-9]/)
  .withMessage('Password must contain a number.')
  .matches(/[^A-Za-z0-9]/)
  .withMessage('Password must contain a symbol.');

const registerRules = [
  body('email').isEmail().withMessage('A valid email is required.').normalizeEmail(),
  passwordRule,
];

const loginRules = [
  body('email').isEmail().withMessage('A valid email is required.').normalizeEmail(),
  body('password').isString().notEmpty().withMessage('Password is required.'),
];

const studentRules = [
  body('first_name').trim().isLength({ min: 1, max: 60 }).withMessage('First name is required (max 60).').escape(),
  body('last_name').trim().isLength({ min: 1, max: 60 }).withMessage('Last name is required (max 60).').escape(),
  body('email').isEmail().withMessage('A valid student email is required.').normalizeEmail(),
  body('age').isInt({ min: 3, max: 120 }).withMessage('Age must be between 3 and 120.').toInt(),
  body('grade').trim().isLength({ min: 1, max: 20 }).withMessage('Grade is required (max 20).').escape(),
  body('enrolled').optional().isBoolean().withMessage('Enrolled must be true/false.').toBoolean(),
];

module.exports = {
  handleValidation,
  registerRules,
  loginRules,
  studentRules,
};
