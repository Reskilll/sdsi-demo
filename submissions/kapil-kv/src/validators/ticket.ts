import Joi from "joi";

export const createTicketSchema = Joi.object({
  title: Joi.string().required().min(1).max(500),
  description: Joi.string().allow("").max(5000).default(""),
  priority: Joi.string().valid("P1", "P2", "P3", "P4").required(),
  assigneeGroup: Joi.string().pattern(/^[a-f\d]{24}$/i).allow(null).default(null),
  status: Joi.string().valid("OPEN", "IN_PROGRESS").default("OPEN"),
});

export const updateTicketSchema = Joi.object({
  title: Joi.string().min(1).max(500),
  description: Joi.string().allow("").max(5000),
  priority: Joi.string().valid("P1", "P2", "P3", "P4"),
  assigneeGroup: Joi.string().pattern(/^[a-f\d]{24}$/i).allow(null),
});

export const ticketStatusSchema = Joi.object({
  status: Joi.string().valid("OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED").required(),
  reason: Joi.string().max(1000).allow("").default(""),
});

export const ticketQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  limit: Joi.number().integer().min(1).max(100).default(20),
  search: Joi.string().max(200).allow(""),
  priority: Joi.alternatives().try(
    Joi.string().valid("P1", "P2", "P3", "P4"),
    Joi.array().items(Joi.string().valid("P1", "P2", "P3", "P4")),
  ),
  status: Joi.alternatives().try(
    Joi.string().valid("OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED"),
    Joi.array().items(Joi.string().valid("OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED")),
  ),
  assigneeGroup: Joi.string().pattern(/^[a-f\d]{24}$/i).allow(""),
  dateFrom: Joi.date().iso(),
  dateTo: Joi.date().iso(),
  sortBy: Joi.string().valid("createdAt", "updatedAt", "ticketNumber", "priority", "status").default("createdAt"),
  sortOrder: Joi.string().valid("asc", "desc").default("desc"),
});

export const ticketIdParamsSchema = Joi.object({
  id: Joi.string().pattern(/^[a-f\d]{24}$/i).required(),
});