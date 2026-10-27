'use strict';

/**
 * Small error hierarchy so routes can throw domain errors and the central
 * error handler turns them into the right HTTP status + JSON body.
 */
class AppError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.statusCode = statusCode;
  }
}

class ValidationError extends AppError {
  constructor(message) {
    super(400, message);
  }
}

class ConflictError extends AppError {
  constructor(message) {
    super(409, message);
  }
}

module.exports = { AppError, ValidationError, ConflictError };